---
title: Radar Demográfico & Polos Regionais (IBGE)
---

```sql regioes_demo
select 'TODAS' as nome_regiao, 0 as ordem
union all
select distinct nome_regiao, 1 as ordem
from sidralake.dim_geografia
order by ordem, nome_regiao
```

```sql ufs_demo
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.dim_geografia
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
	</div>
</header>

<section class="sl-control-card">
	<Slider name=min_pop_demo title="População Mínima para Ranking Municipal" min=0 max=200000 step=10000 defaultValue=50000 fmt="#,##0" size=full />
</section>

```sql kpis_demografia
with pop_ranked as (
    select
        p.codigo_ibge_municipio,
        cast(p.ano_referencia as integer) as ano,
        p.populacao_residente,
        p.area_km2,
        g.sigla_uf,
        g.nome_regiao,
        g.nome_regiao_imediata,
        row_number() over (partition by p.codigo_ibge_municipio order by p.ano_referencia desc) as rn_ult,
        row_number() over (
            partition by p.codigo_ibge_municipio
            order by case when cast(p.ano_referencia as integer) = 2022 then 0 else 1 end, p.ano_referencia asc
        ) as rn_base
    from sidralake.fct_populacao_municipal as p
    inner join sidralake.dim_geografia as g
        on p.codigo_ibge_municipio = g.codigo_ibge_municipio
    where ('${inputs.regiao.value}' = 'TODAS' or g.nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or g.sigla_uf = '${inputs.uf.value}')
),
ult as (
    select * from pop_ranked where rn_ult = 1
),
base as (
    select codigo_ibge_municipio, populacao_residente as pop_base
    from pop_ranked
    where rn_base = 1
)
select
    sum(u.populacao_residente) as pop_atual,
    cast(cast(max(u.ano) as integer) as varchar) as ano_atual,
    sum(u.populacao_residente) - sum(coalesce(b.pop_base, u.populacao_residente)) as saldo_pop,
    round(
        (sum(u.populacao_residente) - sum(coalesce(b.pop_base, u.populacao_residente))) * 1.0
        / nullif(sum(coalesce(b.pop_base, u.populacao_residente)), 0),
        4
    ) as variacao_pop_pct,
    round(sum(u.populacao_residente) * 1.0 / nullif(sum(u.area_km2), 0), 1) as densidade_media,
    count(distinct u.nome_regiao_imediata) as total_polos
from ult as u
left join base as b
    on u.codigo_ibge_municipio = b.codigo_ibge_municipio
