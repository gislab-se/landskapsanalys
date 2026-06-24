# Leaflet View Persistence Inventory For V3

Datum: 2026-06-09

Syfte: handoff från V2 till V3 för att hålla Leaflet-kartans zoomnivå och kartutsnitt stabila när användaren togglar overlays, source layers, buffer layers, result layers eller baslager.

Detta dokument inventerar V2. Ingen V2-implementation ändras här.

## Kort slutsats

V2 löser zoomhopp genom att skilja på tre saker:

1. Kartvy sparas separat i `window.localStorage` som `lat`, `lng` och `zoom`.
2. Overlay visibility sparas separat i `window.localStorage`.
3. `fitBounds` körs bara i en initial `fitInitialBounds()`-fas när ingen sparad vy finns.

Layer control i V2 får alltså ändra lager, legend och overlay-persistens, men den får inte ändra kartans center eller zoom. Baslagerbyte saknar egen handler och ändrar inte heller view.

Den viktigaste V3-regeln är: låt inte `rendered_snapshot` eller overlay-toggle trigga en ny automatisk `fitBounds` om regionen är samma och användaren redan har en sparad view.

## 1. Var styrs kartvy i V2?

### Primär renderer

Den relevanta renderern är `build_layered_hex_map_html()`:

- `apps/potential_model/map_rendering.py:133`

Den tar in:

- `center`
- `zoom`
- `bounds`
- `map_state_key`
- `map_reset_token`

Inputvärden serialiseras till JS här:

- `apps/potential_model/map_rendering.py:176` `layerSpecs`
- `apps/potential_model/map_rendering.py:177` `defaultCenter`
- `apps/potential_model/map_rendering.py:178` `defaultBounds`
- `apps/potential_model/map_rendering.py:180` `mapStateKey`
- `apps/potential_model/map_rendering.py:181` `mapResetToken`

### Initial center och zoom

V2 läser först eventuell sparad view:

- `apps/potential_model/map_rendering.py:277` `const savedView = readSavedView();`
- `apps/potential_model/map_rendering.py:279` `mapStartCenter = savedView ? [savedView.lat, savedView.lng] : defaultCenter`
- `apps/potential_model/map_rendering.py:280` `mapStartZoom = savedView ? savedView.zoom : zoom`
- `apps/potential_model/map_rendering.py:281` `L.map(...).setView(mapStartCenter, mapStartZoom)`

Det betyder:

- Finns sparad view används den direkt.
- Finns ingen sparad view används regionens default center och default zoom.
- `fitBounds` kan senare justera view, men bara i initialfasen och bara om ingen sparad view finns.

### Region-specifik default view

`potential_app.py` skickar regionens defaults till renderern:

- `potential_app.py:7447` `_render_layers(...)`
- `potential_app.py:7464` `center=list(region.get("default_map_center", [55.14, 14.92]))`
- `potential_app.py:7465` `zoom=int(region.get("default_zoom", 9))`
- `potential_app.py:7466` `bounds=region.get("default_map_bounds")`

Regionmanifesterna innehåller nu:

- `apps/potential_model/manifests/regions/bornholm.json:9` `default_map_center`
- `apps/potential_model/manifests/regions/bornholm.json:10` `default_map_bounds`
- `apps/potential_model/manifests/regions/bornholm.json:11` `default_zoom`
- `apps/potential_model/manifests/regions/trondelag.json:9` `default_map_center`
- `apps/potential_model/manifests/regions/trondelag.json:10` `default_zoom`
- `apps/potential_model/manifests/regions/vara.json:9` `default_map_center`
- `apps/potential_model/manifests/regions/vara.json:10` `default_zoom`

Bornholm har explicit `default_map_bounds`. Trøndelag och Vara har center/zoom men ingen default bounds i de träffar som inventerats.

### Bounds och fitBounds

För layered potential-kartan finns `fitInitialBounds()` här:

