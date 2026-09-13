# 詳細植生 — メッシュ交差クアッドはビルボードに勝る

## 4. Detail vegetation — mesh crossed-quads beat billboards

Grass added as `DetailRenderMode.GrassBillboard` looks like flat pasted cards when viewed from an
oblique/top-down angle, because billboards rotate to face the camera. The fix that reads as real 3D
from any angle: a **crossed-quad mesh** (3 quads at 0/60/120°, double-sided, alpha-cutout material),
used as a mesh detail prototype. Recipe in `references/recipes.md` → "Mesh grass detail".

- Build the tuft mesh in code, save `.asset`, make an alpha-clip two-sided `URP/Lit` material
  (`_AlphaClip=1`, `_ALPHATEST_ON`, `_Cull=0`), save a prefab, then set the `DetailPrototype` with
  `usePrototypeMesh=true`, `prototype=prefab`, `useInstancing=true`, **`renderMode=DetailRenderMode.VertexLit`**.
- **⚠️ `useInstancing=true` + `renderMode=Grass` renders NOTHING — silently.** No warning, no error;
  the density map fills, the inspector looks right, and zero blades draw in any view. Instanced mesh
  details require `VertexLit`. If "the grass never shows up no matter what", check this FIRST. (Cost
  of VertexLit: no wind waving — acceptable; a still lawn beats an invisible one.)
- **⚠️ Check `terrainData.detailScatterMode` before writing density values.** In `CoverageMode`
  (Unity 2022.2+ default for new data) a cell value is a 0–255 *coverage percentage*, so writing
  instance-count-style values (4–15) ≈ 2–6% coverage ≈ virtually no grass — again silently. Either
  `td.SetDetailScatterMode(DetailScatterMode.InstanceCountMode)` (clears layers — refill after) or
  scale values to 0–255. Both this and the renderMode trap produce the same symptom: "painted density,
  see nothing."
- **Density cell size caps your lawn.** detailResolution=1024 on a 4096 m terrain = 4×4 m cells,
  max 16 instances/cell = 1 tuft/m² — physically can't read as turf. For a walkable lawn raise
  detailResolution so cells are ~1 m (`SetDetailResolution(4096,16)`, wipes layers — regenerate
  procedurally) and fill grass zones at ~4–11/m² with 2-octave Perlin patchiness. For lawn (芝) make
  tufts short+wide (h 0.28–0.55, w 0.55–0.95); tone the tuft material's `_BaseColor` muted
  (~0.42,0.50,0.33) or it reads neon against a luminance-tinted ground.
- **Density from the splat**: read the grass channel of the painted alphamap; place density only where
  grass weight is high AND slope is gentle AND above the waterline (and later: not on roads).
- `terrain.detailObjectDistance` ~120 m for dense 1 m-cell lawns (~180–200 m only for sparse meadow).
- Replacing `detailPrototypes[0]` keeps the painted density layer — don't call `SetDetailResolution`
  again (that wipes density).
- **Detail grass does NOT render in one-shot offscreen `Camera.Render()`** (trees and terrain do), so
  a temp-camera screenshot can't verify it — detail patches are built across editor frames, not inside
  `Render()`. Working verify recipe: create a persistent camera GameObject + RT, `Render()` once to
  prime, return from execute_code, wait ~5 s (editor ticks build the patches), then in a second call
  `Render()` again and read the RT. Also: `SceneView.camera`'s transform only syncs during GUI repaint —
  setting `sv.pivot/rotation/size` then immediately rendering its camera captures the OLD pose (or
  origin after a domain reload); the persistent world camera sidesteps both problems.

**Lawn (芝) that actually reads as grass — density cap + sprite recipe.**
- **`detailResolution` caps lawn density**: on a 4096 m terrain, detailRes 1024 = 4 m cells × max 16/cell
  = **1 tuft/m², physically unable to look like turf** no matter the tuning. `SetDetailResolution(4096,16)`
  (1 m cells, wipes density — regenerate procedurally from the grass splat channel) enables 8–15/m²;
  ~2.8 M instances is fine with `detailObjectDistance≈110`.
