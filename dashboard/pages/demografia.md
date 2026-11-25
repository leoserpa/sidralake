---
title: Radar Demográfico & Polos Regionais (IBGE)
---

```sql regioes_demo
select 'TODAS' as nome_regiao, 0 as ordem
union all
select distinct nome_regiao, 1 as ordem
from sidralake.mart_demografia_municipal
order by ordem, nome_regiao
```

```sql ufs_demo
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_demografia_municipal
where '${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}'
order by ordem, sigla_uf
```

<header class="sl-page-header">
	<div class="sl-page-heading">
		<h1 class="sl-page-title">Radar Demográfico &amp; Polos Regionais</h1>
		<p class="sl-page-subtitle">Evolução populacional oficial (Censo 2022 → Estimativas recentes), densidade urbana e áreas de influência por Região Imediata IBGE</p>
	</div>
	<div class="sl-filter-bar">
		<Dropdown data={regioes_demo} name=regiao value=nome_regiao title="Região" defaultValue="TODAS" />
		<Dropdown data={ufs_demo} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
		<ResetFilters />
	</div>
</header>

<section class="sl-control-card">
	<Slider name=min_pop_demo title="População Mínima para Ranking Municipal" min=0 max=200000 step=10000 defaultValue=50000 fmt="#,##0" size=full />
</section>

```sql kpis_demografia
select
    sum(populacao_atual) as pop_atual,
    case
        when min(ano_populacao_atual) = max(ano_populacao_atual)
            then cast(cast(max(ano_populacao_atual) as integer) as varchar)
        else cast(cast(min(ano_populacao_atual) as integer) as varchar)
            || '–' || cast(cast(max(ano_populacao_atual) as integer) as varchar)
    end as ano_atual,
    sum(saldo_populacional_desde_2022) as saldo_pop,
    round(
        sum(saldo_populacional_desde_2022) * 1.0
        / nullif(sum(case when saldo_populacional_desde_2022 is not null then populacao_censo_2022 end), 0),
        4
    ) as variacao_pop_pct,
    round(sum(populacao_atual) * 1.0 / nullif(sum(area_km2), 0), 1) as densidade_media,
    count(distinct codigo_regiao_imediata) as total_polos
from sidralake.mart_demografia_municipal
where ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and (
      '${inputs.uf.value}' = 'TODAS'
      or sigla_uf = '${inputs.uf.value}'
      or not exists (
          select 1
          from sidralake.dim_geografia as _chk
          where _chk.sigla_uf = '${inputs.uf.value}'
            and ('${inputs.regiao.value}' = 'TODAS' or _chk.nome_regiao = '${inputs.regiao.value}')
      )
  )
```

<div class="sl-kpi-grid-5">
	<KpiCard data={kpis_demografia} value="pop_atual" title="População Atual" fmt="pop_mi" icon="users" subtitleCol="ano_atual" subtitlePrefix="Estimativa oficial IBGE " />
	<KpiCard data={kpis_demografia} value="saldo_pop" title="Saldo Demográfico" fmt="pop_mi" icon="trending" subtitle="Variação desde o Censo 2022" />
	<KpiCard data={kpis_demografia} value="variacao_pop_pct" title="Crescimento Populacional" fmt="signed_pct2" icon="percent" subtitle="Expansão acumulada desde 2022" />
	<KpiCard data={kpis_demografia} value="densidade_media" title="Densidade Média" fmt="dec1" icon="layers" subtitle="Habitantes por km²" />
	<KpiCard data={kpis_demografia} value="total_polos" title="Regiões Imediatas" fmt="int" icon="mappin" subtitle="Áreas de influência IBGE" />
</div>

```sql cresc_pop_uf
with agg as (
    select
        sigla_uf as uf,
        round(
            sum(saldo_populacional_desde_2022) * 1.0
            / nullif(sum(case when saldo_populacional_desde_2022 is not null then populacao_censo_2022 end), 0),
            4
        ) as cresc_pct
    from sidralake.mart_demografia_municipal
    where ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and (
          '${inputs.uf.value}' = 'TODAS'
          or sigla_uf = '${inputs.uf.value}'
          or not exists (
              select 1
              from sidralake.dim_geografia as _chk
              where _chk.sigla_uf = '${inputs.uf.value}'
                and ('${inputs.regiao.value}' = 'TODAS' or _chk.nome_regiao = '${inputs.regiao.value}')
          )
      )
    group by 1
),
ranked as (
    select
        uf,
        cresc_pct,
        row_number() over (order by cresc_pct desc) as pos
    from agg
    where cresc_pct is not null
    order by pos asc
    limit 12
)
select
    uf,
    cresc_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

```sql top_cidades_demo
with ranked as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(crescimento_populacional_desde_2022_pct / 100.0, 4) as cresc_pct,
        row_number() over (order by crescimento_populacional_desde_2022_pct desc) as pos
    from sidralake.mart_demografia_municipal
    where crescimento_populacional_desde_2022_pct is not null
      and coalesce(populacao_atual, 0) >= coalesce(try_cast('${inputs.min_pop_demo}' as double), 50000)
      and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and (
          '${inputs.uf.value}' = 'TODAS'
          or sigla_uf = '${inputs.uf.value}'
          or not exists (
              select 1
              from sidralake.dim_geografia as _chk
              where _chk.sigla_uf = '${inputs.uf.value}'
                and ('${inputs.regiao.value}' = 'TODAS' or _chk.nome_regiao = '${inputs.regiao.value}')
          )
      )
    order by pos asc
    limit 10
)
select
    municipio,
    cresc_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Quais UFs mais crescem em população?</h3>
			<p class="sl-card-subtitle">Variação acumulada desde o Censo 2022 · UF líder em azul</p>
		</div>
		<BarChart
			data={cresc_pop_uf}
			x=uf
			y=cresc_pct
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0%"
			leftPadding=14
			rightPadding=44
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
		/>
	</div>
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Quais municípios têm maior crescimento populacional (%)?</h3>
			<p class="sl-card-subtitle">Variação percentual desde o Censo 2022 no porte filtrado · Líder em azul</p>
		</div>
		<BarChart
			data={top_cidades_demo}
			x=municipio
			y=cresc_pct
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
			rightPadding=48
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
		/>
	</div>
