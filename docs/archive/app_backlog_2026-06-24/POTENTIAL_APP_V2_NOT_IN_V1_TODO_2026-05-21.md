# Potential App: v2-only items to assess for v1 backport

This note tracks functionality that exists in the Trondelag/v2 app branch and should be reviewed before deciding what belongs in the Bornholm/v1 app.

## Implemented in v2, not yet reviewed for v1

- Trondelag-only app shell with fixed default region and beta labelling.
- Zoom-adaptive H3 display for Trondelag R7/R6/R5.
- Trondelag establishment-area behavior using shared solar/wind establishment logic, without exposing R9 in the interactive app.
- Trondelag population buffers shown as dissolved polygon buffers from the 250 m population-grid/centroid proxy.
- Expanded solar filters for roads, culture, reindeer, coastal constraints, and electrical proximity feasibility.
- Electrical infrastructure handled as a positive proximity/feasibility rule, not as an exclusion buffer.
- Reindeer/reindrift controller for Trondelag solar and wind filtering.
- Social-acceptance layer display, impact tinting, and allocation-priority sliders using synthetic test data.
- Solar filter impact summary comparing unfiltered and filtered large-scale solar area.
- Separate `Markanvändning: skog` solar filter in v2. Trondelag uses a real N500 markdekke polygon source filtered to `objtype = Skog`, with the same source-GeoJSON, optional buffer, runtime geometry, and H3 aggregation flow as culture and protected-nature filters.
- Defensive Streamlit HTML map renderer that falls back to `st.iframe` when available and avoids a hard crash if `streamlit.components.v1` is unavailable.

## Backport checks before changing v1

- Decide whether v1 should remain Bornholm-only or adopt selected shared-shell controls from v2.
- For Bornholm forest filtering, prefer direct `forest`/`fredskov` inputs over the broader `protected_forest_habitat` factor, because that factor mixes forest, protected nature, and habitat cores.
- If adding the v2 forest filter to v1, use Bornholm's direct forest/fredskov polygon layer flow where possible.
- Validate Bornholm and Trondelag separately after any shared filter changes.
- Keep generated GIS outputs out of commits unless there is a clear handoff note explaining source and purpose.
