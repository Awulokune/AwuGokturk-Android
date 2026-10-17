"""Model güncelleme sistemi testleri (istenen senaryolar + güvenlik testleri).

Çalıştırma (embedded_agent/ dizininden):
    python3 -m unittest tests.test_model_updater -v
    python3 -m unittest discover -s tests

ÖNEMLİ (dürüstlük): Bu testler GERÇEK ağ kullanmaz. Taşıma katmanı
(`fetch_bytes` / `download_to`) sahte bir katmanla değiştirilir; böylece
indirme yarıda kalması, SHA uyuşmazlığı, disk yetersizliği gibi durumlar
gerçek ağ beklemeden ve tekrarlanabilir biçimde denenir.

Testlerde kullanılan "yeni sürüm" dosyası, paket içi modelin ağırlıklarından
türetilmiş bir SENTETİK dosyadır; gerçekten yayımlanmış bir model sürümü
DEĞİLDİR. Depoda yayımlanmış sürüm bulunmadığı için canlı senaryo yalnızca
`AWU_LIVE_UPDATE_TEST=1` verildiğinde çalışır (opt-in).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from awa_agent import android_bridge as AB
from awa_agent import classifier5k as C5
from awa_agent import classifier5k_lite as LITE
from awa_agent import model_updater as MU

_ROOT = Path(__file__).resolve().parents[1]                      # embedded_agent/
BUNDLED = _ROOT / "android" / "app" / "src" / "main" / "assets" / "classifier5k.json"

OWNER, REPO = MU.GITHUB_OWNER, MU.GITHUB_REPO
BASE = "https://github.com/{o}/{r}/releases/download".format(o=OWNER, r=REPO)
MANIFEST_URL = BASE + "/v5K-1.1.0/awu-model-manifest.json"
ARTIFACT_URL = BASE + "/v5K-1.1.0/classifier5k.json"


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def synthetic_artifact(version: str = "5K-1.1.0", name: str = None) -> bytes:
    """Paket içi modelden türetilmiş SENTETİK ağırlık dosyası (test amaçlı)."""
    d = json.loads(BUNDLED.read_text(encoding="utf-8"))
    d["model_version"] = version
    if name:
        d["model_name"] = name
    # Ağırlığı hafifçe oynat: dosya "farklı bir model" olsun (yapı aynı kalır).
    d["fc_bias"] = [float(x) + 0.013 for x in d["fc_bias"]]
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


def manifest_for(artifact: bytes, version: str = "5K-1.1.0",
                 url: str = ARTIFACT_URL, sha256: str = None,
                 size: int = None, fmt: str = "awugokturk-mcu-5k-lite-v1",
                 arch: str = "lite-json-v1", min_app: str = "1.0.0",
                 name: str = "classifier5k.json") -> dict:
    import hashlib
    return {
        "manifest_version": 1,
        "model_name": "AwuGöktürk-Microcontroller:5K",
        "model_version": version,
        "architecture": arch,
        "format": fmt,
        "tokenizer_version": "char-vocab-103",
        "vocab_size": 103,
        "labels": 8,
        "emb": 8,
        "hidden": 31,
        "artifact": {
            "name": name,
            "url": url,
            "size": size if size is not None else len(artifact),
            "sha256": sha256 or hashlib.sha256(artifact).hexdigest(),
        },
        "min_app_version": min_app,
        "release_notes": "Test sürümü: sentetik ağırlık dosyası.",
    }


def release(manifest: dict, artifact: bytes, tag: str = "v5K-1.1.0",
            draft: bool = False, prerelease: bool = False) -> dict:
    return {
        "tag_name": tag,
        "name": "AwuGöktürk-5K " + tag,
        "draft": draft,
        "prerelease": prerelease,
        "published_at": "2026-01-01T00:00:00Z",
        "html_url": "https://github.com/{o}/{r}/releases/tag/{t}".format(o=OWNER, r=REPO, t=tag),
        "assets": [
            {"name": MU.MANIFEST_ASSET_NAME, "browser_download_url": MANIFEST_URL,
             "size": len(json.dumps(manifest).encode("utf-8"))},
            {"name": manifest["artifact"]["name"],
             "browser_download_url": manifest["artifact"]["url"],
             "size": len(artifact)},
        ],
    }


class FakeNet:
    """Sahte taşıma katmanı: URL → bayt eşlemesi + hata enjeksiyonu."""

    def __init__(self):
        self.responses = {}          # url -> bytes
        self.errors = {}             # url -> Exception (fetch)
        self.download_error = {}     # url -> Exception
        self.truncate = {}           # url -> oran (0..1): yarıda kes
        self.lingering = False       # True → bloklar arası bekle (iptal denemesi)
        self.calls = []
        self.progress_seen = []

    def set(self, url, data: bytes) -> "FakeNet":
        self.responses[url] = data
        return self

    def fetch_bytes(self, url, max_bytes=None, timeout=None):
        self.calls.append(("fetch", url))
        if url in self.errors:
            raise self.errors[url]
        if url not in self.responses:
            raise MU.NetworkError("sahte katman: bilinmeyen URL %s" % url)
        data = self.responses[url]
        if max_bytes and len(data) > max_bytes:
            raise MU.SizeLimitError("sahte: yanıt çok büyük")
        return data

    def download_to(self, url, dest_path, progress_cb=None, cancel_cb=None,
                    max_bytes=None, timeout=None):
        self.calls.append(("download", url))
        if url in self.download_error:
            raise self.download_error[url]
        data = self.responses.get(url)
        if data is None:
            raise MU.NetworkError("sahte katman: bilinmeyen dosya %s" % url)
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        cut = self.truncate.get(url)
        total = len(data)
        written = 0
        try:
            with open(dest, "wb") as fh:
                step = max(1, total // 4)
                limit = int(total * cut) if cut else total
                for i in range(0, limit, step):
                    if cancel_cb is not None and cancel_cb():
                        raise MU.CancelledError("sahte: iptal")
                    block = data[i:i + step]
                    fh.write(block)
                    written += len(block)
                    if progress_cb is not None:
                        progress_cb(written, total)
                        self.progress_seen.append((written, total))
                    if self.lingering:
                        time.sleep(0.12)
                if cut:
                    raise MU.NetworkError("sahte: bağlantı koptu")
        except MU.UpdateError:
            try:
                dest.unlink()
            except Exception:
                pass
            raise
        return {"processed": written, "total": total,
                "sha256": MU.sha256_file(dest)}


class UpdaterTestBase(unittest.TestCase):
    """Ortak kurulum: geçici depo, sahte ağ, küresel durumun geri yüklenmesi."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="awu_upd_"))
        self.bundled = self.tmp / "classifier5k.json"
        shutil.copy2(BUNDLED, self.bundled)
        self.base = self.tmp / "files"
        self.base.mkdir(parents=True, exist_ok=True)
        self.net = FakeNet()

        # Küresel durumu koru (diğer testleri etkilememek için).
        self._lite_path = LITE.MODEL_PATH
        self._lite_obj = getattr(LITE, "_lite", None)
        self._agent = AB._agent
        MU.set_transport(fetch_bytes=self.net.fetch_bytes,
                         download_to=self.net.download_to)
        MU.set_load_probe(None)
        MU._last_check = {"at": 0, "result": None}
        MU._pending = {"manifest": None, "release": None}
        MU._PROGRESS.clear()
        MU._CANCEL.clear()
        MU._WORKER = None
        MU.configure(self.base, self.bundled, app_version="1.0.0")

    def tearDown(self):
        MU.reset_transport()
        MU.set_load_probe(None)
        MU._WORKER = None
        MU._CANCEL.clear()
        LITE.set_model_path(str(self._lite_path))
        if self._lite_obj is not None:
            LITE._lite = self._lite_obj
        C5.reset()
        AB._agent = self._agent
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- ortak yardımcılar -------------------------------------------------
    def give_release(self, version="5K-1.1.0", artifact=None, manifest=None,
                     tag="v5K-1.1.0", **man_kw):
        artifact = artifact if artifact is not None else synthetic_artifact(version)
        manifest = manifest if manifest is not None else manifest_for(
            artifact, version=version, **man_kw)
        rel = release(manifest, artifact, tag=tag)
        self.net.set(MU.RELEASES_URL, json.dumps([rel]).encode("utf-8"))
        self.net.set(MANIFEST_URL, json.dumps(manifest).encode("utf-8"))
        self.net.set(manifest["artifact"]["url"], artifact)
        return manifest, artifact

    def wait_terminal(self, timeout=15.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            p = MU.current_progress()
            if p.get("state") in ("done", "error", "cancelled"):
                return p
            time.sleep(0.02)
        self.fail("güncelleme akışı zaman aşımına uğradı: %r" % (MU.current_progress(),))


# ---------------------------------------------------------------------------
# Sürüm karşılaştırma + URL güvenliği
# ---------------------------------------------------------------------------

class TestVersionAndUrl(UpdaterTestBase):

    def test_version_compare_numeric(self):
        self.assertEqual(MU.compare_versions("5K-1.0.0", "5K-1.0.0"), 0)
        self.assertEqual(MU.compare_versions("5K-1.0.0", "5K-1.1.0"), -1)
        self.assertEqual(MU.compare_versions("5K-1.10.0", "5K-1.9.0"), 1)
        self.assertEqual(MU.version_parts("v5K-2.3"), [5, 2, 3])
        self.assertEqual(MU.version_parts("bilinmeyen"), [0])

    def test_unsafe_urls_rejected(self):
        for bad in ("http://github.com/%s/%s/x" % (OWNER, REPO),
                    "https://evil.example.com/x.json",
                    "https://github.com/Other/repo/x.json",
                    "https://raw.githubusercontent.com/Other/repo/main/x.json",
                    "https://api.github.com/repos/Other/repo/releases",
                    "ftp://github.com/%s/%s/x" % (OWNER, REPO),
                    "", "   ", None, 123):
            with self.assertRaises(MU.UnsafeUrlError, msg=repr(bad)):
                MU.validate_url(bad)  # type: ignore[arg-type]

    def test_allowed_urls(self):
        self.assertEqual(MU.validate_url(ARTIFACT_URL), ARTIFACT_URL)
        self.assertTrue(MU.validate_url(MU.RELEASES_URL).startswith("https://api.github.com/"))
        self.assertTrue(MU.validate_url(
            "https://objects.githubusercontent.com/github-production-release-asset/x")
            .startswith("https://objects.githubusercontent.com/"))


# ---------------------------------------------------------------------------
# Manifest doğrulama
# ---------------------------------------------------------------------------

class TestManifestValidation(UpdaterTestBase):

    def test_valid_manifest_passes(self):
        art = synthetic_artifact()
        man = manifest_for(art)
        out = MU.validate_manifest(man, release(man, art)["assets"])
        self.assertEqual(out["model_version"], "5K-1.1.0")
        self.assertEqual(out["artifact_size"], len(art))
        self.assertEqual(out["hidden"], 31)
        self.assertEqual(out["tokenizer_version"], "char-vocab-103")

    def test_missing_fields_rejected(self):
        art = synthetic_artifact()
        man = manifest_for(art)
        for key in ("model_version", "architecture", "format", "artifact",
                    "min_app_version", "manifest_version", "model_name"):
            broken = dict(man)
            broken.pop(key)
            with self.assertRaises(MU.InvalidManifestError, msg=key):
                MU.validate_manifest(broken)

    def test_unsupported_format_and_architecture_rejected(self):
        art = synthetic_artifact()
        with self.assertRaises(MU.InvalidManifestError):
            MU.validate_manifest(manifest_for(art, fmt="awugokturk-mcu-5k-lite-v9"))
        with self.assertRaises(MU.InvalidManifestError):
            MU.validate_manifest(manifest_for(art, arch="torch-checkpoint-v2"))

    def test_bad_sha_and_bad_size_rejected(self):
        art = synthetic_artifact()
        with self.assertRaises(MU.InvalidManifestError):
            MU.validate_manifest(manifest_for(art, sha256="kisa"))
        with self.assertRaises(MU.InvalidManifestError):
            MU.validate_manifest(manifest_for(art, size=0))
        with self.assertRaises(MU.InvalidManifestError):
            MU.validate_manifest(manifest_for(art, size=MU.MAX_ARTIFACT_BYTES + 1))

    def test_artifact_not_in_release_assets_rejected(self):
        """"Manifestte bulunmayan/beklenmeyen dosya model olarak çalıştırılmaz."""
        art = synthetic_artifact()
        man = manifest_for(art, name="../kacak.json")
        with self.assertRaises(MU.InvalidManifestError):
            MU.validate_manifest(man)

        # Release'te yayımlanmış varlık adı manifest ile aynı olmak zorunda.
        man2 = manifest_for(art)                     # adı: classifier5k.json
        rel = release(man2, art)
        rel["assets"][1]["name"] = "beklenmeyen.json"
        with self.assertRaises(MU.InvalidManifestError):
            MU.validate_manifest(man2, rel["assets"])

    def test_url_mismatch_with_release_asset_rejected(self):
        art = synthetic_artifact()
        rel = release(manifest_for(art), art)        # varlık adresi: ARTIFACT_URL
        # Aynı sha/boyut, ama başka bir adres bildiren manifest kabul edilmez.
        man2 = manifest_for(art, url=BASE + "/v5K-1.1.0/farkli.json")
        with self.assertRaises(MU.InvalidManifestError):
            MU.validate_manifest(man2, rel["assets"])

    def test_min_app_version_newer_than_app_rejected(self):
        art = synthetic_artifact()
        man = manifest_for(art, min_app="9.9.9")
        with self.assertRaises(MU.InvalidManifestError) as cm:
            MU.validate_manifest(man)
        self.assertEqual(cm.exception.extra.get("kind"), "app_too_old")


# ---------------------------------------------------------------------------
# Model dosyası doğrulama (yapı + fiili yükleme)
# ---------------------------------------------------------------------------

class TestModelFileValidation(UpdaterTestBase):

    def test_bundled_asset_is_valid(self):
        info = MU.probe_model(BUNDLED)
        self.assertTrue(info["ok"])
        self.assertEqual(info["params"], 4893)
        self.assertEqual(info["vocab_size"], 103)
        self.assertEqual(info["hidden"], 31)
        self.assertEqual(len(info["labels"]), 8)

    def test_synthetic_artifact_is_loadable(self):
        p = self.tmp / "yeni.json"
        p.write_bytes(synthetic_artifact())
        info = MU.probe_model(p)
        self.assertTrue(info["ok"])
        self.assertEqual(info["model_version"], "5K-1.1.0")
        self.assertTrue(info["loaded"])

    def test_broken_json_rejected(self):
        p = self.tmp / "bozuk.json"
        p.write_bytes(b"{ bu json degil")
        with self.assertRaises(MU.VerificationError):
            MU.structural_check(p)

    def test_wrong_format_rejected(self):
        p = self.tmp / "yanlis.json"
        d = json.loads(synthetic_artifact().decode("utf-8"))
        d["format"] = "baska-format-v1"
        p.write_text(json.dumps(d), encoding="utf-8")
        with self.assertRaises(MU.VerificationError):
            MU.structural_check(p)

    def test_shape_mismatch_rejected(self):
        p = self.tmp / "sekil.json"
        d = json.loads(synthetic_artifact().decode("utf-8"))
        d["fc_weight"] = d["fc_weight"][:4]                  # eksik satır
        p.write_text(json.dumps(d), encoding="utf-8")
        with self.assertRaises(MU.VerificationError):
            MU.structural_check(p)

    def test_vocab_size_inconsistent_rejected(self):
        p = self.tmp / "vocab.json"
        d = json.loads(synthetic_artifact().decode("utf-8"))
        d["config"]["vocab_size"] = 999
        p.write_text(json.dumps(d), encoding="utf-8")
        with self.assertRaises(MU.VerificationError):
            MU.structural_check(p)

    def test_manifest_inconsistency_rejected(self):
        """Manifestte 8 sınıf yazıp dosyada 8 varsa geçer; 4 derse reddedilir."""
        art = synthetic_artifact()
        p = self.tmp / "a.json"
        p.write_bytes(art)
        ok = MU.structural_check(p, {"labels": 8, "vocab_size": 103, "hidden": 31})
        self.assertTrue(ok["ok"])
        with self.assertRaises(MU.VerificationError):
            MU.structural_check(p, {"labels": 4})

    def test_sha_mismatch_rejected(self):
        art = synthetic_artifact()
        p = self.tmp / "a.json"
        p.write_bytes(art)
        flat = MU.validate_manifest(manifest_for(art, sha256="0" * 64))
        with self.assertRaises(MU.VerificationError):
            MU.probe_model(p, flat)


# ---------------------------------------------------------------------------
# Senaryo 1-2: güncelleme kontrolü
# ---------------------------------------------------------------------------

class TestCheckForUpdate(UpdaterTestBase):

    def test_01_yeni_surum_var(self):
        self.give_release()
        res = MU.check_for_update(force=True)
        self.assertTrue(res["ok"])
        self.assertTrue(res["update_available"])
        self.assertEqual(res["installed_version"], "5K-1.0.0")
        self.assertEqual(res["latest_version"], "5K-1.1.0")
        self.assertEqual(res["size"], len(synthetic_artifact()))
        self.assertIn("sentetik", res["release_notes"])
        self.assertEqual(res["min_app_version"], "1.0.0")
        self.assertEqual(res["architecture"], "lite-json-v1")
        self.assertTrue(res["release"]["tag"])
        # Arayüzde gösterilecek boyut metni hazır gelir.
        self.assertTrue(res["size_h"].endswith(("B", "KB", "MB")))

    def test_02_yeni_surum_yok(self):
        # Sunucudaki sürüm, yüklü sürümle aynı.
        art = synthetic_artifact("5K-1.0.0")
        man = manifest_for(art, version="5K-1.0.0")
        rel = release(man, art, tag="v5K-1.0.0")
        self.net.set(MU.RELEASES_URL, json.dumps([rel]).encode("utf-8"))
        self.net.set(MANIFEST_URL, json.dumps(man).encode("utf-8"))
        res = MU.check_for_update(force=True)
        self.assertTrue(res["ok"])
        self.assertFalse(res["update_available"])
        self.assertEqual(res["reason"], "up_to_date")
        self.assertEqual(res["message"], "Modeliniz güncel.")

    def test_02b_daha_eski_surum_yayinda(self):
        art = synthetic_artifact("5K-0.9.0")
        man = manifest_for(art, version="5K-0.9.0")
        rel = release(man, art, tag="v5K-0.9.0")
        self.net.set(MU.RELEASES_URL, json.dumps([rel]).encode("utf-8"))
        self.net.set(MANIFEST_URL, json.dumps(man).encode("utf-8"))
        res = MU.check_for_update(force=True)
        self.assertFalse(res["update_available"])

    def test_depoda_yayimlanmis_model_yok(self):
        """Gerçek depo durumu: Release var ama model manifesti yok."""
        rel = {"tag_name": "v1.0", "draft": False, "prerelease": False,
               "assets": [{"name": "notes.txt", "browser_download_url":
                           BASE + "/v1.0/notes.txt"}],
               "html_url": "x", "published_at": "2026-01-01T00:00:00Z"}
        self.net.set(MU.RELEASES_URL, json.dumps([rel]).encode("utf-8"))
        res = MU.check_for_update(force=True)
        self.assertTrue(res["ok"])
        self.assertFalse(res["update_available"])
        self.assertEqual(res["reason"], "no_published_model")
        self.assertEqual(res["latest_version"], None)
        self.assertEqual(len(res["problems"]), 1)

    def test_bos_release_listesi(self):
        self.net.set(MU.RELEASES_URL, b"[]")
        res = MU.check_for_update(force=True)
        self.assertTrue(res["ok"])
        self.assertFalse(res["update_available"])
        self.assertEqual(res["reason"], "no_published_model")

    def test_onay_oncesi_surum_atlanir(self):
        art = synthetic_artifact()
        man = manifest_for(art)
        rel = release(man, art)
        rel["prerelease"] = True
        self.net.set(MU.RELEASES_URL, json.dumps([rel]).encode("utf-8"))
        res = MU.check_for_update(force=True)
        self.assertFalse(res["update_available"])

    def test_uyumsuz_surum_uygun_degil(self):
        """min_app_version daha yüksek → sürüm sunulmaz, dürüst gerekçe döner."""
        art = synthetic_artifact()
        man = manifest_for(art, min_app="2.0.0")
        rel = release(man, art)
        self.net.set(MU.RELEASES_URL, json.dumps([rel]).encode("utf-8"))
        self.net.set(MANIFEST_URL, json.dumps(man).encode("utf-8"))
        res = MU.check_for_update(force=True)
        self.assertTrue(res["ok"])
        self.assertFalse(res["update_available"])
        self.assertIn("uygulama", res["problems"][0]["message"])

    def test_gecersiz_manifestli_surum_atlanir(self):
        art = synthetic_artifact()
        man = manifest_for(art, fmt="bozuk-format")
        rel = release(man, art)
        self.net.set(MU.RELEASES_URL, json.dumps([rel]).encode("utf-8"))
        self.net.set(MANIFEST_URL, json.dumps(man).encode("utf-8"))
        res = MU.check_for_update(force=True)
        self.assertFalse(res["update_available"])
        self.assertIn("biçimi", res["problems"][0]["message"])

    def test_iki_surumdan_en_yenisi_secinir(self):
        a1 = synthetic_artifact("5K-1.1.0")
        m1 = manifest_for(a1, version="5K-1.1.0")
        u1 = BASE + "/v5K-1.1.0/awu-model-manifest.json"
        a2 = synthetic_artifact("5K-1.2.0")
        m2 = manifest_for(a2, version="5K-1.2.0",
                          url=BASE + "/v5K-1.2.0/classifier5k.json")
        m2url = BASE + "/v5K-1.2.0/awu-model-manifest.json"
        r1 = release(m1, a1, tag="v5K-1.1.0")
        r2 = release(m2, a2, tag="v5K-1.2.0")
        r2["assets"][0]["browser_download_url"] = m2url
        self.net.set(MU.RELEASES_URL, json.dumps([r1, r2]).encode("utf-8"))
        self.net.set(u1, json.dumps(m1).encode("utf-8"))
        self.net.set(m2url, json.dumps(m2).encode("utf-8"))
        res = MU.check_for_update(force=True)
        self.assertTrue(res["update_available"])
        self.assertEqual(res["latest_version"], "5K-1.2.0")


# ---------------------------------------------------------------------------
# Senaryo 3: ağ yok / API limiti
# ---------------------------------------------------------------------------

class TestNetworkFailures(UpdaterTestBase):

    def test_03_internet_yok(self):
        self.net.errors[MU.RELEASES_URL] = MU.NetworkError("Ağ hatası: URLError")
        res = MU.check_for_update(force=True)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "network")
        self.assertIn("Ağ", res["message"])
        # Kritik: yerel model çalışmaya devam eder.
        r = MU.resolve_active()
        self.assertEqual(r["source"], "bundled")
        self.assertEqual(r["version"], "5K-1.0.0")
        self.assertTrue(Path(r["active_path"]).is_file())

    def test_api_limiti(self):
        self.net.errors[MU.RELEASES_URL] = MU.RateLimitError(
            "GitHub API istek sınırı aşıldı.", reset_at=1790000000)
        res = MU.check_for_update(force=True)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "rate_limit")
        self.assertEqual(res["reset_at"], 1790000000)

    def test_http_404(self):
        self.net.errors[MU.RELEASES_URL] = MU.HttpStatusError("Sunucu hatası (HTTP 404).", status=404)
        res = MU.check_for_update(force=True)
        self.assertEqual(res["error"], "http")
        self.assertEqual(res["status"], 404)

    def test_indirme_sirasinda_ag_kopar(self):
        self.give_release()
        self.net.download_error[ARTIFACT_URL] = MU.NetworkError("sahte: kopma")
        self.assertTrue(MU.check_for_update(force=True)["update_available"])
        self.assertTrue(MU.start_download()["ok"])
        p = self.wait_terminal()
        self.assertEqual(p["state"], "error")
        self.assertEqual(p["error_code"], "network")
        # Model değişmedi ve yarım dosya kalmadı.
        st = MU.load_state()
        self.assertEqual(st["installed_version"], "5K-1.0.0")
        self.assertEqual(st["installed_path"], "")
        self.assertEqual(list((MU.models_dir() / "downloads").glob("*.part")), [])

    def test_http_error_403_limit_gercek_cevirici(self):
        """Gerçek HTTPError çevirisi: 403 + kalan hak 0 → rate_limit."""
        import urllib.error
        from email.message import Message
        hdrs = Message()
        hdrs["X-RateLimit-Remaining"] = "0"
        hdrs["X-RateLimit-Reset"] = "1800000000"
        exc = urllib.error.HTTPError(ARTIFACT_URL, 403, "Forbidden", hdrs, None)
        err = MU._translate_http_error(exc)
        self.assertIsInstance(err, MU.RateLimitError)
        self.assertEqual(err.extra["reset_at"], 1800000000)

        hdrs2 = Message()
        exc2 = urllib.error.HTTPError(ARTIFACT_URL, 500, "Server Error", hdrs2, None)
        err2 = MU._translate_http_error(exc2)
        self.assertIsInstance(err2, MU.HttpStatusError)
        self.assertEqual(err2.status, 500)


