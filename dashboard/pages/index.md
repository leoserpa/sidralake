---
title: SidraLake 360° — Visão Executiva Brasil
---

```sql anos_disponiveis
select distinct ano_referencia
from sidralake.mart_inteligencia_mercado_municipal
where pib_real_mil_brl is not null
order by ano_referencia desc
```

```sql regioes_disponiveis
select 'TODAS' as nome_regiao, 0 as ordem
union all
select distinct nome_regiao, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, nome_regiao
```

```sql ufs_disponiveis
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, sigla_uf
```

```sql tiers_disponiveis
select 'TODOS' as tier_mercado, 0 as ordem
union all
select distinct tier_mercado, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, tier_mercado
```

<header class="sl-page-header">
	<div class="sl-page-heading">
		<h1 class="sl-page-title">Inteligência de Mercado 360° — Brasil</h1>
		<p class="sl-page-subtitle">5.571 municípios oficiais IBGE · Valores constantes IPCA · Destaque pré-atentivo no líder</p>
	</div>
	<div class="sl-filter-bar">
		<Dropdown data={anos_disponiveis} name=ano value=ano_referencia title="Ano" defaultValue={2023} />
		<Dropdown data={regioes_disponiveis} name=regiao value=nome_regiao title="Região" defaultValue="TODAS" />
		<Dropdown data={ufs_disponiveis} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
		<Dropdown data={tiers_disponiveis} name=tier value=tier_mercado title="Tier" defaultValue="TODOS" />
	</div>
</header>

```sql kpis_gerais
select
    count(*) as total_municipios,
    sum(populacao_residente) as populacao_total,
    sum(pib_real_mil_brl) / 1e9 as pib_real_tri,
    sum(massa_salarial_real_mil_brl) / 1e6 as massa_salarial_bi,
    sum(num_empresas_atuantes) as empresas_atuantes,
    round(avg(ims_score_0_100), 2) as ims_medio
from sidralake.mart_inteligencia_mercado_municipal
where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
```

```sql ipca_resumo_home
select
    substr(ano_mes, 5, 2) || '/' || substr(ano_mes, 1, 4) as ultima_competencia,
    round(variacao_acum_12m_pct / 100.0, 4) as ipca_12m_pct,
    round(variacao_mensal_pct / 100.0, 4) as ipca_mes_pct
from sidralake.fct_ipca_mensal
order by data_referencia desc
limit 1
```

<div class="sl-kpi-grid-5">
	<KpiCard data={kpis_gerais} value="pib_real_tri" title="PIB Real Brasil" fmt="brl_tri" icon="landmark" subtitle="Valores constantes IPCA" />
	<KpiCard data={kpis_gerais} value="populacao_total" title="População Residente" fmt="pop_mi" icon="users" subtitleCol="total_municipios" subtitleFmt="int" subtitleSuffix=" municípios no recorte" />
	<KpiCard data={kpis_gerais} value="massa_salarial_bi" title="Massa Salarial Formal" fmt="brl_bi" icon="briefcase" subtitleCol="empresas_atuantes" subtitleFmt="pop_mi" subtitleSuffix=" empresas CEMPRE" />
	<KpiCard data={kpis_gerais} value="ims_medio" title="Score IMS Médio" fmt="dec2" icon="gauge" subtitle="Escala 0–100 · 4 pilares" />
	<KpiCard data={ipca_resumo_home} value="ipca_12m_pct" title="IPCA Acum. 12m" fmt="pct2" icon="percent" subtitleCol="ultima_competencia" subtitlePrefix="Ref. " subtitle2Col="ipca_mes_pct" subtitle2Fmt="signed_pct2" subtitle2Prefix=" · " subtitle2Suffix=" mês" />
</div>

```sql top_12_ims
with base as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(ims_score_0_100, 1) as ims_score_0_100,
        row_number() over (order by ims_score_0_100 desc, pib_real_mil_brl desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
      and ims_score_0_100 is not null
      and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
      and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
    order by pos asc
    limit 10
)
select
    municipio,
    ims_score_0_100,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

```sql pib_por_regiao
with agg as (
    select
        nome_regiao as regiao,
        count(*) as municipios,
        round(sum(pib_real_mil_brl) / 1e6, 1) as pib_real_bi,
        round(avg(ims_score_0_100), 2) as ims_medio
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
      and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
    group by 1
),
ranked as (
    select
        *,
        row_number() over (order by pib_real_bi desc nulls last) as pos
    from agg
)
select
    regiao,
    municipios,
    pib_real_bi,
    ims_medio,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<BarChart
			data={top_12_ims}
			x=municipio
			y=ims_score_0_100
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0"
			leftPadding=18
			rightPadding=34
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
			title="Quais municípios lideram o Score IMS?"
			subtitle="Top 10 no recorte (0–100) · Líder em azul pré-atentivo"
		/>
	</div>
	<div class="sl-card">
		<DonutPanel data={pib_por_regiao} labelCol="regiao" valueCol="pib_real_bi" title="Como o PIB real se distribui por Região?" centerLabel="PIB Real Total" />
	</div>
