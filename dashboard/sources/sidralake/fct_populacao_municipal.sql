select
    codigo_ibge_municipio,
    ano_referencia,
    populacao_residente,
    area_km2,
    densidade_demografica,
    origem_dado,
    is_interpolado
from read_parquet('sources/sidralake/data/fct_populacao_municipal.parquet')
