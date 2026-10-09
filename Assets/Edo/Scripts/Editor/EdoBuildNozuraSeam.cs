// EdoBuild — 野面の土留めの継ぎ目と見え面を光線で測る(2026-10-09・EDO-0502 第64巡・施主「石垣の隙間に土が見えていたり、
//   石垣の部材のつなぎ目で段差ができてたり」)。⛔ 測るだけ ── 直さない(直しは据える関数の側: FaceAcross・flatRanges)。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>**野面の継ぎ目の段差と、見え面から土が覗く所を数える**(2026-10-09・EDO-0502 第64巡)。
    /// 一時の MeshCollider を駒・皮・近くの部材に掛け(<paramref name="walls"/> の子 = 野面の駒・<paramref name="skin"/> = 縁の皮・地形は TerrainCollider)、
    /// <para>① 継ぎ目: 外接箱の触れる駒の対ごとに、直線の駒の見え面の向きで継ぎ目の両脇 0.12〜0.44 へ水平の光線を打ち、見え面の前後の差(高さごとの中央値の中央値)、
    /// 天端の差(見え面から 0.1〜0.45 奥へ下ろした光線の中央値の差 ── 勾配の駒・隅の駒を含む対は数えない)、走りの向きの口(実メッシュの射影の重なり &lt; 0)を測る。
    /// 見え面のずれは【柔】(狙い 0.05)・天端の差は天端一直線の run で【硬】・口は【硬】(隙 0)。</para>
    /// <para>② 土: 駒ごとに見え面の向き(隅の駒は触れる直線の駒の向き)で 0.08 格子の水平の光線を打ち、前の地表 + 0.3 より上で最初に当たるのが皮・地形のもの ──
    /// 「被り」= 自分の面の手前 0.4 以内に土(土が見え面を覆う)/「口」= 自分に当たらず端から 0.3 以内(継ぎ目から土が覗く)/「穴」= 自分に当たらず端から 0.3 より内(直線の駒だけ)。
    /// いずれも【硬】(許容 0 の隙・被り)。</para>
    /// ⟶ 返す: 要約の数行(件数・最悪・上位)。<paramref name="tsv"/> を渡せば明細を書く。⚠ 一回 15 秒前後(駒 190・光線 12 万)── 30 秒を超える所では呼ばない。
    /// 当たる先: 野面の乱積みの土留めを持つ全邸(岡部 Dan・山王 前庭)── Stage3b の末に刷る。</summary>
    public static string NozuraSeamReport(Transform root, Transform walls, Transform skin, string tsv = null)
    {
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        var ws = new List<GameObject>(); foreach (Transform c in walls) if (c.gameObject.activeInHierarchy) ws.Add(c.gameObject);
        var tmp = new GameObject("__seam_tmp_colliders"); tmp.hideFlags = HideFlags.HideAndDontSave;
        var kind = new Dictionary<Collider, string>(); var owner = new Dictionary<Collider, GameObject>(); var ownC = new Dictionary<GameObject, List<Collider>>();
        var wb = new List<Bounds>();
        Action<MeshFilter, string, GameObject> addC = (mf, k, own) =>
        {
            if (mf.sharedMesh == null) return; var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) return;
            var go = new GameObject("c"); go.hideFlags = HideFlags.HideAndDontSave; go.transform.SetParent(tmp.transform, false);
            go.transform.position = mf.transform.position; go.transform.rotation = mf.transform.rotation; go.transform.localScale = mf.transform.lossyScale;
            var mc = go.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; kind[mc] = k; owner[mc] = own;
            if (k == "wall") { List<Collider> l; if (!ownC.TryGetValue(own, out l)) ownC[own] = l = new List<Collider>(); l.Add(mc); }
        };
        var sbJ = new System.Text.StringBuilder(); var sbS = new System.Text.StringBuilder(); string summary;
        try
        {
            foreach (var w in ws) { foreach (var mf in w.GetComponentsInChildren<MeshFilter>()) addC(mf, "wall", w); wb.Add(RB(w)); }
            if (skin != null) foreach (var mf in skin.GetComponentsInChildren<MeshFilter>()) addC(mf, "skin", skin.gameObject);
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.transform.IsChildOf(walls) || (skin != null && mf.transform.IsChildOf(skin))) continue;
                var rr = mf.GetComponent<Renderer>(); if (rr == null) continue; var b = rr.bounds; bool near = false;
                foreach (var x in wb) { var e = x; e.Expand(3f); if (e.Intersects(b)) { near = true; break; } }
                if (near) addC(mf, "other", mf.gameObject);
            }
            Physics.SyncTransforms();
            var dg = Drawn();
            Func<Vector3, Vector3, float, RaycastHit[]> cast = (o, d, maxd) => { var hs = Physics.RaycastAll(o, d, maxd); Array.Sort(hs, (a, b2) => a.distance.CompareTo(b2.distance)); return hs; };
            Func<RaycastHit, string> kOf = h => { string k; return kind.TryGetValue(h.collider, out k) ? k : (h.collider is TerrainCollider ? "terrain" : "ext"); };
            var fOf = new Dictionary<GameObject, Vector2>(); var straight = new Dictionary<GameObject, bool>(); var flat = new Dictionary<GameObject, bool>(); var vs = new Dictionary<GameObject, List<Vector3>>();
            foreach (var w in ws)
            {
                fOf[w] = new Vector2(w.transform.forward.x, w.transform.forward.z).normalized; straight[w] = !w.name.Contains("kado");
                var mf = w.GetComponentInChildren<MeshFilter>(); string mn = mf != null && mf.sharedMesh != null ? mf.sharedMesh.name : "";
                flat[w] = straight[w] && (mn.Contains("G+000") || mn.Contains("Tome")); vs[w] = Body(w.transform, 999999);
            }
            // ---- ① 継ぎ目 ----
            int nJ = 0, nF = 0, nC = 0, nG = 0, nK = 0; float wF = 0f, wC = 0f, wG = 0f; var topJ = new List<KeyValuePair<float, string>>();
            for (int i = 0; i < ws.Count; i++) for (int j = i + 1; j < ws.Count; j++)
            {
                var a = ws[i]; var b = ws[j]; var ba = wb[i]; ba.Expand(0.05f); if (!ba.Intersects(wb[j])) continue;
                GameObject s = straight[a] ? a : (straight[b] ? b : null); if (s == null) continue;
                Vector2 f = fOf[s];
                float ang = Vector2.Angle(fOf[a], fOf[b]);
                if (straight[a] && straight[b] && ang > 25f) continue;    // 入隅・T 字(隅の駒の無い折れ)は継ぎ目でない
                Vector2 X = new Vector2(f.y, -f.x); Vector2 o = new Vector2(s.transform.position.x, s.transform.position.z);
                Func<GameObject, float[]> pr = g => { float a0 = 1e9f, a1 = -1e9f, y0 = 1e9f, y1 = -1e9f; foreach (var v in vs[g]) { float u = Vector2.Dot(new Vector2(v.x, v.z) - o, X); a0 = Mathf.Min(a0, u); a1 = Mathf.Max(a1, u); y0 = Mathf.Min(y0, v.y); y1 = Mathf.Max(y1, v.y); } return new[] { a0, a1, y0, y1 }; };
                var pa = pr(a); var pb = pr(b);
                bool aL = (pa[0] + pa[1]) < (pb[0] + pb[1]); GameObject L = aL ? a : b, R = aL ? b : a; var pl = aL ? pa : pb; var prr = aL ? pb : pa;
                float ov = Mathf.Min(pl[1], prr[1]) - Mathf.Max(pl[0], prr[0]);
                if (ov > 1.0f) continue;                                   // 積み下ろし・重ねて埋める駒(継ぎ目でない)
                if (ov < -0.6f) continue;                                  // 外接箱だけ触れる隣でない駒(隅の駒の腕の先の向こうの駒)
                float seam = 0.5f * (pl[1] + prr[0]);
                float yLo = Mathf.Max(pl[2], prr[2]), yHi = Mathf.Min(pl[3], prr[3]);
                Vector2 sp = o + X * seam; float fg = dg.At(sp.x + f.x * 0.6f, sp.y + f.y * 0.6f); if (float.IsNaN(fg)) fg = yLo;
                var dfs = new List<float>();
                for (float h = Mathf.Max(yLo, fg) + 0.1f; h <= yHi - 0.15f; h += 0.1f)
                {
                    var la = new List<float>(); var lb = new List<float>();
                    foreach (float du in new[] { 0.12f, 0.2f, 0.28f, 0.36f, 0.44f })
                        for (int side = 0; side < 2; side++)
                        {
                            float u = side == 0 ? seam - du : seam + du; Vector2 q = o + X * u + f * 2.0f;
                            foreach (var hh in cast(new Vector3(q.x, h, q.y), new Vector3(-f.x, 0f, -f.y), 4f))
                            { if (kOf(hh) != "wall") continue; if (owner[hh.collider] == (side == 0 ? L : R)) (side == 0 ? la : lb).Add(hh.distance); break; }
                        }
                    if (la.Count >= 2 && lb.Count >= 2) { la.Sort(); lb.Sort(); dfs.Add(la[la.Count / 2] - lb[lb.Count / 2]); }
                }
                float fd = float.NaN; if (dfs.Count > 0) { dfs.Sort(); fd = dfs[dfs.Count / 2]; }
                float faceRef = -1e9f; foreach (var v in vs[L]) if (v.y >= pl[3] - 0.3f) faceRef = Mathf.Max(faceRef, Vector2.Dot(new Vector2(v.x, v.z) - o, f));
                var ta = new List<float>(); var tb = new List<float>();
                foreach (float du in new[] { 0.15f, 0.25f, 0.35f })
                    foreach (float dd in new[] { 0.1f, 0.2f, 0.3f, 0.45f })
                        for (int side = 0; side < 2; side++)
                        {
                            float u = side == 0 ? seam - du : seam + du; Vector2 q = o + X * u + f * (faceRef - dd);
                            foreach (var hh in cast(new Vector3(q.x, yHi + 2f, q.y), Vector3.down, 4f))
                            { if (kOf(hh) != "wall") continue; if (owner[hh.collider] == (side == 0 ? L : R)) (side == 0 ? ta : tb).Add(hh.point.y); break; }
                        }
                float cd = float.NaN; bool crestCounted = flat[L] && flat[R] && ang < 1f;
                if (ta.Count >= 3 && tb.Count >= 3) { ta.Sort(); tb.Sort(); cd = tb[tb.Count / 2] - ta[ta.Count / 2]; }
                nJ++; if (ang >= 1f) nK++;
                if (!float.IsNaN(fd) && Mathf.Abs(fd) > 0.05f) nF++; if (!float.IsNaN(fd)) wF = Mathf.Max(wF, Mathf.Abs(fd));
                if (crestCounted && !float.IsNaN(cd)) { if (Mathf.Abs(cd) > 0.05f) nC++; wC = Mathf.Max(wC, Mathf.Abs(cd)); }
                if (ov < -0.02f) { nG++; wG = Mathf.Max(wG, -ov); }
                float worst = Mathf.Max(float.IsNaN(fd) ? 0f : Mathf.Abs(fd), Mathf.Max(crestCounted && !float.IsNaN(cd) ? Mathf.Abs(cd) : 0f, -ov));
                string line = L.name + " × " + R.name + " 前後 " + fd.ToString("+0.000;-0.000", ci) + (crestCounted ? " 天端 " + cd.ToString("+0.000;-0.000", ci) : "") + " 口 " + Mathf.Max(0f, -ov).ToString("F3", ci) + (ang >= 1f ? " 折れ " + ang.ToString("F1", ci) + "°" : "");
                topJ.Add(new KeyValuePair<float, string>(worst, line));
                sbJ.AppendLine("J\t" + L.name + "\t" + R.name + "\t" + fd.ToString("F3", ci) + "\t" + cd.ToString("F3", ci) + "\t" + (crestCounted ? 1 : 0) + "\t" + ov.ToString("F3", ci) + "\t" + ang.ToString("F1", ci) + "\t" + sp.x.ToString("F2", ci) + "," + sp.y.ToString("F2", ci));
            }
            // ---- ② 土 ----
            int nCov = 0, nKuchi = 0, nAna = 0; float wCov = 0f; var byPiece = new Dictionary<string, int>();
            var hit1 = new RaycastHit();
            foreach (var w in ws)
            {
                var dirs = new List<Vector2>();
                if (straight[w]) dirs.Add(fOf[w]);
                else
                {
                    var b1 = RB(w); b1.Expand(0.1f);
                    for (int j = 0; j < ws.Count; j++) if (straight[ws[j]] && b1.Intersects(wb[j]))
                    { bool dup = false; foreach (var d0 in dirs) if (Vector2.Dot(d0, fOf[ws[j]]) > 0.95f) dup = true; if (!dup) dirs.Add(fOf[ws[j]]); }
                }
                List<Collider> mine; if (!ownC.TryGetValue(w, out mine)) continue;
                foreach (var f in dirs)
                {
                    Vector2 X = new Vector2(f.y, -f.x); Vector2 o = new Vector2(w.transform.position.x, w.transform.position.z);
                    float a0 = 1e9f, a1 = -1e9f, y0 = 1e9f, y1 = -1e9f, fr = -1e9f;
                    foreach (var v in vs[w]) { var r = new Vector2(v.x, v.z) - o; float u = Vector2.Dot(r, X); a0 = Mathf.Min(a0, u); a1 = Mathf.Max(a1, u); y0 = Mathf.Min(y0, v.y); y1 = Mathf.Max(y1, v.y); fr = Mathf.Max(fr, Vector2.Dot(r, f)); }
                    for (float u = a0 + 0.03f; u <= a1 - 0.03f; u += 0.08f)
                    {
                        Vector2 bs = o + X * u; float fg = dg.At(bs.x + f.x * (fr + 0.6f), bs.y + f.y * (fr + 0.6f));
                        for (float h = y0 + 0.02f; h <= y1 - 0.02f; h += 0.08f)
                        {
                            if (!float.IsNaN(fg) && h < fg + 0.3f) continue;
                            Vector2 q = bs + f * (fr + 1.5f); var o3 = new Vector3(q.x, h, q.y); var d3 = new Vector3(-f.x, 0f, -f.y);
                            var hs = cast(o3, d3, 3.5f); if (hs.Length == 0) continue; string k = kOf(hs[0]);
                            if (k != "skin" && k != "terrain") continue;
                            float dOwn = float.NaN; var ray = new Ray(o3, d3);
                            foreach (var c in mine) if (c.Raycast(ray, out hit1, 3.5f) && (float.IsNaN(dOwn) || hit1.distance < dOwn)) dOwn = hit1.distance;
                            string cat = null; float dep = float.NaN;
                            if (!float.IsNaN(dOwn)) { dep = dOwn - hs[0].distance; if (dep > 0.005f && dep <= 0.4f) cat = "被り"; }
                            else if (Mathf.Min(u - a0, a1 - u) < 0.3f) cat = "口";
                            else if (straight[w]) cat = "穴";
                            if (cat == null) continue;
                            if (cat == "被り") { nCov++; wCov = Mathf.Max(wCov, dep); } else if (cat == "口") nKuchi++; else nAna++;
                            int nn; byPiece.TryGetValue(w.name, out nn); byPiece[w.name] = nn + 1;
                            sbS.AppendLine("S\t" + w.name + "\t" + cat + "\t" + k + "\t" + u.ToString("F2", ci) + "\t" + h.ToString("F2", ci) + "\t" + (h - fg).ToString("F2", ci) + "\t" + (y1 - h).ToString("F2", ci) + "\t" + dep.ToString("F3", ci) + "\t" + hs[0].point.x.ToString("F2", ci) + "," + hs[0].point.z.ToString("F2", ci));
                        }
                    }
                }
            }
            topJ.Sort((x, y) => y.Key.CompareTo(x.Key));
            var pcs = new List<KeyValuePair<string, int>>(byPiece); pcs.Sort((x, y) => y.Value.CompareTo(x.Value));
            var sb = new System.Text.StringBuilder();
            sb.AppendLine("野面の継ぎ目(光線・" + nJ + " 対・うち折れ " + nK + "): 見え面の前後 > 0.05 が " + nF + "(最悪 " + wF.ToString("F3", ci) + "・柔 狙い 0.05)/ 天端の差 > 0.05 が " + nC + "(水平の駒どうし・最悪 " + wC.ToString("F3", ci) + "・硬)/ 走りの口 > 0.02 が " + nG + "(最悪 " + wG.ToString("F3", ci) + "・硬)");
            for (int i = 0; i < Mathf.Min(8, topJ.Count); i++) sb.AppendLine("    " + topJ[i].Value);
            sb.AppendLine("野面の見え面の土(前の地表 +0.3 より上・0.08 格子): 被り " + nCov + "(最悪 " + wCov.ToString("F3", ci) + ")/ 継ぎ目の口から土 " + nKuchi + " / 面の穴から土 " + nAna + "(硬 0)");
            for (int i = 0; i < Mathf.Min(8, pcs.Count); i++) sb.Append((i == 0 ? "    " : "・") + pcs[i].Key + " " + pcs[i].Value);
            summary = sb.ToString();
        }
        finally { UnityEngine.Object.DestroyImmediate(tmp); }
        if (!string.IsNullOrEmpty(tsv)) { System.IO.File.WriteAllText(tsv + "_joints.tsv", sbJ.ToString()); System.IO.File.WriteAllText(tsv + "_soil.tsv", sbS.ToString()); }
        return summary;
    }
}
