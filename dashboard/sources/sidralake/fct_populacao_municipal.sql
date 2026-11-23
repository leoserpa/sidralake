select
    codigo_ibge_municipio,
    ano_referencia,
    populacao_residente,
    area_km2,
    densidade_demografica,
    origem_dado,
    is_interpolado
from read_parquet('parquet_data/fct_populacao_municipal.parquet')