- **A believable tuft sprite can be generated procedurally** (works when no AI image provider is
  configured): ~150 quadratic-bezier blades rooted at the bottom of the canvas, width tapering
  `(1-t)^0.75`, root-dark→tip-light colour lerp, ~10% dry blades, per-blade shade jitter, drawn at 2×
  and box-downsampled for AA. Derive the palette from the ground albedo's *measured* avg RGB so tufts
  match the terrain colour. Mesh = 4 crossed quads (0/45/90/135°); material `_BaseColor` white (colour
  lives in the texture); use healthy/dry (e.g. (0.72,0.82,0.66)/(0.80,0.78,0.58)) only to tone the tufts
  down into the ground. Olive Asset-Store grass albedos: fix with the luminance-based green tint (§3),
  e.g. FJG `Ground_Grass_01` avg (65,73,29) → shiba green avg (33,65,25), and reuse the pack's matching
  normal map so relief aligns with the visible pattern.
- **SceneView-camera capture DOES include detail grass** once the view has settled: `sv.LookAtDirect(...)`
  in one execute_code call, `sleep ~3 s`, then render `sv.camera` to a RT in a *second* call (LookAtDirect
  is async — a same-call capture shows the old pose).

**Real 3D grass clumps modelled in Blender (when crossed-quad billboards read "ペラペラ").**
The crossed-quad `shiba_tuft` carpet still shows its flat edge at close range and users call it out as
ペラペラ. The fix that satisfied: model actual low-poly grass CLUMPS in Blender and use them as terrain
detail meshes. Hard-won gotchas, all of which produced a *broken* result first:
- **`renderMode=DetailRenderMode.Grass` does NOT render MESH detail prototypes in URP terrain** — the
  clumps are simply invisible (density is there, nothing draws). The working carpet's proto was
  `VertexLit`. **Use `DetailRenderMode.VertexLit` for mesh grass**; it renders the mesh with its material.
  (`Grass` mode is for the billboard/waving-texture path.) This alone was the "表示されない" cause.
- **Thin blade meshes render near-BLACK under VertexLit** because the strip faces point sideways, so
  terrain lighting shades them dark. Fix = **force every vertex normal to world-up (+Y)** (classic grass-
  card trick) so blades receive soft top light and read bright green. Easiest in Unity: clone the imported
  mesh, `mesh.normals = new Vector3[n] {all Vector3.up}`, save as `.asset`, repoint the prefab's MeshFilter.
- **Blender→Unity FBX lays the clump on its SIDE** (Z-up vs Y-up) unless you export with
  `axis_forward='-Z', axis_up='Y', bake_space_transform=True` (bakes the rotation into vertices). Without
  the bake the whole clump is rotated 90° and looks "倒れている".
- **Importer normalises FBX to 1 m** (`globalScale` ~2.4–3.2) so a 12 cm clump comes in ~40 cm tall.
  After import, set `ModelImporter.globalScale *= targetH / mesh.bounds.size.y` and reimport.
- **Poly budget**: a dense CARPET needs cheap clumps — ~10–16 blades, SEG=2, V-fold cross-section for
  thickness → 80–130 tris. At 13–16/m² that's ~3 M instances over the lawn, comfortable at
  `detailObjectDistance≈90`. Keep a separate heavier hero clump (1000+ tris) only for sparse accents.
