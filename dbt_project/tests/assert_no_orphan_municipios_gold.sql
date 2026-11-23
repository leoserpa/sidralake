-- Integridade referencial: nenhum municipio nos fatos municipais pode ficar orfao na dim_geografia.
with municipios_fatos as (
    select distinct codigo_ibge_municipio from {{ ref('fct_pib_municipal') }}
    union
    select distinct codigo_ibge_municipio from {{ ref('fct_populacao_municipal') }}
    union
    select distinct codigo_ibge_municipio from {{ ref('fct_cempre_municipal') }}
)

select
    f.codigo_ibge_municipio
from municipios_fatos as f
left join {{ ref('dim_geografia') }} as g
    on f.codigo_ibge_municipio = g.codigo_ibge_municipio
    and g.is_current
where g.codigo_ibge_municipio is null
