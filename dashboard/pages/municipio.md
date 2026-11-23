---
title: Raio-X Municipal (5.571 Cidades)
---

Selecione qualquer **UF** e pesquise qualquer um dos **5.571 municípios brasileiros** para obter um dossiê executivo 360°: trajetória real do PIB, curva demográfica (2018–2026), diagnóstico dos 4 pilares do Score IMS, vocação produtiva (VAB), tecido empresarial (CEMPRE) e benchmarking contra os vizinhos da mesma Região Imediata.

```sql ufs_cidade
select distinct sigla_uf, nome_uf
from sidralake.dim_geografia
order by sigla_uf
```

<Dropdown data={ufs_cidade} name=uf value=sigla_uf label=sigla_uf title="UF" defaultValue="SP" />

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

<Dropdown data={cidades_da_uf} name=cidade value=codigo_ibge_municipio label=nome_municipio title="Município" defaultValue={3550308} />

```sql perfil_cidade
select
    g.codigo_ibge_municipio,
    g.nome_municipio || ' - ' || g.sigla_uf as cidade_uf,
    g.nome_regiao,
    g.nome_regiao_intermediaria,
    g.nome_regiao_imediata,
    m.ano_referencia,
    m.rank_nacional_ims,
    m.rank_estadual_ims,
    m.ims_score_0_100,
    m.tier_mercado,
    m.populacao_residente,
    round(m.densidade_demografica, 1) as densidade_hab_km2,
    round(m.pib_real_mil_brl / 1e6, 3) as pib_real_bi,
    round(m.pib_per_capita_real_brl, 0) as pib_pc_real,
    m.num_empresas_atuantes,
    m.pessoal_ocupado_total,
    round(m.salario_medio_real_brl, 0) as salario_medio_real,
    round(m.cagr_pib_real_3a_pct, 2) as cagr_3a_pct
from sidralake.dim_geografia as g
left join sidralake.mart_inteligencia_mercado_municipal as m
    on g.codigo_ibge_municipio = m.codigo_ibge_municipio
   and m.is_ultimo_ano_completo
where g.codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
```

### Ficha Executiva — <Value data={perfil_cidade} column=cidade_uf /> (<Value data={perfil_cidade} column=tier_mercado />)

**Região Imediata:** <Value data={perfil_cidade} column=nome_regiao_imediata /> · **Região Intermediária:** <Value data={perfil_cidade} column=nome_regiao_intermediaria /> · **Grande Região:** <Value data={perfil_cidade} column=nome_regiao />

<BigValue data={perfil_cidade} value=rank_nacional_ims title="Rank Brasil (IMS)" fmt="#,##0" />
<BigValue data={perfil_cidade} value=rank_estadual_ims title="Rank Estadual (IMS)" fmt="#,##0" />
<BigValue data={perfil_cidade} value=ims_score_0_100 title="Score IMS (0–100)" fmt="0.00" />
<BigValue data={perfil_cidade} value=populacao_residente title="População Residente" fmt="#,##0" />

<BigValue data={perfil_cidade} value=pib_real_bi title="PIB Real (R$ Bi)" fmt="#,##0.000" />
<BigValue data={perfil_cidade} value=pib_pc_real title="PIB Per Capita Real (R$)" fmt="#,##0" />
<BigValue data={perfil_cidade} value=num_empresas_atuantes title="Empresas Atuantes" fmt="#,##0" />
<BigValue data={perfil_cidade} value=salario_medio_real title="Salário Médio Real (R$)" fmt="#,##0" />

---

```sql serie_pib_cidade
select
    ano_referencia as ano,
    round(pib_real_mil_brl / 1e6, 3) as pib_real_bi,
    round(pib_per_capita_real_brl, 0) as pib_pc_real
from sidralake.mart_inteligencia_mercado_municipal
where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
  and pib_real_mil_brl is not null
order by ano_referencia asc
```

```sql serie_pop_cidade
select
    ano_referencia as ano,
    populacao_residente as populacao,
    origem_dado
from sidralake.fct_populacao_municipal
where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
order by ano_referencia asc
```

