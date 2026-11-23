{% snapshot snap_ibge_cnae_secoes %}

{{
    config(
        target_schema='snapshots',
        unique_key='codigo_secao',
        strategy='check',
        check_cols=['descricao_secao', 'categoria_sidra_12762_id', 'observacoes'],
        invalidate_hard_deletes=True
    )
}}

select
    codigo_secao,
    descricao_secao,
    categoria_sidra_12762_id,
    observacoes
from {{ ref('stg_ibge__cnae_secoes') }}

{% endsnapshot %}