# ---------------------------------------------------------------------------
# Senaryo 4-8: indirme, doğrulama, etkinleştirme
# ---------------------------------------------------------------------------

class TestDownloadAndActivate(UpdaterTestBase):

    def test_04_indirme_yarida_kalir(self):
        self.give_release()
        self.net.truncate[ARTIFACT_URL] = 0.5          # %50'de bağlantı kopar
        self.assertTrue(MU.check_for_update(force=True)["update_available"])
        MU.start_download()
        p = self.wait_terminal()
        self.assertEqual(p["state"], "error")
        st = MU.load_state()
        self.assertEqual(st["installed_version"], "5K-1.0.0")
        self.assertEqual(list((MU.models_dir() / "downloads").glob("*.part")), [])

    def test_05_sha256_uyusmaz(self):
        art = synthetic_artifact()
        man = manifest_for(art, sha256="f" * 64)
        self.give_release(artifact=art, manifest=man)
        self.assertTrue(MU.check_for_update(force=True)["update_available"])
        MU.start_download()
        p = self.wait_terminal()
        self.assertEqual(p["state"], "error")
        self.assertEqual(p["error_code"], "verification")
        self.assertIn("SHA-256", p["message"])
        self.assertEqual(MU.load_state()["installed_version"], "5K-1.0.0")

    def test_05b_indirilen_boyut_uyusmaz(self):
        art = synthetic_artifact()
        man = manifest_for(art, size=len(art) + 1000)   # yanlış boyut
        self.give_release(artifact=art, manifest=man)
        MU.check_for_update(force=True)
        MU.start_download()
        p = self.wait_terminal()
        self.assertEqual(p["state"], "error")
        self.assertEqual(MU.load_state()["installed_version"], "5K-1.0.0")

    def test_06_bicim_uyumsuz_dosya(self):
        """Manifest doğru ama içerik başka bir biçimde → etkinleşmez."""
        art = synthetic_artifact()
        broken = json.loads(art.decode("utf-8"))
        broken["format"] = "torch-baseline-v1"
        broken_bytes = json.dumps(broken).encode("utf-8")
        man = manifest_for(broken_bytes)                 # sha/boyut bu dosyaya göre
        self.give_release(artifact=broken_bytes, manifest=man)
        MU.check_for_update(force=True)
        MU.start_download()
        p = self.wait_terminal()
        self.assertEqual(p["state"], "error")
        self.assertEqual(p["error_code"], "verification")
        self.assertEqual(MU.load_state()["installed_version"], "5K-1.0.0")

    def test_07_disk_alanı_yetersiz(self):
        self.give_release()
        MU.check_for_update(force=True)
        orig = MU.free_bytes
        try:
            MU.free_bytes = lambda path: 1024          # ~1 KB boş
            MU.start_download()
            p = self.wait_terminal()
        finally:
            MU.free_bytes = orig
        self.assertEqual(p["state"], "error")
        self.assertEqual(p["error_code"], "disk")
        self.assertIn("disk", p["message"].lower())
        self.assertFalse(self.net.calls and any(c[0] == "download" for c in self.net.calls))
        self.assertEqual(MU.load_state()["installed_version"], "5K-1.0.0")

    def test_08_yeni_model_yuklenemez_geri_donulur(self):
        """SHA doğru, yapı doğru; ancak yükleme başarısız → otomatik geri dönüş."""
        self.give_release()
        MU.check_for_update(force=True)
        calls = {"n": 0}

        def failing_probe(path):
            calls["n"] += 1
            raise MU.VerificationError("Model belleğe yüklenemedi (sahte arıza).")

        MU.set_load_probe(failing_probe)
        MU.start_download()
        p = self.wait_terminal()
        self.assertEqual(p["state"], "error")
        self.assertTrue(p["rolled_back"])
        self.assertIn("önceki çalışan modele dönüldü", p["message"])
        self.assertGreaterEqual(calls["n"], 1)

        st = MU.load_state()
        self.assertEqual(st["installed_version"], "5K-1.0.0")
        self.assertEqual(st["installed_path"], "")
        self.assertTrue(st["backup_path"])                 # yedek korundu
        r = MU.resolve_active()
        self.assertEqual(r["version"], "5K-1.0.0")
        # Etkinleştirme yarımları temizlendi.
        self.assertEqual(list((MU.models_dir() / "downloads").glob("*.part")), [])

    def test_basarili_indirme_ve_yukseltme(self):
        man, art = self.give_release()
        chk = MU.check_for_update(force=True)
        self.assertTrue(chk["update_available"])

        activated = {}
        MU.start_download(on_activated=lambda info: activated.update(info))
        p = self.wait_terminal()
        self.assertEqual(p["state"], "done", p)
        self.assertEqual(p["active_version"], "5K-1.1.0")
        self.assertEqual(p["active_source"], "updated")
        self.assertEqual(p["percent"], 100)
        self.assertIn("yükseltildi", p["message"])

        # İndirme gerçekten dosyaya yazıldı ve SHA tutuyor.
        st = MU.load_state()
        self.assertEqual(st["installed_version"], "5K-1.1.0")
        self.assertTrue(Path(st["installed_path"]).is_file())
        self.assertEqual(MU.sha256_file(st["installed_path"]),
                         man["artifact"]["sha256"])
        self.assertEqual(activated.get("active_version"), "5K-1.1.0")
        self.assertEqual(st["backup_version"], "5K-1.0.0")
        self.assertTrue(st["backup_path"])

    def test_ilerleme_bildirimi_ve_iptal(self):
        """İndirme sırasında iptal: durum 'cancelled', model değişmez."""
        self.give_release()
        MU.check_for_update(force=True)
        self.net.lingering = True                     # bloklar arası bekleme
        ok = MU.start_download()
        self.assertTrue(ok["ok"])
        # İlerleme gerçekten bildiriliyor mu?
        deadline = time.time() + 5
        while time.time() < deadline and not self.net.progress_seen:
            time.sleep(0.01)
        self.assertTrue(self.net.progress_seen, "ilerleme bildirimi gelmedi")
        while time.time() < deadline and not MU.is_running():
            time.sleep(0.01)
        res = MU.cancel()
        self.assertTrue(res["ok"], res)
        p = self.wait_terminal()
        self.assertEqual(p["state"], "cancelled")
        self.assertEqual(MU.load_state()["installed_version"], "5K-1.0.0")
        self.assertEqual(list((MU.models_dir() / "downloads").glob("*.part")), [])

    def test_iptal_edilecek_is_yoksa_durust_yanit(self):
        res = MU.cancel()
        self.assertFalse(res["ok"])
        self.assertIn("yok", res["message"].lower())

    def test_onaysiz_indirme_yok(self):
        """Kontrol yapılmadan indirme başlatılamaz (kullanıcı onayı şart)."""
        self.give_release()
        res = MU.start_download()
        self.assertFalse(res["ok"])
        self.assertIn("kontrol", res["message"])
        self.assertFalse(any(c[0] == "download" for c in self.net.calls))


