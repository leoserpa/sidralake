> 🌐 **Language:** [Português (BR)](../../pt-br/referencia/fontes-ibge-e-contratos.md) | **English** · [Index](../README.md)

# Reference: IBGE Sources and Data Contracts

Complete catalog of the 9 official IBGE data sources ingested by the pipeline, extraction specifications in `src/ibge_market_intel/ingestion/catalogs.py`, SIDRA special codes, and Pydantic/Pandera data contracts.

---

## 1. Catalog of the 9 Official IBGE Sources

| Bronze Table | Endpoint / Aggregate | Territorial Level | Extracted Variables / Fields | Classifications | Default Window | Chunking Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `localidades` | `GET /v1/localidades/municipios` | `5,571` municipalities | `id`, `nome`, `regiao-imediata`, `regiao-intermediaria`, `UF`, `regiao`, optional `microrregiao` | — | Reference snapshot | Single request |
| `cnae_secoes` | `GET /v2/cnae/secoes` | National (`21` sections) | `id` (`A`–`U`), `descricao`, `observacoes` | Mapped to `12762` | Reference snapshot | Single request |
| `pib_municipal` | SIDRA `5938` (annual) | `N6` (Municipalities) | `37` (GDP), `543` (Net taxes), `498` (Total GVA), `513` (Agri), `517` (Industry), `6575` (Private services), `525` (Public adm.) | — | Dynamic (`min_year=2018`) | `chunk_by_uf=True` (`N6[N3[uf]]`) |
| `censo_populacao` | SIDRA `4714` (annual) | `N6` (Municipalities) | `93` (Resident population), `6318` (Area km²), `614` (Density hab/km²) | — | Dynamic (`min_year=2022`) | `N6[all]` |
| `estimativa_populacao` | SIDRA `6579` (annual) | `N6` (Municipalities) | `9324` (Estimated resident population) | — | Dynamic (`min_year=2018`) | `N6[all]` |
| `cempre_municipal` | SIDRA `9509` (annual, new series) | `N6` (Municipalities) | `706` (Local units), `367` (Active firms), `707` (Total employed), `708` (Salaried), `5944` (Avg salaried), `662` (Payroll k BRL), `1606` (Avg wage MW), `10143` (Avg wage BRL) | — | Dynamic (`min_year=2022`) | `chunk_by_uf=True` (`N6[N3[uf]]`) |
| `cempre_setorial_uf` | SIDRA `9418` (annual, new series) | `N3` (27 States) | `2585` (Firms), `707` (Total employed), `708` (Salaried), `662` (Payroll k BRL) | `12762` (`21` CNAE sections) | Dynamic (`min_year=2022`) | `N3[all]` per year |
| `ipca_mensal` | SIDRA `1737` (monthly) | `N1` (Brazil) | `2266` (Index number), `63` (MoM %), `2263` (3m %), `2264` (6m %), `69` (YTD %), `2265` (12m %) | — | Dynamic (`min_year=2018`) | `N1[all]` (12 months/year) |
| `pmc_varejo_uf` | SIDRA `8883` (monthly) | `N3` (27 States) | `7169` (Index 2022=100), `7170` (SA Index), `11708` (MoM SA %), `11709` (YoY %), `11710` (YTD %), `11711` (12m %) | `11046` (2 index types) + `85` (14 activities) | Dynamic (`min_year=2020`) | `chunk_months_half_year=True` (6 months/req) |
| `pms_servicos_uf` | SIDRA `5906` (monthly) | `N3` (27 States) | `7167` (Index 2022=100), `7168` (SA Index), `11623` (MoM SA %), `11624` (YoY %), `11625` (YTD %), `11626` (12m %) | `11046` (2 index types: revenue & volume) | Dynamic (`min_year=2020`) | `N3[all]` (12 months/year) |
| `pnad_desocupacao_uf` | SIDRA `4099` (quarterly) | `N3` (27 States) | `4099` (Unemployment %), `4114` (Unemp. + Underemp.), `4116` (Unemp. + Potential), `4118` (Composite underutilization) | — | Dynamic (`min_year=2018`) | `N3[all]` (4 quarters/year) |
| `pnad_rendimento_uf` | SIDRA `5436` (quarterly) | `N3` (27 States) | `5933` (Average real monthly earnings across all jobs) | `2` (Sex: Total, Men, Women) | Dynamic (`min_year=2018`) | `N3[all]` (4 quarters/year) |

---

## 2. Mapped SIDRA Classifications

### CNAE 2.0 Sections in Classification `12762` (`CNAE_SIDRA_SECOES_12762`)

`A=116830`, `B=116880`, `C=116910`, `D=117296`, `E=117307`, `F=117329`, `G=117363`, `H=117484`, `I=117543`, `J=117555`, `K=117608`, `L=117666`, `M=117673`, `N=117714`, `O=117774`, `P=117788`, `Q=117810`, `R=117838`, `S=117861`, `T=117888`, `U=117892`.

### PMC — Index Types (`11046`) and 14 Retail Activities (`85`)