- `apps/potential_model/map_rendering.py:808`

Regeln är:

- Om `savedView` finns: spara om view och returnera direkt.
- Annars, om `defaultBounds` finns: `map.fitBounds(defaultBounds, { padding: [18, 18] })`.
- Annars, om renderade lager har giltiga bounds: `map.fitBounds(dataBounds.pad(0.04))`.
- Efter initial fit sparas view i localStorage.

Kodreferenser:

- `apps/potential_model/map_rendering.py:810` early return om `savedView`
- `apps/potential_model/map_rendering.py:814` kontroll av `defaultBounds`
- `apps/potential_model/map_rendering.py:815` `map.fitBounds(defaultBounds, { padding: [18, 18] })`
- `apps/potential_model/map_rendering.py:819` bygger `L.featureGroup(renderedLayers)`
- `apps/potential_model/map_rendering.py:822` `map.fitBounds(dataBounds.pad(0.04))`
- `apps/potential_model/map_rendering.py:824` `storeMapView()`
- `apps/potential_model/map_rendering.py:826` kör initial fit med `setTimeout(..., 80)`

Notera att fallback-fit görs mot `renderedLayers`, inte mot den just nu synliga overlaymängden. Det gör att bounds-underlaget är stabilt vid initial render och inte räknas om när användaren togglar synliga lager.

### MinZoom och maxZoom

V2 sätter ingen `minZoom` på `L.map(...)` i `build_layered_hex_map_html()`.

Tile layers har `maxZoom: 20`:

- `apps/potential_model/map_rendering.py:283` OSM
- `apps/potential_model/map_rendering.py:288` Satellite

Leaflet-kartan skapas med:

- `apps/potential_model/map_rendering.py:281` `L.map('map', { preferCanvas: true }).setView(...)`

### Persistens från app-sidan

V2 skickar en stabil map-state key från potential workspace:

- `potential_app.py:156` `MAP_VIEW_RESET_TOKEN_KEY = "potential_map_view_reset_token"`
- `potential_app.py:157` `MAP_STATE_VERSION = "establishment-start-v6"`
- `potential_app.py:2412` `_map_view_reset_token()`
- `potential_app.py:4494` `_map_panel_controls(...)`
- `potential_app.py:4566` returnerar `preserve_map_view=True` och reset token
- `potential_app.py:13431` `map_state_key=f"{region_id}:workspace:{MAP_STATE_VERSION}"`
- `potential_app.py:13432` skickar `map_reset_token`

Detta betyder att V2:s view-key är scopad per region och workspace-version, inte per analysresultat eller rendered snapshot.

## 2. Hur undviker V2 zoomhopp vid layer-toggle?

V2 använder Leaflet layer control:

- `apps/potential_model/map_rendering.py:619` `L.control.layers({ 'OSM': osm, 'Satellite': satellite }, overlays, { collapsed: true }).addTo(map)`

Overlay-events finns här:

- `apps/potential_model/map_rendering.py:632` `map.on('overlayadd', ...)`
- `apps/potential_model/map_rendering.py:641` `map.on('overlayremove', ...)`

I dessa handlers gör V2 bara:

- synkar eventuella auto-familjer för zoombaserade lager
- sparar overlay visibility
- uppdaterar legend

De kör inte:

- `fitBounds`
- `setView`
- `panTo`
- `flyTo`
- återställning med `getCenter()` eller `getZoom()`

Det finns ingen `baselayerchange`-handler i den inventerade layered renderern. Baslagerbyte hanteras av Leaflet som ren klient-side lagerändring.

### Mekanismen i praktiken

V2 undviker zoomhopp genom negativ kontroll:

- `fitBounds` ligger inte i overlay-events.
- `fitBounds` ligger bara i `fitInitialBounds()`.
- `fitInitialBounds()` hoppar över fit om `savedView` finns.
- Efter första initiala fit sparas view, så nästa HTML-render i samma `map_state_key` startar från samma view och gör early return.

