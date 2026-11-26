"""Testes automatizados de integridade da documentacao bilingue Diataxis, ADRs e governanca."""

from __future__ import annotations

import re

from ibge_market_intel.config import get_settings

_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_FORBIDDEN_PT_HEADING_RE = re.compile(
    r"\b(Tutorials|How-to Guides?|Reference|Explanation|Quick Start|Quality Gates|Smoke Run)\b"
)
_REQUIRED_ADR_HEADINGS = (
    "## Status",
    "## Date",
    "## Context",
    "## Decision",
    "## Alternatives Considered",
    "## Consequences",
)


def test_bilingual_diataxis_docs_links_and_headings() -> None:
    root = get_settings().project_root
    agents_file = root / "AGENTS.md"
    changelog_file = root / "CHANGELOG.md"
    docs_index = root / "docs" / "README.md"
    assert agents_file.is_file()
    assert changelog_file.is_file()
    assert docs_index.is_file()

    md_files = sorted(
        [
            root / "README.md",
            root / "README.en.md",
            agents_file,
            changelog_file,
            *(root / "docs").rglob("*.md"),
        ]
    )
    assert len(md_files) >= 32

    pt_dir = root / "docs" / "pt-br"
    en_dir = root / "docs" / "en"
    pt_files = sorted(p.relative_to(pt_dir) for p in pt_dir.rglob("*.md"))
    en_files = sorted(p.relative_to(en_dir) for p in en_dir.rglob("*.md"))
    assert len(pt_files) == 10
    assert len(en_files) == 10

    decisions_dir = root / "docs" / "decisions"
    decisions_index_path = decisions_dir / "README.md"
    assert decisions_index_path.is_file()
    decisions_index = decisions_index_path.read_text(encoding="utf-8")
    adr_files = sorted(decisions_dir.glob("ADR-*.md"))
    assert len(adr_files) >= 6

    for adr in adr_files:
        adr_text = adr.read_text(encoding="utf-8")
        assert adr.name in decisions_index, f"ADR nao indexado em decisions/README.md: {adr.name}"
        for heading in _REQUIRED_ADR_HEADINGS:
            assert heading in adr_text, f"Secao obrigatoria ausente em {adr.name}: {heading}"

    for md in md_files:
        text = md.read_text(encoding="utf-8")
        assert len(text.strip()) > 300, f"Documento vazio ou incompleto: {md}"
        clean_text = _FENCE_RE.sub("", text)

        for match in _LINK_RE.finditer(clean_text):
            href = match.group(1).strip()
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_rel = href.split("#", 1)[0]
            if target_rel:
                target = (md.parent / target_rel).resolve()
                assert target.exists(), f"Link quebrado em {md.relative_to(root)}: {href}"

        if md == root / "README.md" or pt_dir in md.parents:
            for line in clean_text.splitlines():
                if line.startswith(("#", "| **")):
                    assert not _FORBIDDEN_PT_HEADING_RE.search(line), (
                        f"Titulo nao traduzido em {md.relative_to(root)}: {line}"
                    )