<Grid cols=2>
    <LineChart
        data={serie_pib_cidade}
        x=ano
        y=pib_real_bi
        xFmt="0"
        yFmt="#,##0.00"
        markers=true
        yGridlines=false
        xGridlines=false
        colorPalette={['#3b82f6']}
        title="Evolução do PIB Real (2018–2023)"
        subtitle="Valores constantes (R$ Bi · IPCA)"
        yAxisTitle="R$ Bilhões"
    />
    <AreaChart
        data={serie_pop_cidade}
        x=ano
        y=populacao
        xFmt="0"
        yFmt="#,##0"
        yGridlines=false
        xGridlines=false
        colorPalette={['#3b82f6']}
        title="Curva Demográfica (2018–2026)"
        subtitle="Censo 2022 + Estimativas IBGE"
        yAxisTitle="Habitantes"
    />
</Grid>

---

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
    select 'Tamanho de Mercado (35%)' as pilar, score_tamanho_mercado as nota from raw_p
    union all select 'Poder de Compra (30%)', score_poder_compra from raw_p
    union all select 'Dinamismo Econômico (20%)', score_dinamismo from raw_p
    union all select 'Maturidade Empresarial (15%)', score_maturidade_empresarial from raw_p
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
    select 'Serviços Privados' as setor, round(share_vab_servicos_privados * 100, 1) as share_pct from raw_v
    union all select 'Indústria', round(share_vab_industria * 100, 1) from raw_v
    union all select 'Agropecuária', round(share_vab_agropecuaria * 100, 1) from raw_v
    union all select 'Administração Pública', round(share_vab_adm_publica * 100, 1) from raw_v
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

<Grid cols=2>
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
        rightPadding=24
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Onde a cidade é mais forte no IMS?"
        subtitle="4 Pilares (0–100) · Pilar líder em azul"
    />
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
        labelFmt="0.0"
        rightPadding=24
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Qual é a vocação produtiva (VAB)?"
        subtitle="Participação (%) · Último VAB IBGE (2021)"
    />
</Grid>

---

## Benchmarking na Mesma Região Imediata

```sql vizinhos_regiao_imediata
select
    m.nome_municipio as municipio,
    m.rank_nacional_ims as rk_br,
    m.populacao_residente as populacao,
    round(m.pib_real_mil_brl / 1e6, 3) as pib_real_bi,
    round(m.pib_per_capita_real_brl, 0) as pib_pc_real,
    m.num_empresas_atuantes as empresas,
    round(m.salario_medio_real_brl, 0) as salario_medio_real,
    round(m.ims_score_0_100, 1) as ims,
    m.tier_mercado as tier,
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
limit 15
```

<BarChart
    data={vizinhos_regiao_imediata}
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
    rightPadding=24
    legend=false
    yGridlines=false
    xGridlines=false
    yAxisLabels=false
    yBaseline=false
    seriesColors={{'Cidade Selecionada': '#3b82f6', 'Vizinhos': '#525866'}}
    title="Como a cidade se posiciona frente aos vizinhos da Região Imediata?"
    subtitle="Score IMS (0–100) · Cidade selecionada em azul"
/>

<DataTable data={vizinhos_regiao_imediata} rows=15 />

---

## Tecido Empresarial Histórico (CEMPRE 2022–2024)

```sql historico_cempre_cidade
select
    ano_referencia as ano,
    num_unidades_locais as unidades_locais,
    num_empresas_atuantes as empresas_atuantes,
    pessoal_ocupado_total as pessoal_ocupado,
    pessoal_ocupado_assalariado as assalariados,
    round(taxa_assalariamento_formal * 100, 1) as formalizacao_pct,
    round(massa_salarial_real_mil_brl / 1e3, 2) as massa_real_mi,
    round(salario_medio_real_brl, 0) as salario_medio_real,
    round(salario_medio_sm, 2) as salario_sm,
    round(crescimento_empresas_yoy_pct, 1) as cresc_emp_yoy_pct,
    round(crescimento_emprego_yoy_pct, 1) as cresc_trab_yoy_pct
from sidralake.mart_inteligencia_mercado_municipal
where codigo_ibge_municipio = coalesce(try_cast('${inputs.cidade.value}' as integer), 3550308)
  and num_empresas_atuantes is not null
order by ano_referencia desc
```

<DataTable data={historico_cempre_cidade} />