- **Scatter two variants**: fine (slot 0, dense everywhere) + broad-leaf (slot 1, sparse Perlin patches).
- **Verifying still needs the settled SceneView camera** (off-screen AND forced-pose `scam.Render()` both
  skip detail grass). If the user is navigating, `sv.pivot/rotation/size` fights them and captures land at
  the wrong pose (camera ends up hundreds of m up) — ask them to hold the view still, then capture.
  Canonical build script: `scratchpad/make_grass_lowpoly.py` pattern (bezier-ish blades, cluster jitter,
  lean in ALL azimuths so the clump isn't a neat radial star, droop arc integrated over SEG).

**Organic grass edges (breaking straight land-use / 町割り boundaries).** Detail-grass painted by a
hard `grassSplatWeight > t` gate inherits the land-use zoning's STRAIGHT rectangular block edges — users
call this out ("生えているエリアが直線的"). The fix that works: (1) binarize the grass zone to a mask,
(2) **box-blur the mask** (separable running-sum, radius ~9 texels ≈ 36 m) so the edge becomes a wide
ramp `cover∈[0,1]`, (3) place where `cover >= thr` with `thr` driven by a **high-contrast low-freq noise**
so the boundary sweeps in/out across the blurred band → bays and peninsulas. Interior (`cover==1`) always
passes (stays solid — no bare patches); only the ramp band is carved. Verify numerically before rendering:
scan the density array for "grass-end X per row" — it should vary by tens of metres, not ±a few.
- **THE bug that cost the most: Unity's `Mathf.SmoothStep(a,b,t)` is NOT GLSL smoothstep.** It smithers
  `a→b` by a smoothed `t` and RETURNS a value in `[a,b]` — so `Mathf.SmoothStep(0.35,0.65, noise)` returns
  ~0.35–0.65, collapsing your threshold noise to a near-constant ~0.5 and leaving the edge dead straight.
  Also, **averaging several Perlin octaves for a threshold kills contrast** (central-limit → clusters at
  0.5; measured 0.33–0.67 range). Use a hand-rolled GLSL smoothstep
  `t=clamp01((x-e0)/(e1-e0)); return t*t*(3-2*t);` on a SINGLE (or lightly-weighted) low-freq Perlin —
  raw `Mathf.PerlinNoise` spans ~[-0.04,0.96], and `ss(0.36,0.64, perlin)` then swings the full [0,1], so
  `thr = Lerp(0.12,0.90, big)` genuinely moves the boundary. Probe the noise's min/max over a grid FIRST;
  if it isn't reaching ~0 and ~1 the edge will stay straight no matter what.
- Let grass run **into shallow water** for a natural reedy shore: cutoff at `waterSurfaceY - ~1.5 m`
  (water surface = the water renderer's `bounds.max.y`, e.g. -19.73 here) with a depth-fade on the
  place-probability, instead of a hard exclusion at/above the waterline (which itself reads as a straight edge).

- **⚠️ `GetDetailLayer`/`SetDetailLayer` の配列は [x, y]（dim0=width）— GetHeights/GetAlphamaps の
  [y, x] と逆.** 非正方形リージョンで heights と同じ `den[zz,xx]` の書き方をすると
  IndexOutOfRange か、もっと悪いと**転置された位置に密度が書かれて黙って成功**する（実測:
  width=275,height=126 で GetLength(0)=275）。取得直後に `GetLength(0)==width` を確認し、
  ループは `den[ix,iy]`＝`x=dx0+ix, z=dz0+iy` で書く。転置書き込みで壊した周辺セルは、草スプラット
  重み(alphamap layer)から密度を再導出して領域全体を作り直せば整合的に修復できる（proven 2026-08-08 御預地）。

**Trees (terrain tree instances).** For the real greenery of a treed landscape, scatter `TreeInstance`s
via `terrainData.SetTreeInstances` — GPU-cheap vs thousands of GameObjects. Build a `TreePrototype`
from a prefab (a combined trunk+canopy mesh with 2 submeshes/materials works; for broadleaf use a few
overlapping canopy spheres, deep muted green). **Gotcha that wastes an hour: custom mesh trees render
solid BLACK beyond `treeBillboardDistance`** because Unity tries to billboard them and a plain prefab
has no baked billboard. Fix: set `terrain.treeBillboardDistance = terrain.treeDistance` (billboards
disabled; trees just cull past treeDistance). Also set `material.enableInstancing=true`. Scatter
**by land-use zone**, not uniformly: dense in temple groves (鎮守の森) and samurai gardens, ~none in
commoner blocks / roads / water / fields — sample the class map per candidate (`EdoLandUse.WorldToMapPixel`),
skip steep slopes and sub-waterline. Use a seeded `System.Random` for reproducible layouts. Canonical
impl: `Assets/Edo/Scripts/Editor/EdoTrees.cs`.

**Placing ONE hand-sited building where the user pointed (bookmark mark → world → seated shop).**
When the ask is "put a shop *here*" rather than a procedural scatter, the whole job is turning the
user's red mark into a world point and then seating the building believably:
- **Resolve the mark to world by reconstructing the bookmark camera and raycasting.** From
  `bookmarks.json` rebuild a temp `Camera` with the stored `pos/euler/aspect` **and** `ortho`+`orthoSize`
  (a Scene view in 2D mode is orthographic — using a perspective fov instead sends the ray from the
  wrong origin), then `ViewportPointToRay(new Vector3(m.x, 1f - m.y, 0))` — **marks are stored
  top-origin (GUI), viewport is bottom-origin, so the y MUST be flipped** — and `Physics.RaycastAll`.
  A single bookmark is only as precise as its `orthoSize` (a 68 m half-height view ≈ ±several m), so
  when the user marks the same feature in **two** bookmarks, raycast both and take the convergence;
  agreement within a few metres confirms you read the right spot.
- **Level a pad, don't fight the relief.** A 14 m building over 2 m heightmap texels typically spans
  0.5–0.8 m of relief — seating it by any single ground sample leaves one corner buried and the
  opposite corner floating. Flatten to the **median** footprint height (minimises cut+fill), full
  strength inside footprint+1 m ramping to 0 by +4.5 m.
- **⚠️ Guard the pad against nearby 石垣.** Terrain next to a revetment sits at the wall crest, so a
  pad that raises ground near it pushes dirt up through the stone cap (§5c). Add a hard mask: skip any
  heightmap cell within ~3 m of a wall piece's XZ bounds and fade the weight in over the next ~2.5 m.
  If the building still lands within a few metres of the wall, nudge it along its own front normal
  first — cheaper than tuning the pad.
- **Seat by the foundation stones, not the pivot or bounds** (see `EdoFitToGround.cs`): Village Kit
  houses put `stone Base` bottom at local y −0.35, so `pivot.y = groundY + 0.30` lands the 根石 0.05 m
  into grade — 石場建て, the correct look.
- **Dress in the parent's LOCAL frame.** Parent an empty at the site with the building's rotation, add
  everything as children with local coords, and the whole shop moves/rotates as one. For props that
  must sit on grade under a rotated parent, `localY = InverseTransformPoint(groundPoint).y + offset`
  — passing a bare world height, or an offset alone, floats them. Bench-top props need `offset ≈ 0.42`
  (bench top is 0.41 above grade); measure, don't guess, or you get planks hanging in mid-air.
- **Japanese Village Kit `Small House` local frame** (handy, saves a probe): walls occupy x −6..6,
  z −5..3; **front facade is +Z at z = 3**, with the sliding-door opening at **x 0..6** and solid wall
  x −6..0; floor y = 0, lintel/beam y = 3.0, eave edge z ≈ 4.2. So 暖簾 go at `(1,3,5 , 2.25, 3.06)`,
  床几 under the eaves at z ≈ 4.05, 犬矢来 against the closed half at x ≈ −3.6.
- A lone building on bare terrain reads as dropped-in no matter how well it's seated — a handful of
  `TreeInstance`s flanking it (validated ≥7 m from any wall, above the waterline) does most of the work
  of making it belong.

**Composing a SMALL building the kit has no prefab for (辻番所・番小屋, ~4 m square).** Village Kit's
smallest complete building is `Small House` (14.5 × 10.5 m ≈ 8間×6間) — far too big for a guardhouse,
and reusing it makes every structure in the scene look identical. Build one from modules instead:
- **Walls**: `Shopping Streets/Wall Shop *` panels are a clean 2 m × 3 m kit, pivot at bottom-centre,
  panel plane in XY facing ±Z. Variants read as distinct building types: `Wall Shop`/`B` shoji lattice,
  `C`/`E`/`F` 格子 (vertical slats — the 番所 window), `Wood` solid boards, `Plaster` white 漆喰.
  A 4×4 m box = 2 panels per side at ±1 along the edge, edges at ±2, rotY 0/90/180/270.
  Close the corner joints with `Wall Shop E end` (a thin post) at each corner, rotY 45+q·90.
- **Roof — `Roofs B` is a 2 m-grid set** (the main `Roofs` folder is 4 m and won't tile under 8 m).
  Convention: a module descends along its **local +X**, pivot at the **top-inner** corner
  (`roof B 2 x 2` = x 0..2.02, y +0.13 down to −1.21 → 31° pitch). rotY 270 makes it descend +Z,
  rotY 90 → −Z, rotY 0 → +X, rotY 180 → −X.
- **⚠️ A gable roof on a module-built hut leaves the gable TRIANGLE wide open** — the kit has no
  triangular 妻壁, so you see straight through above the 3 m walls and the roof reads as "floating".
  Wasted a pass diagnosing this as a height error. On a square plan just build a **方形 (pyramidal) hip**
  instead: `roof B corner A 2 x 2` ×4, all at the *same* local position, rotY 0/90/180/270. No gable,
  no hole, and it's the correct form for a small 番小屋 anyway.
- **⚠️ The roof PLANE must meet the wall top at the WALL line, not at the eave line.** Placing the
  module so its lowest edge sits on the wall top puts the whole plane above the wall out at the
  overhang radius, leaving a see-through slot all round. Solve it as geometry: with apex pivot `Yr`,
  eave radius `R` and total drop `D`, the plane height at the wall radius `r` is `Yr − (r/R)·D`; set
  `Yr = wallTop + (r_wall/R)·D` so the eave hangs *below* the wall top and closes the joint.
- **This kit tiles edge-to-edge with no built-in overhang** (unlike the 4 m `Roofs` set, whose 5.64 m
  modules on a 4 m grid overlap 0.8 m). The separate `roof B end` eave course is fiddly to chain and
  leaves a visible second tier. Far cleaner: **scale the hip modules in XZ** (≈1.45) to create the
  overhang, ×1.15 in Y to keep the pitch. Gap-free by construction; 45 % shingle stretch is invisible
  on a small dark roof.

**What plants the project actually owns** is listed in `<project>/docs/asset-catalog.md` §9
(species, prefab path, real size, per-species scale factor), with the full 2,681-asset dump in
`docs/asset-index.tsv`. Check stock there before assuming a species is missing — and the TSV's
`shader` column is the fastest check on whether a re-import re-broke the URP conversion below
(the `BUILTIN` count jumps from 4 to 80+).

**Using an Asset-Store vegetation pack (e.g. Japanese Garden 2 Free) in URP.** Far better than
recolouring photos, but three gotchas bite on import:
1. **Pink materials** — the pack ships Built-in shaders (`Nature/SpeedTree8`, `Standard`). Convert:
   SpeedTree8 → `Universal Render Pipeline/Nature/SpeedTree8_PBRLit` (property names match, just swap
   `m.shader`); `Standard` → `URP/Lit` but re-map `_MainTex→_BaseMap`, `_Color→_BaseColor` by hand
   (those names differ, so a bare shader-swap loses the albedo). Iterate `AssetDatabase.FindAssets("t:Material", packFolder)`.
2. **Third-party script won't compile on Unity 6** — packs from before Unity 6000.5 call
   `Object.GetInstanceID()`, now obsolete-**as-error** (CS0619). A `#pragma` can't suppress an error;
   `(int)GetEntityId()` is ALSO obsolete-as-error. Fix: replace `.GetInstanceID()` with
   `.GetHashCode()` — non-obsolete, and Unity's `Object.GetHashCode()` still returns the instance id,
   so int dictionary keys keep working. (Same class of patch as the PLATEAU SDK EntityId fix.)
3. **SpeedTree billboards render as white/washed quads in URP** (the distant LOD). Simplest cure until
   you fix the billboard material: `terrain.treeBillboardDistance = terrain.treeDistance` so trees only
   ever render as 3D mesh (they cull past treeDistance instead of billboarding).

4. **A pack can be URP-ready for its BUILDINGS but not its FOLIAGE.** The Japanese Castle pack's
   building materials render fine, so it reads as "converted" — but `Meshes/Foliage/Materials/Azalea.mat`
   still uses a Built-in Amplify shader (`Japanese/Foliage`) and renders **magenta**. Don't judge a pack
   by the first prefab you place. Convert: read the old textures BEFORE swapping the shader
   (`_AlbedoTransparency`, `_Normal`), then `m.shader = URP/Lit`, `_BaseMap`/`_MainTex` ← albedo,
   `_BumpMap` ← normal + `_NORMALMAP`, `_AlphaClip=1` + `EnableKeyword("_ALPHATEST_ON")`, `_Cutoff≈0.5`,
   `_Cull=0` (two-sided leaves), `renderQueue=2450`. Note the Amplify property names differ from both
   Standard and URP, so a bare shader swap silently loses the albedo.

Extra: when picking a pack ground texture for roads/bare, **sample the albedo's average RGB first** —
a "gravel" that averages ~(141,139,117) is near-white and paints ugly pale blotches; pick the darker
~(76,68,43) variant for a natural packed path.
