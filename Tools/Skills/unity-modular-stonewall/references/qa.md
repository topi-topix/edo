# QAスクリプトと目視検証

SKILL.md §5 の合格表に対する実行手段。

```csharp
// paste into mcp__unityMCP__execute_code — per-group audit
var sb = new System.Text.StringBuilder();
foreach (var n in new string[]{"Edo_Yashiki_Ota","Edo_Yashiki_Kano","Edo_Yashiki_Matsudaira"}) {
  var root = GameObject.Find(n).transform.Find("Ishigaki");
  var py = new System.Collections.Generic.HashSet<float>();
  var sy = new System.Collections.Generic.HashSet<float>();
  var yaws = new System.Collections.Generic.Dictionary<int,int>();
  float lo = 9999, hi = -9999; int corners = 0;
  foreach (Transform c in root) {
    py.Add(Mathf.Round(c.position.y*1000)/1000f);
    sy.Add(Mathf.Round(c.localScale.y*1000)/1000f);
    bool isC = c.name.Contains("CWC") || c.name.Contains("Corner");
    if (isC) corners++;
    else { int k = Mathf.RoundToInt(c.eulerAngles.y*100);
           yaws[k] = yaws.ContainsKey(k) ? yaws[k]+1 : 1; }
    var rs = c.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) continue;
    var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
    lo = Mathf.Min(lo, b.max.y); hi = Mathf.Max(hi, b.max.y);
  }
  sb.AppendLine(n + " n=" + root.childCount + " 出隅=" + corners
    + " posY=" + py.Count + " scaleY=" + sy.Count
    + " 天端ばらつき=" + (hi-lo).ToString("F3") + "m headings=" + yaws.Count);
  foreach (var kv in yaws) sb.Append("   yaw " + (kv.Key/100f).ToString("F2") + " n=" + kv.Value + "\n");
}
return sb.ToString();
```

For the geometric checks (vertex distance, flush-face angle, pitch histogram, lateral spread), dump
the transforms to CSV and analyse offline — see `references/yashiki-enclosure-baseline.md`, which
contains the dump snippet and the reference numbers to compare against.

Auditing an **older committed version** (to see what changed) is easier outside Unity:
`git show <sha>:Assets/Edo/Scenes/Akasaka.unity`, then parse the `--- !u!1001` prefab instances with
`references/scene_prefab_dump.py` (Ext_* groups) or `references/dump_yashiki.py` (屋敷 groups).

## 5b. Verify visually, always

Numbers pass ⇏ it looks right. Three shots close every wall job (`manage_camera` with
`view_position` + `view_rotation` euler — `view_target` takes a GameObject *name*, so use the
explicit pair for a free viewpoint):

1. **Top-down just above coping height at a corner** — does the block actually close the L?
2. **Low oblique along the run** — the coping must read as one straight edge.
3. **Wide 3/4 from outside** — catches the ground stepping down the wall face in 2 m heightmap
   terraces, which no transform metric will report.