select
    ano_mes,
    ano_referencia,
    mes_referencia,
    data_referencia,
    numero_indice_ipca,
    variacao_mensal_pct,
    variacao_acum_3m_pct,
    variacao_acum_6m_pct,
    variacao_acum_ano_pct,
    variacao_acum_12m_pct,
    ano_mes_base_deflator,
    fator_deflator_base_atual
from read_parquet('sources/sidralake/data/fct_ipca_mensal.parquet')
