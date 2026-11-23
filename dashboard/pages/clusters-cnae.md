---
title: Clusters Setoriais & Emprego Formal (CNAE 2.0 / CEMPRE)
---

```sql anos_cempre
select distinct ano_referencia
from sidralake.mart_clusters_setoriais_uf
order by ano_referencia desc
```

```sql ufs_cnae
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_clusters_setoriais_uf
order by ordem, sigla_uf
```

```sql secoes_cnae
select 'TODAS' as codigo_secao_cnae, 0 as ordem
union all
select distinct codigo_secao_cnae, 1 as ordem
from sidralake.mart_clusters_setoriais_uf
order by ordem, codigo_secao_cnae
```

<header class="sl-page-header">
	<div class="sl-page-heading">
		<h1 class="sl-page-title">Clusters Setoriais &amp; Emprego Formal (CNAE 2.0)</h1>
		<p class="sl-page-subtitle">Cadastro Central de Empresas (CEMPRE · SIDRA 9418) por UF e 21 Seções CNAE · Sigilo estatístico IBGE (X) sinalizado</p>
	</div>
	<div class="sl-filter-bar">
		<Dropdown data={anos_cempre} name=ano value=ano_referencia title="Ano" defaultValue={2024} />
		<Dropdown data={ufs_cnae} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
		<Dropdown data={secoes_cnae} name=cnae value=codigo_secao_cnae title="CNAE" defaultValue="TODAS" />
	</div>
</header>

```sql kpis_cnae
select
    sum(pessoal_ocupado_total) as emprego_total,
    sum(pessoal_ocupado_assalariado) as assalariados_total,
    sum(num_empresas) as empresas_total,
    round(sum(massa_salarial_real_mil_brl) / 1e6, 2) as massa_real_bi,
    sum(case when has_sigilo_estatistico then 1 else 0 end) as celulas_sigilo_x
from sidralake.mart_clusters_setoriais_uf
where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
```

<div class="sl-kpi-grid-5">
	<KpiCard data={kpis_cnae} value="emprego_total" title="Pessoal Ocupado" fmt="pop_mi" icon="users" subtitle="Vínculos + sócios ativos" />
	<KpiCard data={kpis_cnae} value="assalariados_total" title="Assalariados Formais" fmt="pop_mi" icon="briefcase" subtitle="Carteira assinada / estatutários" />
	<KpiCard data={kpis_cnae} value="empresas_total" title="Empresas Atuantes" fmt="pop_mi" icon="building" subtitle="Unidades cadastradas CEMPRE" />
	<KpiCard data={kpis_cnae} value="massa_real_bi" title="Massa Salarial Real" fmt="brl_bi" icon="wallet" subtitle="Valores constantes IPCA" />
	<KpiCard data={kpis_cnae} value="celulas_sigilo_x" title="Células Sigilo IBGE (X)" fmt="int" icon="shield" subtitle="Suprimidas sem distorcer totais" />
</div>

```sql top_shares_setoriais
with base as (
    select
        sigla_uf || ' · ' || codigo_secao_cnae as uf_setor,
        round(market_share_uf_no_setor_pct / 100.0, 4) as share_br_pct,
        row_number() over (order by market_share_uf_no_setor_pct desc) as pos
    from sidralake.mart_clusters_setoriais_uf
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
      and market_share_uf_no_setor_pct is not null
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
      and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
    order by pos asc
    limit 10
)
select
    uf_setor,
    share_br_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

```sql emprego_por_secao
with agg as (
    select
        codigo_secao_cnae || ' · ' || case codigo_secao_cnae
            when 'A' then 'Agropecuária'
            when 'B' then 'Ind. Extrativas'
            when 'C' then 'Ind. Transformação'
            when 'D' then 'Energia e Gás'
            when 'E' then 'Água e Saneamento'
            when 'F' then 'Construção'
            when 'G' then 'Comércio e Veículos'
            when 'H' then 'Transporte e Correio'
            when 'I' then 'Alojamento e Alim.'
            when 'J' then 'TI e Comunicação'
            when 'K' then 'Finanças e Seguros'
            when 'L' then 'Ativ. Imobiliárias'
            when 'M' then 'Serv. Profissionais'
            when 'N' then 'Serv. Administrativos'
            when 'O' then 'Adm. Pública'
            when 'P' then 'Educação'
            when 'Q' then 'Saúde e Serv. Sociais'
            when 'R' then 'Artes e Cultura'
            when 'S' then 'Outros Serviços'
            when 'T' then 'Serv. Domésticos'
            when 'U' then 'Org. Internacionais'
            else codigo_secao_cnae
        end as setor,
        round(sum(pessoal_ocupado_total) / 1e6, 2) as emprego_mi
    from sidralake.mart_clusters_setoriais_uf
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
      and pessoal_ocupado_total is not null
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
      and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
    group by 1
),
ranked as (
    select
        *,
        row_number() over (order by emprego_mi desc) as pos
    from agg
    order by pos asc
    limit 10
)
select
    setor,
    emprego_mi,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<BarChart
			data={top_shares_setoriais}
			x=uf_setor
			y=share_br_pct
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0%"
			leftPadding=16
			rightPadding=36
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f8fafc' }, subtextStyle: { color: '#94a3b8' } }, xAxis: { axisLabel: { color: '#f8fafc' } }, yAxis: { axisLabel: { color: '#f8fafc' }, axisLine: { lineStyle: { color: '#334155' } } } }}
			title="Quais UFs lideram o share setorial?"
			subtitle="Participação no emprego nacional do setor · Líder em azul"
		/>
	</div>
	<div class="sl-card">
		<BarChart
			data={emprego_por_secao}
			x=setor
			y=emprego_mi
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.00"
			leftPadding=26
			rightPadding=34
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f8fafc' }, subtextStyle: { color: '#94a3b8' } }, xAxis: { axisLabel: { color: '#f8fafc' } }, yAxis: { axisLabel: { color: '#f8fafc' }, axisLine: { lineStyle: { color: '#334155' } } } }}
			title="Quais seções CNAE mais empregam?"
			subtitle="Pessoal ocupado formal (milhões) · Seção líder em azul"
		/>
	</div>
