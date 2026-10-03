// EdoBuild — 造成(平場を採る)。2026-09-27・EDO-0477 P1(山王 Stage1_Grade と松江松平 DesignY の型を、図を持たない区画へ)。
//
// ⭐ 面の高さは地形が決める(CLAUDE.md 規則3・9)。棟の足あとの下の**造成前の地盤**(base_dem・規則13)の中央値を
//    その棟の平場の高さに採り、足あとの外は法面で地山へ擦り付ける。法は一枚の土の面(施主の規則: 盛土 1:1.5・切土 1:1.0)。
// ⭐ 造成は**区画の外へ出さない**(施主の規則)。区画の縁で地山に戻るよう、縁からの距離でも法を縛る ──
//    縁に近すぎて平場が平らに取れない棟は ⚠(柔らかい条件: 最も近い姿で建てて刷る・PlaceBest と同じ作法)。
// ⭐ 冪等: 毎回、区画の中の節点を造成前の地盤へ戻してから平場を起こす(松江松平 LoadNatural・山王 Stage1_Grade(prev) の型)。
//    二度流しても同じ面になる。⛔ live terrain を「造成前」として読まない(規則13 ── 自他の造成が焼き込まれる)。
// ⚠ 造成の後で、据えた駒は全部据え直す(施主の規則)── 呼び手の務め。
// 当たる先: 類型ビルダーで建てる全区画(武家・寺社・町屋・公有地)。図から起こした邸は自前の造成を持つので呼ばない。

using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using UnityEngine;

public static partial class EdoBuild
{
    static Func<float, float, float> _baseDem;

    /// <summary>区画の縁に沿って地山のまま残す幅[m] = 塀の足元(厚み 0.4〜0.6)+ 犬走り。【確度 U】一般類型。
    /// 当たる先: 区画の線の上に立つ全ての囲い(塀・長屋)。</summary>
    public const float EDGE_BERM = 1.0f;

    /// <summary>造成前の地盤(`docs/Sashizu/base_dem.json`・2m 格子の双一次)。範囲外・欠けは NaN。</summary>
    public static Func<float, float, float> BaseDem()
    {
        if (_baseDem != null) return _baseDem;
        string path = Path.Combine(Path.GetDirectoryName(Application.dataPath), "docs/Sashizu/base_dem.json");
        var dem = EdoMiniJson.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
        float x0 = Convert.ToSingle(dem["x0"]), z0 = Convert.ToSingle(dem["z0"]), st = Convert.ToSingle(dem["step"]);
        var rows = dem["h"] as List<object>;
        int nz = rows.Count, nx = (rows[0] as List<object>).Count;
        var H = new float[nz, nx];
        for (int j = 0; j < nz; j++)
        {
            var r = rows[j] as List<object>;
            for (int i = 0; i < nx; i++) H[j, i] = (r == null || i >= r.Count || r[i] == null) ? float.NaN : Convert.ToSingle(r[i]);
        }
        KindaiFill(H, x0, z0, st, nx, nz);   // ⭐ 近代の造作を除く(EDO-0514)── 正本は現代の地面のまま・読む面だけ江戸へ戻す
        _baseDem = (x, z) =>
        {
            float fi = (x - x0) / st, fj = (z - z0) / st;
            int i = Mathf.FloorToInt(fi), j = Mathf.FloorToInt(fj);
            if (i < 0 || j < 0 || i + 1 >= nx || j + 1 >= nz) return float.NaN;
            float tx = fi - i, tz = fj - j;
            return Mathf.Lerp(Mathf.Lerp(H[j, i], H[j, i + 1], tx), Mathf.Lerp(H[j + 1, i], H[j + 1, i + 1], tx), tz);
        };
        return _baseDem;
    }

    /// <summary>近代の造作の範囲(<see cref="EdoAssets.Eg.KindaiSpec"/>)。</summary>
    public class Kindai { public string id, name; public Vector2[] poly; }
    static List<Kindai> _kindai;
    /// <summary>近代の造作を除く帳を読む(無ければ空)。</summary>
    public static List<Kindai> KindaiList()
    {
        if (_kindai != null) return _kindai;
        _kindai = new List<Kindai>();
        string path = Path.Combine(Path.GetDirectoryName(Application.dataPath), EdoAssets.Eg.KindaiSpec);
        if (!File.Exists(path)) return _kindai;
        var root = EdoMiniJson.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
        var es = root != null && root.ContainsKey("entries") ? root["entries"] as List<object> : null;
        if (es == null) return _kindai;
        foreach (var o in es)
        {
            var d = o as Dictionary<string, object>; if (d == null || !d.ContainsKey("poly")) continue;
            var l = d["poly"] as List<object>; var poly = new Vector2[l.Count];
            for (int i = 0; i < l.Count; i++) { var q = l[i] as List<object>; poly[i] = new Vector2(Convert.ToSingle(q[0]), Convert.ToSingle(q[1])); }
            _kindai.Add(new Kindai { id = d.ContainsKey("id") ? d["id"] as string : "?", name = d.ContainsKey("name") ? d["name"] as string : "?", poly = poly });
        }
        return _kindai;
    }

    /// <summary>**近代の造作を除く**(2026-10-03 EDO-0514・施主「道の高まりが本当に元の地形か」)。帳の範囲ごとに、範囲の中の格子節点を
    /// 範囲の外の節点を境にした調和補間(ラプラス方程式をガウス・ザイデルで解く)へ置き換える ── 台や掘削跡を、周りの地盤から
    /// いちばん滑らかに繋いだ面にする。冪等(正本だけから出す)。当たる先: BaseDem を読む全て(類型の造成・門の置き場・道の造成・囲いの縁)。</summary>
    static void KindaiFill(float[,] H, float x0, float z0, float st, int nx, int nz)
    {
        foreach (var k in KindaiList())
        {
            var inner = new List<Vector2Int>();
            for (int j = 1; j < nz - 1; j++)
                for (int i = 1; i < nx - 1; i++)
                    if (EdoGeom.PIP(k.poly, new Vector2(x0 + i * st, z0 + j * st)) && EdoGeom.DistToPolyEdge(k.poly, new Vector2(x0 + i * st, z0 + j * st)) > 1e-3f)
                        inner.Add(new Vector2Int(i, j));
            for (int it = 0; it < 4000; it++)
                foreach (var c in inner)
                    H[c.y, c.x] = 0.25f * (H[c.y - 1, c.x] + H[c.y + 1, c.x] + H[c.y, c.x - 1] + H[c.y, c.x + 1]);
        }
    }

