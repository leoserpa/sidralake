"""Testes automatizados de integridade da documentacao bilingue Diataxis (pt-BR e en)."""

from __future__ import annotations

import re

from ibge_market_intel.config import get_settings

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_FORBIDDEN_PT_HEADING_RE = re.compile(
    r"\b(Tutorials|How-to Guides?|Reference|Explanation|Quick Start|Quality Gates|Smoke Run)\b"
)


def test_bilingual_diataxis_docs_links_and_headings() -> None:
    root = get_settings().project_root
    md_files = sorted([root / "README.md", root / "README.en.md", *(root / "docs").rglob("*.md")])
    assert len(md_files) == 23

    pt_dir = root / "docs" / "pt-br"
    en_dir = root / "docs" / "en"
    pt_files = sorted(p.relative_to(pt_dir) for p in pt_dir.rglob("*.md"))
    en_files = sorted(p.relative_to(en_dir) for p in en_dir.rglob("*.md"))
    assert len(pt_files) == 10
    assert len(en_files) == 10

    for md in md_files:
        text = md.read_text(encoding="utf-8")
        assert len(text.strip()) > 300, f"Documento vazio ou incompleto: {md}"

        for match in _LINK_RE.finditer(text):
            href = match.group(1).strip()
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_rel = href.split("#", 1)[0]
            if target_rel:
                target = (md.parent / target_rel).resolve()
                assert target.exists(), f"Link quebrado em {md.relative_to(root)}: {href}"

        if md == root / "README.md" or pt_dir in md.parents:
            for line in text.splitlines():
                if line.startswith(("#", "| **")):
                    assert not _FORBIDDEN_PT_HEADING_RE.search(line), (
                        f"Titulo nao traduzido em {md.relative_to(root)}: {line}"
                    )