</div>

```sql heatmap_uf_cnae
with top_ufs as (
    select sigla_uf
    from sidralake.mart_clusters_setoriais_uf
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
    group by 1
    order by sum(pessoal_ocupado_total) desc nulls last
    limit 12
)
select
    m.sigla_uf as uf,
    m.codigo_secao_cnae as cnae,
    round(m.market_share_uf_no_setor_pct / 100.0, 4) as share_pct
from sidralake.mart_clusters_setoriais_uf as m
inner join top_ufs as t
    on m.sigla_uf = t.sigla_uf
where m.ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
  and m.market_share_uf_no_setor_pct is not null
  and m.codigo_secao_cnae in ('A', 'C', 'F', 'G', 'H', 'I', 'J', 'K', 'M', 'N', 'P', 'Q')
order by m.sigla_uf asc, m.codigo_secao_cnae asc
```

<div class="sl-card sl-stack">
	<Heatmap
		data={heatmap_uf_cnae}
		x=cnae
		y=uf
		value=share_pct
		valueFmt="0.0%"
		colorScale={['#141b26', '#1e3a8a', '#2563eb', '#3b82f6']}
		echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f8fafc' }, subtextStyle: { color: '#94a3b8' } }, xAxis: { axisLabel: { color: '#f8fafc' } }, yAxis: { axisLabel: { color: '#f8fafc' } } }}
		title="Concentração Estadual (%) no Emprego Brasileiro por Seção CNAE"
		subtitle="Top 12 UFs · A=Agro · C=Indústria · F=Construção · G=Comércio · H=Transporte · J=TI · K=Finanças · N=Adm · P=Educação · Q=Saúde"
	/>
</div>

```sql tabela_clusters
select
    cast(cast(ano_referencia as integer) as varchar) as ano,
    sigla_uf as uf,
    codigo_secao_cnae as cnae,
    case codigo_secao_cnae
        when 'A' then 'Agropecuária'
        when 'B' then 'Ind. Extrativas'
        when 'C' then 'Ind. Transformação'
        when 'D' then 'Energia e Gás'
        when 'E' then 'Água e Saneamento'
        when 'F' then 'Construção'
        when 'G' then 'Comércio e Veículos'
        when 'H' then 'Transporte e Correio'
        when 'I' then 'Alojamento e Alim.'
        when 'J' then 'TI e Comunicação'
        when 'K' then 'Finanças e Seguros'
        when 'L' then 'Ativ. Imobiliárias'
        when 'M' then 'Serv. Profissionais'
        when 'N' then 'Serv. Administrativos'
        when 'O' then 'Adm. Pública'
        when 'P' then 'Educação'
        when 'Q' then 'Saúde e Serv. Sociais'
        when 'R' then 'Artes e Cultura'
        when 'S' then 'Outros Serviços'
        when 'T' then 'Serv. Domésticos'
        when 'U' then 'Org. Internacionais'
        else descricao_secao_cnae
    end as setor,
    num_empresas as empresas,
    pessoal_ocupado_total as emprego,
    round(massa_salarial_real_mil_brl / 1e3, 1) as massa_mi,
    round(market_share_uf_no_setor_pct / 100.0, 4) as share_br_pct,
    round(crescimento_emprego_setor_yoy_pct / 100.0, 4) as cresc_yoy_pct,
    has_sigilo_estatistico as sigilo_x
from sidralake.mart_clusters_setoriais_uf
where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
order by pessoal_ocupado_total desc nulls last
```

<ExecTable
	data={tabela_clusters}
	title="Matriz Completa UF × Seção CNAE 2.0"
	subtitle="Destaque azul: maior cluster, Share BR ≥ 25% e Cresc. YoY ≥ +8%"
	search={true}
	searchPlaceholder="Buscar UF ou setor CNAE..."
	exportCsv={true}
	csvFilename="sidralake_clusters_cnae.csv"
	rowsPerPage={20}
	highlightFirstRow={true}
	columns={[
		{ key: 'ano', label: 'Ano', kind: 'year' },
		{ key: 'uf', label: 'UF', align: 'center', kind: 'primary' },
		{ key: 'cnae', label: 'CNAE', align: 'center', kind: 'tier_badge' },
		{ key: 'setor', label: 'Seção Setorial', kind: 'primary' },
		{ key: 'empresas', label: 'Empresas', align: 'right', fmt: 'int' },
		{ key: 'emprego', label: 'Emprego', align: 'right', fmt: 'int' },
		{ key: 'massa_mi', label: 'Massa (R$ Mi)', align: 'right', fmt: 'brl_mi' },
		{ key: 'share_br_pct', label: 'Share BR', align: 'right', kind: 'databar', fmt: 'pct1', barMax: 0.6, barThreshold: 0.25 },
		{ key: 'cresc_yoy_pct', label: 'Cresc. YoY', align: 'right', kind: 'growth', highlightThreshold: 0.08 },
		{ key: 'sigilo_x', label: 'Sigilo', align: 'center', kind: 'sigilo_badge' }
	]}
/>
