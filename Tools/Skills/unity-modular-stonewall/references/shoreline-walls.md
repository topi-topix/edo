# 護岸・堀の石垣(`Ishigaki_Ext_*` 系)

## 8. Shoreline / moat walls (the `Ishigaki_Ext_*` variant)

The pond and canal walls predate the 屋敷 work and use a **different scale convention** —
straight `(2, h, 1.3)`, corner `(2, h, 2.0)`, module spacing 2.40 m, so 4.8 m thick and 2.6 m along
the run. Don't mix the two conventions inside one wall, and prefer the §1–§3 convention for anything
new. Baseline of the shipped wall:

| group | pieces | straight `scale.y` | coping y | corners |
|---|---|---|---|---|
| `Ishigaki_Ext_1` | 75 | 1.668 → ramp → 1.10 | -16.33 → -18.58 | 1 出隅 + 1 入隅 |
| `Ishigaki_Ext_2` | 70 | 1.620 (65/70) | -16.52 | 3 出隅 + 2 入隅 |
| `Ishigaki_Ext_3` | 81 | 1.66 (all) | -16.35 | — (straight run) |
| `Ishigaki_Ext_4` | 87 | 1.10 (all) | -18.58 | — (straight run) |

Shared `position.y = -23.00` for all 311 pieces.

### Fit to the WATERLINE, not to the WaterBody outline polygon

**The `outline` array is authoring input, not the shoreline.** Each outline vertex carries its own
`y`, which drives how deep the baker carves there. If a vertex's `y` is pushed **below** `waterY`, the
real waterline ends up *inland* of the polygon edge and every distance-to-polygon measurement lies to
you. (Akasaka: `Water_212447.outline[9].y` went -16.74 → -22.23 with `waterY = -21.50`, which made a
correctly-placed wall read as "0.75 m inside the water".)

Measure the physical waterline instead — march from the wall's water-facing face and find where the
terrain crosses `waterY`:

```csharp
Vector3 face = bounds.center + waterDir * halfThickness;
float gap = -1;
for (float d = 0; d <= 20f; d += 0.25f)
  if (terrain.SampleHeight(face + waterDir*d) + terrain.transform.position.y <= waterY) { gap = d; break; }
// waterDir = whichever perpendicular has the LOWER terrain 5 m out
```

**Project convention: `gap == 0.00` for every piece.** Ext_3 (81), Ext_4 (87) and Ext_2's yaw297 run
(55) all measure a median of exactly 0.00. Any run with a growing gap is misfitted; any run measuring
`-1` (no water within 20 m) is stranded inland.

### The coverage scan that actually finds the defect

Distance-to-shoreline says nothing about *unretained* shoreline. Sweep by column instead:

```csharp
for (float x = X0; x <= X1; x += 1f) {
  float zw = -1;
  for (float z = Z1; z >= Z0; z -= 0.25f) if (TH(x,z) <= waterY) { zw = z; break; }
  if (zw < 0) continue;
  bool ok = false;
  for (float o = -1.5f; o <= 3.5f; o += 0.25f) if (HitAnyWallOBB(new Vector2(x, zw+o))) { ok = true; break; }
  if (!ok) Report(x, zw);          // ← shoreline with no wall behind it
}
```

Test against **oriented** boxes, not world AABBs — a 45°-rotated piece's AABB is 1.41× too big and
hides real gaps. This is what located the Akasaka defect (uncovered `x = 185…200`) after
outline-distance metrics had pointed at the wrong run entirely.