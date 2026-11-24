---
title: Comparador Head-to-Head (Cidade A × Cidade B)
---

```sql ufs_comp
select distinct sigla_uf
from sidralake.dim_geografia
order by sigla_uf
```

```sql cidades_a
select
    g.codigo_ibge_municipio,
    g.nome_municipio,
    coalesce(m.populacao_residente, 0) as pop_ord
from sidralake.dim_geografia as g
left join sidralake.mart_inteligencia_mercado_municipal as m
    on g.codigo_ibge_municipio = m.codigo_ibge_municipio
   and m.is_ultimo_ano_completo
where g.sigla_uf = '${inputs.uf_a.value}'
order by pop_ord desc, g.nome_municipio asc
```

```sql cidades_b
select
    g.codigo_ibge_municipio,
    g.nome_municipio,
    coalesce(m.populacao_residente, 0) as pop_ord
from sidralake.dim_geografia as g
left join sidralake.mart_inteligencia_mercado_municipal as m
    on g.codigo_ibge_municipio = m.codigo_ibge_municipio
   and m.is_ultimo_ano_completo
where g.sigla_uf = '${inputs.uf_b.value}'
order by pop_ord desc, g.nome_municipio asc
```

<header class="sl-page-header">
	<div class="sl-page-heading">
		<h1 class="sl-page-title">Comparador Head-to-Head (Cidade A × Cidade B)</h1>
		<p class="sl-page-subtitle">Compare quaisquer duas cidades do Brasil lado a lado · Cidade A em azul pré-atentivo (#3B82F6) × Cidade B em ardósia (#64748B)</p>
	</div>
</header>

<section class="sl-control-card">
	<div class="sl-slider-grid-2">
		<div class="sl-filter-bar">
			<span class="sl-outline-pill">Cidade A · Foco</span>
			<Dropdown data={ufs_comp} name=uf_a value=sigla_uf title="UF A" defaultValue="SP" />
			<Dropdown data={cidades_a} name=cidade_a value=codigo_ibge_municipio label=nome_municipio title="Município A" defaultValue={3550308} />
		</div>
		<div class="sl-filter-bar">
			<span class="sl-outline-pill">Cidade B · Referência</span>
			<Dropdown data={ufs_comp} name=uf_b value=sigla_uf title="UF B" defaultValue="PR" />
			<Dropdown data={cidades_b} name=cidade_b value=codigo_ibge_municipio label=nome_municipio title="Município B" defaultValue={4106902} />
		</div>
	</div>
</section>

```sql comparativo_pilares
with sel as (
    select
        case
            when codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade_a.value}' as integer), 3550308) then 'Cidade A'
            else 'Cidade B'
        end as lado,
        score_tamanho_mercado,
        score_poder_compra,
        score_dinamismo,
        score_maturidade_empresarial
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and codigo_ibge_municipio in (coalesce(try_cast('${inputs.cidade_a.value}' as integer), 3550308), coalesce(try_cast('${inputs.cidade_b.value}' as integer), 4106902))
)
select 'Tamanho (35%)' as pilar, lado, round(score_tamanho_mercado, 1) as nota from sel
union all select 'Poder Compra (30%)', lado, round(score_poder_compra, 1) from sel
union all select 'Dinamismo (20%)', lado, round(score_dinamismo, 1) from sel
union all select 'Maturidade (15%)', lado, round(score_maturidade_empresarial, 1) from sel
```

```sql comparativo_pib_serie
select
    ano_referencia as ano,
    case
        when codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade_a.value}' as integer), 3550308) then 'Cidade A'
        else 'Cidade B'
    end as lado,
    round(pib_real_mil_brl / 1e6, 2) as pib_real_bi
from sidralake.mart_inteligencia_mercado_municipal
where codigo_ibge_municipio in (coalesce(try_cast('${inputs.cidade_a.value}' as integer), 3550308), coalesce(try_cast('${inputs.cidade_b.value}' as integer), 4106902))
  and pib_real_mil_brl is not null
order by ano_referencia asc, lado asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<BarChart
			data={comparativo_pilares}
			x=pilar
			y=nota
			series=lado
			type=grouped
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0"
			yMax=115
			leftPadding=24
			rightPadding=44
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Cidade A': '#3b82f6', 'Cidade B': '#686e6c'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
			title="Pilares do Score IMS: Cidade A × Cidade B"
			subtitle="Notas normalizadas (0–100) · Cidade A em azul"
		/>
	</div>
	<div class="sl-card">
		<LineChart
			data={comparativo_pib_serie}
			x=ano
			y=pib_real_bi
			series=lado
			xFmt="0"
			yFmt="#,##0.0"
			markers=true
			rightPadding=24
			yGridlines=false
			xGridlines=false
			seriesColors={{'Cidade A': '#3b82f6', 'Cidade B': '#9ca3a0'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { min: 'dataMin', max: 'dataMax', minInterval: 1, axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			title="Trajetória do PIB Real (2018–2023)"
			subtitle="Valores constantes em R$ Bilhões · Linhas puras sem sombreado"
			yAxisTitle="R$ Bilhões"
		/>
	</div>
</div>

```sql tabela_head_to_head
select
    case
        when codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade_a.value}' as integer), 3550308) then 'Cidade A'
        else 'Cidade B'
    end as lado,
    nome_municipio || ' - ' || sigla_uf as municipio,
    rank_nacional_ims as rk_br,
    round(ims_score_0_100, 2) as ims,
    populacao_residente as populacao,
    round(pib_real_mil_brl / 1e6, 2) as pib_bi,
    round(pib_per_capita_real_brl, 0) as pib_pc,
    round(cagr_pib_real_3a_pct / 100.0, 4) as cagr_3a_pct,
    num_empresas_atuantes as empresas,
    round(salario_medio_real_brl, 0) as salario_real,
    round(taxa_assalariamento_formal, 4) as formalizacao_pct
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and codigo_ibge_municipio in (coalesce(try_cast('${inputs.cidade_a.value}' as integer), 3550308), coalesce(try_cast('${inputs.cidade_b.value}' as integer), 4106902))
order by lado asc
```

<ExecTable
	data={tabela_head_to_head}
	title="Quadro Comparativo Completo (Último Ano Completo)"
	subtitle="Destaque azul: Cidade A, Score IMS ≥ 85, Formalização ≥ 90% e CAGR ≥ +10%"
	rowsPerPage={10}
	highlightFirstRow={true}
	columns={[
		{ key: 'lado', label: 'Lado', kind: 'tier_badge', align: 'center' },
		{ key: 'municipio', label: 'Município', kind: 'primary' },
		{ key: 'rk_br', label: 'RK BR', kind: 'rank' },
		{ key: 'populacao', label: 'População', align: 'right', fmt: 'int' },
		{ key: 'pib_bi', label: 'PIB Real (Bi)', align: 'right', fmt: 'brl_bi2' },
		{ key: 'pib_pc', label: 'PIB Per Capita', align: 'right', fmt: 'brl_int' },
		{ key: 'cagr_3a_pct', label: 'CAGR 3A', align: 'right', kind: 'growth', highlightThreshold: 0.1 },
		{ key: 'empresas', label: 'Empresas', align: 'right', fmt: 'int' },
		{ key: 'salario_real', label: 'Salário Médio', align: 'right', fmt: 'brl_int' },
		{ key: 'formalizacao_pct', label: 'Formalização', align: 'right', kind: 'databar', fmt: 'pct1', barMax: 1, barThreshold: 0.9 },
		{ key: 'ims', label: 'Score IMS', align: 'right', kind: 'databar', fmt: 'dec2', barMax: 100, barThreshold: 85 }
	]}
/>