### Overlay toggle är klient-side

Leaflet layer control kör i komponentens HTML/JS. Toggling av overlays i layer control triggar inte en Streamlit-rerun i sig.

Streamlit-reruns kan fortfarande ske av andra widgets, men då återanvänder V2 samma `map_state_key` och läser sparad view.

### `default_visible` jämfört med senare toggles

V2 använder `default_visible` bara när ingen sparad overlay visibility finns.

För vanliga layers:

- `apps/potential_model/map_rendering.py:506` läser sparad overlay visibility
- `apps/potential_model/map_rendering.py:508` fallback till `spec.default_visible !== false`
- `apps/potential_model/map_rendering.py:510` lägger till layer om den ska synas

För auto-familjer:

- `apps/potential_model/map_rendering.py:610` läser sparad overlay visibility
- `apps/potential_model/map_rendering.py:612` fallback till `family.defaultVisible`
- `apps/potential_model/map_rendering.py:614` lägger till controller om den ska synas

Senare toggles vinner alltså över defaultvärden via localStorage.

## 3. localStorage / view persistence

### Använder V2 localStorage?

Ja. V2 använder `window.localStorage` i layered renderern:

- `apps/potential_model/map_rendering.py:185` `browserStorage()`
- `apps/potential_model/map_rendering.py:187` `const storage = window.localStorage`
- `apps/potential_model/map_rendering.py:197` `const viewStorage = browserStorage()`

`browserStorage()` testar att storage fungerar genom att skriva och ta bort en testnyckel.

### Keys

Alla keys byggs av:

- `apps/potential_model/map_rendering.py:199` `storageKey(kind)`
- `apps/potential_model/map_rendering.py:200` `'regional-energy-potential:' + mapStateKey + ':' + kind`

Med normal workspace-rendering blir mönstret:

```text
regional-energy-potential:<region_id>:workspace:establishment-start-v6:view
regional-energy-potential:<region_id>:workspace:establishment-start-v6:overlays
regional-energy-potential:<region_id>:workspace:establishment-start-v6:reset-token
```

Exempel:

```text
regional-energy-potential:bornholm:workspace:establishment-start-v6:view
regional-energy-potential:trondelag:workspace:establishment-start-v6:view
regional-energy-potential:vara:workspace:establishment-start-v6:view
```

### Vad sparas?

View sparas som JSON:

- `lat`
- `lng`
- `zoom`

Kod:

- `apps/potential_model/map_rendering.py:262` `storeMapView()`
- `apps/potential_model/map_rendering.py:266` `map.getCenter()`
- `apps/potential_model/map_rendering.py:272` `map.getZoom()`

Overlay visibility sparas separat som JSON-dict med overlay-namn till boolean:

- `apps/potential_model/map_rendering.py:622` `storeOverlayVisibility()`
- `apps/potential_model/map_rendering.py:630` skriver `storageKey('overlays')`

V2 sparar inte bounds som egen view-state. Bounds används bara som initial fallback.

Baslager-valet OSM/Satellite verkar inte sparas i den här layered renderern.

### När läses värdena tillbaka?

View:

- `apps/potential_model/map_rendering.py:220` `readSavedView()`
- `apps/potential_model/map_rendering.py:225` läser `storageKey('view')`
- `apps/potential_model/map_rendering.py:229` läser `lat`
- `apps/potential_model/map_rendering.py:230` läser `lng`
- `apps/potential_model/map_rendering.py:231` läser `zoom`
- `apps/potential_model/map_rendering.py:233` validerar intervall

Overlay visibility:

- `apps/potential_model/map_rendering.py:244` `readSavedOverlayVisibility()`
- `apps/potential_model/map_rendering.py:249` läser `storageKey('overlays')`

### När reset:as de?

V2 har en reset-token:

