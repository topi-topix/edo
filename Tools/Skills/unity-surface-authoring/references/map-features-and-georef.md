# 古地図から地形へ(道・水)/ 土地利用ゾーンでのプレハブ配置 / ジオリファレンス

## 5. Painting map features (roads / water) onto terrain

To stamp an Edo street network or waterways onto the terrain, extract them from a **georeferenced
old map** by colour, map map-pixels → world, and paint the splat. Discipline that avoids wasted paints:

1. **Preview the detection first.** Colour-threshold the map (e.g. Edo roads are the *yellow* lines;
   water is blue; lots are cream; temples pink) and write a highlight image where detected pixels are
   painted red — open it and confirm before touching the terrain.
2. **Correct world↔map mapping** (see §6) — for each alphamap texel: world→lat/lon
   (`GeoReference.UnityToLatLon`) → map uv → sample the map. Sample a small 3×3 neighbourhood in
   map space and vote, both to fight undersampling and to slightly widen thin lines.
3. Give the feature a distinct layer meaning (roads = compacted light bare earth; suppress grass on
   them). Repaint the whole alphamap including the feature so weights stay normalized.

Full walkthrough + thresholds in `references/recipes.md` → "Extract roads from map".

**Land-use classification (beyond roads).** An Edo 大絵図 colour-codes land use: yellow=road,
blue=water, pink/red=temple(寺社), cream=samurai estate(武家地), gray=commoner block(町人地),
green=field(田畑). Classify every map pixel by colour into these classes, then **block-fill**:
flood-fill regions bounded ONLY by road+water and assign each region its majority land-use class.
Crucial gotcha — do NOT treat text/labels (the "other/dark" class) as a fill barrier: if you do, the
kanji labels stay as dark speckle and fragment the block. Make barriers = road+water only, and let
text pixels be traversable + repainted with the region majority — the labels vanish cleanly.
This zoning map does double duty: a subtle per-class ground treatment now (commoner=packed earth,
samurai=earth+garden grass, temple=grassier, field=grass) AND the placement map for buildings later
(machiya on 町人地, yashiki on 武家地, halls on 寺社). Canonical implementation lives in the project:
`Assets/Edo/Scripts/Editor/EdoLandUse.cs` (classify + block-fill + bake) — read it before reimplementing.

**Persistent manual overrides (never lose hand edits).** Auto-classification is imperfect, so give the
user a way to correct it ("this is actually a road") that SURVIVES re-baking. The pattern: keep a
separate **override mask** asset (a PNG at alphamap resolution, one class id per texel, 0=auto). The
bake order is always: auto-classify → **apply override on top** → paint splat. Never let the user paint
straight onto the splat — a re-bake would wipe it. A Scene-view **brush** (raycast terrain → override
texel, paint a disc of the chosen class, with an in-window undo stack) makes this ergonomic. See
`Assets/Edo/Scripts/Editor/EdoLandUseBrush.cs`. Register `Undo.RegisterCompleteObjectUndo(terrainData)`
before every bake so the whole paint is revertable.

## 5b. Placing building/prop prefabs by land-use zone

The land-use map (§5) is also the **placement map** for buildings — reuse it, don't invent a new one.
Proven workflow (Japanese Village Kit / Japanese Castle Asset-Store packs, edo-unity Akasaka scene):

- **Query the class at a world point via reflection.** `EdoLandUse` lives in the *editor* assembly, so
  `System.Type.GetType("EdoLandUse")` returns **null** (NRE on the next `.GetMethod`). Use the
  assembly-qualified name: `System.Type.GetType("EdoLandUse, Assembly-CSharp-Editor") ?? System.Type.GetType("EdoLandUse")`.
  Then `BuildMapClasses(out W,out H,true)` → `byte[]` once, and `WorldToMapPixel(world,W,H,out px,out py)`
  → `cls[py*W+px]` per candidate. Class ids: ROAD=1,WATER=2,SAMURAI=3,COMMONER=4,TEMPLE=5,FIELD=6.
- **Match prefab to zone**: big estates (Manor 38×62, Big House) on SAMURAI(3), narrow machiya
  (House B 8.8×18.3, Small House) on COMMONER(4), temple halls on TEMPLE(5). Skip ROAD/WATER.
