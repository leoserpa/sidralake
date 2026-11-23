select
    codigo_secao,
    descricao_secao,
    categoria_sidra_12762_id
from read_parquet('parquet_data/dim_cnae.parquet')