```

<div class="sl-kpi-grid-5">
	<KpiCard data={kpis_demografia} value="pop_atual" title="População Atual" fmt="pop_mi" icon="users" subtitleCol="ano_atual" subtitlePrefix="Estimativa oficial IBGE " />
	<KpiCard data={kpis_demografia} value="saldo_pop" title="Saldo Demográfico" fmt="pop_mi" icon="trending" subtitle="Variação desde o Censo base" />
	<KpiCard data={kpis_demografia} value="variacao_pop_pct" title="Crescimento Populacional" fmt="signed_pct2" icon="percent" subtitle="Expansão acumulada no recorte" />
	<KpiCard data={kpis_demografia} value="densidade_media" title="Densidade Média" fmt="dec1" icon="layers" subtitle="Habitantes por km²" />
	<KpiCard data={kpis_demografia} value="total_polos" title="Regiões Imediatas" fmt="int" icon="mappin" subtitle="Áreas de influência IBGE" />
</div>

```sql cresc_pop_uf
with pop_ranked as (
    select
        p.codigo_ibge_municipio,
        p.populacao_residente,
        g.sigla_uf,
        g.nome_regiao,
        row_number() over (partition by p.codigo_ibge_municipio order by p.ano_referencia desc) as rn_ult,
        row_number() over (
            partition by p.codigo_ibge_municipio
            order by case when cast(p.ano_referencia as integer) = 2022 then 0 else 1 end, p.ano_referencia asc
        ) as rn_base
    from sidralake.fct_populacao_municipal as p
    inner join sidralake.dim_geografia as g
        on p.codigo_ibge_municipio = g.codigo_ibge_municipio
    where ('${inputs.regiao.value}' = 'TODAS' or g.nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or g.sigla_uf = '${inputs.uf.value}')
),
agg as (
    select
        u.sigla_uf as uf,
        round(
            (sum(u.populacao_residente) - sum(coalesce(b.populacao_residente, u.populacao_residente))) * 1.0
            / nullif(sum(coalesce(b.populacao_residente, u.populacao_residente)), 0),
            4
        ) as cresc_pct
    from (select * from pop_ranked where rn_ult = 1) as u
    left join (select codigo_ibge_municipio, populacao_residente from pop_ranked where rn_base = 1) as b
        on u.codigo_ibge_municipio = b.codigo_ibge_municipio
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
with pop_ranked as (
    select
        p.codigo_ibge_municipio,
        cast(p.ano_referencia as integer) as ano,
        p.populacao_residente,
        g.nome_municipio,
        g.sigla_uf,
        g.nome_regiao,
        row_number() over (partition by p.codigo_ibge_municipio order by p.ano_referencia desc) as rn_ult,
        row_number() over (
            partition by p.codigo_ibge_municipio
            order by case when cast(p.ano_referencia as integer) = 2022 then 0 else 1 end, p.ano_referencia asc
        ) as rn_base
    from sidralake.fct_populacao_municipal as p
    inner join sidralake.dim_geografia as g
        on p.codigo_ibge_municipio = g.codigo_ibge_municipio
    where ('${inputs.regiao.value}' = 'TODAS' or g.nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or g.sigla_uf = '${inputs.uf.value}')
),
cresc as (
    select
        u.nome_municipio || ' - ' || u.sigla_uf as municipio,
        round(
            (u.populacao_residente - b.populacao_residente) * 1.0
            / nullif(b.populacao_residente, 0),
            4
        ) as cresc_pct
    from (select * from pop_ranked where rn_ult = 1) as u
    inner join (select codigo_ibge_municipio, ano as ano_base, populacao_residente from pop_ranked where rn_base = 1) as b
        on u.codigo_ibge_municipio = b.codigo_ibge_municipio
    where u.ano > b.ano_base
      and u.populacao_residente >= coalesce(try_cast('${inputs.min_pop_demo}' as double), 50000)
      and b.populacao_residente > 0
),
ranked as (
    select
        municipio,
        cresc_pct,
        row_number() over (order by cresc_pct desc) as pos
    from cresc
    where cresc_pct is not null
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
			title="Quais UFs mais crescem em população?"
			subtitle="Variação acumulada desde o Censo base · UF líder em azul"
		/>
	</div>
	<div class="sl-card">
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
			title="Quais municípios mais ganham habitantes?"
			subtitle="Expansão demográfica recente no porte filtrado · Líder em azul"
		/>
	</div>
</div>

```sql top_polos_regionais
with base as (
    select
        nome_regiao_imediata || ' - ' || sigla_uf as polo_regional,
        round(sum(pib_real_mil_brl) / 1e6, 1) as pib_bi,
        row_number() over (order by sum(pib_real_mil_brl) desc nulls last) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and pib_real_mil_brl is not null
      and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
    group by 1
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
		title="Quais Regiões Imediatas concentram o maior PIB real combinado?"
		subtitle="Mercado somado de todos os municípios da área de influência (R$ Bilhões constantes IPCA) · Polo líder em azul"
	/>
</div>

```sql tabela_polos_regionais
with pop_ranked as (
    select
        p.codigo_ibge_municipio,
        p.populacao_residente,
        p.area_km2,
        row_number() over (partition by p.codigo_ibge_municipio order by p.ano_referencia desc) as rn_ult,
        row_number() over (
            partition by p.codigo_ibge_municipio
            order by case when cast(p.ano_referencia as integer) = 2022 then 0 else 1 end, p.ano_referencia asc
        ) as rn_base
    from sidralake.fct_populacao_municipal as p
),
pop_mun as (
    select
        u.codigo_ibge_municipio,
        u.populacao_residente as pop_atual,
        coalesce(b.populacao_residente, u.populacao_residente) as pop_base,
        u.area_km2
    from (select * from pop_ranked where rn_ult = 1) as u
    left join (select codigo_ibge_municipio, populacao_residente from pop_ranked where rn_base = 1) as b
        on u.codigo_ibge_municipio = b.codigo_ibge_municipio
)
select
    row_number() over (order by sum(m.pib_real_mil_brl) desc nulls last) as rk,
    m.nome_regiao_imediata as regiao_imediata,
    m.sigla_uf as uf,
    count(*) as municipios,
    sum(coalesce(pm.pop_atual, m.populacao_residente)) as pop_atual,
    round(
        (sum(coalesce(pm.pop_atual, m.populacao_residente)) - sum(coalesce(pm.pop_base, m.populacao_residente))) * 1.0
        / nullif(sum(coalesce(pm.pop_base, m.populacao_residente)), 0),
        4
    ) as cresc_pop_pct,
    round(
        sum(coalesce(pm.pop_atual, m.populacao_residente)) * 1.0
        / nullif(sum(coalesce(pm.area_km2, m.area_km2)), 0),
        1
    ) as densidade,
    round(sum(m.pib_real_mil_brl) / 1e6, 2) as pib_bi,
    round(sum(m.massa_salarial_real_mil_brl) / 1e6, 2) as massa_bi,
    round(avg(m.ims_score_0_100), 2) as ims_medio
from sidralake.mart_inteligencia_mercado_municipal as m
left join pop_mun as pm
    on m.codigo_ibge_municipio = pm.codigo_ibge_municipio
where m.is_ultimo_ano_completo
  and ('${inputs.regiao.value}' = 'TODAS' or m.nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or m.sigla_uf = '${inputs.uf.value}')
group by 2, 3
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
