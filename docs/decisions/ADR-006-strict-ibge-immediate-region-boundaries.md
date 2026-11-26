# ADR-006: Strict Adherence to Official IBGE Immediate Geographic Regions (`Região Geográfica Imediata`)

## Status
Accepted

## Date
2026-11-25

## Context
In the **Raio-X Municipal** dashboard page (`dashboard/pages/municipio.md`), the **Benchmarking na Mesma Região Imediata** chart and **Municípios da Mesma Região Imediata** table compare a selected municipality against its regional peers. A concrete real-world question arose when inspecting **Amparo - SP (`3501905`)**: physically neighboring **Pedreira - SP (`3537107`)** does not appear in Amparo's peer table, raising the question of whether the SQL filter had a bug or whether proximity should be widened.

Inspecting `dim_geografia.parquet` confirmed the official IBGE territorial hierarchy:
- **Amparo (`3501905`)** belongs to **Região Geográfica Imediata de Amparo (`350048`)** — 5 municipalities (*Águas de Lindóia*, *Amparo*, *Lindóia*, *Monte Alegre do Sul*, *Serra Negra*) — within **Região Geográfica Intermediária de Campinas (`3510`)**.
- **Pedreira (`3537107`)** belongs to **Região Geográfica Imediata de Campinas (`350038`)** — 18 municipalities (*Campinas*, *Pedreira*, *Jaguariúna*, *Paulínia*, *Valinhos*, *Vinhedo*, etc.) — also within **Região Geográfica Intermediária de Campinas (`3510`)**.

IBGE defines *Regiões Geográficas Imediatas* based on functional urban-network poles (daily commuting, retail attraction, and service flows) rather than straight-line municipal border adjacency alone.

## Decision
Keep the **Municípios da Mesma Região Imediata** filter strictly bound to IBGE's official `nome_regiao_imediata` classification without adding ad-hoc distance overrides or silently switching the benchmark to `nome_regiao_intermediaria`. Users seeking arbitrary border-city comparisons (such as *Amparo* vs. *Pedreira*) use the dedicated **Comparador Head-to-Head** page (`/comparador/`).

## Alternatives Considered

### Switching the Benchmark Scope to `Região Geográfica Intermediária`
- **Pros:** Groups adjacent cities that sit on the border between two Immediate Regions (like *Amparo* and *Pedreira* inside `Campinas`).
- **Cons:** Dilutes tight functional clusters into oversized regions (Campinas Intermediate Region spans dozens of municipalities across very different economic hubs) and contradicts the IBGE *Região Imediata* label and IMS `rank_regional_ims` grain.
- **Rejected:** Blurs local economic benchmarking fidelity.

### Adding Geometric Radius Buffers (Haversine Distance) Around Municipal Centroids
- **Pros:** Captures physical neighbors regardless of administrative boundaries.
- **Cons:** Requires ingesting IBGE territorial centroids/malhas not present in the API v1 Localidades dataset and introduces arbitrary distance thresholds (`30 km`, `50 km`) decoupled from IBGE methodology.
- **Rejected:** Adds ungrounded heuristics where an official IBGE functional taxonomy already exists.

## Consequences
- **100% methodological fidelity:** Regional peer tables (`municipio.md`) and `rank_regional_ims` (`mart_inteligencia_mercado_municipal`) match official IBGE *Regiões Geográficas Imediatas* without hidden overrides.
- **Clear separation of use cases:** Functional immediate-region benchmarking lives in `/municipio/`; cross-boundary 1-to-1 comparison (*Amparo* × *Pedreira*) lives in `/comparador/`.
- **Documented nuance:** Both this ADR and the methodology docs explicitly clarify why bordering municipalities in different RGIs appear separately so future maintainers do not treat IBGE's division as a SQL bug.
