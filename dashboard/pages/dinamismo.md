---
title: Dinamismo Econômico & Estrutura Produtiva (VAB / HHI)
---

```sql ufs_dinamismo
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, sigla_uf
```

<header class="sl-page-header">
	<div class="sl-page-heading">
		<h1 class="sl-page-title">Dinamismo Econômico &amp; Estrutura Produtiva</h1>
		<p class="sl-page-subtitle">CAGR real de 3 anos deflacionado pelo IPCA, composição setorial do VAB (IBGE) e diversificação produtiva (HHI)</p>
	</div>
	<div class="sl-filter-bar">
		<Dropdown data={ufs_dinamismo} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
	</div>
</header>

<section class="sl-control-card">
	<Slider name=min_pop_din title="População Mínima para Ranking CAGR e Dispersão" min=0 max=200000 step=10000 defaultValue=50000 fmt="#,##0" size=full />
</section>

```sql top_cagr
with base as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(cagr_pib_real_3a_pct / 100.0, 4) as cagr_3a_pct,
        row_number() over (order by cagr_pib_real_3a_pct desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and coalesce(populacao_residente, 0) >= coalesce(try_cast('${inputs.min_pop_din}' as double), 50000)
      and cagr_pib_real_3a_pct is not null
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
    order by pos asc
    limit 10
)
select
    municipio,
    cagr_3a_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

```sql vab_empilhado_regiao
with ult_vab as (
    select
        nome_regiao as regiao,
        round(avg(share_vab_servicos_privados), 4) as servicos,
        round(avg(share_vab_agropecuaria), 4) as agropecuaria,
        round(avg(share_vab_industria), 4) as industria,
        round(avg(share_vab_adm_publica), 4) as adm_publica
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = (
        select max(ano_referencia)
        from sidralake.mart_inteligencia_mercado_municipal
        where indice_diversificacao_setorial is not null
    )
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
    group by 1
)
select regiao, 'Serviços' as setor, servicos as share from ult_vab
union all select regiao, 'Indústria', industria from ult_vab
union all select regiao, 'Agro', agropecuaria from ult_vab
union all select regiao, 'Adm. Púb.', adm_publica from ult_vab
order by regiao asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<BarChart
			data={top_cagr}
			x=municipio
			y=cagr_3a_pct
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0%"
			leftPadding=28
			rightPadding=38
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
			title="Quais municípios mais cresceram?"
			subtitle="CAGR real 3 anos (IPCA) · Líder em azul pré-atentivo"
		/>
	</div>
	<div class="sl-card">
		<BarChart
			data={vab_empilhado_regiao}
			x=regiao
			y=share
			series=setor
			type=stacked100
			swapXY=true
			leftPadding=20
			rightPadding=16
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Serviços': '#3b82f6', 'Indústria': '#94a3b8', 'Agro': '#64748b', 'Adm. Púb.': '#334155'}}
			title="Composição setorial do VAB por Região"
			subtitle="Proporção 100% · Serviços em destaque azul · Último VAB IBGE (2021)"
		/>
	</div>
</div>

```sql scatter_poder_compra
select
    nome_municipio || ' - ' || sigla_uf as municipio,
    case
        when tier_mercado = 'Tier 1 - Polo Nacional' then 'Tier 1 · Polo'
        else 'Demais Municípios'
    end as grupo_tier,
    round(pib_per_capita_real_brl, 0) as pib_per_capita_real,
    ims_score_0_100 as ims
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and coalesce(populacao_residente, 0) >= coalesce(try_cast('${inputs.min_pop_din}' as double), 50000)
  and pib_per_capita_real_brl is not null
  and ims_score_0_100 is not null
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
order by ims_score_0_100 desc
limit 500
```

<div class="sl-card sl-stack">
	<ScatterPlot
		data={scatter_poder_compra}
		x=pib_per_capita_real
		y=ims
		series=grupo_tier
		tooltipTitle=municipio
		xFmt="#,##0"
		yGridlines=false
		xGridlines=false
		seriesColors={{'Tier 1 · Polo': '#3b82f6', 'Demais Municípios': '#525866'}}
		title="Polos Nacionais (Tier 1) concentram alto poder de compra e Score IMS"
		subtitle="Dispersão PIB Per Capita Real (R$) × Score IMS · Polos Tier 1 em azul"
		xAxisTitle="PIB Per Capita Real (R$)"
		yAxisTitle="Score IMS (0–100)"
	/>
</div>

```sql vab_por_uf
select
    cast(cast(max(ano_referencia) as integer) as varchar) as ano,
    sigla_uf as uf,
    nome_regiao as regiao,
    count(*) as municipios,
    round(avg(share_vab_agropecuaria), 4) as agro_pct,
    round(avg(share_vab_industria), 4) as ind_pct,
    round(avg(share_vab_servicos_privados), 4) as servicos_pct,
    round(avg(share_vab_adm_publica), 4) as adm_pub_pct,
    round(avg(indice_diversificacao_setorial), 3) as hhi_div
from sidralake.mart_inteligencia_mercado_municipal
where ano_referencia = (
    select max(ano_referencia)
    from sidralake.mart_inteligencia_mercado_municipal
    where indice_diversificacao_setorial is not null
)
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
group by 2, 3
order by hhi_div desc
```

<ExecTable
	data={vab_por_uf}
	title="Estrutura Produtiva Média por UF (Último VAB Publicado — 2021)"
	subtitle="Estados ordenados pelo Índice de Diversificação Setorial (HHI) · Destaque azul: UF líder e HHI ≥ 0,65"
	search={true}
	searchPlaceholder="Buscar UF ou região..."
	exportCsv={true}
	csvFilename="sidralake_vab_estrutura_uf.csv"
	rowsPerPage={15}
	highlightFirstRow={true}
	columns={[
		{ key: 'ano', label: 'Ano', kind: 'year' },
		{ key: 'uf', label: 'UF', kind: 'primary', align: 'center' },
		{ key: 'regiao', label: 'Região' },
		{ key: 'municipios', label: 'Municípios', align: 'right', fmt: 'int' },
		{ key: 'agro_pct', label: 'Agro %', align: 'right', fmt: 'pct1' },
		{ key: 'ind_pct', label: 'Indústria %', align: 'right', fmt: 'pct1' },
		{ key: 'servicos_pct', label: 'Serviços %', align: 'right', fmt: 'pct1' },
		{ key: 'adm_pub_pct', label: 'Adm. Púb. %', align: 'right', fmt: 'pct1' },
		{ key: 'hhi_div', label: 'HHI Div.', align: 'right', kind: 'databar', fmt: 'dec3', barMax: 0.75, barThreshold: 0.65 }
	]}
/>