</div>

```sql top_12_pib
with base as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(pib_real_mil_brl / 1e6, 1) as pib_real_bi,
        row_number() over (order by pib_real_mil_brl desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
      and pib_real_mil_brl is not null
      and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
      and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
    order by pos asc
    limit 8
)
select
    municipio,
    pib_real_bi,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

```sql regimes_varejo_home
with base as (
    select
        case regime_consumo
            when 'EXPANSAO_REAL' then 'Expansão Real'
            when 'PRESSAO_INFLACIONARIA' then 'Pressão Inflac.'
            when 'ESTABILIDADE' then 'Estabilidade'
            when 'RETRACAO' then 'Retração'
            else regime_consumo
        end as regime,
        count(*) as series
    from sidralake.mart_pulso_consumo_macro
    where ano_mes = (select max(ano_mes) from sidralake.mart_pulso_consumo_macro)
      and regime_consumo <> 'SEM_DADO'
    group by 1
),
ranked as (
    select
        regime,
        series,
        round(series * 1.0 / sum(series) over (), 4) as share_pct,
        row_number() over (order by series desc) as pos
    from base
)
select
    regime,
    series,
    share_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<BarChart
			data={top_12_pib}
			x=municipio
			y=pib_real_bi
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="#,##0.0"
			leftPadding=22
			rightPadding=36
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
			title="Quais municípios têm maior PIB real?"
			subtitle="Top 8 no recorte (R$ Bilhões) · Valores constantes IPCA"
		/>
	</div>
	<div class="sl-card">
		<BarChart
			data={regimes_varejo_home}
			x=regime
			y=share_pct
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0%"
			leftPadding=24
			rightPadding=40
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
			title="Qual regime domina o varejo nacional (PMC × IPCA)?"
			subtitle="Participação das séries UF × Atividade (PMC × IPCA) · Líder em azul"
		/>
	</div>
</div>

```sql tabela_municipios
select
    rank_nacional_ims as rk,
    nome_municipio as municipio,
    sigla_uf as uf,
    populacao_residente as populacao,
    round(pib_real_mil_brl / 1e6, 2) as pib_bi,
    round(pib_per_capita_real_brl, 0) as pib_pc,
    num_empresas_atuantes as empresas,
    round(salario_medio_real_brl, 0) as salario_real,
    round(cagr_pib_real_3a_pct / 100.0, 4) as cagr_3a_pct,
    round(ims_score_0_100, 2) as ims,
    case tier_mercado
        when 'Tier 1 - Polo Nacional' then 'Tier 1'
        when 'Tier 2 - Expansao Prioritaria' then 'Tier 2'
        when 'Tier 3 - Emergente' then 'Tier 3'
        when 'Tier 4 - Local / Nicho' then 'Tier 4'
        else 'N/D'
    end as tier
from sidralake.mart_inteligencia_mercado_municipal
where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
order by rank_nacional_ims asc
```

<ExecTable
	data={tabela_municipios}
	title="Explorador Executivo de Municípios"
	subtitle="Cidades ranqueadas por Score IMS · Destaque azul: Líder #1, IMS ≥ 85 e CAGR ≥ +10%"
	search={true}
	searchPlaceholder="Buscar município ou UF..."
	exportCsv={true}
	csvFilename="sidralake_municipios_ims.csv"
	rowsPerPage={15}
	highlightFirstRow={true}
	columns={[
		{ key: 'rk', label: 'RK', kind: 'rank' },
		{ key: 'municipio', label: 'Município', kind: 'primary' },
		{ key: 'uf', label: 'UF', align: 'center' },
		{ key: 'populacao', label: 'População', align: 'right', fmt: 'int' },
		{ key: 'pib_bi', label: 'PIB Real (Bi)', align: 'right', fmt: 'brl_bi' },
		{ key: 'pib_pc', label: 'PIB Per Capita', align: 'right', fmt: 'brl_int' },
		{ key: 'cagr_3a_pct', label: 'CAGR 3A', align: 'right', kind: 'growth', highlightThreshold: 0.1 },
		{ key: 'ims', label: 'Score IMS', align: 'right', kind: 'databar', fmt: 'dec2', barMax: 100, barThreshold: 85 },
		{ key: 'tier', label: 'Tier de Mercado', align: 'center', kind: 'tier_badge' }
	]}
/>

<footer class="sl-footer">
	<span><strong>Fonte dos Dados:</strong> Instituto Brasileiro de Geografia e Estatística (IBGE) · Dados públicos abertos.</span>
	<span>SidraLake 360° · GNU GPL v3.0</span>
</footer>