# ---------------------------------------------------------------------------
# Senaryo 9-10: geri dönme + yeniden başlatma
# ---------------------------------------------------------------------------

class TestRollbackAndRestart(UpdaterTestBase):

    def _upgrade(self):
        man, art = self.give_release()
        MU.check_for_update(force=True)
        MU.start_download()
        p = self.wait_terminal()
        self.assertEqual(p["state"], "done", p)
        return man

    def test_09_onceki_modele_geri_donme(self):
        self._upgrade()
        self.assertEqual(MU.status()["installed_version"], "5K-1.1.0")
        self.assertTrue(MU.status()["can_rollback"])

        res = MU.rollback()
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["active_version"], "5K-1.0.0")
        st = MU.load_state()
        self.assertEqual(st["installed_version"], "5K-1.0.0")
        self.assertEqual(st["installed_path"], "")
        self.assertFalse(st["backup_path"])
        self.assertEqual(MU.resolve_active()["source"], "bundled")

    def test_geri_donulecek_yedek_yoksa_durust_hata(self):
        res = MU.rollback()
        self.assertFalse(res["ok"])
        self.assertIn("yedek", res["message"])

    def test_10_yeniden_baslatmada_dogru_model(self):
        man = self._upgrade()
        updated_path = MU.load_state()["installed_path"]
        # Yeniden başlatma: configure() yeniden çağrılır (bellek içi durum sıfır).
        MU._PROGRESS.clear()
        info = MU.configure(self.base, self.bundled, app_version="1.0.0")
        self.assertEqual(info["active_version"], "5K-1.1.0")
        self.assertEqual(info["source"], "updated")
        self.assertEqual(info["active_path"], updated_path)
        self.assertEqual(MU.sha256_file(info["active_path"]), man["artifact"]["sha256"])

    def test_10b_bozuk_guncelleme_paket_ic_baslangica_doner(self):
        self._upgrade()
        path = Path(MU.load_state()["installed_path"])
        path.write_bytes(b"bozulmus")                 # dosya bozuldu
        MU._PROGRESS.clear()
        info = MU.configure(self.base, self.bundled, app_version="1.0.0")
        self.assertEqual(info["source"], "bundled_fallback")
        self.assertEqual(info["active_version"], "5K-1.0.0")
        self.assertEqual(info["active_path"], str(self.bundled))
        # Durum düzeltildi.
        self.assertEqual(MU.load_state()["installed_path"], "")

    def test_10c_yarim_part_dosyasi_aktif_edilmez(self):
        self._upgrade()
        dl = MU.models_dir() / "downloads"
        dl.mkdir(parents=True, exist_ok=True)
        (dl / "classifier5k.json.part").write_bytes(b"yarim")
        info = MU.configure(self.base, self.bundled, app_version="1.0.0")
        self.assertEqual(info["active_version"], "5K-1.1.0")   # etkilenmedi
        self.assertEqual(list(dl.glob("*.part")), [])          # temizlendi

    def test_10d_bekleyen_etkinlestirme_yarim_sayilir(self):
        st = MU.load_state()
        st["pending"] = {"version": "5K-9.9.9", "path": "/yok/x.json", "at": 1}
        MU.save_state(st)
        info = MU.configure(self.base, self.bundled, app_version="1.0.0")
        self.assertEqual(info["active_version"], "5K-1.0.0")
        self.assertIsNone(MU.load_state()["pending"])

    def test_durum_dosyasi_atomik_yazilir(self):
        MU.save_state({"state_version": 1, "installed_version": "5K-1.0.0"})
        p = MU.state_path()
        self.assertTrue(p.is_file())
        # Yarım (.tmp) dosya kalmamalı.
        self.assertFalse(p.with_suffix(p.suffix + ".tmp").exists())
        self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["installed_version"],
                         "5K-1.0.0")

    def test_durum_dosyasi_bozuksa_guvenli_varsayilan(self):
        MU.state_path().write_text("{ bozuk", encoding="utf-8")
        st = MU.load_state()
        self.assertEqual(st["installed_version"], MU.bundled_version())
        self.assertEqual(st["installed_path"], "")


