# 屋敷囲い石垣 — the user's hand-built baseline (measured)

Everything here was measured off the live Akasaka scene at commit `038a07d`
(`Edo_Yashiki_{Ota,Kano,Matsudaira}/Ishigaki`) and cross-checked against the two machine-generated
versions the user rejected. These are the numbers §1–§5 of `SKILL.md` are derived from; use them as
the acceptance target when rebuilding or reviewing a 屋敷 wall.

## Dumping the current state

```csharp
// mcp__unityMCP__execute_code — writes one row per piece
var sb = new System.Text.StringBuilder();
sb.AppendLine("group,idx,name,prefab,px,py,pz,rx,ry,rz,sx,sy,sz,bcx,bcy,bcz,bex,bey,bez");
string[] roots = {"Edo_Yashiki_Ota/Ishigaki","Edo_Yashiki_Kano/Ishigaki","Edo_Yashiki_Matsudaira/Ishigaki"};
foreach (var rn in roots) {
  var root = GameObject.Find(rn); int i = 0;
  foreach (Transform c in root.transform) {
    var src = UnityEditor.PrefabUtility.GetCorrespondingObjectFromSource(c.gameObject);
    string pf = src != null ? System.IO.Path.GetFileNameWithoutExtension(UnityEditor.AssetDatabase.GetAssetPath(src)) : "(none)";
    var rs = c.GetComponentsInChildren<Renderer>();
    Bounds b = new Bounds(c.position, Vector3.zero);
    if (rs.Length > 0) { b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); }
    var e = c.eulerAngles; var p = c.position; var s = c.localScale;
    sb.AppendLine(string.Format("{0},{1},{2},{3},{4:F3},{5:F3},{6:F3},{7:F2},{8:F2},{9:F2},{10:F4},{11:F4},{12:F4},{13:F3},{14:F3},{15:F3},{16:F3},{17:F3},{18:F3}",
      rn.Split('/')[0], i++, c.name, pf, p.x,p.y,p.z, e.x,e.y,e.z, s.x,s.y,s.z,
      b.center.x,b.center.y,b.center.z, b.extents.x,b.extents.y,b.extents.z));
  }
}
System.IO.File.WriteAllText("<scratchpad>/ishigaki_now.csv", sb.ToString());
return sb.Length;
```

For a past commit, use `dump_yashiki.py` (parses `Edo_Yashiki_*/Ishigaki` out of the scene YAML):

```bash
git show "038a07d:Assets/Edo/Scenes/Akasaka.unity" > /tmp/x.unity
python3 references/dump_yashiki.py /tmp/x.unity /tmp/x.json
```

(zsh gotcha: always brace `"${c}:Assets/…"` — a bare `$c:A…` triggers history modifiers.)

`scene_prefab_dump.py` is the equivalent for the flat `Ishigaki_Ext_*` groups (§8 walls).

## Shipped composition

| group | pieces | `Castle Wall` | `Castle Wall Corner` | scale | `position.y` | coping |
|---|---|---|---|---|---|---|
| 太田 | 137 | 133 | 4 | (1, 1.500, 1) | -21.000 | -15.00 |
| 加納 | 154 | 150 | 4 | (1, 2.000, 1) | -19.000 | -11.00 |
| 松平 | 312 | 308 | 4 | (1, 2.000, 1) | -19.000 | -11.00 |

`rotation.x = rotation.z = 0` on all 603 pieces. One `position.y` and one `scale.y` per group.
Coping spread `max−min` of `Renderer.bounds.max.y` = **0.000 m** in all three.

## Headings

Straight headings, Unity yaw (degrees):

| group | headings |
|---|---|
| 太田 | 49.07 / 118.17 / 225.68 / 308.00 |
| 加納 | 57.53 / 117.95 / 229.00 / 308.00 |
| 松平 | 57.53 / 128.00 / 225.68 / 310.04 |

Traversal is yaw-increasing = clockwise from above; the wall body lands on the left of travel, i.e.
**outside** the pivot polygon (verified: body-direction · toward-centroid < 0 on all 12 runs).

> The turn at each corner varies from site to site and is **not a criterion** — do not derive a rule
> from it, and do not gate a QA pass on it. Corners are placed by R1 (one face coplanar with a
> neighbouring wall) and R2 (the other wall's outer face through the non-apex endpoint of the other
> face). Both are distances.

## Corners, piece by piece

`flush` = which run the corner is exactly coplanar with (R1). `R2 offset` = signed distance from the
**non-apex endpoint** of the corner's other face to the other wall's outer-face plane. `apex offset`
is shown only to demonstrate that the apex is *not* the control point.

