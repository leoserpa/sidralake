---
title: Raio-X Municipal (5.571 Cidades)
---

```sql ufs_cidade
select distinct sigla_uf, nome_uf
from sidralake.dim_geografia
order by sigla_uf
```

```sql cidades_da_uf
select
    g.codigo_ibge_municipio,
    g.nome_municipio,
    coalesce(m.populacao_residente, 0) as pop_ord
from sidralake.dim_geografia as g
left join sidralake.mart_inteligencia_mercado_municipal as m
    on g.codigo_ibge_municipio = m.codigo_ibge_municipio
   and m.is_ultimo_ano_completo
where g.sigla_uf = '${inputs.uf.value}'
order by pop_ord desc, g.nome_municipio asc
```

```sql perfil_cidade
select
    g.codigo_ibge_municipio,
    g.nome_municipio || ' - ' || g.sigla_uf as cidade_uf,
    g.sigla_uf,
    g.nome_regiao,
    g.nome_regiao_intermediaria,
    g.nome_regiao_imediata,
    m.rank_nacional_ims,
    m.rank_estadual_ims,
    m.ims_score_0_100,
    coalesce(m.tier_mercado, 'Emancipado 2024+') as tier_mercado,
    m.populacao_residente,
    round(m.pib_real_mil_brl / 1e6, 2) as pib_real_bi,
    round(m.pib_per_capita_real_brl, 0) as pib_pc_real,
    m.num_empresas_atuantes,
    round(m.salario_medio_real_brl, 0) as salario_medio_real
from sidralake.dim_geografia as g
left join sidralake.mart_inteligencia_mercado_municipal as m
    on g.codigo_ibge_municipio = m.codigo_ibge_municipio
   and m.is_ultimo_ano_completo
where g.codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
```

<CityHero data={perfil_cidade}>
	<Dropdown data={ufs_cidade} name=uf value=sigla_uf label=sigla_uf title="UF" defaultValue="SP" />
	<Dropdown data={cidades_da_uf} name=cidade value=codigo_ibge_municipio label=nome_municipio title="Município" defaultValue={3550308} />
</CityHero>

<div class="sl-kpi-grid-6">
	<KpiCard data={perfil_cidade} value="rank_nacional_ims" title="Rank Brasil (IMS)" fmt="rank" icon="trophy" subtitle="Entre 5.570 municípios" />
	<KpiCard data={perfil_cidade} value="rank_estadual_ims" title="Rank Estadual" fmt="rank" icon="mappin" subtitleCol="sigla_uf" subtitlePrefix="Posição na UF " />
	<KpiCard data={perfil_cidade} value="ims_score_0_100" title="Score IMS (0–100)" fmt="dec2" icon="gauge" subtitle="Média ponderada 4 pilares" />
	<KpiCard data={perfil_cidade} value="populacao_residente" title="População" fmt="pop_mi" icon="users" subtitleCol="populacao_residente" subtitleFmt="int" subtitlePrefix="IBGE · " subtitleSuffix=" hab" />
	<KpiCard data={perfil_cidade} value="pib_real_bi" title="PIB Real" fmt="brl_bi_exact" icon="landmark" subtitleCol="pib_pc_real" subtitleFmt="brl_int" subtitlePrefix="Per capita " />
	<KpiCard data={perfil_cidade} value="salario_medio_real" title="Salário Médio" fmt="brl_int" icon="wallet" subtitleCol="num_empresas_atuantes" subtitleFmt="int" subtitleSuffix=" empresas ativas" />
</div>

```sql serie_pib_cidade
select
    ano_referencia as ano,
    round(pib_real_mil_brl / 1e6, 3) as pib_real_bi
from sidralake.mart_inteligencia_mercado_municipal
where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
  and pib_real_mil_brl is not null
order by ano_referencia asc
```

