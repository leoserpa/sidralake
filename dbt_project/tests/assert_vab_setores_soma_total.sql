-- Reconciliacao setorial: soma dos 4 setores do VAB deve igualar o VAB Total
-- Tolera arredondamentos em milhares de reais do SIDRA 5938.
select
    codigo_ibge_municipio,
    ano_referencia,
    vab_total_mil_brl,
    (
        coalesce(vab_agropecuaria_mil_brl, 0.0)
        + coalesce(vab_industria_mil_brl, 0.0)
        + coalesce(vab_servicos_privados_mil_brl, 0.0)
        + coalesce(vab_adm_publica_mil_brl, 0.0)
    ) as soma_vab_setores
from {{ ref('fct_pib_municipal') }}
where vab_total_mil_brl is not null
    and abs(
        vab_total_mil_brl
        - (
            coalesce(vab_agropecuaria_mil_brl, 0.0)
            + coalesce(vab_industria_mil_brl, 0.0)
            + coalesce(vab_servicos_privados_mil_brl, 0.0)
            + coalesce(vab_adm_publica_mil_brl, 0.0)
        )
    ) > greatest(5.0, abs(vab_total_mil_brl) * 0.01)
