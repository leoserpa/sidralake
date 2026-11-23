---
title: Clusters Setoriais por UF (CNAE 2.0 / CEMPRE)
---

Mapeamento do emprego formal e da massa salarial real por **Unidade da Federação e Seção CNAE 2.0** (tabela SIDRA `9418`). Quando o IBGE suprime células por sigilo estatístico (`X`), o pipeline preserva o indicador `has_sigilo_estatistico` e evita distorções nos denominadores de Quociente Locacional.

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

<Dropdown data={ufs_cnae} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
<Dropdown data={secoes_cnae} name=cnae value=codigo_secao_cnae title="Seção CNAE 2.0" defaultValue="TODAS" />

```sql kpis_cnae
select
    max(ano_referencia) as ultimo_ano,
    sum(pessoal_ocupado_total) as emprego_total,
    sum(num_empresas) as empresas_total,
    round(sum(massa_salarial_real_mil_brl) / 1e6, 2) as massa_real_bi,
    sum(case when has_sigilo_estatistico then 1 else 0 end) as celulas_sigilo_x
from sidralake.mart_clusters_setoriais_uf
where ano_referencia = (select max(ano_referencia) from sidralake.mart_clusters_setoriais_uf)
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
```

<BigValue data={kpis_cnae} value=ultimo_ano title="Ano CEMPRE" fmt="0" />
<BigValue data={kpis_cnae} value=emprego_total title="Pessoal Ocupado" fmt="#,##0" />
<BigValue data={kpis_cnae} value=massa_real_bi title="Massa Salarial Real (R$ Bi)" fmt="#,##0.00" />
<BigValue data={kpis_cnae} value=celulas_sigilo_x title="Células com Sigilo IBGE (X)" fmt="#,##0" />

---

## Maiores Participações Estaduais no Emprego Nacional por Setor

```sql top_shares_setoriais
select
    sigla_uf || ' · ' || codigo_secao_cnae as uf_setor,
    sigla_uf as uf,
    codigo_secao_cnae as cnae,
    descricao_secao_cnae as setor,
    pessoal_ocupado_total as emprego,
    round(market_share_uf_no_setor_pct, 2) as share_br_pct,
    round(massa_salarial_real_mil_brl / 1e6, 2) as massa_real_bi,
    round(crescimento_emprego_setor_yoy_pct, 2) as cresc_yoy_pct
from sidralake.mart_clusters_setoriais_uf
where ano_referencia = (select max(ano_referencia) from sidralake.mart_clusters_setoriais_uf)
  and market_share_uf_no_setor_pct is not null
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
order by market_share_uf_no_setor_pct desc
limit 20
```

<BarChart
    data={top_shares_setoriais}
    x=uf_setor
    y=share_br_pct
    swapXY=true
    sort=false
    title="Participação Estadual no Emprego Brasileiro do Setor (%)"
    yAxisTitle="Share no Brasil (%)"
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
    round(massa_salarial_real_mil_brl / 1e3, 2) as massa_real_mi,
    round(market_share_uf_no_setor_pct, 2) as share_br_pct,
    round(crescimento_emprego_setor_yoy_pct, 2) as cresc_yoy_pct,
    has_sigilo_estatistico as sigilo_x,
    perfil_especializacao as perfil
from sidralake.mart_clusters_setoriais_uf
where ano_referencia = (select max(ano_referencia) from sidralake.mart_clusters_setoriais_uf)
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.cnae.value}' = 'TODAS' or codigo_secao_cnae = '${inputs.cnae.value}')
order by pessoal_ocupado_total desc nulls last
```

<DataTable data={tabela_clusters} search=true rows=20 />
