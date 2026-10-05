using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 排水(雨落ち・溝・桝・蓋石・水切り・水抜き)の置き方 ── 線を建った物から引き、底の高さを式で解き、1m の駒を並べる。
//
// 【作法】(docs/oki-kata.md・CLAUDE.md 規則2・5・21)
//   ① 線は**建った物を測って**引く: 軒先 = 屋根の実メッシュの外周(<see cref="EaveRect"/>)/ 面の縁 = 指図の面の多角形(呼び手が世界へ写す)/
//      塀・土留めの面 = 駒の実メッシュ(<see cref="WallFaceLine"/>)/ 柵の芯 = 駒の実メッシュの厚みの中(<see cref="WallMidLine"/>)。
//      ⛔ 座標を発明しない ── 引けない線は呼び手が Wait に名乗る。
//      相手の名で書いた線(N1 軒の外周・N2 相手側の軒先・N3 面の縁・N4 長屋の内の軒先・N5/N6 坂の帯・N7 門の背・N8 長屋の内面・N9 最短・N10 受け)は末尾の節。
//      段落ち(H)・張り石の落とし(I)・受け(J)も末尾の節(駒の実メッシュの段鼻・天端・縁を測って据える)。
//   ② 底の高さは**硬い条件**を式で満たす(<see cref="SolveMizoBottom"/>): 落とし先へ下がり続ける(逆勾配・窪み 0)/
//      受ける側の底 < 入る側の底(呼び手が上流の底を `caps` で渡す)/ 段落ち 1段 ≤ riseMax。
//      ⭐ 溝の底 ≤ **駒が覆う矩形の地面の最低** + topAbove − 深さ(<see cref="MizoFootGroundMin"/>)── 欄の頭の底はその上限として読み、地面より高ければ下げて名乗る。
//      据えた駒も矩形の各点で 天端 ≤ 地面 + topAbove + 0.01 を検め、破る駒は据えずに呼び手へ返す(<see cref="LayMizo"/> の hardFail)。
//      ⛔ 線の上の一点で地面を引かない ── 小段・面の縁・線の折れの外で、駒の縁と小口が下の面の上へ浮く(土井 D9 seg1・2026-10-05・EDO-0533)。
//      ⛔ 硬い条件は「最も近い所」で妥協しない ── 破れば ✗ を返し、呼び手は据えない。
//   ③ 天端を地盤 + topAbove に揃えるのは**柔らかい条件**(狙い)── 深さの決まった駒で勾配を取ると天端が沈む。沈みの最悪を ⚠ で返す。
//   ④ 駒の高さは**駒の実メッシュで測った溝の底(当たり)**を解いた底へ当てて決める(<see cref="MizoPieceOf"/>)。⛔ ピボットで決めない。
//      平面は部材方の作法(溝の芯の平面・+Z が下流)に拠る ── 札(PartSpecs)が出来たら札の芯へ替える。
//   ⑤ 走りの端は駒を切る・伸ばさない: 最後の駒は走りの端へ引き戻して前の駒へ重ねる(部材どうしの重なりは数えない ── oki-kata §4)。
//
// 【当たる先】土井 S9 排水(EdoDoiBuilder.Mizo.cs)。同じ型は溝・雨落ちを持つ邸(岡部・松江松平・山王)の排水の Stage に当たる。
public static partial class EdoBuild
{
    // ---------------------------------------------------------------- 部材の名(反射)
    /// <summary>**まだ EdoAssets に無いかもしれない部材**を名で引く(部材方が並行して足している ── DoiMizo・DoiMasu ほか)。
    /// 無ければ null(呼び手は据えずに控えへ積む)。⛔ 直に書くと登録されるまでコンパイルできない。
    /// 当たる先: 土井の排水の駒すべて。登録されたら直の参照へ替えてよい。</summary>
    public static string AssetByName(string cls, string member, params object[] args)
    {
        var bf = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static;
        var t = typeof(EdoAssets).GetNestedType(cls, System.Reflection.BindingFlags.Public);
        if (t == null) return null;
        if (args == null || args.Length == 0)
        {
            var f = t.GetField(member, bf);
            if (f != null) return f.GetValue(null) as string;
            var p = t.GetProperty(member, bf);
            if (p != null) return p.GetValue(null, null) as string;
        }
        foreach (var m in t.GetMethods(bf))
        {
            if (m.Name != member || m.ReturnType != typeof(string)) continue;
            var ps = m.GetParameters(); if (ps.Length < args.Length) continue;
            bool rest = true; for (int i = args.Length; i < ps.Length; i++) rest &= ps[i].IsOptional;   // 省いた引数は既定値で埋める(DoiMizo(kata) など)
            if (!rest) continue;
            var conv = new object[ps.Length]; bool ok = true;
            for (int i = 0; i < ps.Length && ok; i++)
            {
                if (i >= args.Length) { conv[i] = ps[i].DefaultValue; continue; }
                try { conv[i] = Convert.ChangeType(args[i], ps[i].ParameterType, System.Globalization.CultureInfo.InvariantCulture); }
                catch (Exception) { ok = false; }
            }
            if (!ok) continue;
            try { return m.Invoke(null, conv) as string; } catch (Exception) { return null; }
        }
        return null;
    }

    // ---------------------------------------------------------------- 駒の実測
    /// <summary>溝・桝・蓋の駒の**局所の実測**(倍率の前・Y 回転 0)。top = 天端(最上点)/ floor = 溝の底(芯の帯 |x| ≤ 0.12 の最下点)/
    /// bottom = 駒の最下点 / halfW = 幅の半分(x)/ len = 長さ(z)/ zMin・zMax = 長さの端。</summary>
    public class MizoPiece { public bool ok; public float top, floor, bottom, halfW, len, zMin, zMax, xMin, xMax; public float Depth { get { return top - floor; } } }
    static readonly Dictionary<string, MizoPiece> _mizoPieceCache = new Dictionary<string, MizoPiece>();
    /// <summary>駒の実メッシュを一度だけ測る(当たり = 溝の底・天端・幅)。⛔ ピボットの高さを溝の底と見なさない。
    /// 当たる先: 溝(DoiMizo)・桝(DoiMasu)・蓋石(DoiFutaishi)・水切り(DoiMizukiri)・水抜き(DoiMizunuki)。</summary>
    public static MizoPiece MizoPieceOf(string path)
    {
        MizoPiece got;
        if (string.IsNullOrEmpty(path)) return new MizoPiece();
        if (_mizoPieceCache.TryGetValue(path, out got)) return got;
        var r = new MizoPiece();
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (pf != null)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
            go.transform.position = Vector3.zero; go.transform.rotation = Quaternion.identity; go.transform.localScale = Vector3.one;
            try
            {
                var pts = new List<Vector3>();
                foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
                {
                    if (mf.sharedMesh == null) continue;
                    var m = mf.transform.localToWorldMatrix; foreach (var v in mf.sharedMesh.vertices) pts.Add(m.MultiplyPoint3x4(v));
                }
                if (pts.Count > 0)
                {
                    r.top = float.MinValue; r.bottom = float.MaxValue; r.xMin = r.zMin = float.MaxValue; r.xMax = r.zMax = float.MinValue;
                    foreach (var p in pts)
                    {
                        r.top = Mathf.Max(r.top, p.y); r.bottom = Mathf.Min(r.bottom, p.y);
                        r.xMin = Mathf.Min(r.xMin, p.x); r.xMax = Mathf.Max(r.xMax, p.x); r.zMin = Mathf.Min(r.zMin, p.z); r.zMax = Mathf.Max(r.zMax, p.z);
                    }
                    float fl = float.MaxValue; float band = Mathf.Min(0.12f, 0.25f * (r.xMax - r.xMin));
                    foreach (var p in pts) if (Mathf.Abs(p.x) <= band) fl = Mathf.Min(fl, p.y);
                    // 溝の底は芯の帯の上向きの面 ── 帯の最下点が駒の最下点と同じなら(底石の下面)、帯で上向きの面の最下を採る
                    float upFloor = float.MaxValue;
                    foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
                    {
                        if (mf.sharedMesh == null) continue;
                        var m = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices; var tri = mf.sharedMesh.triangles;
                        for (int i = 0; i + 2 < tri.Length; i += 3)
                        {
                            Vector3 a = m.MultiplyPoint3x4(vs[tri[i]]), b = m.MultiplyPoint3x4(vs[tri[i + 1]]), c = m.MultiplyPoint3x4(vs[tri[i + 2]]);
                            var nv = Vector3.Cross(b - a, c - a); float mag = nv.magnitude; if (mag < 1e-9f || nv.y / mag < 0.7f) continue;
                            var cc = (a + b + c) / 3f; if (Mathf.Abs(cc.x) > band) continue;
                            upFloor = Mathf.Min(upFloor, cc.y);
                        }
                    }
                    r.floor = upFloor < float.MaxValue ? upFloor : fl;
                    r.halfW = 0.5f * (r.xMax - r.xMin); r.len = r.zMax - r.zMin;
                    r.ok = r.floor < float.MaxValue && r.len > 1e-3f;
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
        }
        _mizoPieceCache[path] = r;
        return r;
    }

    // ---------------------------------------------------------------- 線: 軒先
    /// <summary>**軒先の外周** = 屋根の実メッシュの、棟の軸 <paramref name="ax"/> と直交軸での外形の矩形(世界 XZ・反時計回り)。
    /// 屋根の見分けはメッシュ名・材の名(<see cref="IsRoofLabel"/>)。屋根と名乗るメッシュが無い一体の駒は、
    /// 丈の上半分(屋根が載る所)の頂点の外形で代える(how に名乗る)。<paramref name="eaveY"/> = 屋根の最下点(軒先の下端)。
    /// 当たる先: 雨落ち(A・B・C)の線すべて ── 御殿(EdoGotenKit の棟)・附属屋(一体の駒)。</summary>
    public static bool EaveRect(Transform bld, Vector2 ax, out Vector2[] rect, out float eaveY, out string how)
    {
        rect = null; eaveY = float.NaN; how = "";
        if (bld == null) { how = "棟が無い"; return false; }
        ax = ax.normalized; var ay = new Vector2(-ax.y, ax.x);
        var roof = new List<Vector3>(); var all = new List<Vector3>();
        foreach (var mf in bld.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null || !mf.gameObject.activeInHierarchy) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            var m = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices;
            bool meshRoof = IsRoofLabel(mf.gameObject.name) || IsRoofLabel(mf.sharedMesh.name);
            var mats = rr.sharedMaterials;
            if (meshRoof) foreach (var v in vs) roof.Add(m.MultiplyPoint3x4(v));
            else
            {
                for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
                {
                    string mat = s < mats.Length && mats[s] != null ? mats[s].name : "";
                    if (!IsRoofLabel(mat)) continue;
                    foreach (int i in mf.sharedMesh.GetTriangles(s)) roof.Add(m.MultiplyPoint3x4(vs[i]));
                }
            }
            foreach (var v in vs) all.Add(m.MultiplyPoint3x4(v));
        }
        var use = roof;
        if (use.Count == 0)
        {
            if (all.Count == 0) { how = "メッシュが無い"; return false; }
            float y0 = float.MaxValue, y1 = float.MinValue; foreach (var p in all) { y0 = Mathf.Min(y0, p.y); y1 = Mathf.Max(y1, p.y); }
            float mid = 0.5f * (y0 + y1); use = new List<Vector3>(); foreach (var p in all) if (p.y >= mid) use.Add(p);
            how = "屋根と名乗るメッシュが無い ── 丈の上半分の外形で代えた";
        }
        else how = "屋根の実メッシュ";
        float a0 = float.MaxValue, a1 = float.MinValue, b0 = float.MaxValue, b1 = float.MinValue; eaveY = float.MaxValue;
        foreach (var p in use)
        {
            var q = new Vector2(p.x, p.z); float sa = Vector2.Dot(q, ax), sb = Vector2.Dot(q, ay);
            a0 = Mathf.Min(a0, sa); a1 = Mathf.Max(a1, sa); b0 = Mathf.Min(b0, sb); b1 = Mathf.Max(b1, sb); eaveY = Mathf.Min(eaveY, p.y);
        }
        rect = new[] { ax * a0 + ay * b0, ax * a1 + ay * b0, ax * a1 + ay * b1, ax * a0 + ay * b1 };
        return true;
    }

    /// <summary>多角形(反時計回りでも時計回りでも)の辺のうち、外向きの法線が <paramref name="dir"/> と <paramref name="minDot"/> 以上で向く辺を、
    /// 続いている所で一本につないだ鎖の列。当たる先: 軒先の片側・面の縁の片側。</summary>
    public static List<List<Vector2>> PolyEdgesToward(Vector2[] poly, Vector2 dir, float minDot)
    {
        var res = new List<List<Vector2>>(); int n = poly.Length; if (n < 3) return res;
        dir = dir.normalized;
        var sel = new bool[n];
        for (int i = 0; i < n; i++) sel[i] = Vector2.Dot(-EdoGeom.InwardNormal(poly, i), dir) >= minDot;
        int start = -1; for (int i = 0; i < n; i++) if (!sel[i]) { start = i; break; }
        if (start < 0) { var all = new List<Vector2>(poly); all.Add(poly[0]); res.Add(all); return res; }
        List<Vector2> cur = null;
        for (int k = 1; k <= n; k++)
        {
            int i = (start + k) % n;
            if (sel[i]) { if (cur == null) { cur = new List<Vector2> { poly[i] }; res.Add(cur); } cur.Add(poly[(i + 1) % n]); }
            else cur = null;
        }
        return res;
    }

    /// <summary>矩形(<see cref="EaveRect"/>)の 4 辺のうち外向きの法線が <paramref name="dir"/> にいちばん近い 1 辺(2 点)。
    /// 近さ(cos)を <paramref name="dot"/> に返す ── 呼び手は 0.7 未満を「向きが決まらない」として退ける。</summary>
    public static List<Vector2> RectSideToward(Vector2[] rect, Vector2 dir, out float dot)
    {
        dir = dir.normalized; int best = -1; dot = -2f;
        for (int i = 0; i < 4; i++) { float d = Vector2.Dot(-EdoGeom.InwardNormal(rect, i), dir); if (d > dot) { dot = d; best = i; } }
        return new List<Vector2> { rect[best], rect[(best + 1) % 4] };
    }