    /// <summary>**区画の外の地形へ、近代の造作を除いた地盤を書く**(区画を建てる前に呼ぶ・冪等)。<paramref name="parcel"/> から
    /// <paramref name="reach"/> 以内に掛かる帳の範囲について、範囲の中で**どの区画にも入らない**節点(= 道)を <see cref="BaseDem"/> の値へ戻す。
    /// 区画の中は触らない(類型の造成が毎回 BaseDem から起こす)。指図で造成する道(欄 zosei)の面の中は道の造成に任せて触らない。
    /// 返りは刷る一行(範囲が無ければ空)。当たる先: 帳に載る範囲に接する全区画(今は樹下)。</summary>
    public static string ApplyKindaiNear(Vector2[] parcel, float reach = 3f)
    {
        var notes = new List<string>();
        var dem = BaseDem();
        foreach (var k in KindaiList())
        {
            bool near = false;
            foreach (var p in parcel) if (EdoGeom.PIP(k.poly, p) || EdoGeom.DistToPolyEdge(k.poly, p) <= reach) { near = true; break; }
            if (!near) foreach (var p in k.poly) if (EdoGeom.PIP(parcel, p)) { near = true; break; }
            if (!near) continue;
            var others = EdoParcels.All.Where(q => q.pts.Count >= 3).Select(q => q.pts.ToArray()).ToList();
            var michi = MichiZosei();
            var t = T(); var td = t.terrainData; int res = td.heightmapResolution;
            Vector3 tp = t.transform.position, ts = td.size;
            float mnx = k.poly.Min(q => q.x), mxx = k.poly.Max(q => q.x), mnz = k.poly.Min(q => q.y), mxz = k.poly.Max(q => q.y);
            int i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / ts.x * (res - 1)), 0, res - 1);
            int i1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / ts.x * (res - 1)), 0, res - 1);
            int j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / ts.z * (res - 1)), 0, res - 1);
            int j1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / ts.z * (res - 1)), 0, res - 1);
            int w = i1 - i0 + 1, h = j1 - j0 + 1;
            var Hh = td.GetHeights(i0, j0, w, h);
            int written = 0; float maxDown = 0f;
            for (int j = 0; j < h; j++)
                for (int i = 0; i < w; i++)
                {
                    var q = NodeXZ(tp, ts, res, i0 + i, j0 + j);
                    if (!EdoGeom.PIP(k.poly, q)) continue;
                    if (others.Any(o => EdoGeom.PIP(o, q))) continue;
                    if (michi.Any(m => EdoGeom.PIP(m.area, q))) continue;
                    float y = dem(q.x, q.y); if (float.IsNaN(y)) continue;
                    float cur = tp.y + Hh[j, i] * ts.y; maxDown = Mathf.Max(maxDown, cur - y);
                    Hh[j, i] = Mathf.Clamp01((y - tp.y) / ts.y); written++;
                }
            td.SetHeightsDelayLOD(i0, j0, Hh); td.SyncHeightmap();
            notes.Add(string.Format("近代の造作を除いた {0}: 区画の外の節点 {1} を造成前の江戸の地盤へ(最大 {2:F2}m 下げた)", k.name, written, maxDown));
        }
        return string.Join(" / ", notes);
    }

    /// <summary>平場の結果(棟ごと)。</summary>
    public class Hiraba
    {
        public float y;          // 平場の高さ(足あとの下の造成前の地盤の中央値)
        public float relief;     // 足あとの下の地盤の起伏(最大 − 最小)
        public int squeezed;     // 区画の縁の法の縛りで、平らに取れなかった足あとの節点
    }

    /// <summary>**棟の足あとごとに平場を採り、法面で地山へ擦り付ける。**<paramref name="pads"/> は棟の壁体の足あと
    /// (世界 xz の多角形。呼び手が実メッシュから測る)。<paramref name="margin"/> は足あとの外へ平らに取る幅(犬走り・雨落ち)。
    /// 返りは棟ごとの平場の高さ。区画の中の節点だけを書き、区画の外(道・隣)は触らない。
    /// <para>節点の高さ = 造成前の地盤 b を、最寄りの平場 p(高さ)からの距離 d で [p − d/盛土の法, p + d/切土の法] に挟む
    /// (地盤が低ければ盛土の法 1:1.5 で、高ければ切土の法 1:1.0 で平場へ擦り付く)。さらに区画の縁からの距離 e で
    /// [b − e/切土の法, b + e/盛土の法] に挟み、縁で地山へ戻す(区画の外へ造成を出さない)。</para></summary>
    /// <summary>門構えの平場(2026-09-30 EDO-0491)。<see cref="foot"/> = 門構えの足元(札の foot の凸包)、
    /// <see cref="a"/>〜<see cref="b"/> = 区画の線の上で門構えが掛かる区間(表の辺への射影)。</summary>
    public class MonPad { public Vector2[] foot; public Vector2 a, b; }

    /// <summary>門構えの平場を**袖の塀の下まで**延ばす(EDO-0514・施主 2026-10-03「敷地・道の造成、整地も選択肢に」)。
    /// 区画の線(<paramref name="la"/>→<paramref name="lb"/>)に沿って門構えの区間の左右へ <paramref name="sode"/> ずつ、内へ
    /// <paramref name="depth"/> の帯を足した凸包を平場の足あとにする。高さは今までどおり区画の線の上の道の高さ(区間が左右へ延びるので、
    /// 坂でも門の芯の高さに近い中央値)。⭐ 門と左右の袖の塀が一枚の平場に立つ ── 段塀(<see cref="DanPlan"/>)は門の左右を
    /// 区切らないので、袖の塀は布石を見せずに門と同じ高さで並ぶ。区画の外(道)は触らない。
    /// 当たる先: 門が練塀の辺に立つ類型の全区画(呼び手が渡す)。</summary>
    public static MonPad MonPadWithSode(MonPad mon, Vector2 la, Vector2 lb, Vector2 inward, float sode, float depth)
    {
        if (mon == null) return null;
        var ed = lb - la; float L2 = ed.sqrMagnitude; if (L2 < 1e-6f) return mon;
        float L = Mathf.Sqrt(L2);
        float t0 = Vector2.Dot(mon.a - la, ed) / L2 - sode / L, t1 = Vector2.Dot(mon.b - la, ed) / L2 + sode / L;
        t0 = Mathf.Clamp01(t0); t1 = Mathf.Clamp01(t1);
        Vector2 a = la + ed * t0, b = la + ed * t1, n = inward.normalized * depth;
        var pts = new List<Vector2>(mon.foot) { a, b, a + n, b + n };
        var arr = pts.ToArray();
        return new MonPad { foot = EdoGeom.HullXZ(arr).Select(k => arr[k]).ToArray(), a = a, b = b };
    }

    /// <summary>区画の縁への距離。ただし <paramref name="exA"/>〜<paramref name="exB"/>(辺の上の区間)は縁と見なさない。</summary>
    static float DistToPolyEdgeExcept(Vector2[] poly, Vector2 q, Vector2 exA, Vector2 exB)
    {
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++)
        {
            Vector2 p0 = poly[i], p1 = poly[(i + 1) % poly.Length], d = p1 - p0; float L2 = d.sqrMagnitude;
            if (L2 < 1e-8f) continue;
            float L = Mathf.Sqrt(L2);
            float ea = Mathf.Abs(d.x * (exA.y - p0.y) - d.y * (exA.x - p0.x)) / L, eb = Mathf.Abs(d.x * (exB.y - p0.y) - d.y * (exB.x - p0.x)) / L;
            float ta = Vector2.Dot(exA - p0, d) / L2, tb = Vector2.Dot(exB - p0, d) / L2;
            if (ea < 0.05f && eb < 0.05f && Mathf.Max(ta, tb) > 0f && Mathf.Min(ta, tb) < 1f)
            {   // この辺(の線)に抜きの区間が載る ── 残りの二つの切れ端だけを縁とする
                float lo = Mathf.Clamp01(Mathf.Min(ta, tb)), hi = Mathf.Clamp01(Mathf.Max(ta, tb));
                if (lo > 1e-4f) { float e = EdoGeom.DistToEdge(q, p0, p0 + d * lo); if (!float.IsNaN(e) && e < m) m = e; }
                if (hi < 1f - 1e-4f) { float e = EdoGeom.DistToEdge(q, p0 + d * hi, p1); if (!float.IsNaN(e) && e < m) m = e; }
                continue;
            }
            float e2 = EdoGeom.DistToEdge(q, p0, p1);
            if (!float.IsNaN(e2) && e2 < m) m = e2;
        }
        return m;
    }

    /// <summary>区画の縁への距離。<paramref name="exs"/> の各区間(辺の上の [a, b])は縁と見なさない(門構え・表店の店先)。
    /// 区間が一つなら <see cref="DistToPolyEdgeExcept"/> と同じ。</summary>
    static float DistToPolyEdgeExceptAll(Vector2[] poly, Vector2 q, List<Vector2[]> exs)
    {
        if (exs.Count == 1) return DistToPolyEdgeExcept(poly, q, exs[0][0], exs[0][1]);
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++)
        {
            Vector2 p0 = poly[i], p1 = poly[(i + 1) % poly.Length], d = p1 - p0; float L2 = d.sqrMagnitude;
            if (L2 < 1e-8f) continue;
            float L = Mathf.Sqrt(L2);
            var cuts = new List<Vector2>();   // この辺の上で抜く [lo, hi](辺の比)
            foreach (var ex in exs)
            {
                float ea = Mathf.Abs(d.x * (ex[0].y - p0.y) - d.y * (ex[0].x - p0.x)) / L, eb = Mathf.Abs(d.x * (ex[1].y - p0.y) - d.y * (ex[1].x - p0.x)) / L;
                float ta = Vector2.Dot(ex[0] - p0, d) / L2, tb = Vector2.Dot(ex[1] - p0, d) / L2;
                if (ea < 0.05f && eb < 0.05f && Mathf.Max(ta, tb) > 0f && Mathf.Min(ta, tb) < 1f)
                    cuts.Add(new Vector2(Mathf.Clamp01(Mathf.Min(ta, tb)), Mathf.Clamp01(Mathf.Max(ta, tb))));
            }
            if (cuts.Count == 0) { float e2 = EdoGeom.DistToEdge(q, p0, p1); if (!float.IsNaN(e2) && e2 < m) m = e2; continue; }
            cuts.Sort((x, y) => x.x.CompareTo(y.x));
            float cur = 0f;
            foreach (var c in cuts)
            {
                if (c.x > cur + 1e-4f) { float e = EdoGeom.DistToEdge(q, p0 + d * cur, p0 + d * c.x); if (!float.IsNaN(e) && e < m) m = e; }
                cur = Mathf.Max(cur, c.y);
            }
            if (cur < 1f - 1e-4f) { float e = EdoGeom.DistToEdge(q, p0 + d * cur, p1); if (!float.IsNaN(e) && e < m) m = e; }
        }
        return m;
    }

    /// <summary>足あとの節点が区画の縁の法に届かないとき、平場を優先して縁の法を急にしてよい差の上限[m]【U】(EDO-0495)。
    /// 数cm は見えず、棟の浮き(許容0)を作らないほうを採る。これを越える差は置く段で退けるべき所として数える。</summary>
    const float SQUEEZE_YIELD = 0.10f;

    public static List<Hiraba> GradePads(Vector2[] parcel, IList<Vector2[]> pads, float margin, out string report,
                                         float fillRun = 1.5f, float cutRun = 1.0f, MonPad mon = null, IList<MonPad> faced = null)
    {
        // ⭐ **通りに面する棟**(表店)は門構えと同じ扱い(EDO-0503・2026-10-02 施主「町家のために 2.6m の石垣は本当か」)。
        //    <paramref name="faced"/>[k] が非 null の棟 k は、平場の高さ = その棟の店先が掛かる区画の線の上の区間の**道の高さ**、
        //    隣の棟と束ねない(軒ごとに段を付ける)、店先の区間は縁の帯と縁の法を外す。
        //    史実: 坂に面した町家は軒ごとに店先の土間を道に合わせ段々に下げる。布石の見えは 0.45m 以下・上限 0.9m【B 一般類型】。
        //    ⛔ 2026-10-02 まで表店も束ねて一つの高さに均し、坂の下手で布石の見えが 2.6m(門前4)になった。
        //    当たる先: 類型の町屋の全区画の表店(呼び手が渡す)。
        // ⭐ 門構えの平場は別扱い(2026-09-30 EDO-0491・施主「門が浮いてます」)。門は区画の線に立つので、棟と同じに扱うと
        //    縁の帯(EDGE_BERM)と縁の法に縛られて平らにならず、門の足元が坂のまま残った(西溜池2 で足元の地形 18.0〜21.4m・浮き 3.40m)。
        //    高さ = 区画の線の上で門構えが掛かる区間の造成前の地盤の中央値(敷居を道の高さへ合わせる)。その区間だけ縁の帯と縁の法を外し、
        //    内側へは法面で擦り付ける。区画の外(道)は触らない。当たる先: 門のある類型の全区画(門 8 種・番所)。
        int monIdx = -1;
        if (mon != null && mon.foot != null && mon.foot.Length >= 3)
        {
            var pl = new List<Vector2[]>(pads); pl.Add(mon.foot); pads = pl; monIdx = pads.Count - 1;
        }
        var outp = new List<Hiraba>();
        var dem = BaseDem();
        var t = T(); var td = t.terrainData; int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in parcel) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        int i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int i1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int j1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int w = i1 - i0 + 1, h = j1 - j0 + 1;
        var H = td.GetHeights(i0, j0, w, h);
        // ⭐ 平らに取る幅は**格子の対角以上**(2026-09-28 EDO-0477 実測)。地表は節点の間を双一次で結ぶので、足あとの縁に
        //    掛かる格子の 4 節点が全部平場でないと、縁の下で面が傾く ── 格子 2.0m に幅 1.0m では観理院の客殿の下端が
        //    0.17m 浮き 0.16m 埋まった。当たる先: GradePads を呼ぶ全区画(類型の全区画)。
        float cell = Mathf.Max(ts.x, ts.z) / (res - 1);
        margin = Mathf.Max(margin, cell * 1.415f);

        // 1. 平場の高さ = 足あと(+margin)の下の造成前の地盤の中央値
        foreach (var pad in pads)
        {
            var ys = new List<float>();
            float lo = float.MaxValue, hi = float.MinValue;
            for (int j = 0; j < h; j++)
                for (int i = 0; i < w; i++)
                {
                    var q = NodeXZ(tp, ts, res, i0 + i, j0 + j);
                    if (!EdoGeom.PIP(pad, q)) continue;
                    float b = dem(q.x, q.y); if (float.IsNaN(b)) b = H[j, i] * ts.y + tp.y;
                    ys.Add(b); lo = Mathf.Min(lo, b); hi = Mathf.Max(hi, b);
                }
            var hb = new Hiraba();
            if (ys.Count == 0) { var c = Centroid(pad); float b = dem(c.x, c.y); hb.y = float.IsNaN(b) ? Ground(c.x, c.y) : b; }
            else { ys.Sort(); hb.y = ys[ys.Count / 2]; hb.relief = hi - lo; }
            outp.Add(hb);
        }

        if (monIdx >= 0)
        {   // 門構えの平場の高さ = 区画の線の上の区間の道の高さ(0.25m 刻みの中央値)。造成した道は設計の高さ(RoadY・2026-09-30 EDO-0495)
            var ys = new List<float>(); float L = Vector2.Distance(mon.a, mon.b); int ns = Mathf.Max(2, Mathf.CeilToInt(L / 0.25f) + 1);
            for (int k = 0; k < ns; k++) { var q = Vector2.Lerp(mon.a, mon.b, k / (float)(ns - 1)); float b = RoadY(q.x, q.y); if (!float.IsNaN(b)) ys.Add(b); }
            if (ys.Count > 0) { ys.Sort(); outp[monIdx].y = ys[ys.Count / 2]; }
        }

        var facedIdx = new HashSet<int>();
        if (faced != null)
            for (int k = 0; k < faced.Count && k < outp.Count; k++)
            {
                var fm = faced[k]; if (fm == null) continue;
                var ys = new List<float>(); float L = Vector2.Distance(fm.a, fm.b); int ns = Mathf.Max(2, Mathf.CeilToInt(L / 0.25f) + 1);
                for (int k2 = 0; k2 < ns; k2++) { var q = Vector2.Lerp(fm.a, fm.b, k2 / (float)(ns - 1)); float b = RoadY(q.x, q.y); if (!float.IsNaN(b)) ys.Add(b); }
                if (ys.Count > 0) { ys.Sort(); outp[k].y = ys[ys.Count / 2]; facedIdx.Add(k); }
            }

        // 1b. 近い棟の平場を一つの高さに束ねる(2026-09-28 EDO-0477 実測)。⛔ 棟ごとに中央値を採ると、縁取りが触れ合う
        //    隣の平場と数cm違い、あいだの格子が傾いて下端が浮く(観理院の客殿 0.024m・鐘楼 0.038m)。足あとの間が
        //    縁取り 2 つぶんより近い棟は**同じ格子の節点を分け合う**ので、一つの高さでしか両方を平らにできない。
        // ⭐ 束の高さは、どの棟も自分の地盤の中央値から ±PAD_SHIFT(規則3 の系統差)の内に収まる幅の中で、
        //    **平らに取れない節点(SqueezeAt)が最も少ない高さ**を 1cm 刻みで選び、同じなら面積で重みを付けた平均に最も近い物を採る
        //    (2026-09-29 EDO-0472 実測)。⛔ 2026-09-28 までは「差 0.30 未満なら最も広い棟の高さへ」だった ──
        //    ① 差 0.33 の本堂と土蔵(十坊 7)が束ねられず、あいだの節点を土蔵の高さに取られて本堂の下端が 0.040m 浮いた。
        //    ② 束ねた土蔵(十坊 6)が本堂の高さへ 0.13m 下げられ、区画の縁の法に届かない節点が出て 0.020m 浮いた。
        //    差が 2×PAD_SHIFT を超える近い棟は束ねない(段として残す)── 置く段の硬い制約で離すべき物で、数えて刷る。
        //    当たる先: GradePads を呼ぶ全区画(類型の全区画の棟)。
        int n = pads.Count; var grp = new int[n]; for (int k = 0; k < n; k++) grp[k] = k;
        Func<int, int> root = null; root = k => grp[k] == k ? k : (grp[k] = root(grp[k]));
        int apart = 0;
        for (int a = 0; a < n; a++)
            for (int b2 = a + 1; b2 < n; b2++)
            {
                if (a == monIdx || b2 == monIdx) continue;              // 門構えの平場は道の高さで決まる ── 束ねない
                if (facedIdx.Contains(a) || facedIdx.Contains(b2)) continue;   // 表店は軒ごとに道の高さ ── 束ねない(段を付ける)
                if (PolyGap(pads[a], pads[b2]) >= 2f * margin) continue;
                if (Mathf.Abs(outp[a].y - outp[b2].y) > 2f * PAD_SHIFT) { apart++; continue; }
                grp[root(a)] = root(b2);
            }
        var areas = new float[n]; for (int k = 0; k < n; k++) areas[k] = Mathf.Abs(PolyArea(pads[k]));
        int merged = 0;
        var groups = new Dictionary<int, List<int>>();
        for (int k = 0; k < n; k++) { int r = root(k); if (!groups.ContainsKey(r)) groups[r] = new List<int>(); groups[r].Add(k); }
        foreach (var g in groups.Values)
        {
            if (g.Count < 2) continue;
            float lo = float.MinValue, hi2 = float.MaxValue, wsum = 0f, wy = 0f;
            foreach (var k in g) { lo = Mathf.Max(lo, outp[k].y - PAD_SHIFT); hi2 = Mathf.Min(hi2, outp[k].y + PAD_SHIFT); wsum += areas[k]; wy += areas[k] * outp[k].y; }
            float mean = wsum > 0f ? wy / wsum : outp[g[0]].y;
            if (lo > hi2)
            {   // 鎖で繋がって幅が無い束 ── 最も広い棟の高さへ(旧の作法)。数えて刷る
                int l = g[0]; foreach (var k in g) if (areas[k] > areas[l]) l = k;
                foreach (var k in g) if (k != l) { outp[k].y = outp[l].y; merged++; }
                apart++;
                continue;
            }
            float bestY = Mathf.Clamp(mean, lo, hi2); int bestSq = int.MaxValue;
            var rings = new List<List<RingNode>>(); foreach (var k in g) rings.Add(PadRing(parcel, pads[k], margin));
            for (float y = lo; y <= hi2 + 1e-4f; y += 0.01f)
            {
                int s2 = 0; foreach (var r in rings) s2 += SqueezeAt(r, y, fillRun, cutRun);
                if (s2 < bestSq || (s2 == bestSq && Mathf.Abs(y - mean) < Mathf.Abs(bestY - mean))) { bestSq = s2; bestY = y; }
            }
            foreach (var k in g) { if (Mathf.Abs(outp[k].y - bestY) > 1e-4f) merged++; outp[k].y = bestY; }
        }

        // 2. 区画の中の節点: 造成前の地盤へ戻し、最寄りの平場の法で挟み、縁の法で地山へ戻す
        var exs = new List<Vector2[]>();
        if (monIdx >= 0)
        {
            var dir = (mon.b - mon.a).normalized; float ext = margin + EDGE_BERM;
            exs.Add(new[] { mon.a - dir * ext, mon.b + dir * ext });
        }
        foreach (var k in facedIdx)
        {   // 表店の店先の区間(縁取りぶん延ばす ── 隣の店との間の節点も道の高さ側で取る)
            var fm = faced[k]; var dir = (fm.b - fm.a).normalized; float ext = margin;
            exs.Add(new[] { fm.a - dir * ext, fm.b + dir * ext });
        }
        bool exOn = exs.Count > 0;
        int written = 0, yielded = 0; float maxCut = 0f, maxFill = 0f, edgeCut = 0f;
        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
            {
                var q = NodeXZ(tp, ts, res, i0 + i, j0 + j);
                if (!EdoGeom.PIP(parcel, q)) continue;
                float b = dem(q.x, q.y);
                if (float.IsNaN(b)) continue;                                 // 正典の地盤が無い所は触らない
                float y = b;
                // 最寄りの平場(足あとの外へ margin まで平ら)
                // ⭐ 平場は**足あとへの素の距離**が最も近い棟の物を採る(2026-09-28)。⛔ 縁取り(margin)を引いた後の距離で
                //    比べると、二棟の縁取りが重なる所で 0 が並び、先に見つかった棟の高さが隣の足あとの縁へ食い込んだ
                //    (観理院の物置 0.17m・蔵 0.09m の浮き)。
                int best = -1; float bd = float.MaxValue, braw = float.MaxValue;
                for (int k = 0; k < pads.Count; k++)
                {
                    float d = EdoGeom.PIP(pads[k], q) ? 0f : EdoGeom.DistToPolyEdge(pads[k], q);
                    if (d < braw) { braw = d; best = k; }
                }
                if (best >= 0) bd = Mathf.Max(0f, braw - margin);
                if (best >= 0)
                {
                    float p = outp[best].y;
                    y = Mathf.Clamp(b, p - bd / fillRun, p + bd / cutRun);   // 地盤が低ければ盛土の法、高ければ切土の法で平場へ
                }
                // 縁で地山へ戻す(区画の外へ出さない)。⭐ 縁から EDGE_BERM までは地山のまま残し、法はその内から起こす
                //    (2026-09-28 EDO-0477 実測: 縁から法を起こすと、区画の線の上に立つ塀の足元の内側が削られ、
                //    塀の厚み 0.42m のあいだで地面が 0.8m 落ちて塀の下端が浮いた ── 観理院 49/199 駒・最悪 0.76m)。
                // ⭐ 門構えの区間(足元の幅 + 縁取り + 帯)は縁と見なさない ── 門の足元を道の高さで平らに取る(EDO-0491)
                float e = Mathf.Max(0f, (exOn ? DistToPolyEdgeExceptAll(parcel, q, exs) : EdoGeom.DistToPolyEdge(parcel, q)) - EDGE_BERM);
                float y2 = Mathf.Clamp(y, b - e / cutRun, b + e / fillRun);
                // ⭐ 表店の足あと(+縁取り)の節点は**縁でも平場の高さ**(切土のみ)── 背後が高い筆は裏を区画の線まで切り、
                //    線の上の塀が段塀の布石で土留めを兼ねる(EDO-0503 考証【U】「表を道に揃え、背後を切って裏に土留」)。
                //    ⛔ 縁で地山へ戻すと、奥行 6m の筆で背後が 2.5m 高い門前4 の店が奥で当たり、店先が 2.5m 浮いた。盛土は従前どおり縁で戻す。
                if (best >= 0 && bd <= 0f && facedIdx.Contains(best) && y < b) { if (y2 > y) edgeCut = Mathf.Max(edgeCut, y2 - y); y2 = y; }
                // ⭐ 足あと(+縁取り)の節点は平場を優先する ── 縁の法に届かない差が SQUEEZE_YIELD 以下なら平場の高さのまま取り、
                //    縁の法をその分だけ急にする(見えない数cm)。⛔ 2026-10-01 まで縁の法を優先し、束ねた平場の高さに 1 節点届かず
                //    棟の下端が浮いた(十坊8 の物置 0.023m・EDO-0495)。差が大きい所は従前どおり数える(置く段で退けるべき所)。
                //    当たる先: GradePads を呼ぶ全区画(類型の全区画の棟・門構え)。
                if (best >= 0 && bd <= 0f && Mathf.Abs(y2 - y) > 0.01f)
                {
                    if (Mathf.Abs(y2 - y) <= SQUEEZE_YIELD) { yielded++; y2 = y; }
                    else outp[best].squeezed++;
                }
                y = y2;
                if (y < b) maxCut = Mathf.Max(maxCut, b - y); else maxFill = Mathf.Max(maxFill, y - b);
                H[j, i] = Mathf.Clamp01((y - tp.y) / ts.y);
                written++;
            }
        td.SetHeightsDelayLOD(i0, j0, H); td.SyncHeightmap();
        int sq = 0; foreach (var hb in outp) sq += hb.squeezed;
        report = string.Format("造成: 平場 {0} 面(うち隣へ束ねた {5})・節点 {1}(区画の中だけ・毎回造成前の地盤から)・最大の切土 {2:F2}m・盛土 {3:F2}m{4}{6}{7}",
                               pads.Count, written, maxCut, maxFill,
                               sq > 0 ? string.Format(" ⚠ 区画の縁に近く平らに取れない節点 {0}(土留めが要る所・P3)", sq) : "", merged,
                               apart > 0 ? string.Format(" ⚠ 近いのに高さの差が {0:F2}m を超えて束ねられない平場 {1} 組", 2f * PAD_SHIFT, apart) : "",
                               yielded > 0 ? string.Format("・平場を優先して縁の法を急にした節点 {0}({1:F2}m 以内)", yielded, SQUEEZE_YIELD) : "")
               + (edgeCut > 0f ? string.Format("・表店の裏を区画の線まで切った(縁での切り 最大 {0:F2}m ── 線の上の塀の布石が土留め)", edgeCut) : "");
        return outp;
    }

    /// <summary>**この足あとに平場が取れるか**を置く前に測る(2026-09-28 EDO-0477)。<see cref="GradePads"/> と同じ格子・同じ法で、
    /// 足あと(+縁取り)の節点のうち、区画の縁の法に縛られて平場の高さまで切り盛りできない物を数える(0 なら取れる)。
    /// 硬い制約として <see cref="PlaceBest"/> へ渡す ── 取れない所に建てると下端が浮き・埋まる(観理院の本堂 浮き 1.72m・埋まり 0.92m、
    /// 区画の北の角から 2.7m で 27 節点)。当たる先: 造成して建てる類型の全棟(寺社の本堂・附属、武家の御殿・長屋以外の棟)。</summary>
    public static int PadSqueeze(Vector2[] parcel, Vector2[] foot, float margin, float fillRun = 1.5f, float cutRun = 1.0f)
    {
        var ring = PadRing(parcel, foot, margin);
        float med = RingMedian(ring);
        return float.IsNaN(med) ? 0 : SqueezeAt(ring, med, fillRun, cutRun);
    }

    /// <summary>**置いた棟の平場と束ねても平場が取れるか**(2026-09-29 EDO-0472)。<paramref name="placed"/> = 既に置いた棟の壁体の足あと。
    /// 縁取り 2 つぶんより近い棟は <see cref="GradePads"/> が一つの高さへ束ねるので、束の高さ(どの棟も自分の中央値から ±PAD_SHIFT の内)の
    /// どれかで**束の全部**が平らに取れるかを見る。返り = 最も良い高さで取れない節点の数(0 なら取れる)。束の幅が無ければ(差 &gt; 2×PAD_SHIFT)取れない数を返す。
    /// ⛔ 自分だけの中央値で見ると、置いた後の束ねで高さが動き、区画の縁の法に届かない節点が出て下端が浮く
    /// (十坊 9 の物置 0.040m ── 自分の中央値では 0 節点、束ねた 8.60 では 3 節点)。当たる先: 類型の寺社の全棟(置く段の硬い制約)。</summary>
    public static int PadSqueeze(Vector2[] parcel, Vector2[] foot, float margin, IList<Vector2[]> placed, float fillRun = 1.5f, float cutRun = 1.0f)
    {
        var ring = PadRing(parcel, foot, margin);
        float med = RingMedian(ring);
        if (float.IsNaN(med)) return 0;
        float m2 = 2f * CellMargin(margin);
        var rings = new List<List<RingNode>> { ring }; var meds = new List<float> { med };
        // ⭐ 束は**鎖で繋がる**(GradePads の union-find と同じ)── 自分に近い棟だけでなく、その棟に近い棟も束に入る。
        //    ⛔ 2026-10-01 まで自分に直に近い棟しか見ず、物置↔庫裏↔本堂の鎖で束の高さが動き、縁の法に 1 節点届かず
        //    下端が 0.023m 浮いた(十坊8 の物置・EDO-0495)。当たる先: 類型の寺社の全棟(置く段の硬い制約)。
        if (placed != null)
        {
            var inSet = new List<Vector2[]> { foot }; var left = new List<Vector2[]>(placed); bool grew = true;
            while (grew)
            {
                grew = false;
                for (int k = left.Count - 1; k >= 0; k--)
                {
                    var pf = left[k]; bool near = false;
                    foreach (var f in inSet) if (PolyGap(f, pf) < m2) { near = true; break; }
                    if (!near) continue;
                    left.RemoveAt(k); inSet.Add(pf); grew = true;
                    var r2 = PadRing(parcel, pf, margin); float md2 = RingMedian(r2);
                    if (float.IsNaN(md2)) continue;
                    rings.Add(r2); meds.Add(md2);
                }
            }
        }
        if (rings.Count == 1) return SqueezeAt(ring, med, fillRun, cutRun);
        float lo = float.MinValue, hi = float.MaxValue;
        foreach (var md in meds) { lo = Mathf.Max(lo, md - PAD_SHIFT); hi = Mathf.Min(hi, md + PAD_SHIFT); }
        if (lo > hi) return ring.Count + 1;                                   // 束ねる幅が無い = 近すぎる段違い
        int best = int.MaxValue;
        for (float y = lo; y <= hi + 1e-4f && best > 0; y += 0.01f)
        {
            int sq = 0; foreach (var r in rings) { sq += SqueezeAt(r, y, fillRun, cutRun); if (sq >= best) break; }
            if (sq < best) best = sq;
        }
        return best;
    }

    /// <summary>足あとの平場を高さ <paramref name="padY"/> にしたとき平らに取れない節点の数(0 なら取れる)。縁取りの内の節点ごとに:
    /// ① 区画の中 ── 造成前の地盤から区画の縁の法(縁から EDGE_BERM は地山のまま)で届くか。
    /// ② 区画の外 ── **今の地表**が平場の高さに揃っているか(造成は区画の外を書かない)。
    /// ⭐ ② を造成前の地盤で見ない(2026-09-29 EDO-0472 実測: 十坊 9 の土蔵の角の格子に道の節点が掛かり、道は造成前より
    ///    0.79m 掘り下げてあったのに「地山のまま = 平場の高さ」と数えて通し、下端が 0.038m 浮いた)。
    /// 当たる先: <see cref="PadSqueeze(Vector2[],Vector2[],float,float,float)"/>(置く前の硬い制約)と <see cref="GradePads"/> の束ねの高さ選び ── 類型の全区画の棟。</summary>
    static int SqueezeAt(List<RingNode> ring, float padY, float fillRun, float cutRun)
    {
        int n = 0;
        foreach (var r in ring)
        {
            if (!r.inP) { if (Mathf.Abs(r.live - padY) > 0.01f) n++; continue; }
            if (float.IsNaN(r.y)) continue;                                  // 正典の地盤が無い所は造成も触らない
            if (padY - r.y > r.e / fillRun + 0.01f || r.y - padY > r.e / cutRun + 0.01f) n++;
        }
        return n;
    }

    static int SqueezeAt(Vector2[] parcel, Vector2[] foot, float margin, float padY, float fillRun, float cutRun)
    { return SqueezeAt(PadRing(parcel, foot, margin), padY, fillRun, cutRun); }

    /// <summary>縁取りの内の節点。y = 造成前の地盤(無ければ NaN)/ live = 今の地表 / inFoot = 足あとの中 /
    /// inP = 区画の中 / e = 区画の縁の法が使える距離(縁から EDGE_BERM を引いた残り)。</summary>
    struct RingNode { public float y, live, e; public bool inFoot, inP; }

    static float CellMargin(float margin)
    {
        var td = T().terrainData; float cell = Mathf.Max(td.size.x, td.size.z) / (td.heightmapResolution - 1);
        return Mathf.Max(margin, cell * 1.415f);
    }

    static float RingMedian(List<RingNode> ring)
    {
        var ys = new List<float>();
        foreach (var r in ring) if (r.inFoot && !float.IsNaN(r.y)) ys.Add(r.y);
        if (ys.Count == 0) return float.NaN;
        ys.Sort(); return ys[ys.Count / 2];
    }

    static List<RingNode> PadRing(Vector2[] parcel, Vector2[] foot, float margin)
    {
        var dem = BaseDem();
        var t = T(); var td = t.terrainData; int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        margin = CellMargin(margin);
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in foot) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        int i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - margin - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int i1 = Mathf.Clamp(Mathf.CeilToInt((mxx + margin - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - margin - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int j1 = Mathf.Clamp(Mathf.CeilToInt((mxz + margin - tp.z) / ts.z * (res - 1)), 0, res - 1);
        var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
        var ring = new List<RingNode>();
        for (int j = j0; j <= j1; j++)
            for (int i = i0; i <= i1; i++)
            {
                var q = NodeXZ(tp, ts, res, i, j);
                bool inside = EdoGeom.PIP(foot, q);
                if (!inside && EdoGeom.DistToPolyEdge(foot, q) > margin) continue;
                bool inP = EdoGeom.PIP(parcel, q);
                ring.Add(new RingNode { y = dem(q.x, q.y), live = H[j - j0, i - i0] * ts.y + tp.y, inFoot = inside, inP = inP,
                                        e = inP ? Mathf.Max(0f, EdoGeom.DistToPolyEdge(parcel, q) - EDGE_BERM) : 0f });
            }
        return ring;
    }

    /// <summary>束ねた平場が、棟ごとの地盤の中央値から動いてよい幅[m] = 規則3 の系統差 ±0.25。
    /// 束の差がこの 2 倍までなら、どの棟も ±0.25 の内に収まる高さが取れる。</summary>
    public const float PAD_SHIFT = 0.25f;

    static float PolyArea(Vector2[] p)
    {
        float s = 0f; for (int i = 0; i < p.Length; i++) { var a = p[i]; var b = p[(i + 1) % p.Length]; s += a.x * b.y - b.x * a.y; }
        return 0.5f * s;
    }

    /// <summary>二つの多角形の縁どうしの最短距離(頂点↔相手の辺で近似。重なれば 0)。</summary>
    static float PolyGap(Vector2[] a, Vector2[] b)
    {
        float d = float.MaxValue;
        foreach (var q in a) { if (EdoGeom.PIP(b, q)) return 0f; d = Mathf.Min(d, EdoGeom.DistToPolyEdge(b, q)); }
        foreach (var q in b) { if (EdoGeom.PIP(a, q)) return 0f; d = Mathf.Min(d, EdoGeom.DistToPolyEdge(a, q)); }
        return d;
    }

    /// <summary>崖とみなす横断勾配(高さ/水平)。1:1.4(約 35°)より急なら崖。【確度 U】── 盛土の法 1:1.5 より急な地山は人が土で保てない。</summary>
    public const float CLIFF_SLOPE = 0.7f;

    /// <summary>崖と数える続きの最短[m]。これより短い急な所は塀の駒(2m)で跨ぐ段差として囲う。【確度 U】</summary>
    public const float CLIFF_MIN_RUN = 1.0f;

    /// <summary>**辺のうち塀が立てる区間**(2026-09-28・EDO-0477。施主の規則「崖の線は面の縁だけ囲う・崖の中腹に塀を建てない」)。
    /// 辺 a→b に沿って 0.25m ごとに、**今の地面**(造成の後)で塀の足あとの下を読み、崖に掛かる所を外して、
    /// 残る区間を [t0, t1](a からの距離)で返す。<paramref name="minSpan"/> より短い区間は捨てる。崖とみなすのは:
    /// ① 線に沿って ±0.5m の勾配が CLIFF_SLOPE より急(塀が崖を登る)② 線から内へ 0.5m の勾配が CLIFF_SLOPE より急(塀の内の半分が崖の面に掛かる)。
    /// ⭐ 線の外が高いだけの所(崖の裾・施主裁定X で線を寄せた所)は囲う ── 外の半分は崖の裾へ埋めて据える(根入れが基本・§0a)。
    /// ⛔ 2026-09-28 までは造成前の地盤で線の内外 ±1m の差を見ていて、造成で平らになった崖の裾まで崖と数え、
    /// 観理院 辺4 の頭 6m(うち平ら 3m)を素通しにした(EDO-0468 の検査・人が通れる口)。
    /// 当たる先: 類型の全区画の囲い(塀・柵の種別)。長屋の囲いは棟なので別に扱う(未)。
    /// ⭐ <paramref name="alongOnly"/>=true は ② を見ない ── 段塀(練塀)は線を横切る元の斜面に埋めて据え、下がる側は布石が受ける(2026-09-29 EDO-0477 施主裁定)。</summary>
    public static List<float[]> CliffFreeSpans(Vector2 a, Vector2 b, Vector2 outward, float minSpan, out float cliffLen, bool alongOnly = false)
    {
        var outp = new List<float[]>(); cliffLen = 0f;
        float L = (b - a).magnitude; if (L < 1e-3f) return outp;
        var d = (b - a) / L; var inN = -outward.normalized;
        // ⭐ 刻み 0.25m・区間は**最後の崖でない標本**で終える(⛔ 崖と判じた標本で終えると最後の駒が崖へ登った ── 観理院 辺4 の下端 8.15)
        const float STEP = 0.25f;
        var ts = new List<float>(); var cl = new List<bool>();
        for (float s = 0f; s <= L + 1e-3f; s += STEP)
        {
            float t = Mathf.Min(s, L); var p = a + d * t;
            var p0 = a + d * Mathf.Max(0f, t - 0.5f); var p1 = a + d * Mathf.Min(L, t + 0.5f);
            float g = Ground(p.x, p.y), gi = Ground(p.x + inN.x * 0.5f, p.y + inN.y * 0.5f);
            float g0 = Ground(p0.x, p0.y), g1 = Ground(p1.x, p1.y);
            ts.Add(t);
            cl.Add(!float.IsNaN(g) && !float.IsNaN(gi) && !float.IsNaN(g0) && !float.IsNaN(g1)
                   && (Mathf.Abs(g1 - g0) / Mathf.Max(0.01f, (p1 - p0).magnitude) > CLIFF_SLOPE
                       || (!alongOnly && Mathf.Abs(g - gi) / 0.5f > CLIFF_SLOPE)));
        }
        // ⭐ 崖の続きが CLIFF_MIN_RUN より短い所は崖と数えない ── 塀の駒 1 つで跨げる段差で、地盤の格子(2m)の角の段が崖と出る。
        //    ⛔ 2026-09-28 まで角の 0.75m が崖と出て区間が角から始まらず、角の延ばしが効かずに口が残った(観理院 v4 0.07m・EDO-0477)。
        for (int i = 0; i < cl.Count;)
        {
            if (!cl[i]) { i++; continue; }
            int j = i; while (j < cl.Count && cl[j]) j++;
            if ((j - i) * STEP < CLIFF_MIN_RUN) for (int k = i; k < j; k++) cl[k] = false;
            i = j;
        }
        float start = 0f, lastOk = 0f; bool open = true;
        for (int i = 0; i < ts.Count; i++)
        {
            float t = ts[i]; bool cliff = cl[i];
            if (cliff) cliffLen += STEP;
            if (cliff && open) { if (lastOk - start >= minSpan) outp.Add(new[] { start, lastOk }); open = false; }
            else if (!cliff && !open) { start = t; open = true; }
            if (!cliff) lastOk = t;
        }
        if (open && L - start >= minSpan) outp.Add(new[] { start, L });
        cliffLen = Mathf.Min(cliffLen, L);
        return outp;
    }

    static Vector2 NodeXZ(Vector3 tp, Vector3 ts, int res, int i, int j)
    {
        return new Vector2(tp.x + i * ts.x / (res - 1), tp.z + j * ts.z / (res - 1));
    }
}
