"""Guardioes automatizados de contratos, SQL e renderizacao do dashboard Evidence.dev.

Previne regressoes de build, escala percentual (100x), formatacao de anos em DuckDB-WASM
(DOUBLE -> '2024.0' ou '2,024'), SQL injection em nomes municipais com apostrofo,
rotulos duplicados em barras empilhadas, caixas de SQL expostas e paginas/tabelas ausentes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from ibge_market_intel.analytics.bi_export import BI_GOLD_TABLES

_SQL_BLOCK_RE = re.compile(r"```sql\s+(\w+)\s*\n(.*?)```", re.DOTALL)
_COMPONENT_OPEN_RE = re.compile(
    r"<(?P<tag>BarChart|LineChart|AreaChart|ScatterPlot|BubbleChart|Heatmap|DataTable|"
    r"BigValue|Dropdown|Slider|Value|ECharts|KpiCard|ExecTable|DonutPanel|CityHero|DataFooter)(?=[\s/>])"
)
_TABLE_REF_RE = re.compile(r"\bsidralake\.(\w+)\b")
_DATA_ATTR_RE = re.compile(r"\bdata=\{\s*(\w+)\s*\}")
_NAME_ATTR_RE = re.compile(r'\bname=(?:"([^"]+)"|\'([^\']+)\'|([^\s/>]+))')
_VALUE_ATTR_RE = re.compile(r'\bvalue=(?:"([^"]+)"|\'([^\']+)\'|([^\s/>]+))')
_DEFAULT_ATTR_RE = re.compile(
    r'\bdefaultValue=(?:\{\s*([^}]+?)\s*\}|"([^"]+)"|\'([^\']+)\'|([^\s/>]+))'
)
_RIGHT_PADDING_RE = re.compile(r"\brightPadding=(?:\{\s*(\d+)\s*\}|(\d+))")
_BAD_DOUBLE_YEAR_CAST_RE = re.compile(
    r"(?:cast\(\s*(?:(?:max|min)\(\s*)?(?:\w+\.)?ano_referencia\s*\)?\s+as\s+"
    r"(?:varchar|text)\s*\)|(?:\w+\.)?ano_referencia\s*::\s*(?:varchar|text)\b)",
    re.IGNORECASE,
)
_RAW_CITY_INPUT_RE = re.compile(r"\$\{inputs\.cidade\w*\.value\}")
_SAFE_CITY_CAST_RE = re.compile(
    r"try_cast\(\s*'\$\{inputs\.cidade\w*\.value\}'\s+as\s+integer\s*\)",
    re.IGNORECASE,
)
_RAW_NUM_INPUT_RE = re.compile(r"\$\{inputs\.(?:ano\.value|min_\w+)\}")
_SAFE_NUM_CAST_RE = re.compile(
    r"try_cast\(\s*'\$\{inputs\.(?:ano\.value|min_\w+)\}'\s+as\s+"
    r"(?:integer|double|bigint|numeric)\s*\)",
    re.IGNORECASE,
)
_FRONTMATTER_TITLE_RE = re.compile(r"\A---\s*\n.*?^title:\s*\S+.*?^---\s*\n", re.DOTALL | re.M)
_YEAR_STR_RE = re.compile(r"^\d{4}$")
_COMPETENCIA_RE = re.compile(r"^\d{2}/\d{4}$")
_UPPER_SNAKE_ENUM_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
_SHARE_PCT_COL_RE = re.compile(r"(?:share|formalizacao|agro|ind|servicos|adm_pub).*_pct$")

_FORBIDDEN_SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {".parquet", ".csv", ".tsv", ".duckdb", ".db", ".arrow", ".ipc", ".json"}
)
_FATAL_HTML_PATTERNS: tuple[str, ...] = (
    "Catalog Error:",
    "Binder Error:",
    "Parser Error:",
    "Conversion Error:",
    "Runtime Error:",
)
_LAYOUT_REQUIRED_PROPS: tuple[str, ...] = (
    "neverShowQueries={true}",
    "fullWidth={true}",
    "hideTOC={true}",
    "hideSidebar={true}",
    "hideHeader={true}",
    "builtWithEvidence={false}",
)
_WORKFLOW_REQUIRED_GATES: tuple[str, ...] = (
    "touch build/.nojekyll",
    "sources:strict",
    "validate-bi",
    "run test:e2e",
)
_DUCKDB_INT_TYPES: frozenset[str] = frozenset(
    {"INTEGER", "BIGINT", "SMALLINT", "TINYINT", "HUGEINT"}
)


@dataclass(frozen=True)
class DashboardIssue:
    """Falha detectada em alguma camada de validacao do dashboard Evidence.dev."""

    rule: str
    file: str
    message: str


@dataclass(frozen=True)
class ParsedSqlBlock:
    """Bloco ```sql <nome>``` extraido de uma pagina Markdown Evidence."""

    page: str
    name: str
    sql: str
    line: int


@dataclass(frozen=True)
class ParsedComponent:
    """Componente Svelte/Evidence extraido de uma pagina Markdown."""

    page: str
    tag: str
    attrs: str
    data_ref: str | None


@dataclass(frozen=True)
class ParsedDashboardPage:
    """Representacao estruturada de uma pagina Evidence (`dashboard/pages/*.md`)."""

    path: Path
    name: str
    text: str
    sql_blocks: tuple[ParsedSqlBlock, ...]
    components: tuple[ParsedComponent, ...]
    input_defaults: dict[str, str]


def _extract_attr_value(match: re.Match[str] | None) -> str | None:
    if match is None:
        return None
    for group in match.groups():
        if group is not None:
            return group.strip().strip("\"'")
    return None


def _find_tag_close(text: str, start: int) -> int:
    """Encontra o '>' que fecha uma tag Svelte respeitando aspas e blocos {...} aninhados."""
    idx = start
    length = len(text)
    brace_depth = 0
    quote: str | None = None

    while idx < length:
        ch = text[idx]
        if quote is not None:
            if ch == "\\" and idx + 1 < length:
                idx += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
        elif ch == "{":
            brace_depth += 1
        elif ch == "}" and brace_depth > 0:
            brace_depth -= 1
        elif ch == ">" and brace_depth == 0:
            return idx
        idx += 1
    return -1


def _scan_components(page_name: str, text: str) -> tuple[list[ParsedComponent], dict[str, str]]:
    """Extrai componentes Evidence sem truncar expressoes JS com `=>` ou `>` dentro de `{...}`."""
    components: list[ParsedComponent] = []
    input_defaults: dict[str, str] = {}

    for match in _COMPONENT_OPEN_RE.finditer(text):
        tag = match.group("tag")
        close_idx = _find_tag_close(text, match.end())
        if close_idx == -1:
            continue
        raw_attrs = text[match.end() : close_idx]
        attrs = raw_attrs[:-1] if raw_attrs.endswith("/") else raw_attrs

        data_match = _DATA_ATTR_RE.search(attrs)
        data_ref = data_match.group(1) if data_match else None
        components.append(ParsedComponent(page=page_name, tag=tag, attrs=attrs, data_ref=data_ref))

        if tag in ("Dropdown", "Slider"):
            name_val = _extract_attr_value(_NAME_ATTR_RE.search(attrs))
            default_val = _extract_attr_value(_DEFAULT_ATTR_RE.search(attrs))
            if name_val and default_val is not None:
                key = (
                    f"${{inputs.{name_val}.value}}"
                    if tag == "Dropdown"
                    else f"${{inputs.{name_val}}}"
                )
                input_defaults[key] = default_val

    return components, input_defaults


def parse_dashboard_page(md_path: Path) -> ParsedDashboardPage:
    """Extrai blocos SQL, componentes Evidence e valores default de inputs de uma pagina."""
    text = md_path.read_text(encoding="utf-8")

    sql_blocks = tuple(
        ParsedSqlBlock(
            page=md_path.name,
            name=match.group(1),
            sql=match.group(2),
            line=text[: match.start()].count("\n") + 1,
        )
        for match in _SQL_BLOCK_RE.finditer(text)
    )
    components, input_defaults = _scan_components(md_path.name, text)

    return ParsedDashboardPage(
        path=md_path,
        name=md_path.name,
        text=text,
        sql_blocks=sql_blocks,
        components=tuple(components),
        input_defaults=input_defaults,
    )


def parse_dashboard_pages(pages_dir: Path) -> list[ParsedDashboardPage]:
    """Carrega e analisa todas as paginas `.md` do dashboard Evidence."""
    return [parse_dashboard_page(p) for p in sorted(pages_dir.glob("*.md"))]


def _check_sources_dir(project_root: Path, dashboard_dir: Path) -> list[DashboardIssue]:
    sources_dir = dashboard_dir / "sources"
    sidralake_sources = sources_dir / "sidralake"

    issues = [
        DashboardIssue(
            rule="no_binary_in_sources",
            file=str(item.relative_to(project_root)),
            message=(
                "Arquivo de dados nao deve residir em dashboard/sources/ "
                "(Evidence tenta executar binarios como templates SQL). "
                "Use dashboard/parquet_data/."
            ),
        )
        for item in sorted(sources_dir.rglob("*"))
        if item.is_file() and item.suffix.lower() in _FORBIDDEN_SOURCE_EXTENSIONS
    ]

    expected_sql = {f"{tbl}.sql" for tbl in BI_GOLD_TABLES}
    actual_sql = {p.name for p in sidralake_sources.glob("*.sql")}

    issues.extend(
        DashboardIssue(
            rule="source_table_parity",
            file=f"dashboard/sources/sidralake/{fname}",
            message=f"Tabela Gold '{fname[:-4]}' em BI_GOLD_TABLES sem arquivo SQL de origem.",
        )
        for fname in sorted(expected_sql - actual_sql)
    )
    issues.extend(
        DashboardIssue(
            rule="source_table_parity",
            file=f"dashboard/sources/sidralake/{fname}",
            message=f"Arquivo SQL orfao '{fname}' nao declarado em BI_GOLD_TABLES.",
        )
        for fname in sorted(actual_sql - expected_sql)
    )

    for tbl in BI_GOLD_TABLES:
        sql_file = sidralake_sources / f"{tbl}.sql"
        expected_ref = f"read_parquet('parquet_data/{tbl}.parquet')"
        if sql_file.exists() and expected_ref not in sql_file.read_text(encoding="utf-8"):
            issues.append(
                DashboardIssue(
                    rule="source_parquet_path",
                    file=str(sql_file.relative_to(project_root)),
                    message=f"Origem deve referenciar {expected_ref}.",
                )
            )
    return issues


def _check_package_and_workflow(project_root: Path, dashboard_dir: Path) -> list[DashboardIssue]:
    issues: list[DashboardIssue] = []

    pkg_path = dashboard_dir / "package.json"
    if not pkg_path.exists():
        issues.append(
            DashboardIssue(
                rule="typescript_pin",
                file="dashboard/package.json",
                message="dashboard/package.json ausente.",
            )
        )
    else:
        pkg: dict[str, Any] = json.loads(pkg_path.read_text(encoding="utf-8"))
        dev_ts = str(pkg.get("devDependencies", {}).get("typescript", ""))
        ovr_ts = str(pkg.get("overrides", {}).get("typescript", ""))
        if not dev_ts.startswith(("^5.", "~5.", "5.")) or not ovr_ts.startswith(
            ("^5.", "~5.", "5.")
        ):
            issues.append(
                DashboardIssue(
                    rule="typescript_pin",
                    file="dashboard/package.json",
                    message=(
                        "TypeScript deve permanecer pinado em 5.x em devDependencies e overrides "
                        "(previne conflito peer svelte2tsx no npm install)."
                    ),
                )
            )
        e2e_cmd = str(pkg.get("scripts", {}).get("test:e2e", ""))
        smoke_script = dashboard_dir / "scripts" / "smoke_test_build.mjs"
        if "smoke_test_build.mjs" not in e2e_cmd or not smoke_script.exists():
            issues.append(
                DashboardIssue(
                    rule="e2e_smoke_script",
                    file="dashboard/scripts/smoke_test_build.mjs",
                    message=(
                        "Script E2E headless Chromium (test:e2e -> smoke_test_build.mjs) ausente."
                    ),
                )
            )

    pages_wf = project_root / ".github" / "workflows" / "pages.yml"
    if not pages_wf.exists():
        issues.append(
            DashboardIssue(
                rule="pages_workflow_guardrails",
                file=".github/workflows/pages.yml",
                message="Workflow .github/workflows/pages.yml ausente.",
            )
        )
    else:
        wf_text = pages_wf.read_text(encoding="utf-8")
        issues.extend(
            DashboardIssue(
                rule="pages_workflow_guardrails",
                file=".github/workflows/pages.yml",
                message=f"Quality gate obrigatorio ausente no workflow Pages: {gate}",
            )
            for gate in _WORKFLOW_REQUIRED_GATES
            if gate not in wf_text
        )

    return issues


def _check_layout_and_configs(project_root: Path, dashboard_dir: Path) -> list[DashboardIssue]:
    issues: list[DashboardIssue] = []

    layout_path = dashboard_dir / "pages" / "+layout.svelte"
    if not layout_path.exists():
        issues.append(
            DashboardIssue(
                rule="layout_security_and_ux",
                file="dashboard/pages/+layout.svelte",
                message="Layout customizado ausente; queries SQL ficarao expostas no dashboard.",
            )
        )
    else:
        layout_text = layout_path.read_text(encoding="utf-8")
        issues.extend(
            DashboardIssue(
                rule="layout_security_and_ux",
                file="dashboard/pages/+layout.svelte",
                message=f"Propriedade obrigatoria ausente no layout: {prop}",
            )
            for prop in _LAYOUT_REQUIRED_PROPS
            if prop not in layout_text
        )

    evidence_cfg = dashboard_dir / "evidence.config.yaml"
    if not evidence_cfg.exists() or "basePath: /sidralake" not in evidence_cfg.read_text(
        encoding="utf-8"
    ):
        issues.append(
            DashboardIssue(
                rule="evidence_config_basepath",
                file="dashboard/evidence.config.yaml",
                message="basePath: /sidralake obrigatorio para deploy sem 404 no GitHub Pages.",
            )
        )

    issues.extend(_check_package_and_workflow(project_root, dashboard_dir))
    return issues


def _check_sql_block_static(
    blk: ParsedSqlBlock,
    rel_file: str,
    allowed_tables: set[str],
) -> list[DashboardIssue]:
    loc = f"{rel_file}:{blk.line}"
    issues = [
        DashboardIssue(
            rule="unknown_source_table",
            file=loc,
            message=(
                f"Query '{blk.name}' referencia sidralake.{m.group(1)}, "
                "nao registrada em BI_GOLD_TABLES."
            ),
        )
        for m in _TABLE_REF_RE.finditer(blk.sql)
        if m.group(1) not in allowed_tables
    ]

    if _BAD_DOUBLE_YEAR_CAST_RE.search(blk.sql):
        issues.append(
            DashboardIssue(
                rule="no_double_to_varchar_year_cast",
                file=loc,
                message=(
                    f"Query '{blk.name}' faz cast direto de ano_referencia para varchar/text "
                    "(gera '2024.0' no DuckDB-WASM). "
                    "Use cast(cast(... as integer) as varchar)."
                ),
            )
        )

    if len(_RAW_CITY_INPUT_RE.findall(blk.sql)) > len(_SAFE_CITY_CAST_RE.findall(blk.sql)):
        issues.append(
            DashboardIssue(
                rule="safe_input_casting",
                file=loc,
                message=(
                    f"Query '{blk.name}' usa ${{inputs.cidade*.value}} sem "
                    "try_cast(... as integer) (risco de quebra com apostrofo ou SSR)."
                ),
            )
        )

    if len(_RAW_NUM_INPUT_RE.findall(blk.sql)) > len(_SAFE_NUM_CAST_RE.findall(blk.sql)):
        issues.append(
            DashboardIssue(
                rule="safe_input_casting",
                file=loc,
                message=(
                    f"Query '{blk.name}' usa input numerico sem try_cast "
                    "(quebra no prerender SSR quando vazio)."
                ),
            )
        )

    return issues


def _check_barchart_static(comp: ParsedComponent, rel_file: str) -> list[DashboardIssue]:
    issues: list[DashboardIssue] = []
    is_stacked = bool(re.search(r'\btype=(?:"stacked"|\'stacked\'|stacked)(?=\s|$)', comp.attrs))
    has_labels = bool(re.search(r"\blabels=(?:true|\{\s*true\s*\})(?=\s|$)", comp.attrs))
    has_no_total = bool(
        re.search(r"\bstackTotalLabel=(?:false|\{\s*false\s*\})(?=\s|$)", comp.attrs)
    )

    if is_stacked and has_labels and not has_no_total:
        issues.append(
            DashboardIssue(
                rule="stacked_barchart_no_double_labels",
                file=rel_file,
                message=(
                    f"<BarChart data={{{comp.data_ref}}}> empilhado com labels=true "
                    "deve declarar stackTotalLabel=false."
                ),
            )
        )

    is_swapped = bool(re.search(r"\bswapXY=(?:true|\{\s*true\s*\})(?=\s|$)", comp.attrs))
    if is_swapped and has_labels:
        rp_match = _RIGHT_PADDING_RE.search(comp.attrs)
        rp_val = int(rp_match.group(1) or rp_match.group(2)) if rp_match else 0
        if rp_val < 28:
            issues.append(
                DashboardIssue(
                    rule="swapxy_label_padding",
                    file=rel_file,
                    message=(
                        f"<BarChart data={{{comp.data_ref}}}> horizontal com labels=true "
                        f"precisa de rightPadding >= 28 (atual: {rp_val})."
                    ),
                )
            )
    return issues


def _check_component_static(
    comp: ParsedComponent,
    rel_file: str,
    defined_queries: set[str],
) -> list[DashboardIssue]:
    issues: list[DashboardIssue] = []

    if comp.data_ref and comp.data_ref not in defined_queries:
        issues.append(
            DashboardIssue(
                rule="missing_query_ref",
                file=rel_file,
                message=(
                    f"<{comp.tag}> referencia data={{{comp.data_ref}}}, "
                    "mas essa query nao existe nesta pagina."
                ),
            )
        )

    if comp.tag == "BarChart":
        issues.extend(_check_barchart_static(comp, rel_file))

    if comp.tag == "Dropdown":
        name_val = _extract_attr_value(_NAME_ATTR_RE.search(comp.attrs)) or ""
        value_col = _extract_attr_value(_VALUE_ATTR_RE.search(comp.attrs)) or ""
        if name_val.startswith("cidade") and value_col != "codigo_ibge_municipio":
            issues.append(
                DashboardIssue(
                    rule="city_dropdown_id_binding",
                    file=rel_file,
                    message=(
                        f"<Dropdown name={name_val}> deve usar value=codigo_ibge_municipio "
                        f"(atual: {value_col!r}) para impedir erro SQL com apostrofo."
                    ),
                )
            )

    if (
        comp.tag in ("LineChart", "AreaChart")
        and re.search(r"\by=\{\s*\[", comp.attrs)
        and re.search(r"\bseriesColors=", comp.attrs)
    ):
        issues.append(
            DashboardIssue(
                rule="multi_y_linechart_color_palette",
                file=rel_file,
                message=(
                    f"<{comp.tag} data={{{comp.data_ref}}}> multi-serie y={{[...]}} "
                    "deve usar colorPalette posicional em vez de seriesColors."
                ),
            )
        )

    return issues


def _check_pages_static(pages: list[ParsedDashboardPage]) -> list[DashboardIssue]:
    issues: list[DashboardIssue] = []
    allowed_tables = set(BI_GOLD_TABLES)

    for page in pages:
        rel_file = f"dashboard/pages/{page.name}"
        if not _FRONTMATTER_TITLE_RE.search(page.text):
            issues.append(
                DashboardIssue(
                    rule="page_frontmatter",
                    file=rel_file,
                    message="Pagina deve iniciar com frontmatter YAML contendo `title:`.",
                )
            )

        defined_queries: set[str] = set()
        for blk in page.sql_blocks:
            if blk.name in defined_queries:
                issues.append(
                    DashboardIssue(
                        rule="duplicate_query_name",
                        file=f"{rel_file}:{blk.line}",
                        message=f"Nome de query duplicado na mesma pagina: '{blk.name}'.",
                    )
                )
            defined_queries.add(blk.name)
            issues.extend(_check_sql_block_static(blk, rel_file, allowed_tables))

        for comp in page.components:
            issues.extend(_check_component_static(comp, rel_file, defined_queries))

    return issues


def validate_dashboard_static_contracts(project_root: Path) -> list[DashboardIssue]:
    """Executa todas as validacoes estaticas de configuracao, layout, SQL e componentes."""
    dashboard_dir = project_root / "dashboard"
    pages = parse_dashboard_pages(dashboard_dir / "pages")

    if not pages:
        return [
            DashboardIssue(
                rule="pages_exist",
                file="dashboard/pages",
                message="Nenhuma pagina .md encontrada em dashboard/pages/.",
            )
        ]

    issues = _check_sources_dir(project_root, dashboard_dir)
    issues.extend(_check_layout_and_configs(project_root, dashboard_dir))
    issues.extend(_check_pages_static(pages))
    return issues


def _substitute_inputs(sql: str, mapping: dict[str, str], *, empty_mode: bool) -> str:
    rendered = sql
    for placeholder, default_val in mapping.items():
        rendered = rendered.replace(placeholder, "" if empty_mode else default_val)
    if empty_mode:
        rendered = re.sub(r"\$\{inputs\.[^}]+\}", "", rendered)
    return rendered


def _register_parquet_views(
    con: duckdb.DuckDBPyConnection,
    parquet_dir: Path,
    *,
    emulate_evidence_double: bool,
) -> list[DashboardIssue]:
    issues: list[DashboardIssue] = []
    con.execute("create schema if not exists sidralake;")

    for table_name in BI_GOLD_TABLES:
        pq_path = parquet_dir / f"{table_name}.parquet"
        if not pq_path.exists():
            issues.append(
                DashboardIssue(
                    rule="parquet_exists",
                    file=str(pq_path),
                    message=f"Parquet BI ausente: {table_name}.parquet",
                )
            )
            continue

        pq_posix = pq_path.as_posix().replace("'", "''")
        if emulate_evidence_double:
            desc_sql = f"describe select * from read_parquet('{pq_posix}')"  # noqa: S608
            schema_rows = con.execute(desc_sql).fetchall()
            select_exprs = [
                f'cast("{col}" as double) as "{col}"' if dtype in _DUCKDB_INT_TYPES else f'"{col}"'
                for col, dtype, *_ in schema_rows
            ]
            view_sql = (
                f"create or replace view sidralake.{table_name} as "  # noqa: S608
                f"select {', '.join(select_exprs)} from read_parquet('{pq_posix}')"
            )
        else:
            view_sql = (
                f"create or replace view sidralake.{table_name} as "  # noqa: S608
                f"select * from read_parquet('{pq_posix}')"
            )
        con.execute(view_sql)

    return issues


def _validate_source_sql_files(
    con: duckdb.DuckDBPyConnection,
    sources_dir: Path,
    parquet_dir: Path,
    *,
    require_non_empty: bool,
) -> list[DashboardIssue]:
    issues: list[DashboardIssue] = []
    for table_name in BI_GOLD_TABLES:
        src_sql_path = sources_dir / f"{table_name}.sql"
        if not src_sql_path.exists():
            continue
        pq_posix = (parquet_dir / f"{table_name}.parquet").as_posix().replace("'", "''")
        src_sql = (
            src_sql_path.read_text(encoding="utf-8")
            .replace(f"parquet_data/{table_name}.parquet", pq_posix)
            .strip()
            .rstrip(";")
        )
        try:
            count_sql = f"select count(*) from ({src_sql})"  # noqa: S608
            cnt_row = con.execute(count_sql).fetchone()
            cnt = int(cnt_row[0]) if cnt_row else 0
            if require_non_empty and cnt == 0:
                issues.append(
                    DashboardIssue(
                        rule="source_non_empty",
                        file=f"dashboard/sources/sidralake/{table_name}.sql",
                        message=f"Source '{table_name}' retornou 0 linhas.",
                    )
                )
        except Exception as exc:
            issues.append(
                DashboardIssue(
                    rule="source_sql_exec",
                    file=f"dashboard/sources/sidralake/{table_name}.sql",
                    message=f"Falha ao executar source SQL: {exc}",
                )
            )
    return issues


def _discover_edge_city_codes(con: duckdb.DuckDBPyConnection) -> list[str]:
    codes: list[str] = []
    apostrophe_row = con.execute(
        "select cast(codigo_ibge_municipio as integer) from sidralake.dim_geografia "
        "where nome_municipio like '%''%' limit 1"
    ).fetchone()
    if apostrophe_row:
        codes.append(str(apostrophe_row[0]))
    emancipated_row = con.execute(
        "select cast(codigo_ibge_municipio as integer) from sidralake.dim_geografia "
        "where cast(codigo_ibge_municipio as integer) = 5101837 limit 1"
    ).fetchone()
    if emancipated_row:
        codes.append(str(emancipated_row[0]))
    return codes


def _check_pct_column(
    loc: str,
    query_name: str,
    col_name: str,
    non_null_vals: list[Any],
) -> list[DashboardIssue]:
    try:
        num_vals = [float(v) for v in non_null_vals]
    except (TypeError, ValueError):
        return [
            DashboardIssue(
                rule="pct_numeric_type",
                file=loc,
                message=(
                    f"Coluna '{query_name}.{col_name}' contem valor nao numerico "
                    f"(ex.: {non_null_vals[0]!r}); esperado float na escala 0..1."
                ),
            )
        ]

    if _SHARE_PCT_COL_RE.search(col_name):
        if min(num_vals) < -0.0001 or max(num_vals) > 1.0001:
            return [
                DashboardIssue(
                    rule="pct_scale_0_1",
                    file=loc,
                    message=(
                        f"Coluna '{query_name}.{col_name}' fora de [0, 1] "
                        f"(min={min(num_vals):.4f}, max={max(num_vals):.4f})."
                    ),
                )
            ]
        return []

    max_abs = max(abs(v) for v in num_vals)
    if max_abs > 2.5:
        return [
            DashboardIssue(
                rule="pct_scale_0_1",
                file=loc,
                message=(
                    f"Coluna '{query_name}.{col_name}' tem |valor|={max_abs:.2f} > 2.5 "
                    "(provavel erro 100x em coluna *_pct)."
                ),
            )
        ]
    return []


def _check_query_result_semantics(
    loc: str,
    query_name: str,
    cols: list[str],
    rows: list[tuple[Any, ...]],
    *,
    is_datatable: bool,
) -> list[DashboardIssue]:
    issues: list[DashboardIssue] = []
    for col_idx, col_name in enumerate(cols):
        non_null_vals = [r[col_idx] for r in rows if r[col_idx] is not None]
        if not non_null_vals:
            continue

        if col_name.endswith("_pct"):
            issues.extend(_check_pct_column(loc, query_name, col_name, non_null_vals))

        if col_name == "ano" and is_datatable:
            bad = next(
                (v for v in non_null_vals if not isinstance(v, str) or not _YEAR_STR_RE.match(v)),
                None,
            )
            if bad is not None:
                issues.append(
                    DashboardIssue(
                        rule="datatable_ano_format",
                        file=loc,
                        message=(
                            f"Coluna '{query_name}.ano' retornou {bad!r} "
                            f"({type(bad).__name__}); esperado 'YYYY'."
                        ),
                    )
                )

        if col_name in ("competencia", "ultima_competencia"):
            bad_comp = next(
                (
                    v
                    for v in non_null_vals
                    if not isinstance(v, str) or not _COMPETENCIA_RE.match(v)
                ),
                None,
            )
            if bad_comp is not None:
                issues.append(
                    DashboardIssue(
                        rule="competencia_mm_yyyy",
                        file=loc,
                        message=(
                            f"Coluna '{query_name}.{col_name}' retornou {bad_comp!r}; "
                            "esperado formato 'MM/YYYY'."
                        ),
                    )
                )

        if col_name in ("regime", "grupo"):
            raw_enum = next(
                (v for v in non_null_vals if isinstance(v, str) and _UPPER_SNAKE_ENUM_RE.match(v)),
                None,
            )
            if raw_enum is not None:
                issues.append(
                    DashboardIssue(
                        rule="no_raw_enum_labels",
                        file=loc,
                        message=(
                            f"Coluna '{query_name}.{col_name}' expos enum cru {raw_enum!r} "
                            "em vez de rotulo amigavel."
                        ),
                    )
                )

    return issues


def _run_page_query_modes(
    con: duckdb.DuckDBPyConnection,
    page: ParsedDashboardPage,
    blk: ParsedSqlBlock,
    *,
    is_datatable: bool,
    edge_city_codes: list[str],
    require_non_empty: bool,
) -> tuple[bool, list[DashboardIssue]]:
    loc = f"dashboard/pages/{page.name}:{blk.line}"
    issues: list[DashboardIssue] = []

    # Modo A: default
    sql_default = _substitute_inputs(blk.sql, page.input_defaults, empty_mode=False)
    try:
        cursor = con.execute(sql_default)
        cols = [d[0] for d in (cursor.description or ())]
        rows = cursor.fetchall()
    except Exception as exc:
        return False, [
            DashboardIssue(
                rule="query_exec_default",
                file=loc,
                message=f"Query '{blk.name}' falhou no modo default: {exc}",
            )
        ]

    if require_non_empty and not rows:
        issues.append(
            DashboardIssue(
                rule="query_non_empty_default",
                file=loc,
                message=f"Query '{blk.name}' retornou 0 linhas com os filtros default.",
            )
        )

    issues.extend(
        _check_query_result_semantics(loc, blk.name, cols, rows, is_datatable=is_datatable)
    )

    # Modo B: ssr_empty
    sql_ssr = _substitute_inputs(blk.sql, page.input_defaults, empty_mode=True)
    try:
        con.execute(sql_ssr).fetchall()
    except Exception as exc:
        issues.append(
            DashboardIssue(
                rule="query_exec_ssr_empty",
                file=loc,
                message=f"Query '{blk.name}' falhou no modo SSR vazio: {exc}",
            )
        )

    # Modo C: edge_cases de municipios (apostrofo + emancipado 2024+)
    city_keys = [k for k in page.input_defaults if "cidade" in k]
    for code in edge_city_codes if city_keys else ():
        edge_map = {**page.input_defaults, **{ck: code for ck in city_keys}}
        sql_edge = _substitute_inputs(blk.sql, edge_map, empty_mode=False)
        try:
            con.execute(sql_edge).fetchall()
        except Exception as exc:
            issues.append(
                DashboardIssue(
                    rule="query_exec_edge_city",
                    file=loc,
                    message=f"Query '{blk.name}' falhou para municipio {code}: {exc}",
                )
            )

    return True, issues


def validate_dashboard_queries(
    project_root: Path,
    parquet_dir: Path,
    *,
    emulate_evidence_double: bool = True,
    require_non_empty: bool = True,
) -> tuple[int, list[DashboardIssue]]:
    """Executa todas as queries de sources e pages em DuckDB (emulando DOUBLE do DuckDB-WASM)."""
    dashboard_dir = project_root / "dashboard"
    pages = parse_dashboard_pages(dashboard_dir / "pages")
    sources_dir = dashboard_dir / "sources" / "sidralake"
    executed_queries = 0

    con = duckdb.connect()
    try:
        issues = _register_parquet_views(
            con, parquet_dir, emulate_evidence_double=emulate_evidence_double
        )
        if issues:
            return executed_queries, issues

        issues.extend(
            _validate_source_sql_files(
                con, sources_dir, parquet_dir, require_non_empty=require_non_empty
            )
        )
        edge_city_codes = _discover_edge_city_codes(con)

        for page in pages:
            datatable_queries = {
                c.data_ref
                for c in page.components
                if c.tag in ("DataTable", "ExecTable") and c.data_ref
            }
            for blk in page.sql_blocks:
                ran, blk_issues = _run_page_query_modes(
                    con,
                    page,
                    blk,
                    is_datatable=blk.name in datatable_queries,
                    edge_city_codes=edge_city_codes,
                    require_non_empty=require_non_empty,
                )
                if ran:
                    executed_queries += 1
                issues.extend(blk_issues)
    finally:
        con.close()

    return executed_queries, issues


def validate_built_dashboard(
    project_root: Path, build_dir: Path | None = None
) -> list[DashboardIssue]:
    """Valida o artefato estatico gerado por `npm run build` antes do deploy no GitHub Pages."""
    dashboard_dir = project_root / "dashboard"
    pages_dir = dashboard_dir / "pages"
    target_build = build_dir or (dashboard_dir / "build")
    issues: list[DashboardIssue] = []

    if not target_build.exists():
        return [
            DashboardIssue(
                rule="build_exists",
                file=str(target_build),
                message="Diretorio de build estatico nao encontrado.",
            )
        ]

    if not (target_build / ".nojekyll").exists():
        issues.append(
            DashboardIssue(
                rule="nojekyll_exists",
                file=str(target_build / ".nojekyll"),
                message="Arquivo .nojekyll ausente (GitHub Pages bloqueia assets _app/ sem ele).",
            )
        )

    for md_path in sorted(pages_dir.glob("*.md")):
        route_html = (
            target_build / "index.html"
            if md_path.stem == "index"
            else target_build / md_path.stem / "index.html"
        )
        if not route_html.exists():
            issues.append(
                DashboardIssue(
                    rule="route_html_exists",
                    file=str(route_html),
                    message=f"Rota HTML nao gerada para pagina {md_path.name}.",
                )
            )
            continue

        html_text = route_html.read_text(encoding="utf-8", errors="replace")
        issues.extend(
            DashboardIssue(
                rule="build_html_no_fatal_error",
                file=str(route_html),
                message=f"HTML gerado contem erro fatal '{fatal}'.",
            )
            for fatal in _FATAL_HTML_PATTERNS
            if fatal in html_text
        )

    built_parquets = {
        p.stem for p in target_build.rglob("*.parquet") if p.is_file() and p.stat().st_size > 0
    }
    issues.extend(
        DashboardIssue(
            rule="build_data_table_exists",
            file=str(target_build),
            message=(
                f"Tabela '{tbl}.parquet' ausente ou vazia nos artefatos estaticos de build "
                "(causaria Catalog Error no navegador)."
            ),
        )
        for tbl in BI_GOLD_TABLES
        if tbl not in built_parquets
    )

    return issues