- `apps/potential_model/map_rendering.py:203` `applyResetToken()`
- `apps/potential_model/map_rendering.py:207` token key
- `apps/potential_model/map_rendering.py:210` tar bort `storageKey('view')`
- `apps/potential_model/map_rendering.py:211` tar bort `storageKey('overlays')`
- `apps/potential_model/map_rendering.py:212` sparar ny token

Om token ändras rensas både view och overlay visibility.

App-sidan definierar token-key:

- `potential_app.py:156` `MAP_VIEW_RESET_TOKEN_KEY`
- `potential_app.py:2412` `_map_view_reset_token()`

I den inventerade koden hittas ingen aktiv increment/reset-knapp för denna token. Mekanismen finns, men normalflödet verkar använda token `0`.

### Scope

View-state scope i V2 är:

- region
- workspace
- statisk map-state version

Den är inte scopad per:

- scenario
- draft/widget state
- rendered snapshot id
- layer visibility
- source/buffer/result kombination

Det är viktigt. Om V3 inkluderar rendered snapshot-id i view-key kommer kartan ofta sakna sparad view efter varje apply och då göra ny fit. Det är exakt den typen av beteende som kan skapa hopp.

### Debounce eller throttle

Det finns ingen egen debounce/throttle runt localStorage-skrivning.

V2 lyssnar på Leaflet-events som redan sker när interaktionen är klar:

- `apps/potential_model/map_rendering.py:650` `map.on('moveend', storeMapView)`
- `apps/potential_model/map_rendering.py:651` `map.on('zoomend', ...)`
- `apps/potential_model/map_rendering.py:654` `storeMapView()`

Overlay-events sparar bara overlay visibility, inte view.

## 4. När får V2 använda fitBounds?

För den layered potential-kartan gäller:

| Situation | V2-beteende |
| --- | --- |
| Första render utan sparad view | Får köra `fitBounds` mot `defaultBounds` eller renderade lager |
| Första render med sparad view | Kör inte `fitBounds` |
| Regionbyte | Annan `map_state_key`, så ingen sparad view för nya regionen om användaren inte varit där tidigare |
| Ny analys/applied state i samma region | Bevarar view via samma `map_state_key`; `fitInitialBounds()` returnerar tidigt |
| Resultatlager ändras | Får inte i sig trigga ny fit om sparad view finns |
| Overlay toggle | Kör aldrig `fitBounds` |
| Baslagerbyte OSM/Satellite | Kör aldrig `fitBounds` |
| Explicit reset-token ändras | Rensar view/overlays; nästa render får använda initial fit igen |

V2 använder alltså inte regeln "fit to visible overlays after render". Den använder regeln "fit once when no persisted view exists".

## 5. Skillnad mellan initial render och UI-only layer toggle

### Initial render

V2 väljer view så här:

1. Försök läsa sparad `lat`, `lng`, `zoom` från localStorage.
2. Om sparad view finns: `setView(savedCenter, savedZoom)`.
3. Om sparad view saknas: `setView(defaultCenter, defaultZoom)`.
4. Efter kort timeout: kör `fitInitialBounds()`.
5. `fitInitialBounds()` gör ingenting om sparad view fanns.
6. Om ingen sparad view fanns: fit till regionens `default_map_bounds`, annars till alla renderade lagers bounds.
7. Spara slutlig view.

### UI-only toggle i Leaflet layer control

När användaren togglar overlay:

- Leaflet lägger till eller tar bort overlay-lagret.
- V2 sparar overlay visibility.
- V2 uppdaterar legend.
- V2 ändrar inte Streamlit state.
- V2 ändrar inte center eller zoom.
- V2 kör inte `fitBounds`.

När användaren byter baslager:

- Leaflet byter tile layer.
- V2 har ingen extra `baselayerchange`-logik.
- Center och zoom lämnas oförändrade.

### Applied update efter `Använd ändringar`

När workspace renderas på nytt i samma region:

