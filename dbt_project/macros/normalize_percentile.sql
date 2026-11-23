{#
  Normalizacao robusta por percentis (winsorizacao) na escala [0, 100] dentro de uma particao.
  Evita que outliers extremos (ex.: Sao Paulo/SP) comprimam a escala dos demais municipios.
#}
{% macro normalize_winsorized(expr, low_col, high_col) -%}
    case
        when {{ expr }} is null then null::double
        when {{ high_col }} is null or {{ low_col }} is null then null::double
        when {{ high_col }} <= {{ low_col }} then 50.0::double
        else least(
            100.0::double,
            greatest(
                0.0::double,
                (
                    (least(greatest({{ expr }}, {{ low_col }}), {{ high_col }}) - {{ low_col }})
                    / nullif({{ high_col }} - {{ low_col }}, 0.0)
                ) * 100.0
            )
        )
    end
{%- endmacro %}
