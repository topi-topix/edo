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
                // 奥を通す埋めた駒(_Tooshi・const.abutOrder「土に埋め・根入れと同じ扱い」)は継ぎ目の対にしない ── 見え面を持たず、表の駒の背で重なるだけ(第105巡)
                if (a.name.Contains("_Tooshi") || b.name.Contains("_Tooshi")) continue;
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
                if (ov < -0.02f)
                {   // 間に挟まる駒が口を覆っていれば隣でない(第70巡: 岡部 Kado79 × 039f の口 0.401 は間の 038f が −2.78〜−0.93 で覆っていた ── 偽の口)
                    bool covered = false; float g0 = Mathf.Min(pl[1], prr[1]), g1 = Mathf.Max(pl[0], prr[0]);
                    foreach (var w3 in ws) { if (w3 == a || w3 == b) continue; var b3 = RB(w3); b3.Expand(0.05f); if (!b3.Intersects(ba)) continue; var p3 = pr(w3); if (p3[0] <= g0 + 0.02f && p3[1] >= g1 - 0.02f) { covered = true; break; } }
                    if (covered) continue;
                }
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

    /// <summary>**皮の頂点が野面の見え面の平面より前に出ないか**(硬・EDO-0502 第69巡 ── 施主「石垣の隙間に土が見える」の縦の帯の検め)。
    /// 駒ごと・見え面ごとに <see cref="NozuraCrestCover"/> の帯(天端の前の縁 → 法尻の平面・<see cref="NozuraCrestCover.FacePlaneY"/>)を作り、
    /// 駒の外形の中で天端の前の縁より前にある皮の頂点が 平面 − 0.02 を越えたら数える。根入れの土(帯の前 0.25〜1.0 の皮の頂点の最も低い高さ = 前の地表)以下は数えない。
    /// ⟶ 返す: 件数・最悪(平面からの高さ)・上位の駒。当たる先: 野面の乱積みの土留めを持つ全邸(岡部 Dan)── Stage3b の末に刷る。</summary>
    public static string NozuraSkinPlaneCheck(Transform walls, Transform skin)
    {
        var cc = new NozuraCrestCover(); var hullOf = new Dictionary<GameObject, Vector2[]>();
        foreach (Transform c in walls)
        {
            if (!c.gameObject.activeInHierarchy) continue; var mf = c.GetComponentInChildren<MeshFilter>(); if (mf == null || mf.sharedMesh == null || !mf.sharedMesh.name.Contains("Nozura")) continue;
            if (c.name.Contains("_Tooshi")) continue;   // 入隅の通しの駒(PlaceNozuraNet・const.abutOrder 10-10o「土に埋め・根入れと同じ扱い」)── 見え面を持たない
            cc.Add(c.gameObject, mf.sharedMesh.name.Contains("_Kado"));
        }
        foreach (var fb in cc.list) if (!hullOf.ContainsKey(fb.go)) hullOf[fb.go] = cc.HullOf(fb.go);
        var pts = new List<Vector3>();
        foreach (var mf in skin.GetComponentsInChildren<MeshFilter>()) { if (mf.sharedMesh == null) continue; var V = mf.sharedMesh.vertices; foreach (var v in V) pts.Add(mf.transform.TransformPoint(v)); }
        // 前の地表(帯ごと): 外形の外・前 0.25〜1.0 の頂点の高さの中央値(前後 2 割り)
        var gF = new Dictionary<long, List<float>>();
        for (int fi = 0; fi < cc.list.Count; fi++)
        {
            var fb = cc.list[fi]; var hl = hullOf[fb.go]; if (hl == null) continue;
            foreach (var p in pts)
            {
                var q = new Vector2(p.x, p.z); int b; float d; if (!cc.FaceAt(fb, q, out b, out d) || d >= 0f || EdoGeom.PIP(hl, q)) continue;
                float ed = EdgeDist(hl, q); if (ed < 0.25f || ed > 1.0f) continue;
                long k = ((long)fi << 20) | (long)b; List<float> gl; if (!gF.TryGetValue(k, out gl)) gF[k] = gl = new List<float>(); gl.Add(p.y);
            }
        }
        int n = 0, nB = 0, nHid = 0; float worst = 0f, worstB = 0f, worstV = 0f; Vector3 wAt = Vector3.zero; string wBy = "-"; var by = new Dictionary<string, int>();
        foreach (var p in pts)
        {
            var q = new Vector2(p.x, p.z); float ex = float.NaN; string who = null; bool exBuried = false;
            for (int fi = 0; fi < cc.list.Count; fi++)
            {
                var fb = cc.list[fi]; var hl = hullOf[fb.go]; int b; float d; if (hl == null || !cc.FaceAt(fb, q, out b, out d) || d >= 0f || !EdoGeom.PIP(hl, q)) continue;
                float g = float.NaN; { var gs = new List<float>(); for (int db = -2; db <= 2; db++) { List<float> gl; if (gF.TryGetValue(((long)fi << 20) | (long)(b + db), out gl)) gs.AddRange(gl); } if (gs.Count > 0) { gs.Sort(); g = gs[gs.Count / 2]; } }
                if (float.IsNaN(g)) { var tr0 = Terrain.activeTerrain; float fu0 = fb.footU[b]; if (tr0 != null && !float.IsNaN(fu0)) { var qf = q + fb.f * (fu0 - Vector2.Dot(q, fb.f) + 0.6f); g = tr0.SampleHeight(new Vector3(qf.x, 0f, qf.y)) + tr0.transform.position.y; } }
                if (!float.IsNaN(g) && p.y <= g + 0.02f) continue;   // 根入れの土
                float e = p.y - (cc.FacePlaneY(fb, b, Vector2.Dot(q, fb.f)) - 0.02f);
                // 埋めた面(提案・第71巡): 前の地表が天端から 0.36 以内の面は見え面が地上に出ていない ── 別に数える(外さずに両方刷る)
                bool buriedFace = !float.IsNaN(g) && g >= fb.crest[b] - 0.36f;
                if (e > 1e-3f && (float.IsNaN(ex) || e > ex)) { ex = e; who = fb.go.name; exBuried = buriedFace; }
            }
            if (float.IsNaN(ex)) continue;
            // 別の駒の中(第92巡): 頂点が別の野面の駒 B の外形の中で、B の見え面の平面より背(B の石の中・背の土)なら、who の見え面の前でも B に隠れる ──
            //   同じ段の入隅で可動側の駒の背の中に通す側の見え面の帯が入る所(SkinHeightSolve が見え面の上限を外した点と同じ測り)。当たる先: 野面の入隅すべて。
            bool hidByOther = false;
            for (int fi = 0; fi < cc.list.Count && !hidByOther; fi++)
            {
                var fb = cc.list[fi]; if (fb.go == null || fb.go.name == who) continue; var hl = hullOf[fb.go]; int b; float d;
                if (hl == null || !EdoGeom.PIP(hl, q) || !cc.FaceAt(fb, q, out b, out d)) continue;
                if (d >= 0f ? p.y <= fb.crest[b] : p.y <= cc.FacePlaneY(fb, b, Vector2.Dot(q, fb.f)) - 0.02f) hidByOther = true;
            }
            if (hidByOther) { nHid++; continue; }
            n++; if (exBuried) { nB++; if (ex > worstB) worstB = ex; } else if (ex > worstV) worstV = ex;
            int c0; by.TryGetValue(who, out c0); by[who] = c0 + 1; if (ex > worst) { worst = ex; wAt = p; wBy = who; }
        }
        var l = new List<KeyValuePair<string, int>>(by); l.Sort((a, b2) => b2.Value.CompareTo(a.Value)); var top = new List<string>(); for (int i = 0; i < Mathf.Min(6, l.Count); i++) top.Add(l[i].Key + " " + l[i].Value);
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        return "皮の頂点が野面の見え面の平面より前(硬 0・平面 −0.02・根入れの土を除く): " + n + " / " + pts.Count + " 頂点" + (n > 0 ? "(最悪 +" + worst.ToString("F2", ci) + " @(" + wAt.x.ToString("F1", ci) + ", " + wAt.y.ToString("F2", ci) + ", " + wAt.z.ToString("F1", ci) + ")〔" + wBy + "〕・" + string.Join("・", top.ToArray()) + ") ⛔" : " ⭕") + (n > 0 ? " ── うち埋めた面(前の地表が天端から 0.36 以内)" + nB + "(最悪 +" + worstB.ToString("F2", ci) + ")・外すと " + (n - nB) + "(最悪 +" + worstV.ToString("F2", ci) + ")" : "") + "・別の駒の中に隠れて数えない " + nHid;
    }

    /// <summary>**縁の落差 &gt; 0.3 の土の面**(硬・EDO-0502 第72巡・指図 terraces[Kadonouchi].edgeRetain 追記 2026-10-09e「縁の落差が 0.3 を超える所は全部石垣の見え面で受け、土の面を見せない」)。
    /// 面 <paramref name="region"/>(+<paramref name="buffer"/>)の中の皮の三角形のうち、高さの幅 &gt; <paramref name="drop"/> かつ 1:<paramref name="bf"/> の法より急な物(土が立たない面)を数える。
    /// 穴の縁の垂れ(平面の面積 ≒ 0)と、部材の外形(凸包)の中の三角形(部材の下・裏で見えない)は数えない。近い名のある部材(5m 以内)ごとに束ねる。
    /// ⟶ 返す: 件数・最大の高さ・束。当たる先: 縁の皮を持つ全邸(岡部 Stage3b の末に刷る)。</summary>
    public static string SkinSteepReport(Transform root, Transform skin, Vector2[] region, float buffer, float drop, float bf, string label)
    {
        var ci = System.Globalization.CultureInfo.InvariantCulture; float nyMax = 1f / Mathf.Sqrt(1f + 1f / (bf * bf));
        Func<Vector2, bool> inReg = q => EdoGeom.PIP(region, q) || EdgeDist(region, q) <= buffer;
        var parts = new List<KeyValuePair<string, Vector2[]>>(); var ctrs = new List<Vector3>();
        foreach (Transform g in root) foreach (Transform c in g)
        {
            if (!c.gameObject.activeInHierarchy || c == skin || c.IsChildOf(skin)) continue; var rr = c.GetComponentInChildren<Renderer>(); if (rr == null) continue;
            var bc = rr.bounds; if (!inReg(new Vector2(bc.center.x, bc.center.z)) && EdgeDist(region, new Vector2(bc.center.x, bc.center.z)) > buffer + 8f) continue;
            var p2 = new List<Vector2>(); foreach (var v in Body(c, 4000)) p2.Add(new Vector2(v.x, v.z)); if (p2.Count < 3) continue;
            string nm = System.Text.RegularExpressions.Regex.Replace(c.name, @"_[0-9]+f$|_kado[0-9]+$|_tome[0-9]*$", "");
            parts.Add(new KeyValuePair<string, Vector2[]>(nm, ConvexHull2(p2).ToArray())); ctrs.Add(bc.center);
        }
        int n = 0; float wMax = 0f; Vector3 wAt = Vector3.zero; var by = new Dictionary<string, int>(); var byMax = new Dictionary<string, float>(); var byAt = new Dictionary<string, Vector3>();
        foreach (var mf in skin.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue; var V = mf.sharedMesh.vertices; var T = mf.sharedMesh.triangles; var tr = mf.transform;
            for (int t = 0; t < T.Length; t += 3)
            {
                var a = tr.TransformPoint(V[T[t]]); var b = tr.TransformPoint(V[T[t + 1]]); var c = tr.TransformPoint(V[T[t + 2]]);
                float lo = Mathf.Min(a.y, Mathf.Min(b.y, c.y)), hi = Mathf.Max(a.y, Mathf.Max(b.y, c.y)); if (hi - lo <= drop) continue;
                var nrm = Vector3.Cross(b - a, c - a); float area2 = Mathf.Abs(nrm.y); if (area2 < 1e-3f) continue;   // 垂れ
                nrm.Normalize(); if (Mathf.Abs(nrm.y) >= nyMax) continue;
                var ctr = (a + b + c) / 3f; var q = new Vector2(ctr.x, ctr.z); if (!inReg(q)) continue;
                bool hid = false; foreach (var kv in parts) if (EdoGeom.PIP(kv.Value, q)) { hid = true; break; } if (hid) continue;
                n++; if (hi - lo > wMax) { wMax = hi - lo; wAt = ctr; }
                string who = "-"; float bd = 5f; for (int k = 0; k < parts.Count; k++) { float d2 = Mathf.Min(EdgeDist(parts[k].Value, q), bd); if (d2 < bd) { bd = d2; who = parts[k].Key; } }
                int c0; by.TryGetValue(who, out c0); by[who] = c0 + 1; float m0; if (!byMax.TryGetValue(who, out m0) || hi - lo > m0) { byMax[who] = hi - lo; byAt[who] = (a + b + c) / 3f; }
            }
        }
        var l = new List<KeyValuePair<string, int>>(by); l.Sort((x, y) => y.Value.CompareTo(x.Value)); var top = new List<string>();
        for (int i = 0; i < Mathf.Min(14, l.Count); i++) top.Add(l[i].Key + " " + l[i].Value + "(" + byMax[l[i].Key].ToString("F2", ci) + " @" + byAt[l[i].Key].x.ToString("F1", ci) + "," + byAt[l[i].Key].y.ToString("F2", ci) + "," + byAt[l[i].Key].z.ToString("F1", ci) + ")");
        return label + " の縁の落差 > " + drop.ToString("F1", ci) + " の土の面(皮の三角形・1:" + bf.ToString("0.0", ci) + " より急・部材の下と垂れを除く・硬 0): " + n + (n > 0 ? "(最大の高さ " + wMax.ToString("F2", ci) + " @(" + wAt.x.ToString("F1", ci) + ", " + wAt.y.ToString("F2", ci) + ", " + wAt.z.ToString("F1", ci) + ")・" + string.Join("・", top.ToArray()) + ") ⛔" : " ⭕");
    }
    /// <summary>EdgeDist の公開の窓口(ビルダーの検めから)。</summary>
    public static float EdgeDistPublic(Vector2[] poly, Vector2 p) { return EdgeDist(poly, p); }
}
