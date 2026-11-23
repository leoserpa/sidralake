---
title: Clusters Setoriais & Emprego Formal (CNAE 2.0 / CEMPRE)
---

Análise setorial do **Cadastro Central de Empresas (CEMPRE — SIDRA 9418)** por **Unidade da Federação e 21 Seções CNAE 2.0** (série 2022–2024). Células suprimidas pelo IBGE por sigilo estatístico (`X`) são sinalizadas de forma transparente sem distorcer os denominadores nacionais.

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

<Dropdown data={anos_cempre} name=ano value=ano_referencia title="Ano CEMPRE" defaultValue={2024} />
<Dropdown data={ufs_cnae} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
<Dropdown data={secoes_cnae} name=cnae value=codigo_secao_cnae title="Seção CNAE 2.0" defaultValue="TODAS" />

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

<BigValue data={kpis_cnae} value=emprego_total title="Pessoal Ocupado" fmt="#,##0" />
<BigValue data={kpis_cnae} value=assalariados_total title="Assalariados Formais" fmt="#,##0" />
<BigValue data={kpis_cnae} value=empresas_total title="Empresas" fmt="#,##0" />
<BigValue data={kpis_cnae} value=massa_real_bi title="Massa Salarial Real (R$ Bi)" fmt="#,##0.00" />
<BigValue data={kpis_cnae} value=celulas_sigilo_x title="Células Sigilo IBGE (X)" fmt="#,##0" />

---

```sql top_shares_setoriais
with base as (
    select
        sigla_uf || ' · ' || codigo_secao_cnae as uf_setor,
        round(market_share_uf_no_setor_pct, 1) as share_br_pct,
        row_number() over (order by market_share_uf_no_setor_pct desc) as pos
    from sidralake.mart_clusters_setoriais_uf
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
      and market_share_uf_no_setor_pct is not null
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
      and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
    order by pos asc
    limit 12
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
        codigo_secao_cnae || ' · ' || left(descricao_secao_cnae, 26) as setor,
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
    limit 12
)
select
    setor,
    emprego_mi,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<Grid cols=2>
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
        labelFmt="0.0"
        rightPadding=24
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Quais UFs lideram o share setorial?"
        subtitle="Participação (%) no emprego do setor"
    />
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
        rightPadding=26
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Quais seções CNAE mais empregam?"
        subtitle="Pessoal ocupado formal (milhões)"
    />
</Grid>

---

## Mapa de Calor: Concentração Estadual por Seção CNAE 2.0 (Top 12 UFs)

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
    round(m.market_share_uf_no_setor_pct, 1) as share_pct
from sidralake.mart_clusters_setoriais_uf as m
inner join top_ufs as t
    on m.sigla_uf = t.sigla_uf
where m.ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
  and m.market_share_uf_no_setor_pct is not null
  and m.codigo_secao_cnae in ('A', 'C', 'F', 'G', 'H', 'I', 'J', 'K', 'M', 'N', 'P', 'Q')
order by m.sigla_uf asc, m.codigo_secao_cnae asc
```

<Heatmap
    data={heatmap_uf_cnae}
    x=cnae
    y=uf
    value=share_pct
    valueFmt="0.0"
    colorScale={['#1e293b', '#1d4ed8', '#3b82f6', '#93c5fd']}
    title="Participação Estadual (%) no Emprego Brasileiro por Seção CNAE"
    subtitle="A=Agro · C=Indústria · F=Construção · G=Comércio · H=Transporte · J=Tech/TI · K=Finanças · N=Adm · P=Educação · Q=Saúde"
/>

---

## Matriz Completa UF × Seção CNAE 2.0

```sql tabela_clusters
select
    ano_referencia as ano,
    sigla_uf as uf,
    nome_regiao as regiao,
    codigo_secao_cnae as cnae,
    descricao_secao_cnae as setor,
    num_empresas as empresas,
    pessoal_ocupado_total as emprego,
    pessoal_ocupado_assalariado as assalariados,
    round(massa_salarial_real_mil_brl / 1e3, 2) as massa_real_mi,
    round(market_share_uf_no_setor_pct, 2) as share_br_pct,
    round(crescimento_emprego_setor_yoy_pct, 2) as cresc_yoy_pct,
    has_sigilo_estatistico as sigilo_x,
    perfil_especializacao as perfil
from sidralake.mart_clusters_setoriais_uf
where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2024)
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
order by pessoal_ocupado_total desc nulls last
```

<DataTable data={tabela_clusters} search=true rows=20 />