| group | corner yaw | flush with | R1 offset | R2 offset | apex offset | pivot→vertex | gap to next straight | gap from prev straight |
|---|---|---|---|---|---|---|---|---|
| 加納 | 27.95 | outgoing 117.95 | −0.011 | **−0.920** | +0.265 | 0.69 | 1.919 | 1.186 |
| 加納 | 139.00 | outgoing 229.00 | −0.007 | +0.038 | −0.824 | 0.21 | 0.844 | 1.115 |
| 加納 | 218.00 | outgoing 308.00 | −0.003 | −0.010 | +0.448 | 0.04 | 1.076 | 0.193 |
| 加納 | 327.53 | outgoing 57.53 | +0.025 | −0.049 | −0.851 | 0.11 | 1.283 | 0.701 |
| 松平 | 38.00 | outgoing 128.00 | +0.001 | **−0.467** | +0.335 | 0.35 | 1.966 | 0.606 |
| 松平 | 135.68 | outgoing 225.68 | +0.010 | −0.003 | −0.324 | 0.02 | 1.919 | 0.587 |
| 松平 | 225.68 | **incoming** 225.68 | −0.016 | −0.055 | +0.181 | 0.04 | 1.267 | 0.877 |
| 松平 | 327.53 | outgoing 57.53 | −0.035 | −0.048 | −0.769 | 0.07 | 1.413 | 1.155 |
| 太田 | 28.17 | outgoing 118.17 | −0.003 | −0.011 | +0.845 | 0.16 | 1.973 | 0.785 |
| 太田 | 135.68 | outgoing 225.68 | −0.022 | −0.024 | −0.746 | 0.09 | 1.138 | 0.928 |
| 太田 | 225.68 | **incoming** 225.68 | +0.005 | −0.028 | +0.293 | 0.01 | 1.958 | 1.810 |
| 太田 | 319.00 | outgoing 49.07 | −0.037 | +0.002 | −0.456 | 0.05 | 1.459 | 1.587 |

Flush-face angle reads **0.00°** in every row (0.07° on 太田/319.00) and the offset is ≤ 0.037 m.
R2 is within **0.06 m** on 10 of 12; the two bold rows are the sharpest turns on the site and carry
hand slack. The apex column ranges over ±0.85 m with no pattern — pinning the apex is what the
machine version did wrong.

Which wall is chosen as the flush one is free: the user used the outgoing run on 10 of 12 and the
incoming on 2 (both duplicate instances, `CWC_2` / `CWC_3 (2)`, moved without re-rotating).

## Straight runs

| group | heading | n | length | pitch | lateral spread | gate gap |
|---|---|---|---|---|---|---|
| 太田 | 49.07 | 47 | 79.29 | 1.42–1.89 | 0.054 | — |
| 太田 | 118.17 | 23 | 40.31 | 1.29–1.99 | 0.008 | — |
| 太田 | 225.68 | 39 | 85.26 | 1.40–1.98 | 0.029 | **15.52** |
| 太田 | 308.00 | 24 | 43.03 | 1.62–1.94 | 0.021 | — |
| 加納 | 57.53 | 24 | 68.46 | 1.800 | 0.011 | **29.01** |
| 加納 | 117.95 | 38 | 66.60 | 1.800 | 0.001 | — |
| 加納 | 229.00 | 45 | 78.76 | 1.800 | 0.003 | — |
| 加納 | 308.00 | 43 | 75.05 | 1.800 | 0.001 | — |
| 松平 | 57.53 | 73 | 142.51 | 1.800 | 0.077 | **17.07** |
| 松平 | 128.00 | 70 | 123.04 | 1.800 | 0.013 | — |
| 松平 | 225.68 | 79 | 139.95 | 1.800 | 0.009 | — |
| 松平 | 310.04 | 86 | 153.28 | 1.800 | 0.015 | — |

423 of 450 joints in 加納 + 松平 are 1.800 ± 0.005. The exceptions are the single short closing piece
at a run end (1.25 / 1.28 / 1.35 / 1.36 / 1.61 m) — deliberate overlap, not error.

太田's irregular pitch is an older hand pass predating the 1.80 convention; it is not a target.

## What the machine versions got wrong

| | `f9bd701` (v1) | `a3f5187` (v2) | `038a07d` (user) |
|---|---|---|---|
| straight scale | (2, h, 1.3) | (1, h, 1) | (1, h, 1) |
| corner scale | (2, h, 2.0) | (1, h, 1) | (1, h, 1) |
| 松平 runs | 6 (2 pairs that read as one face) | 6 (extra vertices barely off straight) | **4** |
| 松平 corners | 6 | 6 | **4** |
| R2 — other wall's face → non-apex endpoint | not met | not met | **≤ 0.06 m on 10/12** |
| corner pivot → vertex (a *result*, not the rule) | 37 – 2436 m | **3.40 m** (= √2 × 2.4) on every corner | **≤ 0.69 m** |
| 松平 base / coping | -19.5 / -11.5 | -19.5 / -11.5 | **-19.0 / -11.0** |

The 3.40 m offset came from `pc = A + localX*2.4 − localZ*2.4`, which pins the block's *outer apex*
to the boundary vertex. Because the straights' bodies sit on the **outward** side of the boundary
line, that lands the corner block on the **inward** side — a 2.4 m stone cube in the garden with the
enclosure's actual corner left open. The apex is never the control point; the non-apex endpoint of
the non-flush face is. `EdoYashikiBuilder.cs:635` still contains this formula; it is inert only
because `f8f9209` made the builder preserve an existing `Ishigaki` child.

## Known open defect

松平's 築地塀 bottom is **-11.50** against a coping of **-11.00** — the 塀 is sunk 0.50 m into the wall
top. `EdoYashikiBuilder.cs` still carries `padY = -13.0` for that site while the user raised the wall
to a coping of -11.00. 太田 (-15.00) and 加納 (-11.00) match exactly. Whatever places the 塀 must read
the coping off the wall, not off a constant.
