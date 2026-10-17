"""Response Handler: sonucu kullaniciya sunulacak bicime getirir."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import knowledge_registry as KR


@dataclass
class AgentResponse:
    status: str                      # ok | needs_info | unsupported | error | greeting | info
    message: str
    board: Optional[str] = None
    framework: Optional[str] = None
    code: Optional[str] = None
    intent: Optional[str] = None
    modules: list = field(default_factory=list)
    libraries: list = field(default_factory=list)
    wiring: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    guard: list = field(default_factory=list)          # [(level, message)]
    build: dict = field(default_factory=dict)
    tests: list = field(default_factory=list)
    hardware_plan: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    classifier_hint: Optional[str] = None


def support_matrix() -> list[dict]:
    return KR.support_matrix()


def render_markdown(r: AgentResponse) -> str:
    out = [f"**Durum:** {r.status}"]
    if r.intent:
        out.append(f"**Gorev turu (Intent):** {r.intent}")
    if r.board:
        out.append(f"**Kart:** {r.board}  |  **Framework:** {r.framework}")
    if r.classifier_hint:
        out.append(f"**5K siniflandirici ipucu:** {r.classifier_hint}")
    out.append("")
    out.append(r.message)
    if r.questions:
        out.append("\n**Sorular:**")
        out += [f"- {q}" for q in r.questions]
    if r.assumptions:
        out.append("\n**Varsayimlar:**")
        out += [f"- {a}" for a in r.assumptions]
    if r.modules:
        out.append("\n**Moduller:** " + ", ".join(r.modules))
    if r.libraries:
        out.append("**Kutuphaneler:** " + ", ".join(r.libraries))
    if r.code:
        out.append("\n```cpp\n" + r.code.rstrip() + "\n```")
    if r.wiring:
        out.append("**Baglanti notlari:**")
        out += [f"- {w}" for w in r.wiring]
    if r.guard:
        out.append("**AwuGuard bulgulari:**")
        icons = {"error": "[HATA]", "warning": "[UYARI]", "info": "[BILGI]"}
        out += [f"- {icons.get(lvl, lvl)} {m}" for lvl, m in r.guard]
    else:
        out.append("**AwuGuard:** belirgin hata bulunmadi (kapsam sinirlidir).")
    if r.build:
        b = r.build
        if b.get("ran"):
            out.append(f"**Derleme (host sozdizimi):** {'BASARILI' if b.get('ok') else 'BASARISIZ'}"
                       f"  ({b.get('tool')})")
            if not b.get("ok") and b.get("stderr"):
                out.append("```\n" + b["stderr"][:600] + "\n```")
        out.append(f"  not: {b.get('note', '')}")
    if r.tests:
        out.append("**Testler:**")
        for t in r.tests:
            out.append(f"- [{t.get('type')}] {t.get('expect', t.get('note', ''))}")
    if r.hardware_plan:
        out.append("**Donanim dogrulama plani:**")
        out += [f"- {h}" for h in r.hardware_plan]
    if r.notes:
        out.append("**Notlar:**")
        out += [f"- {n}" for n in r.notes]
    return "\n".join(out)
