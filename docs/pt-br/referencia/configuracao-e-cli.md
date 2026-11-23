> 🌐 **Idioma:** **Português (BR)** | [English](../../en/reference/configuration-and-cli.md) · [Índice](../README.md)

# Referência: Configuração, CLI e Ambiente

Especificação técnica dos comandos CLI, alvos do `Makefile`, variáveis de ambiente (`PipelineSettings`), perfis do `dbt-duckdb` e pipeline de Integração Contínua (CI).

---

## 1. CLI `sidralake` (e alias `ibge-pipeline`)

Definida em `src/ibge_market_intel/cli.py` e exposta via `pyproject.toml` (`[project.scripts]`).

```bash
uv run sidralake <subcomando> [opcoes]
```

| Comando | Opções | Comportamento |
| :--- | :--- | :--- |
| `sidralake run` | `--mode {smoke,full}` (padrão: `full`) | Executa o ciclo completo: ingestão assíncrona IBGE + validação Pandera → Delta Bronze → `dbt build` → exportação ACID Silver e Gold para Delta Lake. Em `--mode smoke`, limita `uf_filter` para `[35, 51]` (se `IBGE_UF_FILTER` não estiver definida) e usa janela anual reduzida. |
| `sidralake maintain` | — | Percorre `data/bronze/`, `data/silver/` e `data/gold/` e executa `OPTIMIZE` (`compact()`) e `VACUUM` (`retention_hours=168`, `dry_run=False`) em cada tabela Delta Lake. |
| `sidralake inspect` | — | Executa 6 consultas analíticas de verificação diretamente no DuckDB e no Delta Lake Gold (Top 15 Score IMS, distribuição por Tier, validação de *Boa Esperança do Norte*, Top 10 Clusters CNAE por QL, pulso PMC × IPCA e versões `_delta_log`). |
| `sidralake insights` | `--top N`, `--uf SIGLA`, `--year ANO` | Executa consultas analíticas *one-shot* via **Polars Lazy API (`pl.scan_delta`)** diretamente nos Data Marts Delta Gold (Top municípios por IMS, maior CAGR real em 3 anos, liderança setorial CNAE e pulso do varejo por regime de consumo). |
| `sidralake test` | — | Roda toda a bateria de qualidade localmente (`ruff`, `mypy --strict`, `pytest` unitário + E2E, `dbt parse` e os 10 testes unitários SQL do dbt). |

---

## 2. Alvos do `Makefile`

Definidos em `Makefile`:

| Alvo | Comando Executado | Descrição |
| :--- | :--- | :--- |
| `make setup` | `uv sync --dev` + `uv run dbt deps ...` | Cria `.venv/` e instala dependências Python + `dbt-labs/dbt_utils`. |
| `make lint` | `ruff check src tests` + `ruff format --check src tests` | Verifica lint e formatação Python. |
| `make format` | `ruff format src tests` + `ruff check --fix src tests` | Formata e corrige automaticamente código Python. |
| `make typecheck` | `uv run mypy src` | Checagem estática de tipos em `src/`. |
| `make sql-lint` | `uv run sqlfluff lint dbt_project/models dbt_project/macros dbt_project/tests` | Linter SQL com dialeto `duckdb` e templater `dbt`. |
| `make test-unit` | `uv run pytest tests/unit -v --cov=ibge_market_intel` | Executa 15 testes unitários Python com cobertura. |
| `make test-integration` | `uv run pytest tests/integration -v` | Executa o teste de integração E2E offline completo. |
| `make test-dbt` | `dbt parse` + `dbt test --select test_type:unit` | Valida o parsing do projeto e executa os 4 testes unitários SQL declarados em YAML (`unit_tests:` em `_intermediate.yml` e `_gold.yml`). **Não** executa os testes singulares em `dbt_project/tests/`; para rodá-los após construir os modelos, execute `uv run dbt test --select test_type:singular --project-dir dbt_project --profiles-dir dbt_project` (ou `make dbt-build`). |
| `make test` | `lint` + `typecheck` + `test-unit` + `test-integration` + `test-dbt` | Executa toda a suíte padrão de qualidade. |
| `make dbt-deps` | `uv run dbt deps --project-dir dbt_project --profiles-dir dbt_project` | Instala pacotes dbt (`packages.yml`). |
| `make dbt-parse` | `uv run dbt parse ...` | Compila o `manifest.json` sem executar queries. |
| `make dbt-build` | `uv run dbt build ...` | Executa snapshots, modelos Silver/Gold, testes de dados e unit tests. |
| `make dbt-docs` | `dbt docs generate` + `dbt docs serve --port 8080` | Gera e serve o catálogo interativo do dbt Docs na porta `8080`. |
| `make dagster-dev` | `DAGSTER_HOME="$(CURDIR)/.dagster" uv run dagster dev` | Sobe a Dagster UI e daemon local. |
| `make materialize-smoke` | `uv run ibge-pipeline run --mode smoke` | Carga rápida SP/MT ponta a ponta. |
| `make materialize-full` | `uv run ibge-pipeline run --mode full` | Carga completa do Brasil (5.571 municípios). |
| `make delta-maintenance` | `uv run ibge-pipeline maintain` | Executa `OPTIMIZE` e `VACUUM` nas tabelas Delta. |
| `make inspect-gold` | `uv run ibge-pipeline inspect` | Imprime métricas analíticas da camada Gold. |

---

## 3. Variáveis de Ambiente (`PipelineSettings`)

