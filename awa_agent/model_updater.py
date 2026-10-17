"""AwuGöktürk-5K — model güncelleme motoru (kontrol + indirme + doğrulama + atomik etkinleştirme).

NEDEN PYTHON: Bu projede iş mantığı `awa_agent/` içindedir; Kotlin yalnızca arayüz
ve JSON köprüsüdür. Güncelleme kararı, manifest doğrulaması, SHA-256 denetimi,
yedekleme/geri dönme ve durum kalıcılığı da bu kurala uyar. Böylece tüm senaryolar
ana makinede, **ağ ve torch gerekmeden** (sahte taşıma katmanıyla) test edilebilir.

KAYNAK: GitHub Releases API — `Awulokune/AwuGokturk-Android`.
Her model sürümü bir Release'tir; Release'te iki varlık (asset) bulunur:

    1) `awu-model-manifest.json`  → sürüm manifesti (aşağıdaki şema)
    2) manifest'in `artifact.name` alanında bildirilen ağırlık dosyası

Manifest ÖRNEĞİ (ayrıntı: `model/manifest.schema.md`):

    {
      "manifest_version": 1,
      "model_name": "AwuGöktürk-Microcontroller:5K",
      "model_version": "5K-1.1.0",
      "architecture": "lite-json-v1",
      "format": "awugokturk-mcu-5k-lite-v1",
      "tokenizer_version": "char-vocab-103",
      "vocab_size": 103, "labels": 8, "emb": 8, "hidden": 31,
      "artifact": {
        "name": "classifier5k.json",
        "url": "https://github.com/Awulokune/AwuGokturk-Android/releases/download/v5K-1.1.0/classifier5k.json",
        "size": 99663,
        "sha256": "<64 hex>"
      },
      "min_app_version": "1.0.0",
      "release_notes": "…"
    }

GÜVENLİK ÖZETİ (bkz. `docs`: REPORT.md §11)
  * Yalnızca **HTTPS** ve izin verilen ana bilgisayarlar + sabit depo yolu.
  * Yönlendirmeler adım adım doğrulanır (izin listesi dışına çıkılamaz).
  * Boyut üst sınırı + disk alanı ön kontrolü.
  * Manifest ile indirilen dosya tutarlı olmalı (ad, boyut, SHA-256, mimari/biçim,
    tokenizer/vocab). Manifestte bildirilmeyen dosya model olarak çalıştırılmaz.
  * Yeni model, doğrulanıp **fiilen yüklenebildiği** kanıtlandıktan sonra etkinleşir;
    aksi hâlde **önceki çalışan modele otomatik dönülür**.
  * Yarım inen dosya (`*.part`) asla etkinleştirilmez; uygulama indirme sırasında
    kapanırsa durum dosyası değişmediği için eski model çalışmaya devam eder.
  * Token/parola/erişim anahtarı **gömülmez**; kimlik doğrulaması istenmez
    (anonim GitHub API; 60 istek/saat).

DÜRÜSTLÜK NOTU: Bu modül yalnızca yayımlanmış gerçek Release'lerden indirir.
Yayımlanmamış sürüm veya var olmayan bağlantı üretmez. Depoda Release yoksa
`reason="no_published_model"` döner.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

GITHUB_OWNER = "Awulokune"
GITHUB_REPO = "AwuGokturk-Android"

API_BASE = "https://api.github.com"
RELEASES_URL = "{api}/repos/{owner}/{repo}/releases?per_page=30".format(
    api=API_BASE, owner=GITHUB_OWNER, repo=GITHUB_REPO)

#: İndirme yalnızca bu ana bilgisayarlardan yapılabilir.
ALLOWED_HOSTS = frozenset({
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "raw.githubusercontent.com",
    "codeload.github.com",
})

#: `github.com` ve ham içerik için zorunlu depo yolu ön eki.
ALLOWED_REPO_PATH = "/{}/{}".format(GITHUB_OWNER, GITHUB_REPO)
ALLOWED_API_PATH = "/repos/{}/{}".format(GITHUB_OWNER, GITHUB_REPO)

MANIFEST_ASSET_NAME = "awu-model-manifest.json"

#: Desteklenen model mimarisi / dosya biçimi. Bunların dışındaki bir sürüm
#: "uyumlu değil" sayılır ve **indirilmez**.
SUPPORTED_ARCHITECTURES = frozenset({"lite-json-v1"})
SUPPORTED_FORMATS = frozenset({"awugokturk-mcu-5k-lite-v1"})
MANIFEST_VERSION = 1

#: APK ile birlikte gelen (paket içi) modelin sürümü.
BUNDLED_MODEL_VERSION = "5K-1.0.0"
APP_VERSION_FALLBACK = "1.0.0"

#: 5K modeli ~100 KB'dır. Sınır, kötü niyetli/yanlış dosyaların bellek/disk
#: tüketmesini engellemek için cömert ama katı biçimde seçildi.
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024          # 8 MiB
MAX_MANIFEST_BYTES = 256 * 1024               # 256 KiB
MAX_RELEASES_BYTES = 2 * 1024 * 1024          # 2 MiB
DISK_MARGIN_BYTES = 8 * 1024 * 1024           # ek güvenlik payı

CHECK_INTERVAL_SECONDS = 24 * 60 * 60         # otomatik kontrol aralığı (24 saat)
METADATA_TIMEOUT = 20.0
DOWNLOAD_TIMEOUT = 30.0
CHUNK_BYTES = 64 * 1024
MAX_REDIRECTS = 5

#: Ağ isteğinde kullanılan kimlik (GitHub politikası gereği UA zorunlu).
USER_AGENT = ("AwuGokturk-Android-Android/{v} "
              "(+https://github.com/{o}/{r})").format(
    v=APP_VERSION_FALLBACK, o=GITHUB_OWNER, r=GITHUB_REPO)

_STATUS_OK = "ok"


# ---------------------------------------------------------------------------
# Hatalar
# ---------------------------------------------------------------------------

class UpdateError(Exception):
    """Güncelleme akışındaki tüm hataların ortak atası."""

    code = "error"

    def __init__(self, message: str = "", **extra):
        super().__init__(message)
        self.message = message
        self.extra = extra


class UnsafeUrlError(UpdateError):
    code = "unsafe_url"


class NetworkError(UpdateError):
    code = "network"


class RateLimitError(UpdateError):
    code = "rate_limit"


class HttpStatusError(UpdateError):
    code = "http"

    @property
    def status(self) -> int:
        return int(self.extra.get("status", 0))


class SizeLimitError(UpdateError):
    code = "size_limit"


class DiskSpaceError(UpdateError):
    code = "disk"


class CancelledError(UpdateError):
    code = "cancelled"


class VerificationError(UpdateError):
    code = "verification"


class InvalidManifestError(UpdateError):
    code = "invalid_manifest"


class StateError(UpdateError):
    code = "state"


# ---------------------------------------------------------------------------
# Sürüm karşılaştırma
# ---------------------------------------------------------------------------

def version_parts(value: str) -> List[int]:
    """'5K-1.10.2' → [5, 10, 2] (sayısal parçalar; yoksa [0])."""
    return [int(x) for x in re.findall(r"\d+", str(value))] or [0]


def compare_versions(a: str, b: str) -> int:
    """a < b → -1, a == b → 0, a > b → 1 (sayısal parça karşılaştırması)."""
    pa, pb = version_parts(a), version_parts(b)
    n = max(len(pa), len(pb))
    pa = pa + [0] * (n - len(pa))
    pb = pb + [0] * (n - len(pb))
    return (pa > pb) - (pa < pb)


# ---------------------------------------------------------------------------
# URL güvenliği
# ---------------------------------------------------------------------------

def validate_url(url: str) -> str:
    """URL'yi doğrular; güvensizse `UnsafeUrlError` yükseltir.

    Kurallar: yalnızca https, izin verilen ana bilgisayar, sabit depo yolu,
    sorgu dizesi yok (GitHub indirme bağlantıları sorgu kullanmaz).
    """
    if not url or not isinstance(url, str):
        raise UnsafeUrlError("Boş bağlantı.")
    p = urllib.parse.urlsplit(url.strip())
    if p.scheme != "https":
        raise UnsafeUrlError("Yalnızca HTTPS bağlantılarına izin verilir (şema: %r)." % p.scheme)
    host = (p.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise UnsafeUrlError("İzin verilmeyen ana bilgisayar: %s" % (host or "?"))
    if host == "api.github.com":
        if not p.path.startswith(ALLOWED_API_PATH):
            raise UnsafeUrlError("İzin verilmeyen API yolu: %s" % p.path)
    elif host in ("github.com", "raw.githubusercontent.com", "codeload.github.com"):
        if not p.path.startswith(ALLOWED_REPO_PATH):
            raise UnsafeUrlError("İzin verilmeyen depo yolu: %s" % p.path)
    return url.strip()


class _AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Her yönlendirme adımını izin listesine karşı doğrular."""

    def __init__(self):
        self._hops = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self._hops += 1
        if self._hops > MAX_REDIRECTS:
            raise UnsafeUrlError("Çok fazla yönlendirme (%d)." % self._hops)
        validate_url(newurl)
        return urllib.request.HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl)


