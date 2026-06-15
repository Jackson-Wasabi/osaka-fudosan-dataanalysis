{#
  駅名正規化（D-006 の Step1+Step2）
  (1) 括弧除去（半角・全角） (2) 末尾の「駅」除去
  mapping CSV（Step3）はスカラーで表現できないため、各モデル側で
  station_name_mapping を LEFT JOIN し COALESCE で適用する。
  stg_transactions と stg_station_master で同一ロジックを共有するためのマクロ。
#}
{% macro normalize_station_name(col) %}
regexp_replace(
    regexp_replace(
        regexp_replace({{ col }}, r'\([^)]*\)', ''),
        r'（[^）]*）', ''
    ),
    r'駅$', ''
)
{% endmacro %}
