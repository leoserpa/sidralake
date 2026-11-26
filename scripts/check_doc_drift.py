"""Verificador de links Markdown, conformidade de ADRs e drift de documentacao via historico Git."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT_BIN = shutil.which("git") or "git"

DOC_SCAN_TARGETS: tuple[Path, ...] = (
    ROOT / "README.md",
    ROOT / "README.en.md",
    ROOT / "AGENTS.md",
    ROOT / "CHANGELOG.md",
)

REQUIRED_ADR_HEADINGS: tuple[str, ...] = (
    "## Status",
    "## Date",
    "## Context",
    "## Decision",
    "## Alternatives Considered",
    "## Consequences",
)

# Mapeamento explicito entre documentos de referencia/arquitetura e caminhos de codigo-fonte.
DRIFT_MAPPINGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "README.md",
        (
            "src/ibge_market_intel/",
            "dbt_project/",
            "dashboard/pages/",
            ".github/workflows/",
            "pyproject.toml",
        ),
    ),
    (
        "README.en.md",
        (
            "src/ibge_market_intel/",
            "dbt_project/",
            "dashboard/pages/",
            ".github/workflows/",
            "pyproject.toml",
        ),
    ),
    (
        "AGENTS.md",
        (
            "src/ibge_market_intel/",
            "dbt_project/",
            "dashboard/components/",
            "Makefile",
            ".github/workflows/",
        ),
    ),
    (
        "docs/pt-br/referencia/configuracao-e-cli.md",
        (
            "src/ibge_market_intel/cli.py",
            "src/ibge_market_intel/config.py",
            "Makefile",
            "dbt_project/dbt_project.yml",
            "dbt_project/profiles.yml",
            ".github/workflows/",
        ),
    ),
    (
        "docs/en/reference/configuration-and-cli.md",
        (
            "src/ibge_market_intel/cli.py",
            "src/ibge_market_intel/config.py",
            "Makefile",
            "dbt_project/dbt_project.yml",
            "dbt_project/profiles.yml",
            ".github/workflows/",
        ),
    ),
    (
        "docs/pt-br/referencia/fontes-ibge-e-contratos.md",
        (
            "src/ibge_market_intel/ingestion/catalogs.py",
            "src/ibge_market_intel/ingestion/schemas.py",
            "src/ibge_market_intel/quality/contracts.py",
            "dbt_project/macros/parse_ibge_numeric.sql",
        ),
    ),
    (
        "docs/en/reference/ibge-sources-and-contracts.md",
        (
            "src/ibge_market_intel/ingestion/catalogs.py",
            "src/ibge_market_intel/ingestion/schemas.py",
            "src/ibge_market_intel/quality/contracts.py",
            "dbt_project/macros/parse_ibge_numeric.sql",
        ),
    ),
    (
        "docs/pt-br/referencia/dicionario-de-dados-lakehouse.md",
        (
            "dbt_project/models/",
            "dbt_project/snapshots/",
            "dbt_project/tests/",
            "src/ibge_market_intel/orchestration/",
        ),
    ),
    (
        "docs/en/reference/data-dictionary-lakehouse.md",
        (
            "dbt_project/models/",
            "dbt_project/snapshots/",
            "dbt_project/tests/",
            "src/ibge_market_intel/orchestration/",
        ),
    ),
    (
        "docs/pt-br/explicacoes/arquitetura-medalhao-e-design.md",
        (
            "src/ibge_market_intel/ingestion/",
            "src/ibge_market_intel/orchestration/",
            "src/ibge_market_intel/analytics/bi_export.py",
            "src/ibge_market_intel/quality/dashboard_guard.py",
            "dbt_project/models/",
        ),
    ),
    (
        "docs/en/explanation/medallion-architecture-and-design.md",
        (
            "src/ibge_market_intel/ingestion/",
            "src/ibge_market_intel/orchestration/",
            "src/ibge_market_intel/analytics/bi_export.py",
            "src/ibge_market_intel/quality/dashboard_guard.py",
            "dbt_project/models/",
        ),
    ),
    (
        "docs/pt-br/explicacoes/metodologia-inteligencia-de-mercado.md",
        (
            "dbt_project/models/silver/intermediate/",
            "dbt_project/models/gold/marts/",
            "dbt_project/macros/normalize_percentile.sql",
        ),
    ),
    (
        "docs/en/explanation/market-intelligence-methodology.md",
        (
            "dbt_project/models/silver/intermediate/",
            "dbt_project/models/gold/marts/",
            "dbt_project/macros/normalize_percentile.sql",
        ),
    ),
    (
        "docs/pt-br/guias-praticos/portoes-de-qualidade-e-ci.md",
        (
            "Makefile",
            ".github/workflows/ci.yml",
            ".github/workflows/pages.yml",
            "tests/",
            "dashboard/scripts/smoke_test_build.mjs",
        ),
    ),
    (
        "docs/en/how-to/run-quality-gates-and-ci.md",
        (
            "Makefile",
            ".github/workflows/ci.yml",
            ".github/workflows/pages.yml",
            "tests/",
            "dashboard/scripts/smoke_test_build.mjs",
        ),
    ),
)

_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


@dataclass(frozen=True)
class DriftResult:
    doc_path: str
    status: str  # current | stale | can't tell
    detail: str


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [GIT_BIN, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def collect_markdown_files() -> list[Path]:
    files = [p for p in DOC_SCAN_TARGETS if p.exists()]
    docs_dir = ROOT / "docs"
    if docs_dir.exists():
        files.extend(sorted(docs_dir.rglob("*.md")))
    return files


def check_markdown_links(files: list[Path]) -> list[str]:
    errors: list[str] = []
    for md_file in files:
        content = md_file.read_text(encoding="utf-8")
        cleaned = _FENCE_RE.sub("", content)
        cleaned = _INLINE_CODE_RE.sub("", cleaned)
        for raw_target in _LINK_RE.findall(cleaned):
            target = raw_target.strip()
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "file://")):
                continue
            target = target.strip("<>").split("#", 1)[0].split("?", 1)[0].strip()
            if not target:
                continue
            resolved = (md_file.parent / target).resolve()
            if not resolved.exists():
                rel = md_file.relative_to(ROOT)
                errors.append(f"{rel}: link quebrado -> '{raw_target}'")
    return errors


def check_adrs() -> tuple[int, list[str]]:
    decisions_dir = ROOT / "docs" / "decisions"
    if not decisions_dir.exists():
        return 0, ["docs/decisions/: diretorio ausente"]

    errors: list[str] = []
    index_path = decisions_dir / "README.md"
    index_text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    if not index_path.exists():
        errors.append("docs/decisions/README.md: arquivo indice ausente")

    adr_files = sorted(decisions_dir.glob("ADR-*.md"))
    if not adr_files:
        errors.append("docs/decisions/: nenhum arquivo ADR-*.md encontrado")

    for adr in adr_files:
        text = adr.read_text(encoding="utf-8")
        rel = adr.relative_to(ROOT)
        errors.extend(
            f"{rel}: secao obrigatoria ausente '{heading}'"
            for heading in REQUIRED_ADR_HEADINGS
            if heading not in text
        )
        if index_text and adr.name not in index_text:
            errors.append(f"docs/decisions/README.md: ADR '{adr.name}' nao esta listado no indice")

    return len(adr_files), errors


def _latest_commit_for(paths: tuple[str, ...]) -> tuple[str, str] | None:
    res = _git("log", "-1", "--format=%H %ad", "--date=short", "--", *paths)
    if res.returncode != 0 or not res.stdout.strip():
        return None
    sha, _, date_str = res.stdout.strip().partition(" ")
    return sha, date_str


def check_git_drift() -> list[DriftResult]:
    shallow_res = _git("rev-parse", "--is-shallow-repository")
    is_shallow = shallow_res.returncode == 0 and shallow_res.stdout.strip() == "true"

    results: list[DriftResult] = []
    for doc_rel, code_paths in DRIFT_MAPPINGS:
        if not (ROOT / doc_rel).exists():
            results.append(DriftResult(doc_rel, "can't tell", "arquivo de doc nao encontrado"))
            continue
        if is_shallow:
            results.append(
                DriftResult(
                    doc_rel,
                    "can't tell",
                    "repositorio shallow clone; ordem git indisponivel",
                )
            )
            continue

        doc_info = _latest_commit_for((doc_rel,))
        code_info = _latest_commit_for(code_paths)
        if doc_info is None or code_info is None:
            results.append(
                DriftResult(doc_rel, "can't tell", "sem historico git suficiente (nao commitado)")
            )
            continue

        doc_sha, doc_date = doc_info
        code_sha, code_date = code_info

        if doc_sha == code_sha:
            results.append(
                DriftResult(doc_rel, "current", f"alterados juntos ({doc_sha[:7]} em {doc_date})")
            )
            continue

        code_before_doc = _git("merge-base", "--is-ancestor", code_sha, doc_sha).returncode == 0
        if code_before_doc:
            results.append(
                DriftResult(
                    doc_rel,
                    "current",
                    f"doc {doc_sha[:7]} ({doc_date}) >= codigo {code_sha[:7]} ({code_date})",
                )
            )
            continue

        doc_before_code = _git("merge-base", "--is-ancestor", doc_sha, code_sha).returncode == 0
        if doc_before_code:
            msg = f"codigo {code_sha[:7]} ({code_date}) mudou apos doc {doc_sha[:7]} ({doc_date})"
            results.append(DriftResult(doc_rel, "stale", msg))
            continue

        results.append(
            DriftResult(doc_rel, "can't tell", "ramos divergentes; ancestralidade indeterminada")
        )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Valida links, ADRs e drift de documentacao via Git."
    )
    parser.add_argument(
        "--strict-drift",
        action="store_true",
        help="Retorna codigo de saida != 0 se houver qualquer documento com status 'stale'.",
    )
    args = parser.parse_args(argv)

    md_files = collect_markdown_files()
    link_errors = check_markdown_links(md_files)
    adr_count, adr_errors = check_adrs()
    drift_results = check_git_drift()

    print(f"Markdown files checked: {len(md_files)} | ADRs checked: {adr_count}")
    if link_errors:
        print("\nLINK ERRORS:")
        for err in link_errors:
            print(f"  - {err}")
    if adr_errors:
        print("\nADR STRUCTURE ERRORS:")
        for err in adr_errors:
            print(f"  - {err}")

    print("\nDOCUMENTATION DRIFT AUDIT (git ancestry):")
    stale_count = 0
    for item in drift_results:
        if item.status == "stale":
            stale_count += 1
        print(f"  [{item.status:10}] {item.doc_path} :: {item.detail}")

    has_structural_errors = bool(link_errors or adr_errors)
    if has_structural_errors:
        return 1
    if args.strict_drift and stale_count > 0:
        print(f"\nFAILED (--strict-drift): {stale_count} stale doc(s) detected.")
        return 1
    print("\nOK: links e estrutura de ADRs validos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