def _opener():
    return urllib.request.build_opener(_AllowlistRedirectHandler())


def _request(url: str, accept: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Cache-Control": "no-cache",
    })


def _translate_http_error(exc: "urllib.error.HTTPError") -> UpdateError:
    status = int(getattr(exc, "code", 0) or 0)
    headers = getattr(exc, "headers", None)
    remaining = headers.get("X-RateLimit-Remaining") if headers else None
    if status in (403, 429) and (remaining == "0" or status == 429):
        reset = None
        try:
            reset = int((headers.get("X-RateLimit-Reset") or "").strip())
        except Exception:
            reset = None
        return RateLimitError(
            "GitHub API istek sınırı aşıldı. Sınır yenilenince yeniden deneyin.",
            reset_at=reset)
    return HttpStatusError("Sunucu hatası (HTTP %d)." % status, status=status)


def _translate_network_error(exc: Exception) -> NetworkError:
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return NetworkError("Bağlantı zaman aşımına uğradı.",
                            detail=exc.__class__.__name__)
    return NetworkError("Ağ hatası: sunucuya ulaşılamadı (bağlantı yok veya engellendi).",
                        detail=exc.__class__.__name__)


# ---------------------------------------------------------------------------
# Gerçek taşıma katmanı (urllib) — testler bunu `set_transport` ile değiştirir
# ---------------------------------------------------------------------------

def _default_fetch_bytes(url: str, max_bytes: int = MAX_MANIFEST_BYTES,
                         timeout: float = METADATA_TIMEOUT) -> bytes:
    validate_url(url)
    try:
        with _opener().open(_request(url, "application/vnd.github+json, application/json"),
                            timeout=timeout) as resp:
            data = resp.read(max_bytes + 1)
    except urllib.error.HTTPError as e:                       # URLError'un alt sınıfı
        raise _translate_http_error(e)
    except (urllib.error.URLError, ssl.SSLError, socket.timeout, TimeoutError, OSError) as e:
        raise _translate_network_error(e)
    if len(data) > max_bytes:
        raise SizeLimitError("Sunucu yanıtı beklenenden büyük.", limit=max_bytes)
    return data


def _default_download_to(url: str, dest_path: str,
                         progress_cb=None, cancel_cb=None,
                         max_bytes: int = MAX_ARTIFACT_BYTES,
                         timeout: float = DOWNLOAD_TIMEOUT) -> Dict[str, int]:
    validate_url(url)
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    processed = 0
    sha = hashlib.sha256()
    try:
        with _opener().open(_request(url, "application/octet-stream"), timeout=timeout) as resp:
            try:
                total = int(resp.headers.get("Content-Length") or 0)
            except Exception:
                total = 0
            if total and total > max_bytes:
                raise SizeLimitError("Dosya boyut sınırını aşıyor.",
                                     limit=max_bytes, size=total)
            with open(dest, "wb") as fh:
                while True:
                    if cancel_cb is not None and cancel_cb():
                        raise CancelledError("İndirme iptal edildi.")
                    chunk = resp.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    processed += len(chunk)
                    if processed > max_bytes:
                        raise SizeLimitError("Dosya boyut sınırını aşıyor.", limit=max_bytes)
                    fh.write(chunk)
                    sha.update(chunk)
                    if progress_cb is not None:
                        progress_cb(processed, total)
    except UpdateError:
        _safe_unlink(dest)
        raise
    except urllib.error.HTTPError as e:
        _safe_unlink(dest)
        raise _translate_http_error(e)
    except (urllib.error.URLError, ssl.SSLError, socket.timeout, TimeoutError, OSError) as e:
        _safe_unlink(dest)
        raise _translate_network_error(e)
    except BaseException:
        _safe_unlink(dest)
        raise
    if progress_cb is not None:
        progress_cb(processed, processed if total == 0 else total)
    return {"processed": processed, "total": total, "sha256": sha.hexdigest()}


_TRANSPORT = {"fetch_bytes": _default_fetch_bytes, "download_to": _default_download_to}