# ---------------------------------------------------------------------------
# Otomatik kontrol politikası + arayüz durumu
# ---------------------------------------------------------------------------

class TestAutoCheckPolicy(UpdaterTestBase):

    def test_ilk_calistirmada_kontrol_zamanı_gelir(self):
        self.assertTrue(MU.auto_check_due())

    def test_24_saat_gecmeden_tekrar_kontrol_edilmez(self):
        MU.check_for_update(force=True)          # -> << veri yok >> ama zaman damgası yazılır
        self.assertFalse(MU.auto_check_due())
        self.assertTrue(MU.auto_check_due(now=int(time.time()) + MU.CHECK_INTERVAL_SECONDS + 1))

    def test_onbellek_ag_istegi_tekrarlanmaz(self):
        self.give_release()
        MU.check_for_update(force=True)
        n = len(self.net.calls)
        res = MU.check_for_update(force=False)          # önbellekten
        self.assertTrue(res.get("cached"))
        self.assertEqual(len(self.net.calls), n)        # yeni ağ isteği yok

    def test_otomatik_kontrol_kapatilabilir(self):
        MU.set_auto_check(False)
        self.assertFalse(MU.auto_check_due())
        self.assertFalse(MU.status()["auto_check"])
        MU.set_auto_check(True)
        self.assertTrue(MU.status()["auto_check"])

    def test_otomatik_kontrol_indirme_baslatmaz(self):
        self.give_release()
        MU.check_for_update(force=True)
        self.assertFalse(any(c[0] == "download" for c in self.net.calls))

    def test_status_ozeti_arayuz_icin_tam(self):
        s = MU.status()
        for key in ("installed_version", "bundled_version", "active_path",
                    "active_version", "source", "can_rollback", "auto_check",
                    "last_check_at", "history", "app_version", "repo"):
            self.assertIn(key, s)
        self.assertEqual(s["bundled_version"], "5K-1.0.0")
        self.assertEqual(s["active_version"], "5K-1.0.0")