- **Seat on terrain**: `pos.y = terrain.SampleHeight(new Vector3(x,0,z)) + terrain.transform.position.y`
  (the `+transform.position.y` matters — this terrain sits at y=-35). Village Kit prefabs have
  **min.y ≈ -1.0** (geometry extends 1 m below pivot), so placing the pivot at ground height buries the
  base ~1 m — good, it hides gaps on slopes instead of floating.
- **Spacing**: keep a placed-points list and reject candidates closer than a min distance (≥55 m for
  manors, ≥20 m for machiya) — cheap Poisson-ish scatter. Seed `new System.Random(fixed)` for
  reproducibility. Snap rotation to `rng.Next(4)*90` for a tidy-ish look (true street alignment needs
  road-direction sampling — a later refinement).
- **Instantiate as prefab links** (`PrefabUtility.InstantiatePrefab`, not `Instantiate`) under one parent
  GameObject (e.g. `Edo_Buildings_Akasaka`) so the whole layer is easy to delete/re-run; then
  `EditorSceneManager.MarkSceneDirty`.
- **Asset-Store Edo packs (Edo Factory Village Kit / Castle) are URP-ready out of the box** — no pink
  materials, unlike the Waldemarst garden pack. Verify with a screenshot anyway.
- Akasaka scans ~70% SAMURAI — historically correct, so estate lots read as *sparse/scattered* from
  eye level; a denser townscape needs machiya packed into COMMONER strips + road alignment.
- **Street alignment (facade→road)**: at each candidate, sample the class at a ring of *world* offsets
  (radii 3→9 m, 24 angles) and take the first ROAD hit as `toRoad` — pure world-space sampling sidesteps
  all map-orientation/flip ambiguity. Keep only COMMONER cells whose nearest road is in a **frontage
  band** (3–7 m) so buildings hug the street edge, then `rotation = Quaternion.LookRotation(toRoad, up)`.
  Village Kit houses have their long axis on local **+Z**, so +Z→road puts the **narrow frontage on the
  street with the deep lot behind** — exactly the machiya arrangement. Speed: pre-bake the land-use class
  to a **world-space byte grid** (step 2 m over the district, via reflection once) and read that array in
  the ring scan — per-candidate reflection would be millions of calls and time out.
- **⚠️ FIRST check the terrain layers don't share a texture.** The #1 cause of "land-use bake does nothing
  visible" on this project: two `terrainData.terrainLayers` (e.g. `L_dirt` slot 0 and `L_bare` slot 2) were
  both pointing at the SAME diffuse (`edo_ground_pale`). The whole land-use system differentiates classes by
  shifting splat weight between dirt and bare — but if those two layers are the same image, every class
  (COMMONER/SAMURAI/OTHER) renders identically no matter what you bake, and no `ClassToSplat` weight tweak
  can ever help (I wasted a whole pass "biasing COMMONER to dirt vs SAMURAI to bare" — futile when dirt==bare).
  Verify up front: for each `td.terrainLayers[i]`, print `.diffuseTexture.name` and its avg RGB; if two earth
  layers match, that's the bug. Fix = assign a genuinely different texture to one layer (here: `L_dirt` →
  `T_FJG_Ground_Soil_01_Albedo`, a darker brown soil from the Waldemarst set, tileSize ~8), `SetDirty(layer)`
  + `SaveAssets()`. Only `_Splat1`(grass, green) and `_Splat3`(rock) were ever visually distinct; the two
  earth layers must be kept visibly different for districts to read. Decisive test that the control map even
  reaches the shader: reversibly `SetAlphamaps` a patch to 100% grass(layer1)/rock(layer3), Flush, render —
  if it turns green the pipeline is fine and the problem is texture sameness, not binding.