- kart-HTML byggs om
- `map_state_key` är fortfarande `"<region_id>:workspace:establishment-start-v6"`
- JS läser sparad view
- `fitInitialBounds()` ser `savedView` och returnerar utan ny fit

Det gör att nya applied/result layers kan bytas ut utan att kartan automatiskt hoppar tillbaka till nya visible overlay-bounds.

### UI-only Streamlit-rerun

V2 har också ett cached/reused workspace-flöde:

- `potential_app.py:2207` `_ui_only_rerun_requested()`
- `potential_app.py:11674` `_render_reused_workspace_outputs(...)`
- `potential_app.py:11699` skickar samma typ av `map_state_key`
- `potential_app.py:12685` kontrollerar UI-only rerun

Detta gör att UI-only ändringar kan återanvända senaste beräknade map/potential i stället för att bygga ny analys. Kartans view bevaras ändå av samma localStorage-mekanism.

## 6. Rekommendation till V3

V3 bör porta V2:s modell nästan rakt av.

### Ta bort automatisk fitBounds efter varje render

V3 gör i dag `fitBounds` på visible overlays efter render. Det bör ändras.

Rekommenderad regel:

- Kör `fitBounds` bara i en initialiseringsfunktion.
- Kör den bara om ingen sparad view finns.
- Fit:a i första hand till regionens default bounds.
- Fit:a i andra hand till ett stabilt bounds-underlag från hela rendered snapshot, inte bara visible overlays.
- Kör aldrig `fitBounds` från `overlayadd`, `overlayremove` eller `baselayerchange`.

### Spara view i localStorage

V3 bör spara:

- `lat`
- `lng`
- `zoom`

V3 kan också spara overlay visibility, men det ska vara separat från view.

### Föreslagna keys

Nycklarna bör vara stabila inom regionen:

```text
landskapspotential:v3:<region_id>:map:<view_version>:view
landskapspotential:v3:<region_id>:map:<view_version>:overlays
landskapspotential:v3:<region_id>:map:<view_version>:reset-token
```

Exempel:

```text
landskapspotential:v3:skaraborg:map:v1:view
landskapspotential:v3:skaraborg:map:v1:overlays
landskapspotential:v3:skaraborg:map:v1:reset-token
```

Undvik:

```text
landskapspotential:v3:<region_id>:<rendered_snapshot_id>:view
```

Det skulle göra att varje ny applied snapshot saknar sparad view och därför riskerar att fit:a om kartan.

### Scope

Rekommenderad scope:

- `region_id`
- app/map-kontraktversion, exempelvis `v1`
- eventuell explicit reset-token

Inte i view-key:

- draft state
- widget keys
- selected technology
- parameter values
- rendered snapshot id
- visible layer set

Om V3 behöver kunna reseta vid större kontraktsändring, höj `view_version` eller ändra reset-token.

### Skillnad mellan first render, new applied snapshot och layer toggle

V3 bör ha denna state machine:

| Händelse | View-regel |
| --- | --- |
| First render för region utan sparad view | `setView(defaultCenter, defaultZoom)`, sedan optional initial fit |
| First render för region med sparad view | `setView(savedCenter, savedZoom)`, ingen fit |
| Layer toggle | Ändra bara Leaflet layer visibility, ingen fit |
| Base layer toggle | Ändra bara tile layer, ingen fit |
| Draftändring | Ingen kartändring före apply |
| Apply i samma region | Bygg ny rendered snapshot, bevara saved view, ingen fit |
| Regionbyte | Annan region-key; default view eller sparad view för just den regionen |
| Explicit reset | Rensa view/overlays; nästa render får initial fit |

### Events V3 bör använda

Använd:

- `moveend` för att spara view
- `zoomend` för att spara view och eventuellt uppdatera zoomberoende symboler
- `overlayadd` för att spara overlay visibility och uppdatera legend/status
- `overlayremove` för att spara overlay visibility och uppdatera legend/status
- `baselayerchange` bara om V3 vill spara baslager-val, inte för view