# ---------------------------------------------------------------------------
# Mevcut davranışın bozulmadığını kanıtlayan regresyon testleri
# ---------------------------------------------------------------------------

class TestNoRegression(UpdaterTestBase):

    def test_5k_params_degismedi(self):
        c = LITE.LiteClassifier(path=str(BUNDLED))
        self.assertTrue(c.available)
        self.assertEqual(c.param_count(), 4893)
        r = c.predict("Arduino Uno LED blink")
        self.assertTrue(r.available)
        self.assertIn(r.label, c.labels)

    def test_paket_ici_agirliklar_degismedi(self):
        """Model ağırlıkları/dosya içeriği bu çalışmada değiştirilmedi."""
        import hashlib
        self.assertEqual(
            hashlib.sha256(BUNDLED.read_bytes()).hexdigest(),
            "7e4346913c2aae4891495b6695d67d29e2eab3e8caa564d77b06e1be7990abc6")

    def test_bridge_app_info_calisir(self):
        AB.set_model_path(str(BUNDLED))
        info = json.loads(AB.app_info())
        self.assertEqual(info["app_name"], "AwuGöktürk")
        self.assertEqual(info["model_name"], "AwuGöktürk-Microcontroller:5K")
        self.assertEqual(info["slogan"], "NO SAY CAVAS")

    def test_sohbet_ve_kod_uretimi_bozulmadi(self):
        AB.set_model_path(str(BUNDLED))
        rep = json.loads(AB.handle("Arduino Uno pin 7 LED 5 saniyede bir blink"))
        self.assertTrue(rep.get("code"), "kod üretimi bozuldu")
        self.assertIn("INTERVAL_MS", rep["code"])