- **Index types (`11046`)**: `56735` (`RECEITA_NOMINAL`), `56736` (`VOLUME_VENDAS`).
- **Activities (`85`, `PMC_ATIVIDADES_85`)**: `90671` (Fuels & lubricants), `90672` (Hypermarkets, supermarkets, food, beverages & tobacco), `103154` (Hypermarkets & supermarkets), `90673` (Textiles, apparel & footwear), `2759` (Furniture & home appliances), `31555` (Furniture), `31556` (Home appliances), `103155` (Pharmaceuticals, medical, orthopedic, perfumery & cosmetics), `103156` (Books, newspapers, magazines & stationery), `103157` (Office, IT & communication equipment), `103158` (Other personal & household goods), `103159` (Vehicles, motorcycles, parts & accessories), `2762` (Construction materials), `56741` (Specialized wholesale food, beverages & tobacco).

---

## 3. SIDRA Special Token Semantics

Handled centrally by `dbt_project/macros/parse_ibge_numeric.sql` (`parse_ibge_value` and `parse_ibge_status`):

| Raw Value (`valor_bruto`) | Numeric Value (`valor_numerico`) | Status (`status_valor_ibge`) | Official IBGE Meaning |
| :--- | :--- | :--- | :--- |
| Valid number (e.g., `104.5`) | `double` | `VALIDO` | Standard measured numeric value. |
| `"-"` | `0.0::double` | `ZERO_EXATO` | Exact zero (not a rounded value). |
| `".."` | `NULL::double` | `NAO_SE_APLICA` | Not applicable to this breakdown. |
| `"..."` | `NULL::double` | `NAO_DISPONIVEL` | Data not available / not collected yet. |
| `"X"` | `NULL::double` | `SIGILO_ESTATISTICO` | Suppressed to preserve respondent confidentiality. |
| `""` or `NULL` | `NULL::double` | `AUSENTE` | Missing / null field in response. |
| Any other string | `NULL::double` | `INVALIDO` | Unexpected token (blocked upstream in Bronze by Pandera). |

---

## 4. Data Contracts (Ingestion → Bronze)

### 4.1 Pydantic v2 Contracts (`src/ibge_market_intel/ingestion/schemas.py`)

- **`LocalidadeMunicipioPayload`**: validates `id`, `nome`, `regiao-imediata` (`id`, `nome`, `regiao-intermediaria.UF.regiao`), and accepts `microrregiao: None` (handling *Boa Esperança do Norte/MT*).
- **`CnaeSecaoPayload`**: validates `id`, `descricao`, and `observacoes`.
- **`SidraVariavelPayload`**: validates nested `variavel -> resultados -> classificacoes -> series -> serie[periodo]` responses and flattens into the canonical 16-column `SIDRA_BRONZE_SCHEMA` (sorting classifications by `int(c.id)` for deterministic mapping).

### 4.2 Technical Audit Columns (`DeltaLakeWriter`)

Injected on every write via `attach_audit_columns`:

| Column | Polars Type | Description |
| :--- | :--- | :--- |
| `_ingestion_id` | `String` | Execution identifier (Dagster `run_id` or CLI run ID). |
| `_ingested_at_utc` | `String` | UTC ISO-8601 timestamp of the write transaction. |
| `_source_url` | `String` | Source API URL (or `duckdb://<schema>.<table>` for exports). |
| `_payload_hash` | `String` | Deterministic sorted SHA-256 hash over all business columns. |

### 4.3 Pandera Contracts (`src/ibge_market_intel/quality/contracts.py`)

Enforced prior to Bronze writes in the CLI and as blocking `@asset_check(..., blocking=True)` in Dagster:

- **`BronzeLocalidadesSchema`**: unique integer `municipio_id` in `[1100000, 5399999]`, `uf_sigla` in the 27 states (`VALID_UF_SIGLAS`), `regiao_sigla` in `["N", "NE", "SE", "S", "CO"]`, `regiao_imediata_id > 0`, nullable `microrregiao_*` / `mesorregiao_*`.
- **`BronzeCnaeSchema`**: unique `secao_codigo` (`^[A-U]$`), unique `categoria_sidra_12762_id > 0`.
- **`BronzeSidraSchema` + `validate_sidra_contract`**:
  - `localidade_id` (`^\d{1,7}$`), `nivel_territorial` in `["N1", "N2", "N3", "N6", "N7", "N8", "N9"]`, `periodo_id` (`^\d{4}(\d{2})?$`), `ano_referencia` (`^\d{4}$`), nullable `unidade`.
  - Enforces composite natural-key uniqueness across `(agregado_id, variavel_id, localidade_id, classificacao_1_id, categoria_1_id, classificacao_2_id, categoria_2_id, periodo_id)`.
  - Enforces `_IBGE_VALUE_REGEX` (`^(?:-|\.\.|\.\.\.|X||-?\d+(?:[.,]\d+)?)$`).
  - Produces a `QualityReport` recording `row_count`, `distinct_localidades`, `duplicate_key_rows`, `invalid_value_rows`, `secrecy_x_rate`, `unavailable_rate`, and `exact_zero_rate`.
