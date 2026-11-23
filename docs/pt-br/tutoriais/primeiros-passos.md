> 🌐 **Idioma:** **Português (BR)** | [English](../../en/tutorials/getting-started.md) · [Índice](../README.md)

# Primeiros Passos: do Zero à Camada Gold

Neste tutorial prático, você vai preparar o ambiente local, executar o pipeline **IBGE Market Intelligence 360** no modo *smoke* contra as APIs reais do IBGE, consultar os resultados diretamente no Delta Lake via DuckDB e explorar a linhagem completa na **Dagster UI** e no **dbt Docs**.

---

## Pré-requisitos

Certifique-se de ter instalado na sua máquina:
- **Sistema operacional**: Linux ou macOS
- **Python**: `>=3.12,<3.14`
- **uv**: gerenciador de ambientes e pacotes Python (`uv --version`)
- **git**: para dependências do dbt e controle de versão (`git --version`)
- **Acesso HTTP**: conectividade de saída para `https://servicodados.ibge.gov.br/api`

---

## Passo 1: Preparar o Ambiente e Dependências

Na raiz do repositório (`projeto ibge`), execute:

```bash
make setup
```

Esse comando executa duas ações:
1. `uv sync --dev` — cria o ambiente virtual `.venv/` e instala as dependências de produção e desenvolvimento definidas em `pyproject.toml`.
2. `uv run dbt deps --project-dir dbt_project --profiles-dir dbt_project` — instala o pacote `dbt-labs/dbt_utils` em `dbt_project/dbt_packages/`.

Para confirmar que os executáveis foram instalados corretamente, valide o CLI:

```bash
uv run ibge-pipeline --help
```

Você verá os subcomandos `run`, `maintain` e `inspect`.

---

## Passo 2: Executar a Primeira Carga (Modo Rápido)

Em vez de baixar os 5.571 municípios de 2018 a 2026 logo no primeiro contato, rode o modo `smoke`, que extrai dados reais das UFs **São Paulo (`35`)** e **Mato Grosso (`51`)** em uma janela reduzida:

```bash
make materialize-smoke
```

Durante a execução, você acompanhará os logs estruturados das três fases:
1. **Ingestão Bronze (`_ingest_all_bronze`)**: requisições HTTP assíncronas às APIs de Localidades, CNAE 2.0 e SIDRA, validação pelos contratos **Pandera** e escrita particionada em `data/bronze/<tabela>`.
2. **Transformação `dbt build`**: criação das views *staging* e tabelas *intermediate* (`silver`), snapshots **SCD Type 2** (`snapshots`), Star Schema + Data Marts OBT (`gold`) e execução automática dos testes de schema, reconciliação contábil e `unit_tests`.
3. **Exportação ACID (`silver_delta_export` e `gold_delta_export`)**: gravação das tabelas curadas em `data/silver/` e `data/gold/` no formato aberto **Delta Lake**.

> **Nota:** Se você já executou uma carga completa (`make materialize-full`), rodar `make materialize-smoke` sobrescreverá as tabelas finais com o recorte SP/MT. Basta rodar `make materialize-full` novamente para restaurar o Brasil inteiro.

---

## Passo 3: Inspecionar a Camada Gold

Execute o comando de inspeção integrado para ver um resumo imediato das tabelas analíticas:

```bash
make inspect-gold
```

A saída no terminal exibe:
- **Top 15 municípios** ordenados pelo Score `ims_score_0_100`
- **Distribuição por Tier** (`Tier 1 - Polo Nacional` até `Tier 4 - Local / Nicho`)
- Presença de *Boa Esperança do Norte - MT* (`5101837`) em `gold.dim_geografia`
- **Top clusters setoriais estaduais** por Quociente Locacional (`QL`)
- **Pulso do varejo (PMC × IPCA)** na última competência mensal disponível
- Contagem de linhas e versão Delta (`_delta_log`) dos 3 Data Marts Gold

Agora execute uma consulta SQL ad-hoc lendo diretamente a tabela **Delta Lake** da camada Gold via DuckDB (sem depender do arquivo `.duckdb` aberto em modo escrita):

```bash
uv run python -c "
import duckdb
con = duckdb.connect()
con.execute('LOAD delta;')
rows = con.execute('''
    SELECT
        rank_nacional_ims,
        nome_municipio,
        sigla_uf,
        ano_referencia,
        ims_score_0_100,
        tier_mercado
    FROM delta_scan('data/gold/mart_inteligencia_mercado_municipal')
    WHERE is_ultimo_ano_completo
    ORDER BY rank_nacional_ims
    LIMIT 5
''').fetchall()
for r in rows:
    print(r)
"
```

---

## Passo 4: Explorar Linhagem e Catálogo Visualmente

### 4.1 Interface Dagster (Orquestração, Partições e Verificações)

Inicie o servidor local do Dagster:

```bash
make dagster-dev
```

Abra o endereço exibido no terminal (por padrão `http://127.0.0.1:3000`). Na interface:
- Acesse **Assets → Global Asset Lineage** para visualizar o grafo completo de **39 assets** conectando `bronze/*` → `silver/*` → `gold/*` → `lakehouse/*`.
- Clique em qualquer asset da Bronze (como `bronze/pib_municipal`) para inspecionar as partições por `ano_referencia`, métricas de execução (`rows_written`, `delta_version`, `payload_hash`) e o status dos **Asset Checks** do Pandera.
- Acesse **Automation** para visualizar o sensor `ibge_new_period_sensor` e os *schedules* mensais/semanais.

Encerre o servidor com `Ctrl+C` quando terminar.

### 4.2 dbt Docs (Catálogo de Colunas e Linhagem SQL)

Gere e sirva a documentação interativa do dbt:

```bash
make dbt-docs
```

Abra `http://127.0.0.1:8080` no navegador para inspecionar descrições de modelos, contratos tipados, macros e o grafo de dependências SQL entre `bronze_ibge`, `silver`, `snapshots` e `gold`. Encerre com `Ctrl+C`.

---

## Próximos Passos

Agora que você concluiu sua primeira execução de ponta a ponta:
- Para carregar todos os **5.571 municípios brasileiros** e aprender a reprocessar partições específicas, siga para [Backfill, Reprocessamento e Manutenção Delta Lake](../guias-praticos/backfill-e-reprocessamento.md).
- Para entender as decisões arquiteturais e os casos de borda reais do IBGE tratados neste pipeline, leia [Arquitetura Medalhão e Decisões de Engenharia](../explicacoes/arquitetura-medalhao-e-design.md).