# ---------------------------------------------------------------------------
# Köprü (Kotlin'in çağırdığı JSON API) entegrasyon testleri
# ---------------------------------------------------------------------------

class TestBridgeIntegration(UpdaterTestBase):
    """Kotlin'in kullandığı birebir JSON fonksiyonlarını doğrular."""

    def test_configure_models_paket_ici_modeli_yukler(self):
        info = json.loads(AB.configure_models(str(self.base), str(self.bundled)))
        self.assertTrue(info["ok"])
        self.assertEqual(info["active_version"], "5K-1.0.0")
        self.assertEqual(info["source"], "bundled")
        self.assertTrue(Path(info["loaded_path"]).is_file())
        # Sınıflandırıcı gerçekten yüklendi.
        st = json.loads(AB.classifier_status())
        self.assertTrue(st["available"])
        self.assertEqual(st["params"], 4893)

    def test_update_status_json(self):
        AB.configure_models(str(self.base), str(self.bundled))
        s = json.loads(AB.update_status())
        for key in ("installed_version", "bundled_version", "can_rollback",
                    "auto_check", "progress", "running", "repo"):
            self.assertIn(key, s)
        self.assertEqual(s["installed_version"], "5K-1.0.0")
        self.assertEqual(s["progress"]["state"], "idle")

    def test_update_check_ve_indirme_kopru_uzerinden(self):
        AB.configure_models(str(self.base), str(self.bundled))
        self.give_release()
        chk = json.loads(AB.update_check(True))
        self.assertTrue(chk["update_available"])
        self.assertEqual(chk["latest_version"], "5K-1.1.0")

        self.assertTrue(json.loads(AB.update_download_start())["ok"])
        p = self.wait_terminal()
        self.assertEqual(p["state"], "done", p)

        # Köprü, yeni modeli gerçekten yükledi mi?
        st = json.loads(AB.classifier_status())
        self.assertTrue(st["available"])
        s = json.loads(AB.update_status())
        self.assertEqual(s["installed_version"], "5K-1.1.0")
        self.assertEqual(s["active_version"], "5K-1.1.0")
        self.assertEqual(s["source"], "updated")

        # Sohbet/kod üretimi hâlâ çalışıyor (güncelleme sonrası regresyon yok).
        rep = json.loads(AB.handle("Arduino Uno pin 7 LED blink"))
        self.assertTrue(rep.get("code"))

    def test_update_rollback_kopru_uzerinden(self):
        AB.configure_models(str(self.base), str(self.bundled))
        self.give_release()
        AB.update_check(True)
        AB.update_download_start()
        self.assertEqual(self.wait_terminal()["state"], "done")

        res = json.loads(AB.update_rollback())
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["active_version"], "5K-1.0.0")
        self.assertEqual(json.loads(AB.update_status())["installed_version"], "5K-1.0.0")
        self.assertTrue(json.loads(AB.classifier_status())["available"])

    def test_update_set_auto_kopru(self):
        AB.configure_models(str(self.base), str(self.bundled))
        r = json.loads(AB.update_set_auto(False))
        self.assertFalse(r["auto_check"])
        self.assertFalse(json.loads(AB.update_status())["auto_check"])
        r = json.loads(AB.update_set_auto(True))
        self.assertTrue(r["auto_check"])

    def test_update_cancel_kopru(self):
        AB.configure_models(str(self.base), str(self.bundled))
        res = json.loads(AB.update_cancel())
        self.assertFalse(res["ok"])

    def test_app_info_degismedi(self):
        AB.configure_models(str(self.base), str(self.bundled))
        info = json.loads(AB.app_info())
        self.assertEqual(info["app_name"], "AwuGöktürk")
        self.assertEqual(info["slogan"], "NO SAY CAVAS")
        self.assertEqual(info["version"], "1.0.0")


