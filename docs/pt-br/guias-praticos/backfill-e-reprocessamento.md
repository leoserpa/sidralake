> 🌐 **Idioma:** **Português (BR)** | [English](../../en/how-to/backfill-and-reprocess.md) · [Índice](../README.md)

# Como Fazer Backfill, Reprocessamento e Manutenção Delta Lake

Este guia apresenta receitas práticas para executar cargas completas, reprocessar partições individuais de forma idempotente, inspecionar histórico via Delta Time Travel e compactar arquivos no Lakehouse.

---

## 1. Executar a Carga Completa do Brasil

Para ingerir todos os **5.571 municípios** na janela dinâmica (`2018+`, descoberta na API do IBGE), rodar o `dbt build` completo e exportar todas as camadas para Delta Lake:

```bash
make materialize-full
```

---

## 2. Restringir a Carga para UFs Específicas (Desenvolvimento / Homologação)

Use a variável de ambiente `IBGE_UF_FILTER` (lista JSON de códigos IBGE de UF) antes de rodar o pipeline:

```bash
IBGE_UF_FILTER='[35, 33]' uv run ibge-pipeline run --mode full
```

O filtro é aplicado automaticamente às tabelas municipais (`N6`), estaduais (`N3`) e ao cadastro de localidades.

---

## 3. Reprocessar ou Fazer Backfill de uma Única Partição Anual

Todas as tabelas SIDRA na camada Bronze são particionadas por `ano_referencia` e gravadas via `replace_where` (`predicate="ano_referencia = '<ano>'"`), garantindo zero duplicação.

### Opção A: Via Dagster UI (Backfill Declarativo)

1. Inicie a interface com `make dagster-dev`.
2. Abra **Assets** e selecione o asset desejado (por exemplo, `bronze/pib_municipal` ou `bronze/cempre_municipal`).
3. Clique em **Materialize** e escolha apenas o ano (ou intervalo de anos) desejado na tela de partições.
4. Após a conclusão e aprovação do **Asset Check** bloqueante do Pandera, dispare o job `dbt_medallion_job` para atualizar Silver, Gold e exportação Delta.

### Opção B: Programaticamente em Python (Recarga Cirúrgica)

Execute o snippet abaixo substituindo a especificação (`PIB_MUNICIPAL_SPEC`) e o ano alvo (`"2023"`):

```bash
uv run python - << 'EOF'
import asyncio
from ibge_market_intel.config import get_settings
from ibge_market_intel.ingestion.catalogs import PIB_MUNICIPAL_SPEC
from ibge_market_intel.ingestion.client import IBGEAsyncClient
from ibge_market_intel.ingestion.delta_writer import DeltaLakeWriter
from ibge_market_intel.quality.contracts import validate_sidra_contract

async def backfill_year(ano: str) -> None:
    settings = get_settings()
    settings.ensure_directories()
    async with IBGEAsyncClient(settings) as client:
        res = await client.fetch_agregado_for_year(PIB_MUNICIPAL_SPEC, ano=ano, uf_codes=settings.uf_filter)
    report = validate_sidra_contract(res.df, PIB_MUNICIPAL_SPEC.table_name)
    if not report.passed:
        raise RuntimeError(report.error_message)
    writer = DeltaLakeWriter(settings.resolved_bronze_dir)
    out = writer.write_partition_overwrite(
        res.df,
        PIB_MUNICIPAL_SPEC.table_name,
        partition_col="ano_referencia",
        partition_value=ano,
        ingestion_id=f"manual-backfill-{ano}",
        source_url=res.source_urls[0] if res.source_urls else "",
    )
    print(f"Particao {ano} gravada: delta_v={out.delta_version}, rows={out.rows_written}")

asyncio.run(backfill_year("2023"))
EOF
```

Em seguida, recompile as camadas analíticas e reexporte para Delta:

```bash
make dbt-build
uv run dagster asset materialize --select lakehouse/silver_delta_export,lakehouse/gold_delta_export -m ibge_market_intel.orchestration.definitions
```

> **Dica:** Para carregar um ano fora da janela padrão (ex.: PIB `2017`), inclua `"2017"` em `PIB_YEARS` em `src/ibge_market_intel/ingestion/catalogs.py` para registrá-lo também em `PIB_PARTITIONS` no Dagster.

---

## 4. Auditar Histórico e Consultar Versões Anteriores (Viagem no Tempo / *Time Travel*)

Cada operação em `data/bronze/`, `data/silver/` ou `data/gold/` cria uma nova transação imutável no `_delta_log`.

Para listar o histórico de commits e ler uma versão anterior:

```bash
uv run python - << 'EOF'
from deltalake import DeltaTable
import polars as pl

path = "data/bronze/pib_municipal"
dt = DeltaTable(path)
print("Versao atual:", dt.version())
for entry in dt.history(limit=5):
    print(entry.get("version"), entry.get("timestamp"), entry.get("operation"))

# Leitura da versao 0 para comparacao
dt_v0 = DeltaTable(path, version=0)
df_v0 = pl.from_arrow(dt_v0.to_pyarrow_table())
print("Linhas na versao 0:", df_v0.height)
EOF
```

---

## 5. Compactar Arquivos Pequenos e Limpar Arquivos Órfãos (`OPTIMIZE` + `VACUUM`)

Reprocessamentos frequentes de partições geram múltiplos arquivos Parquet e versões antigas no disco. Execute a rotina de manutenção ACID do Lakehouse:

```bash
make delta-maintenance
```

Esse comando percorre `data/bronze/`, `data/silver/` e `data/gold/` executando:
- `dt.optimize.compact()` — consolida arquivos pequenos em arquivos Parquet otimizados para leitura.
- `dt.vacuum(retention_hours=168, dry_run=False, enforce_retention_duration=True)` — remove arquivos físicos referenciados apenas por transações com mais de 7 dias (168 horas), preservando a janela de Time Travel recente.

Você também pode disparar o job `delta_maintenance_job` manualmente na aba **Jobs** da Dagster UI.
