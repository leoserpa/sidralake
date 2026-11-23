{% snapshot snap_ibge_municipios %}

{{
    config(
        target_schema='snapshots',
        unique_key='codigo_ibge_municipio',
        strategy='check',
        check_cols=[
            'nome_municipio',
            'sigla_uf',
            'nome_uf',
            'nome_regiao_imediata',
            'nome_regiao_intermediaria'
        ],
        invalidate_hard_deletes=True
    )
}}

select
    codigo_ibge_municipio,
    nome_municipio,
    codigo_uf,
    sigla_uf,
    nome_uf,
    codigo_regiao,
    sigla_regiao,
    nome_regiao,
    codigo_regiao_imediata,
    nome_regiao_imediata,
    codigo_regiao_intermediaria,
    nome_regiao_intermediaria,
    codigo_microrregiao,
    nome_microrregiao,
    codigo_mesorregiao,
    nome_mesorregiao
from {{ ref('stg_ibge__localidades') }}

{% endsnapshot %}
