# 出隅(corner)の幾何とピボットの罠

SKILL.md §1 の根拠データと詳細。原則(R1〜R4)は SKILL.md 側にある。

### The kit

`Assets/Japanese Castle/Prefabs/Exterior/Defence Walls/`. Local box **before** transform scale — the
origin sits at a *corner* of the box, never its centre:

| prefab | guid | local X | local Y | local Z | role |
|---|---|---|---|---|---|
| `Castle Wall` | `d481c045` | `[-2.40, 0]` | `[0, 4.0]` | `[-2.00, 0]` | straight |
| `Castle Wall Corner` | `b8acc577` | `[-2.40, 0]` | `[0, 4.0]` | `[0, +2.40]` | **出隅** (convex) |
| `Castle Wall Corner 2_2x2` | `dc63c516` | `[-2.00, 0]` | `[0, 4.0]` | `[0, +2.00]` | 入隅 (concave) |

At the project's **`scale = (1, h, 1)`**: straight = 2.4 m thick × 2.0 m along the run;
出隅 = 2.4 × 2.4 square. Height is **4.0 m per 1.0 of `scale.y`**.

Counter-intuitive and worth re-reading: **`scale.x` is the wall THICKNESS, `scale.z` stretches the
piece ALONG the run.** For yaw θ: local `+Z` = `(sinθ, cosθ)` = direction of travel;
local `−X` = `(−cosθ, sinθ)` = the wall body, i.e. the **left of travel**.

### The two constraints that place a corner

A corner block has two dressed faces meeting at an **apex**. In plan (scale 1) the block is a square
with four points; name them by local coords:

```
   apex (-2.4,+2.4) ─── face B ─── Z (0,+2.4)
        │                              │
     face A                        (butt end)
        │                              │
   X (-2.4, 0) ────── (butt end) ──── O (0,0) = pivot
```

Face A is the segment `X`–`apex`; face B is `Z`–`apex`. Every corner is set by exactly two
constraints, and **neither of them is an angle**:

### R1 — 片方の面を、隣の石垣の面と完全に一致させる

Pick one of the two walls meeting here. The corner's corresponding face must be **coplanar** with
that wall's outer face — not close, coplanar. Measured across the user's 12 corners: flush-face
angle **0.00°**, face offset within **0.04 m**.

Which of the two walls you pick is free (the user used the outgoing run on 10 of 12, the incoming on
2). What is never acceptable is a corner flush with neither, or "split the difference" between them —
that opens two seams instead of none.

### R2 — もう一方の辺は、コーナーのもう一方の面の**端点**に合わせる

The other wall's outer face must pass through the **non-apex endpoint** of the corner's other face:
`X` if face B is the flush one, `Z` if face A is. Slide the block along the flush face until that
lands, and the corner is placed.

Measured — signed distance from that endpoint to the other wall's outer-face plane:

| group | the four corners |
|---|---|
| 加納 | −0.010, −0.049, +0.038, **(−0.920)** |
| 松平 | −0.003, −0.048, −0.055, **(−0.467)** |
| 太田 | −0.024, +0.002, −0.011, −0.028 |

**10 of 12 within 0.06 m.** The two in bold are the loosest fits on the site and carry 0.5–0.9 m of
hand slack.

This is the constraint that makes the angle free: the corner hands the next wall a **point**, not a
direction. The next wall then leaves at whatever heading the site requires, and the two faces open or
close into a V about that pinned endpoint. **Never derive the next wall's direction from the corner,
and never require the turn to be near square.**

> Measure with the endpoint, not the apex. The apex's distance to the neighbouring face scatters over
> ±0.85 m across the same 12 corners — it is a consequence of the turn, not a control point. This is
> exactly what the machine version got wrong: `pc = A + localX*2.4 − localZ*2.4` pins the *apex* to
> the boundary vertex, which put every block **3.40 m** (= √2 × 2.4, one wall thickness diagonally)
> off, on the inward side of the boundary — a 2.4 m stone cube standing in the garden with the actual
> corner of the enclosure left open. `f9bd701` was worse still (37 – 2436 m). The user's blocks land
> 0.01 – 0.69 m from the vertex, but that is a *result* of R1+R2, not the rule.

**Closed form for a generator.** If you choose the outgoing run (heading θ) as the flush wall, R1+R2
collapse to `yaw = θ − 90°`, `position = the boundary vertex`. The `−90` here is the block's own
square geometry, **not** an assumption about the turn — it holds for any turn angle. Always verify
the result against R1 and R2 rather than trusting the shortcut.

### R3 — 辺はまっすぐ通す。同じ面に見えるものは1本の辺

A corner block belongs where the wall genuinely changes face. If two runs read as one continuous
face, they *are* one run: one heading, one line, no block between them.

This was the second defect in the machine versions. `a3f5187`'s 松平 was authored as a 6-gon whose
extra vertices barely deviated from straight; each got a 2.4 m corner block, which reads as a lump in
an otherwise straight 140 m wall. The user merged them into single runs and deleted the two blocks:
6 corners → 4.

The test is a **distance, not an angle** — fit a line to a run's pivots and check the lateral spread
(§2). The user's runs measure ≤ 0.077 m over 153 m. A "run" whose pivots spread further than ~0.1 m
is two headings pretending to be one; either straighten it or give it a real corner.

| group | straights | runs | 出隅 | 入隅 |
|---|---|---|---|---|
| 太田 | 133 | 4 | 4 | 0 |
| 加納 | 150 | 4 | 4 | 0 |
| 松平 | 308 | 4 | 4 | 0 |

A convex parcel needs **only 出隅**. `Castle Wall Corner 2_2x2` (入隅) goes at a concave junction —
same R1/R2 construction, 2.0 m block instead of 2.4 m. A 横矢掛かり / rectangular jog is
出隅×2 + 入隅×2.

### R4 — 両側の直線を出隅に食い込ませる。突き合わせない

Measured distance along the run from the corner pivot to the nearest straight piece:

- outgoing run's first straight: **0.84 – 1.97 m** (always < the 2.4 m corner depth)
- incoming run's last straight: **0.19 – 1.81 m** (always < the 2.0 m module)

Both runs are carried *into* the corner footprint. A straight piece left buried inside the corner
block is fine — keep it as fill. **A seam is worse than an overlap**, always.

---

---

## 9. Pivot gotcha — never place or measure by `transform.position`

The kit's pivots are not at the mesh centre. Mesh-centre offset, local, pre-scale:

| part | offset |
|---|---|
| `Castle Wall` | `(-1.20, 0, -1.00)` |
| `Castle Wall Corner` / `Corner 2_2x2` | `(-1.20, 0, +1.20)` |

So a corner whose `transform.position` looks 3.4 m off the wall line can be perfectly placed — and
the reverse. **Place by `transform.position` (the rules above are written in pivot terms), but check
alignment, gaps and coping with `Renderer.bounds`.**

```csharp
var rs = t.GetComponentsInChildren<Renderer>();
var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
// b.max.y == coping height, b.center == true plan position
```