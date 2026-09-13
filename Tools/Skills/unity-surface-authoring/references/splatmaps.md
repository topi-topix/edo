# 地形スプラットマップ — リアルな土の地表

## 3. Terrain splatmaps — realistic earthen ground

A blank terrain has 0 layers and renders flat/grey. Assign PBR `TerrainLayer` assets, then paint the
alphamap procedurally from **slope + height + noise** rather than by hand. Recipe in
`references/recipes.md` → "Splatmap paint".

Principles that produced good results:
- **Reserve each layer a meaning**: base packed earth (dirt), grassy banks, compacted/worn bare earth,
  steep rock. Blend by `terrainData.GetSteepness(u,v)` and `GetInterpolatedHeight`.
- **Noise breaks tiling**: 2 octaves of `Mathf.PerlinNoise` (one fine ~×50, one macro ~×10) to mix
  patches so the ground isn't uniform.
- **Normalize the 4 weights** per texel; write with `SetAlphamaps`.
- **Kanto-loam reddish-brown earth is historically correct** for Edo/Tokyo — don't "correct" it to
  neutral. Dry earth = matte (metallic 0, smoothness 0).
- Alphamap res 1024 over a 4 km terrain (~4 m/texel) blends fine because the diffuse tiling supplies
  the close detail; the splat only controls blending.
- **Kill visible tiling repetition — the only real fix is stochastic sampling in the SHADER.**
  A single splat layer at a fixed `tileSize` over a large flat area shows an obvious repeating
  "polka-dot" grid. Half-measures that DON'T actually solve it (users will call this out): enlarging
  tileSize just rescales the same repeat; blending two textures by macro noise still shows each
  texture's own repeat; per-tile interior randomness is meaningless when the tile itself is repeated.
  The correct fix is **stochastic / hex tiling** (Heitz-Neyret): sample the texture with a random
  offset per virtual hex cell and blend the 3 nearest cells by barycentric weights — the repeat
  vanishes with a single texture. Native `TerrainLit` can't do it, so **copy URP's terrain shader set
  and inject hex sampling**: `cp` `Shaders/Terrain/TerrainLit.shader` + `TerrainLitPasses.hlsl` from
  the URP PackageCache into `Assets/…`, rename the shader, point the shader's `TerrainLitPasses`
  includes at your local copy, add a `EdoHexSample(TEXTURE2D_PARAM(tex,smp), uv)` function (hash→hex
  triangle grid→3× `SAMPLE_TEXTURE2D_GRAD` with `ddx/ddy` for correct mips→weighted blend), and swap
  the 4 diffuse (`SplatmapMix`) + 4 normal (`NormalMapMix`) `SAMPLE_TEXTURE2D(_Splat/_Normal…)` calls
  for `EdoHexSample(TEXTURE2D_ARGS(…))`. Make a material with the new shader, assign it to
  `terrain.materialTemplate` — the terrain feeds splat data automatically. Reuses all of URP's
  lighting/splat logic; only the fetch changes. Canonical impl:
  `Assets/Edo/Shaders/StochTerrain/`. (Cost: 3× texture fetches per layer — fine for dev.)
- **Zone contrast needs hue-distinct textures, not just splat weights.** If two layers you're trying to
  contrast (e.g. dirt vs grass) render as the same muddy tone no matter the weight, the *textures* are
  the problem — sample their average RGB (`GetPixels32` + mean) to check. Many stock "grass" diffuses
  are a dry olive-yellow (e.g. avg ~(114,97,37)), nearly identical in hue to dirt, so land-use zones
  built on them are invisible from above (and the 3D detail grass that *does* look green only renders
  within `detailObjectDistance`). Fix by recolouring the diffuse to the right regional hue and saving a
  new texture the layer points at: for **Edo/Japan** the greenery is deep broadleaf / summer-shiba
  green (照葉樹林・雑木林・芝), NOT Mediterranean olive. **Use a luminance-based green tint, NOT
  independent per-channel multipliers.** Naive `r*a, g*b, b*c` (especially lifting blue) pushes the
  texture's bright/grey pixels — highlights, pebbles, flecks — to a higher blue than green, so they
  render as ugly BLUE SPECKLES that read as "moss". Instead preserve detail via luminance and force the
  hue green so blue can never exceed green: `L=0.30r+0.59g+0.11b; out=(L*0.50, L*0.92 + (g-L)*0.5, L*0.40)`
  (the `(g-L)` term re-adds natural green mottling). Do the same for the detail-grass sprite (keep its
  alpha!) and set the detail material `_BaseColor` near-neutral so you don't double-tint it back to
  olive. Remember the biggest "green" in an Edo view is actually TREES (estate gardens, shrine/temple
  groves), so let tree cover — placed via the land-use zoning — carry most of the green; keep ground
  grass for lawns/banks/fields.
