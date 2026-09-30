using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

// ══════════════════════════════════════════════════════════════════════
//  門構え(門・番所)を**部材の札**で置き、塀の口を札から出す(EDO-0491・2026-09-29)
//  ⭐ 組み立ての最中にメッシュを推し量らない ── 位置は札(EdoPartSpec)から解析的に一度で決める。
//     地面への据え(高さ)だけは相手が地形なので実測(SeatOnGround)。→ docs/oki-kata.md §8
//  ⛔ 2026-09-29 まで門構えの位置は段ごとに別の物差しで測っていた(帯 0.3〜0.6H の頂点・材の名で屋根を落とした全部・
//     参道の空き・Body(monT)・FootprintXZ)── 食い違って十坊の門の脇に 1.9m の隙が出た。
// ══════════════════════════════════════════════════════════════════════
public static partial class EdoBuild
{
    /// <summary>塀の端を門構えへ埋める量[m](§0a「埋めて隠す」・山王の勝手口の bite と同じ作法)。
    /// ⛔ 測った隙を消すための数ではない ── 触れる所までは札で寄せ、その先の埋め。板塀の駒は厚み 0 の一枚板なので厚みの半分には寄せない。</summary>
    public const float GATE_BURY_MAX = 0.15f;

    /// <summary>置いた駒の札(資産の道から引く)。札の無い駒は null。</summary>
    public static EdoPartSpec.Spec SpecOf(GameObject go)
    {
        if (go == null) return null;
        var p = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
        return EdoPartSpec.Get(p);
    }