    /// <summary>**「棟 X の <相手>側」の辺**を選ぶ。矩形(軒先の外周)の 4 辺それぞれについて、辺の外の半平面に入る相手の多角形の広さ(1m の標本の数)を数え、
    /// 辺の外 3m の帯が他の棟(<paramref name="blockers"/>)に塞がれている辺は外す(坪の向かいの棟の側を「泉水側」と取らない)。
    /// いちばん広い辺が次の辺の 1.3 倍に満たなければ「向きが決まらない」で null(呼び手は Wait)。当たる先: 雨落ちの片側の線(D1・D3)。</summary>
    public static List<Vector2> SideFacing(Vector2[] rect, Vector2[] target, IList<Vector2[]> blockers, out string why)
    {
        why = null;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in target) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        var pts = new List<Vector2>();
        for (float x = mnx + 0.5f; x < mxx; x += 1f) for (float z = mnz + 0.5f; z < mxz; z += 1f) { var q = new Vector2(x, z); if (EdoGeom.PIP(target, q)) pts.Add(q); }
        if (pts.Count == 0) { why = "相手の多角形が空"; return null; }
        var score = new int[4]; var blocked = new bool[4];
        for (int i = 0; i < 4; i++)
        {
            Vector2 a = rect[i], b = rect[(i + 1) % 4], n = -EdoGeom.InwardNormal(rect, i);
            foreach (var q in pts) if (Vector2.Dot(q - a, n) > 0f) score[i]++;
            if (blockers != null)
            {
                foreach (var bl in blockers)
                {
                    if (bl == null) continue;
                    bool hit = false;
                    // 辺の両端 15% は数えない(隣の棟の軒の隅が掛かるだけの辺を塞がれたと取らない)
                    for (int k = 0; k <= 8 && !hit; k++) { var q = Vector2.Lerp(a, b, 0.15f + 0.7f * k / 8f) + n * 1.5f; if (EdoGeom.PIP(bl, q)) hit = true; }
                    var sa = Vector2.Lerp(a, b, 0.15f); var sb2 = Vector2.Lerp(a, b, 0.85f); var strip2 = new[] { sa, sb2, sb2 + n * 3f, sa + n * 3f };
                    foreach (var c in bl) if (!hit && EdoGeom.PIP(strip2, c)) hit = true;
                    if (hit) { blocked[i] = true; break; }
                }
            }
            if (blocked[i]) score[i] = -1;
        }
        int b1 = -1, b2 = -1;
        for (int i = 0; i < 4; i++) { if (b1 < 0 || score[i] > score[b1]) { b2 = b1; b1 = i; } else if (b2 < 0 || score[i] > score[b2]) b2 = i; }
        if (score[b1] <= 0) { why = "どの辺の外にも相手が無い(塞がれた辺を外した後)"; return null; }
        if (b2 >= 0 && score[b2] > 0 && score[b1] < 1.3f * score[b2]) { why = "二辺が拮抗(" + score[b1] + " / " + score[b2] + ")── 向きが決まらない"; return null; }
        return new List<Vector2> { rect[b1], rect[(b1 + 1) % 4] };
    }

    /// <summary>二つの矩形の向き合う辺の**中心線**(向き合う辺どうしの重なる区間だけ)。
    /// <paramref name="gap"/> = 向き合う辺どうしの離れ(負 = 軒が重なる)。当たる先: 坪・棟間の路地の溝(D1 seg3・D4 seg1)。</summary>
    public static List<Vector2> MidlineBetween(Vector2[] ra, Vector2[] rb, out float gap)
    {
        gap = float.NaN;
        Vector2 ca = (ra[0] + ra[2]) * 0.5f, cb = (rb[0] + rb[2]) * 0.5f;
        float da, db;
        var ea = RectSideToward(ra, cb - ca, out da); var eb = RectSideToward(rb, ca - cb, out db);
        if (da < 0.7f || db < 0.7f) return null;
        Vector2 t = (ea[1] - ea[0]).normalized; Vector2 n = -EdoGeom.InwardNormal(ra, IndexOfEdge(ra, ea[0]));
        float a0 = Mathf.Min(Vector2.Dot(ea[0], t), Vector2.Dot(ea[1], t)), a1 = Mathf.Max(Vector2.Dot(ea[0], t), Vector2.Dot(ea[1], t));
        float b0 = Mathf.Min(Vector2.Dot(eb[0], t), Vector2.Dot(eb[1], t)), b1 = Mathf.Max(Vector2.Dot(eb[0], t), Vector2.Dot(eb[1], t));
        float s0 = Mathf.Max(a0, b0), s1 = Mathf.Min(a1, b1); if (s1 - s0 < 0.3f) return null;
        float na = Vector2.Dot(ea[0], n), nb = Vector2.Dot(eb[0], n); gap = nb - na; float nm = 0.5f * (na + nb);
        return new List<Vector2> { t * s0 + n * nm, t * s1 + n * nm };
    }
    static int IndexOfEdge(Vector2[] poly, Vector2 a)
    { for (int i = 0; i < poly.Length; i++) if ((poly[i] - a).sqrMagnitude < 1e-8f) return i; return 0; }

    /// <summary>折れ線を <paramref name="d"/> だけ横へずらす。向きは各区間の左法線 × 符号で、符号は最初の区間で <paramref name="toward"/> の側。
    /// 角は隣の区間のずらした線の交点で継ぐ。</summary>
    public static List<Vector2> OffsetPolyline(List<Vector2> pl, float d, Vector2 toward)
    {
        if (pl == null || pl.Count < 2) return pl;
        Vector2 t0 = (pl[1] - pl[0]).normalized, l0 = new Vector2(-t0.y, t0.x);
        float sg = Vector2.Dot(l0, toward) >= 0f ? 1f : -1f;
        var segs = new List<Vector2[]>();
        for (int i = 0; i + 1 < pl.Count; i++)
        {
            var t = (pl[i + 1] - pl[i]); if (t.sqrMagnitude < 1e-8f) continue; t.Normalize();
            var o = new Vector2(-t.y, t.x) * (sg * d); segs.Add(new[] { pl[i] + o, pl[i + 1] + o });
        }
        var res = new List<Vector2> { segs[0][0] };
        for (int i = 0; i + 1 < segs.Count; i++)
            res.Add(EdoGeom.LineIntersect(segs[i][0], segs[i][1] - segs[i][0], segs[i + 1][0], segs[i + 1][1] - segs[i + 1][0], segs[i][1]));
        res.Add(segs[segs.Count - 1][1]);
        return res;
    }

    public static float PolylineLength(List<Vector2> pl)
    { float L = 0f; for (int i = 0; i + 1 < pl.Count; i++) L += Vector2.Distance(pl[i], pl[i + 1]); return L; }
    public static Vector2 PointAt(List<Vector2> pl, float s, out Vector2 dir)
    {
        dir = Vector2.right;
        for (int i = 0; i + 1 < pl.Count; i++)
        {
            float l = Vector2.Distance(pl[i], pl[i + 1]); if (l < 1e-6f) continue;
            dir = (pl[i + 1] - pl[i]) / l;
            if (s <= l || i + 2 == pl.Count) return pl[i] + dir * Mathf.Min(s, l);
            s -= l;
        }
        return pl[pl.Count - 1];
    }
    /// <summary>折れ線の上で点に最も近い所の弧長と距離。</summary>
    public static float NearestS(List<Vector2> pl, Vector2 p, out float dist)
    {
        float best = float.MaxValue, bs = 0f, acc = 0f;
        for (int i = 0; i + 1 < pl.Count; i++)
        {
            Vector2 a = pl[i], b = pl[i + 1]; float l = Vector2.Distance(a, b); if (l < 1e-6f) continue;
            float t = Mathf.Clamp(Vector2.Dot(p - a, b - a) / (l * l), 0f, 1f); float d = Vector2.Distance(p, a + (b - a) * t);
            if (d < best) { best = d; bs = acc + t * l; }
            acc += l;
        }
        dist = best; return bs;
    }
    /// <summary>二つの折れ線の交点(最初の一つ)。無ければ false。当たる先: 蓋石(溝が路・園路を横切る所)。</summary>
    public static bool PolylineCross(List<Vector2> a, List<Vector2> b, out Vector2 at, out float sA)
    {
        at = Vector2.zero; sA = 0f; float acc = 0f;
        for (int i = 0; i + 1 < a.Count; i++)
        {
            Vector2 p = a[i], r = a[i + 1] - a[i]; float lr = r.magnitude;
            for (int j = 0; j + 1 < b.Count; j++)
            {
                Vector2 q = b[j], s = b[j + 1] - b[j];
                float den = r.x * s.y - r.y * s.x; if (Mathf.Abs(den) < 1e-9f) continue;
                Vector2 qp = q - p; float t = (qp.x * s.y - qp.y * s.x) / den, u = (qp.x * r.y - qp.y * r.x) / den;
                if (t >= 0f && t <= 1f && u >= 0f && u <= 1f) { at = p + r * t; sA = acc + t * lr; return true; }
            }
            acc += lr;
        }
        return false;
    }

    // ---------------------------------------------------------------- 線: 塀・土留め・柵の実メッシュ
    /// <summary>駒の列(一本の走り)の**面の線**を実メッシュから採る。走りの向き = 頂点の主軸、面 = <paramref name="towardPoint"/> の側。
    /// 高さの帯は駒の列の最下点からの [yLo, yHi]。走りに沿って <paramref name="step"/> ごとに、帯の中で面の側へいちばん出た頂点を拾って線にする。
    /// <paramref name="normal"/> = 面の外向き(towardPoint の側)。当たる先: 塀の内面(D3 seg2)・土留めの根石の前面と天端の背(D2・D6・D9)。</summary>
    public static List<Vector2> WallFaceLine(IList<GameObject> pieces, Vector2 towardPoint, float yLo, float yHi, float step, out Vector2 normal, out string why, bool fromTop = false)
    {
        normal = Vector2.zero; why = null;
        // 帯は**駒ごと**: fromTop = false なら駒の最下点から [yLo, yHi]、true なら駒の最上点から [yLo, yHi](負で下へ)── 斜面の走りでも帯がずれない
        var P = new List<Vector3>(); var inBand = new List<bool>();
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            var B = Body(g.transform, 999999, false); if (B.Count == 0) continue;
            float lo = float.MaxValue, hi = float.MinValue; foreach (var p in B) { lo = Mathf.Min(lo, p.y); hi = Mathf.Max(hi, p.y); }
            float b0 = fromTop ? hi + yLo : lo + yLo, b1 = fromTop ? hi + yHi : lo + yHi;
            foreach (var p in B) { P.Add(p); inBand.Add(p.y >= b0 && p.y <= b1); }
        }
        if (P.Count < 8) { why = "駒の実メッシュが無い"; return null; }
        Vector2 t, c; PrincipalAxis(P, out c, out t);
        var n = new Vector2(-t.y, t.x); if (Vector2.Dot(towardPoint - c, n) < 0f) n = -n; normal = n;
        float s0 = float.MaxValue, s1 = float.MinValue;
        foreach (var p in P) { float s = Vector2.Dot(new Vector2(p.x, p.z) - c, t); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); }
        int nb = Mathf.Max(1, Mathf.CeilToInt((s1 - s0) / step));
        var best = new float[nb]; for (int i = 0; i < nb; i++) best[i] = float.MinValue;
        for (int k = 0; k < P.Count; k++)
        {
            if (!inBand[k]) continue; var p = P[k];
            var q = new Vector2(p.x, p.z) - c; int b = Mathf.Clamp((int)((Vector2.Dot(q, t) - s0) / step), 0, nb - 1);
            best[b] = Mathf.Max(best[b], Vector2.Dot(q, n));
        }
        var line = new List<Vector2>();
        for (int i = 0; i < nb; i++) if (best[i] > float.MinValue) line.Add(c + t * (s0 + (i + 0.5f) * step) + n * best[i]);
        if (line.Count < 2) { why = "帯の中に面の頂点が無い"; return null; }
        // 端は走りの端まで延ばす(最初・最後の区間の中点から端へ)
        line[0] = c + t * s0 + n * Vector2.Dot(line[0] - c, n);
        line[line.Count - 1] = c + t * s1 + n * Vector2.Dot(line[line.Count - 1] - c, n);
        return line;
    }

    /// <summary>駒の列の**厚みの芯の線**(帯の中の両面の中央)。当たる先: 柵の柱の芯(D5 の埒 F04)。</summary>
    public static List<Vector2> WallMidLine(IList<GameObject> pieces, float yLo, float yHi, out Vector2 axis, out string why)
    {
        axis = Vector2.zero; why = null;
        var P = new List<Vector3>(); float y0 = float.MaxValue;
        foreach (var g in pieces) { if (g == null || !g.activeInHierarchy) continue; foreach (var p in Body(g.transform, 999999, false)) { P.Add(p); y0 = Mathf.Min(y0, p.y); } }
        if (P.Count < 8) { why = "駒の実メッシュが無い"; return null; }
        Vector2 t, c; PrincipalAxis(P, out c, out t); axis = t; var n = new Vector2(-t.y, t.x);
        float s0 = float.MaxValue, s1 = float.MinValue, lo = float.MaxValue, hi = float.MinValue;
        foreach (var p in P)
        {
            if (p.y < y0 + yLo || p.y > y0 + yHi) continue;
            var q = new Vector2(p.x, p.z) - c; float s = Vector2.Dot(q, t), m = Vector2.Dot(q, n);
            s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); lo = Mathf.Min(lo, m); hi = Mathf.Max(hi, m);
        }
        if (s1 <= s0) { why = "帯の中に頂点が無い"; return null; }
        float mid = 0.5f * (lo + hi);
        return new List<Vector2> { c + t * s0 + n * mid, c + t * s1 + n * mid };
    }

    static void PrincipalAxis(List<Vector3> P, out Vector2 c, out Vector2 t)
    {
        double sx = 0, sz = 0; foreach (var p in P) { sx += p.x; sz += p.z; }
        c = new Vector2((float)(sx / P.Count), (float)(sz / P.Count));
        double xx = 0, xz = 0, zz = 0;
        foreach (var p in P) { double dx = p.x - c.x, dz = p.z - c.y; xx += dx * dx; xz += dx * dz; zz += dz * dz; }
        double ang = 0.5 * Math.Atan2(2 * xz, xx - zz);
        t = new Vector2((float)Math.Cos(ang), (float)Math.Sin(ang));
    }

    // ---------------------------------------------------------------- 底の高さ(硬い条件)
    /// <summary>溝一本の設計。line は**上流 → 下流**。</summary>
    public class MizoSpec
    {
        public string name, kata;
        public List<Vector2> line;
        public Func<float, float, float> groundAt;
        /// <summary>天端の狙い = 地盤 + topAbove(柔)。</summary>
        public float topAbove;
        /// <summary>深さの決まった駒の深さ(実測)。NaN なら深さは駒を選んで合わせる(E・F)。</summary>
        public float pieceDepth = float.NaN;
        public float depthMin, depthMax;
        /// <summary>底の勾配の下限(硬 ── 下がり続ける)。0 のときは 0.001 で下がり続けさせる。</summary>
        public float slopeMin;
        /// <summary>頭の底(欄 bottom / bottomHead・硬)。NaN なら天端の狙いから引く。</summary>
        public float headBottom = float.NaN;
        /// <summary>尻の底の上限(欄 bottomTail / 落とし先の底・硬)。</summary>
        public float tailMax = float.NaN;
        /// <summary>段に落とす間隔[m](0 = 段にしない)と 1段の上限(硬)。</summary>
        public float stepPitch, stepRiseMax;
        /// <summary>上流から入る溝の底(弧長 s で底 ≤ 値 − drop)。硬い条件「受ける側の底 &lt; 入る側の底」。</summary>
        public List<Vector3> caps = new List<Vector3>();   // (s, 入る底, 落ちの最小)
        /// <summary>駒の幅の半分[m](実測)。0 なら線の上だけで地面を引く。⭐ 硬「溝の底 ≤ そこの地面 + topAbove − 深さ」の「そこ」は駒が覆う矩形の全体(EDO-0533)。</summary>
        public float halfW;
        /// <summary>駒の長さ[m](<see cref="LayMizo"/> の駒割りと同じ)。</summary>
        public float pieceLen = 1f;
        /// <summary>⭐ 駒を**弦**に据える(土井が渡す・2026-10-05 EDO-0533 第11巡の直し)── 駒 [s0, s1] を線の上の二点 P(s0)・P(s1) を結ぶ弦に置き、
        /// 線の頭の駒は頭の小口を P(0) へ、尻の駒は尻の小口を P(L) へ当てる。⛔ false(既定)は従来どおり弧長の中ほど P((s0+s1)/2) の向きに真っ直ぐ据える ──
        /// 折れの手前に中ほどが来る駒は折れの先へ真っ直ぐ伸び、桝の面へ 45° で入る短い脚(D1 seg2・seg4)では尻の駒が桝の窪みの上へ 0.33〜0.53 張り出して浮いた。
        /// 当たる先: <see cref="SolveMizoBottom"/>(駒の矩形の地面)・<see cref="LayMizo"/>(据え)。</summary>
        public bool chord;
    }
    public class MizoProfile
    {
        public bool ok = true; public string hard = "";
        public float[] s, ground, bottom; public Vector2[] p; public float length;
        public float worstSink, worstDeep, worstShallow; public float worstRise; public int steps;
        /// <summary>駒 q が覆う矩形の地面の最低(<see cref="MizoPieceSpans"/> の駒割り)。<see cref="LayMizo"/> が深さを選ぶのに使う。</summary>
        public float[] pieceGround;
        public float halfW, pieceLen = 1f, topAbove;
        /// <summary><see cref="MizoSpec.chord"/> の写し(<see cref="LayMizo"/> が読む)。</summary>
        public bool chord;
        /// <summary>欄の頭の底を硬い条件(地面 − 深さ)で下げた量[m](0 = 欄のまま)。</summary>
        public float headLowered;
        public float Head { get { return bottom[0]; } }
        public float Tail { get { return bottom[bottom.Length - 1]; } }
        public float At(float ss)
        {
            if (ss <= s[0]) return bottom[0];
            for (int i = 1; i < s.Length; i++) if (ss <= s[i]) { float t = (ss - s[i - 1]) / Mathf.Max(1e-6f, s[i] - s[i - 1]); return Mathf.Lerp(bottom[i - 1], bottom[i], t); }
            return bottom[bottom.Length - 1];
        }
    }
    /// <summary>駒割り(<see cref="LayMizo"/> と同じ): 駒 q は弧長 [s0, s1](最後の駒は走りの端へ引き戻して前の駒へ重ねる)。</summary>
    public static List<Vector2> MizoPieceSpans(float L, float pieceLen = 1f)
    {
        var res = new List<Vector2>(); if (L < 0.2f) return res;
        float pl = Mathf.Max(0.1f, pieceLen);
        int k = Mathf.Max(1, Mathf.CeilToInt(L / pl - 1e-3f));
        for (int q = 0; q < k; q++) { float s0 = Mathf.Min(q * pl, Mathf.Max(0f, L - pl)); res.Add(new Vector2(s0, Mathf.Min(L, s0 + pl))); }
        return res;
    }

    /// <summary>**駒が覆う矩形の地面の最低**。矩形 = 弧長 [s0, s1] の中ほどの点を芯に、その点の向きへ長さ (s1 − s0)・幅 2 × halfW
    /// (<see cref="LayMizo"/> の据え方と同じ ── 駒は線の折れに沿わず弦に真っ直ぐ据わるので、折れの外へ小口の隅が出る)。
    /// 縦 5 × 横 3 の点で引く。引けない点は飛ばし、全部引けなければ NaN。
    /// ⭐ 線の上の一点で地面を引くと、格子(1m)より細い小段の上では塀の天端の升を拾って高く読み、駒の縁と小口が下の平場へ浮く(土井 D9 seg1 ── EDO-0533)。
    /// 当たる先: 溝の全系統(<see cref="SolveMizoBottom"/>・<see cref="LayMizo"/>)。</summary>
    public static float MizoFootGroundMin(List<Vector2> line, float s0, float s1, float halfW, Func<float, float, float> groundAt, bool chord = false)
    {
        float sc = 0.5f * (s0 + s1), half = 0.5f * (s1 - s0); Vector2 d; var c = PointAt(line, sc, out d);
        if (chord) { Vector2 dd; var p0 = PointAt(line, s0, out dd); var p1 = PointAt(line, s1, out dd); if ((p1 - p0).sqrMagnitude > 1e-6f) { c = 0.5f * (p0 + p1); d = p1 - p0; } }   // 弦の駒(MizoSpec.chord)
        if (d.sqrMagnitude < 1e-8f) d = Vector2.up; d.Normalize(); var nrm = new Vector2(-d.y, d.x);
        float g = float.MaxValue;
        for (int a = -2; a <= 2; a++)
            for (int b = -1; b <= 1; b++)
            {
                var q = c + d * (half * a / 2f) + nrm * (halfW * b);
                float y = groundAt(q.x, q.y); if (!float.IsNaN(y)) g = Mathf.Min(g, y);
            }
        return g == float.MaxValue ? float.NaN : g;
    }

    /// <summary>**溝の底を解く**(硬い条件を式で満たす)。各点の底の候補 = **駒が覆う矩形の地面の最低** + topAbove − 深さ(深さの決まった駒はその深さ・
    /// 選べる駒は depthMin)。⭐ 硬: 「溝の底 ≤ そこの地面 + topAbove − 深さ」── 「そこ」はその点を覆う駒(前後の駒も ── 弧長 ds の内で掛かる駒)の矩形の全体。
    /// 上流から `底[i] = min(候補[i], 底[i−1] − slopeMin × ds, 入る溝の底 − 落ち)` で下ろし、尻を tailMax 以下へ抑える。欄の頭の底(headBottom)は**上限**として読み、
    /// 候補より高ければ候補へ下げて <see cref="MizoProfile.headLowered"/> に名乗る(⛔ 欄の底のまま駒を地面の上へ浮かせない)。
    /// 段に落とす溝(stepPitch &gt; 0)は区間ごとに最も低い底で平らにし、段の落ちが stepRiseMax を超えたら ✗(硬)。
    /// 返り値の worstSink = 天端の狙い(線の上の地盤 + topAbove)からの沈みの最悪(柔 ⚠)・worstDeep = depthMax を超えた最悪(柔 ⚠ ── D は E へ替える区間)。
    /// 当たる先: 溝の全系統(D1〜D13 の segs)── 今は土井 S9 だけが呼ぶ。</summary>
    public static MizoProfile SolveMizoBottom(MizoSpec sp, float ds = 0.5f)
    {
        var pr = new MizoProfile();
        float L = PolylineLength(sp.line); pr.length = L;
        pr.halfW = Mathf.Max(0f, sp.halfW); pr.pieceLen = Mathf.Max(0.1f, sp.pieceLen); pr.topAbove = sp.topAbove; pr.chord = sp.chord;
        int n = Mathf.Max(2, Mathf.CeilToInt(L / ds) + 1);
        pr.s = new float[n]; pr.ground = new float[n]; pr.bottom = new float[n]; pr.p = new Vector2[n];
        float slope = Mathf.Max(sp.slopeMin, 0.001f);
        bool fixedDepth = !float.IsNaN(sp.pieceDepth);
        for (int i = 0; i < n; i++)
        {
            float s = L * i / (n - 1); Vector2 d; var q = PointAt(sp.line, s, out d);
            pr.s[i] = s; pr.p[i] = q; pr.ground[i] = sp.groundAt(q.x, q.y);
            if (float.IsNaN(pr.ground[i])) { pr.ok = false; pr.hard += "地盤が引けない点 @" + s.ToString("F1") + "m・"; pr.ground[i] = i > 0 ? pr.ground[i - 1] : 0f; }
        }
        // 駒ごとの矩形の地面の最低 → 点ごとの地面(その点を弧長 ds の内で覆う駒すべての最低)
        var spans = MizoPieceSpans(L, pr.pieceLen);
        pr.pieceGround = new float[spans.Count];
        for (int q = 0; q < spans.Count; q++)
        {
            float g = MizoFootGroundMin(sp.line, spans[q].x, spans[q].y, pr.halfW, sp.groundAt, sp.chord);
            pr.pieceGround[q] = float.IsNaN(g) ? float.MaxValue : g;
        }
        var foot = new float[n];
        for (int i = 0; i < n; i++)
        {
            float g = pr.ground[i];
            for (int q = 0; q < spans.Count; q++)
                if (pr.s[i] >= spans[q].x - ds - 1e-4f && pr.s[i] <= spans[q].y + ds + 1e-4f) g = Mathf.Min(g, pr.pieceGround[q]);
            foot[i] = g;
        }
        for (int q = 0; q < spans.Count; q++) if (pr.pieceGround[q] == float.MaxValue) pr.pieceGround[q] = float.NaN;
        for (int i = 0; i < n; i++)
        {
            float cand = foot[i] + sp.topAbove - (fixedDepth ? sp.pieceDepth : sp.depthMin);
            foreach (var c in sp.caps) if (Mathf.Abs(c.x - pr.s[i]) <= ds * 0.5f + 1e-4f) cand = Mathf.Min(cand, c.y - Mathf.Max(0.001f, c.z));
            if (i == 0)
            {
                if (float.IsNaN(sp.headBottom)) pr.bottom[0] = cand;
                else { pr.bottom[0] = Mathf.Min(sp.headBottom, cand); pr.headLowered = Mathf.Max(0f, sp.headBottom - cand); }
            }
            else pr.bottom[i] = Mathf.Min(cand, pr.bottom[i - 1] - slope * (pr.s[i] - pr.s[i - 1]));
        }
        if (!float.IsNaN(sp.tailMax) && pr.bottom[n - 1] > sp.tailMax)
        {
            // 尻を抑える: 足りない落ちを弧長に比例して全長へ割り振る(頭は動かさない・下がり続けるのは保つ ── 尻の一点で段を作らない)
            float lack = pr.bottom[n - 1] - sp.tailMax;
            for (int i = 1; i < n; i++) pr.bottom[i] -= lack * pr.s[i] / Mathf.Max(1e-6f, L);
        }
        if (sp.stepPitch > 0.01f)
        {
            int bins = Mathf.Max(1, Mathf.CeilToInt(L / sp.stepPitch)); var lv = new float[bins];
            for (int b = 0; b < bins; b++) lv[b] = float.MaxValue;
            for (int i = 0; i < n; i++) { int b = Mathf.Min(bins - 1, (int)(pr.s[i] / sp.stepPitch)); lv[b] = Mathf.Min(lv[b], pr.bottom[i]); }
            for (int b = 1; b < bins; b++) lv[b] = Mathf.Min(lv[b], lv[b - 1]);
            for (int i = 0; i < n; i++) pr.bottom[i] = lv[Mathf.Min(bins - 1, (int)(pr.s[i] / sp.stepPitch))];
            pr.steps = bins;
            for (int b = 1; b < bins; b++) pr.worstRise = Mathf.Max(pr.worstRise, lv[b - 1] - lv[b]);
            if (sp.stepRiseMax > 0f && pr.worstRise > sp.stepRiseMax + 1e-4f)
            { pr.ok = false; pr.hard += "段の 1段 " + pr.worstRise.ToString("F3") + " > 上限 " + sp.stepRiseMax.ToString("F2") + "(間隔 " + sp.stepPitch.ToString("F3") + "m)・"; }
        }
        // 硬: 逆勾配・窪み 0
        for (int i = 1; i < n; i++)
            if (pr.bottom[i] > pr.bottom[i - 1] + 1e-5f) { pr.ok = false; pr.hard += "逆勾配 @" + pr.s[i].ToString("F1") + "m・"; break; }
        if (pr.bottom[n - 1] >= pr.bottom[0] - 1e-5f) { pr.ok = false; pr.hard += "尻が頭より下がらない・"; }
        for (int i = 0; i < n; i++)
        {
            float topWant = pr.ground[i] + sp.topAbove;
            float depth = topWant - pr.bottom[i];
            if (fixedDepth) pr.worstSink = Mathf.Max(pr.worstSink, topWant - (pr.bottom[i] + sp.pieceDepth));
            else
            {
                pr.worstDeep = Mathf.Max(pr.worstDeep, depth - sp.depthMax);
                pr.worstShallow = Mathf.Max(pr.worstShallow, sp.depthMin - depth);
            }
        }
        return pr;
    }

    // ---------------------------------------------------------------- 駒を並べる
    /// <summary>**1m の駒を線に並べる**。駒ごとに: 平面 = 線の上(部材の作法: 溝の芯・+Z が下流)/ 向き = 区間の向き /
    /// 傾き = 底の勾配(駒の前後の底の差)/ 高さ = **駒の実測の溝の底**を解いた底へ当てる(⛔ ピボットで決めない)。
    /// 最後の駒は走りの端へ引き戻して前の駒へ重ねる(切る・伸ばさない)。<paramref name="pathAt"/> は駒の深さの要求(= 駒が覆う矩形の地面の最低 − 駒の頭の底)から
    /// 部材を選ぶ(null を返したら据えずに数える)。
    /// ⭐ 硬(許容0): **駒が地面より浮かない** ── 据えた駒の実メッシュの矩形(縦 3 × 横 3 の点)で、天端 ≤ その点の地面 + topAbove + 0.01(oki-kata §4 地面 ±0.01)。
    /// 破る駒は据えずに消し、<paramref name="hardFail"/> へ駒の名・浮きの最悪・場所を積む(呼び手は Wait に名乗る ── ⛔ 浮かせて据えない)。
    /// groundAt が null なら検めない(旧の呼び方)。当たる先: 溝の全系統。</summary>
    public static List<GameObject> LayMizo(Transform parent, string prefix, MizoProfile pr, Func<float, string> pathAt, out int missing, out string missWhy,
                                           Func<float, float, float> groundAt = null, List<string> hardFail = null)
    {
        var made = new List<GameObject>(); missing = 0; missWhy = null;
        var line = new List<Vector2>(pr.p);
        float L = pr.length; if (L < 0.2f) return made;
        var spans = MizoPieceSpans(L, pr.pieceLen);
        for (int q = 0; q < spans.Count; q++)
        {
            float s0 = spans[q].x, s1 = spans[q].y, sc = 0.5f * (s0 + s1);
            Vector2 dir; var c = PointAt(line, sc, out dir);
            // 弦の駒(MizoSpec.chord): 平面と向きは P(s0)→P(s1) の弦・頭の駒は頭の小口を P(0)・尻の駒は尻の小口を P(L) へ
            int anchor = 0; Vector2 pA = c, pB = c;
            if (pr.chord)
            {
                Vector2 dd; pA = PointAt(line, s0, out dd); pB = PointAt(line, s1, out dd);
                if ((pB - pA).sqrMagnitude > 1e-6f)
                {
                    c = 0.5f * (pA + pB); dir = (pB - pA).normalized;
                    bool head = s0 <= 1e-4f, tail = s1 >= L - 1e-4f;
                    anchor = head && !tail ? -1 : tail && !head ? 1 : 0;
                }
            }
            float b0 = pr.At(s0), b1 = pr.At(s1), bc = 0.5f * (b0 + b1);
            // 深さの要求 = 駒が覆う矩形の地面の最低 − 駒の頭(高い側)の底(⛔ 線の上の一点の地面で選ばない ── 縁と小口が浮く)
            float gq = pr.pieceGround != null && q < pr.pieceGround.Length && !float.IsNaN(pr.pieceGround[q]) ? pr.pieceGround[q] : float.NaN;
            float need;
            if (!float.IsNaN(gq)) need = gq - Mathf.Max(b0, b1);
            else { int i = Array.BinarySearch(pr.s, sc); if (i < 0) i = Mathf.Clamp(~i, 0, pr.s.Length - 1); need = pr.ground[i] - bc; }
            string path = pathAt(need);
            if (string.IsNullOrEmpty(path) || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { missing++; if (missWhy == null) missWhy = path ?? "(部材の名が無い)"; continue; }
            var mp = MizoPieceOf(path); if (!mp.ok) { missing++; if (missWhy == null) missWhy = path + "(溝の底が測れない)"; continue; }
            float pitch = Mathf.Atan2(b0 - b1, Mathf.Max(1e-3f, pr.chord ? Mathf.Max((pB - pA).magnitude, 0.5f * (s1 - s0)) : s1 - s0)) * Mathf.Rad2Deg;
            float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
            string nm = prefix + "_" + q.ToString("000");
            var go = Place(path, new Vector3(c.x, 0f, c.y), yaw, Vector3.one, parent, nm);
            go.transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
            // 溝の底の当たり(局所 (0, floor, 中ほど))を解いた底 bc へ
            var zc = 0.5f * (mp.zMin + mp.zMax);
            var w = go.transform.TransformPoint(new Vector3(0f, mp.floor, anchor < 0 ? mp.zMin : anchor > 0 ? mp.zMax : zc));
            Vector2 atP = anchor < 0 ? pA : anchor > 0 ? pB : c; float yAt = anchor < 0 ? b0 : anchor > 0 ? b1 : bc;
            go.transform.position += new Vector3(atP.x - w.x, yAt - w.y, atP.y - w.z);
            if (groundAt != null)
            {
                // 硬: 駒の矩形の各点で 天端 ≤ 地面 + topAbove + 0.01
                float worst = 0f; Vector3 at = Vector3.zero; float atG = float.NaN;
                foreach (float lx in new[] { mp.xMin, 0.5f * (mp.xMin + mp.xMax), mp.xMax })
                    foreach (float lz in new[] { mp.zMin, zc, mp.zMax })
                    {
                        var tp = go.transform.TransformPoint(new Vector3(lx, mp.top, lz));
                        float g = groundAt(tp.x, tp.z); if (float.IsNaN(g)) continue;
                        float over = tp.y - (g + pr.topAbove);
                        if (over > worst) { worst = over; at = tp; atG = g; }
                    }
                if (worst > 0.01f)
                {
                    UnityEngine.Object.DestroyImmediate(go);
                    if (hardFail != null) hardFail.Add(nm + " 天端が地面 + " + pr.topAbove.ToString("F2") + " より " + worst.ToString("F3") + "m 上 @(" + at.x.ToString("F1") + ", " + at.z.ToString("F1")
                                                       + ")(底 " + bc.ToString("F3") + "・深さ " + mp.Depth.ToString("F2") + "・地面 " + atG.ToString("F2") + ")");
                    continue;
                }
            }
            made.Add(go);
        }
        return made;
    }

    /// <summary>桝を据える。平面 = <paramref name="at"/>(溝の出合い)・向き = 出る溝の向き。高さ = **桝の実測の底**を
    /// min(天端の狙い − 桝の深さ, 入る溝の底の最低 − 溜め)へ当てる(硬: 桝の底 &lt; 入る溝の底)。天端の沈みを sink に返す(柔)。
    /// 当たる先: D1・D2 の G1・D11 の G2。</summary>
    public static GameObject PlaceMasu(Transform parent, string name, string path, Vector2 at, Vector2 outDir, float topWant, float floorMax, out float floor, out float sink)
    {
        floor = float.NaN; sink = float.NaN;
        var mp = MizoPieceOf(path); if (!mp.ok) return null;
        floor = Mathf.Min(topWant - mp.Depth, floorMax);
        sink = topWant - (floor + mp.Depth);
        var go = Place(path, new Vector3(at.x, 0f, at.y), Mathf.Atan2(outDir.x, outDir.y) * Mathf.Rad2Deg, Vector3.one, parent, name);
        var w = go.transform.TransformPoint(new Vector3(0f, mp.floor, 0.5f * (mp.zMin + mp.zMax)));
        go.transform.position += new Vector3(at.x - w.x, floor - w.y, at.y - w.z);
        return go;
    }

    /// <summary>蓋石を溝の天端に載せる。平面 = 溝の芯の上(長さは溝を横切る向き = 局所 X)。高さ = 蓋の**下端**を、その位置の溝の駒の
    /// 実メッシュの天端(当たり = 縁の天端)へ。路面との差(柔 topTol)を off に返す。当たる先: 型 L(D2・D3・D5 の横断・路の上)。</summary>
    public static GameObject LayFutaishi(Transform parent, string name, string path, Vector2 at, Vector2 flowDir, IList<GameObject> under, Func<float, float, float> groundAt, out float off)
    {
        off = float.NaN;
        var mp = MizoPieceOf(path); if (!mp.ok) return null;
        float crest = float.MinValue;
        foreach (var g in under)
        {
            if (g == null) continue;
            foreach (var p in Body(g.transform, 999999, true))
                if ((new Vector2(p.x, p.z) - at).sqrMagnitude <= 0.6f * 0.6f) crest = Mathf.Max(crest, p.y);
        }
        if (crest == float.MinValue) return null;
        var go = Place(path, new Vector3(at.x, 0f, at.y), Mathf.Atan2(flowDir.x, flowDir.y) * Mathf.Rad2Deg, Vector3.one, parent, name);
        float yb = go.transform.TransformPoint(new Vector3(0f, mp.bottom, 0f)).y;
        go.transform.position += new Vector3(0f, crest - yb, 0f);
        float top = crest + (mp.top - mp.bottom);
        off = top - groundAt(at.x, at.y);
        return go;
    }

    // ---------------------------------------------------------------- 暗渠(溝が据わった駒の足元の下を抜ける所)
    /// <summary><see cref="LayAnkyoUnder"/> の答え。</summary>
    public class AnkyoRep
    {
        /// <summary>据えた蓋石の数・蓋を掛けた(駒, 溝)の組・地面に掛からず据えなかった蓋の数。</summary>
        public int lids, pairs, refused;
        /// <summary>据えた蓋の天端と相手の足元の差の最悪[m](作りの上では 0)。</summary>
        public float worstTop;
        public List<string> notes = new List<string>();
        public List<string> refusedWhy = new List<string>();
        public string Summary() { return "暗渠の蓋 " + lids + " 枚(駒と溝の組 " + pairs + ")" + (refused > 0 ? "・据えない " + refused : ""); }
    }

    /// <summary>XZ の点の凸包(反時計回り・Andrew の単調連鎖)。2 点以下はそのまま返す。</summary>
    public static List<Vector2> ConvexHull2(List<Vector2> pts)
    {
        var p = new List<Vector2>(pts); p.Sort((a, b) => a.x != b.x ? a.x.CompareTo(b.x) : a.y.CompareTo(b.y));
        if (p.Count < 3) return p;
        Func<Vector2, Vector2, Vector2, float> cr = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
        var h = new List<Vector2>();
        for (int i = 0; i < p.Count; i++) { while (h.Count >= 2 && cr(h[h.Count - 2], h[h.Count - 1], p[i]) <= 0f) h.RemoveAt(h.Count - 1); h.Add(p[i]); }
        int lo = h.Count + 1;
        for (int i = p.Count - 2; i >= 0; i--) { while (h.Count >= lo && cr(h[h.Count - 2], h[h.Count - 1], p[i]) <= 0f) h.RemoveAt(h.Count - 1); h.Add(p[i]); }
        h.RemoveAt(h.Count - 1);
        return h;
    }

    /// <summary>二つの凸多角形(XZ)が <paramref name="eps"/> を超えて重なるか(分離軸)。辺が触れるだけの組は重ならないと読む。</summary>
    public static bool ConvexOverlap(List<Vector2> a, List<Vector2> b, float eps = 0.005f)
    {
        if (a == null || b == null || a.Count < 3 || b.Count < 3) return false;
        foreach (var poly in new[] { a, b })
            for (int i = 0; i < poly.Count; i++)
            {
                var e = poly[(i + 1) % poly.Count] - poly[i]; var ax = new Vector2(-e.y, e.x); float m = ax.magnitude; if (m < 1e-6f) continue; ax /= m;
                float a0 = float.MaxValue, a1 = float.MinValue, b0 = float.MaxValue, b1 = float.MinValue;
                foreach (var q in a) { float t = Vector2.Dot(q, ax); a0 = Mathf.Min(a0, t); a1 = Mathf.Max(a1, t); }
                foreach (var q in b) { float t = Vector2.Dot(q, ax); b0 = Mathf.Min(b0, t); b1 = Mathf.Max(b1, t); }
                if (a1 < b0 + eps || b1 < a0 + eps) return false;
            }
        return true;
    }

    /// <summary>駒の実メッシュ(屋根を除く・世界)の三角形と平面の外形(全頂点の凸包)。<see cref="LowestSurfaceAt"/> の下ごしらえ。</summary>
    public class SurfaceSet { public GameObject go; public List<Vector3[]> tris = new List<Vector3[]>(); public List<Vector2> hull; }
    public static SurfaceSet SurfaceOf(GameObject go)
    {
        if (go == null) return null;
        var r = new SurfaceSet { go = go }; var xz = new List<Vector2>();
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null || !mf.gameObject.activeInHierarchy) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            if (IsRoofLabel(mf.name)) continue;
            var M = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices; var tr = mf.sharedMesh.triangles;
            var W = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) { W[i] = M.MultiplyPoint3x4(vs[i]); xz.Add(new Vector2(W[i].x, W[i].z)); }
            for (int t = 0; t + 2 < tr.Length; t += 3) r.tris.Add(new[] { W[tr[t]], W[tr[t + 1]], W[tr[t + 2]] });
        }
        if (r.tris.Count == 0) return null;
        r.hull = ConvexHull2(xz); return r.hull.Count >= 3 ? r : null;
    }

    /// <summary>点 (x, z) の鉛直線と駒の三角形の交わりのうち**最も低い高さ** = その点の足元(駒の下面)。交わらなければ NaN。
    /// ⭐ 帯(最下点から 0.05)で足元を採ると、段に据わる布石のように下面が段違いの駒では最も低い所しか拾えない ── 点ごとに下面を引く。</summary>
    public static float LowestSurfaceAt(SurfaceSet s, Vector2 q)
    {
        float best = float.MaxValue;
        foreach (var t in s.tris)
        {
            Vector3 a = t[0], b = t[1], c = t[2];
            if (q.x < Mathf.Min(a.x, Mathf.Min(b.x, c.x)) || q.x > Mathf.Max(a.x, Mathf.Max(b.x, c.x)) || q.y < Mathf.Min(a.z, Mathf.Min(b.z, c.z)) || q.y > Mathf.Max(a.z, Mathf.Max(b.z, c.z))) continue;
            float d = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z); if (Mathf.Abs(d) < 1e-9f) continue;
            float u = ((b.z - c.z) * (q.x - c.x) + (c.x - b.x) * (q.y - c.z)) / d, v = ((c.z - a.z) * (q.x - c.x) + (a.x - c.x) * (q.y - c.z)) / d, w = 1f - u - v;
            if (u < -1e-5f || v < -1e-5f || w < -1e-5f) continue;
            best = Mathf.Min(best, u * a.y + v * b.y + w * c.y);
        }
        return best == float.MaxValue ? float.NaN : best;
    }

    /// <summary>点 (x, z) の鉛直線上で、**上に <paramref name="minSolid"/> 以上の実体が続く下面**のうち最も低い高さ = 駒が立つ足元。無ければ NaN。
    /// 交わりを低い順に並べ、偶奇で入る面(下面)と出る面(上面)を組にし、組の厚みが minSolid 未満の物(塀の笠・水切り・軒の張り出しの裏)は足元と数えない。最も低い交わりが上向きの面なら(底の開いた駒)点の近くの頂点の最も低い所。
    /// ⭐ <see cref="LowestSurfaceAt"/> は最も低い交わりを返すので、溝が塀の脇を走って笠の張り出しの下を通るだけの所でも笠の裏(地面から 2m 上)を足元と読み、
    /// 蓋が宙に浮くと偽って退けた(土井 S9 奥の塀 Oku_Hei_Roka・Oku_Hei_0_4 ほか 18 点 ── EDO-0533 第11巡)。
    /// 当たる先: <see cref="LayAnkyoUnder"/>(土井 S9)。張り出しを持つ駒(練塀・築地・長屋の軒)の足元を点で引く所すべて。</summary>
    public static float LowestFootAt(SurfaceSet s, Vector2 q, float minSolid = 0.3f)
    {
        var hs = new List<Vector2>();   // x = 高さ・y = 面の法線の y
        foreach (var t in s.tris)
        {
            Vector3 a = t[0], b = t[1], c = t[2];
            if (q.x < Mathf.Min(a.x, Mathf.Min(b.x, c.x)) || q.x > Mathf.Max(a.x, Mathf.Max(b.x, c.x)) || q.y < Mathf.Min(a.z, Mathf.Min(b.z, c.z)) || q.y > Mathf.Max(a.z, Mathf.Max(b.z, c.z))) continue;
            float d = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z); if (Mathf.Abs(d) < 1e-9f) continue;
            float u = ((b.z - c.z) * (q.x - c.x) + (c.x - b.x) * (q.y - c.z)) / d, v = ((c.z - a.z) * (q.x - c.x) + (a.x - c.x) * (q.y - c.z)) / d, w = 1f - u - v;
            if (u < -1e-5f || v < -1e-5f || w < -1e-5f) continue;
            hs.Add(new Vector2(u * a.y + v * b.y + w * c.y, Vector3.Cross(b - a, c - a).normalized.y));
        }
        if (hs.Count == 0) return float.NaN;
        hs.Sort((x, y) => x.x.CompareTo(y.x));
        var uq = new List<Vector2>(); foreach (var h in hs) if (uq.Count == 0 || h.x - uq[uq.Count - 1].x > 1e-4f) uq.Add(h);   // 稜で二つの三角形に当たった重複を落とす
        // 底の面を持たない駒(下の開いた練塀の腰 ── 最も低い交わりが上向きの面)は、点が実体の中にある。足元は点を挟む鉛直な面の下の縁(OpenBottomFoot)
        if (uq[0].y > 0.1f)
        {
            float lo = OpenBottomFoot(s, q);
            return !float.IsNaN(lo) && lo < uq[0].x ? lo : float.NaN;
        }
        for (int i = 0; i + 1 < uq.Count; i += 2) if (uq[i + 1].x - uq[i].x >= minSolid) return uq[i].x;
        return float.NaN;
    }

    /// <summary>**底の開いた駒の足元**(点 q の鉛直線が下面に当たらない駒 ── 練塀 Dobei2m の下見板の腰は底も天端も無い箱の側面だけ)。
    /// 点から平面で <paramref name="r"/> 以内を通る鉛直な面のうち、点が**面の裏(駒の内)**にある物を集め、外向きが向かい合う二枚(内積 &lt; −0.7)で
    /// 下の縁の高さが揃う(差 ≤ 0.05)組 = 点を挟む壁の両面 ── その下の縁(点の位置での面の最も低い所)の最小を返す。組が無ければ NaN(点は実体の外)。
    /// ⭐ 2026-10-05 まで「点の近く 0.3m の頂点の最も低い所」で引き、腰の列(0.668m 毎)の中ほどの点では下見板の下の頂点が 0.3m の外になって
    /// 貫の下端(+0.70)を足元と読み、蓋を「宙に浮く」と退けた(土井 S9 奥の塀 Oku_Hei_Roka の駒の継ぎ目 2 点 ── 塀が溝 D2 の上で 0.680 浮いた・EDO-0533 第11巡)。
    /// 軒の下で壁の外の点も、壁の下の頂点が 0.3m 以内なら足元と読んでいた(Oku_Hei_0_4)── 点が面の裏にある組だけを数えて塞ぐ。
    /// 当たる先: <see cref="LowestFootAt"/> の底の開いた駒(練塀 Dobei2m・Dobei2m_End・袖塀 ── 同じ生成器の腰を持つ駒すべて)。呼ぶのは土井 S9 の暗渠だけ。</summary>
    public static float OpenBottomFoot(SurfaceSet s, Vector2 q, float r = 0.6f)
    {
        // 巻きの裏返った駒(外向きが内を向く)でも、点が外にあれば裏にある面は片側だけ ── 向きを逆にして引き直しても外の点は NaN のまま
        float y = OpenBottomFootSigned(s, q, r, 1f);
        return float.IsNaN(y) ? OpenBottomFootSigned(s, q, r, -1f) : y;
    }
    static float OpenBottomFootSigned(SurfaceSet s, Vector2 q, float r, float sgn)
    {
        var faces = new List<Vector3>();   // x, y = 外向き(平面)・z = 点の位置での面の下の縁
        foreach (var t in s.tris)
        {
            var nv = Vector3.Cross(t[1] - t[0], t[2] - t[0]); float mag = nv.magnitude; if (mag < 1e-9f || Mathf.Abs(nv.y) / mag > 0.2f) continue;
            var nh = new Vector2(nv.x, nv.z) * sgn; if (nh.sqrMagnitude < 1e-12f) continue; nh.Normalize();
            // 平面で最も離れた二頂点を面の軸に取る
            int a = 0, b = 1; float dmax = -1f;
            for (int u = 0; u < 3; u++) for (int v = u + 1; v < 3; v++) { float dd = new Vector2(t[u].x - t[v].x, t[u].z - t[v].z).sqrMagnitude; if (dd > dmax) { dmax = dd; a = u; b = v; } }
            if (dmax < 1e-6f) continue;
            Vector2 A = new Vector2(t[a].x, t[a].z), ab = new Vector2(t[b].x, t[b].z) - A; float L2 = ab.sqrMagnitude;
            float uq = Vector2.Dot(q - A, ab) / L2; if (uq < -1e-3f || uq > 1f + 1e-3f) continue;
            float side = Vector2.Dot(q - (A + ab * Mathf.Clamp01(uq)), nh);
            if (side > 1e-4f || -side > r) continue;   // 点が面の表(外)・遠い
            float lo = float.MaxValue;
            for (int e = 0; e < 3; e++)
            {
                var p0 = t[e]; var p1 = t[(e + 1) % 3];
                float u0 = Vector2.Dot(new Vector2(p0.x, p0.z) - A, ab) / L2, u1 = Vector2.Dot(new Vector2(p1.x, p1.z) - A, ab) / L2;
                float mn = Mathf.Min(u0, u1), mx = Mathf.Max(u0, u1); if (uq < mn - 1e-3f || uq > mx + 1e-3f) continue;
                float yy = mx - mn < 1e-5f ? Mathf.Min(p0.y, p1.y) : Mathf.Lerp(p0.y, p1.y, Mathf.Clamp01((uq - u0) / (u1 - u0)));
                lo = Mathf.Min(lo, yy);
            }
            if (lo < float.MaxValue) faces.Add(new Vector3(nh.x, nh.y, lo));
        }
        float best = float.NaN;
        for (int i = 0; i < faces.Count; i++)
            for (int j = i + 1; j < faces.Count; j++)
            {
                if (faces[i].x * faces[j].x + faces[i].y * faces[j].y > -0.7f || Mathf.Abs(faces[i].z - faces[j].z) > 0.05f) continue;
                float yy = Mathf.Max(faces[i].z, faces[j].z);
                if (float.IsNaN(best) || yy < best) best = yy;
            }
        return best;
    }

    /// <summary>**暗渠**(硬い・許容0 ── 足元の浮き)。溝の駒 <paramref name="channel"/> が、地面に据わった駒 <paramref name="over"/>(塀・布石・石段)の
    /// 足元の下を抜ける所に、蓋石を溝の向きに並べて**蓋の天端を駒の足元に合わせる**(溝の中の水は蓋の下を通る ── 江戸の作りの、塀の下を石の蓋で抜ける形)。
    /// <para>当たり: 蓋の天端 × 駒の下面(蓋の天端の面の中ほどと四隅で、鉛直に引いた駒の三角形の最も低い交わり ── 塀が布石に載る所は布石の下面が最も低いので、そこへ合わせる)/
    /// 蓋の両端の下面 × 溝の脇の地面(蓋は溝の縁ではなく脇の地面に掛かる ── 天端の沈んだ溝の上に浮かせない)。</para>
    /// <para>据える条件: 蓋の位置で駒の足元が溝の天端より 0.01 を超えて高い(= 溝の上で足元が浮いている)。
    /// 厚み <paramref name="tChoices"/> は大きい順に、蓋の下端が溝の天端を割らない最も厚い物(割るなら最も薄い物 ── 溝の縁へ埋まるのは部材どうしで数えない)。
    /// 蓋の両端の地面より下端が 0.01 を超えて高い所は**据えない**(硬い ── 蓋が宙に浮く)。それは溝ではなく駒の足元の側の欠陥(段の継ぎ目で布石が届かない等)なので、
    /// <see cref="AnkyoRep.refusedWhy"/> に駒の名と差を名乗る。</para>
    /// <para>⭐ <paramref name="coverHollow"/>(土井が渡す・2026-10-05 EDO-0533 第11巡の直し): 足元が溝の天端より高くなくても(布石の下端が溝の縁と同じ高さ)、
    /// **駒の実体が溝の芯の真上にあり、足元が溝の底(芯の鉛直線で上を向く面の最も高い所 ── 縁の天端 − 0.02 より下)より 0.01 を超えて高い**なら、駒は溝の窪みを
    /// 跨いで浮いている ── 同じく蓋を据える(天端 = 足元・厚みは最も薄い物 ── 蓋が溝の縁へ埋まるのは部材どうしで数えない)。
    /// ⛔ 渡さないと従来どおり(足元 − 天端 ≤ 0.01 は「溝が足元を割る」と読んで飛ばす ── 奥の塀の布石 Oku_Hei_0_0〜0_4_ishi が溝 D2 の窪みの上で 0.13〜0.18 浮いた)。</para>
    /// <para>⭐ coverHollow のとき(2026-10-05 EDO-0533 第12巡): 窪みを跨ぐかは溝の芯でなく**足元を引いた点**で見る(溝が駒の脇を並走して芯が駒の外にある所 ── 布石の縁だけが溝に掛かる所)/他の駒の天端に載る足元(布石に載る塀の下端)は数えない(<see cref="RestsOnOther"/>)。</para>
    /// <para><paramref name="minSolid"/>: 足元と読む実体の厚みの下限(<see cref="LowestFootAt"/>)。既定 0.3 は塀の笠の裏を外す値 ── 薄い石(飛石・沓脱)を相手にする呼び手だけが下げる。</para>
    /// 当たる先: 溝が塀・布石・石段の足元の下を通る所の全部(いまは土井 S9 だけが呼ぶ ── 奥の塀・奥の塀の廊下際・蔵の石段)。</summary>
    public static List<GameObject> LayAnkyoUnder(Transform parent, string prefix, IList<GameObject> channel, IList<GameObject> over,
                                                 Func<float, string> lidPathForT, float[] tChoices, Func<float, float, float> groundAt, out AnkyoRep rep,
                                                 bool coverHollow = false, float minSolid = 0.3f)
    {
        rep = new AnkyoRep(); var made = new List<GameObject>();
        if (channel == null || over == null || tChoices == null || tChoices.Length == 0) return made;
        var ts = new List<float>(tChoices); ts.Sort((x, y) => y.CompareTo(x));
        var mps = new Dictionary<float, MizoPiece>(); var paths = new Dictionary<float, string>();
        // 蓋石は低ポリの板で芯の帯に頂点も上向きの面の重心も無く、溝の底(floor)が解けず mp.ok が偽になる(EDO-0533 第11巡 ── 暗渠が全型で「測れない」)。
        // 蓋に要るのは外形(長さ・幅・丈)だけなので、ok ではなく外形が取れたかで採る。
        foreach (var t in ts) { string p = lidPathForT(t); var mp = MizoPieceOf(p); if (p != null && mp.len > 1e-3f && mp.top > mp.bottom) { mps[t] = mp; paths[t] = p; } }
        if (mps.Count == 0) { rep.notes.Add("蓋石の部材が測れない"); return made; }
        var mp0 = mps[ts.Find(t => mps.ContainsKey(t))];
        float lidLen = mp0.zMax - mp0.zMin, lidHalfW = 0.5f * (mp0.xMax - mp0.xMin);
        if (lidLen < 0.05f) { rep.notes.Add("蓋石の長さが測れない"); return made; }
        // 相手の下面
        var feet = new List<SurfaceSet>();
        foreach (var g in over) { if (g == null || !g.activeInHierarchy) continue; var ss = SurfaceOf(g); if (ss != null) feet.Add(ss); }
        // 溝の駒の外形と頂点
        var chHull = new List<List<Vector2>>(); var chPts = new List<List<Vector3>>(); var chGo = new List<GameObject>();
        foreach (var c in channel)
        {
            if (c == null || !c.activeInHierarchy) continue;
            var pts = Body(c.transform, 999999, true); if (pts.Count == 0) continue;
            var xz = new List<Vector2>(); foreach (var p in pts) xz.Add(new Vector2(p.x, p.z));
            var h = ConvexHull2(xz); if (h.Count < 3) continue;
            chHull.Add(h); chPts.Add(pts); chGo.Add(c);
        }
        Func<Vector2, float> crestAt = q =>
        {
            float best = float.MinValue;
            for (int i = 0; i < chGo.Count; i++) foreach (var p in chPts[i]) if ((new Vector2(p.x, p.z) - q).sqrMagnitude <= 0.35f * 0.35f) best = Mathf.Max(best, p.y);
            return best == float.MinValue ? float.NaN : best;
        };
        var lidAt = new List<Vector2>(); var pairSeen = new HashSet<string>();
        var chSurf = new Dictionary<int, SurfaceSet>();
        for (int ci = 0; ci < chGo.Count; ci++)
        {
            var hp = chHull[ci];
            var hits = feet.FindAll(f => ConvexOverlap(hp, f.hull));
            if (hits.Count == 0) continue;
            // 溝の駒の軸(局所 +Z = 流れ)と、軸に沿う外形の範囲・軸に直交する芯
            var fw = chGo[ci].transform.forward; var d = new Vector2(fw.x, fw.z); if (d.sqrMagnitude < 1e-6f) continue; d.Normalize();
            var nrm = new Vector2(-d.y, d.x);
            float s0 = float.MaxValue, s1 = float.MinValue, n0 = float.MaxValue, n1 = float.MinValue;
            foreach (var q in hp) { float s = Vector2.Dot(q, d), n = Vector2.Dot(q, nrm); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); n0 = Mathf.Min(n0, n); n1 = Mathf.Max(n1, n); }
            float nc = 0.5f * (n0 + n1);
            for (float sc = s0 + 0.5f * lidLen; sc - 0.5f * lidLen < s1 - 1e-3f; sc += lidLen)
            {
                var c = d * sc + nrm * nc;
                var rect = new List<Vector2> { c - d * 0.5f * lidLen - nrm * lidHalfW, c + d * 0.5f * lidLen - nrm * lidHalfW, c + d * 0.5f * lidLen + nrm * lidHalfW, c - d * 0.5f * lidLen + nrm * lidHalfW };
                if (lidAt.Exists(q => (q - c).sqrMagnitude < 0.25f * lidLen * lidLen)) continue;
                // 足元 = 蓋の天端の面(中ほどと四隅の内 0.8)の上にある駒の下面の最も低い所(塀が布石に載る所は布石の下面)
                float foot = float.MaxValue; string who = null; SurfaceSet whoS = null; var on = new List<SurfaceSet>(); Vector2 footQ = c;
                foreach (var f in hits)
                {
                    if (!ConvexOverlap(rect, f.hull)) continue;
                    float fm = float.MaxValue; Vector2 fq = c;
                    foreach (var q in new[] { c, c + 0.8f * (rect[0] - c), c + 0.8f * (rect[1] - c), c + 0.8f * (rect[2] - c), c + 0.8f * (rect[3] - c) })
                    {
                        float y = LowestFootAt(f, q, minSolid); if (float.IsNaN(y)) continue;   // 笠・水切りの張り出しの裏は足元でない
                        // coverHollow(土井): 他の駒の天端に載る足元(布石に載る塀の下端)は地面の足元でない ── 数えると布石の天端 27.10 を足元と読み「蓋が宙に浮く」と退けた
                        //   (奥の塀 Oku_Hei_0_4・1_4 ── EDO-0533 第12巡)。足元は布石(載せている駒)の側で引く
                        if (coverHollow && RestsOnOther(f, q, y, hits)) continue;
                        if (y < fm) { fm = y; fq = q; }
                    }
                    if (fm == float.MaxValue) continue;
                    on.Add(f); if (fm < foot) { foot = fm; who = f.go.name; whoS = f; footQ = fq; }
                }
                if (on.Count == 0) continue;
                float crest = crestAt(c); if (float.IsNaN(crest)) continue;
                bool bridge = false;
                if (foot - crest <= 0.01f)
                {
                    // 足元は溝の天端より高くない(溝が足元を割る所 ── 部材どうしの重なり)。coverHollow のときだけ、窪みを跨ぐ駒かを見る
                    // ⭐ 窪みを跨ぐかは**足元を引いた点**(footQ)で見る ── 溝の芯で駒の実体を引くと、溝が駒の脇を並走して芯が駒の外にある所(布石の縁だけが溝の上に
                    //   掛かる所)を全部飛ばした(奥の塀 Oku_Hei_0_0〜0_3_ishi が D2 の上で 0.15〜0.18 浮いたまま・溝の芯は布石の外 ── EDO-0533 第12巡)
                    if (!coverHollow || whoS == null) continue;
                    SurfaceSet cs; if (!chSurf.TryGetValue(ci, out cs)) { cs = SurfaceOf(chGo[ci]); chSurf[ci] = cs; }
                    float fl = cs != null ? ChannelFloorAt(cs, footQ, crest - 0.02f) : float.NaN;
                    if (float.IsNaN(fl) || foot - fl <= 0.01f) continue;
                    bridge = true;
                }
                float t = ts.Find(x => mps.ContainsKey(x) && foot - x >= crest - 1e-3f);
                if (t <= 0f) { t = ts[ts.Count - 1]; while (!mps.ContainsKey(t)) t = ts[ts.IndexOf(t) - 1]; }
                var mp = mps[t]; float bottom = foot - (mp.top - mp.bottom);
                float gEnd = float.MaxValue;
                foreach (float sg in new[] { 1f, -1f }) { var e = c + nrm * sg * (lidHalfW - 0.05f); float g = groundAt(e.x, e.y); if (!float.IsNaN(g)) gEnd = Mathf.Min(gEnd, g); }
                if (gEnd == float.MaxValue) continue;
                if (bottom > gEnd + 0.01f)
                {
                    rep.refused++;
                    rep.refusedWhy.Add(who + ": 足元 " + foot.ToString("F3") + " が溝の脇の地面 " + gEnd.ToString("F3") + " より " + (foot - gEnd).ToString("F3") + "m 高い @(" + c.x.ToString("F1") + ", " + c.y.ToString("F1") + ")── 蓋が宙に浮く(溝でなく足元の側)");
                    lidAt.Add(c); continue;
                }
                var go = Place(paths[t], new Vector3(c.x, 0f, c.y), Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg, Vector3.one, parent, prefix + "_" + rep.lids.ToString("000"));
                if (go == null) continue;
                // 平面 = 蓋の実メッシュの中ほどを c へ・高さ = 実メッシュの天端を足元へ(⛔ ピボットで決めない)
                var w = go.transform.TransformPoint(new Vector3(0.5f * (mp.xMin + mp.xMax), mp.top, 0.5f * (mp.zMin + mp.zMax)));
                go.transform.position += new Vector3(c.x - w.x, foot - w.y, c.y - w.z);
                float topNow = go.transform.TransformPoint(new Vector3(0f, mp.top, 0f)).y;
                rep.worstTop = Mathf.Max(rep.worstTop, Mathf.Abs(topNow - foot));
                made.Add(go); lidAt.Add(c); rep.lids++;
                foreach (var f in on) if (pairSeen.Add(f.go.name + "|" + chGo[ci].name)) rep.pairs++;
                rep.notes.Add(go.name + " → " + who + "(足元 " + foot.ToString("F3") + "・溝の天端 " + crest.ToString("F3") + "・t " + t.ToString("0.00") + "・脇の地面 " + gEnd.ToString("F3") + (bridge ? "・窪みを跨ぐ駒" : "") + ")");
            }
        }
        return made;
    }

    /// <summary>駒 <paramref name="f"/> の点 q の足元 <paramref name="y"/> が、<paramref name="others"/> の別の駒の**上を向く面**(天端)に ±<paramref name="tol"/> で載っているか
    /// (塀が布石に載る・柱が礎石に載る)。載っていれば、その足元は地面の足元でない。当たる先: <see cref="LayAnkyoUnder"/> の coverHollow(土井 S9)。</summary>
    public static bool RestsOnOther(SurfaceSet f, Vector2 q, float y, IList<SurfaceSet> others, float tol = 0.03f)
    {
        if (others == null) return false;
        foreach (var g in others)
        {
            if (g == null || g == f || g.go == f.go) continue;
            foreach (var t in g.tris)
            {
                Vector3 a = t[0], b = t[1], c = t[2];
                if (q.x < Mathf.Min(a.x, Mathf.Min(b.x, c.x)) || q.x > Mathf.Max(a.x, Mathf.Max(b.x, c.x)) || q.y < Mathf.Min(a.z, Mathf.Min(b.z, c.z)) || q.y > Mathf.Max(a.z, Mathf.Max(b.z, c.z))) continue;
                if (Vector3.Cross(b - a, c - a).normalized.y <= 0.1f) continue;
                float d = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z); if (Mathf.Abs(d) < 1e-9f) continue;
                float u = ((b.z - c.z) * (q.x - c.x) + (c.x - b.x) * (q.y - c.z)) / d, v = ((c.z - a.z) * (q.x - c.x) + (a.x - c.x) * (q.y - c.z)) / d, w = 1f - u - v;
                if (u < -1e-5f || v < -1e-5f || w < -1e-5f) continue;
                if (Mathf.Abs(u * a.y + v * b.y + w * c.y - y) <= tol) return true;
            }
        }
        return false;
    }

    /// <summary>溝の駒の**底**(点 q の鉛直線で上を向く面のうち <paramref name="below"/> より低い最も高い所 ── 窪みの床)。無ければ NaN。
    /// 当たる先: <see cref="LayAnkyoUnder"/> の coverHollow(土井 S9)。</summary>
    public static float ChannelFloorAt(SurfaceSet s, Vector2 q, float below)
    {
        float best = float.NaN;
        foreach (var t in s.tris)
        {
            Vector3 a = t[0], b = t[1], c = t[2];
            if (q.x < Mathf.Min(a.x, Mathf.Min(b.x, c.x)) || q.x > Mathf.Max(a.x, Mathf.Max(b.x, c.x)) || q.y < Mathf.Min(a.z, Mathf.Min(b.z, c.z)) || q.y > Mathf.Max(a.z, Mathf.Max(b.z, c.z))) continue;
            if (Vector3.Cross(b - a, c - a).normalized.y <= 0.1f) continue;
            float d = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z); if (Mathf.Abs(d) < 1e-9f) continue;
            float u = ((b.z - c.z) * (q.x - c.x) + (c.x - b.x) * (q.y - c.z)) / d, v = ((c.z - a.z) * (q.x - c.x) + (a.x - c.x) * (q.y - c.z)) / d, w = 1f - u - v;
            if (u < -1e-5f || v < -1e-5f || w < -1e-5f) continue;
            float y = u * a.y + v * b.y + w * c.y;
            if (y < below && (float.IsNaN(best) || y > best)) best = y;
        }
        return best;
    }

    // ---------------------------------------------------------------- 桝の置き場を面の取り合いで解く(EDO-0533 第11巡)
    /// <summary><see cref="MasuPlanOffLine"/> の答え。at・outDir は <see cref="PlaceMasu"/> へそのまま渡す。face* = 桝の外面の中央(世界 XZ)──
    /// faceIn = 棟側(線の側)・faceOut = 外(outDir の側)・faceXmin / faceXmax = 局所 X の両側面。onLine = 軸線と線の交点。
    /// straightDev = 二つの辺の一直線からの外れの最大[m]・axisSkewDeg = 軸線と線の法線のなす角。</summary>
    public class MasuPlan
    {
        public bool ok; public string why;
        public Vector2 at, outDir, lat, center, faceIn, faceOut, faceXmin, faceXmax, onLine;
        /// <summary>桝の駒の局所の原点(ピボット = 桝の芯)の世界 XZ ── 局所 +X = lat・+Z = outDir。内法の窪みの外形を引くのに使う(<see cref="MasuInnerHull"/>)。</summary>
        public Vector2 pivot;
        public float off, straightDev, axisSkewDeg;
    }

    /// <summary>**桝の平面を面の取り合いで解く**(指図 masu[].at「<棟>と<棟>の間の坪の中心線を<相手>側へ延ばした線の上。桝の棟側の外面は、<棟>・<棟> の軒の矩形の<相手>側の辺から外へ d。
    /// 桝の辺は軒の矩形に平行」)。線 = <paramref name="sideA"/>(軒の矩形の辺)を通る直線・外 = 棟の芯 <paramref name="bldCenter"/> から離れる向き。
    /// 桝の向き: 局所 +Z(<see cref="PlaceMasu"/> の outDir)= 線の外向きの法線(辺は線に平行)。
    /// 位置: **桝の駒の実測の外形**(<see cref="MizoPieceOf"/> の xMin..xMax・zMin..zMax)で、棟側の外面(局所 zMin の面)を線から外へ <paramref name="off"/>、
    /// 横の外形の中央を軸線 <paramref name="axis"/>(坪の中心線を延ばした線)の上へ。⛔ ピボット・入る溝の尻の平均で置かない。
    /// <paramref name="sideB"/> は「二つは一直線」の確かめ(外れの最大を straightDev に刷る ── 呼び手が判ずる)。
    /// 当たる先: 土井 D1 masu[0](書院・表役所の坪の口)。以後、軒先の線・塀の面から離れを指図した桝の全て。</summary>
    public static MasuPlan MasuPlanOffLine(string path, List<Vector2> sideA, List<Vector2> sideB, Vector2 bldCenter, List<Vector2> axis, float off)
    {
        var r = new MasuPlan { off = off };
        var mp = MizoPieceOf(path); if (!mp.ok) { r.why = "桝の駒が測れない(" + path + ")"; return r; }
        if (sideA == null || sideA.Count < 2 || axis == null || axis.Count < 2) { r.why = "線か軸線が無い"; return r; }
        Vector2 a = sideA[0], t = sideA[sideA.Count - 1] - sideA[0]; if (t.sqrMagnitude < 1e-6f) { r.why = "軒の辺の長さが 0"; return r; }
        t.Normalize();
        var n = new Vector2(-t.y, t.x); if (Vector2.Dot(n, a - bldCenter) < 0f) n = -n;
        r.straightDev = 0f;
        if (sideB != null) foreach (var q in sideB) r.straightDev = Mathf.Max(r.straightDev, Mathf.Abs(Vector2.Dot(q - a, n)));
        Vector2 ad = axis[axis.Count - 1] - axis[0]; if (ad.sqrMagnitude < 1e-6f) { r.why = "軸線の長さが 0"; return r; }
        ad.Normalize();
        float cosA = Mathf.Abs(Vector2.Dot(ad, n));
        if (cosA < 0.5f) { r.why = "軸線が軒の辺とほぼ平行(交わらない)"; return r; }
        r.axisSkewDeg = Mathf.Acos(Mathf.Clamp01(cosA)) * Mathf.Rad2Deg;
        r.onLine = EdoGeom.LineIntersect(axis[0], ad, a, t, axis[0]);
        var lat = new Vector2(n.y, -n.x);   // PlaceMasu の yaw で局所 +X が向く向き
        float xmid = 0.5f * (mp.xMin + mp.xMax), zmid = 0.5f * (mp.zMin + mp.zMax);
        var P = r.onLine + n * (off - mp.zMin) - lat * xmid;   // 局所の原点(棟側の面 = 線 + off・横の外形の中央 = 軸線)
        r.outDir = n; r.lat = lat;
        r.pivot = P;
        r.at = P + n * zmid;
        r.center = P + n * zmid + lat * xmid;
        r.faceIn = P + n * mp.zMin + lat * xmid; r.faceOut = P + n * mp.zMax + lat * xmid;
        r.faceXmin = P + n * zmid + lat * mp.xMin; r.faceXmax = P + n * zmid + lat * mp.xMax;
        r.ok = true; return r;
    }

    /// <summary>**直線の折れ線の、点 <paramref name="q"/> に近い方の端を q へ動かす**(延ばす・縮める)── 坪の中心線を桝の面の中央まで延ばす(指図「泉水側の端は masu の棟側の面の中央まで延ばす」)。
    /// q が終わりの区間の延長から <paramref name="tol"/> を超えて外れるなら null(延ばす線が桝の面の中央を通らない)。返すのは q で終わる向き(上流 → q)。
    /// 当たる先: 土井 D1 seg3。以後、区間の端を桝・吐口の面の中央で止める線の全て。</summary>
    public static List<Vector2> LineEndAt(List<Vector2> pl, Vector2 q, float tol, out string why)
    {
        why = null; if (pl == null || pl.Count < 2) { why = "線が無い"; return null; }
        var cp = new List<Vector2>(pl);
        if ((q - cp[0]).sqrMagnitude < (q - cp[cp.Count - 1]).sqrMagnitude) cp.Reverse();
        var p0 = cp[cp.Count - 2]; var t = cp[cp.Count - 1] - p0; if (t.sqrMagnitude < 1e-8f) { why = "終わりの区間の長さが 0"; return null; }
        t.Normalize();
        var d = q - p0; float off = Mathf.Abs(t.x * d.y - t.y * d.x);
        if (off > tol) { why = "桝の面の中央が線の延長から " + off.ToString("F3") + "m 外れる(許し " + tol.ToString("F2") + ")"; return null; }
        if (Vector2.Dot(d, t) < 0.05f) { why = "桝の面の中央が線の終わりの区間より手前"; return null; }
        cp[cp.Count - 1] = q; return cp;
    }

    /// <summary>**軒先の鉛直下の溝を、桝の側面の中央から <paramref name="deg"/> 度に引いた線で折って桝へ入れる**(指図「坪の側の端は、桝の X 側の面の中央から 45° に引いた線が
    /// 軒先の線に当たる所で止め、そこから masu の X 側の面の中央へ最短」)。<paramref name="eave"/> = 軒先の辺(2 点)・<paramref name="face"/> = 桝の側面の中央・
    /// <paramref name="faceN"/> = その面の外向き(桝の芯から面へ ── 軒の辺に平行)。面の中央から faceN を軒先の線の側へ deg 度振った線が軒先の線に当たる点 K を求め、
    /// [軒先の辺の K から遠い端, K, 面の中央] を返す(上流 → 桝)。K が軒先の辺の外なら null。当たる先: 土井 D1 seg2・seg4。以後、軒先の線の外に据えた桝へ入る雨落ちの全て。</summary>
    public static List<Vector2> EaveLineToFace(List<Vector2> eave, Vector2 face, Vector2 faceN, float deg, out string why)
    {
        why = null;
        if (eave == null || eave.Count < 2) { why = "軒先の辺が無い"; return null; }
        Vector2 a = eave[0], b = eave[eave.Count - 1], t = b - a; float L = t.magnitude; if (L < 1e-3f) { why = "軒先の辺の長さが 0"; return null; }
        t /= L;
        var foot = a + t * Vector2.Dot(face - a, t); var toLine = foot - face; float dl = toLine.magnitude;
        if (dl < 1e-3f) { why = "桝の面の中央が軒先の線の上にある"; return null; }
        toLine /= dl;
        var fn = faceN - toLine * Vector2.Dot(faceN, toLine); if (fn.sqrMagnitude < 1e-6f) { why = "桝の面が軒先の線に向く(側面でない)"; return null; }
        fn.Normalize();
        float rad = Mathf.Clamp(deg, 1f, 89f) * Mathf.Deg2Rad;
        var dir = fn * Mathf.Cos(rad) + toLine * Mathf.Sin(rad);
        var K = face + dir * (dl / Mathf.Sin(rad));
        float sK = Vector2.Dot(K - a, t), sF = Vector2.Dot(foot - a, t);
        if (sK < -1e-3f || sK > L + 1e-3f) { why = "当たる所が軒先の辺の外(辺の端から " + (sK < 0f ? -sK : sK - L).ToString("F2") + "m)"; return null; }
        var far = sK > sF ? b : a;
        if ((far - K).magnitude < 0.05f) { why = "当たる所が軒先の辺の端と重なる"; return null; }
        return new List<Vector2> { far, K, face };
    }

    /// <summary>棟の床下の足元(子の名の頭が <paramref name="prefixes"/> の駒)の、**駒の下端から <paramref name="band"/> までの実メッシュ**の平面の外形(凸包・世界 XZ)を駒ごとに返す
    /// (束石の外形 = 縁束の駒の下の帯 ── 縁束・縁桁の上の部を外形に入れない)。当たる先: 桝・溝と束石の離れ(土井 D1 toriai)。</summary>
    public static List<List<Vector2>> FootHullsXZ(Transform mune, string[] prefixes, float band)
    {
        var res = new List<List<Vector2>>(); if (mune == null) return res;
        foreach (var tr in mune.GetComponentsInChildren<Transform>())
        {
            bool hit = false; foreach (var p in prefixes) if (tr.name.StartsWith(p)) { hit = true; break; }
            if (!hit || !tr.gameObject.activeInHierarchy) continue;
            var pts = Body(tr, 4000, false); if (pts.Count < 3) continue;
            float y0 = float.MaxValue; foreach (var p in pts) y0 = Mathf.Min(y0, p.y);
            var xz = new List<Vector2>(); foreach (var p in pts) if (p.y <= y0 + band) xz.Add(new Vector2(p.x, p.z));
            var h = ConvexHull2(xz); if (h.Count >= 3) res.Add(h);
        }
        return res;
    }

    /// <summary>二つの凸多角形(XZ)の離れ[m](重なれば負 ── 値は −0.001 の印)。当たる先: 桝・溝と束石の離れ。</summary>
    public static float HullGapXZ(List<Vector2> a, List<Vector2> b)
    {
        if (a == null || b == null || a.Count < 3 || b.Count < 3) return float.NaN;
        if (ConvexOverlap(a, b, 0f)) return -0.001f;
        var la = new List<Vector2>(a) { a[0] }; var lb = new List<Vector2>(b) { b[0] };
        float best = float.MaxValue;
        foreach (var p in a) best = Mathf.Min(best, Vector2.Distance(p, ClosestOn(lb, p)));
        foreach (var q in b) best = Mathf.Min(best, Vector2.Distance(q, ClosestOn(la, q)));
        return best;
    }

    /// <summary>線を、点 <paramref name="c"/> から半径 <paramref name="r"/> の円に初めて入る所で切る(桝へ入る溝の尻を桝の外の面で止める ──
    /// 溝の駒が桝の窪みの上へ張り出さない)。円は桝の外形に内接するので、どの向きから入っても尻は桝の壁の中に止まり、隙は開かない。
    /// 切った長さが <paramref name="minLen"/> に満たなければ元の線を返す。当たる先: 桝へ入る溝の全部(土井 S9 の D1・D2・D11)。</summary>
    public static List<Vector2> TrimLineAtCircle(List<Vector2> pl, Vector2 c, float r, float minLen, out float cut)
    {
        cut = 0f; float L = PolylineLength(pl); if (L < 1e-3f || r <= 0f) return pl;
        float sIn = float.NaN;
        for (float s = 0f; s <= L + 1e-4f; s += 0.02f) { Vector2 d; var q = PointAt(pl, Mathf.Min(s, L), out d); if ((q - c).magnitude <= r) { sIn = Mathf.Min(s, L); break; } }
        if (float.IsNaN(sIn) || sIn < minLen) return pl;
        cut = L - sIn;
        return cut > 1e-3f ? SubPolyline(pl, 0f, sIn) : pl;
    }

    /// <summary>**線の頭を他の溝の駒の外形の外で止める**(頭の駒が、既に据わった別の系統の溝の窪みの上へ張り出して浮かない)。
    /// 頭の断面(芯と両縁 ±<paramref name="halfW"/> の 5 点)が <paramref name="hulls"/> のどれかの中にある間、頭を 0.02m ずつ下流へ送り、
    /// 断面が全部外へ出た所で切る。切る長さが <paramref name="maxCut"/> を超える(= 頭の出合いではなく並走の重なり)か、残りが <paramref name="minLeft"/> に
    /// 満たないなら切らない(元の線を返す)。
    /// ⭐ 2026-10-05 EDO-0533 第11巡: 奥の軒先の雨落ち D2 seg1 線3 の頭と D3 seg1 線3 の頭が奥の同じ隅から出て、D2 の頭の駒(底 26.93)が D3 の頭の駒の窪みの上に
    /// 0.28 浮き、頭の小口の下が 0.24 覗いた(皮の隙)。当たる先: 土井 S9 の溝の全系統の線の頭(同じ系統の線どうし ── 二手に分けた線の頭 ── は呼び手が外す)。</summary>
    public static List<Vector2> TrimHeadOutOfHulls(List<Vector2> pl, IList<Vector2[]> hulls, float halfW, float maxCut, float minLeft, out float cut)
    {
        cut = 0f; float L = PolylineLength(pl); if (L < 1e-3f || hulls == null || hulls.Count == 0) return pl;
        Func<float, bool> inside = sq =>
        {
            Vector2 d; var q = PointAt(pl, sq, out d); if (d.sqrMagnitude < 1e-8f) d = Vector2.up; d.Normalize(); var n = new Vector2(-d.y, d.x);
            foreach (float k in new[] { -1f, -0.5f, 0f, 0.5f, 1f }) { var p = q + n * (halfW * k); foreach (var h in hulls) if (h != null && h.Length >= 3 && EdoGeom.PIP(h, p)) return true; }
            return false;
        };
        if (!inside(0f)) return pl;
        float sOut = float.NaN;
        for (float sq = 0.02f; sq <= Mathf.Min(maxCut, L - minLeft) + 1e-4f; sq += 0.02f) if (!inside(sq)) { sOut = sq; break; }
        if (float.IsNaN(sOut)) return pl;
        cut = sOut; return SubPolyline(pl, sOut, L);
    }

    /// <summary>**面の取り合いで解いた桝の内法の窪み**(世界 XZ の矩形 ── 局所 x, z ∈ [−a, a]・a = 内法の半分)。桝の外の面の壁の厚みの内は含めない
    /// (溝の駒が桝の壁へ載るのは部材どうしの重なりで数えない ── oki-kata §0a)。当たる先: <see cref="TrimTailOutOfHull"/>(土井 D1 masu[0])。</summary>
    public static Vector2[] MasuInnerHull(MasuPlan pl, float innerHalf)
    {
        if (pl == null || !pl.ok || innerHalf <= 0f) return null;
        var o = pl.pivot; var x = pl.lat; var z = pl.outDir;
        return new[] { o - x * innerHalf - z * innerHalf, o + x * innerHalf - z * innerHalf, o + x * innerHalf + z * innerHalf, o - x * innerHalf + z * innerHalf };
    }

    /// <summary>**線の尻を、尻の駒が窪み <paramref name="hull"/> の上へ張り出さない所で止める**(硬い ── 溝の駒が桝の窪みの上で浮かない)。
    /// 駒割り(<see cref="MizoPieceSpans"/>)の各駒を<b>弦</b>(P(s0)→P(s1)・幅 2 × <paramref name="halfW"/>)の矩形で引き、どれかが hull と重なる間、尻を 0.01m ずつ上流へ戻す。
    /// 戻す長さが <paramref name="maxCut"/> を超える(= 線が窪みを横切る)か、残りが <paramref name="minLeft"/> に満たないなら切らない(元の線・cut = −1)。
    /// ⭐ 2026-10-05 EDO-0533 第12巡: 面の取り合いで解いた桝(<see cref="MasuPlanOffLine"/>)へ 45° の脚(<see cref="EaveLineToFace"/>)で入る雨落ち D1 seg2・seg4 は、
    /// 尻の小口の芯を桝の側面の中央へ当てるので、斜めの小口の隅が壁(厚み 0.15)を越えて内法の上へ出て、尻の駒が 0.33〜0.53 浮いた(<see cref="TrimLineAtCircle"/> は
    /// 面の取り合いの桝には掛けていなかった)。⇒ 窪みの矩形と駒の弦の矩形の重なりで止める(円でなく ── 斜めに入る小口の隅を測る)。
    /// 当たる先: 面の中央で止める線の全て(土井 D1 seg2・seg3・seg4)。以後、斜めに桝・吐口へ入る溝の全て。</summary>
    public static List<Vector2> TrimTailOutOfHull(List<Vector2> pl, Vector2[] hull, float halfW, float pieceLen, float maxCut, float minLeft, out float cut)
    {
        cut = 0f; float L = PolylineLength(pl); if (L < 1e-3f || hull == null || hull.Length < 3) return pl;
        var hl = new List<Vector2>(hull);
        Func<List<Vector2>, bool> over = line =>
        {
            float LL = PolylineLength(line);
            foreach (var sp in MizoPieceSpans(LL, pieceLen))
            {
                if (sp.y < LL - 2f * pieceLen - 1e-3f) continue;   // 尻から 2 駒より上流は窪みに届かない
                Vector2 dd; var a = PointAt(line, sp.x, out dd); var b = PointAt(line, sp.y, out dd);
                var d = b - a; if (d.sqrMagnitude < 1e-8f) continue; d.Normalize(); var n = new Vector2(-d.y, d.x);
                var rect = new List<Vector2> { a - n * halfW, b - n * halfW, b + n * halfW, a + n * halfW };
                if (ConvexOverlap(rect, hl, 0.005f)) return true;
            }
            return false;
        };
        if (!over(pl)) return pl;
        for (float c = 0.01f; c <= maxCut + 1e-4f && L - c >= minLeft; c += 0.01f)
        {
            var t = SubPolyline(pl, 0f, L - c);
            if (!over(t)) { cut = c; return t; }
        }
        cut = -1f; return pl;
    }

    /// <summary>坂の頭へ水切り石を据える。平面 = 坂の頭の縁から下へ <paramref name="inset"/> の線の中ほど・坂の軸に対して skew 度振る
    /// (振る向き = 坂の脇のうち地盤の低い側)。高さ = 石の**下端**を足元の地盤の最低 − 埋め(石の丈 − topAbove)。
    /// 当たる先: 型 O(D8 の R_Tsuyomon・R_Tomomachi の頭)。</summary>
    public static GameObject PlaceMizukiri(Transform parent, string name, string path, Vector2 headMid, Vector2 downDir, float skewDeg, float topAbove, Func<float, float, float> groundAt, out string note)
    {
        note = null; var mp = MizoPieceOf(path); if (!mp.ok) { note = "石が測れない"; return null; }
        var side = new Vector2(-downDir.y, downDir.x);
        float gl = groundAt(headMid.x + side.x, headMid.y + side.y), gr = groundAt(headMid.x - side.x, headMid.y - side.y);
        if (gr < gl) side = -side;   // 低い側へ
        float r = (90f - skewDeg) * Mathf.Deg2Rad;
        var along = (side * Mathf.Cos(r) + downDir * Mathf.Sin(r)).normalized;   // 石の長さの向き(局所 X)
        float yaw = Mathf.Atan2(-along.y, along.x) * Mathf.Rad2Deg;
        var go = Place(path, new Vector3(headMid.x, 0f, headMid.y), yaw, Vector3.one, parent, name);
        float half = 0.5f * (mp.xMax - mp.xMin), gmin = float.MaxValue, gmax = float.MinValue;
        for (int i = -4; i <= 4; i++) { var q = headMid + along * (half * i / 4f); float g = groundAt(q.x, q.y); gmin = Mathf.Min(gmin, g); gmax = Mathf.Max(gmax, g); }
        float yb = go.transform.TransformPoint(new Vector3(0f, mp.bottom, 0f)).y;
        // 天端 = 地盤の最高 + topAbove(石の天端が坂の面より上に出て水を切る)・下端は丈なりに埋まる
        float topY = gmax + topAbove, want = topY - (mp.top - mp.bottom);
        go.transform.position += new Vector3(0f, want - yb, 0f);
        note = "天端 " + topY.ToString("F2") + "(足元の地盤 " + gmin.ToString("F2") + "〜" + gmax.ToString("F2") + " + " + topAbove.ToString("F2") + ")・下端 " + want.ToString("F2") + (want > gmin ? " ⚠ 下端が足元の最低より " + (want - gmin).ToString("F2") + "m 浮く(石の丈が坂の横の落差に足りない)" : "");
        return go;
    }

    // ================================================================ 線の型 N1〜N10(相手の名で書いた線 ── 普請方の設計 2026-10-04・EDO-0533)
    //   どれも**建った物を測って**引く。引けなければ null と理由を返す(呼び手は Wait に名乗って据えない ── ⛔ 座標を発明しない)。

    /// <summary>折れ線の弧長 [s0, s1] の部分(s0 &gt; s1 なら逆向き)。当たる先: 帯の縁・門の背の線を区間で切る(土井 S9 の N5・N7)。</summary>
    public static List<Vector2> SubPolyline(List<Vector2> pl, float s0, float s1)
    {
        bool rev = s0 > s1; float a = Mathf.Min(s0, s1), b = Mathf.Max(s0, s1);
        var res = new List<Vector2>(); Vector2 d;
        res.Add(PointAt(pl, a, out d));
        float acc = 0f;
        for (int i = 0; i + 1 < pl.Count; i++) { acc += Vector2.Distance(pl[i], pl[i + 1]); if (acc > a + 1e-4f && acc < b - 1e-4f) res.Add(pl[i + 1]); }
        res.Add(PointAt(pl, b, out d));
        if (rev) res.Reverse();
        return res;
    }

    /// <summary>多角形の面積の重心(退化していれば頂点の平均)。当たる先: 「<相手>側」の相手の芯(N2)。</summary>
    public static Vector2 PolyCentroid(Vector2[] poly)
    {
        double a = 0, cx = 0, cz = 0; int n = poly.Length;
        for (int i = 0; i < n; i++) { var p = poly[i]; var q = poly[(i + 1) % n]; double c = p.x * q.y - q.x * p.y; a += c; cx += (p.x + q.x) * c; cz += (p.y + q.y) * c; }
        if (Math.Abs(a) < 1e-6) { var m = Vector2.zero; foreach (var p in poly) m += p; return m / Mathf.Max(1, n); }
        return new Vector2((float)(cx / (3 * a)), (float)(cz / (3 * a)));
    }

    /// <summary>点に最も近い折れ線の上の点(1 点だけの線はその点)。</summary>
    public static Vector2 ClosestOn(List<Vector2> pl, Vector2 p)
    {
        if (pl.Count == 1) return pl[0];
        float best = float.MaxValue; Vector2 bp = pl[0];
        for (int i = 0; i + 1 < pl.Count; i++)
        {
            Vector2 a = pl[i], b = pl[i + 1], ab = b - a; float l2 = ab.sqrMagnitude;
            float t = l2 < 1e-10f ? 0f : Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2); var q = a + ab * t; float d = (q - p).sqrMagnitude;
            if (d < best) { best = d; bp = q; }
        }
        return bp;
    }

    static List<Vector2> SubtractIntervals(float lo, float hi, List<Vector2> cuts)
    {
        var res = new List<Vector2> { new Vector2(lo, hi) };
        foreach (var c in cuts)
        {
            var nx = new List<Vector2>();
            foreach (var r in res)
            {
                if (c.y <= r.x || c.x >= r.y) { nx.Add(r); continue; }
                if (c.x > r.x) nx.Add(new Vector2(r.x, c.x));
                if (c.y < r.y) nx.Add(new Vector2(c.y, r.y));
            }
            res = nx;
        }
        return res;
    }

    /// <summary>線分の列を、端どうしが tol 内で継がる所でつないだ折れ線の列(輪になれば最初の点を最後にも置く)。</summary>
    public static List<List<Vector2>> ChainSegments(List<Vector2[]> segs, float tol)
    {
        var res = new List<List<Vector2>>(); var used = new bool[segs.Count]; float t2 = tol * tol;
        for (int s = 0; s < segs.Count; s++)
        {
            if (used[s]) continue; used[s] = true;
            var pl = new List<Vector2> { segs[s][0], segs[s][1] };
            for (int side = 0; side < 2; side++)
            {
                bool grew = true;
                while (grew)
                {
                    grew = false; var end = side == 0 ? pl[pl.Count - 1] : pl[0];
                    for (int k = 0; k < segs.Count; k++)
                    {
                        if (used[k]) continue;
                        Vector2 nxt; if ((segs[k][0] - end).sqrMagnitude <= t2) nxt = segs[k][1]; else if ((segs[k][1] - end).sqrMagnitude <= t2) nxt = segs[k][0]; else continue;
                        used[k] = true; grew = true; if (side == 0) pl.Add(nxt); else pl.Insert(0, nxt); break;
                    }
                }
            }
            res.Add(pl);
        }
        return res;
    }

    /// <summary>**N1 列べた棟の軒の外周 ── 除く棟の軒の下を除く**: 軒の矩形(<see cref="EaveRect"/>・同じ軸 <paramref name="ax"/> で測った物)を合わせた外形の辺を、
    /// 区間の数え(他の矩形に覆われる所・同じ向きで重なる辺の二つ目を外す)で正確に切り出し、除く棟の軒の矩形に入る区間を切り取って、継がる所でつないだ開いた線の列。
    /// 当たる先: 御殿の連なりの雨落ち(土井 D2 seg1 の玄関・広間・台所)・棟を列べて軒の外周に溝を回す邸の御殿群。</summary>
    public static List<List<Vector2>> EaveUnionOutline(IList<Vector2[]> rects, IList<Vector2[]> exclude, Vector2 ax, out string why)
    {
        why = null; ax = ax.normalized; var ay = new Vector2(-ax.y, ax.x);
        Func<Vector2[], Vector4> box = r =>
        {
            float a0 = float.MaxValue, a1 = float.MinValue, b0 = float.MaxValue, b1 = float.MinValue;
            foreach (var p in r) { float a = Vector2.Dot(p, ax), b = Vector2.Dot(p, ay); a0 = Mathf.Min(a0, a); a1 = Mathf.Max(a1, a); b0 = Mathf.Min(b0, b); b1 = Mathf.Max(b1, b); }
            return new Vector4(a0, a1, b0, b1);
        };
        var B = new List<Vector4>(); foreach (var r in rects) B.Add(box(r));
        var X = new List<Vector4>(); if (exclude != null) foreach (var r in exclude) X.Add(box(r));
        // 軸に揃っているか(矩形の各頂点が a・b の端のどちらかに載る)
        for (int i = 0; i < rects.Count; i++)
            foreach (var p in rects[i])
            {
                float a = Vector2.Dot(p, ax), b = Vector2.Dot(p, ay);
                if (Mathf.Min(Mathf.Abs(a - B[i].x), Mathf.Abs(a - B[i].y)) > 0.02f || Mathf.Min(Mathf.Abs(b - B[i].z), Mathf.Abs(b - B[i].w)) > 0.02f) { why = "軒の矩形の軸が揃っていない ── 外周を合わせられない"; return null; }
            }
        const float eps = 0.01f;
        var frags = new List<Vector2[]>();
        for (int i = 0; i < B.Count; i++)
        {
            var bi = B[i];
            for (int e = 0; e < 4; e++)
            {
                bool horiz = e < 2; float sgn = (e % 2 == 0) ? -1f : 1f;
                float c = horiz ? (sgn < 0 ? bi.z : bi.w) : (sgn < 0 ? bi.x : bi.y);
                float lo = horiz ? bi.x : bi.z, hi = horiz ? bi.y : bi.w;
                var cuts = new List<Vector2>();
                for (int j = 0; j < B.Count; j++)
                {
                    if (j == i) continue; var bj = B[j];
                    float jlo = horiz ? bj.z : bj.x, jhi = horiz ? bj.w : bj.y, c2 = c + sgn * eps;
                    float jr0 = horiz ? bj.x : bj.z, jr1 = horiz ? bj.y : bj.w;
                    if (c2 > jlo && c2 < jhi) cuts.Add(new Vector2(jr0, jr1));                                    // 外が他の矩形に覆われる = 内の辺
                    else if (j < i && Mathf.Abs(c - (sgn > 0 ? jhi : jlo)) < eps) cuts.Add(new Vector2(jr0, jr1)); // 同じ向きで重なる辺は一つだけ
                }
                foreach (var xj in X)
                {
                    float xlo = horiz ? xj.z : xj.x, xhi = horiz ? xj.w : xj.y;
                    if (c >= xlo - eps && c <= xhi + eps) cuts.Add(horiz ? new Vector2(xj.x, xj.y) : new Vector2(xj.z, xj.w));
                }
                foreach (var iv in SubtractIntervals(lo, hi, cuts))
                {
                    if (iv.y - iv.x < 0.05f) continue;
                    Vector2 p0 = horiz ? ax * iv.x + ay * c : ax * c + ay * iv.x, p1 = horiz ? ax * iv.y + ay * c : ax * c + ay * iv.y;
                    frags.Add(new[] { p0, p1 });
                }
            }
        }
        if (frags.Count == 0) { why = "外周が全部除く棟の軒の下に入る"; return null; }
        return ChainSegments(frags, 0.02f);
    }

    /// <summary>**N2 棟の <相手>側の軒先**: 矩形(軒の外周)の 4 辺のうち、棟の芯から相手の芯(多角形の重心)へ向く方向に最も向く辺。
    /// cos &lt; <paramref name="minDot"/> なら向きが決まらない(null)。相手は面・庭・坂の多角形、棟なら軒の矩形を呼び手が渡す。
    /// 当たる先: 奥の広間側・土蔵側の雨落ち(土井 D2 seg1)・供待の坂側(D9 seg4)── 「<棟> の <相手id> 側」の雨落ちすべて。</summary>
    public static List<Vector2> RectSideTowardTarget(Vector2[] rect, Vector2[] target, float minDot, out float dot, out string why)
    {
        why = null; dot = -2f;
        if (rect == null || target == null || target.Length == 0) { why = "棟か相手が無い"; return null; }
        var c = 0.5f * (rect[0] + rect[2]); var tc = target.Length >= 3 ? PolyCentroid(target) : target[0];
        if ((tc - c).sqrMagnitude < 1e-6f) { why = "相手の芯が棟の芯と同じ"; return null; }
        var side = RectSideToward(rect, tc - c, out dot);
        if (dot < minDot) { why = "相手の芯への向きに辺が向かない(cos " + dot.ToString("F2") + " < " + minDot.ToString("F2") + ")"; return null; }
        return side;
    }

    /// <summary>**N3 面の縁のうち相手に向く一続き**: 多角形の各辺について、外の 0.5m が相手の内に入るか、辺の中点から相手の最寄りの点への向きと外向きの法線の
    /// cos ≥ <paramref name="minDot"/> なら「向く」。続いている辺を一続きにつなぎ、相手に最も近い一続きを返す(次の一続きとの差が 0.5m 未満なら決まらない)。
    /// <paramref name="outward"/> = 一続きの最初の辺の外向き。当たる先: 台地の縁の前庭の溝(土井 D2 seg4)・谷頭の崖の法尻(D10 seg2)・稲荷の座の外(D13 seg2)。</summary>
    public static List<Vector2> PolyEdgesFacingTarget(Vector2[] poly, Vector2[] target, float minDot, out Vector2 outward, out string why)
    {
        outward = Vector2.zero; why = null; int n = poly.Length;
        if (n < 3 || target == null || target.Length < 3) { why = "面か相手の多角形が無い"; return null; }
        var tl = new List<Vector2>(target); tl.Add(target[0]);
        var sel = new bool[n];
        for (int i = 0; i < n; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % n], m = 0.5f * (a + b), on = -EdoGeom.InwardNormal(poly, i);
            if (EdoGeom.PIP(target, m + on * 0.5f)) { sel[i] = true; continue; }
            var q = ClosestOn(tl, m); var d = q - m; if (d.sqrMagnitude < 1e-6f) { sel[i] = true; continue; }
            sel[i] = Vector2.Dot(d.normalized, on) >= minDot;
        }
        var chains = new List<KeyValuePair<List<Vector2>, int>>();
        int start = -1; for (int i = 0; i < n; i++) if (!sel[i]) { start = i; break; }
        if (start < 0) { why = "全周が相手に向く ── 一続きに切れない"; return null; }
        List<Vector2> cur = null;
        for (int k = 1; k <= n; k++)
        {
            int i = (start + k) % n;
            if (sel[i]) { if (cur == null) { cur = new List<Vector2> { poly[i] }; chains.Add(new KeyValuePair<List<Vector2>, int>(cur, i)); } cur.Add(poly[(i + 1) % n]); }
            else cur = null;
        }
        if (chains.Count == 0) { why = "相手に向く縁が無い"; return null; }
        float best = float.MaxValue, second = float.MaxValue; int bi = -1;
        for (int c = 0; c < chains.Count; c++)
        {
            float dmin = float.MaxValue;
            foreach (var p in chains[c].Key) { float dd = EdoGeom.PIP(target, p) ? 0f : Vector2.Distance(p, ClosestOn(tl, p)); dmin = Mathf.Min(dmin, dd); }
            for (int i = 0; i + 1 < chains[c].Key.Count; i++) { var m = 0.5f * (chains[c].Key[i] + chains[c].Key[i + 1]); float dd = EdoGeom.PIP(target, m) ? 0f : Vector2.Distance(m, ClosestOn(tl, m)); dmin = Mathf.Min(dmin, dd); }
            if (dmin < best) { second = best; best = dmin; bi = c; } else if (dmin < second) second = dmin;
        }
        if (second - best < 0.5f) { why = "相手に向く一続きが " + chains.Count + " 本あり近さが拮抗(" + best.ToString("F2") + " / " + second.ToString("F2") + "m)── 一本に決まらない"; return null; }
        outward = -EdoGeom.InwardNormal(poly, chains[bi].Value);
        return chains[bi].Key;
    }

    /// <summary>**N4 長屋の内の軒先**: 軒の矩形(<see cref="EaveRect"/>・軸 = 走りの向き)の 4 辺のうち、区画の線 a–b から最も遠い辺(= 区画の線と反対の側)。
    /// 当たる先: 北の境の長屋の内の雨落ち(土井 D2 seg3)・境に建つ長屋の内の雨落ちすべて。</summary>
    public static List<Vector2> EaveSideAwayFromLine(Vector2[] rect, Vector2 a, Vector2 b)
    {
        int best = 0; float far = float.MinValue;
        for (int i = 0; i < 4; i++) { var m = 0.5f * (rect[i] + rect[(i + 1) % 4]); float d = EdoGeom.DistToEdge(m, a, b); if (d > far) { far = d; best = i; } }
        return new List<Vector2> { rect[best], rect[(best + 1) % 4] };
    }

    /// <summary>**直線の列を一続きに**: 並べた順に向きを揃え(前の尻に近い端を次の頭に)、<paramref name="cornerDeg"/> 以上折れる所は二直線の交点で折り(入隅・出隅)、
    /// 平行に近い所は尻から頭へそのまま継ぐ。当たる先: 長屋の内面・内の軒先の線(N4・N8 ── 表長屋・北の境の長屋の連なり)。</summary>
    public static List<Vector2> ChainStraights(List<List<Vector2>> parts, float cornerDeg)
    {
        var P = new List<Vector2[]>();
        foreach (var p in parts) if (p != null && p.Count >= 2) P.Add(new[] { p[0], p[p.Count - 1] });
        if (P.Count == 0) return null;
        if (P.Count > 1)
        {
            float dEnd = Mathf.Min((P[0][1] - P[1][0]).sqrMagnitude, (P[0][1] - P[1][1]).sqrMagnitude), dSt = Mathf.Min((P[0][0] - P[1][0]).sqrMagnitude, (P[0][0] - P[1][1]).sqrMagnitude);
            if (dSt < dEnd) P[0] = new[] { P[0][1], P[0][0] };
        }
        var res = new List<Vector2> { P[0][0], P[0][1] };
        for (int i = 1; i < P.Count; i++)
        {
            var pb = res[res.Count - 1]; var pa = res[res.Count - 2];
            Vector2 a = P[i][0], b = P[i][1]; if ((b - pb).sqrMagnitude < (a - pb).sqrMagnitude) { var t = a; a = b; b = t; }
            Vector2 d0 = (pb - pa).normalized, d1 = (b - a).normalized;
            if (Vector2.Angle(d0, d1) >= cornerDeg)
            {
                var x = EdoGeom.LineIntersect(pa, d0, a, d1, pb);
                if ((x - pb).magnitude < 5f && (x - a).magnitude < 5f) { res[res.Count - 1] = x; res.Add(b); continue; }
            }
            if ((a - pb).sqrMagnitude > 1e-4f) res.Add(a);
            res.Add(b);
        }
        return res;
    }

    /// <summary>**N8 長屋・塀の面(一直線)**: 駒の実メッシュの、駒ごとの足元から [yLo, yHi] の帯で <paramref name="towardPoint"/> の側へ最も出た所(実際に触れる面)を、
    /// 走りの向きの一直線(2 点)にする。当たる先: 表長屋の内面からの溝(土井 D7 seg1・D9 seg3)・塀の内面へ下ろす段落ち(D10 seg4)・門の背の面(N7)。</summary>
    public static List<Vector2> FaceStraight(IList<GameObject> pieces, Vector2 towardPoint, float yLo, float yHi, out Vector2 normal, out string why)
    {
        var fl = WallFaceLine(pieces, towardPoint, yLo, yHi, 0.5f, out normal, out why);
        if (fl == null) return null;
        var t = new Vector2(normal.y, -normal.x); var o = fl[0];
        float s0 = float.MaxValue, s1 = float.MinValue, off = float.MinValue;
        foreach (var q in fl) { float s = Vector2.Dot(q - o, t); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); off = Mathf.Max(off, Vector2.Dot(q - o, normal)); }
        return new List<Vector2> { o + t * s0 + normal * off, o + t * s1 + normal * off };
    }

    /// <summary>折れ線の端を接線の向きへ延ばし、相手の線の列(<paramref name="infinite"/> なら各区間を無限の直線として)に当てる。
    /// 延ばす端 = <paramref name="near"/> に近い端。maxExt を超えて当たらなければ false(線は変えない)。
    /// 当たる先: N3「<区間> まで延ばす」(土井 D13 seg2)・N8「<長屋> の内面まで延ばして止める」(D7 seg1)。</summary>
    public static bool ExtendEndTo(List<Vector2> pl, Vector2 near, List<List<Vector2>> targets, bool infinite, float maxExt, out float ext)
    {
        ext = float.NaN; if (pl == null || pl.Count < 2 || targets == null) return false;
        bool atStart = (pl[0] - near).sqrMagnitude < (pl[pl.Count - 1] - near).sqrMagnitude;
        Vector2 e = atStart ? pl[0] : pl[pl.Count - 1], dir = (atStart ? pl[0] - pl[1] : pl[pl.Count - 1] - pl[pl.Count - 2]).normalized;
        float best = float.MaxValue;
        foreach (var tl in targets)
            for (int i = 0; tl != null && i + 1 < tl.Count; i++)
            {
                Vector2 q = tl[i], s = tl[i + 1] - tl[i];
                float den = dir.x * s.y - dir.y * s.x; if (Mathf.Abs(den) < 1e-6f) continue;
                Vector2 qp = q - e; float t = (qp.x * s.y - qp.y * s.x) / den, u = (qp.x * dir.y - qp.y * dir.x) / den;
                if (!infinite && (u < -1e-4f || u > 1f + 1e-4f)) continue;
                if (t < -0.05f || t > maxExt) continue;
                best = Mathf.Min(best, t);
            }
        if (best == float.MaxValue) return false;
        ext = best; var hit = e + dir * best;
        if (best > 0.01f) { if (atStart) pl.Insert(0, hit); else pl.Add(hit); }
        else { if (atStart) pl[0] = hit; else pl[pl.Count - 1] = hit; }
        return true;
    }

    /// <summary>帯(土の坂)の測り。center = 芯の折れ線(世界)・hi/lo = 地盤の高い側・低い側の縁・poly = 帯の多角形・headAtEnd = 芯の終わりの端が頭(地盤の高い端)。</summary>
    public class Band { public List<Vector2> center, hi, lo; public Vector2[] poly; public float halfW; public int hiSign = 1; public bool headAtEnd, sideKnown; public string why; }
    /// <summary>**帯(坂)**: 芯と半幅から両縁と多角形を引き、地盤の高い側(縁の外 1.5m の地盤を全長で平均)と頭(芯の地盤の高い端)を測る。
    /// <paramref name="groundAt"/> が null なら多角形だけ。当たる先: 土の坂の脇の溝・坂の足の横断(土井 D2 seg6・seg8 の R_OmoteSaka)・坂を相手にした線(N2・N3)。</summary>
    public static Band BandOf(List<Vector2> center, float halfW, Func<float, float, float> groundAt)
    {
        var b = new Band { center = center, halfW = halfW };
        var t0 = (center[1] - center[0]).normalized; var l0 = new Vector2(-t0.y, t0.x);
        var left = OffsetPolyline(center, halfW, l0); var right = OffsetPolyline(center, halfW, -l0);
        var poly = new List<Vector2>(left); for (int i = right.Count - 1; i >= 0; i--) poly.Add(right[i]); b.poly = poly.ToArray();
        b.hi = left; b.lo = right;
        if (groundAt == null) return b;
        var lo2 = OffsetPolyline(center, halfW + 1.5f, l0); var ro2 = OffsetPolyline(center, halfW + 1.5f, -l0);
        double sl = 0, sr = 0; int nl = 0, nr = 0;
        float L = PolylineLength(center);
        for (float s = 0f; s <= L; s += 0.5f)
        {
            Vector2 d; float g1 = groundAt(PointAt(lo2, s, out d).x, PointAt(lo2, s, out d).y), g2 = groundAt(PointAt(ro2, s, out d).x, PointAt(ro2, s, out d).y);
            if (!float.IsNaN(g1)) { sl += g1; nl++; }
            if (!float.IsNaN(g2)) { sr += g2; nr++; }
        }
        if (nl == 0 || nr == 0) { b.why = "帯の脇の地盤が引けない"; return b; }
        b.sideKnown = true;
        if (sr / nr > sl / nl) { b.hi = right; b.lo = left; b.hiSign = -1; }
        float gs = groundAt(center[0].x, center[0].y), ge = groundAt(center[center.Count - 1].x, center[center.Count - 1].y);
        b.headAtEnd = ge > gs;
        return b;
    }

    /// <summary>**N5 坂の帯の高い側の縁 ── 頭から相手の駒の端まで**: 帯の高い側の縁を、頭(地盤の高い端)から、相手の駒(実メッシュ)を縁へ写した区間の
    /// 頭に近い端まで切る(相手は縁から 6m 内の頂点だけを数える)。当たる先: 土井 D2 seg8(R_OmoteSaka の切の法尻 ── 頭から石垣 TW_Shiro_KitaNagaya の端まで)。</summary>
    public static List<Vector2> BandHighEdgeToPieces(Band b, IList<GameObject> pieces, out string why)
    {
        why = null;
        if (!b.sideKnown) { why = b.why ?? "帯の高い側が測れない"; return null; }
        float L = PolylineLength(b.hi), smin = float.MaxValue, smax = float.MinValue; int n = 0;
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            foreach (var p in Body(g.transform, 4000, false)) { float dd; float s = NearestS(b.hi, new Vector2(p.x, p.z), out dd); if (dd > 6f) continue; smin = Mathf.Min(smin, s); smax = Mathf.Max(smax, s); n++; }
        }
        if (n == 0) { why = "相手の駒が帯の高い側の縁から 6m 内に無い"; return null; }
        float sHead = b.headAtEnd ? L : 0f, sEnd = b.headAtEnd ? smax : smin;
        if (Mathf.Abs(sHead - sEnd) < 0.3f) { why = "相手の駒が頭まで掛かる ── 頭からの区間が無い"; return null; }
        return SubPolyline(b.hi, sHead, sEnd);
    }

    /// <summary>**N6 坂の足の横断**: 芯を足(低い端)から辿り、芯の地盤が面の高さ <paramref name="faceY"/>(± tol)に載った後に離れる点で、帯に直交に横切る線(低い側の縁 → 高い側)。
    /// 高い側は相手の線(<paramref name="hiTo"/>)に当たるまで(maxReach まで)・低い側は帯の縁まで。当たる先: 土井 D2 seg6(R_OmoteSaka の足 ↔ 面 MonNoUchi・高い側は D2 seg5)。</summary>
    public static List<Vector2> BandFootCross(Band b, Func<float, float, float> groundAt, float faceY, float tol, List<List<Vector2>> hiTo, float maxReach, out string why)
    {
        why = null;
        if (!b.sideKnown) { why = b.why ?? "帯の高い側が測れない"; return null; }
        float L = PolylineLength(b.center); bool seen = false; float sLeave = float.NaN, prev = float.NaN;
        for (float k = 0f; k <= L + 1e-3f; k += 0.25f)
        {
            float s = b.headAtEnd ? k : L - k; Vector2 d; var q = PointAt(b.center, s, out d); float g = groundAt(q.x, q.y);
            if (float.IsNaN(g)) continue;
            if (Mathf.Abs(g - faceY) <= tol) seen = true;
            else if (seen && g > faceY + tol) { sLeave = prev; break; }
            prev = s;
        }
        if (!seen) { why = "芯の地盤が面の高さ " + faceY.ToString("F2") + " に載る所が無い"; return null; }
        if (float.IsNaN(sLeave)) { why = "芯の地盤が面の高さを離れない(頭まで面の高さ)"; return null; }
        Vector2 dir; var c = PointAt(b.center, sLeave, out dir);
        var nHi = new Vector2(-dir.y, dir.x) * b.hiSign;
        var low = c - nHi * b.halfW;
        float best = float.MaxValue;
        foreach (var tl in hiTo ?? new List<List<Vector2>>())
            for (int i = 0; tl != null && i + 1 < tl.Count; i++)
            {
                Vector2 q = tl[i], s = tl[i + 1] - tl[i]; float den = nHi.x * s.y - nHi.y * s.x; if (Mathf.Abs(den) < 1e-6f) continue;
                Vector2 qp = q - c; float t = (qp.x * s.y - qp.y * s.x) / den, u = (qp.x * nHi.y - qp.y * nHi.x) / den;
                if (u < -1e-4f || u > 1f + 1e-4f || t <= 0f || t > maxReach) continue; best = Mathf.Min(best, t);
            }
        if (best == float.MaxValue) { why = "足の点から高い側へ " + maxReach.ToString("F0") + "m 内に相手の線が無い"; return null; }
        return new List<Vector2> { low, c + nHi * best };
    }

    /// <summary>**N7 長屋門の扉口の番所側の脇柱**: 札の通り口(passage・潜戸まで一つの札なら潜戸の反対の端から扉の幅 <paramref name="leafW"/>)の、潜戸の側(= 片番所の側)の端の世界の点と、
    /// そこから外(番所の側)へ向く単位ベクトル。札が無ければ実メッシュの断面から測る(EdoPartSpec.Measure)。当たる先: 土井の表門(D2 seg7 の尻)・片番所の長屋門すべて。</summary>
    public static bool GateDoorJambBansho(GameObject gate, float leafW, out Vector2 jamb, out Vector2 outward, out string why)
    {
        jamb = outward = Vector2.zero; why = null;
        if (gate == null) { why = "門が建っていない"; return false; }
        var sp = SpecOf(gate);
        if (sp == null) { string note; sp = EdoPartSpec.Measure(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(gate), "gate", 1f, out note); }
        if (sp == null || sp.passage == null) { why = "門の札(通り口)が無い"; return false; }
        if (sp.passageKuguri == null || sp.passageKuguri.x1 - sp.passageKuguri.x0 <= 0.05f) { why = "札に潜戸の口が無い ── 番所の側が決まらない"; return false; }
        float x0 = sp.passage.x0, x1 = sp.passage.x1, kc = 0.5f * (sp.passageKuguri.x0 + sp.passageKuguri.x1);
        bool joined = sp.passageKuguri.x0 >= x0 - 0.01f && sp.passageKuguri.x1 <= x1 + 0.01f;
        bool kHi = kc > 0.5f * (x0 + x1);
        if (joined) { if (float.IsNaN(leafW) || leafW <= 0f) { why = "口が潜戸まで一つの札なのに扉の幅が無い"; return false; } if (kHi) x1 = x0 + leafW; else x0 = x1 - leafW; }
        float xj = kHi ? x1 : x0, sg = kHi ? 1f : -1f;
        jamb = EdoPartSpec.W(gate.transform, xj, 0f);
        outward = (EdoPartSpec.W(gate.transform, xj + sg, 0f) - jamb).normalized;
        return true;
    }

    /// <summary>**N7 門の躯体の背の面からの溝の線**: 門の駒の実メッシュの背の面(足元から [0.1, 1.2] の帯で内の側へ最も出た所・<see cref="FaceStraight"/>)を
    /// <paramref name="off"/> だけ内へずらし、<paramref name="from"/>・<paramref name="to"/> を線へ写した間を返す(from → to)。面の端から外へは maxExt まで延ばす(延ばした量を extUsed に)。
    /// 当たる先: 土井 D2 seg7(表門の背の溝)・長屋門の背に溝を回す邸。</summary>
    public static List<Vector2> GateBackLine(GameObject gate, Vector2 inward, float off, Vector2 from, Vector2 to, float maxExt, out float extUsed, out string why)
    {
        extUsed = 0f; why = null;
        if (gate == null) { why = "門が建っていない"; return null; }
        var c = RB(gate).center; Vector2 nrm;
        var face = FaceStraight(new List<GameObject> { gate }, new Vector2(c.x, c.z) + inward.normalized * 10f, 0.1f, 1.2f, out nrm, out why);
        if (face == null) { why = "門の背の面が測れない(" + why + ")"; return null; }
        var t = (face[1] - face[0]).normalized; var o = face[0] + nrm * off; float len = Vector2.Distance(face[0], face[1]);
        float sf = Vector2.Dot(from - o, t), st = Vector2.Dot(to - o, t);
        extUsed = Mathf.Max(0f, Mathf.Max(-Mathf.Min(sf, st), Mathf.Max(sf, st) - len));
        if (extUsed > maxExt) { why = "区間の端が門の背の面の端から " + extUsed.ToString("F2") + "m 外(上限 " + maxExt.ToString("F1") + ")"; return null; }
        if (Mathf.Abs(st - sf) < 0.3f) { why = "区間の長さが 0.3m に満たない"; return null; }
        return new List<Vector2> { o + t * sf, o + t * st };
    }

    /// <summary>**N9 最短**: 二つの相手(点・折れ線・外形の輪の列)の間の最も近い二点を結ぶ直線(a の側 → b の側)。当たる先: 井戸の流しから溝へ(土井 D7 seg2)・区間の尻から
    /// 次の区間の頭へ(D9 seg2)・塀の内面へ下ろす段落ち(D10 seg4)・吐口から受けへ(D11 seg1)。</summary>
    public static List<Vector2> ShortestLink(List<List<Vector2>> a, List<List<Vector2>> b, out float dist)
    {
        dist = float.MaxValue; Vector2 pa = Vector2.zero, pb = Vector2.zero;
        foreach (var la in a) foreach (var lb in b)
            {
                if (la == null || lb == null || la.Count == 0 || lb.Count == 0) continue;
                foreach (var p in la) { var q = ClosestOn(lb, p); float d = Vector2.Distance(p, q); if (d < dist) { dist = d; pa = p; pb = q; } }
                foreach (var q in lb) { var p = ClosestOn(la, q); float d = Vector2.Distance(p, q); if (d < dist) { dist = d; pa = p; pb = q; } }
            }
        if (dist == float.MaxValue) return null;
        return new List<Vector2> { pa, pb };
    }

    /// <summary>駒の実メッシュの平面の外形(凸包・世界 XZ・閉じた輪)。当たる先: 井戸の駒の外形(N9 の始点 ── 土井 D7 seg2)・据えた受けの足元。</summary>
    public static List<Vector2> HullXZ(GameObject go)
    {
        var pts = new List<Vector2>(); foreach (var p in Body(go.transform, 4000, true)) pts.Add(new Vector2(p.x, p.z));
        if (pts.Count < 3) return null;
        pts.Sort((u, v) => u.x != v.x ? u.x.CompareTo(v.x) : u.y.CompareTo(v.y));
        Func<Vector2, Vector2, Vector2, float> cr = (o, u, v) => (u.x - o.x) * (v.y - o.y) - (u.y - o.y) * (v.x - o.x);
        var h = new List<Vector2>();
        for (int pass = 0; pass < 2; pass++)
        {
            int st = h.Count;
            for (int i = 0; i < pts.Count; i++)
            {
                var p = pass == 0 ? pts[i] : pts[pts.Count - 1 - i];
                while (h.Count >= st + 2 && cr(h[h.Count - 2], h[h.Count - 1], p) <= 0f) h.RemoveAt(h.Count - 1);
                h.Add(p);
            }
            h.RemoveAt(h.Count - 1);
        }
        h.Add(h[0]);
        return h;
    }

    /// <summary>塀の外の地盤: 塀の駒の実メッシュの、内の点 <paramref name="inner"/> から <paramref name="dir"/> の向きの外面を測り、その 0.3m 外の地盤。
    /// 当たる先: 水抜きの口の底 ≥ 道 + d(土井 D10 の練塀 E11_Hei)・塀の外の側溝へ落とす口すべて。</summary>
    public static float GroundBeyondWall(IList<GameObject> pieces, Vector2 inner, Vector2 dir, Func<float, float, float> groundAt, out string why)
    {
        Vector2 n; var face = FaceStraight(pieces, inner + dir.normalized * 10f, 0.1f, 1.2f, out n, out why);
        if (face == null) return float.NaN;
        var q = ClosestOn(face, inner) + n * 0.3f; return groundAt(q.x, q.y);
    }

    // ---------------------------------------------------------------- 段落ち(H)・張り石の落とし(I)・受け(J)
    static void LocalMesh(string path, List<Vector3> V, List<int> T)
    {
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path); if (pf == null) return;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
        go.transform.position = Vector3.zero; go.transform.rotation = Quaternion.identity; go.transform.localScale = Vector3.one;
        try
        {
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue; var m = mf.transform.localToWorldMatrix; int b = V.Count;
                foreach (var v in mf.sharedMesh.vertices) V.Add(m.MultiplyPoint3x4(v));
                foreach (var i in mf.sharedMesh.triangles) T.Add(b + i);
            }
        }
        finally { UnityEngine.Object.DestroyImmediate(go); }
    }

    /// <summary>段の駒の局所の実測: upper = 芯の帯(|x| ≤ 0.12)の上向きの面の最も高い所(段鼻の天端・上の平石の天端)/ lower = 同じく最も低い所(水叩きの天端)/
    /// noseZ = upper の高さの上向きの面の最も下流(+Z)の z(段鼻の線)/ zMin・zMax = 駒の長さの端 / rim = 外形の縁(端から 0.12 内の頂点)の高さの平均(受けの肩の土の皮)。</summary>
    public class StepPiece { public bool ok; public float upper, lower, noseZ, zMin, zMax, xMin, xMax, top, bottom, rim; public float Rise { get { return upper - lower; } } public float Len { get { return zMax - zMin; } } }
    static readonly Dictionary<string, StepPiece> _stepCache = new Dictionary<string, StepPiece>();
    /// <summary>段落ち・張り石の落とし・受けの駒を一度だけ測る。⛔ ピボットを段鼻・天端と見なさない。当たる先: DoiDanOchi・DoiHariOtoshi・DoiTamaUke。</summary>
    public static StepPiece StepPieceOf(string path)
    {
        StepPiece r; if (string.IsNullOrEmpty(path)) return new StepPiece(); if (_stepCache.TryGetValue(path, out r)) return r;
        r = new StepPiece(); var V = new List<Vector3>(); var T = new List<int>(); LocalMesh(path, V, T);
        if (V.Count > 0)
        {
            r.xMin = r.zMin = r.bottom = float.MaxValue; r.xMax = r.zMax = r.top = float.MinValue;
            foreach (var p in V) { r.xMin = Mathf.Min(r.xMin, p.x); r.xMax = Mathf.Max(r.xMax, p.x); r.zMin = Mathf.Min(r.zMin, p.z); r.zMax = Mathf.Max(r.zMax, p.z); r.bottom = Mathf.Min(r.bottom, p.y); r.top = Mathf.Max(r.top, p.y); }
            float band = Mathf.Min(0.12f, 0.25f * (r.xMax - r.xMin));
            var up = new List<Vector3>();
            for (int i = 0; i + 2 < T.Count; i += 3)
            {
                Vector3 a = V[T[i]], b = V[T[i + 1]], c = V[T[i + 2]]; var nv = Vector3.Cross(b - a, c - a); float mag = nv.magnitude;
                if (mag < 1e-9f || nv.y / mag < 0.7f) continue; var cc = (a + b + c) / 3f; if (Mathf.Abs(cc.x) > band) continue; up.Add(cc);
            }
            if (up.Count > 0)
            {
                r.upper = float.MinValue; r.lower = float.MaxValue; foreach (var p in up) { r.upper = Mathf.Max(r.upper, p.y); r.lower = Mathf.Min(r.lower, p.y); }
                r.noseZ = float.MinValue; foreach (var p in up) if (p.y >= r.upper - 0.02f) r.noseZ = Mathf.Max(r.noseZ, p.z);
                double s = 0; int n = 0;
                foreach (var p in V) if (Mathf.Min(Mathf.Min(p.x - r.xMin, r.xMax - p.x), Mathf.Min(p.z - r.zMin, r.zMax - p.z)) <= 0.12f) { s += p.y; n++; }
                r.rim = n > 0 ? (float)(s / n) : r.top;
                r.ok = r.Len > 1e-3f;
            }
        }
        _stepCache[path] = r; return r;
    }

    /// <summary>段落ち・落としの並べ(返り値)。rises = 段ごとの実測の 1段・tailY = 尻の底(段の後の高さ)。
    /// overlap = 踏面が駒より短いときの段の駒どうしの重ねの最大[m](柔・0 = 重ねない)/ headOut = 頭の駒が線の頭より上流へ出る量[m]。</summary>
    public class StepRun { public bool ok = true; public string hard = "", soft = ""; public int steps; public float headY, tailY, pitch, length, overlap, headOut; public List<float> rises = new List<float>(); public List<GameObject> pieces = new List<GameObject>(); }

    static GameObject SeatAt(Transform parent, string path, string name, Vector2 at, float yaw, Vector3 localRef, float y)
    {
        var go = Place(path, new Vector3(at.x, 0f, at.y), yaw, Vector3.one, parent, name);
        if (go == null) return null;
        var w = go.transform.TransformPoint(localRef);
        go.transform.position += new Vector3(at.x - w.x, y - w.y, at.y - w.z);
        return go;
    }

    /// <summary>**型 H 石組の段落ち**を p0(頭)→ p1(尻)の直線に並べる。段数 = <paramref name="steps"/>(0 なら ceil(落差 / riseMax))・1段 = 残りの落差 ÷ 残りの段数 を
    /// 0.05 刻みに切り下げた駒(尻は狙いより下がらない)・踏面 = 平面の長さ ÷ 段数。駒ごとに**駒の実メッシュで測った段鼻の天端と段鼻の線**を段の高さと位置へ当て
    /// (⛔ ピボットで決めない)、踏面の残りは平らな駒(rise 0 ── 実測の溝の底)で埋める(端の駒は引き戻して重ねる)。
    /// 硬: 1段 ≤ riseMax・段鼻の線が守れる(踏面が駒より短いときの重ね ≤ 前の段の駒の水叩きの長さ)・尻の底 ≥ tailMin(NaN なら問わない)── 一つでも破れば何も据えない。
    /// 柔: **踏面 &lt; 駒の長さ**なら次の段の駒を前の段の駒の水叩きへ重ねて据える(部材どうしのめり込みは数えない ── 埋めて隠す・docs/oki-kata.md §4)。
    ///     段鼻は (k+1) × 踏面 の位置・高さのまま。重ね[m]と、頭の駒が線の頭より上流へ出る量を ⚠ と実測で名乗る(<see cref="StepRun.overlap"/>)。
    /// ⛔ 2026-10-05 まで「踏面 ≥ 駒の長さ」を硬い条件にして D9 seg2(踏面 0.43・駒 0.50)を建てなかった ── 重なりは許容0の欠陥ではない(EDO-0533)。
    /// 当たる先: 土井 D9 seg2(小段 → 供待の平場)・D10 seg4(谷頭 → 練塀の水抜き)・D11 seg1(崖の段落ち)── LayDanOchi を呼ぶ所すべて(今は土井だけ)。</summary>
    public static StepRun LayDanOchi(Transform parent, string prefix, Vector2 p0, Vector2 p1, float headY, float tailWant, int steps, float riseMax, float tailMin, Func<float, string> pathOfRise)
    {
        var R = new StepRun { headY = headY };
        float drop = headY - tailWant, L = Vector2.Distance(p0, p1); R.length = L;
        if (drop <= 0.01f) { R.ok = false; R.hard += "落差が無い(頭 " + headY.ToString("F3") + " ≤ 尻の狙い " + tailWant.ToString("F3") + ")・"; return R; }
        if (L < 0.3f) { R.ok = false; R.hard += "平面の長さが 0.3m に満たない・"; return R; }
        if (steps <= 0) steps = Mathf.Max(1, Mathf.CeilToInt(drop / riseMax - 1e-4f));
        R.steps = steps; R.pitch = L / steps;
        var paths = new List<string>(); var sps = new List<StepPiece>(); float rem = drop;
        for (int k = 0; k < steps; k++)
        {
            float want = rem / (steps - k), r = Mathf.Max(0.15f, Mathf.Floor(want / 0.05f + 1e-3f) * 0.05f);
            string path = pathOfRise(r); var sp = StepPieceOf(path);
            if (!sp.ok) { R.ok = false; R.hard += "駒が測れない " + (path ?? "(名が無い)") + "・"; return R; }
            paths.Add(path); sps.Add(sp); R.rises.Add(sp.Rise); rem -= sp.Rise;
            if (sp.Rise > riseMax + 1e-4f) { R.ok = false; R.hard += "1段 " + sp.Rise.ToString("F3") + " > 上限 " + riseMax.ToString("F2") + "・"; }
            // 踏面が駒より短い ── 柔: 次の段の駒を前の段の駒の水叩き(段鼻より下流)へ重ねる。硬: 重ねが前の段の水叩きを越えて段鼻の線に掛かる
            float ov = sp.Len - R.pitch;
            if (ov > 1e-3f)
            {
                R.overlap = Mathf.Max(R.overlap, ov);
                if (k > 0)
                {
                    var pv = sps[k - 1]; float apron = pv.zMax - pv.noseZ;
                    if (ov > apron + 1e-3f) { R.ok = false; R.hard += "段鼻の線が守れない(段 " + k + " の重ね " + ov.ToString("F3") + " > 前の段の駒の水叩き " + apron.ToString("F3") + ")・"; }
                }
                else R.headOut = ov;
            }
        }
        if (R.overlap > 1e-3f)
            R.soft += "踏面 " + R.pitch.ToString("F3") + " < 駒の長さ ── 次の段の駒を前の段の水叩きへ最大 " + R.overlap.ToString("F3") + "m 重ねた(めり込み)"
                    + (R.headOut > 1e-3f ? "・頭の駒は線の頭より " + R.headOut.ToString("F3") + "m 上流へ出る(入る区間の底へ重ねる)" : "") + "・";
        R.tailY = headY - (drop - rem);
        if (!float.IsNaN(tailMin) && R.tailY < tailMin - 1e-4f) { R.ok = false; R.hard += "尻の底 " + R.tailY.ToString("F3") + " < 下限 " + tailMin.ToString("F3") + "・"; }
        if (Mathf.Abs(rem) > 0.005f) R.soft += "尻の底が狙いと " + rem.ToString("+0.000;-0.000") + "m 違う(駒の 1段 は 0.05 刻み)・";
        string flat = pathOfRise(0f); var mf = MizoPieceOf(flat);
        if (!mf.ok) { R.ok = false; R.hard += "平らな駒が測れない " + (flat ?? "(名が無い)") + "・"; }
        if (!R.ok) return R;
        Vector2 dir = (p1 - p0).normalized; float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg; float y = headY; int nm = 0;
        Action<float, float, float> fill = (a, b, yy) =>
        {
            float lf = mf.len; if (b - a < 0.02f) return;
            int n = Mathf.Max(1, Mathf.CeilToInt((b - a) / lf - 1e-3f));
            for (int i = 0; i < n; i++)
            {
                float sc = Mathf.Min(a + lf * (i + 0.5f), b - lf * 0.5f);
                var go = SeatAt(parent, flat, prefix + "_F" + (nm++).ToString("00"), p0 + dir * sc, yaw, new Vector3(0f, mf.floor, 0.5f * (mf.zMin + mf.zMax)), yy);
                if (go != null) R.pieces.Add(go);
            }
        };
        for (int k = 0; k < steps; k++)
        {
            var sp = sps[k]; float noseS = (k + 1) * R.pitch - (sp.zMax - sp.noseZ);
            fill(k * R.pitch, noseS - (sp.noseZ - sp.zMin), y);
            var go = SeatAt(parent, paths[k], prefix + "_D" + k.ToString("00"), p0 + dir * noseS, yaw, new Vector3(0f, sp.upper, sp.noseZ), y);
            if (go != null) R.pieces.Add(go);
            y -= sp.Rise;
        }
        return R;
    }

    /// <summary>**型 I 張り石の落とし**を p0(法肩)→ p1(法尻)の直線に並べる。段数 = ceil(落差 / riseMax)・1段 = 落差 ÷ 段数 を 0.05 刻みに丸め(0.10〜0.30)・
    /// 法の勾配の版 = 平面の長さ ÷ 落差 に近い方(1.0 / 1.5)。駒 k は**駒の実メッシュの上の平石の天端と頭の端(zMin)**を (s = k × 踏面, 天端 − k × 1段) へ当てる
    /// ── 踏面 = 駒の実長・1段 = 実長 ÷ 法の勾配(⛔ ピボットで決めない)。柔: 平面の長さとの差(⚠)。硬: 尻の天端 ≥ tailMin。
    /// 当たる先: 土井 D2 seg2 の座の落とし(Za_Kura1・Za_Kura2 → 北の路の溝)・法面を縦に下ろす落とし(D6・D9 の吐口 ── 置き場の欄が名で書かれたら)。</summary>
    public static StepRun LayHariOtoshi(Transform parent, string prefix, Vector2 p0, Vector2 p1, float topY, float footY, float riseMax, float tailMin, Func<float, float, string> pathOf)
    {
        var R = new StepRun { headY = topY };
        float drop = topY - footY, L = Vector2.Distance(p0, p1); R.length = L;
        if (drop <= 0.05f) { R.ok = false; R.hard += "法の落差が無い(" + drop.ToString("F3") + ")・"; return R; }
        int steps = Mathf.Max(1, Mathf.CeilToInt(drop / riseMax - 1e-4f)); R.steps = steps;
        float r = Mathf.Clamp(Mathf.Round(drop / steps / 0.05f) * 0.05f, 0.10f, 0.30f);
        float nori = L / drop < 1.25f ? 1.0f : 1.5f;
        string path = pathOf(r, nori); var sp = StepPieceOf(path);
        if (!sp.ok) { R.ok = false; R.hard += "駒が測れない " + (path ?? "(名が無い)") + "・"; return R; }
        float rise = sp.Len / nori; R.pitch = sp.Len;
        for (int k = 0; k < steps; k++) R.rises.Add(rise);
        R.tailY = topY - steps * rise;
        if (rise > riseMax + 1e-4f) { R.ok = false; R.hard += "1段 " + rise.ToString("F3") + " > 上限 " + riseMax.ToString("F2") + "・"; }
        if (!float.IsNaN(tailMin) && R.tailY < tailMin - 1e-4f) { R.ok = false; R.hard += "尻の天端 " + R.tailY.ToString("F3") + " < 下限 " + tailMin.ToString("F3") + "・"; }
        float plan = steps * sp.Len;
        if (Mathf.Abs(plan - L) > 0.3f) R.soft += "並べた長さ " + plan.ToString("F2") + "m と法の平面の長さ " + L.ToString("F2") + "m の差 " + (plan - L).ToString("+0.00;-0.00") + "m(法の勾配の版 1:" + nori.ToString("0.0") + ")・";
        if (Mathf.Abs(R.tailY - footY) > 0.05f) R.soft += "尻の天端が法尻と " + (R.tailY - footY).ToString("+0.000;-0.000") + "m 違う・";
        if (!R.ok) return R;
        Vector2 dir = (p1 - p0).normalized; float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
        for (int k = 0; k < steps; k++)
        {
            var go = SeatAt(parent, path, prefix + "_I" + k.ToString("00"), p0 + dir * (k * sp.Len), yaw, new Vector3(0f, sp.upper, sp.zMin), topY - k * rise);
            if (go != null) R.pieces.Add(go);
        }
        return R;
    }

    /// <summary>地盤の勾配(中心差分 ±1m の傾きの大きさ)。引けない点は +∞。当たる先: 受けの置き場の硬い条件(N10)。</summary>
    public static float SlopeAt(Vector2 q, Func<float, float, float> groundAt)
    {
        float gx0 = groundAt(q.x - 1f, q.y), gx1 = groundAt(q.x + 1f, q.y), gz0 = groundAt(q.x, q.y - 1f), gz1 = groundAt(q.x, q.y + 1f);
        if (float.IsNaN(gx0) || float.IsNaN(gx1) || float.IsNaN(gz0) || float.IsNaN(gz1)) return float.PositiveInfinity;
        return Mathf.Sqrt((gx1 - gx0) * (gx1 - gx0) + (gz1 - gz0) * (gz1 - gz0)) * 0.5f;
    }

    /// <summary>**N10 受け(型 J 玉石の受け)の置き場**: 区画の内の 1m の格子の点を起点に近い順に並べ、<see cref="PlaceBest(IEnumerable{Vector2},int,Func{Vector2,GameObject},IList{Hard},IList{Soft},SeiyakuTally)"/> で
    /// 硬い条件(足元の外形が区画の内・指名の辺から <paramref name="keep"/> 以上内・足元の勾配 ≤ slopeMax)で退け、柔らかい条件(起点に近い)で選ぶ。
    /// 長手(局所 Z)= 平ら(勾配 ≤ slopeMax の格子の一続き・半径 15m)の主軸・+Z(溢れ口)= 長手の両端のうち地盤の低い側。
    /// 高さ = 駒の外形の縁(実メッシュ・<see cref="StepPiece.rim"/>)を足元の外周の地盤の最低へ(埋めて隠す ── 浮かせない)。
    /// 当たる先: 土井 D11 seg2(西の谷底の受け)・竪樋の足の受け(D12 ── 置き場の欄が名で書かれたら)。</summary>
    public static GameObject PlaceUke(Transform parent, string name, string path, Vector2 origin, Vector2[] parcel, IList<Vector2[]> keepEdges, float keep, float slopeMax,
                                      Func<float, float, float> groundAt, SeiyakuTally tally, out string note)
    {
        note = null; var sp = StepPieceOf(path);
        if (!sp.ok) { note = "受けの駒が測れない " + (path ?? "(名が無い)"); return null; }
        var slopeCache = new Dictionary<long, float>();
        Func<Vector2, float> slopeAt = q =>
        {
            long key = ((long)Mathf.RoundToInt(q.x * 2f) + 1000000L) * 4000000L + (Mathf.RoundToInt(q.y * 2f) + 1000000L); float sv;
            if (slopeCache.TryGetValue(key, out sv)) return sv;
            sv = SlopeAt(q, groundAt); slopeCache[key] = sv; return sv;
        };
        Func<Vector2, Vector2> axisAt = q =>
        {
            var cells = new List<Vector2>(); var seen = new HashSet<long>(); var qu = new Queue<Vector2Int>(); qu.Enqueue(Vector2Int.zero); seen.Add(0);
            while (qu.Count > 0 && cells.Count < 1000)
            {
                var c = qu.Dequeue(); var w = q + new Vector2(c.x, c.y);
                if (!EdoGeom.PIP(parcel, w) || slopeAt(w) > slopeMax) continue; cells.Add(w);
                foreach (var dd in new[] { Vector2Int.right, Vector2Int.left, Vector2Int.up, Vector2Int.down })
                { var nx = c + dd; if (Mathf.Abs(nx.x) > 15 || Mathf.Abs(nx.y) > 15) continue; long key = (long)(nx.x + 100) * 1000 + (nx.y + 100); if (seen.Add(key)) qu.Enqueue(nx); }
            }
            if (cells.Count < 3) return Vector2.zero;
            var P = new List<Vector3>(); foreach (var c in cells) P.Add(new Vector3(c.x, 0f, c.y)); Vector2 cen, t; PrincipalAxis(P, out cen, out t); return t;
        };
        // 置き場 → (平面・向き)── 同じ入力で同じ結果(PlaceBest の置き直しのため)
        Func<Vector2, Vector3> frame = q =>
        {
            var ax = axisAt(q); if (ax == Vector2.zero) return new Vector3(float.NaN, 0f, 0f);
            float half = 0.5f * sp.Len; float ga = groundAt(q.x + ax.x * half, q.y + ax.y * half), gb = groundAt(q.x - ax.x * half, q.y - ax.y * half);
            if (gb < ga) ax = -ax;   // +Z(溢れ口)を低い側へ
            return new Vector3(q.x, Mathf.Atan2(ax.x, ax.y) * Mathf.Rad2Deg, q.y);
        };
        float zc = 0.5f * (sp.zMin + sp.zMax);
        // 足元の外形の標本(5×5)── q = 駒の芯(局所 (0, ·, zc))の世界の点
        Func<Vector2, float, List<Vector2>> foot = (q, yaw) =>
        {
            var rot = Quaternion.Euler(0f, yaw, 0f); var l = new List<Vector2>();
            for (int i = 0; i <= 4; i++) for (int j = 0; j <= 4; j++)
                {
                    var lp = rot * new Vector3(Mathf.Lerp(sp.xMin, sp.xMax, i / 4f), 0f, Mathf.Lerp(sp.zMin, sp.zMax, j / 4f) - zc);
                    l.Add(q + new Vector2(lp.x, lp.z));
                }
            return l;
        };
        Func<List<Vector2>, string> hardOf = F =>
        {
            foreach (var p in F) if (!EdoGeom.PIP(parcel, p)) return "区画の内";
            foreach (var p in F) foreach (var e in keepEdges) if (EdoGeom.DistToEdge(p, e[0], e[1]) < keep - 1e-4f) return "辺から " + keep.ToString("F2") + "m 以上内";
            foreach (var p in F) if (slopeAt(p) > slopeMax + 1e-4f) return "足元の勾配 ≤ " + slopeMax.ToString("F2");
            return null;
        };
        // 候補: 1m の格子・起点に近い順・形の上の硬い条件で先に篩う(PlaceBest は据えた駒で測り直す)
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue; foreach (var p in parcel) { x0 = Mathf.Min(x0, p.x); x1 = Mathf.Max(x1, p.x); z0 = Mathf.Min(z0, p.y); z1 = Mathf.Max(z1, p.y); }
        var cand = new List<Vector2>();
        for (float x = Mathf.Floor(x0) + 0.5f; x < x1; x += 1f) for (float z = Mathf.Floor(z0) + 0.5f; z < z1; z += 1f)
            { var q = new Vector2(x, z); if (EdoGeom.PIP(parcel, q) && slopeAt(q) <= slopeMax) cand.Add(q); }
        cand.Sort((u, v) => (u - origin).sqrMagnitude.CompareTo((v - origin).sqrMagnitude));
        var spots = new List<Vector2>(); var frames = new Dictionary<Vector2, Vector3>(); int examined = 0;
        foreach (var q in cand)
        {
            if (++examined > 600) break;   // 起点から近い 600 点で打ち切る(遠い置き場は狙いから外れる)
            var fr = frame(q); if (float.IsNaN(fr.x)) continue;
            if (hardOf(foot(q, fr.y)) != null) continue;
            spots.Add(q); frames[q] = fr; if (spots.Count >= 40) break;
        }
        if (spots.Count == 0) { note = "硬い条件(区画の内・辺から " + keep.ToString("F2") + "m・勾配 ≤ " + slopeMax.ToString("F2") + ")を満たす置き場が無い(格子の候補 " + cand.Count + ")"; return null; }
        float d0 = Vector2.Distance(spots[0], origin);
        Func<Vector2, GameObject> place = q =>
        {
            var fr = frames[q]; var F = foot(q, fr.y); float gmin = float.MaxValue;
            for (int i = 0; i < F.Count; i++) { var g = groundAt(F[i].x, F[i].y); if (!float.IsNaN(g)) gmin = Mathf.Min(gmin, g); }
            if (gmin == float.MaxValue) return null;
            return SeatAt(parent, path, name, q, fr.y, new Vector3(0f, sp.rim, zc), gmin);
        };
        var hards = new List<Hard>
        {
            new Hard("受けの足元(区画の内・辺から離れ・勾配)", go => { var w = go.transform.TransformPoint(new Vector3(0f, sp.rim, zc)); return hardOf(foot(new Vector2(w.x, w.z), go.transform.eulerAngles.y)) == null; })
        };
        var softs = new List<Soft> { new Soft("起点に近い(−距離)", -(d0 + 0.01f), go => { var w = go.transform.TransformPoint(new Vector3(0f, sp.rim, zc)); return -Vector2.Distance(new Vector2(w.x, w.z), origin); }) };
        var res = PlaceBest(spots, spots.Count, place, hards, softs, tally);
        if (res == null) { note = "据えた駒の足元が硬い条件を破る(置き場 " + spots.Count + " を試した)"; return null; }
        var rp = res.transform.TransformPoint(new Vector3(0f, sp.rim, zc));
        note = "起点から " + Vector2.Distance(new Vector2(rp.x, rp.z), origin).ToString("F1") + "m・長手の向き " + res.transform.eulerAngles.y.ToString("F0") + "°(+Z = 溢れ口 = 低い側)・縁の高さ = 足元の外周の地盤の最低(埋めて隠す)";
        return res;
    }
}
