> 🌐 **Idioma:** **Português (BR)** | [English](../../en/how-to/tune-ims-and-add-ibge-source.md) · [Índice](../README.md)

# Como Ajustar Pesos do Score IMS e Adicionar uma Nova Fonte IBGE

Este guia reúne duas tarefas comuns de evolução do projeto: recalibrar o **Índice de Atratividade e Potencial de Mercado (`IMS`)** e integrar um **novo agregado da API SIDRA v3** de ponta a ponta.

---

## Receita 1: Recalibrar os Pesos do Score IMS

Os quatro pilares de `gold.mart_inteligencia_mercado_municipal` são controlados pelas variáveis `vars` em `dbt_project/dbt_project.yml`:

```yaml
vars:
  ims_weight_market_size: 0.35
  ims_weight_purchasing_power: 0.30
  ims_weight_dynamism: 0.20
  ims_weight_business_maturity: 0.15
```

### Opção A: Sobrescrita Pontual via CLI (Sem Editar Arquivo)

Para testar uma calibração voltada a poder de compra e tamanho de mercado sem alterar o padrão do repositório:

```bash
IBGE_BRONZE_DIR="$PWD/data/bronze" IBGE_DUCKDB_PATH="$PWD/data/warehouse/ibge_market_intel.duckdb" \
uv run dbt build \
  --select mart_inteligencia_mercado_municipal \
  --vars '{"ims_weight_market_size": 0.45, "ims_weight_purchasing_power": 0.35, "ims_weight_dynamism": 0.10, "ims_weight_business_maturity": 0.10}' \
  --project-dir dbt_project --profiles-dir dbt_project
```

### Opção B: Alteração Permanente no Projeto

1. Edite os pesos em `dbt_project/dbt_project.yml` (garantindo soma igual a `1.0` para interpretação intuitiva, embora a query já normalize pelo denominador dos pilares disponíveis).
2. Recompile o mart e valide o teste singular `assert_ims_score_bounds_and_distribution`:
   ```bash
   uv run dbt build --select mart_inteligencia_mercado_municipal --project-dir dbt_project --profiles-dir dbt_project
   ```
3. Reexporte a tabela Delta Gold e confira o novo ranking:
   ```bash
   uv run dagster asset materialize --select lakehouse/gold_delta_export -m ibge_market_intel.orchestration.definitions
   make inspect-gold
   ```

---

## Receita 2: Adicionar um Novo Agregado SIDRA do IBGE

Siga este checklist de 7 passos para incorporar uma nova tabela SIDRA (por exemplo, Pesquisa Mensal de Serviços ou Produção Agrícola Municipal) mantendo contratos, linhagem Dagster e exportação Delta:

### Passo 1: Validar Metadados Ao Vivo no IBGE

Verifique as variáveis, níveis territoriais suportados (`N1`, `N3`, `N6`), classificações e períodos disponíveis:

```bash
uv run python -c "
import json, urllib.request
ag = 5457  # exemplo: PAM
with urllib.request.urlopen(f'https://servicodados.ibge.gov.br/api/v3/agregados/{ag}/metadados') as r:
    m = json.loads(r.read())
print(m['nome'], '| niveis:', m['nivelTerritorial'])
print('vars:', [(v['id'], v['nome']) for v in m['variaveis'][:5]])
print('classificacoes:', [(c['id'], c['nome']) for c in m['classificacoes']])
"
```

### Passo 2: Declarar `AgregadoSpec` e Janela de Anos

Em `src/ibge_market_intel/ingestion/catalogs.py`:
- Crie a constante de anos (ex.: `PAM_YEARS`) e a instância `AgregadoSpec(...)`.
- Defina `chunk_by_uf=True` sempre que `nivel_territorial == "N6"` com múltiplas variáveis para evitar timeouts no SIDRA.
- Registre a nova spec em `ALL_SIDRA_SPECS`.

### Passo 3: Criar Partição, Ativo Bronze e Verificação Bloqueante

1. Em `src/ibge_market_intel/orchestration/partitions.py`, adicione `DynamicPartitionsDefinition(name="pam_years")`.
2. Em `src/ibge_market_intel/orchestration/assets_bronze.py`, crie o `@asset(key_prefix=["bronze"], name="<tabela>", ...)` reutilizando `_ingest_sidra_partition(...)`.
3. Inclua o asset em `BRONZE_ASSETS` e adicione o nome da tabela à tupla de `_make_sidra_check(...)` em `BRONZE_ASSET_CHECKS`.
4. Se quiser inclusão automática na CLI `ibge-pipeline run`, adicione `(SPEC, YEARS)` ao `plan` em `src/ibge_market_intel/cli.py`.

### Passo 4: Registrar Fonte Delta em `bronze_sources.yml`

Em `dbt_project/models/bronze_sources.yml`, adicione o bloco da nova tabela com o mesmo `asset_key` usado no Dagster:

```yaml
      - name: <tabela>
        description: "SIDRA <id>: descricao da pesquisa."
        meta:
          external_location: "delta_scan('{{ env_var('IBGE_BRONZE_DIR', 'data/bronze') }}/<tabela>')"
          dagster:
            asset_key: ["bronze", "<tabela>"]
```

### Passo 5: Criar Modelo de Preparação (*Staging*) na Camada Silver

Crie `dbt_project/models/silver/staging/stg_ibge__<tabela>.sql`:
- Leia de `{{ source('bronze_ibge', '<tabela>') }}`.
- Converta valores com `{{ parse_ibge_value('valor_bruto') }}` e `{{ parse_ibge_status('valor_bruto') }}`.
- Deduplique pela chave natural via `qualify row_number() over (... order by _ingested_at_utc desc) = 1`.
- Adicione testes de schema em `dbt_project/models/silver/staging/_staging.yml`.

### Passo 6: Modelar Gold (com Contrato Obrigatório) e Exportar para Delta

1. Crie o modelo fato/mart em `dbt_project/models/gold/facts/` ou `marts/`.
2. Registre colunas, `data_type` explícitos e `config: { contract: { enforced: true } }` em `dbt_project/models/gold/_gold.yml`.
3. Adicione o nome do modelo a `SILVER_EXPORT_TABLES` ou `GOLD_EXPORT_TABLES` em `src/ibge_market_intel/orchestration/assets_gold_export.py`.

### Passo 7: Validar Linhagem e Qualidade

Execute a verificação de compilação, SQL lint e integridade do grafo unificado Dagster + dbt:

```bash
make dbt-parse
make sql-lint
uv run python -c "
from dagster import AssetKey
from ibge_market_intel.orchestration.definitions import defs

ag = defs.resolve_asset_graph()
assert not ag.external_asset_keys, f'Fontes orfas: {ag.external_asset_keys}'

bronze_key = AssetKey(['bronze', '<tabela>'])
gold_key = AssetKey(['gold', '<modelo_gold>'])
export_key = AssetKey(['lakehouse', 'gold_delta_export'])
assert bronze_key in ag.get_ancestor_asset_keys(gold_key), 'Ativo Bronze nao alcanca modelo Gold'
assert gold_key in ag.get_ancestor_asset_keys(export_key), 'Modelo Gold nao alcanca exportacao Delta Gold'
print('OK:', len(ag.materializable_asset_keys), 'ativos conectados com linhagem ponta a ponta verificada')
"
```

Quando `external_asset_keys` estiver vazio **e** as asserções de ancestralidade até `gold_delta_export` passarem, o novo dataset estará validado ponta a ponta no grafo do Dagster.
