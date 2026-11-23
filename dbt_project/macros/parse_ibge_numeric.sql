{#
  Macros oficiais de tratamento semantico dos codigos especiais do SIDRA/IBGE:
    '-'   -> 0.0 (zero exato, nao resultante de arredondamento)
    '..'  -> NULL (nao se aplica)
    '...' -> NULL (dado nao disponivel)
    'X'   -> NULL (dado omitido para evitar desidentificacao / sigilo estatistico)
    ''    -> NULL (ausente)
#}

{% macro parse_ibge_value(col_name) -%}
    case
        when trim({{ col_name }}) = '-' then 0.0::double
        when trim({{ col_name }}) in ('..', '...', 'X', '') or {{ col_name }} is null then null::double
        else try_cast(replace(trim({{ col_name }}), ',', '.') as double)
    end
{%- endmacro %}

{% macro parse_ibge_status(col_name) -%}
    case
        when trim({{ col_name }}) = '-' then 'ZERO_EXATO'
        when trim({{ col_name }}) = '..' then 'NAO_SE_APLICA'
        when trim({{ col_name }}) = '...' then 'NAO_DISPONIVEL'
        when trim({{ col_name }}) = 'X' then 'SIGILO_ESTATISTICO'
        when trim({{ col_name }}) = '' or {{ col_name }} is null then 'AUSENTE'
        when try_cast(replace(trim({{ col_name }}), ',', '.') as double) is not null then 'VALIDO'
        else 'INVALIDO'
    end
{%- endmacro %}