</div>

```sql top_polos_regionais
with base as (
    select
        codigo_regiao_imediata,
        nome_regiao_imediata || ' - ' || sigla_uf as polo_regional,
        round(sum(pib_real_mil_brl) / 1e6, 1) as pib_bi,
        row_number() over (order by sum(pib_real_mil_brl) desc nulls last) as pos
    from sidralake.mart_demografia_municipal
    where pib_real_mil_brl is not null
      and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and (
          '${inputs.uf.value}' = 'TODAS'
          or sigla_uf = '${inputs.uf.value}'
          or not exists (
              select 1
              from sidralake.dim_geografia as _chk
              where _chk.sigla_uf = '${inputs.uf.value}'
                and ('${inputs.regiao.value}' = 'TODAS' or _chk.nome_regiao = '${inputs.regiao.value}')
          )
      )
    group by 1, 2
    order by pos asc
    limit 12
)
select
    polo_regional,
    pib_bi,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

<div class="sl-card sl-stack">
	<div class="sl-chart-head">
		<h3 class="sl-card-title">Quais Regiões Imediatas concentram o maior PIB real combinado?</h3>
		<p class="sl-card-subtitle">Mercado somado de todos os municípios da área de influência (R$ Bilhões constantes IPCA) · Polo líder em azul</p>
	</div>
	<BarChart
		data={top_polos_regionais}
		x=polo_regional
		y=pib_bi
		series=destaque
		type=stacked
		swapXY=true
		sort=false
		labels=true
		stackTotalLabel=false
		labelPosition=outside
		showAllLabels=true
		labelFmt="#,##0.0"
		leftPadding=30
		rightPadding=48
		legend=false
		yGridlines=false
		xGridlines=false
		yAxisLabels=false
		yBaseline=false
		seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
		echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
	/>
</div>

```sql tabela_polos_regionais
select
    row_number() over (order by sum(pib_real_mil_brl) desc nulls last) as rk,
    nome_regiao_imediata as regiao_imediata,
    sigla_uf as uf,
    count(*) as municipios,
    sum(populacao_atual) as pop_atual,
    round(
        sum(saldo_populacional_desde_2022) * 1.0
        / nullif(sum(case when saldo_populacional_desde_2022 is not null then populacao_censo_2022 end), 0),
        4
    ) as cresc_pop_pct,
    round(sum(populacao_atual) * 1.0 / nullif(sum(area_km2), 0), 1) as densidade,
    round(sum(pib_real_mil_brl) / 1e6, 2) as pib_bi,
    round(sum(massa_salarial_real_mil_brl) / 1e6, 2) as massa_bi,
    round(avg(ims_score_0_100), 2) as ims_medio
from sidralake.mart_demografia_municipal
where ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and (
      '${inputs.uf.value}' = 'TODAS'
      or sigla_uf = '${inputs.uf.value}'
      or not exists (
          select 1
          from sidralake.dim_geografia as _chk
          where _chk.sigla_uf = '${inputs.uf.value}'
            and ('${inputs.regiao.value}' = 'TODAS' or _chk.nome_regiao = '${inputs.regiao.value}')
      )
  )
group by codigo_regiao_imediata, nome_regiao_imediata, sigla_uf
order by pib_bi desc nulls last
```

<ExecTable
	data={tabela_polos_regionais}
	title="Ranking de Polos Regionais (Regiões Imediatas IBGE)"
	subtitle="Áreas de influência econômica com população atualizada, adensamento urbano e PIB real somado · Destaque azul: Polo #1, IMS ≥ 65 e Cresc. Pop ≥ +5%"
	search={true}
	searchPlaceholder="Buscar região imediata ou UF..."
	exportCsv={true}
	csvFilename="sidralake_polos_regionais_ibge.csv"
	rowsPerPage={20}
	highlightFirstRow={true}
	columns={[
		{ key: 'rk', label: 'RK', kind: 'rank' },
		{ key: 'regiao_imediata', label: 'Região Imediata', kind: 'primary' },
		{ key: 'uf', label: 'UF', align: 'center' },
		{ key: 'municipios', label: 'Mun.', align: 'right', fmt: 'int' },
		{ key: 'pop_atual', label: 'População', align: 'right', fmt: 'int' },
		{ key: 'cresc_pop_pct', label: 'Cresc. Pop', align: 'right', kind: 'growth', highlightThreshold: 0.05 },
		{ key: 'densidade', label: 'Hab/km²', align: 'right', fmt: 'dec1' },
		{ key: 'pib_bi', label: 'PIB Real (Bi)', align: 'right', fmt: 'brl_bi2' },
		{ key: 'massa_bi', label: 'Massa Sal. (Bi)', align: 'right', fmt: 'brl_bi2' },
		{ key: 'ims_medio', label: 'IMS Médio', align: 'right', kind: 'databar', fmt: 'dec2', barMax: 100, barThreshold: 65 }
	]}
/>