    /// <summary>床 = 地面と <paramref name="bed"/>(縁と目地は 5cm 跨ぐ・<see cref="BedIndex.AtNear"/>)の高い方。門構えの駒をその駒の布石の上で測る。</summary>
    public static Func<float, float, float> GroundOrBed(BedIndex bed)
    {
        return (x, z) => { float g = Ground(x, z); float b = bed.AtNear(x, z, 0.05f); return float.IsNaN(b) ? g : Mathf.Max(g, b); };
    }
    /// <summary>**門構えの駒の地面との当たりの部材**(札の <c>contact</c>)。null = 全部(下端から ROOT_TOUCH の駒)。
    /// ⭐ 在庫の冠木門は柱と枠(kagami)が足元の飾りより 0.020m 高く、扉の下端は 0.016〜0.046m 上 ── 最下点で据えると柱が浮き、
    ///    扉の下の隙を「浮き」と数えた(2026-09-30 EDO-0491 w3〜w6・堀口・虎ノ門内2,3 0.046m)。当たる先: 札に contact を書いた門の全部。</summary>
    public static Func<MeshFilter, bool> GamaeContact(GameObject piece)
    {
        var sp = SpecOf(piece);
        if (sp == null || sp.contact == null || sp.contact.Count == 0) return null;
        var names = new HashSet<string>(sp.contact);
        return mf => names.Contains(mf.name);
    }
    /// <summary>門構えの駒の**当たりの下端**[世界 y](<see cref="GamaeContact"/> の部材の最下点・無ければ外形の最下点)。</summary>
    public static float GamaeBottom(GameObject piece)
    {
        var only = GamaeContact(piece); if (only == null) return RB(piece).min.y;
        float y = float.MaxValue;
        foreach (var mf in piece.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null || !only(mf)) continue;
            var M = mf.transform.localToWorldMatrix;
            foreach (var v in mf.sharedMesh.vertices) y = Mathf.Min(y, M.MultiplyPoint3x4(v).y);
        }
        return y == float.MaxValue ? RB(piece).min.y : y;
    }
    /// <summary>**門構えの駒を地面へ据える**(高さだけ)── 最下点で <see cref="SeatOnGround"/> した後、札に <c>contact</c> があれば
    /// その部材の当たり(<see cref="RootToBed"/> の最小 = 最も地面に近い所)を地面へ下ろす(外した飾りは根入れ)。硬い ±0.01。
    /// ⭐ 頂点だけで当てると、頂点の間で地面が盛り上がる所(平場の縁の平らに取れない節点のそば)で下端が埋まった
    ///    (2026-09-30 虎ノ門内0 の長屋門 0.168m ほか 9 区画)── 足跡を検査と同じ 0.1m 刻みで引き、最も深い所を地面へ上げる。
    ///    上げて空いた下手は <see cref="GamaeKidan"/> の布石が受ける(布石はこの後で敷く)。</summary>
    public static void SeatGamae(GameObject piece, int verts)
    {
        SeatOnGround(piece, 0f, verts);
        var only = GamaeContact(piece);
        var r = RootToBed(piece, Ground, 0.1f, only);
        if (float.IsNaN(r.lo)) return;
        if (only != null ? Mathf.Abs(r.lo) > 1e-4f : r.lo < -1e-4f) piece.transform.position -= new Vector3(0f, r.lo, 0f);
    }

    /// <summary>囲いの種別 → 門の脇に来る**端の駒**の資産(札を引く相手)。囲わない・杭の類は null(口に端が無い)。</summary>
    public static string FenceEndPiece(string kind)
    {
        switch (kind)
        {
            case "none": case "boji": case "kui": return null;
            case "dobei": return EdoAssets.Own.Dobei2mEnd;
            case "yarai": return EdoAssets.Own.Typ.Takeyarai;
            case "nagaya": return PKnagayaC;
            default: return PHei;   // ita / ita+ikegaki / ishigaki+hei / 既定
        }
    }

    /// <summary>塀の外の面が区画の線からどれだけ外にあるか[m](走りの置き方の約束 × 端の駒の札)。
    /// ⭐ 板塀・練塀は厚みの芯を線に置く(DobeiRun / NeribeiRun)ので外の面 = 厚みの半分。長屋は外の面を線に置く(0)。</summary>
    public static float FenceOuterFace(string kind, out string how)
    {
        how = "";
        var p = FenceEndPiece(kind);
        if (p == null || kind == "nagaya") { how = kind + ": 外の面 = 線"; return 0f; }
        var s = EdoPartSpec.Get(p);
        if (s == null) { how = "⛔ 塀の駒 " + System.IO.Path.GetFileName(p) + " に札が無い"; return float.NaN; }
        float half = (s.faceOut - s.faceIn) * 0.5f * s.unitScale;
        how = string.Format("{0}: 外の面 = 厚みの半分 {1:F3}m(札)", kind, half);
        return half;
    }

    /// <summary>塀の本体の奥行[m](外の面から内の面まで・端の駒の札)。口の縁を決める相手を選ぶのに使う(<see cref="PlaceGamae"/> ⑤)。
    /// 薄い塀(板塀は厚み 0 の一枚板)は 0.05m を下限にする。</summary>
    public static float FenceDepth(string kind)
    {
        var p = FenceEndPiece(kind);
        if (p == null) return 0.05f;
        var s = EdoPartSpec.Get(p);
        if (s == null) return float.NaN;
        return Mathf.Max(0.05f, (s.faceOut - s.faceIn) * s.unitScale);
    }

    /// <summary>塀の端を門構えの脇の面から**どれだけ門へ食い込ませて口を狭めるか**[m]。
    /// = 端の駒の笠木(軒)の出 + 埋め <see cref="GATE_BURY_MAX"/>。
    /// ⭐ 走り(DobeiRun ほか)は駒の**外形の端**(笠木込み)を口の縁に着けるので、笠木の出を足さないと壁の本体が笠木の出だけ手前で止まる。
    /// 長屋(NagayaRun)は壁の端を口の縁に着け、門へ差す量を別に受ける(<paramref name="nagayaTuck"/>)。</summary>
    public static float FenceBite(string kind, out float nagayaTuck, out string how)
    {
        nagayaTuck = 0f; how = "";
        var p = FenceEndPiece(kind);
        if (p == null) { how = kind + ": 口に端の駒が無い(杭・囲わない)"; return 0f; }
        var s = EdoPartSpec.Get(p);
        if (s == null) { how = "⛔ 塀の駒 " + System.IO.Path.GetFileName(p) + " に札が無い"; return float.NaN; }
        float sc = s.unitScale;
        float bury = GATE_BURY_MAX;   // ⭐ 厚みに寄らず一定(板塀の駒は厚み 0 の一枚板で、厚みの半分では埋まらない・2026-09-29 実測)
        if (kind == "nagaya") { nagayaTuck = bury; how = string.Format("長屋: 壁の端を脇の面へ・門へ {0:F3}m 差す", bury); return 0f; }
        float bite = s.copingOverhang * sc + bury;
        how = string.Format("{0}: 笠木の出 {1:F3} + 埋め {2:F3} = {3:F3}m 門へ食い込ませる(札)", kind, s.copingOverhang * sc, bury, bite);
        return bite;
    }

    /// <summary>**表の辺の上で、門構えの幅の中の道がいちばん平らな所**(柔らかい: 狙い)を返す(2026-09-30 EDO-0491)。
    /// 道の高さ = 区画の線の上の造成前の地盤(<see cref="BaseDem"/>・道は造成しない)。辺の上を 0.5m 刻みで動かし、幅 2×<paramref name="half"/> の中の
    /// 高さの差(最大 − 最小)が最も小さい芯を採る。差が 0.05m 以内で並べば辺の中央に近い方。辺が門構えより短いか、中央の差が
    /// <see cref="STATION_MOVE_RANGE"/> 以下なら中央(既定)。
    /// ⭐ 門の敷居は水平なので、道が門の幅の中で傾くと下手の端が道から浮く ── 造成は区画の外(道)を触らないので、置き場で避ける
    /// (⛔ 2026-09-30 まで門は辺の中央に置き、戸田2 の高麗門は幅 15m の中で道が 3.1m 上り、下手が 2.2m 浮いた)。
    /// ⛔ 辺の両端から <see cref="STATION_END_CLEAR"/> は空ける(硬い)── 門構えの脇に塀の端を建てる余地と、隣の区画の造成した節点を足元に拾わないため
    /// (⛔ 2026-09-30 の初版は十坊8 の薬医門を辺の端へ 3.0m 寄せ、脇の塀が無くなり、隣の平場へ削られた節点で 0.81m 浮いた)。
    /// 当たる先: 類型ビルダーの全ての門構え(門 8 種・番所)。</summary>
    public const float STATION_END_CLEAR = 3.0f;
    /// <summary>辺の中央で幅の中の道の高さの差がこれ以下なら中央に置く[m]【確度 U】── 差は基壇の布石(<see cref="GamaeKidan"/>)が受ける。
    /// ⛔ 2026-09-30 の初版は差 0.90m の十坊8 の薬医門を 1.5m 寄せ、塀を建てない崖の区間の隣へ出して門の脇の塀が無くなった。</summary>
    public const float STATION_MOVE_RANGE = 1.0f;
    public static Vector2 FlattestStation(Vector2 a, Vector2 b, float half, out float range, out float rangeMid)
    {
        var dem = BaseDem(); float L = Vector2.Distance(a, b); var d = (b - a) / Mathf.Max(L, 1e-4f);
        Func<float, float> span = c =>
        {
            float lo = float.MaxValue, hi = float.MinValue;
            for (float u = c - half; u <= c + half + 1e-4f; u += 0.25f)
            {
                var q = a + d * Mathf.Clamp(u, 0f, L); float y = dem(q.x, q.y);
                if (float.IsNaN(y)) continue; lo = Mathf.Min(lo, y); hi = Mathf.Max(hi, y);
            }
            return hi >= lo ? hi - lo : float.NaN;
        };
        rangeMid = span(L * 0.5f); range = rangeMid;
        float c0 = half + STATION_END_CLEAR, c1 = L - half - STATION_END_CLEAR;
        if (c1 < c0 + 0.5f || float.IsNaN(rangeMid) || rangeMid <= STATION_MOVE_RANGE) return (a + b) * 0.5f;
        float best = L * 0.5f;
        for (float c = c0; c <= c1 + 1e-4f; c += 0.5f)
        {
            float r = span(c); if (float.IsNaN(r)) continue;
            if (r < range - 0.05f || (Mathf.Abs(r - range) <= 0.05f && Mathf.Abs(c - L * 0.5f) < Mathf.Abs(best - L * 0.5f))) { range = r; best = c; }
        }
        return a + d * best;
    }

    /// <summary>門構えの基壇の布石の浮きの線[m] ── 超えれば布石を敷く。検査の地面の線(±0.01)の半分:
    /// 布石を決める標本(0.25m 刻み)は検査(0.1m 刻み)より粗く、同じ線では 0.010〜0.011m が敷かれずに残った(2026-09-30・4 区画)。</summary>
    public const float KIDAN_FLOAT_TOL = 0.005f;
    /// <summary>基壇の布石の下端を地面へ入れる深さ[m](硬い)= 段塀の布石と同じ(<see cref="DAN_STONE_EMBED"/>)。</summary>
    public const float KIDAN_EMBED = 0.05f;
    static Bounds? _kidanLocal; static Rect _kidanTop; static float _kidanTopY;

    /// <summary>**門構えの駒の下に布石の基壇を敷く**(2026-09-30 EDO-0491・施主「門が浮いてます」)。
    /// 門の敷居は水平なので、道が門の幅の中で傾く所・区画の線をまたぐ地形の格子(2m)で足元が下がる所は、下手の端が地面から浮く。
    /// 造成は区画の外(道)を触らないので、段塀の布石(<see cref="EdoAssets.Own.Dobei2mNunoishi"/>)と同じ型で受ける ──
    /// 駒の札の foot の外接矩形を走り(局所 X)に布石の長さで割り、各区画の下の地面の最も低い所(0.25m 刻み)が駒の下端より
    /// <see cref="KIDAN_FLOAT_TOL"/> を超えて低い区画にだけ、天端 = 駒の下端・下端 = その最も低い所 − <see cref="KIDAN_EMBED"/> の布石を据える。
    /// 硬い: 布石を敷いた後の駒の下端の浮き(布石の天端と地面の高い方で測る)±0.01。布石は根入れ(埋まりは数えない)。
    /// 区域侵犯: 布石の表の面のふくらみ(<see cref="KIDAN_BULGE"/>)だけ札の foot の表より出る ── 囲いの布石と同じく線の上に立つ物として検査はその遊びで数える。
    /// 当たる先: 類型ビルダーの全ての門構え(門 8 種・番所)。名は <c>&lt;駒&gt;_kidan_&lt;k&gt;</c>(検査は "_kidan" を床に数える)。</summary>
    public const float KIDAN_BULGE = 0.05f;
    /// <summary>布石の区画どうしの天端の重ね[m] ── 天端の縁と縁を突き付けると、継ぎ目の一点で下の目地を床に読む(2026-09-30 十坊0 0.165m)。</summary>
    public const float KIDAN_SEAM = 0.02f;
    public static List<GameObject> GamaeKidan(GameObject piece, Transform parent, Func<float, float, float> ground, out string note)
    {
        var made = new List<GameObject>(); note = null;
        var sp = SpecOf(piece);
        if (sp == null || sp.foot == null || sp.foot.Count < 3) { note = piece.name + ": 札の foot が無い ── 基壇を敷けない"; return made; }
        if (_kidanLocal == null)
        {   // 布石の外形と**天端の広さ**を一度だけ測る(天端は外形より表と背で 0.03m 内 ── 石の面のふくらみ)
            var probe = Place(EdoAssets.Own.Dobei2mNunoishi, Vector3.zero, 0f, Vector3.one, null, "_kidan_probe");
            var pb = RB(probe); float tx0 = float.MaxValue, tx1 = float.MinValue, tz0 = float.MaxValue, tz1 = float.MinValue;
            float bestA = 0f, topY = pb.max.y;                          // 天端の平らな面 = 上向きの面のうち最も広い物の高さ(石の頭の凸は外形の上端へ出る)
            foreach (var mf in probe.GetComponentsInChildren<MeshFilter>())
            {
                var M = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices; var ts = mf.sharedMesh.triangles;
                for (int t = 0; t + 2 < ts.Length; t += 3)
                {
                    Vector3 a = M.MultiplyPoint3x4(vs[ts[t]]), b = M.MultiplyPoint3x4(vs[ts[t + 1]]), c = M.MultiplyPoint3x4(vs[ts[t + 2]]);
                    var nv = Vector3.Cross(b - a, c - a); if (nv.magnitude < 1e-9f || nv.y / nv.magnitude < 0.9f) continue;
                    if (Mathf.Min(a.y, Mathf.Min(b.y, c.y)) < pb.max.y - 0.05f) continue;
                    if (nv.magnitude * 0.5f > bestA) { bestA = nv.magnitude * 0.5f; topY = (a.y + b.y + c.y) / 3f; }
                    foreach (var v in new[] { a, b, c }) { tx0 = Mathf.Min(tx0, v.x); tx1 = Mathf.Max(tx1, v.x); tz0 = Mathf.Min(tz0, v.z); tz1 = Mathf.Max(tz1, v.z); }
                }
            }
            UnityEngine.Object.DestroyImmediate(probe);
            _kidanLocal = pb; _kidanTop = new Rect(tx0, tz0, tx1 - tx0, tz1 - tz0); _kidanTopY = topY;
        }
        var kb = _kidanLocal.Value; var kt = _kidanTop;
        var tr = piece.transform; float sc = tr.lossyScale.x;
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        foreach (var f in sp.foot) { x0 = Mathf.Min(x0, f.x); x1 = Mathf.Max(x1, f.x); z0 = Mathf.Min(z0, f.y); z1 = Mathf.Max(z1, f.y); }
        float zFront = z1;                                           // 札の foot の表(区画の線の内 ── PlaceGamae が保つ)
        float wb = GamaeBottom(piece);                               // 駒の当たりの下端(実測 ── 札の contact の部材)
        // ⭐ 地面へ下りている頂点(下端から 0.10m)も覆う ── 在庫の門は札の foot(帯 0.3〜1.8m の壁の線)の外へ礎・敷石が出る
        //    (⛔ 2026-09-30 の初版は foot だけを覆い、覆いの外の頂点で浮きを測り続けた)。地面との当たりは実測でよい(docs/oki-kata.md §8)
        {
            var inv = Quaternion.Euler(0f, -tr.eulerAngles.y, 0f); var onlyC = GamaeContact(piece);
            foreach (var mf in piece.GetComponentsInChildren<MeshFilter>())
            {
                var mesh = mf.sharedMesh; var rr = mf.GetComponent<Renderer>(); if (mesh == null || rr == null || !rr.enabled) continue;
                if (onlyC != null && !onlyC(mf)) continue;
                var M = mf.transform.localToWorldMatrix;
                foreach (var v in mesh.vertices)
                {
                    var w = M.MultiplyPoint3x4(v); if (w.y > wb + 0.10f) continue;
                    var l = inv * (w - tr.position); float lx = l.x / sc, lz = l.z / sc;
                    x0 = Mathf.Min(x0, lx); x1 = Mathf.Max(x1, lx); z0 = Mathf.Min(z0, lz); z1 = Mathf.Max(z1, lz);
                }
            }
            float mg = 0.02f / sc; x0 -= mg; x1 += mg; z0 -= mg; z1 += mg;
            // ⛔ 布石は札の foot の表より外(道)へ出さない(区域侵犯 許容0)── 天端の平らな面だけ 0.01m 越す: 門の下端の頂点が
            //    foot の表の線ちょうどに立つので、線で止めると表の縁の頂点が天端の縁のふくらみ(0.023m 下がる)に載って浮いて測れた
            //    (2026-09-30 十坊0 0.023m)。表のふくらみを足しても foot の表より 0.04m ── KIDAN_BULGE の内
            z1 = Mathf.Min(z1, zFront + 0.01f / sc);
        }
        float W = (x1 - x0) * sc, D = (z1 - z0) * sc;
        int n = Mathf.Max(1, Mathf.CeilToInt(W / kt.width - 0.01f)); float seg = W / n;
        float yaw = tr.eulerAngles.y; var rot = Quaternion.Euler(0f, yaw, 0f);
        Vector3 ax = rot * Vector3.right, az = rot * Vector3.forward;
        var o = tr.position + ax * (x0 * sc) + az * (z0 * sc);      // 外接矩形の局所 (x0, z0) の隅(世界)
        // ⭐ 布石は**天端で**足元を覆う(天端の広さで倍率を決める)。奥行は表の一列(倍率 1 ── 表のふくらみを 0.03m に留める)+ 奥の塊。
        //    ⛔ 2026-09-30 の二版は外形で倍率を決め一枚で奥へ伸ばし、天端が表の縁で 0.09m 内へ引っ込んで門の縁が浮いた(十坊0 0.30m)
        float dF = Mathf.Min(D, kt.height);                          // 表の一列の天端の奥行
        Func<float, float, float, float, float, string, GameObject> put = (u, v, sx, sz, sy, nm) =>
        {   // 天端の芯を (走り u, 奥 v)・天端 = wb へ
            var st = Place(EdoAssets.Own.Dobei2mNunoishi, Vector3.zero, yaw, new Vector3(sx, sy, sz), parent, nm);
            var lc = new Vector3(kt.center.x * sx, _kidanTopY * sy, kt.center.y * sz);   // 天端の平らな面を wb へ(石の頭の凸は門の下端へ埋まる・§0a)
            var want = o + ax * u + az * v; want.y = wb;
            st.transform.position = want - rot * lc;
            return st;
        };
        float worst = 0f; int used = 0;
        for (int k = 0; k < n; k++)
        {
            float gmin = float.MaxValue;
            for (float u = 0f; u <= seg + 1e-4f; u += 0.25f)
                for (float v = 0f; v <= D + 1e-4f; v += 0.25f)
                {
                    var q = o + ax * (k * seg + Mathf.Min(u, seg)) + az * Mathf.Min(v, D);
                    float g = ground(q.x, q.z); if (!float.IsNaN(g)) gmin = Mathf.Min(gmin, g);
                }
            if (gmin == float.MaxValue || wb - gmin <= KIDAN_FLOAT_TOL) continue;
            float h = wb - gmin + KIDAN_EMBED, sy = Mathf.Max(1f, h / kb.size.y), sx = (seg + KIDAN_SEAM) / kt.width, uc = k * seg + seg * 0.5f;
            made.Add(put(uc, D - dF * 0.5f, sx, dF / kt.height, sy, piece.name + "_kidan_" + k));
            float dB = D - dF + 0.10f;                                   // 奥の塊(表の一列へ 0.10m 重ねる)
            if (D - dF > 0.02f) made.Add(put(uc, dB * 0.5f, sx, dB / kt.height, sy, piece.name + "_kidan_" + k + "b"));
            worst = Mathf.Max(worst, wb - gmin); used++;
        }
        if (made.Count > 0) note = string.Format("{0}: 基壇の布石 {1}/{2} 区画・{3} 駒(見え最大 {4:F2}m)", piece.name, used, n, made.Count, worst);
        return made;
    }

    /// <summary>門構えを置いた結果。⭐ `passageC`(通り口の芯)と `gapC/gapHalf`(塀の口)を**分けて**持つ ──
    /// 番所が片方だけの門構えでは二つがずれる(⛔ 2026-09-29 まで一つの gateC が両方を兼ねていた)。</summary>
    public class Gamae
    {
        public Vector2 along, passageC, gapC;
        public float passageHalf, gapHalf, gapLo, gapHi, tuck, faceResid;
        public float jLo, jHi;           // 門構えの両端の脇の面(走りへの射影・世界)
        public GameObject loPiece, hiPiece;   // 両端の脇の面を持つ駒(塀の端が当たる相手)
        public List<string> notes = new List<string>();
    }

    /// <summary>**門構えを札で置く**(硬い: 札が無ければ例外 ── 呼ぶ側は ⛔ を刷ってその門構えを退ける)。
    /// <para>手順(解析で一度に・メッシュを測らない):
    /// ① 横 = 門の通り口の芯を <paramref name="center"/> の走りの位置へ ② 奥行 = 門の正面を塀の外の面 <paramref name="faceOut"/> へ(柔らかい: 面の揃え)
    /// ③ 番所 = 番所の正面を同じ面へ・門に向く脇の面を門の脇の面へ当てる(隙 0)
    /// ④ 区画の線 = 門構えの足元(札の foot)が線を出る最大から、内へ下げる量を出す(硬い: 許容 0)
    /// ⑤ 口 = 両端の脇の面 ∓ <paramref name="bite"/>。</para>
    /// <para>⭐ 番所は k=0 が走りの + 側・k=1 が − 側。据え(高さ)は呼ぶ側が SeatOnGround で行う(平面は動かない)。</para></summary>
    public static Gamae PlaceGamae(GameObject mon, IList<GameObject> bansho, Vector2 A, Vector2 B, Vector2 outward,
                                   Vector2 center, Vector2[] poly, float faceOut, float bite, float fenceDepth)
    {
        var g = new Gamae { along = (B - A).normalized };
        var sm = SpecOf(mon);
        if (sm == null) throw new Exception("門 " + mon.name + " に札が無い");
        if (sm.passage == null || sm.jambL == null || sm.jambR == null) throw new Exception("門 " + mon.name + " の札に通り口・脇の面が無い");
        var al = g.along; var o3 = new Vector3(outward.x, 0f, outward.y); var a3 = new Vector3(al.x, 0f, al.y);
        Func<Vector2, float> sA = p => Vector2.Dot(p, al);
        Func<Vector2, float> sO = p => Vector2.Dot(p - A, outward);

        // ① 横 ② 奥行
        mon.transform.position += a3 * (sA(center) - sA(EdoPartSpec.PassageCenterWorld(sm, mon.transform)));
        mon.transform.position += o3 * (faceOut - sO(EdoPartSpec.FrontWorld(sm, mon.transform)));

        // ③ 番所
        var members = new List<KeyValuePair<GameObject, EdoPartSpec.Spec>> { new KeyValuePair<GameObject, EdoPartSpec.Spec>(mon, sm) };
        Func<GameObject, EdoPartSpec.Spec, float[]> jambs = (go, sp) =>
        {
            float l = sA(EdoPartSpec.JambWorld(go.transform, sp.jambL)), r = sA(EdoPartSpec.JambWorld(go.transform, sp.jambR));
            return new[] { Mathf.Min(l, r), Mathf.Max(l, r) };
        };
        var mj = jambs(mon, sm);
        for (int k = 0; k < bansho.Count; k++)
        {
            var bs = bansho[k]; var sb = SpecOf(bs);
            if (sb == null || sb.jambL == null || sb.jambR == null) throw new Exception("番所 " + bs.name + " に札が無い");
            bs.transform.position += o3 * (faceOut - sO(EdoPartSpec.W(bs.transform, (sb.jambL.x + sb.jambR.x) * 0.5f, sb.front)));
            var bj = jambs(bs, sb);
            float target = k == 0 ? mj[1] : mj[0];              // 門の + 側の脇 / − 側の脇
            float mine = k == 0 ? bj[0] : bj[1];                // 番所の門に向く脇
            bs.transform.position += a3 * (target - mine);
            members.Add(new KeyValuePair<GameObject, EdoPartSpec.Spec>(bs, sb));
        }

        // ④ 区画の線(足元だけ・軒は越えてよい ── 裁定A)
        for (int it = 0; it < 6; it++)
        {
            float over = 0f;
            foreach (var m in members)
                foreach (var q in EdoPartSpec.FootWorld(m.Value, m.Key.transform))
                    if (!EdoGeom.PIP(poly, q)) over = Mathf.Max(over, EdoGeom.DistToPolyEdge(poly, q));
            if (over <= 0f) break;
            float step = over + 0.005f;
            foreach (var m in members) m.Key.transform.position -= o3 * step;
            g.tuck += step;
        }
        if (g.tuck > 0f) g.notes.Add(string.Format("⚠ 門構えの足元が区画の線を出るので内へ {0:F2}m 下げた(硬い・許容0)", g.tuck));
        g.faceResid = sO(EdoPartSpec.FrontWorld(sm, mon.transform)) - faceOut;

        // ⑤ 口
        // ⭐ 塀の端が突き付くのは、塀の本体の奥行(外の面 faceOut 〜 内へ fenceDepth)を**全部覆う**駒だけ。
        //   覆わない駒(長屋の前に出る浅い番所)の脇で塀を止めると、番所の背に穴が抜ける(溜池北0 で 2.4m・EDO-0491)。
        //   その駒は越えて次の駒(門の脇)まで塀を通し、番所は塀の面に当てて据わる(出番所の納め)。門は常に相手に採る。
        float lo = float.MaxValue, hi = float.MinValue;
        foreach (var m in members)
        {
            if (m.Key != mon)
            {
                float xm = (m.Value.jambL.x + m.Value.jambR.x) * 0.5f;
                float zf = sO(EdoPartSpec.W(m.Key.transform, xm, m.Value.front)), zb = sO(EdoPartSpec.W(m.Key.transform, xm, m.Value.back));
                float dIn = Mathf.Min(zf, zb), dOut = Mathf.Max(zf, zb);
                if (dIn > faceOut - fenceDepth + 0.05f || dOut < faceOut - 0.05f)
                {
                    g.notes.Add(string.Format("番所 {0} は塀の奥行 {1:F2}m を覆わない(奥行 {2:F2}m)── 塀は門の脇まで通す", m.Key.name, fenceDepth, dOut - dIn));
                    continue;
                }
            }
            var j = jambs(m.Key, m.Value);
            if (j[0] < lo) { lo = j[0]; g.loPiece = m.Key; }
            if (j[1] > hi) { hi = j[1]; g.hiPiece = m.Key; }
        }
        g.jLo = lo; g.jHi = hi;
        g.gapLo = lo + bite; g.gapHi = hi - bite;
        g.gapHalf = Mathf.Max(0.01f, (g.gapHi - g.gapLo) * 0.5f);
        g.gapC = A + al * ((g.gapLo + g.gapHi) * 0.5f - sA(A));
        g.passageC = EdoPartSpec.PassageCenterWorld(sm, mon.transform);
        g.passageHalf = (sm.passage.x1 - sm.passage.x0) * 0.5f * sm.unitScale;
        return g;
    }

    /// <summary>**水平断面を線分として取り、<paramref name="step"/> 刻みで点を埋める**(世界座標)。
    /// ⭐ <see cref="Section"/> は三角形の辺が切れた所の点だけで、平らな面の途中に点が無い(柱の外の面は隅の点だけ)。
    /// 奥行の筋で向き合いを見る <see cref="ContactPts"/> に渡すと、その筋に面が現れず偽の隙が出た(十坊0 2026-09-29: +0.150)。</summary>
    public static List<Vector3> DenseSection(Transform tr, float y, float step = 0.02f)
    {
        var L = new List<Vector3>();
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled || !mf.gameObject.activeInHierarchy) continue;
            var m = mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices; var tri = mf.sharedMesh.triangles;
            var w = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) w[i] = m.MultiplyPoint3x4(vs[i]);
            var hit = new List<Vector3>(3);
            for (int i = 0; i + 2 < tri.Length; i += 3)
            {
                hit.Clear();
                for (int e = 0; e < 3; e++)
                {
                    Vector3 p = w[tri[i + e]], q = w[tri[i + (e + 1) % 3]];
                    if ((p.y - y) * (q.y - y) > 0f) continue;
                    float dy = q.y - p.y; if (Mathf.Abs(dy) < 1e-7f) continue;
                    hit.Add(Vector3.Lerp(p, q, (y - p.y) / dy));
                }
                if (hit.Count < 2) { L.AddRange(hit); continue; }
                var a = hit[0]; var b = hit[1];
                int n = Mathf.Max(1, Mathf.CeilToInt(Vector3.Distance(a, b) / step));
                for (int k = 0; k <= n; k++) L.Add(Vector3.Lerp(a, b, k / (float)n));
            }
        }
        return L;
    }

    /// <summary>**門構えと塀の取り合いの隙**[m](検査の列・硬い ── 隙 &gt; 0.01 は ⛔・測れない NaN も ⛔)。
    /// 口の脇の塀の端の駒 <paramref name="fenceEnds"/>(表と裏の板のように**一組で塀の厚みを作る駒はまとめて**渡す)と、
    /// その側の脇の面を持つ門構えの駒 <paramref name="gamae"/> を、共通の丈の帯の数段で**水平断面**(実メッシュ)に切り、
    /// 走りの向き <paramref name="toward"/> で向き合う所の最小の隙を取り、段の最悪を返す。
    /// ⭐ 断面なので笠木・軒の張り出しに惑わされない(帯は両者の底 +0.3〜頂 −0.3)。斜面では段が上下に分かれて両方で測る。
    /// ⛔ 表の板だけで測らない ── 板塀は厚み 0 の板を 0.2m 離して表裏に建て、門の正面(沓石の前)に揃う表の板は柱より前にある
    /// (十坊0 の実測 2026-09-29: 表の板だけでは +0.150 の偽の隙・裏の板は柱に 0.15 埋まっていた)。</summary>
    public static float GamaeFenceGap(IList<GameObject> fenceEnds, GameObject gamae, Vector2 toward, out string how)
    {
        how = "";
        // ⭐ 測る丈は相手(門・番所)の札の**脇の面の丈**(jamb の y0〜y1)── 外形の丈で測ると上の段が番所の屋根を切り、
        //   壁の本体どうしが向き合わず「測れない」の嘘の ⛔ が出た(EDO-0491)。⛔ 札が無ければ測らない(推し量らない)
        var spec = SpecOf(gamae);
        if (spec == null || spec.jambL == null || spec.jambR == null) { how = "相手に札が無い"; return float.NaN; }
        var t = gamae.transform;
        float jLo = t.TransformPoint(new Vector3(0f, Mathf.Max(spec.jambL.y0, spec.jambR.y0), 0f)).y;
        float jHi = t.TransformPoint(new Vector3(0f, Mathf.Min(spec.jambL.y1, spec.jambR.y1), 0f)).y;
        float fLo = fenceEnds.Min(f => RB(f).min.y), fHi = fenceEnds.Max(f => RB(f).max.y);
        float y0 = Mathf.Max(fLo, jLo) + 0.05f, y1 = Mathf.Min(fHi, jHi) - 0.05f;
        if (y1 <= y0) { how = "脇の面と塀の共通の丈が無い"; return float.NaN; }
        float worst = float.NaN; int ok = 0;
        var d3 = new Vector3(toward.x, 0f, toward.y);
        for (int i = 0; i < 4; i++)
        {
            float y = Mathf.Lerp(y0, y1, i / 3f);
            var pa = new List<Vector3>(); foreach (var f in fenceEnds) pa.AddRange(DenseSection(f.transform, y));
            var pb = DenseSection(gamae.transform, y);
            Vector3 at; int n;
            float c = ContactPts(pa, pb, d3, out at, out n, 0.01f, 0.05f);
            if (float.IsNaN(c)) continue;
            ok++;
            worst = float.IsNaN(worst) ? c : Mathf.Max(worst, c);
        }
        how = string.Format("{0}/4 段で向き合う・駒 {1}", ok, fenceEnds.Count);
        return ok < 4 ? float.NaN : worst;
    }
}
