> 🌐 **Idioma:** **Português (BR)** | [English](../../en/reference/ibge-sources-and-contracts.md) · [Índice](../README.md)

# Referência: Fontes IBGE e Contratos de Dados

Catálogo completo das 12 fontes oficiais do IBGE consumidas pelo pipeline, especificações de extração em `src/ibge_market_intel/ingestion/catalogs.py`, códigos especiais SIDRA e contratos de validação Pydantic/Pandera.

---

## 1. Catálogo das 12 Fontes Oficiais do IBGE

| Tabela Bronze | Endpoint / Agregado | Nível Territorial | Variáveis / Campos Extraídos | Classificações | Janela Padrão | Estratégia de Chunking |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `localidades` | `GET /v1/localidades/municipios` | `5.571` municípios | `id`, `nome`, `regiao-imediata`, `regiao-intermediaria`, `UF`, `regiao`, `microrregiao` (opcional) | — | Snapshot cadastral | Requisição única |
| `cnae_secoes` | `GET /v2/cnae/secoes` | Nacional (`21` seções) | `id` (`A`–`U`), `descricao`, `observacoes` | Mapeada p/ `12762` | Snapshot cadastral | Requisição única |
| `pib_municipal` | SIDRA `5938` (anual) | `N6` (Municípios) | `37` (PIB), `543` (Impostos líq.), `498` (VAB Total), `513` (Agro), `517` (Indústria), `6575` (Serviços priv.), `525` (Adm. Pública) | — | Dinâmica (`min_year=2018`) | `chunk_by_uf=True` (`N6[N3[uf]]`) |
| `censo_populacao` | SIDRA `4714` (anual) | `N6` (Municípios) | `93` (População residente), `6318` (Área km²), `614` (Densidade hab/km²) | — | Dinâmica (`min_year=2022`) | `N6[all]` |
| `estimativa_populacao` | SIDRA `6579` (anual) | `N6` (Municípios) | `9324` (População residente estimada) | — | Dinâmica (`min_year=2018`) | `N6[all]` |
| `cempre_municipal` | SIDRA `9509` (anual, nova série) | `N6` (Municípios) | `706` (Unid. locais), `367` (Empresas atuantes), `707` (Pessoal ocupado), `708` (Assalariado), `5944` (Assal. médio), `662` (Massa salarial Mil R$), `1606` (Salário SM), `10143` (Salário R$) | — | Dinâmica (`min_year=2022`) | `chunk_by_uf=True` (`N6[N3[uf]]`) |
| `cempre_setorial_uf` | SIDRA `9418` (anual, nova série) | `N3` (27 UFs) | `2585` (Empresas), `707` (Pessoal ocupado), `708` (Assalariado), `662` (Massa salarial Mil R$) | `12762` (`21` seções CNAE) | Dinâmica (`min_year=2022`) | `N3[all]` por ano |
| `ipca_mensal` | SIDRA `1737` (mensal) | `N1` (Brasil) | `2266` (Número-índice), `63` (Var. mensal), `2263` (3m), `2264` (6m), `69` (Ano), `2265` (12m) | — | Dinâmica (`min_year=2018`) | `N1[all]` (12 meses/ano) |
| `pmc_varejo_uf` | SIDRA `8883` (mensal) | `N3` (27 UFs) | `7169` (Índice 2022=100), `7170` (Índice SA), `11708` (MoM SA), `11709` (YoY), `11710` (Acum. Ano), `11711` (Acum. 12m) | `11046` (2 tipos índice) + `85` (14 atividades) | Dinâmica (`min_year=2020`) | `chunk_months_half_year=True` (6 meses/req) |
| `pms_servicos_uf` | SIDRA `5906` (mensal) | `N3` (27 UFs) | `7167` (Índice 2022=100), `7168` (Índice SA), `11623` (MoM SA), `11624` (YoY), `11625` (Acum. Ano), `11626` (Acum. 12m) | `11046` (2 tipos índice: receita e volume) | Dinâmica (`min_year=2020`) | `N3[all]` (12 meses/ano) |
| `pnad_desocupacao_uf` | SIDRA `4099` (trimestral) | `N3` (27 UFs) | `4099` (Desocupação %), `4114` (Desoc. + Suboc.), `4116` (Desoc. + Potencial), `4118` (Subutilização composta) | — | Dinâmica (`min_year=2018`) | `N3[all]` (4 trimestres/ano) |
| `pnad_rendimento_uf` | SIDRA `5436` (trimestral) | `N3` (27 UFs) | `5933` (Rendimento médio mensal real habitual em todos os trabalhos) | `2` (Sexo: Total, Homens, Mulheres) | Dinâmica (`min_year=2018`) | `N3[all]` (4 trimestres/ano) |

---

## 2. Classificações SIDRA Mapeadas

### Seções CNAE 2.0 na Classificação `12762` (`CNAE_SIDRA_SECOES_12762`)

`A=116830`, `B=116880`, `C=116910`, `D=117296`, `E=117307`, `F=117329`, `G=117363`, `H=117484`, `I=117543`, `J=117555`, `K=117608`, `L=117666`, `M=117673`, `N=117714`, `O=117774`, `P=117788`, `Q=117810`, `R=117838`, `S=117861`, `T=117888`, `U=117892`.

### PMC — Tipos de Índice (`11046`) e 14 Atividades (`85`)