def set_transport(fetch_bytes=None, download_to=None) -> None:
    """Test/ileri seviye: ağ katmanını değiştirir (None → varsayılan korunur)."""
    if fetch_bytes is not None:
        _TRANSPORT["fetch_bytes"] = fetch_bytes
    if download_to is not None:
        _TRANSPORT["download_to"] = download_to


def reset_transport() -> None:
    _TRANSPORT["fetch_bytes"] = _default_fetch_bytes
    _TRANSPORT["download_to"] = _default_download_to


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _safe_unlink(path) -> None:
    try:
        Path(path).unlink()
    except Exception:
        pass


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK_BYTES), b""):
            h.update(block)
    return h.hexdigest()


def _is_hex64(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        c in "0123456789abcdefABCDEF" for c in value)


def _safe_asset_name(name) -> bool:
    """Varlık adı yol içermemeli (path traversal koruması)."""
    if not isinstance(name, str) or not name:
        return False
    if name != os.path.basename(name) or name in (".", ".."):
        return False
    return not any(sep in name for sep in ("/", "\\", "\x00"))


def _hd_bytes(n: int) -> str:
    """İnsan okunur boyut (Kotlin tarafı için hazır metin)."""
    try:
        n = float(n)
    except Exception:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024.0 or unit == "GB":
            return ("%.0f %s" if unit == "B" else "%.1f %s") % (n, unit)
        n /= 1024.0
    return "?"


def free_bytes(path) -> int:
    try:
        return int(shutil.disk_usage(str(path)).free)
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# Depolama / durum
# ---------------------------------------------------------------------------

_MODELS_DIRNAME = "awu_models"
_DOWNLOAD_DIRNAME = "downloads"
_STATE_FILENAME = "model_state.json"

_CFG: Dict[str, object] = {
    "base_dir": None,      # type: Optional[Path]
    "bundled_path": None,  # type: Optional[Path]
    "app_version": APP_VERSION_FALLBACK,
}


def configure(base_dir, bundled_path, app_version: Optional[str] = None) -> Dict[str, object]:
    """Depolama köklerini ayarlar ve **etkin modeli** çözer.

    Çağıran (Kotlin köprüsü) dönen `active_path` değerini
    `classifier5k_lite.set_model_path()` ile yükler.

    Ayrıca yarım kalan indirmeleri temizler: `*.part` dosyaları ve
    tamamlanmamış (`pending`) etkinleştirmeler asla aktif sayılmaz.
    """
    base = Path(str(base_dir))
    models = base / _MODELS_DIRNAME
    (models / _DOWNLOAD_DIRNAME).mkdir(parents=True, exist_ok=True)
    _CFG["base_dir"] = base
    _CFG["bundled_path"] = Path(str(bundled_path))
    if app_version:
        _CFG["app_version"] = str(app_version)

    # Yarım kalan indirmeleri temizle (aktif hâle gelmeleri imkânsız).
    for part in (models / _DOWNLOAD_DIRNAME).glob("*.part"):
        _safe_unlink(part)

    state = load_state()
    resolved = resolve_active(state)
    if state.get("pending"):
        # Etkinleştirme tamamlanmadan kesilmiş: kaydı düşür, önceki model geçerli.
        state["pending"] = None
        save_state(state)
    return {
        "ok": True,
        "base_dir": str(base),
        "models_dir": str(models),
        "state_path": str(state_path()),
        "active_path": resolved["active_path"],
        "active_version": resolved["version"],
        "source": resolved["source"],
        "bundled_version": bundled_version(),
        "bundled_sha256": bundled_sha256(),
        "install_dir_writable": os.access(str(models), os.W_OK),
    }


def state_path() -> Path:
    base = _CFG["base_dir"]
    if base is None:
        raise StateError("model_updater.configure() çağrılmadı.")
    return Path(str(base)) / _MODELS_DIRNAME / _STATE_FILENAME


def models_dir() -> Path:
    base = _CFG["base_dir"]
    if base is None:
        raise StateError("model_updater.configure() çağrılmadı.")
    return Path(str(base)) / _MODELS_DIRNAME


def bundled_path() -> Optional[Path]:
    return _CFG["bundled_path"]  # type: ignore[return-value]


def app_version() -> str:
    return str(_CFG.get("app_version") or APP_VERSION_FALLBACK)


def bundled_version() -> str:
    """Paket içi modelin sürümü: dosyada `model_version` varsa o, yoksa sabit."""
    p = bundled_path()
    if p is not None:
        try:
            d = json.loads(Path(str(p)).read_text(encoding="utf-8"))
            v = d.get("model_version")
            if isinstance(v, str) and v.strip():
                return v.strip()
        except Exception:
            pass
    return BUNDLED_MODEL_VERSION


def bundled_sha256() -> str:
    p = bundled_path()
    if p is None:
        return ""
    try:
        return sha256_file(Path(str(p)))
    except Exception:
        return ""


def default_state() -> Dict[str, object]:
    return {
        "state_version": 1,
        "installed_version": bundled_version(),
        "installed_path": "",          # "" → paket içi model
        "installed_sha256": "",
        "source": "bundled",
        "backup_version": "",
        "backup_path": "",
        "pending": None,
        "last_check_at": 0,
        "last_check_result": None,
        "auto_check": True,
        "history": [],
    }


def load_state() -> Dict[str, object]:
    """Durumu okur; bozuksa güvenli varsayılana döner (veri uydurmaz)."""
    try:
        raw = state_path().read_text(encoding="utf-8")
        d = json.loads(raw)
        if not isinstance(d, dict):
            raise ValueError("durum sözlük değil")
    except Exception:
        return default_state()
    st = default_state()
    st.update(d)
    return st


def save_state(state: Dict[str, object]) -> None:
    """Durumu **atomik** yazar (tmp + os.replace): yarım dosya okunmaz."""
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    data = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)


