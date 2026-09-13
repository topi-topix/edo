# 地形に載せるメッシュ — 石垣のスカート、段坂、アトラスのUV流用

## 5c. Seating wall/revetment meshes (石垣) against terrain — the skirt-mesh solution

Placing modular stone-wall pieces (castle ishigaki) along a shore and trying to make the TERRAIN meet
them cleanly fails in a characteristic way, and the fix is architectural, not parametric:

- **Heightmap quantization is the root cause, not your algorithm.** A 4096 m terrain at heightmapRes
  2049 = ~2 m/cell. Conforming the ground to a mesh wall's back edge yields a jagged, stair-stepped
  junction (±1 cell) and hairline gaps wherever the grid falls short of the wall back. No amount of
  boundary smoothing / distance-field tuning fixes it — the surface literally cannot represent the
  line. (Symptom: "カクカク & 隙間" that survives every re-fit.)
- **Fix = a generated "skirt" ribbon mesh** glued to the walls' back-top edges: per piece, compute the
  back-top edge from the REAL mesh corner geometry (project bounds corners onto the piece's
  right/forward axes: back = min proj on `right`, top = max y, shore extent on `fwd`), then emit a
  3-column strip: front vertex sunk 0.2 m INTO the stone at crest−0.03, a shoulder at −2.2 m/−0.55,
  and a hem at −4.8 m dropped to `SampleHeight−0.45` so it tucks UNDER the terrain. Overlap each
  piece's strip ±0.35 m along the shore so neighbors seal. Material: reuse the terrain grass layer's
  diffuse (URP/Lit, smooth 0) tinted to the bank hue. Mesh-to-mesh contact = gap-free by construction.
- **Drop the terrain fill 0.5–1 m below the wall crest** (fill target = crest−0.7). If you fill to the
  crest, the jagged terrain edge pokes up THROUGH the skirt as zigzag patches; kept lower, all
  quantization noise hides beneath the ribbon.
- Related placement traps from the same effort: a modular wall's stone FACE axis varies per piece —
  detect it by summing area-weighted horizontal normals over ±X/±Z (an ±Z-only check silently placed
  91 pieces 90° wrong, comb-teeth style); and conform terrain per the wall's live transforms so
  user hand-adjustments are honored (`Assets/Edo/Scripts/Editor/EdoIshigakiFit.cs` = fit + skirt +
  safety-restore tool).
- **Wall ALIGNMENT must be few straight runs + sharp corners, not the water outline.** Following a
  smooth shoreline polyline vertex-by-vertex reads as "layered flapping sheets" at every shallow bend
  (user: 石垣は基本直線、曲がる時はシャープに). Douglas-Peucker the outline (tol ~4 m) into 3-5 straight
  runs; within a run give every piece the IDENTICAL rotation (coplanar faces = invisible seams);
  extend runs ~0.6 m past each corner and add ONE bisector-oriented piece per corner pulled 0.3 m
  landward and 0.04 m down to plug the crest V-notch (battered faces recede with height, so base-line
  math alone leaves a notch at the cap). Do NOT slide run-end pieces toward the corner — that opens
  gaps inside their own run.
- **Run the wall base BELOW the moat floor at the face.** Wall base −24, waterline −23.3 → carve the
  water-side floor to base+0.35 at the face (buried base, still submerged) then slope to full depth
  over ~9 m. Carving deeper than the base leaves an exposed dirt band under the wall (visible when
  the user dives underwater).
- **Ends die into a bank ALONG the run, never a radial mound.** Blend the water-side profile toward
  bank-top over the last ~10 m along the run direction (and extend the last pieces 6 m into that
  ramp) so the revetment is swallowed by rising ground, 皇居外堀-style; a radius-based mound reads as
  a blob jutting into the pond. Grass-splat the ramp so no bare shore band shows.
- **One continuous skirt for the whole alignment** (columns walked along the mitered back-offset
  polyline) — per-piece ribbons overlap visibly. Give the hem per-column Perlin lengths (geometric
  dissolve beats any straight boundary), paint the land corridor's splat to the same grass layer, and
  tint-match by rendering both surfaces top-down and ratioing mean RGB.
