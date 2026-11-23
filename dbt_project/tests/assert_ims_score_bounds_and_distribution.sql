-- Garante que o Score IMS esteja estritamente em [0, 100], sem NaN/Inf,
-- e que nenhum municipio com dados completos de PIB + CEMPRE fique sem score.
select
    codigo_ibge_municipio,
    ano_referencia,
    ims_score_0_100
from {{ ref('mart_inteligencia_mercado_municipal') }}
where (
    ims_score_0_100 is not null
    and (
        isnan(ims_score_0_100)
        or isinf(ims_score_0_100)
        or ims_score_0_100 < 0.0
        or ims_score_0_100 > 100.0
    )
)
    or (
        pib_real_mil_brl is not null
        and num_empresas_atuantes is not null
        and ims_score_0_100 is null
    )