Använd inte dessa events för att ändra zoom eller center:

- `overlayadd`
- `overlayremove`
- `baselayerchange`
- draft/widget change events

### Applied/rendered snapshot

V3:s `rendered_snapshot.layers` ska kunna bytas ut när användaren trycker `Använd ändringar`, men kartvyn ska inte vara en derivata av visible layers.

Layer-status, source/buffer/result-lager och styles får komma från applied/rendered snapshot. View-state ska komma från:

- region defaults
- saved browser view
- explicit reset-token

Inte från draft/widgetkeys.

## 7. Minimal kod/pseudokod

Detta är V3-pseudokod anpassad efter V2:s faktiska mekanism:

```js
const mapStateKey = `landskapspotential:v3:${regionId}:map:v1`;
const viewKey = `${mapStateKey}:view`;
const overlaysKey = `${mapStateKey}:overlays`;
const resetTokenKey = `${mapStateKey}:reset-token`;

function storage() {
  try {
    const s = window.localStorage;
    const testKey = `${mapStateKey}:__test__`;
    s.setItem(testKey, "1");
    s.removeItem(testKey);
    return s;
  } catch (error) {
    return null;
  }
}

const store = storage();

function applyResetToken(resetToken) {
  if (!store) return false;
  const previous = store.getItem(resetTokenKey);
  const next = String(resetToken ?? 0);
  if (previous !== null && previous !== next) {
    store.removeItem(viewKey);
    store.removeItem(overlaysKey);
    store.setItem(resetTokenKey, next);
    return true;
  }
  store.setItem(resetTokenKey, next);
  return false;
}

const resetRequested = applyResetToken(mapResetToken);

function loadView() {
  if (!store || resetRequested) return null;
  try {
    const value = JSON.parse(store.getItem(viewKey) || "null");
    const lat = Number(value?.lat);
    const lng = Number(value?.lng);
    const zoom = Number(value?.zoom);
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || !Number.isFinite(zoom)) return null;
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
    return { lat, lng, zoom };
  } catch (error) {
    return null;
  }
}

function saveView() {
  if (!store) return;
  const center = map.getCenter();
  store.setItem(viewKey, JSON.stringify({
    lat: center.lat,
    lng: center.lng,
    zoom: map.getZoom()
  }));
}

const savedView = loadView();
const startCenter = savedView ? [savedView.lat, savedView.lng] : defaultCenter;
const startZoom = savedView ? savedView.zoom : defaultZoom;

const map = L.map("map", { preferCanvas: true }).setView(startCenter, startZoom);

const osm = L.tileLayer(osmUrl, { maxZoom: 20 });
const satellite = L.tileLayer(satelliteUrl, { maxZoom: 20 });
osm.addTo(map);

const overlays = buildOverlays(renderedSnapshot.layers);
L.control.layers({ OSM: osm, Satellite: satellite }, overlays, { collapsed: true }).addTo(map);

function fitInitialBounds() {
  map.invalidateSize();

  if (savedView) {
    saveView();
    return;
  }

  if (defaultBounds && defaultBounds.length === 2) {
    map.fitBounds(defaultBounds, { padding: [18, 18] });
    saveView();
    return;
  }

  const allRenderedLayers = Object.values(overlays);
  const group = L.featureGroup(allRenderedLayers);
  const dataBounds = group.getBounds();
  if (dataBounds && dataBounds.isValid()) {
    map.fitBounds(dataBounds.pad(0.04));
  }

  saveView();
}

setTimeout(() => {
  fitInitialBounds();
  refreshScalablePointMarkers();
}, 80);

map.on("moveend", saveView);

map.on("zoomend", () => {
  syncZoomDependentLayers();
  refreshScalablePointMarkers();
  saveView();
});

map.on("overlayadd", (event) => {
  syncAutoFamilyIfNeeded(event.layer);
  saveOverlayVisibility();
  updateLegendContent();
  // Do not call fitBounds(), setView(), flyTo() or panTo().
});

map.on("overlayremove", (event) => {
  clearAutoFamilyIfNeeded(event.layer);
  saveOverlayVisibility();
  updateLegendContent();
  // Do not call fitBounds(), setView(), flyTo() or panTo().
});

map.on("baselayerchange", () => {
  saveBaseLayerChoiceIfV3WantsIt();
  // Do not change zoom or center.
});
```

