using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 地形を座標で引く・邸の Stage が地形を名指す・溝の下の地面を下げる(施主裁定 2026-10-11・EDO-0502)。
//
// ⭐ 地形は二枚になった: 大地形 ModernTerrain(4096m・2m 格子)と、北の3邸(岡部・土井・松江松平)を覆う
//   KitaTerrain(512m・0.25m 格子)。大地形は北の範囲を 2m 格子揃えで穴抜きしてある(→ EdoChikei)。
//   ・**座標から引く所**(地表の高さ・接地)は <see cref="TerrainAt"/> ── 矩形の中に在る一番細かい地形。
//   ・**地形へ書く所**(造成・均し・塗り)は <see cref="T"/> ── 邸の Stage が <see cref="TerrainFocus"/> で名指した地形。
//     名指していなければ一番大きい地形(従前どおり)。
// ⛔ 地面の高さを部材の形から推し量らない(皮・SkinHeightSolve は岡部では退役)── 高さの出どころは造成の面だけ。
//   部材は少し埋めて据え、境を隠す(docs/oki-kata.md「据えは埋めて隠すが基本」)。
public static partial class EdoBuild
{
    static Terrain _focus;
    static Terrain[] _terrains;

    /// <summary>シーンの active な地形すべて(掴んだ物が死んでいれば探し直す)。</summary>
    static Terrain[] Terrains()
    {
        var c = _terrains;
        bool ok = c != null && c.Length > 0;
        if (ok) foreach (var t in c) if (t == null || !t.gameObject.activeInHierarchy) { ok = false; break; }
        if (ok) return c;
        var l = new List<Terrain>();
        foreach (var t in UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None))
            if (t.gameObject.activeInHierarchy && t.terrainData != null) l.Add(t);
        _terrains = l.ToArray();
        return _terrains;
    }

    /// <summary>地形の xz の矩形(世界)。</summary>
    public static Rect TerrainRect(Terrain t)
    {
        var p = t.transform.position; var s = t.terrainData.size;
        return new Rect(p.x, p.z, s.x, s.z);
    }

    /// <summary>地形の heightmap の升[m]。</summary>
    public static float TerrainCell(Terrain t) { var td = t.terrainData; return td.size.x / (td.heightmapResolution - 1); }

    /// <summary>一番細かい地形(大地形しか無ければ null)。<see cref="GroundProbe"/> が使う。</summary>
    public static Terrain FineTerrain()
    {
        Terrain best = null;
        Terrain big = null;
        foreach (var t in Terrains())
        {
            if (best == null || TerrainCell(t) < TerrainCell(best)) best = t;
            if (big == null || t.terrainData.size.x > big.terrainData.size.x) big = t;
        }
        return best == big ? null : best;
    }

    /// <summary>**座標から地形を引く**一つの関数。矩形の中に在る地形のうち一番細かい物。どれにも入らなければ <see cref="T"/>。
    /// 当たる先: 地表を座標で測る所すべて(<see cref="Ground"/>・<see cref="GroundProbe"/>)。</summary>
    public static Terrain TerrainAt(float x, float z)
    {
        Terrain best = null; float bc = float.MaxValue;
        foreach (var t in Terrains())
        {
            if (!TerrainRect(t).Contains(new Vector2(x, z))) continue;
            float c = TerrainCell(t); if (c < bc) { bc = c; best = t; }
        }
        return best != null ? best : T();
    }

    sealed class FocusScope : IDisposable
    {
        readonly Terrain prev; bool done;
        public FocusScope(Terrain t) { prev = _focus; _focus = t; }
        public void Dispose() { if (done) return; done = true; _focus = prev; }
    }

    /// <summary>邸の Stage の間だけ <see cref="T"/> を点 <paramref name="p"/> の地形へ名指す(using で囲む・入れ子可)。
    /// 当たる先: 北の3邸の細かい地形の上で建てる邸(岡部・2026-10-11)。土井・松江松平は移した時に同じ一行を足す。</summary>
    public static IDisposable TerrainFocus(Vector2 p) { return new FocusScope(TerrainAt(p.x, p.y)); }

    // ---------------------------------------------------------------- 溝・桝の下の地面
    /// <summary>前の <see cref="SinkGroundUnderMizo"/> が下げた節点を戻す(今の高さが下げた値のままの節点だけ ── 造成で書き直された節点は触らない)。
    /// ⭐ 溝の据え直しを冪等にする: 溝の底は地面で決めるので、下げた地面の上で据え直すと溝が一巡ごとに沈む。⟶ 戻した節点の数。</summary>
    public static int RestoreSunkGround(string undoPath)
    {
        if (undoPath == null || !System.IO.File.Exists(undoPath)) return 0;
        var t = T(); var td = t.terrainData; int n = 0;
        var rec = new List<float[]>();   // 塊の順に読み、**逆順に**戻す(同じ節点を二度下げていれば後の下げから戻す)
        using (var br = new System.IO.BinaryReader(System.IO.File.OpenRead(undoPath)))
            while (br.BaseStream.Position < br.BaseStream.Length)
            {
                bool mine = br.ReadString() == t.name; int c = br.ReadInt32();
                for (int k = 0; k < c; k++) { float i = br.ReadInt32(), j = br.ReadInt32(), sunk = br.ReadSingle(), was = br.ReadSingle(); if (mine) rec.Add(new[] { i, j, sunk, was }); }
            }
        for (int k = rec.Count - 1; k >= 0; k--)
        {
            int i = (int)rec[k][0], j = (int)rec[k][1];
            var h = td.GetHeights(i, j, 1, 1);
            if (Mathf.Abs(h[0, 0] - rec[k][2]) > 2e-5f) continue;
            h[0, 0] = rec[k][3]; td.SetHeightsDelayLOD(i, j, h); n++;
        }
        if (n > 0) { td.SyncHeightmap(); AssetDatabase.SaveAssetIfDirty(td); }
        System.IO.File.Delete(undoPath);
        return n;
    }

    /// <summary>溝・桝の駒か(部材の資産名で: Doi_Mizo_*(笠を除く)・Doi_Masu_*)。</summary>
    public static bool IsMizoBodyPath(string path)
    {
        if (string.IsNullOrEmpty(path)) return false;
        string f = System.IO.Path.GetFileNameWithoutExtension(path);
        if (f.StartsWith("Doi_Masu_", StringComparison.Ordinal)) return true;
        return f.StartsWith("Doi_Mizo_", StringComparison.Ordinal) && f.IndexOf("Kasa", StringComparison.Ordinal) < 0;
    }

    /// <summary>**溝・桝の駒の下の地面を駒の底より下げる**(施主裁定 2026-10-11:溝は部材が底と壁を持つ・穴は開けない)。
    /// 駒ごとに札(<see cref="MizoPieceOf"/> ── 実メッシュを一度測った外形と最下点)を据えた姿へ写し、外形の中の地形の節点を
    /// 「その点の駒の最下点 − <paramref name="below"/>」へ下げる(⛔ 上げない ── 地際の張り出しの板の下だけの節点を除く・外形の外は触らない)。
    /// 【硬】溝の中に地面を出さない。⚠ 外形の縁から次の節点(≤ 1 升)までは地面が駒の外面へ下りる ── 縁石が外へ張り出す駒(部材の話)で隠れる。
    /// ⭐ 地際の張り出し付きの駒(<see cref="MizoApronOf"/> ── 縁石の外の土の板・岡部 第112巡)は、張り出しの下(|x| > 縁石の外の面)の節点を
    /// **真上の駒の上面 − <paramref name="below"/>**(光線で測る ── 土の板・吐き口の敷き石)へ下げる。駒の最下点(= 板の下面)まで下げると、
    /// 板の外の縁の外に 0.25m 格子の三角形の溝(深さ ≈ 板の厚 0.36)が立つ。溝の中(|x| ≤ 縁石の外の面)は従前どおり最下点 − below。
    /// 板の下だけの節点(どの駒の溝の中にも当たらない)は、低ければ板の上面 − below まで**上げる**(板の下は見えない・板が地面から浮く所で板の縁の前に歯を立てない)。
    /// 縁石に近い板の下の節点は、溝の中の節点(最下点 − below)と結ぶ三角形が内法の壁で溝の底を越えない高さまで下げる(格子の対角 hs·√2 で見積もる・溝の中へ地面を出さない【硬】)。
    /// 蓋を掛けた駒(<paramref name="coverTop"/> ── 門の口の暗渠。天端を蓋の厚だけ下げたので板は地表の下に埋まる)は、板の下を**蓋の天端 − below** までしか下げない
    /// (板は土に埋め、地面は蓋の天端に揃える ── 板の上面まで下げると、蓋の脇に板が 0.15 沈んだ帯と鋸の歯が見えた・第112巡の2回目)。
    /// 書くのは <see cref="T"/>(邸の Stage が名指した地形)。⟶ 下げた節点の数・駒の数・下げの最大。
    /// 当たる先: 溝・桝を据える邸すべて(岡部 Stage3d・土井 S9・松江松平)。</summary>
    public static string SinkGroundUnderMizo(IEnumerable<GameObject> pieces, float below = 0.03f, string undoPath = null, IDictionary<GameObject, float> coverTop = null)
    {
        var undo = new List<float[]>();
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution;
        float hs = td.size.x / (R - 1);
        int nPiece = 0, nNode = 0, nSkip = 0, nApron = 0, nApronNode = 0, nApronDeep = 0, nUpA = 0; float mx = 0f, mUp = 0f; var chan = new HashSet<long>();
        var low = new Dictionary<long, float>();
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            var src = PrefabUtility.GetCorrespondingObjectFromOriginalSource(g);
            string path = src == null ? null : AssetDatabase.GetAssetPath(src);
            if (!IsMizoBodyPath(path)) continue;
            var sp = MizoPieceOf(path); if (!sp.ok) { nSkip++; continue; }
            nPiece++;
            var l2w = g.transform.localToWorldMatrix; var w2l = g.transform.worldToLocalMatrix;
            var apr = MizoApronOf(path); var apMc = new List<MeshCollider>();
            if (apr.has) { nApron++; foreach (var mf in g.GetComponentsInChildren<MeshFilter>()) { if (mf.sharedMesh == null) continue; var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; apMc.Add(mc); } Physics.SyncTransforms(); }
            try {
            float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var lx in new[] { sp.xMin, sp.xMax }) foreach (var lz in new[] { sp.zMin, sp.zMax })
                {
                    var w = l2w.MultiplyPoint3x4(new Vector3(lx, sp.bottom, lz));
                    x0 = Mathf.Min(x0, w.x); x1 = Mathf.Max(x1, w.x); z0 = Mathf.Min(z0, w.z); z1 = Mathf.Max(z1, w.z);
                }
            int i0 = Mathf.Max(0, Mathf.FloorToInt((x0 - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.CeilToInt((x1 - org.x) / hs));
            int j0 = Mathf.Max(0, Mathf.FloorToInt((z0 - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.CeilToInt((z1 - org.z) / hs));
            for (int j = j0; j <= j1; j++)
                for (int i = i0; i <= i1; i++)
                {
                    var wp = new Vector3(org.x + i * hs, 0f, org.z + j * hs);
                    // 鉛直の線と駒の局所の xz の交わり(駒は Y の周りにしか回らない前提 ── 傾いた駒は底の面で読む)
                    var a = w2l.MultiplyPoint3x4(new Vector3(wp.x, 0f, wp.z)); var b = w2l.MultiplyPoint3x4(new Vector3(wp.x, 1f, wp.z));
                    var dv = b - a; if (Mathf.Abs(dv.y) < 1e-6f) continue;
                    float tt = (sp.bottom - a.y) / dv.y; var lp = a + dv * tt;
                    if (lp.x < sp.xMin - 1e-4f || lp.x > sp.xMax + 1e-4f || lp.z < sp.zMin - 1e-4f || lp.z > sp.zMax + 1e-4f) continue;
                    float yb = l2w.MultiplyPoint3x4(new Vector3(lp.x, sp.bottom, lp.z)).y - below; bool apronOnly = false;
                    if (apr.has && Mathf.Abs(lp.x) > apr.xBody - 0.005f)
                    {   // 張り出しの下: 真上の駒の上面(土の板・敷き石)− below
                        float top = float.MinValue; var ray = new Ray(new Vector3(wp.x, RB(g).max.y + 1f, wp.z), Vector3.down); RaycastHit hh;
                        foreach (var mc in apMc) if (mc.Raycast(ray, out hh, RB(g).size.y + 2f)) top = Mathf.Max(top, hh.point.y);
                        float cv; if (coverTop != null && coverTop.TryGetValue(g, out cv)) top = Mathf.Max(top, cv);
                        if (top > float.MinValue)
                        {
                            yb = top - below; nApronNode++; apronOnly = true;
                            // 溝の中へ地面を出さない【硬】: 板の下の節点と溝の中の節点(最下点 − below・格子の対角まで)を結ぶ三角形が溝の内法の壁(xInner)で底を越えないよう、縁石に近い節点は下げる
                            float xN = Mathf.Abs(lp.x), dd = hs * 1.4143f, run = xN - apr.xInner;
                            if (run < dd)
                            {
                                float yC = sp.bottom - below, ratio = dd / (dd - run), lim = sp.floor + (sp.floor - yC) * (ratio - 1f);
                                float yl = l2w.MultiplyPoint3x4(new Vector3(lp.x, lim, lp.z)).y; if (yl < yb) { yb = yl; nApronDeep++; }
                            }
                        }
                    }
                    long k = ((long)i << 32) ^ (uint)j; float cur;
                    if (!low.TryGetValue(k, out cur) || yb < cur) low[k] = yb;
                    if (!apronOnly) chan.Add(k);
                }
            } finally { foreach (var mc in apMc) if (mc != null) UnityEngine.Object.DestroyImmediate(mc); }
        }
        if (low.Count > 0)
        {
            int i0 = int.MaxValue, i1 = int.MinValue, j0 = int.MaxValue, j1 = int.MinValue;
            foreach (var k in low.Keys) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); i0 = Mathf.Min(i0, i); i1 = Mathf.Max(i1, i); j0 = Mathf.Min(j0, j); j1 = Mathf.Max(j1, j); }
            var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
            foreach (var kv in low)
            {
                int i = (int)(kv.Key >> 32), j = (int)(uint)(kv.Key & 0xffffffff);
                float cur = H[j - j0, i - i0] * td.size.y + org.y;
                if (kv.Value >= cur - 1e-4f)
                {   // 板の下だけの節点(どの駒の溝の中にも当たらない)は板の上面 − below まで上げる ── 板が地面から浮いた所で、板の下の低い節点と帯の節点の三角形が板の縁の前に鋸の歯を立てた(第112巡の4回目・D_N40_Mae の頭)
                    if (chan.Contains(kv.Key) || kv.Value <= cur + 1e-4f) continue;
                    mUp = Mathf.Max(mUp, kv.Value - cur); H[j - j0, i - i0] = (kv.Value - org.y) / td.size.y; nUpA++;
                    undo.Add(new[] { i, j, H[j - j0, i - i0], (cur - org.y) / td.size.y }); continue;
                }
                mx = Mathf.Max(mx, cur - kv.Value); H[j - j0, i - i0] = (kv.Value - org.y) / td.size.y; nNode++;
                undo.Add(new[] { i, j, H[j - j0, i - i0], (cur - org.y) / td.size.y });
            }
            if (nNode + nUpA > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        }
        WriteUndo(undoPath, t.name, undo);
        return "溝・桝の下の地面を駒の底 −" + below.ToString("0.00") + " へ下げた: 駒 " + nPiece + "・節点 " + nNode + "・下げの最大 " + mx.ToString("F2")
               + "m(地形 " + t.name + "・升 " + hs.ToString("0.###") + "m" + (nSkip > 0 ? "・札の測れない駒 " + nSkip : "") + (nApron > 0 ? "・地際の張り出しの駒 " + nApron + "(板の下の節点 " + nApronNode + " は板の上面 −" + below.ToString("0.00") + " まで・うち溝の中へ三角形を出さないよう深くした " + nApronDeep + "・板の下だけの節点で板の上面 −" + below.ToString("0.00") + " まで上げた " + nUpA + "(最大 " + mUp.ToString("F2") + "))" : "") + ")";
    }

    /// <summary>**溝の両脇の地面を溝の縁石の天端へ合わせる**(施主 2026-10-11「溝の上面が地表の面と一致しているべき」・指図 grading.omoteNagayaDai.mizo.outerTop
    /// 「溝の縁の天端に地表を合わせる幅 0.3m の帯」・EDO-0502 第111巡)。
    /// 置き方(oki-kata の4手): ① 固定側 = 据わった溝の駒(<see cref="LayMizoOnTopLine"/> が天端の線へ据えた)。② 触れる所 = 駒の両側の縁石の天端の帯
    /// (実メッシュ <see cref="MizoCurbTop"/> ── 側ごと)。③ 駒の外形の外 <paramref name="band"/> 以内の節点を、その節点の局所 z での縁石の天端の高さへ(上げも下げも)。
    /// 蓋を掛けた駒は蓋の天端(<paramref name="coverTop"/>)へ。二つの駒の帯に入る節点は外形に近い方。④ 外形の中は触らない(<see cref="SinkGroundUnderMizo"/> が下げる)。
    /// ⛔ 帯の外は触らない(道は掘らない・盛らない【硬】)。内の側(台の石垣の根・<paramref name="outAt"/> を渡したとき)は**上げるだけ**(根を埋める側へ)── 石垣の見え面の下の節点は後で <see cref="SinkGroundUnderParts"/> が面より下げる。
    /// 書くのは <see cref="T"/>。控えは <see cref="RestoreSunkGround"/> と同じ書式(据え直しの前に戻す)。⟶ 上げた・下げた節点の数と最大。
    /// 当たる先: 地表と面一に埋める溝すべて(岡部 D_N40_Mae・Mizo_*)。同じ型は D_N39_1_Mae・土井の溝へ移せる。</summary>
    public static string FlushGroundToMizoTop(IEnumerable<GameObject> pieces, IDictionary<GameObject, float> coverTop, float band = 0.30f, string undoPath = null, Func<Vector2, Vector2> outAt = null)
    {
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        var want = new Dictionary<long, Vector3>();   // 節点 → (高さ, 外形からの距離, 上げるだけ)
        int nPiece = 0, nApronAll = 0;
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(g); if (!IsMizoBodyPath(path)) continue;
            var mp = MizoPieceOf(path); if (!mp.ok) continue;
            float xaP, xbP, ctP, xaN, xbN, ctN;
            bool okP = MizoCurbTop(path, 1, out xaP, out xbP, out ctP), okN = MizoCurbTop(path, -1, out xaN, out xbN, out ctN);
            if (!okP && !okN) continue;
            if (!okP) { xaP = -xbN; xbP = -xaN; ctP = ctN; } if (!okN) { xaN = -xbP; xbN = -xaP; ctN = ctP; }
            nPiece++;
            // 地際の張り出し付きの駒(第112巡): 溝の縁 = 板の外の縁 ── 帯は板の外の縁から band、高さは板の外の縁の天端へ(板の下は SinkGroundUnderMizo が板の上面より下げる)。
            //   ⛔ 帯を縁石から測って板の下に収めると、道の節点(板の縁 +0.03〜0.06)と板の下の節点の三角形が板の上へ鋸の歯に被った(第112巡の1回目)。
            var apr = MizoApronOf(path); float bandE = band; if (apr.has) nApronAll++;
            float cov = float.NaN; bool hasCov = coverTop != null && coverTop.TryGetValue(g, out cov);
            var l2w = g.transform.localToWorldMatrix; var w2l = g.transform.worldToLocalMatrix;
            int outSide = 0; if (outAt != null) { var c3 = RB(g).center; var od = outAt(new Vector2(c3.x, c3.z)); var rx3 = g.transform.right; outSide = Vector2.Dot(new Vector2(rx3.x, rx3.z), od) >= 0f ? 1 : -1; }
            float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var lx in new[] { mp.xMin - bandE, mp.xMax + bandE }) foreach (var lz in new[] { mp.zMin, mp.zMax })
                { var w = l2w.MultiplyPoint3x4(new Vector3(lx, ctP, lz)); x0 = Mathf.Min(x0, w.x); x1 = Mathf.Max(x1, w.x); z0 = Mathf.Min(z0, w.z); z1 = Mathf.Max(z1, w.z); }
            int i0 = Mathf.Max(0, Mathf.FloorToInt((x0 - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.CeilToInt((x1 - org.x) / hs));
            int j0 = Mathf.Max(0, Mathf.FloorToInt((z0 - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.CeilToInt((z1 - org.z) / hs));
            for (int j = j0; j <= j1; j++)
                for (int i = i0; i <= i1; i++)
                {
                    var a = w2l.MultiplyPoint3x4(new Vector3(org.x + i * hs, 0f, org.z + j * hs)); var b = w2l.MultiplyPoint3x4(new Vector3(org.x + i * hs, 1f, org.z + j * hs));
                    var dv = b - a; if (Mathf.Abs(dv.y) < 1e-6f) continue;
                    var lp = a + dv * ((ctP - a.y) / dv.y);
                    if (lp.z < mp.zMin - 1e-4f || lp.z > mp.zMax + 1e-4f) continue;
                    float ex; int side; if (lp.x > mp.xMax) { ex = lp.x - mp.xMax; side = 1; } else if (lp.x < mp.xMin) { ex = mp.xMin - lp.x; side = -1; } else continue;
                    if (ex > bandE + 1e-4f) continue;
                    float y = hasCov ? cov : apr.has ? l2w.MultiplyPoint3x4(new Vector3(side * apr.xOut, apr.topOut, lp.z)).y
                                                    : l2w.MultiplyPoint3x4(new Vector3(side > 0 ? 0.5f * (xaP + xbP) : 0.5f * (xaN + xbN), side > 0 ? ctP : ctN, lp.z)).y;
                    long k = ((long)i << 32) ^ (uint)j; Vector3 cur;
                    bool raiseOnly = outSide != 0 && side != outSide;   // 内の側(台の石垣の根)は根を埋める側へだけ ── 下げない
                    if (!want.TryGetValue(k, out cur) || ex < cur.y) want[k] = new Vector3(y, ex, raiseOnly ? 1f : 0f);
                }
        }
        int nUp = 0, nDown = 0; float mUp = 0f, mDown = 0f; var undo = new List<float[]>();
        if (want.Count > 0)
        {
            int i0 = int.MaxValue, i1 = int.MinValue, j0 = int.MaxValue, j1 = int.MinValue;
            foreach (var k in want.Keys) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); i0 = Mathf.Min(i0, i); i1 = Mathf.Max(i1, i); j0 = Mathf.Min(j0, j); j1 = Mathf.Max(j1, j); }
            var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
            foreach (var kv in want)
            {
                int i = (int)(kv.Key >> 32), j = (int)(uint)(kv.Key & 0xffffffff);
                float cur = H[j - j0, i - i0] * td.size.y + org.y, y = kv.Value.x;
                if (Mathf.Abs(y - cur) < 1e-4f || (kv.Value.z > 0.5f && y < cur)) continue;
                if (y > cur) { nUp++; mUp = Mathf.Max(mUp, y - cur); } else { nDown++; mDown = Mathf.Max(mDown, cur - y); }
                H[j - j0, i - i0] = (y - org.y) / td.size.y;
                undo.Add(new[] { i, j, H[j - j0, i - i0], (cur - org.y) / td.size.y });
            }
            if (undo.Count > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        }
        WriteUndo(undoPath, t.name, undo);
        return "溝の両脇 " + band.ToString("0.00") + "m の地面を縁石の天端へ合わせた: 駒 " + nPiece + "・上げた節点 " + nUp + "(最大 " + mUp.ToString("F3") + ")・下げた節点 " + nDown + "(最大 " + mDown.ToString("F3") + ")" + (nApronAll > 0 ? "・うち地際の張り出しの駒 " + nApronAll + "(帯は板の外の縁から・高さは板の外の縁の天端)" : "") + "(地形 " + t.name + ")";
    }

    /// <summary>下げた節点の控えを足す(地形の名・数・[i, j, 下げた値, 元の値]… の塊を追記)。</summary>
    static void WriteUndo(string undoPath, string terrainName, List<float[]> undo)
    {
        if (undoPath == null || undo.Count == 0) return;
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(undoPath));
        using (var bw = new System.IO.BinaryWriter(System.IO.File.Open(undoPath, System.IO.FileMode.Append)))
        { bw.Write(terrainName); bw.Write(undo.Count); foreach (var u in undo) { bw.Write((int)u[0]); bw.Write((int)u[1]); bw.Write(u[2]); bw.Write(u[3]); } }
    }

    /// <summary>**多角形の中の地形の節点を、指図の面の高さへ切り盛りする**(2026-10-12 EDO-0502 第113巡)。
    /// <paramref name="poly"/>(世界 xz)の中の節点を <paramref name="yAt"/>(節点の点 → 面の高さ・NaN = 触らない)へ ── 上げも下げもする。
    /// 法は付けない(多角形の外は触らない【硬】)── 面の縁の段は呼び手の多角形の取り方(石垣・塀の下へ入れる)で隠す。
    /// 書くのは <see cref="T"/>(邸の Stage が名指した地形)。⟶ 書いた節点の数(上げ・下げの最大は out)。
    /// 当たる先: 指図が「床のまま通す」「道の面のまま」と面の高さを名指す狭い所(岡部 背の路地の南の延長・通用門の前)。</summary>
    public static int GroundToPoly(Vector2[] poly, Func<Vector2, float> yAt, out float maxUp, out float maxDown)
    {
        maxUp = 0f; maxDown = 0f; if (poly == null || poly.Length < 3) return 0;
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        foreach (var p in poly) { x0 = Mathf.Min(x0, p.x); x1 = Mathf.Max(x1, p.x); z0 = Mathf.Min(z0, p.y); z1 = Mathf.Max(z1, p.y); }
        int i0 = Mathf.Max(0, Mathf.FloorToInt((x0 - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.CeilToInt((x1 - org.x) / hs));
        int j0 = Mathf.Max(0, Mathf.FloorToInt((z0 - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.CeilToInt((z1 - org.z) / hs));
        if (i1 < i0 || j1 < j0) return 0;
        var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1); int n = 0;
        for (int j = j0; j <= j1; j++)
            for (int i = i0; i <= i1; i++)
            {
                var q = new Vector2(org.x + i * hs, org.z + j * hs); if (!EdoGeom.PIP(poly, q)) continue;
                float y = yAt(q); if (float.IsNaN(y)) continue;
                float cur = H[j - j0, i - i0] * td.size.y + org.y; if (Mathf.Abs(y - cur) < 1e-4f) continue;
                if (y > cur) maxUp = Mathf.Max(maxUp, y - cur); else maxDown = Mathf.Max(maxDown, cur - y);
                H[j - j0, i - i0] = (y - org.y) / td.size.y; n++;
            }
        if (n > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        return n;
    }

    /// <summary>**駒の下の地面を駒の上の面より下げる**(石垣・段の土留め・基壇)── 地形の節点の真上に駒の面があれば、その節点を「面 − <paramref name="below"/>」以下へ。
    /// 駒の下の地面は見えない所なので、高さの出どころ(造成の面)は変えない ── 駒の面から地面が覗かない(見え面への土の被り)ようにするだけ。
    /// ⚠ 0.25m の格子では、造成の面の段(上の面 → 下の面)が石垣の線と法の見え面の間の節点に掛かり、見え面の前に土が立つ(第110巡 TW_Higashi_Se で 1.3m)。
    /// 【硬】駒の外形の外の節点は触らない・上げない。測るのは駒の実メッシュの上向きの面(真上からの光線)。書くのは <see cref="T"/>。
    /// 当たる先: 法のある石垣・土留めを細かい地形の上に据える邸すべて(岡部 Stage3d・土井・松江松平を移すとき)。</summary>
    public static string SinkGroundUnderParts(IEnumerable<GameObject> parts, float below = 0.05f, string undoPath = null)
    {
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        var tmp = new List<MeshCollider>(); var bounds = new List<Bounds>();
        foreach (var g in parts)
        {
            if (g == null || !g.activeInHierarchy) continue;
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue; var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
                var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; tmp.Add(mc); bounds.Add(rr.bounds);
            }
        }
        Physics.SyncTransforms();
        var low = new Dictionary<long, float>();
        try
        {
            for (int b = 0; b < tmp.Count; b++)
            {
                var bb = bounds[b];
                int i0 = Mathf.Max(0, Mathf.CeilToInt((bb.min.x - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.FloorToInt((bb.max.x - org.x) / hs));
                int j0 = Mathf.Max(0, Mathf.CeilToInt((bb.min.z - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.FloorToInt((bb.max.z - org.z) / hs));
                for (int j = j0; j <= j1; j++)
                    for (int i = i0; i <= i1; i++)
                    {
                        RaycastHit h;
                        if (!tmp[b].Raycast(new Ray(new Vector3(org.x + i * hs, bb.max.y + 1f, org.z + j * hs), Vector3.down), out h, bb.size.y + 2f)) continue;
                        float y = h.point.y - below; long k = ((long)i << 32) ^ (uint)j; float cur;
                        if (!low.TryGetValue(k, out cur) || y < cur) low[k] = y;
                    }
            }
        }
        finally { foreach (var mc in tmp) if (mc != null) UnityEngine.Object.DestroyImmediate(mc); }
        int n = 0; float mx = 0f; var undo = new List<float[]>();
        if (low.Count > 0)
        {
            int i0 = int.MaxValue, i1 = int.MinValue, j0 = int.MaxValue, j1 = int.MinValue;
            foreach (var k in low.Keys) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); i0 = Mathf.Min(i0, i); i1 = Mathf.Max(i1, i); j0 = Mathf.Min(j0, j); j1 = Mathf.Max(j1, j); }
            var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
            foreach (var kv in low)
            {
                int i = (int)(kv.Key >> 32), j = (int)(uint)(kv.Key & 0xffffffff);
                float cur = H[j - j0, i - i0] * td.size.y + org.y;
                if (kv.Value >= cur - 1e-4f) continue;
                mx = Mathf.Max(mx, cur - kv.Value); H[j - j0, i - i0] = (kv.Value - org.y) / td.size.y; n++;
                undo.Add(new[] { i, j, H[j - j0, i - i0], (cur - org.y) / td.size.y });
            }
            if (n > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        }
        WriteUndo(undoPath, t.name, undo);
        return "駒の下の地面を駒の面 −" + below.ToString("0.00") + " へ下げた: 駒の面 " + tmp.Count + "・節点 " + n + "・下げの最大 " + mx.ToString("F2") + "m(地形 " + t.name + ")";
    }

    /// <summary>**桝の口に地形の穴を開ける**(施主裁定 2026-10-11「穴は桝の口など、ごく一部だけ」)── 0.25m の格子では 0.5m 角の桝の中を
    /// 節点の下げだけで空けられない(縁の節点が口の上へ土を張る)。桝(Doi_Masu_*)の駒の外形を縁から <paramref name="inset"/> 縮めた中に
    /// 芯の入る升だけを穴にする(外形の外は開けない ── 桝の外に地の底を見せない)。控えを <paramref name="undoPath"/> へ書く(<see cref="RestoreHoles"/>)。
    /// 当たる先: 桝を据える邸すべて(岡部 Stage3d・土井 S9 を移すとき)。</summary>
    public static string HoleUnderMasu(IEnumerable<GameObject> pieces, float inset = 0.05f, string undoPath = null)
    {
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.holesResolution; float cs = td.size.x / R;
        var cells = new HashSet<long>(); int np = 0;
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            var src = PrefabUtility.GetCorrespondingObjectFromOriginalSource(g); string path = src == null ? null : AssetDatabase.GetAssetPath(src);
            if (string.IsNullOrEmpty(path) || !System.IO.Path.GetFileName(path).StartsWith("Doi_Masu_", StringComparison.Ordinal)) continue;
            var sp = MizoPieceOf(path); if (!sp.ok) continue; np++;
            var w2l = g.transform.worldToLocalMatrix; var b = RB(g);
            int i0 = Mathf.Max(0, Mathf.FloorToInt((b.min.x - org.x) / cs)), i1 = Mathf.Min(R - 1, Mathf.FloorToInt((b.max.x - org.x) / cs));
            int j0 = Mathf.Max(0, Mathf.FloorToInt((b.min.z - org.z) / cs)), j1 = Mathf.Min(R - 1, Mathf.FloorToInt((b.max.z - org.z) / cs));
            for (int j = j0; j <= j1; j++)
                for (int i = i0; i <= i1; i++)
                {
                    var lp = w2l.MultiplyPoint3x4(new Vector3(org.x + (i + 0.5f) * cs, g.transform.position.y, org.z + (j + 0.5f) * cs));
                    if (lp.x < sp.xMin + inset || lp.x > sp.xMax - inset || lp.z < sp.zMin + inset || lp.z > sp.zMax - inset) continue;
                    cells.Add(((long)i << 32) ^ (uint)j);
                }
        }
        if (cells.Count == 0) return "桝の口の穴: 0 升(桝 " + np + ")";
        int ci0 = int.MaxValue, ci1 = int.MinValue, cj0 = int.MaxValue, cj1 = int.MinValue;
        foreach (var k in cells) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); ci0 = Mathf.Min(ci0, i); ci1 = Mathf.Max(ci1, i); cj0 = Mathf.Min(cj0, j); cj1 = Mathf.Max(cj1, j); }
        int w = ci1 - ci0 + 1, h = cj1 - cj0 + 1; var hv = HolesBlock(td, ci0, cj0, w, h); int n = 0;
        var done = new List<long>();
        foreach (var k in cells) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); if (!hv[j - cj0, i - ci0]) continue; hv[j - cj0, i - ci0] = false; n++; done.Add(k); }
        td.SetHoles(ci0, cj0, hv); EditorUtility.SetDirty(td); AssetDatabase.SaveAssetIfDirty(td);
        if (undoPath != null && done.Count > 0)
        {
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(undoPath));
            using (var bw = new System.IO.BinaryWriter(System.IO.File.Open(undoPath, System.IO.FileMode.Create)))
            { bw.Write(t.name); bw.Write(done.Count); foreach (var k in done) bw.Write(k); }
        }
        return "桝の口に穴: " + n + " 升(" + cs.ToString("0.###") + "m・桝 " + np + "・外形を " + inset.ToString("0.00") + " 縮めた中に芯の入る升)";
    }

    /// <summary>前の <see cref="HoleUnderMasu"/> の穴を塞ぐ(控えを読み、消す)。⟶ 塞いだ升の数。</summary>
    public static int RestoreHoles(string undoPath)
    {
        if (undoPath == null || !System.IO.File.Exists(undoPath)) return 0;
        var t = T(); var td = t.terrainData; int n = 0;
        using (var br = new System.IO.BinaryReader(System.IO.File.OpenRead(undoPath)))
        {
            if (br.ReadString() == t.name)
            {
                int c = br.ReadInt32();
                for (int k = 0; k < c; k++)
                {
                    long key = br.ReadInt64(); int i = (int)(key >> 32), j = (int)(uint)(key & 0xffffffff);
                    td.SetHoles(i, j, new bool[,] { { true } }); n++;
                }
            }
        }
        if (n > 0) { EditorUtility.SetDirty(td); AssetDatabase.SaveAssetIfDirty(td); }
        System.IO.File.Delete(undoPath);
        return n;
    }
}