def resolve_active(state: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Etkin modeli çözer: güncellenmiş dosya geçerliyse o, aksi hâlde paket içi.

    Güncellenmiş dosya silinmiş/bozulmuş/SHA'sı tutmuyorsa **sessizce** paket
    içi modele düşülür. Böylece bozuk bir güncelleme asla çalışmaz.
    """
    st = state if state is not None else load_state()
    inst = str(st.get("installed_path") or "")
    ver = str(st.get("installed_version") or bundled_version())
    if inst:
        p = Path(inst)
        if p.is_file() and not inst.endswith(".part"):
            want = str(st.get("installed_sha256") or "")
            if not want or sha256_file(p) == want:
                return {"active_path": str(p), "version": ver, "source": "updated"}
        # Bozuk/eksik güncelleme: paket içi modele dön.
        st["installed_path"] = ""
        st["installed_sha256"] = ""
        st["installed_version"] = bundled_version()
        st["source"] = "bundled"
        try:
            save_state(st)
        except Exception:
            pass
        return {"active_path": str(bundled_path()), "version": bundled_version(),
                "source": "bundled_fallback"}
    return {"active_path": str(bundled_path()), "version": bundled_version(),
            "source": "bundled"}


# ---------------------------------------------------------------------------
# Manifest doğrulama
# ---------------------------------------------------------------------------

_MANIFEST_REQUIRED = ("manifest_version", "model_name", "model_version",
                      "architecture", "format", "artifact", "min_app_version")


def validate_manifest(obj, release_assets: Optional[List[dict]] = None) -> Dict[str, object]:
    """Manifesti doğrular. Hata durumunda `InvalidManifestError` yükseltir.

    `release_assets` verilirse: manifest'in bildirdiği dosya, Release'te
    **gerçekten yayımlanmış** varlıklarla eşleşmek zorundadır. Böylece manifest
    dışı/beklenmeyen dosyalar model olarak çalıştırılamaz.
    """
    if not isinstance(obj, dict):
        raise InvalidManifestError("Manifest bir JSON nesnesi değil.")
    for key in _MANIFEST_REQUIRED:
        if key not in obj:
            raise InvalidManifestError("Manifest alanı eksik: %s" % key)

    try:
        mv = int(obj["manifest_version"])
    except Exception:
        raise InvalidManifestError("manifest_version sayı değil.")
    if mv != MANIFEST_VERSION:
        raise InvalidManifestError("Desteklenmeyen manifest sürümü: %s" % obj["manifest_version"])

    arch = str(obj.get("architecture") or "")
    fmt = str(obj.get("format") or "")
    if arch not in SUPPORTED_ARCHITECTURES:
        raise InvalidManifestError(
            "Uyumsuz model mimarisi: %s (desteklenen: %s)"
            % (arch or "?", ", ".join(sorted(SUPPORTED_ARCHITECTURES))))
    if fmt not in SUPPORTED_FORMATS:
        raise InvalidManifestError(
            "Uyumsuz dosya biçimi: %s (desteklenen: %s)"
            % (fmt or "?", ", ".join(sorted(SUPPORTED_FORMATS))))

    name = str(obj.get("model_name") or "")
    if not name:
        raise InvalidManifestError("model_name boş.")
    ver = str(obj.get("model_version") or "").strip()
    if not ver:
        raise InvalidManifestError("model_version boş.")
    tokenizer = str(obj.get("tokenizer_version") or "").strip()
    if not tokenizer:
        raise InvalidManifestError("tokenizer_version boş.")

    min_app = str(obj.get("min_app_version") or "").strip()
    if not min_app:
        raise InvalidManifestError("min_app_version boş.")
    if compare_versions(min_app, app_version()) > 0:
        raise InvalidManifestError(
            "Bu sürüm daha yeni bir uygulama gerektiriyor (en az %s; yüklü %s)."
            % (min_app, app_version()), kind="app_too_old", min_app_version=min_app)

    art = obj.get("artifact")
    if not isinstance(art, dict):
        raise InvalidManifestError("artifact bir nesne değil.")
    a_name = art.get("name")
    if not _safe_asset_name(a_name):
        raise InvalidManifestError("artifact.name geçersiz: %r" % (a_name,))
    a_url = validate_url(str(art.get("url") or ""))
    try:
        a_size = int(art.get("size"))
    except Exception:
        raise InvalidManifestError("artifact.size sayı değil.")
    if a_size <= 0:
        raise InvalidManifestError("artifact.size pozitif olmalı.")
    if a_size > MAX_ARTIFACT_BYTES:
        raise InvalidManifestError(
            "Dosya boyutu sınırını aşıyor (%s > %s)."
            % (_hd_bytes(a_size), _hd_bytes(MAX_ARTIFACT_BYTES)))
    a_sha = str(art.get("sha256") or "").strip().lower()
    if not _is_hex64(a_sha):
        raise InvalidManifestError("artifact.sha256 64 karakterlik hex olmalı.")

    # Mimari sayıları (dosyayla tutarlılık için sonradan karşılaştırılır).
    for key in ("vocab_size", "labels", "hidden"):
        if key in obj:
            try:
                int(obj[key])
            except Exception:
                raise InvalidManifestError("%s sayı değil." % key)

    if release_assets is not None:
        names = [str(a.get("name") or "") for a in release_assets
                 if isinstance(a, dict)]
        if a_name not in names:
            raise InvalidManifestError(
                "Manifest'te bildirilen dosya Release'te yayımlanmamış: %s" % a_name)
        urls = [str(a.get("browser_download_url") or "") for a in release_assets
                if isinstance(a, dict)]
        matched = False
        for a in release_assets:
            if not isinstance(a, dict):
                continue
            if str(a.get("name") or "") != a_name:
                continue
            bdu = str(a.get("browser_download_url") or "")
            if bdu and validate_url(bdu) == a_url:
                matched = True
        if not matched and urls:
            raise InvalidManifestError(
                "Manifest bağlantısı Release varlık bağlantısıyla uyuşmuyor.")

    return {
        "manifest_version": mv,
        "model_name": name,
        "model_version": ver,
        "architecture": arch,
        "format": fmt,
        "tokenizer_version": tokenizer,
        "vocab_size": int(obj["vocab_size"]) if "vocab_size" in obj else None,
        "labels": int(obj["labels"]) if "labels" in obj else None,
        "emb": int(obj["emb"]) if "emb" in obj else None,
        "hidden": int(obj["hidden"]) if "hidden" in obj else None,
        "artifact_name": str(a_name),
        "artifact_url": a_url,
        "artifact_size": a_size,
        "artifact_sha256": a_sha,
        "min_app_version": min_app,
        "release_notes": str(obj.get("release_notes") or "").strip(),
    }


# ---------------------------------------------------------------------------
# Model dosyası doğrulama (yapısal + fiili yükleme denemesi)
# ---------------------------------------------------------------------------

def structural_check(path, manifest: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Ağırlık JSON'unun yapısını ve manifest tutarlılığını denetler."""
    p = Path(str(path))
    if not p.is_file():
        raise VerificationError("Model dosyası bulunamadı.", detail=str(p))
    size = p.stat().st_size
    if size <= 0:
        raise VerificationError("Model dosyası boş.")
    if size > MAX_ARTIFACT_BYTES:
        raise VerificationError("Model dosyası boyut sınırını aşıyor.")
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise VerificationError("Model dosyası geçerli JSON değil: %s" % e)
    if not isinstance(d, dict):
        raise VerificationError("Model dosyası bir JSON nesnesi değil.")

    fmt = str(d.get("format") or "")
    if fmt not in SUPPORTED_FORMATS:
        raise VerificationError("Uyumsuz model biçimi: %s" % (fmt or "?"))

    required = ("labels", "vocab", "config", "emb", "gru_weight_ih",
                "gru_weight_hh", "gru_bias_ih", "gru_bias_hh",
                "fc_weight", "fc_bias")
    for key in required:
        if key not in d:
            raise VerificationError("Model dosyasında eksik alan: %s" % key)

    labels = d["labels"]
    vocab = d["vocab"]
    cfg = d["config"]
    if not isinstance(labels, list) or len(labels) < 2:
        raise VerificationError("labels listesi geçersiz.")
    if not isinstance(vocab, list) or len(vocab) < 2:
        raise VerificationError("vocab listesi geçersiz.")
    if not isinstance(cfg, dict):
        raise VerificationError("config nesnesi geçersiz.")
    for key in ("vocab_size", "emb", "hidden"):
        if key not in cfg:
            raise VerificationError("config.%s eksik." % key)
    vs, emb, hid = int(cfg["vocab_size"]), int(cfg["emb"]), int(cfg["hidden"])
    if vs != len(vocab):
        raise VerificationError(
            "config.vocab_size (%d) ile vocab uzunluğu (%d) uyuşmuyor." % (vs, len(vocab)))

    def _shape(key, rows, cols):
        m = d[key]
        if not isinstance(m, list) or len(m) != rows:
            raise VerificationError("%s beklenen satır sayısı %d değil." % (key, rows))
        for row in m:
            if not isinstance(row, list) or len(row) != cols:
                raise VerificationError("%s satır genişliği %d değil." % (key, cols))

    _shape("emb", vs, emb)
    _shape("gru_weight_ih", 3 * hid, emb)
    _shape("gru_weight_hh", 3 * hid, hid)
    _shape("fc_weight", len(labels), hid)
    for key, n in (("gru_bias_ih", 3 * hid), ("gru_bias_hh", 3 * hid),
                   ("fc_bias", len(labels))):
        v = d[key]
        if not isinstance(v, list) or len(v) != n:
            raise VerificationError("%s uzunluğu %d değil." % (key, n))

    if manifest:
        want_fmt = manifest.get("format")
        if want_fmt is not None and str(want_fmt) != fmt:
            raise VerificationError("Dosya biçimi manifest ile uyuşmuyor.")
        mn = str(d.get("model_name") or "")
        want_name = manifest.get("model_name")
        if mn and want_name and mn != str(want_name):
            raise VerificationError("Dosya model adı manifest ile uyuşmuyor.")
        for key, actual in (("vocab_size", vs), ("labels", len(labels)),
                            ("emb", emb), ("hidden", hid)):
            want = manifest.get(key)
            if want is not None and int(want) != int(actual):
                raise VerificationError(
                    "Manifest %s=%s, dosya %s." % (key, want, actual))

    params = (vs * emb
              + (3 * hid) * emb
              + (3 * hid) * hid
              + (3 * hid) + (3 * hid)
              + len(labels) * hid
              + len(labels))
    return {
        "ok": True,
        "size": size,
        "format": fmt,
        "model_name": str(d.get("model_name") or ""),
        "model_version": str(d.get("model_version") or ""),
        "vocab_size": vs,
        "emb": emb,
        "hidden": hid,
        "labels": [str(x) for x in labels],
        "params": params,
    }


def _default_load_probe(path) -> Dict[str, object]:
    """Modeli **gerçekten** yükleyip küçük bir çıkarım çalıştırır.

    Bu adım, "yapı doğru ama yüklenemiyor" durumunu yakalar. Küresel
    sınıflandırıcı durumuna dokunmaz (ayrı bir `LiteClassifier` örneği kullanır).
    """
    from .classifier5k_lite import LiteClassifier

    c = LiteClassifier(path=str(path))
    if not getattr(c, "available", False):
        raise VerificationError("Model belleğe yüklenemedi.")
    r = c.predict("pinMode(13, OUTPUT);")
    if not getattr(r, "available", False):
        raise VerificationError("Model yüklendi ancak çıkarım üretemedi.")
    if r.label not in c.labels:
        raise VerificationError("Çıkarım etiketi model etiketleriyle uyuşmuyor.")
    return {
        "ok": True,
        "params": c.param_count(),
        "labels": list(c.labels),
        "sample_label": r.label,
        "sample_probs": len(r.probs or {}),
    }


_LOAD_PROBE: Callable[[object], Dict[str, object]] = _default_load_probe


def set_load_probe(probe) -> None:
    """Test/ileri seviye: yükleme denemesini değiştirir (None → varsayılan)."""
    global _LOAD_PROBE
    _LOAD_PROBE = probe or _default_load_probe


def probe_model(path, manifest: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Yapısal denetim + (varsa) SHA-256 + fiili yükleme denemesi."""
    info = structural_check(path, manifest)
    if manifest:
        want = str(manifest.get("artifact_sha256") or "")
        if want:
            got = sha256_file(path)
            if got.lower() != want.lower():
                raise VerificationError(
                    "SHA-256 uyuşmuyor (beklenen %s…, hesaplanan %s…)"
                    % (want[:12], got[:12]))
        want_size = int(manifest.get("artifact_size") or 0)
        if want_size and int(info["size"]) != want_size:
            raise VerificationError(
                "Dosya boyutu manifest ile uyuşmuyor (%s ≠ %s bayt)."
                % (info["size"], want_size))
    load = _LOAD_PROBE(path)
    info.update({"loaded": True, "load": load})
    return info


# ---------------------------------------------------------------------------
# GitHub Releases kontrolü
# ---------------------------------------------------------------------------

_last_check: Dict[str, object] = {"at": 0, "result": None}
_pending: Dict[str, object] = {"manifest": None, "release": None}


def _release_tag(rel: dict) -> str:
    return str(rel.get("tag_name") or rel.get("name") or "")


def _pick_asset(rel: dict, name: str) -> Optional[dict]:
    for a in rel.get("assets") or []:
        if isinstance(a, dict) and str(a.get("name") or "") == name:
            return a
    return None


def _error_result(exc: UpdateError) -> Dict[str, object]:
    out = {
        "ok": False,
        "error": getattr(exc, "code", "error"),
        "message": str(exc),
        "checked_at": int(time.time()),
    }
    out.update(exc.extra)
    return out


def check_for_update(force: bool = False,
                     releases_url: str = RELEASES_URL) -> Dict[str, object]:
    """Yayımlanmış en yeni **uyumlu** model sürümünü bulur ve karşılaştırır.

    Ağ hatası / API limiti / yayımlanmamış model durumları `ok=False` ya da
    `update_available=False` + açıklama ile döner; sahte sürüm üretilmez.
    """
    now = int(time.time())
    st = load_state()
    installed = str(st.get("installed_version") or bundled_version())

    if not force and _last_check["result"] is not None:
        age = now - int(_last_check["at"] or 0)
        if age < CHECK_INTERVAL_SECONDS:
            cached = dict(_last_check["result"])  # type: ignore[arg-type]
            cached["cached"] = True
            cached["installed_version"] = installed
            return cached

    try:
        raw = _TRANSPORT["fetch_bytes"](releases_url, MAX_RELEASES_BYTES)
        releases = json.loads(raw.decode("utf-8"))
        if not isinstance(releases, list):
            raise InvalidManifestError("Releases yanıtı beklenen biçimde değil.")
    except UpdateError as e:
        res = _error_result(e)
        _record_check(st, res)
        return res
    except Exception as e:
        res = _error_result(NetworkError("Releases listesi okunamadı (%s)."
                                         % e.__class__.__name__))
        _record_check(st, res)
        return res

    candidates = []          # (ver, manifest, release)
    problems = []            # (tag, message)
    for rel in releases:
        if not isinstance(rel, dict):
            continue
        if rel.get("draft"):
            continue
        if rel.get("prerelease"):
            continue
        tag = _release_tag(rel)
        asset = _pick_asset(rel, MANIFEST_ASSET_NAME)
        if asset is None:
            problems.append((tag, "yayımlanmış model manifesti yok"))
            continue
        try:
            murl = validate_url(str(asset.get("browser_download_url") or ""))
            mraw = _TRANSPORT["fetch_bytes"](murl, MAX_MANIFEST_BYTES)
            obj = json.loads(mraw.decode("utf-8"))
            man = validate_manifest(obj, rel.get("assets") or [])
        except UpdateError as e:
            problems.append((tag, str(e)))
            continue
        except Exception as e:
            problems.append((tag, "manifest okunamadı (%s)" % e.__class__.__name__))
            continue
        candidates.append((man["model_version"], man, rel))

    if not candidates:
        res = {
            "ok": True,
            "update_available": False,
            "installed_version": installed,
            "latest_version": None,
            "reason": "no_published_model",
            "message": ("Bu depoda yayımlanmış bir model sürümü bulunamadı. "
                        "Uygulamayla gelen model kullanılmaya devam ediyor."),
            "problems": [{"tag": t, "message": m} for t, m in problems[:5]],
            "checked_at": now,
        }
        _record_check(st, res)
        return res

    candidates.sort(key=lambda c: version_parts(c[0]))
    latest_ver, latest_man, latest_rel = candidates[-1]

    if compare_versions(latest_ver, installed) <= 0:
        res = {
            "ok": True,
            "update_available": False,
            "installed_version": installed,
            "latest_version": latest_ver,
            "reason": "up_to_date",
            "message": "Modeliniz güncel.",
            "release": _release_info(latest_rel),
            "checked_at": now,
        }
        _record_check(st, res)
        return res

    res = {
        "ok": True,
        "update_available": True,
        "installed_version": installed,
        "latest_version": latest_ver,
        "reason": "update_available",
        "message": "%s sürümü yayımlandı." % latest_ver,
        "manifest": latest_man,
        "release": _release_info(latest_rel),
        "size": latest_man["artifact_size"],
        "size_h": _hd_bytes(latest_man["artifact_size"]),
        "release_notes": latest_man["release_notes"],
        "min_app_version": latest_man["min_app_version"],
        "tokenizer_version": latest_man["tokenizer_version"],
        "architecture": latest_man["architecture"],
        "checked_at": now,
    }
    _pending["manifest"] = latest_man
    _pending["release"] = _release_info(latest_rel)
    _record_check(st, res)
    return res


def _release_info(rel: dict) -> Dict[str, object]:
    return {
        "tag": _release_tag(rel),
        "name": str(rel.get("name") or ""),
        "published_at": str(rel.get("published_at") or ""),
        "html_url": str(rel.get("html_url") or ""),
    }


def _record_check(st: Dict[str, object], res: Dict[str, object]) -> None:
    _last_check["at"] = int(res.get("checked_at") or time.time())
    _last_check["result"] = res
    st["last_check_at"] = _last_check["at"]
    st["last_check_result"] = {
        k: res.get(k) for k in ("ok", "error", "message", "update_available",
                                "installed_version", "latest_version", "reason")
    }
    try:
        save_state(st)
    except Exception:
        pass


def last_check() -> Dict[str, object]:
    return dict(_last_check["result"]) if _last_check["result"] else {}


def auto_check_due(now: Optional[int] = None) -> bool:
    """Otomatik kontrol zamanı geldi mi? (açılışta gereksiz istek yapılmaz.)"""
    st = load_state()
    if not st.get("auto_check", True):
        return False
    now = int(now or time.time())
    return (now - int(st.get("last_check_at") or 0)) >= CHECK_INTERVAL_SECONDS


def set_auto_check(enabled: bool) -> Dict[str, object]:
    st = load_state()
    st["auto_check"] = bool(enabled)
    save_state(st)
    return {"ok": True, "auto_check": bool(enabled)}


# ---------------------------------------------------------------------------
# İndirme + etkinleştirme akışı (arka plan iş parçacığı)
# ---------------------------------------------------------------------------

_PROGRESS: Dict[str, object] = {}
_PROGRESS_LOCK = threading.Lock()
_WORKER: Optional[threading.Thread] = None
_CANCEL = threading.Event()


def _set_progress(**kw) -> None:
    with _PROGRESS_LOCK:
        _PROGRESS.update(kw)


def progress() -> Dict[str, object]:
    with _PROGRESS_LOCK:
        return dict(_PROGRESS)


def _idle_progress() -> Dict[str, object]:
    if _CFG["base_dir"] is None:
        return {"state": "unconfigured", "percent": -1, "processed": 0, "total": 0,
                "message": "", "error": "", "error_code": "", "version": "",
                "active_path": "", "active_version": "", "active_source": "",
                "backup_version": "", "can_rollback": False, "rolled_back": False}
    st = load_state()
    resolved = resolve_active(st)
    return {
        "state": "idle",
        "percent": -1,
        "processed": 0,
        "total": 0,
        "processed_h": "",
        "total_h": "",
        "remaining_h": "",
        "message": "",
        "error": "",
        "error_code": "",
        "version": str(st.get("installed_version") or ""),
        "latest_version": ((st.get("last_check_result") or {}) or {}).get("latest_version") or "",
        "rolled_back": False,
        "active_path": resolved.get("active_path", ""),
        "active_version": resolved.get("version", ""),
        "active_source": resolved.get("source", ""),
        "backup_version": str(st.get("backup_version") or ""),
        "can_rollback": bool(st.get("backup_path")),
        "started_at": 0,
        "finished_at": 0,
    }


def current_progress() -> Dict[str, object]:
    """Aktif iş yoksa kalıcı duruma dayalı 'idle' bilgisi döner."""
    if not _PROGRESS:
        return _idle_progress()
    with _PROGRESS_LOCK:
        out = dict(_PROGRESS)
    st = load_state()
    out.setdefault("backup_version", str(st.get("backup_version") or ""))
    out["can_rollback"] = bool(st.get("backup_path"))
    return out


def is_running() -> bool:
    return bool(_WORKER is not None and _WORKER.is_alive())


def cancel() -> Dict[str, object]:
    if not is_running():
        return {"ok": False, "message": "Süren bir indirme yok."}
    _CANCEL.set()
    _set_progress(message="İptal ediliyor…")
    return {"ok": True, "message": "İptal istendi."}


def _history_add(st: Dict[str, object], entry: Dict[str, object]) -> None:
    hist = list(st.get("history") or [])
    hist.append(entry)
    st["history"] = hist[-10:]


def _do_download_and_activate(manifest: Dict[str, object], release: Dict[str, object],
                              on_activated=None) -> None:
    started = int(time.time())
    try:
        size = int(manifest["artifact_size"])
        dl_dir = models_dir() / _DOWNLOAD_DIRNAME
        dl_dir.mkdir(parents=True, exist_ok=True)

        # --- disk alanı ön kontrolü -------------------------------------
        free = free_bytes(dl_dir)
        if free >= 0 and free < size + DISK_MARGIN_BYTES:
            raise DiskSpaceError(
                "Yeterli disk alanı yok (gerekli ≈ %s, boş %s)."
                % (_hd_bytes(size + DISK_MARGIN_BYTES), _hd_bytes(free)),
                required=size + DISK_MARGIN_BYTES, free=free)

        part = dl_dir / (manifest["artifact_name"] + ".part")
        _safe_unlink(part)

        _set_progress(state="downloading", percent=0, processed=0, total=size,
                      processed_h=_hd_bytes(0), total_h=_hd_bytes(size),
                      remaining_h=_hd_bytes(size), message="İndiriliyor…",
                      error="", error_code="", version=manifest["model_version"],
                      started_at=started, finished_at=0, rolled_back=False)

        def _progress_cb(done, total):
            t = total or size
            pct = int(done * 100 / t) if t else -1
            _set_progress(percent=max(0, min(100, pct)), processed=done, total=t,
                          processed_h=_hd_bytes(done), total_h=_hd_bytes(t),
                          remaining_h=_hd_bytes(max(0, t - done)))

        info = _TRANSPORT["download_to"](manifest["artifact_url"], str(part),
                                        _progress_cb, _CANCEL.is_set,
                                        MAX_ARTIFACT_BYTES)
        if info.get("processed") != size:
            raise VerificationError(
                "İndirilen boyut manifest ile uyuşmuyor (%s ≠ %s bayt)."
                % (info.get("processed"), size))

        # --- doğrulama: SHA-256 + yapı + mimari (ucuz, model kurulmaz) --
        _set_progress(state="verifying", percent=100, message="Doğrulanıyor…")
        got = sha256_file(part)
        if got.lower() != str(manifest["artifact_sha256"]).lower():
            raise VerificationError(
                "SHA-256 doğrulaması başarısız (beklenen %s…, hesaplanan %s…)."
                % (str(manifest["artifact_sha256"])[:12], got[:12]))
        structural_check(part, manifest)

        # --- atomik etkinleştirme (fiili yükleme denemesi + geri dönüş) --
        _set_progress(state="applying", message="Etkinleştiriliyor…")
        result = activate(part, manifest, release)
        if not result.get("ok"):
            # Yeni model yüklenemedi; activate() önceki modele döndü.
            _set_progress(state="error", message=result.get("message", ""),
                          error=result.get("error", ""), error_code="load_failed",
                          rolled_back=True, percent=100,
                          active_path=result.get("active_path", ""),
                          active_version=result.get("active_version", ""),
                          active_source="previous",
                          backup_version=result.get("backup_version", ""),
                          finished_at=int(time.time()))
            return

        if on_activated is not None:
            on_activated(result)

        _set_progress(state="done", percent=100, message=result["message"],
                      error="", error_code="", version=result["active_version"],
                      active_path=result["active_path"],
                      active_version=result["active_version"],
                      active_source="updated",
                      backup_version=result.get("backup_version", ""),
                      rollback_reason="",
                      finished_at=int(time.time()))
    except CancelledError as e:
        _set_progress(state="cancelled", message="İndirme iptal edildi.",
                      error=str(e), error_code="cancelled",
                      finished_at=int(time.time()))
    except UpdateError as e:
        _set_progress(state="error", message=str(e), error=str(e),
                      error_code=getattr(e, "code", "error"),
                      rolled_back=False, finished_at=int(time.time()))
    except Exception as e:                                  # beklenmeyen
        _set_progress(state="error", message="Beklenmeyen hata: %s" % e,
                      error="%s: %s" % (e.__class__.__name__, e),
                      error_code="unexpected", finished_at=int(time.time()))
    finally:
        dl = models_dir() / _DOWNLOAD_DIRNAME
        for leftover in dl.glob("*.part"):
            _safe_unlink(leftover)
        _CANCEL.clear()


def start_download(on_activated=None) -> Dict[str, object]:
    """Bekleyen (kontrol edilmiş) sürümü indirir, doğrular ve etkinleştirir.

    İş **arka plan iş parçacığında** yürür; arayüz `current_progress()` ile
    yoklar. Kullanıcı onayı bu çağrının kendisidir (otomatik indirme yapılmaz).
    """
    global _WORKER
    if is_running():
        return {"ok": False, "message": "Zaten bir indirme sürüyor."}
    man = _pending.get("manifest")
    if not man:
        return {"ok": False, "message": "Önce güncelleme kontrolü yapın."}
    if not auto_ok_for_install(man):
        return {"ok": False, "message": "Bu sürüm uygulamanızla uyumlu değil."}
    _CANCEL.clear()
    _set_progress(state="downloading", percent=0, processed=0, total=0,
                  message="Hazırlanıyor…", error="", error_code="",
                  version=str(man["model_version"]), rolled_back=False,
                  started_at=int(time.time()), finished_at=0)
    rel = _pending.get("release") or {}
    _WORKER = threading.Thread(target=_do_download_and_activate,
                               args=(man, rel, on_activated),
                               name="awu-model-update", daemon=True)
    _WORKER.start()
    return {"ok": True, "message": "İndirme başladı.", "version": man["model_version"]}


def auto_ok_for_install(manifest: Dict[str, object]) -> bool:
    try:
        validate_manifest({
            "manifest_version": MANIFEST_VERSION,
            "model_name": manifest["model_name"],
            "model_version": manifest["model_version"],
            "architecture": manifest["architecture"],
            "format": manifest["format"],
            "tokenizer_version": manifest["tokenizer_version"],
            "artifact": {"name": manifest["artifact_name"],
                         "url": manifest["artifact_url"],
                         "size": manifest["artifact_size"],
                         "sha256": manifest["artifact_sha256"]},
            "min_app_version": manifest["min_app_version"],
        })
        return True
    except UpdateError:
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Etkinleştirme / yedekleme / geri dönme
# ---------------------------------------------------------------------------

def activate(temp_path, manifest: Dict[str, object],
             release: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Doğrulanmış geçici dosyayı etkinleştirir; hata olursa **geri döner**.

    Sıra: yedek al → hedefe taşı → `pending` yaz → yükleme denemesi yap →
    başarılıysa durumu kesinleştir, başarısızsa yedeği geri koy.
    """
    st = load_state()
    version = str(manifest["model_version"])
    target_dir = models_dir() / version
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / str(manifest["artifact_name"])

    prev = resolve_active(st)
    prev_path = str(prev["active_path"])
    prev_version = str(prev["version"])

    # 1) Yedeği koru (etkinleştirmeden ÖNCE).
    backup_path = ""
    if prev_path and Path(prev_path).is_file():
        bdir = models_dir() / "backup"
        bdir.mkdir(parents=True, exist_ok=True)
        backup_path = str(bdir / Path(prev_path).name)
        shutil.copy2(prev_path, backup_path)

    # 2) Geçici dosyayı hedefe taşı (aynı dosya sistemi → atomik replace).
    os.replace(str(temp_path), str(target))

    # 3) `pending` işaretle: bu noktada çökme olursa etkinleştirme sayılmaz.
    st["pending"] = {"version": version, "path": str(target),
                     "at": int(time.time())}
    save_state(st)

    # 4) Fiilen yüklenebiliyor mu? (asıl güvenlik adımı)
    try:
        probe = probe_model(target, manifest)
    except Exception as e:
        # Otomatik geri dönüş: hedefi kaldır, yedeği koru, durumu eski hâline al.
        _safe_unlink(target)
        st["pending"] = None
        st["installed_version"] = prev_version
        st["installed_path"] = prev_path if prev_version != bundled_version() else ""
        st["installed_sha256"] = sha256_file(prev_path) if Path(prev_path).is_file() else ""
        st["source"] = "bundled" if not st["installed_path"] else "updated"
        st["backup_version"] = prev_version
        st["backup_path"] = backup_path
        _history_add(st, {"at": int(time.time()), "from": prev_version, "to": version,
                          "result": "rolled_back", "error": str(e)})
        save_state(st)
        return {
            "ok": False,
            "rolled_back": True,
            "active_path": prev_path,
            "active_version": prev_version,
            "error": str(e),
            "message": "Yeni model yüklenemedi; önceki çalışan modele dönüldü.",
            "probe": None,
        }

    # 5) Kesinleştir.
    sha = sha256_file(target)
    st["installed_version"] = version
    st["installed_path"] = str(target)
    st["installed_sha256"] = sha
    st["source"] = "updated"
    st["backup_version"] = prev_version
    st["backup_path"] = backup_path
    st["pending"] = None
    _history_add(st, {"at": int(time.time()), "from": prev_version, "to": version,
                      "result": "ok"})
    save_state(st)
    _safe_unlink(temp_path)
    return {
        "ok": True,
        "rolled_back": False,
        "active_path": str(target),
        "active_version": version,
        "previous_version": prev_version,
        "backup_path": backup_path,
        "backup_version": prev_version,
        "sha256": sha,
        "size": int(probe["size"]),
        "params": int(probe["load"]["params"]) if probe.get("load") else None,
        "message": "Model %s sürümüne yükseltildi." % version,
        "probe": probe,
    }


def rollback() -> Dict[str, object]:
    """Kullanıcı isteğiyle önceki modele döner (yedekten)."""
    st = load_state()
    bpath = str(st.get("backup_path") or "")
    bver = str(st.get("backup_version") or "")
    if not bpath or not Path(bpath).is_file():
        return {"ok": False, "message": "Geri dönülecek yedek model yok."}
    probe_model(Path(bpath))          # yedek gerçekten çalışıyor mu?
    cur_ver = str(st.get("installed_version") or "")
    is_bundled = bver == bundled_version()
    st["installed_version"] = bver
    st["installed_path"] = "" if is_bundled else bpath
    st["installed_sha256"] = sha256_file(Path(bpath))
    st["source"] = "bundled" if is_bundled else "updated"
    st["backup_path"] = ""
    st["backup_version"] = ""
    st["pending"] = None
    _history_add(st, {"at": int(time.time()), "from": cur_ver, "to": bver,
                      "result": "rollback"})
    save_state(st)
    resolved = resolve_active(st)
    return {
        "ok": True,
        "active_path": resolved["active_path"],
        "active_version": resolved["version"],
        "message": "Önceki modele dönüldü (%s)." % resolved["version"],
    }


def status() -> Dict[str, object]:
    """Arayüz için özet: yüklü sürüm, yedek, son kontrol, otomatik kontrol."""
    st = load_state()
    resolved = resolve_active(st) if _CFG["base_dir"] is not None else {
        "active_path": "", "version": st.get("installed_version"), "source": "?"}
    last = st.get("last_check_result") or {}
    return {
        "ok": True,
        "installed_version": str(st.get("installed_version") or bundled_version()),
        "bundled_version": bundled_version(),
        "active_path": resolved["active_path"],
        "active_version": resolved["version"],
        "source": resolved["source"],
        "installed_sha256": str(st.get("installed_sha256") or ""),
        "backup_version": str(st.get("backup_version") or ""),
        "can_rollback": bool(st.get("backup_path")),
        "auto_check": bool(st.get("auto_check", True)),
        "last_check_at": int(st.get("last_check_at") or 0),
        "auto_check_due": auto_check_due(),
        "last_check_result": last,
        "history": list(st.get("history") or []),
        "model_name": "AwuGöktürk-Microcontroller:5K",
        "app_version": app_version(),
        "repo": "https://github.com/{}/{}".format(GITHUB_OWNER, GITHUB_REPO),
        "pending_manifest": bool(_pending.get("manifest")),
    }