Om V3 vill ha "reset map view" kan den bara öka `mapResetToken`. Det är bättre än att baka in snapshot-id i view-key.

## 8. Testfall för V3

Föreslagna AppTest/blocktest:

1. `test_overlay_toggle_does_not_change_view`
   - Rendera karta med saved eller observerad initial view.
   - Toggle source layer av/på.
   - Assert: `map.getZoom()` och `map.getCenter()` är oförändrade inom tolerans.
   - Assert: ingen `fitBounds`-call sker från `overlayadd` eller `overlayremove`.

2. `test_buffer_overlay_toggle_does_not_change_view`
   - Rendera source och buffer separat.
   - Toggle buffer av/på.
   - Assert: view oförändrad.
   - Assert: source visibility påverkas inte av buffer toggle.

3. `test_result_overlay_toggle_does_not_change_view`
   - Rendera result layer med source/buffer overlays.
   - Toggle result av/på.
   - Assert: view oförändrad.

4. `test_base_layer_toggle_does_not_change_view`
   - Byt OSM till Satellite och tillbaka.
   - Assert: center och zoom oförändrade.
   - Assert: ingen `fitBounds`, `setView`, `flyTo` eller `panTo` körs av `baselayerchange`.

5. `test_draft_change_does_not_update_map_before_apply`
   - Ändra draft-parameter i sidopanel.
   - Assert: `rendered_snapshot.layers` är oförändrad.
   - Assert: kartans view och layer set är oförändrade.

6. `test_apply_updates_rendered_snapshot_but_preserves_view_for_same_region`
   - Sätt view till en känd center/zoom.
   - Ändra draft och tryck `Använd ändringar`.
   - Assert: `rendered_snapshot.layers` uppdateras.
   - Assert: same-region view läses från localStorage och bevaras.
   - Assert: initial `fitBounds` returnerar tidigt när saved view finns.

7. `test_region_change_uses_region_default_or_region_saved_view`
   - Spara view för region A.
   - Byt till region B.
   - Assert: region B använder sin egen saved view om den finns, annars `default_map_center`/`default_zoom` och eventuell initial bounds fit.
   - Assert: region A:s view-key läses inte för region B.

8. `test_local_storage_reset_only_on_region_or_reset_token`
   - Rendera samma region med ny rendered snapshot men samma reset-token.
   - Assert: view-key är samma och view bevaras.
   - Ändra reset-token.
   - Assert: `view` och `overlays` rensas och nästa render får initial fit.

9. `test_visible_overlay_set_does_not_define_fit_bounds_after_first_render`
   - Rendera med flera overlays där en har mycket större bounds.
   - Toggle synliga overlays.
   - Assert: view ändras inte.
   - Assert: om initial fit behövs används region default bounds eller stabilt all-rendered-layers-underlag, inte nuvarande visible overlay-set.

10. `test_overlay_visibility_persistence_is_separate_from_view_persistence`
    - Toggle ett lager av.
    - Panorera/zooma kartan.
    - Rendera om samma region.
    - Assert: overlay visibility återställs från overlay-key.
    - Assert: center/zoom återställs från view-key.

## Portningsregel i en mening

V3 ska behandla Leaflet layer control som UI-only lagerstyrning och behandla kartvy som separat, region-scopad browser state; `fitBounds` får bara användas som initial fallback när ingen sparad view finns eller när användaren uttryckligen reset:ar kartvyn.