- **Tipos de índice (`11046`)**: `56735` (`RECEITA_NOMINAL`), `56736` (`VOLUME_VENDAS`).
- **Atividades (`85`, `PMC_ATIVIDADES_85`)**: `90671` (Combustíveis e lubrificantes), `90672` (Hipermercados, supermercados, alimentos, bebidas e fumo), `103154` (Hipermercados e supermercados), `90673` (Tecidos, vestuário e calçados), `2759` (Móveis e eletrodomésticos), `31555` (Móveis), `31556` (Eletrodomésticos), `103155` (Artigos farmacêuticos, médicos, ortopédicos, perfumaria e cosméticos), `103156` (Livros, jornais, revistas e papelaria), `103157` (Equipamentos de escritório, informática e comunicação), `103158` (Outros artigos de uso pessoal e doméstico), `103159` (Veículos, motocicletas, partes e peças), `2762` (Material de construção), `56741` (Atacado especializado em alimentos, bebidas e fumo).

---

## 3. Semântica de Códigos Especiais do SIDRA

Tratada pela macro `dbt_project/macros/parse_ibge_numeric.sql` (`parse_ibge_value` e `parse_ibge_status`):

| Valor Bruto (`valor_bruto`) | Valor Numérico (`valor_numerico`) | Status (`status_valor_ibge`) | Significado Oficial IBGE |
| :--- | :--- | :--- | :--- |
| Número válido (ex.: `104.5`) | `double` | `VALIDO` | Dado numérico apurado normalmente. |
| `"-"` | `0.0::double` | `ZERO_EXATO` | Zero absoluto (não resultante de arredondamento). |
| `".."` | `NULL::double` | `NAO_SE_APLICA` | Dado não se aplica ao recorte. |
| `"..."` | `NULL::double` | `NAO_DISPONIVEL` | Dado ainda não disponível ou não coletado. |
| `"X"` | `NULL::double` | `SIGILO_ESTATISTICO` | Dado omitido para evitar desidentificação de informantes. |
| `""` ou `NULL` | `NULL::double` | `AUSENTE` | Campo ausente/nulo na resposta. |
| Qualquer outro texto | `NULL::double` | `INVALIDO` | Token inesperado (bloqueado antes na Bronze pelo Pandera). |

---

## 4. Contratos de Dados (Ingestão → Bronze)

### 4.1 Contratos Pydantic v2 (`src/ibge_market_intel/ingestion/schemas.py`)

- **`LocalidadeMunicipioPayload`**: valida `id`, `nome`, `regiao-imediata` (`id`, `nome`, `regiao-intermediaria.UF.regiao`) e aceita `microrregiao: None` (caso real de *Boa Esperança do Norte/MT*).
- **`CnaeSecaoPayload`**: valida `id`, `descricao` e `observacoes`.
- **`SidraVariavelPayload`**: valida resposta aninhada `variavel -> resultados -> classificacoes -> series -> serie[periodo]` e normaliza no schema canônico `SIDRA_BRONZE_SCHEMA` (`16` colunas, ordenando classificações por `int(c.id)` para determinismo).

### 4.2 Colunas Técnicas de Auditoria (`DeltaLakeWriter`)

Injetadas automaticamente em toda escrita via `attach_audit_columns`:

| Coluna | Tipo Polars | Descrição |
| :--- | :--- | :--- |
| `_ingestion_id` | `String` | ID da execução (`run_id` do Dagster ou da CLI). |
| `_ingested_at_utc` | `String` | Timestamp ISO-8601 em UTC da gravação. |
| `_source_url` | `String` | URL de origem da extração (ou `duckdb://<schema>.<table>` nos exports). |
| `_payload_hash` | `String` | Hash SHA-256 determinístico ordenado sobre todas as colunas de negócio. |

### 4.3 Contratos Pandera (`src/ibge_market_intel/quality/contracts.py`)

Executados antes de gravar pela CLI e como `@asset_check(..., blocking=True)` no Dagster:

- **`BronzeLocalidadesSchema`**: `municipio_id` inteiro único em `[1100000, 5399999]`, `uf_sigla` nas 27 UFs (`VALID_UF_SIGLAS`), `regiao_sigla` em `["N", "NE", "SE", "S", "CO"]`, `regiao_imediata_id > 0`, `microrregiao_*` e `mesorregiao_*` anuláveis.
- **`BronzeCnaeSchema`**: `secao_codigo` único (`^[A-U]$`), `categoria_sidra_12762_id > 0` único.
- **`BronzeSidraSchema` + `validate_sidra_contract`**:
  - `localidade_id` (`^\d{1,7}$`), `nivel_territorial` em `["N1", "N2", "N3", "N6", "N7", "N8", "N9"]`, `periodo_id` (`^\d{4}(\d{2})?$`), `ano_referencia` (`^\d{4}$`), `unidade` anulável.
  - Unicidade garantida na chave natural composta `(agregado_id, variavel_id, localidade_id, classificacao_1_id, categoria_1_id, classificacao_2_id, categoria_2_id, periodo_id)`.
  - Validação regex `_IBGE_VALUE_REGEX` (`^(?:-|\.\.|\.\.\.|X||-?\d+(?:[.,]\d+)?)$`).
  - Emite `QualityReport` com `row_count`, `distinct_localidades`, `duplicate_key_rows`, `invalid_value_rows`, `secrecy_x_rate`, `unavailable_rate` e `exact_zero_rate`.