- **"Bake didn't work" is usually "bake worked but classes look identical"**: EdoLandUse.Bake paints the
  override PNG (R=class id) into the terrain alphamap. To *verify* a paint took effect, don't eyeball it —
  load `landuse_override.png`, confirm its dims == `td.alphamapResolution` (mismatch → `LoadOrCreateOverride`
  **silently discards it**), count painted pixels per R value, then sample `td.GetAlphamaps` **at exactly
  those painted pixels** and compare the mean splat weights to the class's `ClassToSplat` recipe. If they
  match, bake is fine and the real issue is that the class recipe is near-identical to its neighbours
  (e.g. all urban classes = compacted dirt) → no visible contrast. Fix is in `ClassToSplat`, not the bake.
  To make COMMONER read as a distinct district, bias it hard to one splat (dark `dirt`, ~0.70 weight) while
  SAMURAI leans pale `bare` + garden `grass` — keep a low-freq `nMacro` bare admixture (15–40%) so the dirt
  still breaks tiling. Verify the contrast numerically (town dirt≈0.70 vs samurai dirt≈0.25) AND visually.
- **OldMapOverlay hides the terrain in top-down shots**: an active `OldMapOverlay` quad sits above the
  terrain, so a straight-down ortho screenshot shows the *old map*, not your baked splat. Toggle it (and the
  buildings root) `SetActive(false)` around the render and restore after. Also: pure top-down at 90° reads
  bluish/flat from sky ambient with no direct sun — use a **low oblique** angle to judge true ground colour.
- **A tidy street-facing ROW (軒を連ねる) needs a road-PCA line, not per-building nearest-road.** Three tries,
  in order of quality: (1) per-building "direction to nearest ROAD" → orientations jitter building-to-building
  ("向きがあっちこっち") because the blobby road raster gives a different vector per cell — REJECT. (2) march each
  building perpendicular to the road edge and snap → hugs the road but STAGGERS on a bent road. (3) WINNER:
  collect ROAD cells near the area, run 2×2 PCA to get the road tangent `Dr` + centroid `Cr`, place buildings
  on a straight line `Cr + Dr*t` offset into the commoner side, ALL sharing one `Quaternion.LookRotation(faceN)`
  (faceN = toward road). Constrain the PCA collection to one side (e.g. `wx <= anchor.x`) so a perpendicular
  cross-street doesn't corrupt the tangent. Align the street-facing FAÇADES (not centres): set each building's
  centre to `Cr + Dr*tc + toComm*(baseOffset + depth*0.5)` so the front face lands at the constant
  `Cr + toComm*baseOffset` regardless of each prefab's depth — ragged backs, flush fronts, which is what reads.
  Advance `t` by that building's own frontage (`bounds.size.x`)+gap so varied widths still sit shoulder-to-shoulder.
  Correct for pivot offset: `pivot = centre - rot*bounds.center` (measure bounds at identity first).
- **Fit buildings to the terrain surface (they float after a manual XZ move)**: moving a placed building in XZ
  keeps its old Y, so it floats/sinks over new terrain height. Snap by the RENDERER BOUNDS BOTTOM, not the
  pivot: `groundY = terr.SampleHeight(bounds.center)+terr.pos.y; pos.y += (groundY - sink) - bounds.min.y;`
  (sink ≈ 0.3 m to hide the gap on uneven ground). Village Kit house pivots sit ~1 m ABOVE the mesh bottom
  (engawa stilts hang below), so Unity's native surface-snap (Shift+Cmd/Ctrl-drag onto the TerrainCollider)
  snaps the *pivot* and leaves the house ~1 m in the air — tell the user, and give them the bounds-based tool
  instead. Shipped `Assets/Edo/Scripts/Editor/EdoFitToGround.cs` = menu `Edo ▸ Fit Selected To Ground` (Ctrl+
  Shift+G): fits every selected object by bounds-bottom, multi-tile-aware, Undo-registered. Manual workflow =
  drag in XZ freely, then hotkey to drop to ground.
- **Correct grounding for Japanese houses = 石場建て (posts on stones, NOT buried).** A Village Kit house has
  short sub-floor posts (`column A small`, its lowest geometry) + a `stone Base` course (根石/foundation stones)
  higher up. Fitting the RENDERER-BOUNDS BOTTOM to grade puts the post feet at grade but leaves the stone course
  floating ~0.3 m in the air with a visible gap — reads wrong. Correct look: the **foundation stones rest ON the
  ground** (bottom ~0.05 m embedded), post feet on the earth, floor raised over a shallow crawlspace (床下, for
  ventilation) — never bury the posts (buried posts = 掘立, a different/older method). So fit by the lowest
  `stone`-named renderer's bottom → `groundY - 0.05`, not by `bounds.min`. `EdoFitToGround.cs` now does exactly
  this (stone-aware, falls back to bounds-bottom when no stone course exists). Applies to all raised-floor JP
  buildings, not just this kit.