```sql pilares_cidade
with raw_p as (
    select
        score_tamanho_mercado,
        score_poder_compra,
        score_dinamismo,
        score_maturidade_empresarial
    from sidralake.mart_inteligencia_mercado_municipal
    where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
      and is_ultimo_ano_completo
),
unpiv as (
    select 'Tamanho (35%)' as pilar, score_tamanho_mercado as nota from raw_p
    union all select 'Poder Compra (30%)', score_poder_compra from raw_p
    union all select 'Dinamismo (20%)', score_dinamismo from raw_p
    union all select 'Maturidade (15%)', score_maturidade_empresarial from raw_p
),
ranked as (
    select
        pilar,
        round(nota, 1) as nota,
        row_number() over (order by nota desc nulls last) as pos
    from unpiv
    where nota is not null
)
select
    pilar,
    nota,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<LineChart
			data={serie_pib_cidade}
			x=ano
			y=pib_real_bi
			xFmt="0"
			yFmt="#,##0.0"
			markers=true
			rightPadding=18
			yGridlines=false
			xGridlines=false
			colorPalette={['#3b82f6']}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, grid: { containLabel: true }, xAxis: { min: 'dataMin', max: 'dataMax', minInterval: 1, axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			title="Evolução do PIB Real (2018–2023)"
			subtitle="Valores constantes (R$ Bi · IPCA) · Linha limpa sem preenchimento"
			yAxisTitle="R$ Bilhões"
		/>
	</div>
	<div class="sl-card">
		<BarChart
			data={pilares_cidade}
			x=pilar
			y=nota
			series=destaque
			type=stacked
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
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
			title="Onde a cidade é mais forte no IMS?"
			subtitle="4 Pilares normalizados (0–100) · Pilar líder em azul"
		/>
	</div>
</div>

```sql vab_cidade
with raw_v as (
    select
        share_vab_agropecuaria,
        share_vab_industria,
        share_vab_servicos_privados,
        share_vab_adm_publica
    from sidralake.mart_inteligencia_mercado_municipal
    where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
      and ano_referencia = (
          select max(ano_referencia)
          from sidralake.mart_inteligencia_mercado_municipal
          where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
            and share_vab_servicos_privados is not null
      )
),
unpiv as (
    select 'Serviços Privados' as setor, round(share_vab_servicos_privados, 4) as share_pct from raw_v
    union all select 'Indústria', round(share_vab_industria, 4) from raw_v
    union all select 'Agropecuária', round(share_vab_agropecuaria, 4) from raw_v
    union all select 'Adm. Pública', round(share_vab_adm_publica, 4) from raw_v
),
ranked as (
    select
        setor,
        share_pct,
        row_number() over (order by share_pct desc nulls last) as pos
    from unpiv
    where share_pct is not null
)
select
    setor,
    share_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

```sql historico_cempre_cidade
select
    cast(cast(ano_referencia as integer) as varchar) as ano,
    num_empresas_atuantes as empresas,
    pessoal_ocupado_total as emprego,
    pessoal_ocupado_assalariado as assalariados,
    round(taxa_assalariamento_formal, 4) as formalizacao_pct,
    round(massa_salarial_real_mil_brl / 1e3, 1) as massa_mi,
    round(salario_medio_real_brl, 0) as salario_real,
    round(salario_medio_sm, 2) as salario_sm,
    round(crescimento_empresas_yoy_pct / 100.0, 4) as cresc_emp_pct,
    round(crescimento_emprego_yoy_pct / 100.0, 4) as cresc_trab_pct
from sidralake.mart_inteligencia_mercado_municipal
where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
  and num_empresas_atuantes is not null
order by ano_referencia desc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<BarChart
			data={vab_cidade}
			x=setor
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
			leftPadding=20
			rightPadding=44
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
			title="Qual é a vocação produtiva (VAB)?"
			subtitle="Participação no Valor Adicionado Bruto (%) · Último VAB IBGE (2021)"
		/>
	</div>
	<ExecTable
		data={historico_cempre_cidade}
		title="Tecido Empresarial Histórico (CEMPRE 2022–2024)"
		subtitle="Empresas atuantes, formalização e crescimento · Destaque azul: ano mais recente e YoY ≥ +8%"
		compact={true}
		rowsPerPage={10}
		highlightFirstRow={true}
		columns={[
			{ key: 'ano', label: 'Ano', kind: 'year' },
			{ key: 'empresas', label: 'Empresas', align: 'right', fmt: 'int' },
			{ key: 'emprego', label: 'Emprego', align: 'right', fmt: 'int' },
			{ key: 'formalizacao_pct', label: 'Formalização', align: 'right', kind: 'databar', fmt: 'pct1', barMax: 1, barThreshold: 0.9 },
			{ key: 'salario_real', label: 'Salário', align: 'right', fmt: 'brl_int' },
			{ key: 'cresc_emp_pct', label: 'Cresc. YoY', align: 'right', kind: 'growth', highlightThreshold: 0.08 }
		]}
	/>
</div>

```sql serie_pop_cidade
select
    ano_referencia as ano,
    populacao_residente as populacao