# ---------------------------------------------------------------------------
# Yayımlama aracı ↔ güncelleme motoru uçtan uca (manifest üretimi tüketilebilir mi?)
# ---------------------------------------------------------------------------

class TestPublishPipeline(UpdaterTestBase):
    """`tools/make_model_manifest.py` çıktısı motora gerçekten yedirilebiliyor mu?"""

    def test_uretilen_manifest_ve_dosya_uygulamayla_uyumlu(self):
        import sys
        sys.path.insert(0, str(_ROOT))
        from tools.make_model_manifest import build as build_manifest

        art_path = self.tmp / "yayin" / "classifier5k.json"
        art_path.parent.mkdir(parents=True, exist_ok=True)
        art_path.write_bytes(synthetic_artifact("5K-1.1.0"))
        url = BASE + "/v5K-1.1.0/classifier5k.json"
        out = self.tmp / "awu-model-manifest.json"
        man = build_manifest(art_path, "5K-1.1.0", url, "Yayın testi", "1.0.0",
                             out, "AwuGöktürk-Microcontroller:5K", "classifier5k.json")
        self.assertTrue(out.is_file())
        self.assertEqual(man["artifact"]["sha256"], MU.sha256_file(art_path))
        self.assertEqual(man["tokenizer_version"], "char-vocab-103")
        self.assertEqual(man["format"], "awugokturk-mcu-5k-lite-v1")

        # Bu manifest + dosya ile gerçek güncelleme akışı çalışıyor mu?
        rel = release(man, art_path.read_bytes(), tag="v5K-1.1.0")
        self.net.set(MU.RELEASES_URL, json.dumps([rel]).encode("utf-8"))
        self.net.set(MANIFEST_URL, out.read_bytes())
        self.net.set(url, art_path.read_bytes())
        chk = MU.check_for_update(force=True)
        self.assertTrue(chk["update_available"], chk)
        MU.start_download()
        p = self.wait_terminal()
        self.assertEqual(p["state"], "done", p)
        self.assertEqual(MU.status()["installed_version"], "5K-1.1.0")

    def test_bozuk_dosya_icin_manifest_uretilemez(self):
        import sys
        sys.path.insert(0, str(_ROOT))
        from tools.make_model_manifest import build as build_manifest

        bad = self.tmp / "bozuk.json"
        bad.write_bytes(b'{"format": "baska"}')
        with self.assertRaises(MU.VerificationError):
            build_manifest(bad, "5K-9.9.9", BASE + "/v5K-9.9.9/bozuk.json", "",
                           "1.0.0", self.tmp / "m.json",
                           "AwuGöktürk-Microcontroller:5K", "bozuk.json")