- **⚠️ Asset-kit wall pieces are HOLLOW OPEN SHELLS (face+cap+sides, NO back).** With terrain filled
  flush behind, any camera above the crest sees over the crest edge INTO the shell and hits the
  terrain inside — which renders as an olive "smeared wall" hiding the stone, plus grid-sawtooth
  "spikes" hanging at the crest (the interp teeth of the interior trench→plateau cliff). These
  artifacts are world-fixed: nudging/respacing pieces doesn't move them (the decisive diagnostic:
  hide the whole wall group and re-render — if the "wall" is still there, you've been looking at
  terrain all along). Fix = BOTH: (1) append a full-height back quad to the mesh (normal facing
  +X/interior so exterior over-crest rays hit stone), and (2) keep interior terrain LOW (base+1.5)
  for the FULL body depth so the trench cliff sits BEHIND the back quad; start the flush plateau at
  the back plane (+0.02 m), never inside the body. A "keep terrain 0.3 m under the batter face" ramp
  CANNOT work at 2 m heightmap texels — interpolation error is meters, the cliff pokes through.
- **★ THE winning recipe for a deep-moat revetment from kit wall pieces: route the terrain's
  crest→floor drop BEHIND the wall, never at its face.** A deep moat (crest −12, water −23) forces an
  ~11 m terrain height change; over 2 m texels that's a near-vertical TERRAIN cliff that competes with
  the stone and wins (you see olive terrain, stone reduced to waterline triangles). Chasing the
  battered face with terrain, pushing the wall water-ward, sharpening the carve — all fail at 2 m
  resolution. What works: use the **native prefab** (`…/Defence Walls/Castle Wall C 8 x 12.prefab`,
  face=+Z, 8w×12h×7.6d, pivot at base, native UVs that DON'T smear — no custom mesh/UV needed);
  place face at the alignment (`LookRotation(N)` maps +Z→water); then conform terrain as
  **crest for s ≤ −9 m (landward) → ramp to a flat submerged floor (−24.5, just below the wall base)
  by s ≤ −6 → floor for all s > −6** where s is signed distance along the water normal. The entire
  crest→floor transition now sits 6–9 m LANDWARD of the wall, so the wall body hides it; the wall
  stands free on the flat moat floor and shows its full height from the water. No skirt, no back quad,
  no interior-lowering, no UV surgery. This is the first approach that produced a clean full-height
  stone face — everything before it fought the texel grid and lost.
- **Kit atlas textures ≠ tiling textures.** The wall's single texture is an ATLAS (stone field +
  white cap band + 算木 corner strip); mesh UVs map parts to regions, at ~1 tile per 8-16 m → faces
  smear to mud at any distance and naive planar UV re-mapping repeats the cap band mid-face. Fix:
  crop an isotropic patch of the stone FIELD to its own texture (wrap=Mirror kills crop seams — but
  crop must avoid directional/diagonal stones or mirroring makes kaleidoscope chevrons), split the
  face triangles into a second submesh, give it a dedicated URP/Lit material, planar-UV at real stone
  scale (~0.25 tiles/m), anisoLevel 16. Diagnose material-vs-geometry confusion with a solid-red
  material swap on the suspect submesh.

---

## 5d. 段坂 — a stepped slope road the 2 m heightmap cannot make on its own

Proven on 汐見坂, Akasaka (2026-08-02): a 100 m road rising 5.1 m, terraced into 16 flat treads with
0.30 m stone risers. Grading the heightmap alone **cannot** do this — a 0.30 m step on a 2 m grid,
sampled along a 45°-diagonal axis, smears into a 3–5 m ramp and reads as a wavy slope, not stairs.

**The recipe that works — mesh for the crisp part, terrain for everything else:**

1. **Work in a wall-relative frame.** Roads in 武家地 run parallel to the estate wall, not to the
   user's clicked marks. Take `yaw` from the wall run (all four 南石垣 runs shared 310.04), set
   `d=(sin,cos)`, `nOut=(-cos,sin)`, and put the origin on the **outer face** of the first piece
   (`pivot + 2.4·nOut`). Then `tt` = along the wall, `n` = out from its face. The user's bookmark
   marks land as a scatter in `n` — use them to pick the road's width band, not its centreline.
2. **Road surface = a generated ribbon mesh** with a flat quad per tread and a vertical quad per
   riser, plus a **0.9 m skirt** dropped at both edges (the skirt hides everything below).
   UV in metres ÷ the terrain layer's tile size (11 m for `L_bare`) so it reads as the same ground.
3. **Grade the terrain with a LAG, not to the same step function.** Feed the terrain
   `target = Level(tt − 3.0)` — the ground steps up ~3 m *after* the mesh does, so the terrain is
   never above the mesh and never pokes through. Same function without the lag leaves the ground
   0.05–0.3 m proud on the low side of every riser. QA is a grid sweep asserting
   `terrainHeight ≤ meshLevel` at every (tt, n): the pass is **0 of 4100**, not "close".
