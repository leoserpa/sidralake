> 🌐 **Idioma:** **Português (BR)** | [English](../../en/how-to/run-quality-gates-and-ci.md) · [Índice](../README.md)

# Como Executar Portões de Qualidade e Diagnosticar Falhas de CI

Este guia mostra como rodar os mesmos portões de qualidade do pipeline de CI localmente e como diagnosticar rapidamente as falhas mais comuns.

---

## 1. Executar os Portões de Qualidade Localmente

Rode a bateria padrão do `Makefile`:

```bash
make test
```

Esse alvo executa em sequência:
1. `make lint` — `ruff check src tests` e `ruff format --check src tests`
2. `make typecheck` — `mypy src`
3. `make test-unit` — `pytest tests/unit -v --cov=ibge_market_intel` (15 testes unitários com `respx` e fixtures reais)
4. `make test-integration` — `pytest tests/integration -v` (teste E2E offline completo com Delta Lake, `dbt build` e SCD Type 2)
5. `make test-dbt` — `dbt parse` + `dbt test --select test_type:unit` (4 testes unitários nativos do dbt em SQL)

Para validar também o estilo SQL do dbt (como executado no `.github/workflows/ci.yml`), rode:

```bash
make sql-lint
```

---

## 2. Diagnosticar e Resolver Falhas Comuns

### 2.1 Disjuntor (*Circuit Breaker*) Pandera Acionado na Camada Bronze

**Sintoma:** `ValueError` ou `RuntimeError: Circuit Breaker Pandera em bronze/<tabela> (<ano>)` indicando falha de `BronzeSidraSchema`, `BronzeLocalidadesSchema` ou `BronzeCnaeSchema`.

**Diagnóstico e ação:**
- Inspecione os campos da mensagem de erro (`duplicate_key_rows`, `invalid_value_rows` e amostras listadas em `failure case examples`).
- **Se `invalid_value_rows > 0`**: o IBGE retornou um token novo em `valor_bruto` além de números e `{"-", "..", "...", "X", ""}`. Confirme o significado nos metadados do agregado (`/api/v3/agregados/{id}/metadados`) antes de atualizar `_IBGE_VALUE_REGEX` em `src/ibge_market_intel/quality/contracts.py` e a macro `dbt_project/macros/parse_ibge_numeric.sql`.
- **Se `duplicate_key_rows > 0`**: verifique `flatten_sidra_response` em `src/ibge_market_intel/ingestion/schemas.py` para checar se o agregado introduziu uma terceira classificação não mapeada em `classificacao_1_id`/`classificacao_2_id`.
- **Se uma coluna opcional mudou na API**: valide o payload Pydantic correspondente em `schemas.py` e ajuste o campo em `contracts.py`.

### 2.2 Quebra de Contrato de Modelo Obrigatório no dbt

**Sintoma:** `dbt build` falha com erro de contrato em `dim_*` ou `fct_*` (`Contract Error: column mismatch` ou `data_type mismatch`).

**Diagnóstico e ação:**
- Compare o `SELECT` final do modelo SQL em `dbt_project/models/gold/dimensions/` ou `facts/` com a definição declarada em `dbt_project/models/gold/_gold.yml`.
- Todos os modelos com `contract: { enforced: true }` exigem `cast(... as <tipo>)` explícito no SQL batendo 1:1 com nome, ordem/existência e tipo (`varchar`, `integer`, `bigint`, `double`, `date`, `timestamp`, `boolean`) no `_gold.yml`.
- Nunca remova `enforced: true` para silenciar erro; atualize o SQL ou faça uma alteração consciente e documentada no contrato.

### 2.3 Falha nos Testes Singulares de Reconciliação Contábil

**Sintoma:** falha em um dos 4 testes em `dbt_project/tests/`:
- `assert_pib_contabilidade_consistente.sql` (`|PIB - (VAB_total + Impostos)| > max(5.0, 0.01 * |PIB|)`)
- `assert_vab_setores_soma_total.sql` (`|VAB_total - soma(4 setores)| > max(5.0, 0.01 * |VAB_total|)`)
- `assert_ims_score_bounds_and_distribution.sql` (`ims_score_0_100` fora de `[0, 100]`, `NaN`/`Inf` ou nulo quando PIB + CEMPRE estão presentes)
- `assert_no_orphan_municipios_gold.sql` (município presente nos fatos sem registro `is_current = true` em `dim_geografia`)

**Diagnóstico e ação:**
- Execute o SQL do teste diretamente no DuckDB (`uv run dbt show --inline ...` ou via Python `duckdb.connect`) para listar os códigos `codigo_ibge_municipio` e `ano_referencia` ofensores.
- Em caso de municípios órfãos, atualize primeiro o cadastro `bronze/localidades` e rode `dbt snapshot` (`snap_ibge_municipios`) antes de reprocessar os fatos.

### 2.4 Erro de Bloqueio de Concorrência no DuckDB

**Sintoma:** `IO Error: Could not set lock on file ".../ibge_market_intel.duckdb": Conflicting lock is held in /usr/bin/python3.12`.

**Causa e resolução:**
- O DuckDB permite apenas **um processo escritor por vez** sobre o mesmo arquivo `.duckdb`. Esse erro ocorre quando `sqlfluff` (com templater dbt), `dbt build`, `dagster dev` ou um teste rodam simultaneamente apontando para o mesmo arquivo.
- Aguarde o processo concorrente finalizar (ou encerre processos travados) e execute um comando por vez.
- Para testes ou execuções isoladas em paralelo, defina um caminho separado via `IBGE_DUCKDB_PATH`:
  ```bash
  IBGE_DUCKDB_PATH=/tmp/ibge_sandbox.duckdb uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project
  ```
