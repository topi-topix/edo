# 地形を石垣に合わせる / 壇を石垣で囲う

## 6. 地形を石垣に合わせる（grading）

When the land behind a wall sits above the coping, cut the ground — never raise the wall.

**Measure at 2–24 m inland, not at the piece's mesh centre.** The mesh centre sits over the carved
trench and reports the wall as fine while the bank behind it is a metre high. Sampling Akasaka's
`Ishigaki_Ext_4` at the mesh centre flagged 14 of 87 pieces; sampling 2–24 m inland showed the bank
was a uniform **+1.00 m above coping along the entire 206 m run**.

Profile the neighbours first to pick a target — "coping level" is not the convention everywhere
(Akasaka: Ext_3 −0.2 m, Ext_1 +0.6…0.8 m, Ext_2 +0.6…0.8 m behind the coping).

```
FLAT  = 8 m    level band at coping, measured from the land-side face
FEATH = 14 m   smoothstep back up to natural ground
TAPER = 12 m   fade in/out at both ends of the run
SMIN  = −2 m   start the cut INSIDE the wall body, not at the mesh centre
newH  = min(originalH, lerp(originalH, coping, wCross * wAlong))   // lower-only, never raise
```

Three gotchas, each of which cost a redo:

- **`s >= 0` is not far enough.** Ending the cut at the mesh centre leaves uncut cells 2 m to the
  water side and bilinear sampling drags the ground back over the coping. Start at `SMIN = −2 m`,
  inside the 4.8 m-thick wall, so the cut is hidden. This alone took 3 pieces from +1.30 m to 0.00.
- **Lower-only via `min()`.** A plain `Lerp` to the coping *raises* ground that was legitimately
  below it — most of a pond bank is.
- **Never touch the water side.** Verify afterwards by sampling ~6 m out on the water side and
  confirming it is unchanged (Akasaka: −23.00 before and after).

Snapshot the heightmap before any cut — terrain edits are **not** covered by `Undo`, so the snapshot
file is the only way back:

```csharp
var full = td.GetHeights(0,0,R,R);                       // R = td.heightmapResolution
var bytes = new byte[R*R*4]; int bi = 0;
for (int z=0; z<R; z++) for (int x=0; x<R; x++) { System.Array.Copy(System.BitConverter.GetBytes(full[z,x]), 0, bytes, bi, 4); bi += 4; }
System.IO.File.WriteAllBytes(System.IO.Path.Combine(Application.dataPath, "../Library/EdoIshigaki_before.bin"), bytes);
```

Write results with `SetHeights(x0, z0, sub)` over the affected sub-rect, not the whole 2049² map.

### Check the DEM baseline BEFORE you cut — cutting may be the wrong fix

Grading down is only right if the coping is already at or above the natural surface. If the coping
sits below the real ground, cutting silently sinks the world below its survey data — **raise the wall
instead.** At Akasaka this exact mistake cut the bank 0.42 m below the GSI DEM; the real defect was
that Ext_4's coping (−18.58) was 0.42 m below the natural surface (−18.16).

```bash
git log --oneline --follow -- Assets/Edo/Terrain/ModernTerrain.asset | tail -1   # the original bake
git show <sha>:Assets/Edo/Terrain/ModernTerrain.asset | git lfs smudge > /tmp/GsiBaseline.asset
cp /tmp/GsiBaseline.asset Assets/Edo/Terrain/_GsiBaseline.asset                  # import, read, then delete
```

**Validate before trusting it:** compare 4–5 control points far from any edit; they must match to
~0.01 m, otherwise the terrain transform or `size.y` changed between bakes and the comparison is
meaningless. Delete the temp asset with `rm` + `AssetDatabase.Refresh()` — `DeleteAsset` is a blocked
MCP pattern. Pick the coping from the DEM's **max** along the land side, not its median.

### Raising terrain is NOT the mirror of lowering it

`SMIN = −2 m` (inside the wall body) is safe for a **cut** — the removed material is hidden. Reuse it
for a **fill** and you pack the water-side carve trench: at Akasaka that filled 5.29 m of the pond
edge and pushed the waterline back to 0.75 m on 23 pieces. **Start any fill at the land-side face
(`s >= +2.0`), never inside the wall.** Rebuild the corridor from the **pre-edit snapshot**, not from
the current already-edited heights:

```
h = (s < 2.0) ? PRE                      // trench + under-wall: exact restore, no interpolation
              : lerp(PRE, GSI, wCross*wAlong)
```

Verify by diffing the water side against the snapshot cell-by-cell — it must be **0 differing
cells**, not "close".

## 7. 壇を石垣で囲う場合の造成インセット

Building a walled terrace (a 屋敷 pad, a bailey, any platform) is the mirror of §6: instead of grading
*to* an existing wall you grade a polygon and ring it with wall. The heightmap is a 2 m grid, so any
height change is a ramp ~2 cells wide, not a step — where that ramp lands decides whether the stone
shows at all:

| flat pad extends to | result |
|---|---|
| 2.4 m *outside* the boundary | ramp starts outside → an earth glacis buries the **whole** wall face |
| exactly the boundary (`d >= 0`) | ramp straddles the face → bottom half buried |
| **3 m inside** (`d >= 3`) | ramp sits **inside the 2.4 m-thick wall body**, hidden → face exposed to its foot ✔ |

```csharp
float d = SignedDist(poly, p);            // + inside
if      (natural > padY && d < 0f) { /* 切土: cut to padY at the edge, feather out over 14 m */ }
else if (d >= GRADE_INSET)          target = padY;      // GRADE_INSET = 3.0
else                                target = natural;   // 盛土側は素の地盤 → 石垣が立つ
```

On the **cut** side do the opposite — grade the outside *down* to `padY` right at the boundary and
feather away over ~14 m. A single `d >= -2.4 → padY` branch for both sides is the bug that produced
two rebuilds at Akasaka.

**Gate openings need a ramp, or the gate opens onto a cliff.** In the same grading pass carve a
corridor (`along ∈ [0, 22 m]`, half-width `gateOpen/2 + 3`) lerping `padY → natural`, with a
smoothstep side-fade so the shoulders blend instead of leaving vertical scars.

**Reordering a polygon renames its edges.** A `ToCCW()` that reverses the array silently moves a
hand-authored `gateEdge = 0` to the opposite side (original edge *i* becomes `n−2−i`, `gateT` becomes
`1−gateT`). Map the indices explicitly and re-check after any winding fix — this put a gate and 107 m
of 長屋 on the wrong face twice.

**`Wall Exterior Defence` (築地塀) on the coping.** Pivot is **centred**: local `X ∈ [-1, 1]` is the
run, `Z ∈ [-1.05, 1.05]` the thickness, height 2.57 (`… Tall` = 4.27). Run axis is local **+X**, so
`yaw = atan2(-d.z, d.x)` — a different convention from `Castle Wall`'s local `+Z`. Inset the
centreline ~1.3 m from the boundary so it stands on the wall top with a narrow 犬走り in front.
`Wall Exterior Defence x 8` is 8 m and cuts the piece count 4×, but **fall back to the 2 m single
near a gate**: an 8 m module whose centre fails the gate-clearance test is dropped whole and leaves a
6 m hole in the 塀.