# ---------------------------------------------------------------------------
# Canlı (opt-in) test: gerçek GitHub API + izin listesi + gerçek hata yolları
# ---------------------------------------------------------------------------

@unittest.skipUnless(os.environ.get("AWU_LIVE_UPDATE_TEST") == "1",
                     "canlı ağ testi: AWU_LIVE_UPDATE_TEST=1 ile çalıştırın")
class TestLiveGitHub(unittest.TestCase):

    def test_canli_kontrol_guvenli_sonuc_dondurur(self):
        MU.reset_transport()
        with tempfile.TemporaryDirectory(prefix="awu_live_") as td:
            b = Path(td) / "classifier5k.json"
            shutil.copy2(BUNDLED, b)
            MU.configure(td, b, app_version="1.0.0")
            MU._last_check = {"at": 0, "result": None}
            res = MU.check_for_update(force=True)
            self.assertIn("ok", res)
            # Gerçek durum: depoda yayımlanmış model yok → dürüst "yok" yanıtı.
            if res.get("ok"):
                self.assertFalse(res["update_available"])
                self.assertIn(res["reason"], ("no_published_model", "up_to_date"))
            else:
                self.assertIn(res["error"], ("network", "rate_limit", "http"))
            print("\n[canlı] kontrol sonucu:", json.dumps(res, ensure_ascii=False)[:400])


if __name__ == "__main__":
    unittest.main(verbosity=2)