from sidralake.fct_populacao_municipal
where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
order by ano_referencia asc
```

```sql vizinhos_chart
select
    m.nome_municipio as municipio,
    round(m.ims_score_0_100, 1) as ims,
    case
        when m.codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308) then 'Cidade Selecionada'
        else 'Vizinhos'
    end as destaque
from sidralake.mart_inteligencia_mercado_municipal as m
where m.is_ultimo_ano_completo
  and m.nome_regiao_imediata = (
      select nome_regiao_imediata
      from sidralake.dim_geografia
      where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
  )
  and m.ims_score_0_100 is not null
order by m.ims_score_0_100 desc
limit 12
```

<div class="sl-grid-2">
	<div class="sl-card">
		<LineChart
			data={serie_pop_cidade}
			x=ano
			y=populacao
			xFmt="0"
			yFmt="#,##0"
			markers=true
			leftPadding=14
			rightPadding=18
			yGridlines=false
			xGridlines=false
			colorPalette={['#3b82f6']}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, grid: { left: 16, containLabel: true }, xAxis: { min: 'dataMin', max: 'dataMax', minInterval: 1, axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			title="Curva Demográfica (2018–2026)"
			subtitle="Censo 2022 + Estimativas IBGE · Série contínua sem área sombreada"
			yAxisTitle="Habitantes"
		/>
	</div>
	<div class="sl-card">
		<BarChart
			data={vizinhos_chart}
			x=municipio
			y=ims
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0"
			leftPadding=24
			rightPadding=34
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Cidade Selecionada': '#3b82f6', 'Vizinhos': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
			title="Benchmarking na Mesma Região Imediata"
			subtitle="Score IMS (0–100) · Cidade selecionada em azul pré-atentivo"
		/>
	</div>
</div>

```sql vizinhos_tabela
select
    m.rank_nacional_ims as rk_br,
    m.nome_municipio as municipio,
    m.populacao_residente as populacao,
    round(m.pib_real_mil_brl / 1e6, 2) as pib_bi,
    round(m.pib_per_capita_real_brl, 0) as pib_pc,
    m.num_empresas_atuantes as empresas,
    round(m.salario_medio_real_brl, 0) as salario_real,
    round(m.ims_score_0_100, 2) as ims
from sidralake.mart_inteligencia_mercado_municipal as m
where m.is_ultimo_ano_completo
  and m.nome_regiao_imediata = (
      select nome_regiao_imediata
      from sidralake.dim_geografia
      where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
  )
  and m.ims_score_0_100 is not null
order by m.ims_score_0_100 desc
limit 15
```

<ExecTable
	data={vizinhos_tabela}
	title="Municípios da Mesma Região Imediata"
	subtitle="Comparação direta contra os vizinhos econômicos mais próximos · Destaque azul: líder regional e IMS ≥ 85"
	rowsPerPage={15}
	highlightFirstRow={true}
	columns={[
		{ key: 'rk_br', label: 'RK BR', kind: 'rank' },
		{ key: 'municipio', label: 'Município', kind: 'primary' },
		{ key: 'populacao', label: 'População', align: 'right', fmt: 'int' },
		{ key: 'pib_bi', label: 'PIB Real (Bi)', align: 'right', fmt: 'brl_bi2' },
		{ key: 'pib_pc', label: 'PIB Per Capita', align: 'right', fmt: 'brl_int' },
		{ key: 'empresas', label: 'Empresas', align: 'right', fmt: 'int' },
		{ key: 'salario_real', label: 'Salário Médio', align: 'right', fmt: 'brl_int' },
		{ key: 'ims', label: 'Score IMS', align: 'right', kind: 'databar', fmt: 'dec2', barMax: 100, barThreshold: 85 }
	]}
/>