4. **Extend the cut to `n = −2 m`, inside the wall body** (§6 of `unity-modular-stonewall`). Stopping
   at the wall face left a 0.28 m berm along the entire foot — 28 of the 4100 QA samples, all at
   `n = 1.0`.
5. **Cut the shoulder outside the kerb** (−0.35 m fading over ~10 m). Without it the 土留め retains
   nothing and reads as a curb lying on flat sand.

**Stone modules (Blender headless → FBX, same pipeline as 土塀/乱杭):**

- The FBX arrives **Z-up** (`bake_space_transform=False` puts the axis conversion nowhere when the
  root object is the mesh). Don't fight the exporter — wrap it in a prefab whose child carries
  `localRotation = (−90,0,0)`. Root-local then reads `+X` = along the module, `+Y` = up,
  `+Z` = −depth, and the module's top sits at `y = 0`, so you place by `position.y = tread level`.
- Yaw from a world direction `v`: local `+X` maps to `(cos a, −sin a)`, so `a = atan2(−v.z, v.x)`
  — a *different* convention from `Castle Wall`'s local `+Z`. Riser stones (running across the road)
  came out at 130.04, kerbs (along it) at 220.04.
- **A smooth 2-stone box with cube-projected UVs turns any masonry texture into mirrored wallpaper.**
  Two dead ends before the fix: shrinking the tiling made a kaleidoscope; stripping the albedo to a
  flat colour made concrete blocks. The fix is **geometry, not material** — 4 stones per 2 m module,
  each with its own height/depth/rotation jitter and ~2 cm joints, then the ordinary 石垣 material
  reads correctly. Vary instances further with 4 material copies differing only in `_BaseColor` and
  `mainTextureOffset`.
- Lateral jitter must stay **under the module overlap** (±0.04 m on a 1.7 m pitch / 2.0 m module).
  ±0.10 m on a 1.8 m pitch opened visible gaps between neighbouring stones.
- Count the modules against the kerb line: 12 × 1.7 m overshot the 土留め by 2.2 m and the risers ran
  out into open ground. Cover `[kerb, kerb]`, not "about the road width".

**Judge it from the user's bookmark camera, not from the road.** At eye level a 0.30 m riser reads as
a proper staircase; from 60 m up it is a line, and 16 of them plus two kerbs read as a **ladder or
railway track**. Say so rather than reporting it done — and expect road width to be the lever: 6間
(10.8 m) was rejected as too narrow, 10間 (18 m) accepted.

## 10. Borrowing a texture region from another atlas via material tiling/offset (UV remap without touching meshes)

Proven 2026-08-02 (太田長屋の腰を門と同じ下見板に統一, commit a2d4124).

When two assets from the same pack family should share a finish (e.g. a gate's
weatherboard 下見板 and an adjacent nagaya's腰), you can re-skin ONE submesh to
sample ANOTHER asset's texture atlas region — no mesh edit, no texture edit,
fully reversible:

1. Measure the target look's UV rect on its own atlas: read `mesh.uv` bounds of
   the reference submesh (e.g. gate `shitami` → u[0.030,0.192] v[0.237,0.531]
   in hnagaya.jpg).
2. Measure the victim submesh's UV rect on its atlas (e.g. `n_namako` →
   u[0.021,0.479] v[0.404,0.512] in knagaya.jpg). Works best when the victim is
   a simple quad strip (few verts, axis-aligned rect).
3. Linear remap via material: `scale = targetSize/victimSize`,
   `offset = targetMin - victimMin*scale`; create a Material copy of the
   victim's own material (keeps shader/URP settings), set `mainTexture` to the
   reference atlas and `mainTextureScale/Offset` to the computed values.
4. `AssetDatabase.CreateAsset` the material (so the scene reference persists),
   assign to `sharedMaterial` of each instance.

Gotchas:
- Assigning `sharedMaterial` on prefab-instance children may NOT dirty the
  scene — `MarkAllScenesDirty()` before `SaveOpenScenes()` or git shows no diff.
- The remap stretches texel density (here 3.5× horizontally); fine for
  low-contrast wood grain, visible for patterned regions. Panel/joint patterns
  built from many sub-quads in the reference mesh can NOT be reproduced this
  way — you only get the base texture region, matched in tone.
- Verify from the user's bookmark angle AND an eye-level closeup at the seam
  between the two assets.
