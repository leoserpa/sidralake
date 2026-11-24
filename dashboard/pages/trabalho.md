---
title: Mercado de Trabalho & Renda Real (PNAD Contínua IBGE)
---

```sql regioes_pnad
select 'TODAS' as nome_regiao, 0 as ordem
union all
select distinct nome_regiao, 1 as ordem
from sidralake.mart_mercado_trabalho_uf
order by ordem, nome_regiao
```

```sql ufs_pnad
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_mercado_trabalho_uf
where '${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}'
order by ordem, sigla_uf
```

<header class="sl-page-header">
	<div class="sl-page-heading">
		<h1 class="sl-page-title">Mercado de Trabalho &amp; Renda Real (PNAD Contínua)</h1>
		<p class="sl-page-subtitle">Desocupação, subutilização da força de trabalho (SIDRA 4099) e rendimento médio real habitual incluindo informais (SIDRA 5436 · 2018+)</p>
	</div>
	<div class="sl-filter-bar">
		<Dropdown data={regioes_pnad} name=regiao value=nome_regiao title="Região" defaultValue="TODAS" />
		<Dropdown data={ufs_pnad} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
		<ResetFilters />
	</div>
</header>

```sql kpis_pnad
select
    max(label_trimestre) as ultimo_trimestre,
    round(avg(taxa_desocupacao_pct) / 100.0, 4) as desocupacao_pct,
    round(avg(taxa_subutilizacao_composta_pct) / 100.0, 4) as subutilizacao_pct,
    round(avg(rendimento_medio_real_brl), 0) as rendimento_real,
    round(avg(hiato_salarial_genero_pct) / 100.0, 4) as hiato_genero_pct
from sidralake.mart_mercado_trabalho_uf
where is_ultimo_trimestre
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
```

<div class="sl-kpi-grid-5">
	<KpiCard data={kpis_pnad} value="ultimo_trimestre" title="Último Trimestre" fmt="raw" icon="calendar" subtitle="Fechamento oficial PNAD IBGE" />
	<KpiCard data={kpis_pnad} value="desocupacao_pct" title="Taxa de Desocupação" fmt="pct1" icon="gauge" subtitle="Média das UFs no recorte" />
	<KpiCard data={kpis_pnad} value="subutilizacao_pct" title="Subutilização Composta" fmt="pct1" icon="layers" subtitle="Desocupação + subocupação + potencial" />
	<KpiCard data={kpis_pnad} value="rendimento_real" title="Rendimento Médio Real" fmt="brl_int" icon="wallet" subtitle="Todos os trabalhos (formal + informal)" />
	<KpiCard data={kpis_pnad} value="hiato_genero_pct" title="Hiato Salarial (M vs. H)" fmt="signed_pct2" icon="percent" subtitle="Diferença média real Mulheres × Homens" />
</div>

```sql serie_desocupacao
with base as (
    select
        data_referencia,
        round(avg(taxa_desocupacao_pct) / 100.0, 4) as desocupacao_pct,
        round(avg(taxa_subutilizacao_composta_pct) / 100.0, 4) as subutilizacao_pct
    from sidralake.mart_mercado_trabalho_uf
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
      and taxa_desocupacao_pct is not null
    group by 1
)
select data_referencia, 'Taxa de Desocupação' as indicador, desocupacao_pct as valor_pct from base
union all
select data_referencia, 'Subutilização Composta' as indicador, subutilizacao_pct as valor_pct from base
order by data_referencia asc, indicador asc
```

```sql serie_rendimento_genero
with base as (
    select
        data_referencia,
        round(avg(rendimento_medio_real_brl), 0) as total_brl,
        round(avg(rendimento_homens_real_brl), 0) as homens_brl,
        round(avg(rendimento_mulheres_real_brl), 0) as mulheres_brl
    from sidralake.mart_mercado_trabalho_uf
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
      and rendimento_medio_real_brl is not null
    group by 1
)
select data_referencia, 'Total' as grupo, total_brl as rendimento_brl from base
union all
select data_referencia, 'Homens' as grupo, homens_brl as rendimento_brl from base
union all
select data_referencia, 'Mulheres' as grupo, mulheres_brl as rendimento_brl from base
order by data_referencia asc, grupo asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<LineChart
			data={serie_desocupacao}
			x=data_referencia
			y=valor_pct
			series=indicador
			yFmt="0.0%"
			yGridlines=false
			xGridlines=false
			seriesColors={{'Taxa de Desocupação': '#3b82f6', 'Subutilização Composta': '#686e6c'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			title="Trajetória da Desocupação vs. Subutilização (2018+)"
			subtitle="Série trimestral PNAD Contínua · Taxa de desocupação em azul"
			yAxisTitle="Percentual (%)"
		/>
	</div>
	<div class="sl-card">
		<LineChart
			data={serie_rendimento_genero}
			x=data_referencia
			y=rendimento_brl
			series=grupo
			yFmt="#,##0"
			yGridlines=false
			xGridlines=false
			seriesColors={{'Total': '#3b82f6', 'Homens': '#9ca3a0', 'Mulheres': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			title="Evolução do Rendimento Médio Real por Gênero (R$/mês)"
			subtitle="Rendimento habitual em todos os trabalhos (preços constantes IBGE) · Total em azul"
			yAxisTitle="R$ / mês"
		/>
	</div>
</div>

```sql ranking_renda_uf
with base as (
    select
        sigla_uf as uf,
        round(rendimento_medio_real_brl, 0) as rendimento_brl,
        row_number() over (order by rendimento_medio_real_brl desc) as pos
    from sidralake.mart_mercado_trabalho_uf
    where is_ultimo_trimestre
      and rendimento_medio_real_brl is not null
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
    limit 12
)
select
    uf,
    rendimento_brl,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

