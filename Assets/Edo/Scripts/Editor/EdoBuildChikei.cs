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
        if (f.StartsWith("Doi_DanOchi_", StringComparison.Ordinal)) return true;   // 型H の段落ち(駒が底と壁を持つ ── 第115巡 岡部 D_MinamiHei)
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
            if (apr.has) nApron++;
            // 下面を測る(第136巡): 駒ごとに一時の当たりを付け、節点の真下から上へ光線を打って**最初に当たる駒の下面**を読む(板の上面は上から)
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>()) { if (mf.sharedMesh == null) continue; var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; apMc.Add(mc); }
            Physics.SyncTransforms();
            try {
            // ⭐ 第136巡: 地面は**駒の下面のすぐ下**へ ── 札の外接の矩形の底へ一律に下げると、六角の曲がり目の桝(GK)の肩の土の皮(石の材)の下まで底 −0.03 へ掘り、
            //   区画の外の道に 0.4〜0.5 の窪み(残った道が瘤に見えた・岡部 辺39/40 の角)。真下から上へ光線を打ち、最初に当たる下面 − below(当たらなければ触らない)。
            //   矩形の溝の駒は下面 = 底なので従前と同じ。当たる先: SinkGroundUnderMizo に渡す溝・桝の駒すべて
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
                    if (!(apr.has && Mathf.Abs(lp.x) > apr.xBody - 0.005f))
                    {   // 下面: 真下から上へ(駒の底の 2m 下から)最初に当たる面
                        float under = float.MaxValue; var rayU = new Ray(new Vector3(wp.x, yb - 2f, wp.z), Vector3.up); RaycastHit hu;
                        foreach (var mc in apMc) if (mc.Raycast(rayU, out hu, RB(g).size.y + 4f)) under = Mathf.Min(under, hu.point.y);
                        if (under == float.MaxValue) continue;   // 駒の下でない
                        yb = Mathf.Max(yb, under - below);
                    }
                    if (apr.has && Mathf.Abs(lp.x) > apr.xBody - 0.005f)
                    {   // 張り出しの下: 真上の駒の上面(土の板・敷き石)− below
                        float top = float.MinValue; var ray = new Ray(new Vector3(wp.x, RB(g).max.y + 1f, wp.z), Vector3.down); RaycastHit hh;
                        foreach (var mc in apMc) if (mc.Raycast(ray, out hh, RB(g).size.y + 2f)) top = Mathf.Max(top, hh.point.y);
                        float cv; if (coverTop != null && coverTop.TryGetValue(g, out cv)) top = Mathf.Max(top, cv);
                        // ⭐ 第137巡: 真上に駒の面が無い節点は駒の下でない ── 触らない。旧は札の矩形の内なら張り出しの下と見て底 −below のまま下げ、
                        //   六角の曲がり目の桝(GK・肩の土の皮が全周で MizoApronOf が xBody 0 と読む)の外形の外の矩形の隅を 13.28 へ掘り、区画の外の道に 0.6 の穴を開けた。
                        //   当たる先: 張り出し(土の板・皮)を持つ溝・桝の駒すべて(岡部 D_Corner_Masu・型A の Ago の溝)。
                        if (top == float.MinValue) continue;
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
    public static string FlushGroundToMizoTop(IEnumerable<GameObject> pieces, IDictionary<GameObject, float> coverTop, float band = 0.30f, string undoPath = null, Func<Vector2, Vector2> outAt = null, string recPath = null)
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
        if (recPath != null) { var rec = new Dictionary<long, float>(); foreach (var kv in want) rec[kv.Key] = kv.Value.x; AppendNodeTargets(recPath, t.name, rec); }   // 造成QA が帯の設計の高さを引く(第131巡)
        return "溝の両脇 " + band.ToString("0.00") + "m の地面を縁石の天端へ合わせた: 駒 " + nPiece + "・上げた節点 " + nUp + "(最大 " + mUp.ToString("F3") + ")・下げた節点 " + nDown + "(最大 " + mDown.ToString("F3") + ")" + (nApronAll > 0 ? "・うち地際の張り出しの駒 " + nApronAll + "(帯は板の外の縁から・高さは板の外の縁の天端)" : "") + "(地形 " + t.name + ")";
    }

    /// <summary>**段落ちの駒(型H)の両脇の地面を駒の側の天端へ合わせる**(<see cref="FlushGroundToMizoTop"/> の段落ち版・EDO-0502 第116巡)。
    /// 段落ちの駒は側の天端が駒の中で段になる(上の底 +0.49 → 下の底 +0.49)ので、縁石の天端一つ(<see cref="MizoCurbTop"/>)では読めない ──
    /// 駒の実メッシュの側の壁(|x| ≥ 0.30)の頂点の最も高い所を局所 z の 0.05 刻みで測り(側ごと)、駒の外形の外 <paramref name="band"/> 以内の節点をその局所 z の天端へ(上げも下げも)。
    /// 二つの駒の帯に入る節点は外形に近い方。外形の中は触らない(<see cref="SinkGroundUnderMizo"/> が下げる)。帯の外は触らない【硬】。書くのは <see cref="T"/>。
    /// 当たる先: Doi_DanOchi_* を地表に埋める所すべて(岡部 D_MinamiHei・土井 D9/D10/D11 を移すとき)。</summary>
    public static string FlushGroundToStepTop(IEnumerable<GameObject> pieces, float band = 0.30f, string undoPath = null, string recPath = null)
    {
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        var want = new Dictionary<long, Vector2>(); int nPiece = 0; var prof = new Dictionary<string, SortedDictionary<int, float>[]>();
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(g); if (string.IsNullOrEmpty(path) || !System.IO.Path.GetFileName(path).StartsWith("Doi_DanOchi_", StringComparison.Ordinal)) continue;
            var sp = StepPieceOf(path); if (!sp.ok) continue;
            SortedDictionary<int, float>[] pr;
            if (!prof.TryGetValue(path, out pr))
            {
                pr = new[] { new SortedDictionary<int, float>(), new SortedDictionary<int, float>() }; var V = new List<Vector3>(); var Tr = new List<int>(); LocalMesh(path, V, Tr);
                // 地際の土の板付き(Doi_DanOchi_Ago_*・第117巡)は板の外の縁の天端へ(FlushGroundToMizoTop と同じ ── 板の内の縁 +0.003 で取ると外の縁より 0.033 高い土の帯が立つ)
                var ap = MizoApronOf(path); float xw = ap.has ? ap.xOut - 0.02f : 0.5f * sp.xMax;
                foreach (var v in V) { if (Mathf.Abs(v.x) < xw) continue; var d = pr[v.x > 0f ? 1 : 0]; int b = Mathf.FloorToInt(v.z / 0.05f); float o; if (!d.TryGetValue(b, out o) || v.y > o) d[b] = v.y; }
                prof[path] = pr;
            }
            nPiece++;
            var l2w = g.transform.localToWorldMatrix; var w2l = g.transform.worldToLocalMatrix;
            float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var lx in new[] { sp.xMin - band, sp.xMax + band }) foreach (var lz in new[] { sp.zMin, sp.zMax }) { var w = l2w.MultiplyPoint3x4(new Vector3(lx, 0f, lz)); x0 = Mathf.Min(x0, w.x); x1 = Mathf.Max(x1, w.x); z0 = Mathf.Min(z0, w.z); z1 = Mathf.Max(z1, w.z); }
            int i0 = Mathf.Max(0, Mathf.FloorToInt((x0 - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.CeilToInt((x1 - org.x) / hs));
            int j0 = Mathf.Max(0, Mathf.FloorToInt((z0 - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.CeilToInt((z1 - org.z) / hs));
            for (int j = j0; j <= j1; j++)
                for (int i = i0; i <= i1; i++)
                {
                    var lp = w2l.MultiplyPoint3x4(new Vector3(org.x + i * hs, g.transform.position.y, org.z + j * hs));
                    if (lp.z < sp.zMin - 1e-4f || lp.z > sp.zMax + 1e-4f) continue;
                    float ex; int side; if (lp.x > sp.xMax) { ex = lp.x - sp.xMax; side = 1; } else if (lp.x < sp.xMin) { ex = sp.xMin - lp.x; side = 0; } else continue;
                    if (ex > band + 1e-4f) continue;
                    var d = pr[side]; if (d.Count == 0) d = pr[1 - side]; int b0 = Mathf.FloorToInt(lp.z / 0.05f); float top = float.NaN; int bd = int.MaxValue;
                    foreach (var kv in d) { int dd = Mathf.Abs(kv.Key - b0); if (dd < bd || (dd == bd && kv.Value > top)) { bd = dd; top = kv.Value; } }
                    if (float.IsNaN(top)) continue;
                    float y = l2w.MultiplyPoint3x4(new Vector3(lp.x, top, lp.z)).y;
                    long k = ((long)i << 32) ^ (uint)j; Vector2 cur; if (!want.TryGetValue(k, out cur) || ex < cur.y) want[k] = new Vector2(y, ex);
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
                float cur = H[j - j0, i - i0] * td.size.y + org.y, y = kv.Value.x; if (Mathf.Abs(y - cur) < 1e-4f) continue;
                if (y > cur) { nUp++; mUp = Mathf.Max(mUp, y - cur); } else { nDown++; mDown = Mathf.Max(mDown, cur - y); }
                H[j - j0, i - i0] = (y - org.y) / td.size.y; undo.Add(new[] { i, j, H[j - j0, i - i0], (cur - org.y) / td.size.y });
            }
            if (undo.Count > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        }
        WriteUndo(undoPath, t.name, undo);
        if (recPath != null) { var rec = new Dictionary<long, float>(); foreach (var kv in want) rec[kv.Key] = kv.Value.x; AppendNodeTargets(recPath, t.name, rec); }   // 造成QA が引く(第131巡)
        return "段落ちの両脇 " + band.ToString("0.00") + "m の地面を駒の側の天端へ合わせた: 駒 " + nPiece + "・上げた節点 " + nUp + "(最大 " + mUp.ToString("F3") + ")・下げた節点 " + nDown + "(最大 " + mDown.ToString("F3") + ")(地形 " + t.name + ")";
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
    public static int GroundToPoly(Vector2[] poly, Func<Vector2, float> yAt, out float maxUp, out float maxDown) { float v; return GroundToPoly(poly, yAt, false, out maxUp, out maxDown, out v); }
    /// <summary><see cref="GroundToPoly(Vector2[],Func{Vector2,float},out float,out float)"/> に「盛るだけ」(<paramref name="raiseOnly"/> ── 今の地面が面より高い節点は触らない)と盛りの体積[m³]を足した物。
    /// 当たる先: 指図が「盛るだけ」と名指す狭い土の面(岡部 D_MinamiHei の隙間の土の雨落ち segs.west.sukima・第131巡)。</summary>
    public static int GroundToPoly(Vector2[] poly, Func<Vector2, float> yAt, bool raiseOnly, out float maxUp, out float maxDown, out float fillM3) { return GroundToPoly(poly, yAt, raiseOnly ? 1 : 0, out maxUp, out maxDown, out fillM3); }
    /// <summary><paramref name="sign"/> = +1 盛るだけ・−1 削るだけ(今の地面が面より低い節点は触らない ── 擦り付けの上限)・0 両方。
    /// 当たる先: 棟の背の帯を座 − d 以下へ下げ、その先を勾配の上限で擦り付ける所(岡部 runs[N40_1].back・第131巡)。</summary>
    public static int GroundToPoly(Vector2[] poly, Func<Vector2, float> yAt, int sign, out float maxUp, out float maxDown, out float fillM3)
    {
        bool raiseOnly = sign > 0, lowerOnly = sign < 0;
        maxUp = 0f; maxDown = 0f; fillM3 = 0f; if (poly == null || poly.Length < 3) return 0;
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
                if (raiseOnly && y < cur) continue;
                if (lowerOnly && y > cur) continue;
                if (y > cur) { maxUp = Mathf.Max(maxUp, y - cur); fillM3 += (y - cur) * hs * hs; } else maxDown = Mathf.Max(maxDown, cur - y);
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
    public static string SinkGroundUnderParts(IEnumerable<GameObject> parts, float below = 0.05f, string undoPath = null) { return SinkGroundUnderParts(parts, below, undoPath, null); }
    /// <summary><see cref="SinkGroundUnderParts(IEnumerable{GameObject},float,string)"/> に**下げの下限**を足した物 ── <paramref name="floorMin"/>(x, z)が NaN でない節点は
    /// その値より下げない(指図 grading.seRoji.southKado「石垣の見え面から 1.0 以内に 床 −0.02 より低い升を残さない【硬】」・岡部 第114巡)。
    /// 法の駒の足が床の下へ根入れで埋まる所(隅の駒の稜は見え面の線より前へ出る)では、真上から最初に当たる面が床の下の足 ⇒ 下げると床に穴が開いた(r113 kado6 で 10.8)。
    /// 当たる先: 法のある石垣の足元に設計の床(路地・犬走り)を持つ所すべて(岡部 TW_Higashi_Se の背の路地。土井・松江松平を細かい地形へ移すときの同じ型)。</summary>
    public static string SinkGroundUnderParts(IEnumerable<GameObject> parts, float below, string undoPath, Func<float, float, float> floorMin)
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
        var low = new Dictionary<long, float>(); var lowN = new Dictionary<long, Vector2>(); var lowTop = new Dictionary<long, float>(); int nFloor = 0, nFront = 0;
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
                        if (floorMin != null) { float fm = floorMin(org.x + i * hs, org.z + j * hs); if (!float.IsNaN(fm) && y < fm) { y = fm; nFloor++; } }
                        if (!low.TryGetValue(k, out cur) || y < cur) { low[k] = y; lowN[k] = new Vector2(h.normal.x, h.normal.z); lowTop[k] = bb.max.y; }
                    }
            }
        }
        finally { foreach (var mc in tmp) if (mc != null) UnityEngine.Object.DestroyImmediate(mc); }
        // ⭐ 埋まった見え面は掘らない(第117巡・岡部 TW_Higashi_Se の南の隅 kado6): 法の見え面の下の節点を「面 − below」へ下げると、見え面の前の地表がその面より高い所
        //   (見え面の足が土に埋まる所)で、見え面と前の地表の間に深さ 1〜2.3m の割れ目が開いた。下げの下限 = **見え面の前の地表**
        //   (面の法線の水平の向きへ、どの駒の下でもない最初の節点の今の高さ)── 見え面が前の地表より上に出る所だけ下げる。天端(法線がほぼ鉛直)は従前どおり。
        if (low.Count > 0)
        {
            var fix = new List<KeyValuePair<long, float>>();
            foreach (var kv in low)
            {
                Vector2 nn; if (!lowN.TryGetValue(kv.Key, out nn)) continue;
                if (nn.magnitude < 0.25f)
                {
                    //   ⭐ 上を向いた面のうち埋まった石の上の面(駒の天端より 0.5 以上低い)は、今の地面より下で、まわり 3 升(0.75m)に駒の外の節点があれば、その最も低い地表より下げない
                    //   (EDO-0502 第132巡: 切坂の足で、隅の駒の法の根入れの石の上の面 12.75〜13.10 を「面 −0.05」へ掘り、溜り 13.29 の前に 0.1〜0.6 の窪みが残った)。
                    int ii = (int)(kv.Key >> 32), jj = (int)(uint)(kv.Key & 0xffffffff); float cur0 = td.GetHeight(ii, jj) + org.y; if (kv.Value >= cur0 - 1e-4f) continue;
                    //   ⛔ 天端(駒の天端から 0.5 以内の上の面)は従前どおり下げる ── 背の地盤が近い天端の縁を残すと表の石の上に土の斑が出た(第132巡の試し 3 本目)
                    float tpF; if (!lowTop.TryGetValue(kv.Key, out tpF) || kv.Value + below >= tpF - 0.5f) continue;
                    float gMinF = float.NaN;
                    for (int di = -3; di <= 3; di++) for (int dj = -3; dj <= 3; dj++)
                    {
                        int fi = ii + di, fj = jj + dj; if (fi < 0 || fj < 0 || fi >= R || fj >= R || low.ContainsKey(((long)fi << 32) ^ (uint)fj)) continue;
                        float gf = td.GetHeight(fi, fj) + org.y; if (float.IsNaN(gMinF) || gf < gMinF) gMinF = gf;
                    }
                    //   まわり 3 升がどれも駒の下(石垣が向き合う坂の足)で、当たった面が駒の天端より 0.5 以上低い(天端でない ── 埋まった石の上の面)なら、まわりの節点の今の高さの最低
                    if (float.IsNaN(gMinF))
                        for (int di = -3; di <= 3; di++) for (int dj = -3; dj <= 3; dj++)
                        { int fi = ii + di, fj = jj + dj; if (fi < 0 || fj < 0 || fi >= R || fj >= R) continue; float gf = td.GetHeight(fi, fj) + org.y; if (float.IsNaN(gMinF) || gf < gMinF) gMinF = gf; }
                    if (!float.IsNaN(gMinF) && kv.Value < gMinF) { fix.Add(new KeyValuePair<long, float>(kv.Key, Mathf.Min(gMinF, cur0))); nFront++; }
                    continue;
                }
                nn.Normalize();
                int i = (int)(kv.Key >> 32), j = (int)(uint)(kv.Key & 0xffffffff); float gF = float.NaN, gWalkMin = float.NaN;
                for (float w = hs; w <= 4f + 1e-3f; w += 0.5f * hs)
                {
                    int fi = Mathf.RoundToInt(i + nn.x * w / hs), fj = Mathf.RoundToInt(j + nn.y * w / hs); if (fi < 0 || fj < 0 || fi >= R || fj >= R) break;
                    if (low.ContainsKey(((long)fi << 32) ^ (uint)fj)) { float gw = td.GetHeight(fi, fj) + org.y; if (float.IsNaN(gWalkMin) || gw < gWalkMin) gWalkMin = gw; continue; }
                    gF = td.GetHeight(fi, fj) + org.y; break;
                }
                //   ⭐ 前の 4m がどれも駒の外形の中(石垣で挟んだ坂の足・隅の駒の法尻 ── 両脇の法の根入れが前の地表を全部覆う)なら、歩いた節点の今の高さの最も低い所を前の地表とする
                //   (EDO-0502 第132巡: R_KiriZaka の足で、両脇の石垣と隅の駒の埋まった法を「面 −0.05」へ掘り、表の溜り 13.29 の前に深さ 1.4〜1.9 の窪みが開いた)。
                //   当たる先: 二つの石垣が 4m 以内で向き合う所・出隅の駒の法尻(岡部 切坂・溜りの隅)── 法のある石垣を細かい地形に据える邸すべて
                if (float.IsNaN(gF)) gF = gWalkMin;
                if (!float.IsNaN(gF) && kv.Value < gF) { fix.Add(new KeyValuePair<long, float>(kv.Key, gF)); nFront++; }
            }
            foreach (var kv in fix) low[kv.Key] = kv.Value;
        }
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
        return "駒の下の地面を駒の面 −" + below.ToString("0.00") + " へ下げた: 駒の面 " + tmp.Count + "・節点 " + n + "・下げの最大 " + mx.ToString("F2") + "m(地形 " + t.name + ")" + (floorMin != null ? "・床の下限で止めた当たり " + nFloor : "") + "・見え面の前の地表で止めた節点 " + nFront;
    }

    /// <summary>**駒の足の下の地面を足の底 + <paramref name="bury"/> へ上げる(上げるだけ)**── 地面を先に焼き切った後(溝・土留めの下げの後)に、
    /// 座で据えた塀の足の下に残る浮きを地面で埋める(岡部 指図 heiFootSpec.order「帯と床を先に焼く → 練塀を run の座で据える(座より下げない)→ 足を測る」・第119巡)。
    /// 足 = 駒の壁体(屋根の材を除く)の下向きの面のうち、駒の最下点から <paramref name="footBand"/> 以内の物 ── 節点の真下から上へ光線を打ち(節点と前後左右 <paramref name="margin"/>)、
    /// 足に当たれば その高さ + bury を下限に。⛔ 下げない・⛔ <paramref name="keep"/>(溝・桝の外接)の中は触らない(溝の中に土を入れない)・<paramref name="allow"/> が偽の節点は触らない(区画の外)。
    /// 硬い(浮き0)。当たる先: 細かい地形の上に座で据えた塀(岡部 練塀・隅 ── 一枚物の腰 0.69 の内外の縁)。地面の高さの出どころは造成の面のまま ── 足の下と縁の一升だけ。
    /// <para>⭐ <paramref name="allowUnderFoot"/>(節点, 足の底)── 足の凸包の中の節点だけ <paramref name="allow"/> に代えて引く(第120巡 2026-10-12: 台の石垣の継ぎ目の切り欠き
    /// 〔段の点で二つの駒の天端の端が落ちる V〕の底の石の面を「石垣の駒の下」と読んで上げず、岡部 Kado_P24 の足の下に 1.04 の穴が残った ── 足の底を支えていない石の上は、
    /// 足に覆われる限り土で埋めてよい)。縁の節点(凸包の外・<paramref name="margin"/> 以内)は従来どおり <paramref name="allow"/>。</para>
    /// <para>⚠ 縁の節点の上げの上限 <paramref name="edgeCap"/> が小さいと、0.25m の格子で足の縁が二つの節点の間に落ちる所で、双一次の地表が縁で足の底を割る
    /// (第120巡: 岡部 辺19 の内の縁で 0.04 浮いた・上限 0.10 では届かなかった ⇒ 岡部は 0.30)。</para></summary>
    public static string FillUnderFoot(IEnumerable<GameObject> pieces, float footBand, float bury, float margin, IList<Bounds> keep, Func<Vector2, bool> allow, string undoPath = null, float edgeCap = 0.10f, Func<Vector2, float, bool> allowUnderFoot = null,
                                       IList<GameObject> keepPieces = null, float keepPad = 0.04f, Func<Vector2, float, bool> rimFull = null, Func<Vector2, float> capUnderFoot = null, float globalBand = float.NaN)
    {
        //   ⭐ globalBand: 足を駒の最下点から globalBand 以内の頂点に限る(水平に据えた棟 ── 長屋・附属屋)。⛔ 足を半径の内の最下点だけで判じると、低い頂点が
        //   半径 0.45 の内に無い所(妻の壁の上端・棟の高い桁)を「足」と読み、その下の地面を 7.85m 上げた(EDO-0502 第129巡 N41_0)。練塀(坂なり)は NaN のまま。
        //   ⭐ capUnderFoot(節点): 足の凸包の中と縁で allowUnderFoot / allow が偽(石が足を支える・石の駒の下)の節点も、上限 cap まで上げる(NaN = 触らない)── 第125巡 岡部:
        //   台の石垣の裏の縁の下の節点(石の天端の下・地表は低い)を触らずにおくと、その一升の双一次が石の裏の縁から足の内の縁(線から 1.46)まで落ち、足の内の縁が
        //   0.2〜0.48 浮いた(Kado_P7・P10・S_Hei_08・NW_Hei_1_3・P35)。上限 = 石の天端 −0.02(土は石の下に隠れる ── 天端に土を載せない)
        //   ⭐ rimFull(節点, 上げる高さ): 縁の節点の上げを edgeCap で止めない所(第122巡 ── 台の石垣の裏の犬走りの土: 外の側が台の天端で受けるので土の柱にならない)。
        //   岡部 d 1.05 の一続きで細い台(倍率 0.25・天端の幅 0.35)の裏に塀の足が載り、縁の上げ 0.30 で足の外の縁が 0.3〜1.4 浮いた
        //   ⭐ keepPieces: 触らない駒(溝・桝)を**駒の向きの外形**(局所の頂点の矩形 + keepPad)で引く(第122巡 2026-10-13)── ⛔ 世界の外接の箱(keep)は斜めの辺で
        //   塀の足の下まで覆い、岡部 北の辺(N_Hei_29〜35・P35)の足の下 4781 節点のうち 1282 を「溝の外接」で除いて 0.3〜1.4 の浮きを残した
        var kpL = new List<KeyValuePair<Matrix4x4, Vector4>>(); var kpB = new List<Bounds>(); var kpY = new List<float>();
        if (keepPieces != null)
            foreach (var kg in keepPieces)
            {
                if (kg == null || !kg.activeInHierarchy) continue; float a0, a1, b0, b1, y0;
                ObbFootprint(kg.transform, out a0, out a1, out b0, out b1, out y0); if (a0 > a1) continue;
                var sc = kg.transform.lossyScale; float px = keepPad / Mathf.Max(1e-4f, Mathf.Abs(sc.x)), pz = keepPad / Mathf.Max(1e-4f, Mathf.Abs(sc.z));
                kpL.Add(new KeyValuePair<Matrix4x4, Vector4>(kg.transform.worldToLocalMatrix, new Vector4(a0 - px, a1 + px, b0 - pz, b1 + pz)));
                var bb = RB(kg); bb.Expand(new Vector3(keepPad * 2f, 0f, keepPad * 2f)); kpB.Add(bb); kpY.Add(kg.transform.position.y);
            }
        Func<Vector2, bool> inKeepPiece = q =>
        {
            for (int k = 0; k < kpL.Count; k++)
            {
                var bb = kpB[k]; if (q.x < bb.min.x || q.x > bb.max.x || q.y < bb.min.z || q.y > bb.max.z) continue;
                var m = kpL[k].Key; var r = kpL[k].Value; var lp = m.MultiplyPoint3x4(new Vector3(q.x, kpY[k], q.y));
                if (lp.x >= r.x && lp.x <= r.y && lp.z >= r.z && lp.z <= r.w) return true;
            }
            return false;
        };
        // ⚠ 一枚物の練塀は底の面を持たない(閉じた断面は小口と側だけ ── 下からの光線は当たらない・第119巡の初回で 0 節点)⇒ 足 = 壁体の頂点のうち最下点から footBand 以内の物の
        //   水平の凸包(直線の駒は腰の矩形・隅の L 字は内の入りの三角を含む ── 小さく埋まるだけ)
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        var want = new Dictionary<long, float>(); int nKeep = 0, nOut = 0, nPc = 0;
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            var vs = BodyExRoof(g.transform, 999999); if (vs.Count == 0) continue;
            float yb = float.MaxValue; foreach (var v in vs) yb = Mathf.Min(yb, v.y);
            //   ⭐ 足 = その所の最下点から footBand 以内の頂点(⛔ 駒の最下点一つで切らない ── 坂なりの練塀〔const.heiLine.tenba・第121巡〕は底が勾配で傾き、
            //   最下点から 0.05 の頂点は低い端の一筋だけ ⇒ 足の凸包が低い端に縮み、残りの足の下に 0.3〜1.2 の空洞が残った)。足の高さも節点の近くの足の頂点で引く。
            //   平らな駒は従来と同じ(その所の最下点 = 駒の最下点)。
            const float FC = 0.15f; var cellV = new Dictionary<long, List<Vector3>>();
            Func<float, float, long> ck = (x, z) => ((long)Mathf.FloorToInt(x / FC) << 32) ^ (uint)Mathf.FloorToInt(z / FC);
            foreach (var v in vs) { long kk = ck(v.x, v.z); List<Vector3> l; if (!cellV.TryGetValue(kk, out l)) cellV[kk] = l = new List<Vector3>(); l.Add(v); }
            Func<float, float, float, float> localMin = (x, z, r) =>
            {
                float m = float.MaxValue; int cx = Mathf.FloorToInt(x / FC), cz = Mathf.FloorToInt(z / FC), rr = Mathf.CeilToInt(r / FC);
                for (int a = -rr; a <= rr; a++) for (int b = -rr; b <= rr; b++) { List<Vector3> l; if (!cellV.TryGetValue(((long)(cx + a) << 32) ^ (uint)(cz + b), out l)) continue; foreach (var w in l) if ((w.x - x) * (w.x - x) + (w.z - z) * (w.z - z) <= r * r) m = Mathf.Min(m, w.y); }
                return m;
            };
            var foot = new List<Vector2>(); var footY = new Dictionary<long, List<Vector3>>();
            //   ⭐ 足の判じは半径 FOOT_R の内の最下点から(footBand + 勾配の許し)── 半径 FC(0.15)の升の最下点では、一枚物の隅の駒の入隅の留め(hashira2・hei の
            //   下端 1.73)だけの升を「足」と読み、その下の節点を座 +1.8〜2.2 へ上げて塀の内に土の柱が立った(第125巡 岡部 P35 ほか 12 か所・線から 1.7)。
            //   壁の厚み 0.41 より広い半径なら、どの升にも下見板の下端が入る。勾配の許しは坂なりの駒の上限 1/8 × 半径。
            const float FOOT_R = 0.45f, FOOT_GRADE = 0.13f;
            foreach (var v in vs) if (v.y <= localMin(v.x, v.z, FOOT_R) + footBand + FOOT_GRADE * FOOT_R && (float.IsNaN(globalBand) || v.y <= yb + globalBand)) { foot.Add(new Vector2(v.x, v.z)); long kk = ck(v.x, v.z); List<Vector3> l; if (!footY.TryGetValue(kk, out l)) footY[kk] = l = new List<Vector3>(); l.Add(v); }
            Func<Vector2, float> ybAt = q =>
            {
                float m = float.MaxValue, bd = float.MaxValue, near = yb; int cx = Mathf.FloorToInt(q.x / FC), cz = Mathf.FloorToInt(q.y / FC);
                for (int a = -2; a <= 2; a++) for (int b = -2; b <= 2; b++) { List<Vector3> l; if (!footY.TryGetValue(((long)(cx + a) << 32) ^ (uint)(cz + b), out l)) continue;
                    foreach (var w in l) { float d2 = (w.x - q.x) * (w.x - q.x) + (w.z - q.y) * (w.z - q.y); if (d2 <= 0.25f * 0.25f) m = Mathf.Min(m, w.y); if (d2 < bd) { bd = d2; near = w.y; } } }
                return m < float.MaxValue ? m : near;
            };
            if (foot.Count < 3) continue;
            var arr = foot.ToArray(); var hi = EdoGeom.HullXZ(arr); if (hi == null || hi.Length < 3) continue;
            var hull = new Vector2[hi.Length]; for (int k = 0; k < hi.Length; k++) hull[k] = arr[hi[k]];
            nPc++;
            float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue; foreach (var q in hull) { x0 = Mathf.Min(x0, q.x); x1 = Mathf.Max(x1, q.x); z0 = Mathf.Min(z0, q.y); z1 = Mathf.Max(z1, q.y); }
            int i0 = Mathf.Max(0, Mathf.CeilToInt((x0 - margin - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.FloorToInt((x1 + margin - org.x) / hs));
            int j0 = Mathf.Max(0, Mathf.CeilToInt((z0 - margin - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.FloorToInt((z1 + margin - org.z) / hs));
            for (int j = j0; j <= j1; j++)
                for (int i = i0; i <= i1; i++)
                {
                    var q = new Vector2(org.x + i * hs, org.z + j * hs);
                    bool inHull = EdoGeom.PIP(hull, q);
                    if (!inHull && EdgeDistPublic(hull, q) > margin + 1e-4f) continue;
                    float ybq = ybAt(q);
                    bool okq = inHull && allowUnderFoot != null ? allowUnderFoot(q, ybq) : (allow == null || allow(q));
                    float capQ = float.NaN;
                    if (!okq && capUnderFoot != null) { capQ = capUnderFoot(q); if (!float.IsNaN(capQ)) okq = true; }
                    if (!okq) { nOut++; continue; }
                    bool kp = false; if (keep != null) foreach (var kb in keep) if (q.x >= kb.min.x && q.x <= kb.max.x && q.y >= kb.min.z && q.y <= kb.max.z) { kp = true; break; }
                    if (!kp && kpL.Count > 0) kp = inKeepPiece(q);
                    if (kp) { nKeep++; continue; }
                    long k2 = ((long)i << 32) ^ (uint)j; float y = ybq + bury, cur;
                    if (!float.IsNaN(capQ)) y = Mathf.Min(y, capQ);
                    // 足の外の縁の節点は上げを edgeCap まで(⛔ 縁の外が急に落ちる所で幅一升・高さ 2m の土の柱が立った ── 岡部 P24 の外・第119巡)。足の下(凸包の中)は隠れるので上限なし
                    if (!inHull && (rimFull == null || !rimFull(q, y))) { float g0 = td.GetHeight(i, j) + org.y; y = Mathf.Min(y, g0 + edgeCap); }
                    if (!want.TryGetValue(k2, out cur) || y > cur) want[k2] = y;
                }
        }
        int n = 0; float mx = 0f; var undo = new List<float[]>();
        if (want.Count > 0)
        {
            int i0 = int.MaxValue, i1 = int.MinValue, j0 = int.MaxValue, j1 = int.MinValue;
            foreach (var k in want.Keys) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); i0 = Mathf.Min(i0, i); i1 = Mathf.Max(i1, i); j0 = Mathf.Min(j0, j); j1 = Mathf.Max(j1, j); }
            var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
            foreach (var kv in want)
            {
                int i = (int)(kv.Key >> 32), j = (int)(uint)(kv.Key & 0xffffffff);
                float cur = H[j - j0, i - i0] * td.size.y + org.y;
                if (kv.Value <= cur + 1e-4f) continue;
                mx = Mathf.Max(mx, kv.Value - cur); undo.Add(new[] { i, j, (kv.Value - org.y) / td.size.y, H[j - j0, i - i0] }); H[j - j0, i - i0] = (kv.Value - org.y) / td.size.y; n++;
            }
            if (n > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        }
        if (undoPath != null) WriteUndo(undoPath, t.name, undo);
        return "足の下の地面を足の底 +" + bury.ToString("0.00") + " へ上げた(上げるだけ・足の凸包 + 縁 " + margin.ToString("0.00") + "): 駒 " + nPc + "・足の下の節点 " + want.Count + "・上げた " + n + "・最大 " + mx.ToString("F2") + "m・溝の外接で除いた " + nKeep + "・区画の外で除いた " + nOut;
    }

    /// <summary>塀の前の帯(<see cref="PlaneBand"/>)の一辺: 線の始め a・走りの向き u・内向き inw・長さ len・帯の内への離れ [q0, q1](走り s の関数)・面の高さ yAt(s)。</summary>
    public class BandEdge { public string name; public Vector2 a, u, inw; public float len; public Func<float, float> q0, q1, yAt; public Func<float, float> qCap; public float capBatter; }
    /// <summary>**塀の前の帯の地面を一枚の面にする**(上げも下げも・第123巡 2026-10-13 岡部 施主「犬走りの地面は座の線と同じ高さ・同じ勾配の一枚の面」【硬: 土の楔 0】)。
    /// 各辺の帯(走り s ∈ [0, len]・線から内へ q ∈ [q0(s), q1(s)])の節点を yAt(s) + <paramref name="off"/> にする(辺の隅で二つの帯に入る節点は高い方)。
    /// 帯は呼び手が決める(岡部: 台の天端の前の縁 c から塀の腰の外の縁の一升奥まで ── 塀の裏・内の帯は触らない)。<paramref name="allow"/> が偽の節点は触らない。
    /// 段は yAt が s で跳ぶ所で一升の中の段になる(呼び手は段の脇の一升を低い側の高さにする ── 双一次の斜めが下の天端の上へ出ないように)。⛔ 部材の基準点を使わない(面は指図の座の線)。当たる先: 天端の線の上の練塀の前(岡部の外周)。</summary>
    /// <para>⭐ <paramref name="recPath"/>: 帯の**設計の高さ**(節点 → 面の高さ・肩の下げの上限)を残す(<see cref="LoadNodeTargets"/> で造成QA が引く ── EDO-0502 第129巡)。
    /// 帯は塀の座の線(天端の線)から解くので算出物 graded は知らない。地形の今の高さは書かない。</para>
    public static string PlaneBand(IList<BandEdge> edges, Func<Vector2, bool> allow, float off, string undoPath = null, float ext = 0f, string recPath = null)
    {
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        var want = new Dictionary<long, float>(); var cap = new Dictionary<long, float>(); var extW = new Dictionary<long, float>();
        //   ⭐ 下げるだけの所(第123巡): 帯の手前の見え面の肩(qCap(s) ≤ q < q0)と辺の端の先(ext)── 面の高さより上の土だけ下げる
        //   (P35: 辺34 の端の先へ延ばした帯が上の踏み面の座で辺35 の下の天端の上へ土を 0.94 盛った・見え面の肩の土は誰も下げていなかった)
        foreach (var be in edges)
        {
            Vector2 b = be.a + be.u * be.len; float qm = 3f;
            float x0 = Mathf.Min(be.a.x, b.x) - qm, x1 = Mathf.Max(be.a.x, b.x) + qm, z0 = Mathf.Min(be.a.y, b.y) - qm, z1 = Mathf.Max(be.a.y, b.y) + qm;
            int i0 = Mathf.Max(0, Mathf.CeilToInt((x0 - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.FloorToInt((x1 - org.x) / hs));
            int j0 = Mathf.Max(0, Mathf.CeilToInt((z0 - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.FloorToInt((z1 - org.z) / hs));
            for (int j = j0; j <= j1; j++)
                for (int i = i0; i <= i1; i++)
                {
                    var p = new Vector2(org.x + i * hs, org.z + j * hs); var r = p - be.a; float sv = Vector2.Dot(r, be.u), qv = Vector2.Dot(r, be.inw);
                    //   ext: 辺の端の先へも帯を延ばす(出隅の外の扇の所 ── 隅の駒の腰の縁が二つの辺の帯のどちらにも入らず浮いた)。面の高さは端の値
                    if (sv < -ext || sv > be.len + ext) continue; float sc = Mathf.Clamp(sv, 0f, be.len);
                    float qlo = be.qCap != null ? Mathf.Min(be.qCap(sc), be.q0(sc)) : be.q0(sc); if (qv < qlo || qv > be.q1(sc)) continue;
                    if (allow != null && !allow(p)) continue;
                    float y = be.yAt(sc) + off; if (float.IsNaN(y)) continue;
                    long k = ((long)i << 32) ^ (uint)j; float cur;
                    //   辺の端の先(ext)は、どの辺の帯の走りの内にも入らない節点(出隅の外の扇)だけを面にする ── 他の辺の帯の内では使わない(P35 の盛りの元)
                    if (qv < be.q0(sc)) { y -= be.capBatter * (be.q0(sc) - qv); if (!cap.TryGetValue(k, out cur) || y < cur) cap[k] = y; }   // 見え面の肩: 法の線より上の土だけ下げる
                    else if (sv < 0f || sv > be.len)
                    {
                        //   ⭐ 他の辺の走りの内で、その辺の帯の奥(q1)より線の側の節点(見え面の前・肩・帯)は使わない(第126巡 岡部 P35: 辺34 の延長が辺35 の見え面の前の
                        //   節点 線から 0.2〜0.8 を上の座 23.6 へ上げ、見え面の前に高さ 2m の土の柱が立った ── const.heiLine.faceFront【硬】)
                        bool other = false;
                        foreach (var ot in edges) { if (ot == be) continue; var r2 = p - ot.a; float s2 = Vector2.Dot(r2, ot.u), q2 = Vector2.Dot(r2, ot.inw); if (s2 < 0f || s2 > ot.len) continue; if (q2 > -0.5f && q2 < ot.q1(s2)) { other = true; break; } }
                        if (!other && (!extW.TryGetValue(k, out cur) || y > cur)) extW[k] = y;
                    }
                    else if (!want.TryGetValue(k, out cur) || y > cur) want[k] = y;
                }
        }
        int nUp = 0, nDn = 0; float mUp = 0f, mDn = 0f; var undo = new List<float[]>();
        foreach (var kv in extW) if (!want.ContainsKey(kv.Key)) want[kv.Key] = kv.Value;
        if (recPath != null) SaveNodeTargets(recPath, t.name, want, cap);
        foreach (var kv in cap) if (!want.ContainsKey(kv.Key)) want[kv.Key] = float.PositiveInfinity;   // 下げるだけ(面の高さは cap)
        if (want.Count > 0)
        {
            int i0 = int.MaxValue, i1 = int.MinValue, j0 = int.MaxValue, j1 = int.MinValue;
            foreach (var k in want.Keys) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); i0 = Mathf.Min(i0, i); i1 = Mathf.Max(i1, i); j0 = Mathf.Min(j0, j); j1 = Mathf.Max(j1, j); }
            var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
            foreach (var kv in want)
            {
                int i = (int)(kv.Key >> 32), j = (int)(uint)(kv.Key & 0xffffffff);
                float cur = H[j - j0, i - i0] * td.size.y + org.y; float tgt = float.IsPositiveInfinity(kv.Value) ? cur : kv.Value; float cp;
                if (cap.TryGetValue(kv.Key, out cp)) tgt = Mathf.Min(tgt, cp);
                float dv = tgt - cur; if (Mathf.Abs(dv) < 1e-4f) continue;
                if (dv > 0f) { nUp++; mUp = Mathf.Max(mUp, dv); } else { nDn++; mDn = Mathf.Max(mDn, -dv); }
                undo.Add(new[] { i, j, (tgt - org.y) / td.size.y, H[j - j0, i - i0] }); H[j - j0, i - i0] = (tgt - org.y) / td.size.y;
            }
            if (nUp + nDn > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        }
        if (undoPath != null) WriteUndo(undoPath, t.name, undo);
        return "塀の前の帯を座の線の一枚の面(座 " + off.ToString("+0.00;-0.00") + ")へ: 帯の節点 " + want.Count + "・上げた " + nUp + "(最大 " + mUp.ToString("F2") + ")・下げた " + nDn + "(最大 " + mDn.ToString("F2") + ")";
    }

    /// <summary>節点(地形の格子の i, j)ごとの設計の高さ <paramref name="want"/>(面の高さ)と上限 <paramref name="cap"/>(下げるだけの所)を <paramref name="path"/> へ残す。
    /// 造成QA が「設計面(graded)からの差が指図どおりの帯の跡か」を domain reload の後も引けるように。当たる先: <see cref="PlaneBand"/>(岡部 塀の前の帯)。</summary>
    public static void SaveNodeTargets(string path, string terrainName, Dictionary<long, float> want, Dictionary<long, float> cap)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var sb = new System.Text.StringBuilder("T\t" + terrainName + "\n");
        if (want != null) foreach (var kv in want) { if (float.IsInfinity(kv.Value) || float.IsNaN(kv.Value)) continue; sb.Append("w\t" + (int)(kv.Key >> 32) + "\t" + (int)(uint)(kv.Key & 0xffffffff) + "\t" + kv.Value.ToString("R", inv) + "\n"); }
        if (cap != null) foreach (var kv in cap) sb.Append("c\t" + (int)(kv.Key >> 32) + "\t" + (int)(uint)(kv.Key & 0xffffffff) + "\t" + kv.Value.ToString("R", inv) + "\n");
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path)); System.IO.File.WriteAllText(path, sb.ToString());
    }
    /// <summary><see cref="SaveNodeTargets"/> の足し書き(同じ地形の記録へ節点 → 設計の高さを追記 ── 後の行が勝つ)。無ければ新しく起こす。
    /// 当たる先: 一つの Stage の中で何度も地面を書く手(岡部 Stage3d の溝の両脇の帯・段落ちの両脇・天端の裏石の帯 ── 造成QA が同じ記録を引く・第131巡)。</summary>
    public static void AppendNodeTargets(string path, string terrainName, Dictionary<long, float> want)
    {
        if (path == null || want == null || want.Count == 0) return;
        var inv = System.Globalization.CultureInfo.InvariantCulture; var sb = new System.Text.StringBuilder();
        if (!System.IO.File.Exists(path)) sb.Append("T\t" + terrainName + "\n");
        foreach (var kv in want) { if (float.IsInfinity(kv.Value) || float.IsNaN(kv.Value)) continue; sb.Append("w\t" + (int)(kv.Key >> 32) + "\t" + (int)(uint)(kv.Key & 0xffffffff) + "\t" + kv.Value.ToString("R", inv) + "\n"); }
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path)); System.IO.File.AppendAllText(path, sb.ToString());
    }
    /// <summary><see cref="SaveNodeTargets"/> を読む ⟶ 節点 → (面の高さ NaN 可, 上限 NaN 可)。地形の名が違えば・無ければ null。</summary>
    public static Dictionary<long, Vector2> LoadNodeTargets(string path, string terrainName)
    {
        if (!System.IO.File.Exists(path)) return null; var inv = System.Globalization.CultureInfo.InvariantCulture; var res = new Dictionary<long, Vector2>();
        foreach (var ln in System.IO.File.ReadAllLines(path))
        {
            var f = ln.Split('\t'); if (f.Length < 2) continue;
            if (f[0] == "T") { if (f[1] != terrainName) return null; continue; }
            if (f.Length < 4) continue; long k = ((long)int.Parse(f[1]) << 32) ^ (uint)int.Parse(f[2]); float y = float.Parse(f[3], inv);
            Vector2 v; if (!res.TryGetValue(k, out v)) v = new Vector2(float.NaN, float.NaN);
            if (f[0] == "w") v.x = y; else if (f[0] == "c") v.y = y; res[k] = v;
        }
        return res;
    }

    /// <summary>**台の石垣の天端の上に載った土を天端の下へ下げる**(下げるだけ・第122巡 2026-10-13 岡部 const.heiLine.kidanCrest【硬】「台の天端に土の楔を見せない」)。
    /// 0.25m の格子では、塀の足の下の地面(内の帯・座より高い)の節点が台の天端の上の一升に掛かり、双一次の地表が天端の上へ斜めに出る(塀の外の縁の前 0.07 の帯で 0.3〜0.8)。
    /// 段の所は上の踏み面の土が下の天端の上へこぼれる(0.8)。節点の真上に石の駒の**平らな天端**(前後左右 <paramref name="probe"/> の天端の差がどれも
    /// <paramref name="flatTol"/> 以内 ── 法の見え面は除く)があり、地面がその天端 − <paramref name="below"/> より高ければ下げる。<paramref name="allow"/> が偽の節点は触らない。
    /// 硬い(土の楔 0)。⛔ 上げない。当たる先: 天端の線の台の石垣(岡部の外周)── 石垣の天端が地表に接する所すべてに効く。</summary>
    public static string LowerSoilOnCrest(IList<GameObject> stones, Func<Vector2, bool> allow, float below = 0.02f, float probe = 0.08f, float flatTol = 0.04f, string undoPath = null)
    {
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        var pt = new PartTops(stones); var want = new Dictionary<long, float>();
        foreach (var g in stones)
        {
            if (g == null || !g.activeInHierarchy) continue; var b = RB(g);
            int i0 = Mathf.Max(0, Mathf.CeilToInt((b.min.x - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.FloorToInt((b.max.x - org.x) / hs));
            int j0 = Mathf.Max(0, Mathf.CeilToInt((b.min.z - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.FloorToInt((b.max.z - org.z) / hs));
            for (int j = j0; j <= j1; j++)
                for (int i = i0; i <= i1; i++)
                {
                    long k = ((long)i << 32) ^ (uint)j; if (want.ContainsKey(k)) continue;
                    var q = new Vector2(org.x + i * hs, org.z + j * hs); if (allow != null && !allow(q)) continue;
                    string who; float st = pt.Top(q.x, q.y, out who); if (float.IsNaN(st)) continue;
                    bool flat = true;
                    foreach (var d in new[] { new Vector2(probe, 0f), new Vector2(-probe, 0f), new Vector2(0f, probe), new Vector2(0f, -probe) })
                    { string w2; float s2 = pt.Top(q.x + d.x, q.y + d.y, out w2); if (float.IsNaN(s2) || Mathf.Abs(s2 - st) > flatTol) { flat = false; break; } }
                    if (!flat) continue;
                    want[k] = st - below;
                }
        }
        int n = 0; float mx = 0f; var undo = new List<float[]>();
        if (want.Count > 0)
        {
            int i0 = int.MaxValue, i1 = int.MinValue, j0 = int.MaxValue, j1 = int.MinValue;
            foreach (var k in want.Keys) { int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); i0 = Mathf.Min(i0, i); i1 = Mathf.Max(i1, i); j0 = Mathf.Min(j0, j); j1 = Mathf.Max(j1, j); }
            var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1);
            foreach (var kv in want)
            {
                int i = (int)(kv.Key >> 32), j = (int)(uint)(kv.Key & 0xffffffff);
                float cur = H[j - j0, i - i0] * td.size.y + org.y;
                if (kv.Value >= cur - 1e-4f) continue;
                mx = Mathf.Max(mx, cur - kv.Value); undo.Add(new[] { i, j, (kv.Value - org.y) / td.size.y, H[j - j0, i - i0] }); H[j - j0, i - i0] = (kv.Value - org.y) / td.size.y; n++;
            }
            if (n > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
        }
        if (undoPath != null) WriteUndo(undoPath, t.name, undo);
        return "台の天端の上の土を天端 −" + below.ToString("0.00") + " へ下げた(平らな天端の真上の節点 " + want.Count + "・下げた " + n + "・最大 " + mx.ToString("F2") + "m)";
    }

    /// <summary>**台の石垣の見え面の前の地面を見え面の足より上へ出さない**(下げるだけ・第126巡 2026-10-13 岡部 const.heiLine.faceFront【硬】
    /// 「見え面から地面が突き出さない・出隅で台の石が抜ける所を作らない」)。見え面の足 = **区画の外の地表**(線から外へ <paramref name="outRef"/> の所 ── 区画の外は触らない)。
    /// 区画の線から内へ <paramref name="frontDepth"/>(節点)までの節点のうち、(1) 真上に石の**見え面**(上向きの面の法線の水平の成分 ≥ 0.25 ── 法)があれば
    /// 外の地表へ(石の底が外の地表より上なら底で止め、台の丈の不足に数える ── 第127巡)、(2) 真上に石が無く、内へ水平に 1.5m 以内に石が在れば(見え面の前・出隅の継ぎ目の口)外の地表へ下げる。
    /// 平らな天端の下(法線がほぼ鉛直)は触らない(天端の土は <see cref="LowerSoilOnCrest"/>)。<paramref name="keepOff"/>(門・石段・溝の駒)の真下の節点は触らない。
    /// 0.25m の格子では、塀の前の帯の延長(<see cref="PlaneBand"/> の ext)・足の下の上げが見え面の前の節点を座の高さへ上げ、見え面の前に幅一升・高さ 2〜3m の土の柱が立った
    /// (岡部 P35 の両脇・北 辺28〜35・P24)。外の地表が石の底より低い所(台の丈の不足)は下げても足が出ない ⇒ 下げずに数えて返す(台の丈を増す方で納める)。
    /// 硬い(見え面の前の土 0)。当たる先: 細かい地形の上に法のある石垣を外周に据える邸すべて(岡部 外周の台・土井・松江松平を細かい地形へ移すとき)。</summary>
    public static string LowerGroundBeforeFace(IList<GameObject> stones, Vector2[] poly, Func<Vector2, bool> allow, Func<Vector2, float> frontDepth, float outRef = 0.3f, float below = 0.05f,
                                               IList<GameObject> keepOff = null, string undoPath = null, IList<GameObject> keepFoot = null)
    {
        var t = T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        //   ⭐ keepFoot(塀・隅の駒): 足の帯(壁体の頂点のうち、その所の最下点 +0.10 以内)の凸包と、その一升の内の節点は触らない(第127巡 ── 軒込みの上面で除くと、
        //   出隅で軒が見え面の前の節点まで覆い、土が残った P8・P9・P24)
        var footHulls = new List<Vector2[]>();
        if (keepFoot != null)
            foreach (var g in keepFoot)
            {
                if (g == null || !g.activeInHierarchy) continue; var vs = BodyExRoof(g.transform, 999999); if (vs.Count < 3) continue;
                var cellMin = new Dictionary<long, float>(); const float FC = 0.3f;
                foreach (var v in vs) { long k = ((long)Mathf.FloorToInt(v.x / FC) << 32) ^ (uint)Mathf.FloorToInt(v.z / FC); float m; if (!cellMin.TryGetValue(k, out m) || v.y < m) cellMin[k] = v.y; }
                var fp = new List<Vector2>();
                foreach (var v in vs)
                {
                    int cx = Mathf.FloorToInt(v.x / FC), cz = Mathf.FloorToInt(v.z / FC); float m = float.MaxValue;
                    for (int da = -1; da <= 1; da++) for (int db = -1; db <= 1; db++) { float mm; if (cellMin.TryGetValue(((long)(cx + da) << 32) ^ (uint)(cz + db), out mm)) m = Mathf.Min(m, mm); }
                    if (v.y <= m + 0.10f) fp.Add(new Vector2(v.x, v.z));
                }
                if (fp.Count < 3) continue; var arr = fp.ToArray(); var hi = EdoGeom.HullXZ(arr); if (hi == null || hi.Length < 3) continue;
                var hull = new Vector2[hi.Length]; for (int k = 0; k < hi.Length; k++) hull[k] = arr[hi[k]]; footHulls.Add(hull);
            }
        Func<Vector2, bool> nearFoot = q => { foreach (var h in footHulls) if (EdoGeom.PIP(h, q) || EdgeDistPublic(h, q) <= hs + 1e-3f) return true; return false; };
        var tmp = new List<MeshCollider>(); var mine = new HashSet<Collider>(); var bb = new Bounds(); bool hasB = false;
        foreach (var g in stones)
        {
            if (g == null || !g.activeInHierarchy) continue;
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue; var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
                var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; tmp.Add(mc); mine.Add(mc);
                if (!hasB) { bb = rr.bounds; hasB = true; } else bb.Encapsulate(rr.bounds);
            }
        }
        var keepTops = keepOff == null || keepOff.Count == 0 ? null : new PartTops(keepOff);
        Physics.SyncTransforms();
        int n = 0, nFace = 0, nFront = 0, nShort = 0, slitN = 0; float mx = 0f, worstShort = 0f; string wMx = "", wShort = ""; var undo = new List<float[]>();
        try
        {
            if (!hasB) return "見え面の前の地面: 石が無い";
            bb.Expand(new Vector3(1.2f, 0f, 1.2f));
            int i0 = Mathf.Max(0, Mathf.CeilToInt((bb.min.x - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.FloorToInt((bb.max.x - org.x) / hs));
            int j0 = Mathf.Max(0, Mathf.CeilToInt((bb.min.z - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.FloorToInt((bb.max.z - org.z) / hs));
            var H = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1); var H0 = (float[,])H.Clone();
            Func<Vector2, float> G0 = p =>
            {   // 書き換える前の地表(双一次)── 外の地表は区画の外の節点で決まり、この関数は触らない
                float fx = (p.x - org.x) / hs - i0, fz = (p.y - org.z) / hs - j0; int ix = Mathf.FloorToInt(fx), iz = Mathf.FloorToInt(fz);
                if (ix < 0 || iz < 0 || ix + 1 > i1 - i0 || iz + 1 > j1 - j0) return EdoBuild.Ground(p.x, p.y);
                float ax = fx - ix, az = fz - iz;
                float h = Mathf.Lerp(Mathf.Lerp(H0[iz, ix], H0[iz, ix + 1], ax), Mathf.Lerp(H0[iz + 1, ix], H0[iz + 1, ix + 1], ax), az);
                return h * td.size.y + org.y;
            };
            int nE = poly.Length; var frontTgt = new Dictionary<long, float>(); var faceNode = new HashSet<long>(); var crestNode = new List<long>();
            for (int j = j0; j <= j1; j++)
                for (int i = i0; i <= i1; i++)
                {
                    var q = new Vector2(org.x + i * hs, org.z + j * hs);
                    if (!EdoGeom.PIP(poly, q) || (allow != null && !allow(q))) continue;
                    // 最も近い辺と線からの離れ
                    int be = -1; float bd = float.MaxValue; Vector2 foot = q;
                    for (int e = 0; e < nE; e++) { Vector2 a = poly[e], b = poly[(e + 1) % nE]; float L = (b - a).magnitude; if (L < 1e-4f) continue; Vector2 u = (b - a) / L; float s = Mathf.Clamp(Vector2.Dot(q - a, u), 0f, L); var f = a + u * s; float d = (q - f).magnitude; if (d < bd) { bd = d; be = e; foot = f; } }
                    if (be < 0) continue; float fd = frontDepth(q); if (float.IsNaN(fd) || bd > fd) continue;
                    Vector2 o = PolyEdgeOut(poly, be);
                    //   外の地表: 線の足から外へ outRef(出隅の扇では線の足 = 頂点 ⇒ 頂点から q の向きの逆へ)
                    Vector2 away = bd > 1e-3f ? (foot - q).normalized : o; var pr = foot + away * outRef; if (EdoGeom.PIP(poly, pr)) continue;
                    float yRef = G0(pr); if (float.IsNaN(yRef)) continue;
                    if (keepTops != null) { string kw; if (!float.IsNaN(keepTops.Top(q.x, q.y, out kw))) continue; }
                    if (footHulls.Count > 0 && nearFoot(q)) continue;
                    float cur = H[j - j0, i - i0] * td.size.y + org.y;
                    // 真上の石
                    float topY = float.NaN; Vector3 topN = Vector3.up;
                    foreach (var h in Physics.RaycastAll(new Vector3(q.x, bb.max.y + 2f, q.y), Vector3.down, bb.size.y + 6f)) { if (!mine.Contains(h.collider)) continue; if (float.IsNaN(topY) || h.point.y > topY) { topY = h.point.y; topN = h.normal; } }
                    float tgt;
                    if (!float.IsNaN(topY))
                    {
                        if (new Vector2(topN.x, topN.z).magnitude < 0.25f) { crestNode.Add(((long)i << 32) ^ (uint)j); continue; }   // 平らな天端の下は触らない(口の脇は後で)
                        //   ⭐ 第127巡: 見え面の下の節点も外の地表へ(面 −0.05 で止めると、前の節点〔外の地表〕との一升の斜めが法 1:0.25 より緩く、
                        //   見え面の足に高さ 0.3〜0.5 の土の歯が並んだ)── 地面は石の中で崖になり見えない。石の底が外の地表より上なら底で止める(台の丈の不足として数える)
                        float yBot = float.NaN; foreach (var h in Physics.RaycastAll(new Vector3(q.x, bb.min.y - 2f, q.y), Vector3.up, bb.size.y + 6f)) { if (!mine.Contains(h.collider)) continue; if (float.IsNaN(yBot) || h.point.y < yBot) yBot = h.point.y; }
                        tgt = yRef; if (!float.IsNaN(yBot) && yBot > yRef + 0.02f) { tgt = yBot; nShort++; if (yBot - yRef > worstShort) { worstShort = yBot - yRef; wShort = "(" + q.x.ToString("F1") + "," + q.y.ToString("F1") + ") 見え面の下"; } }
                        nFace++; faceNode.Add(((long)i << 32) ^ (uint)j);
                    }
                    else
                    {
                        //   内へ水平に 1.5m 以内に石(見え面の前・出隅の継ぎ目の口)── 外の地表の高さと、今の地表の高さの二つで引く
                        Vector2 inw = -away; bool hit = false;
                        foreach (float yy in new[] { yRef + 0.05f, cur - 0.02f, 0.5f * (yRef + cur) })
                        {
                            foreach (var h in Physics.RaycastAll(new Vector3(q.x, yy, q.y), new Vector3(inw.x, 0f, inw.y), 1.5f)) if (mine.Contains(h.collider)) { hit = true; break; }
                            if (hit) break;
                        }
                        if (!hit) continue;
                        tgt = yRef; nFront++; frontTgt[((long)i << 32) ^ (uint)j] = yRef;
                        //   台の丈の不足: 外の地表 +0.02 の高さで内へ引いた光線が石に当たらず、上で当たる ⇒ 石の底が外の地表より上(下げると足が出る ⇒ 下げない)
                        bool lowHit = false; foreach (var h in Physics.RaycastAll(new Vector3(q.x, yRef + 0.02f, q.y), new Vector3(inw.x, 0f, inw.y), 1.5f)) if (mine.Contains(h.collider)) { lowHit = true; break; }
                        if (!lowHit && cur > yRef + 0.02f)
                        {
                            float yb = float.NaN; for (float yy = yRef + 0.05f; yy <= cur; yy += 0.05f) { bool hh = false; foreach (var h in Physics.RaycastAll(new Vector3(q.x, yy, q.y), new Vector3(inw.x, 0f, inw.y), 1.5f)) if (mine.Contains(h.collider)) { hh = true; break; } if (hh) { yb = yy; break; } }
                            if (!float.IsNaN(yb)) { nShort++; if (yb - yRef > worstShort) { worstShort = yb - yRef; wShort = "(" + q.x.ToString("F1") + "," + q.y.ToString("F1") + ") 辺" + be; } tgt = Mathf.Max(tgt, yb - 0.02f); }
                        }
                    }
                    if (tgt >= cur - 1e-4f) continue;
                    if (cur - tgt > mx) { mx = cur - tgt; wMx = "(" + q.x.ToString("F1") + "," + q.y.ToString("F1") + ") 辺" + be; }
                    undo.Add(new[] { i, j, (tgt - org.y) / td.size.y, H[j - j0, i - i0] }); H[j - j0, i - i0] = (tgt - org.y) / td.size.y; n++;
                }
            //   ⭐ 口の脇の天端の下の節点(第127巡 P35・P22): 出隅の口・継ぎ目の口の前の節点を下げても、隣の天端の下の節点が天端の高さのままだと、
            //   一升の斜めが口から天端まで立ち上がり、口の上端に土の切れ端が見えた ⇒ 四方の隣に口の前の節点がある天端の下の節点も、その節点の下げ先の高い方へ
            int nSlit = 0;
            foreach (var k in crestNode)
            {
                int i = (int)(k >> 32), j = (int)(uint)(k & 0xffffffff); float best = float.NaN;
                foreach (var d in new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) })
                { float y2; if (frontTgt.TryGetValue(((long)(i + d.x) << 32) ^ (uint)(j + d.y), out y2) && (float.IsNaN(best) || y2 > best)) best = y2; }
                if (float.IsNaN(best)) continue;
                float cur = H[j - j0, i - i0] * td.size.y + org.y; if (best >= cur - 1e-4f) continue;
                undo.Add(new[] { i, j, (best - org.y) / td.size.y, H[j - j0, i - i0] }); H[j - j0, i - i0] = (best - org.y) / td.size.y; n++; nSlit++;
            }
            if (n > 0) { td.SetHeights(i0, j0, H); AssetDatabase.SaveAssetIfDirty(td); }
            slitN = nSlit;
        }
        finally { foreach (var mc in tmp) if (mc != null) UnityEngine.Object.DestroyImmediate(mc); }
        if (undoPath != null) WriteUndo(undoPath, t.name, undo);
        return "口の脇の天端の下 " + slitN + "・見え面の前の地面を見え面の足(外の地表)へ下げた: 見え面の下 " + nFace + "・見え面の前 " + nFront + "・下げた " + n + "(最大 " + mx.ToString("F2") + " @" + wMx + ")"
               + (nShort > 0 ? "・⚠ 台の丈の不足(石の底が外の地表より上)" + nShort + " 節点・最大 " + worstShort.ToString("F2") + "m @" + wShort + " ── 台を深くする方で納める" : "・台の丈の不足 0");
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