Carregadas via `pydantic-settings` (`env_prefix="IBGE_"`, arquivo opcional `.env` em UTF-8) em `src/ibge_market_intel/config.py`:

| Variável de Ambiente | Tipo | Padrão | Descrição / Restrições |
| :--- | :--- | :--- | :--- |
| `IBGE_PROJECT_ROOT` | `Path` | Diretório raiz do repo | Raiz usada para resolver caminhos relativos padrão. |
| `IBGE_DATA_DIR` | `Path \| None` | `<project_root>/data` | Diretório base do Lakehouse local (`resolved_data_dir`). |
| `IBGE_BRONZE_DIR` | `Path \| None` | `<data_dir>/bronze` | Diretório das tabelas Delta Bronze (`resolved_bronze_dir`). |
| `IBGE_SILVER_DIR` | `Path \| None` | `<data_dir>/silver` | Diretório das tabelas Delta Silver exportadas (`resolved_silver_dir`). |
| `IBGE_GOLD_DIR` | `Path \| None` | `<data_dir>/gold` | Diretório das tabelas Delta Gold exportadas (`resolved_gold_dir`). |
| `IBGE_DUCKDB_PATH` | `Path \| None` | `<data_dir>/warehouse/ibge_market_intel.duckdb` | Arquivo do banco analítico DuckDB (`resolved_duckdb_path`). |
| `IBGE_DBT_PROJECT_DIR` | `Path \| None` | `<project_root>/dbt_project` | Diretório do projeto dbt (`resolved_dbt_project_dir`). |
| `IBGE_IBGE_BASE_URL` | `str` | `https://servicodados.ibge.gov.br/api` | URL base da API de serviços do IBGE. |
| `IBGE_MAX_CONCURRENCY` | `int` | `6` | Limite do `asyncio.Semaphore` (`1 <= x <= 20`). |
| `IBGE_REQUEST_TIMEOUT_S` | `float` | `40.0` | Timeout HTTP por requisição em segundos (`5.0 <= x <= 180.0`). |
| `IBGE_RETRY_MAX_ATTEMPTS` | `int` | `5` | Tentativas máximas com backoff exponencial + jitter (`1 <= x <= 10`). |
| `IBGE_USER_AGENT` | `str` | `ibge-market-intel/0.1.0 (+data-engineering-lakehouse)` | Cabeçalho `User-Agent` enviado nas requisições HTTP. |
| `IBGE_LOG_FORMAT` | `str` | `json` | Formato do `structlog`: `json` ou `console`. |
| `IBGE_LOG_LEVEL` | `str` | `INFO` | Nível mínimo de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `IBGE_UF_FILTER` | `list[int] \| None` | `None` | Lista JSON opcional de códigos UF IBGE (ex.: `[35, 51]`). |

> **Nota sobre `IBGE_IBGE_BASE_URL`:** Como o campo em `PipelineSettings` se chama `ibge_base_url` e o prefixo configurado é `IBGE_`, o nome exato da variável de ambiente é `IBGE_IBGE_BASE_URL`.

---

## 4. Configuração do `dbt-duckdb`

### `dbt_project/profiles.yml`

| Target | Caminho DuckDB | Threads | Extensões Carregadas | Settings |
| :--- | :--- | :---: | :--- | :--- |
| `dev` (padrão) | `{{ env_var('IBGE_DUCKDB_PATH', 'data/warehouse/ibge_market_intel.duckdb') }}` | `4` | `delta`, `parquet` | `preserve_insertion_order: false` |
| `ci` | `{{ env_var('IBGE_DUCKDB_PATH', '/tmp/ibge_market_intel_ci.duckdb') }}` | `2` | `delta`, `parquet` | — |

### Variáveis e Materializações (`dbt_project/dbt_project.yml`)

- **Schemas personalizados**: a macro `dbt_project/macros/generate_schema_name.sql` remove prefixos padrão do `target.schema`, mantendo nomes limpos: `silver`, `snapshots` e `gold`.
- **Materializações padrão**:
  - `models.ibge_market_intel.silver.staging`: `view` (tags: `silver`, `staging`)
  - `models.ibge_market_intel.silver.intermediate`: `table` (tags: `silver`, `intermediate`)
  - `snapshots.ibge_market_intel`: `target_schema: snapshots` (tags: `silver`, `scd2`)
  - `models.ibge_market_intel.gold.dimensions`: `table` (tags: `gold`, `dimension`)
  - `models.ibge_market_intel.gold.facts`: `table` (tags: `gold`, `fact`)
  - `models.ibge_market_intel.gold.marts`: `table` (tags: `gold`, `mart`, `obt`)
- **Pesos do Score IMS (`vars`)**:
  - `ims_weight_market_size`: `0.35`
  - `ims_weight_purchasing_power`: `0.30`
  - `ims_weight_dynamism`: `0.20`
  - `ims_weight_business_maturity`: `0.15`

---

## 5. Pipeline de CI (`.github/workflows/ci.yml`)

Disparado em `push` (`main`, `master`) e em todo `pull_request` no runner `ubuntu-latest`:

1. Instala `uv` com Python `3.12` (`astral-sh/setup-uv@v5`).
2. Executa `uv sync --dev` e `dbt deps`.
3. `ruff check src tests` e `ruff format --check src tests`.
4. `mypy src`.
5. `dbt parse` e `dbt test --select test_type:unit`.
6. `sqlfluff lint dbt_project/models dbt_project/macros dbt_project/tests`.
7. `pytest tests -v --cov=ibge_market_intel`.