```sql ranking_desocupacao_uf
with base as (
    select
        sigla_uf as uf,
        round(taxa_desocupacao_pct / 100.0, 4) as desocupacao_pct,
        row_number() over (order by taxa_desocupacao_pct asc) as pos
    from sidralake.mart_mercado_trabalho_uf
    where is_ultimo_trimestre
      and taxa_desocupacao_pct is not null
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
    limit 12
)
select
    uf,
    desocupacao_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<BarChart
			data={ranking_renda_uf}
			x=uf
			y=rendimento_brl
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="#,##0"
			leftPadding=14
			rightPadding=48
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
			title="Quais UFs têm maior rendimento médio real?"
			subtitle="Último trimestre PNAD Contínua (R$/mês) · UF líder em azul"
		/>
	</div>
	<div class="sl-card">
		<BarChart
			data={ranking_desocupacao_uf}
			x=uf
			y=desocupacao_pct
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
			title="Quais UFs têm menor taxa de desocupação?"
			subtitle="Top 12 menores taxas no último trimestre PNAD · Menor taxa em azul"
		/>
	</div>
</div>

```sql tabela_pnad_uf
select
    label_trimestre as trimestre,
    sigla_uf as uf,
    nome_regiao as regiao,
    round(taxa_desocupacao_pct / 100.0, 4) as desocupacao_pct,
    round(var_yoy_desocupacao_pp, 2) as var_desoc_pp,
    round(taxa_subutilizacao_composta_pct / 100.0, 4) as subutilizacao_pct,
    round(rendimento_medio_real_brl, 0) as rendimento_brl,
    round(var_yoy_rendimento_real_pct / 100.0, 4) as cresc_renda_yoy_pct,
    round(rendimento_homens_real_brl, 0) as homens_brl,
    round(rendimento_mulheres_real_brl, 0) as mulheres_brl,
    round(hiato_salarial_genero_pct / 100.0, 4) as hiato_genero_pct
from sidralake.mart_mercado_trabalho_uf
where is_ultimo_trimestre
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
order by rendimento_medio_real_brl desc nulls last
```

<ExecTable
	data={tabela_pnad_uf}
	title="Panorama Estadual do Mercado de Trabalho (PNAD Contínua — Último Trimestre)"
	subtitle="Rendimento real inclui mercado formal e informal · Destaque azul: UF líder em renda e cresc. real ≥ +5%"
	search={true}
	searchPlaceholder="Buscar UF ou região..."
	exportCsv={true}
	csvFilename="sidralake_pnad_trabalho_uf.csv"
	rowsPerPage={27}
	highlightFirstRow={true}
	columns={[
		{ key: 'trimestre', label: 'Trim.', kind: 'year' },
		{ key: 'uf', label: 'UF', kind: 'primary', align: 'center' },
		{ key: 'regiao', label: 'Região' },
		{ key: 'desocupacao_pct', label: 'Desocup.', align: 'right', fmt: 'pct1' },
		{ key: 'var_desoc_pp', label: 'Var. YoY', align: 'right', fmt: 'signed_pp' },
		{ key: 'subutilizacao_pct', label: 'Subutil.', align: 'right', fmt: 'pct1' },
		{ key: 'rendimento_brl', label: 'Rendimento', align: 'right', fmt: 'brl_int' },
		{ key: 'cresc_renda_yoy_pct', label: 'Renda YoY', align: 'right', kind: 'growth', highlightThreshold: 0.05 },
		{ key: 'homens_brl', label: 'Homens', align: 'right', fmt: 'brl_int' },
		{ key: 'mulheres_brl', label: 'Mulheres', align: 'right', fmt: 'brl_int' },
		{ key: 'hiato_genero_pct', label: 'Hiato M×H', align: 'right', fmt: 'signed_pct1' }
	]}
/>
