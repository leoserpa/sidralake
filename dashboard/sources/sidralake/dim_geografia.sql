select
    codigo_ibge_municipio,
    nome_municipio,
    codigo_uf,
    sigla_uf,
    nome_uf,
    codigo_regiao,
    sigla_regiao,
    nome_regiao,
    nome_regiao_imediata,
    nome_regiao_intermediaria
from read_parquet('sources/sidralake/data/dim_geografia.parquet')