- **Edo 町割り block cluster (perimeter machiya + central 井戸端)**: the authentic commoner-block layout is
  houses lining all 4 sides of a ~58 m block with frontages facing OUT to the streets, backs to the interior,
  and a communal well (会所地/井戸端) in the middle. Don't rely on road-raster flood-fill for the blocks — the
  interior alleys aren't classified ROAD so components merge into 60,000 m² blobs; instead overlay your OWN
  block grid (`Cb = A0 + u*(iu*pitch) + v*(iv*pitch)`, pitch = block 58 + street 16 ≈ 74 m) oriented to the
  main street axis `u`, and only build where `EFF(Cb)==COMMONER`. Per block: 4 sides, each a row via the
  street-row recipe with `outward` = away from centre as the facing normal; march the side axis, `place`
  choosing a random prefab and setting its centre `= edge - outward*(depth/2+gap)` so the frontage sits at the
  block edge and the deep lot runs inward; inset each row `corner≈7 m` from the block corners so adjacent sides
  don't collide. Block half-size `h=29` clears the deepest prefab (House B depth 18.3) so opposing backs leave
  a ~20 m interior for the well. No well prefab exists in the kit — compose one from primitives (a stone-mat
  cylinder curb + 2 wood posts + a beam) plus `bucket A` + `RiceBarrel_01`. ~15 machiya/block; a 2×2 district
  is ~60 buildings — cap deliberately, each house is 150-300 renderers.
- **Machiya vs mansion, and "赤坂1丁目 is 武家地"**: Village Kit has only 7 complete building prefabs (House,
  House A, House B, Small House = townhouses/町家; Big House, Manor = estates/屋敷; Village = a 126 m whole-cluster).
  For 町人地 rows use the first four (House B 8.8×18.3 = narrow-frontage machiya backbone), exclude the estates.
  Watch the history/label mismatch: modern **赤坂1丁目 was daimyo 武家地 in the Edo map** — the commoner town was
  the strip the user hand-painted (override R=COMMONER), which the auto old-map classifier calls 武家. Locate the
  town by the painted override, not the raw map. `GeoReference.LatLonToUnity(lat,lon)` converts a real address to
  world (Unity.x=East, z=North); use it to anchor "near <place>" requests.
- **Distribute, don't cap-in-iteration-order**: filling to an N-cap while marching the grid ix/iz fills
  the first (e.g. westmost) block solid and stops — one dense blob, rest empty. Instead **collect all
  frontage candidates, Fisher–Yates shuffle (seeded), then greedily place with a min-spacing** (≈11 m
  for machiya so 8.8 m-wide House B nearly touch; 55 m for estates). Even coverage across every street.

---

## 6. Georeferencing a map overlay correctly

Symptom seen: an old-map overlay was ~660 m off (Tameike/gates didn't line up) because the raw scan
was placed as a plain ±3000 m square at the world origin, ignoring the map's real geographic centre.

- The scene has a rigorous `Edo.Geo.GeoReference` (real lat/lon ↔ Unity world via JP Plane Rect IX).
  **Ground truth = the `GeoMarker` anchors** (landmarks placed from real coordinates).
- To place an overlay quad: compute the map's four **geographic corners** and set the quad's mesh
  vertices to `GeoReference.LatLonToUnity(lat,lon)` of each — do NOT assume an axis-aligned square
  (there's a small meridian-convergence rotation).
- The edo old-map raster is an **equirectangular** render about `geoCenter (139.74215, 35.67225)`,
  `±3000 m`, 3072 px, row0 = north (see `edo-map/scripts/export_oldmap_overlay.py` +
  `scratchpad_oldmap/meta.json` in the sibling `edo-map` project — that's where the georef source
  lives; it is NOT stored in the Unity project by default).
- **Verify** by projecting each anchor's world pos → map uv and drawing a dot on the map; zoom in and
  confirm the dot lands on the matching drawn landmark (castle keep inside the honmaru, 桜田門 on its
  gate, etc.). Details + formulas in `references/recipes.md` → "Georeference & verify".
