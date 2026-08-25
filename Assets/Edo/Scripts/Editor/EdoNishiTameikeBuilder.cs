// 溜池南西岸の4屋敷ビルダー (2026-08-08)
//   黄=土岐丹波守(頼旨/寄合3500石)  赤=横田筑後守(春松/9500石=旗本最高禄)
//   水=山口筑前守(弘敞/牛久藩1万石上屋敷)  緑=松平日向守(直春/糸魚川藩1万石上屋敷)
// 区画=ユーザー下書き線(EdoSketch 4色)。門位置=尾張屋版赤坂絵図(NDL1286666)の文字向き読取。
// 門格式=『青標帋』天保11年: 1万石大名=長屋門+両番所 / 旗本=長屋門(h_mon)。
// 各段階は既存グループがあればスキップ(手直し保護)。破壊的作り直しは force=true のみ。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoNishiTameikeBuilder
{
    // ---------- assets ----------
    const string PKnagayaC = EdoAssets.Eg.KnagayaC;
    const string PKnagayaL = EdoAssets.Eg.KnagayaL;
    const string PKnagayaR = EdoAssets.Eg.KnagayaR;
    const string PHei = EdoAssets.Eg.DobeiCenter;
    const string PHmon = EdoAssets.Eg.Hmon;
    const string PNmon = EdoAssets.Eg.Nagayamon;
    const string PBansho = EdoAssets.Eg.Bansho;
    const string PKura = EdoAssets.Eg.Kura;
    const string PHouse = EdoAssets.VK.House;
    const string PHouseB = EdoAssets.VK.HouseB;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PBigHouse = EdoAssets.VK.BigHouse;
    const float ES = 1.818f; // edogoyomi scale
    const float PITCH = 7.81f;

    // ---------- estate data ----------
    public class Estate
    {
        public string group, label;
        public Vector2[] poly;      // sketch corners in order
        public int front;           // edge index Pi->Pi+1 carrying the gate
        public float gateT = 0.5f;  // param along front edge
        public string gateType;     // h_mon | nagayamon
        public int bansho;          // number of bansho
        public int[] nagayaEdges;   // blind-nagaya edges (excluding front)
        public int[] dobeiEdges;    // dobei edges
        public float pad;           // main pad (Yamaguchi uses terraces instead)
    }

    // 区画=ユーザー下書き線 v2 (2026-08-08 現代地図基準で引き直し)
    public static Estate[] Estates = new Estate[]
    {
        // 下書きv3 (2026-08-09): 横田・土岐とも溜池岸側へ拡張。水没部は EdoDaichiBuilder.Stage1_Grade で
        // 水面+1mの棚(7.6)へ盛土する(ユーザー指示: 溜池掘削で現況高さが不正確なため必要な造成は可)。
        new Estate{ group="Edo_Yashiki_Yokota", label="横田筑後守(9500石)",
            poly=new[]{ new Vector2(-371.55f,296.12f), new Vector2(-376.89f,413.82f), new Vector2(-366.08f,426.70f), new Vector2(-313.39f,365.93f), new Vector2(-338.54f,290.69f)},
            front=4, gateT=0.5f, gateType="h_mon", bansho=2,
            nagayaEdges=new[]{0}, dobeiEdges=new[]{1,2,3}, pad=9.5f }, // 3=土岐との共有境界(横田持ち)
        new Estate{ group="Edo_Yashiki_Toki", label="土岐丹波守(3500石)",
            poly=new[]{ new Vector2(-335.39f,291.47f), new Vector2(-311.41f,364.43f), new Vector2(-218.69f,321.60f), new Vector2(-223.95f,280.88f)},
            front=3, gateT=0.55f, gateType="h_mon", bansho=1,
            nagayaEdges=new int[0], dobeiEdges=new[]{1,2}, pad=9.5f }, // W辺(0)は横田側の塀が受け持つ
        new Estate{ group="Edo_Yashiki_YamaguchiUshiku", label="山口筑前守(牛久藩上屋敷)",
            poly=new[]{ new Vector2(-140.8f,182.8f), new Vector2(-174.2f,209.8f), new Vector2(-207.3f,259.3f), new Vector2(-279.2f,264.9f), new Vector2(-289.7f,142.1f), new Vector2(-200.3f,88.2f)},
            front=0, gateT=0.5f, gateType="nagayamon", bansho=2,
            nagayaEdges=new[]{2}, dobeiEdges=new[]{1,4,5}, pad=14f }, // W辺(3)は松平日向側の塀
        new Estate{ group="Edo_Yashiki_MatsudairaHyuga", label="松平日向守(糸魚川藩上屋敷)",
            poly=new[]{ new Vector2(-283.5f,266.2f), new Vector2(-386.9f,277.0f), new Vector2(-425.3f,222.7f), new Vector2(-292.3f,144.2f)},
            front=0, gateT=0.5f, gateType="nagayamon", bansho=2,
            nagayaEdges=new[]{1}, dobeiEdges=new[]{2,3}, pad=10f },
    };

    // ---------- shared helpers ----------
    public static Terrain T()
    {
        foreach (var t in UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None))
            if (t.gameObject.activeInHierarchy) return t;
        throw new Exception("no active terrain");
    }
    public static float Ground(float x, float z) { var t = T(); return t.SampleHeight(new Vector3(x, 0, z)) + t.transform.position.y; }

    static GameObject Load(string path)
    {
        var a = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (a == null) throw new Exception("asset not found: " + path);
        return a;
    }
    public static GameObject Place(string path, Vector3 pos, float ry, Vector3 scale, Transform parent, string name)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(Load(path));
        go.name = name;
        go.transform.SetParent(parent, true);
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(0, ry, 0);
        go.transform.localScale = scale;
        Undo.RegisterCreatedObjectUndo(go, "place " + name);
        return go;
    }
    public static Bounds RB(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>();
        if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.zero);
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }
    public static void SeatBottom(GameObject go, float y)
    {
        var b = RB(go);
        go.transform.position += new Vector3(0, y - b.min.y, 0);
    }
    // 頂点を軸に射影した min/max (worldY帯でフィルタ可, 名前フィルタ可)
    static void ProjExtent(GameObject go, Vector2 axis, float yMin, float yMax, Func<string, bool> nameOk, out float mn, out float mx)
    {
        mn = float.MaxValue; mx = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (nameOk != null && !nameOk(mf.gameObject.name)) continue;
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var verts = mesh.vertices;
            for (int i = 0; i < verts.Length; i++)
            {
                var w = mf.transform.TransformPoint(verts[i]);
                if (w.y < yMin || w.y > yMax) continue;
                float p = w.x * axis.x + w.z * axis.y;
                if (p < mn) mn = p; if (p > mx) mx = p;
            }
        }
    }
    static Transform Group(string root, string child)
    {
        var r = GameObject.Find(root);
        if (r == null) { r = new GameObject(root); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EdoYashikiPrefab.EnsureEditable(r);   // ★ プレハブ化済みなら解く(でないと組み替えが黙って失敗する)
        var cur = r.transform;
        if (string.IsNullOrEmpty(child)) return cur;
        foreach (var seg in child.Split('/')) // スラッシュ区切りを1段ずつネスト(1オブジェクト名にスラッシュを入れない)
        {
            var nx = cur.Find(seg);
            if (nx == null)
            {
                var g = new GameObject(seg);
                Undo.RegisterCreatedObjectUndo(g, "grp");
                g.transform.SetParent(cur, false);
                nx = g.transform;
            }
            cur = nx;
        }
        return cur;
    }
    // 辺 i の内向き法線
    // EdoGeom.InwardNormal と実装差あり — 統一は裁定待ち
    public static Vector2 InwardNormal(Estate e, int i)
    {
        var a = e.poly[i]; var b = e.poly[(i + 1) % e.poly.Length];
        var d = (b - a).normalized;
        var n = new Vector2(-d.y, d.x); // left normal
        if (EdoGeom.SignedArea(e.poly) < 0) n = -n; // CW polygon -> left normal points outward
        return n;
    }
    public static float DistToPolyEdge(Vector2[] poly, Vector2 p) => EdoGeom.DistToPolyEdge(poly, p);

    // ---------- Stage 0: backup ----------
    public static string Stage0_Backup()
    {
        var t = T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        var all = td.GetHeights(0, 0, res, res);
        var bytes = new byte[res * res * 4];
        Buffer.BlockCopy(all, 0, bytes, 0, bytes.Length);
        string p = "Library/EdoRegrade_before_20260808_nishitameike.bin";
        File.WriteAllBytes(p, bytes);
        return "saved " + p + " res=" + res;
    }

    // ---------- 自然地形へ完全復元(造成の取り消し) ----------
    // ユーザー方針(2026-08-08): 現地形が江戸期とほぼ変わらない場所は造成せず現地形に従う。
    // 葵坂付近のような明治以降に改変された箇所のみ造成する。溜池南西岸は未改変とみなし自然地形へ戻す。
    public static string RestoreNaturalTerrain()
    {
        var t = T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        string bak = "Library/EdoRegrade_before_20260808_nishitameike.bin";
        if (!File.Exists(bak)) return "ERROR: backup not found " + bak;
        var bytes = File.ReadAllBytes(bak);
        var full = new float[res, res];
        Buffer.BlockCopy(bytes, 0, full, 0, bytes.Length);
        // 造成した矩形と同じ範囲を書き戻す
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (res - 1);
        float x0 = -430, x1 = -135, z0 = 88, z1 = 425;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var H = new float[h, w];
        for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++) H[zz, xx] = full[iz0 + zz, ix0 + xx];
        td.SetHeights(ix0, iz0, H);
        td.SyncHeightmap();
        return "restored natural terrain rect=" + w + "x" + h;
    }

    // 建物・庭を自然地形へ接地し直す(XZは保持、Yのみ地面へ)。カテゴリ別のy下げ量を維持。
    public static string RegroundGroup(string groupName)
    {
        var root = GameObject.Find(groupName);
        if (root == null) return "no group";
        int n = 0;
        foreach (var subName in new[] { "Buildings", "Garden" })
        {
            var sub = root.transform.Find(subName);
            if (sub == null) continue;
            var targets = new List<Transform>();
            if (subName == "Buildings") { foreach (Transform c in sub) targets.Add(c); }
            else { foreach (Transform cat in sub) foreach (Transform c in cat) targets.Add(c); }
            foreach (var tr in targets)
            {
                var nm = tr.name.ToLower();
                float off = -0.10f;
                if (nm.StartsWith("kura")) off = -0.15f;
                else if (nm.StartsWith("tobi")) off = 0.02f;
                else if (nm.StartsWith("iwa") || nm.StartsWith("rock")) off = -0.25f;
                else if (nm.StartsWith("pine") || nm.StartsWith("sakura")) off = -0.05f;
                else if (nm.StartsWith("shrub") || nm.StartsWith("lantern")) off = -0.04f;
                else if (nm.StartsWith("ido") || nm.StartsWith("inari") || nm.StartsWith("umaya")) off = -0.10f;
                var rs = tr.GetComponentsInChildren<Renderer>();
                if (rs.Length == 0) { // 合成物(井戸/稲荷): 親位置のXZで地面へ
                    float g0 = Ground(tr.position.x, tr.position.z);
                    tr.position = new Vector3(tr.position.x, g0, tr.position.z);
                    n++; continue;
                }
                var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                float g = Ground(b.center.x, b.center.z);
                tr.position += new Vector3(0, (g + off) - b.min.y, 0);
                n++;
            }
        }
        return groupName.Substring(11) + " regrounded " + n + " objects";
    }

    // 自然地形モードで全屋敷を作り直す(地形復元→囲い再構築→建物/庭を接地し直す)
    public static string RebuildAllNatural()
    {
        NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(RestoreNaturalTerrain());
        foreach (var e in Estates)
        {
            sb.AppendLine(RebuildEnclosure(e.group));
            sb.AppendLine(RegroundGroup(e.group));
        }
        return sb.ToString();
    }

    // ---------- Stage 1: grading ----------
    public static string Stage1_Grade()
    {
        var t = T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (res - 1);
        // affected rect (world)
        float x0 = -430, x1 = -135, z0 = 88, z1 = 425;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var H = td.GetHeights(ix0, iz0, w, h); // [z,x]
        // 再実行に備え、対象矩形をバックアップ(自然地形)から復元してから造成する
        string bak = "Library/EdoRegrade_before_20260808_nishitameike.bin";
        if (File.Exists(bak))
        {
            var bytes = File.ReadAllBytes(bak);
            var full = new float[res, res];
            Buffer.BlockCopy(bytes, 0, full, 0, bytes.Length);
            for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++) H[zz, xx] = full[iz0 + zz, ix0 + xx];
        }
        int changed = 0;
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx) * cell;
                float wz = tp.z + (iz0 + zz) * cell;
                var p = new Vector2(wx, wz);
                float nat = tp.y + H[zz, xx] * ts.y;
                float target = float.MinValue;
                foreach (var e in Estates)
                {
                    bool inside = EdoGeom.PIP(e.poly, p);
                    float d = DistToPolyEdge(e.poly, p);
                    float padHere = PadAtNat(e, p, nat);
                    float cand;
                    if (inside) cand = padHere;
                    else
                    {
                        // 門前の平場(apron): 門中心から半径13mは門の地盤、13-21mでなだらかに自然へ
                        int nn = e.poly.Length;
                        Vector2 gA = e.poly[e.front], gB = e.poly[(e.front + 1) % nn];
                        Vector2 g2 = Vector2.Lerp(gA, gB, e.gateT);
                        float dg = (p - g2).magnitude;
                        float gatePad = PadAtNat(e, g2, nat);
                        if (dg < 21f)
                        {
                            float s2 = Mathf.Clamp01((dg - 13f) / 8f); s2 = s2 * s2 * (3 - 2 * s2);
                            cand = Mathf.Lerp(gatePad, nat, s2);
                        }
                        else if (d < 8f)
                        {
                            float s = d / 8f; s = s * s * (3 - 2 * s);
                            cand = Mathf.Lerp(padHere, nat, s);
                        }
                        else continue;
                    }
                    if (cand > target) target = cand;
                }
                if (target > float.MinValue && Mathf.Abs(target - nat) > 0.005f)
                {
                    H[zz, xx] = Mathf.Clamp01((target - tp.y) / ts.y);
                    changed++;
                }
            }
        td.SetHeights(ix0, iz0, H);
        td.SyncHeightmap();
        return "graded cells=" + changed + " rect=" + w + "x" + h;
    }

    // ---------- nagaya run ----------
    // A->B: 走り。outward: 敷地外向き法線。baseY: 土台レベル。gapC/gapHalf: 開口(世界座標中心/半幅) 無ければ gapHalf<=0
    /// <summary>⚠ **このピッチ(PITCH=7.81)は屋根幅から採った値で、壁の実寸と合っていない。**
    /// knagaya01c の壁(n_wall/namako/n_dodai/n_taruki)は走り方向に **8.065m** あるので、
    /// 7.81 で並べると**全継ぎ目が 0.252m 重なる** — なまこ紋が二重・瓦がずれ・窓の割りが崩れる。
    /// さらに pitchRun = span/(n-1) で run ごとにピッチを変えるので、重なり量が run ごとに違う。
    /// 直した実装は `EdoMatsudairaBuilder.NagayaChain`(部材を実行時に測り、実寸を積み上げる
    /// カーソルで置く)。**他屋敷の長屋にも同じ崩れが出ているはず** — 作り直すときに寄せること。
    /// 作法は スキル unity-buke-yashiki の references/perimeter.md「ピッチは壁の実寸」。
    /// ここを直すと既存の屋敷すべての長屋が動くので、単独では変更していない(2026-08-23)。</summary>
    public static List<GameObject> NagayaRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, float baseY,
        Vector2 gapC, float gapHalf, string prefix)
    {
        bool followGround = NaturalMode; // 自然地形モードでは各ピースを地面に追従
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg; // 表+Zを外へ
        // run 方向はローカル -X: right=(cosψ,-sinψ) → -right=(-cosψ, sinψ)
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        Vector2 sA = A, sB = B; Vector2 rdir = dir;
        if (Vector2.Dot(dir, negRight) < 0) { sA = B; sB = A; rdir = -dir; }
        // grid: モジュール実体はピボットから走りに約 -4.3..+3.6。始端 pivot=4.4、終端 pivot=len-3.7。
        // 一様ピッチ(≈7.81)になるよう n を丸めてピッチを微調整(格子を崩さない)
        float span = len - 4.4f - 3.7f;
        int n = Mathf.Max(2, Mathf.CeilToInt(span / PITCH) + 1); // ピッチ≦7.81(屋根幅7.96で必ず重なる)
        float pitchRun = span / (n - 1);
        float t0 = 4.4f;
        // kept t 値を先に決め、連続グループごとに端へ妻キャップ(l=低t端 / r=高t端)を割り当てる
        var kept = new List<float>();
        for (int k = 0; k < n; k++)
        {
            float tk = t0 + pitchRun * k;
            if (gapHalf > 0)
            {
                float gT = Vector2.Dot(gapC - sA, rdir);
                float skipLo = gT - gapHalf - 3.9f, skipHi = gT + gapHalf + 3.9f;
                if (tk + 3.6f > skipLo && tk - 4.3f < skipHi) continue;
            }
            kept.Add(tk);
        }
        for (int k = 0; k < kept.Count; k++)
        {
            float tk = kept[k];
            bool lowEnd = (k == 0) || (kept[k] - kept[k - 1] > pitchRun * 1.5f);
            bool highEnd = (k == kept.Count - 1) || (kept[k + 1] - kept[k] > pitchRun * 1.5f);
            string path = lowEnd ? PKnagayaL : (highEnd ? PKnagayaR : PKnagayaC);
            if (lowEnd && highEnd) path = PKnagayaC; // 孤立1棟はcで(両妻は不可能、後で塀が受ける)
            var c2 = sA + rdir * tk;
            // 自然地形モードでは、モジュール足元スパン(走り±4m)の地面最小値に据える(尻上がり回避)
            float pieceBase = baseY;
            if (followGround)
            {
                float g0 = Ground(c2.x - rdir.x * 4f, c2.y - rdir.y * 4f);
                float g1 = Ground(c2.x + rdir.x * 4f, c2.y + rdir.y * 4f);
                float gc = Ground(c2.x, c2.y);
                pieceBase = Mathf.Min(g0, Mathf.Min(g1, gc));
            }
            var go = Place(path, new Vector3(c2.x, pieceBase, c2.y), psi, new Vector3(ES, ES, ES), parent, prefix + "_" + k);
            SeatBottom(go, pieceBase - 0.10f);
            made.Add(go);
        }
        // namako(表)が外向きかを数値検証、逆なら180°回して面位置を復元
        if (made.Count > 0) VerifyFlipOutward(made, outward, prefix);
        return made;
    }
    static void VerifyFlipOutward(List<GameObject> mods, Vector2 outward, string prefix)
    {
        var probe = mods[Mathf.Min(1, mods.Count - 1)];
        float mn, mx;
        ProjExtent(probe, outward, -100, 1000, nm => nm.ToLower().Contains("namako"), out mn, out mx);
        if (mn == float.MaxValue) return; // namako 無し(=判定不能)
        var c = RB(probe).center; float cp = c.x * outward.x + c.z * outward.y;
        if (mx < cp) // namako が内側 → 全反転
        {
            foreach (var go in mods)
            {
                var b0 = RB(go);
                go.transform.rotation *= Quaternion.Euler(0, 180, 0);
                var b1 = RB(go);
                go.transform.position += b0.center - b1.center;
            }
            Debug.LogWarning(prefix + ": namako was inward -> flipped 180");
        }
    }

    // ---------- dobei run (表裏ペア) ----------
    public static List<GameObject> DobeiRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        bool followGround, float flatBase, Vector2 gapC, float gapHalf)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / 2.982f));
        float pitch = len / n;
        float sx = pitch / 1.6447f;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        for (int k = 0; k < n; k++)
        {
            var c2 = A + dir * (pitch * (k + 0.5f));
            if (gapHalf > 0)
            {
                float gT = Vector2.Dot(gapC - A, dir);
                if (Mathf.Abs(pitch * (k + 0.5f) - gT) < gapHalf + pitch * 0.5f - 0.01f) continue;
            }
            float baseY = flatBase;
            if (followGround)
            {
                float g1 = Ground(c2.x - dir.x * pitch * 0.5f, c2.y - dir.y * pitch * 0.5f);
                float g2 = Ground(c2.x + dir.x * pitch * 0.5f, c2.y + dir.y * pitch * 0.5f);
                baseY = Mathf.Max(g1, g2);
            }
            for (int side = 0; side < 2; side++)
            {
                float ry = side == 0 ? psi : psi + 180f;
                var off2 = outward * (side == 0 ? 0.0f : -0.2f);
                var go = Place(PHei, Vector3.zero, ry, new Vector3(sx * ES / 1.818f * 1.818f, ES, ES), parent,
                    prefix + "_" + k + (side == 0 ? "f" : "b"));
                go.transform.localScale = new Vector3(sx, ES, ES);
                // bounds 中心合わせ
                var b = RB(go);
                var target = new Vector3(c2.x + off2.x, 0, c2.y + off2.y);
                go.transform.position += new Vector3(target.x - b.center.x, 0, target.z - b.center.z);
                SeatBottom(go, baseY - 0.10f);
                made.Add(go);
            }
        }
        return made;
    }

    // ---------- Stage 2: enclosures per estate ----------
    public static string Stage2_Enclosure(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root != null && root.transform.Find("Kakoi") != null) return "SKIP: " + e.group + "/Kakoi exists";
        var kak = Group(e.group, "Kakoi");
        var monGrp = Group(e.group, "Omotemon");
        int N = e.poly.Length;
        var sb = new System.Text.StringBuilder();

        // gate world pos
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 fin = InwardNormal(e, e.front);
        Vector2 fout = -fin;
        float basePad = PadAt(e, gate2);

        // --- gate ---
        float gateHalf; GameObject mon;
        float psiIn = Mathf.Atan2(fin.x, fin.y) * Mathf.Rad2Deg;
        if (e.gateType == "nagayamon")
        {
            mon = Place(PNmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one * ES, monGrp, "Nagayamon");
        }
        else
        {
            mon = Place(PHmon, new Vector3(gate2.x, basePad, gate2.y), psiIn, Vector3.one, monGrp, "Hmon");
        }
        SeatBottom(mon, basePad - 0.05f);
        // 幅中心=gate2 に bounds で合わせ
        var mb = RB(mon);
        mon.transform.position += new Vector3(gate2.x - mb.center.x, 0, gate2.y - mb.center.z);
        mb = RB(mon);
        // 実体幅(壁高帯)を走り軸で測る
        Vector2 runAxis = (fB - fA).normalized;
        float wmn, wmx;
        ProjExtent(mon, runAxis, basePad + 0.5f, basePad + 4.5f, null, out wmn, out wmx);
        float monHalf = (wmx - wmn) * 0.5f;
        gateHalf = monHalf;
        sb.AppendLine("gate " + e.gateType + " width=" + (wmx - wmn).ToString("F2"));
        // kagami(控柱) が内側かを検証
        float kmn, kmx;
        ProjExtent(mon, fout, -100, 1000, nm => nm.ToLower().Contains("kagami"), out kmn, out kmx);
        if (kmn != float.MaxValue)
        {
            var mc = RB(mon).center; float cp = mc.x * fout.x + mc.z * fout.y;
            if ((kmn + kmx) * 0.5f > cp)
            {
                mon.transform.rotation *= Quaternion.Euler(0, 180, 0);
                var b1 = RB(mon);
                mon.transform.position += RB(mon).center - b1.center; // no-op guard
                var b2 = RB(mon);
                mon.transform.position += new Vector3(gate2.x - b2.center.x, 0, gate2.y - b2.center.z);
                sb.AppendLine("gate flipped (kagami was outward)");
            }
        }
        // bansho
        for (int i = 0; i < e.bansho; i++)
        {
            float side = (e.bansho == 1) ? 1f : (i == 0 ? 1f : -1f);
            float du = monHalf + 3.2f;
            Vector2 bp = gate2 + runAxis * (side * du) + fout * 0.5f;
            var ban = Place(PBansho, new Vector3(bp.x, basePad, bp.y), psiIn + 180f, Vector3.one * ES, monGrp, "Bansho_" + i);
            SeatBottom(ban, basePad - 0.05f);
            // 前面(+Z)を街路へ: forward が fout と逆なら反転
            var f3 = ban.transform.forward;
            if (f3.x * fout.x + f3.z * fout.y < 0)
                ban.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg, 0);
        }

        // --- edges ---
        for (int i = 0; i < N; i++)
        {
            Vector2 a = e.poly[i], b = e.poly[(i + 1) % N];
            Vector2 outw = -InwardNormal(e, i);
            if (i == e.front)
            {
                float padF = PadAt(e, Vector2.Lerp(a, b, 0.5f));
                NagayaRun(kak, a, b, outw, padF, gate2, gateHalf, "NG_F" + i);
            }
            else if (e.nagayaEdges.Contains(i))
            {
                float padE = PadAt(e, Vector2.Lerp(a, b, 0.5f));
                NagayaRun(kak, a, b, outw, padE, Vector2.zero, -1, "NG_" + i);
            }
            else if (e.dobeiEdges.Contains(i))
            {
                DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
            }
        }
        SceneView.RepaintAll();
        return sb.ToString() + "enclosure done: " + e.group;
    }

    // その地点の設計地盤(=Stage1 と同じ式)。nat=自然地形(築山温存用)。
    // 段丘は「表門のある辺からの奥行き vG」基準。山口は北辺(корidor)沿いだけ別段(10)。
    public static float PadAtNat(Estate e, Vector2 p, float nat)
    {
        if (e.group.Contains("Yamaguchi"))
        {
            // 前面(NE辺 P0-P1)ラインからの奥行き
            Vector2 fa = e.poly[0]; Vector2 fin = InwardNormal(e, 0);
            float vG = Vector2.Dot(p - fa, fin);
            float terr = vG < 58 ? 14f : (vG < 68 ? Mathf.Lerp(14f, 18f, (vG - 58) / 10f) : 18f);
            // 北辺(P3-P4, 東西通り)沿いは 10 の帯
            Vector2 nA = e.poly[3]; Vector2 nin = InwardNormal(e, 3);
            float dvN = Vector2.Dot(p - nA, nin);
            float h;
            if (dvN < 22) h = 10f;
            else if (dvN < 34) h = Mathf.Lerp(10f, terr, (dvN - 22) / 12f);
            else h = terr;
            // 南西奥だけ築山温存(手前は御殿・蔵ゾーンなので切土でテラスを通す)
            if (dvN > 32 && vG > 85)
            {
                float cap = Mathf.Lerp(terr, 24f, Mathf.Clamp01((vG - 85) / 15f));
                h = Mathf.Max(h, Mathf.Min(nat, cap));
            }
            return h;
        }
        if (e.group.Contains("Hyuga"))
        {
            Vector2 fa = e.poly[0]; Vector2 fin = InwardNormal(e, 0);
            float vG = Vector2.Dot(p - fa, fin);
            float terr = vG < 55 ? 10f : (vG < 65 ? Mathf.Lerp(10f, 13f, (vG - 55) / 10f) : 13f);
            if (vG > 63) terr = Mathf.Max(terr, Mathf.Min(nat, 16f)); // 南東の庭山温存
            return terr;
        }
        return e.pad;
    }
    // 自然地形モード: trueなら造成せず地盤=自然地形(NatGround)。ユーザー指示2026-08-08(榎坂保全)。
    public static bool NaturalMode = true;

    public static float PadAt(Estate e, Vector2 p)
    {
        if (NaturalMode) return NatGround(p.x, p.y);
        return PadAtNat(e, p, NatGround(p.x, p.y));
    }
    // 造成前の自然地形(バックアップから)
    static float[,] _natCache; static int _natRes = -1;
    public static float NatGround(float x, float z)
    {
        var t = T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        if (_natCache == null || _natRes != res)
        {
            string p = "Library/EdoRegrade_before_20260808_nishitameike.bin";
            if (!File.Exists(p)) return Ground(x, z);
            var bytes = File.ReadAllBytes(p);
            _natCache = new float[res, res];
            Buffer.BlockCopy(bytes, 0, _natCache, 0, bytes.Length);
            _natRes = res;
        }
        Vector3 tp = t.transform.position, ts = td.size;
        float fx = (x - tp.x) / ts.x * (res - 1), fz = (z - tp.z) / ts.z * (res - 1);
        int ix = Mathf.Clamp(Mathf.FloorToInt(fx), 0, res - 2), iz = Mathf.Clamp(Mathf.FloorToInt(fz), 0, res - 2);
        float ax = fx - ix, az = fz - iz;
        float v = Mathf.Lerp(Mathf.Lerp(_natCache[iz, ix], _natCache[iz, ix + 1], ax), Mathf.Lerp(_natCache[iz + 1, ix], _natCache[iz + 1, ix + 1], ax), az);
        return tp.y + v * ts.y;
    }

    // ---------- Stage 3: buildings ----------
    // (u,v): 原点=門, u=街路沿い(runAxis), v=敷地内向き
    public static GameObject PlaceUV(Estate e, string path, float u, float v, float faceYawOffset, Vector3 scale, Transform parent, string name)
    {
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 uhat = (fB - fA).normalized;
        Vector2 vhat = InwardNormal(e, e.front);
        Vector2 p = gate2 + uhat * u + vhat * v;
        float streetYaw = Mathf.Atan2(-vhat.x, -vhat.y) * Mathf.Rad2Deg; // facade(+Z)が門を向く
        float y = PadAt(e, p);
        var go = Place(path, new Vector3(p.x, y, p.y), streetYaw + faceYawOffset, scale, parent, name);
        SeatBottom(go, y - 0.12f);
        return go;
    }

    public static string Stage3_Buildings(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root != null && root.transform.Find("Buildings") != null) return "SKIP: Buildings exists";
        var bg = Group(e.group, "Buildings");
        var sb = new System.Text.StringBuilder();
        if (e.group.Contains("Yokota"))
        {   // 区画v2は幅~40-55m・奥行~90m。u正=東
            PlaceUV(e, PHouseB, 0, 32, 0, Vector3.one, bg, "Shuoku");          // 主屋(玄関正対)
            PlaceUV(e, PSmallHouse, -12, 46, 0, Vector3.one, bg, "Daidokoro"); // 台所
            PlaceUV(e, PKura, -14, 60, 90, Vector3.one * ES, bg, "Kura_1");
            PlaceUV(e, PKura, 16, 56, -90, Vector3.one * ES, bg, "Kura_2");
            Well(e, bg, -5, 50);
            Umaya(e, bg, 15, 12);
        }
        else if (e.group.Contains("Toki"))
        {
            PlaceUV(e, PHouse, 0, 20, 0, Vector3.one, bg, "Shuoku");
            PlaceUV(e, PSmallHouse, -21, 30, 0, Vector3.one, bg, "Daidokoro");
            PlaceUV(e, PKura, -34, 24, 90, Vector3.one * ES, bg, "Kura_1");
            Well(e, bg, -8, 32);
        }
        else if (e.group.Contains("Yamaguchi"))
        {
            PlaceUV(e, PBigHouse, 0, 30, 0, Vector3.one, bg, "OmoteGoten");
            PlaceUV(e, PHouse, 8, 52, 0, Vector3.one, bg, "OkuGoten");
            PlaceUV(e, PSmallHouse, 22, 42, 0, Vector3.one, bg, "Daidokoro");
            PlaceUV(e, PKura, -6, 74, 90, Vector3.one * ES, bg, "Kura_1");
            PlaceUV(e, PKura, 4, 82, 90, Vector3.one * ES, bg, "Kura_2");
            Well(e, bg, 30, 52);
            Umaya(e, bg, 26, 16);
        }
        else
        {   // 松平日向 v2: 前辺104m・東端が山口境に近いので蔵は西側へ
            PlaceUV(e, PBigHouse, 0, 30, 0, Vector3.one, bg, "OmoteGoten");
            PlaceUV(e, PHouse, 14, 52, 0, Vector3.one, bg, "OkuGoten");
            PlaceUV(e, PSmallHouse, -20, 40, 0, Vector3.one, bg, "Daidokoro");
            PlaceUV(e, PKura, 34, 56, 90, Vector3.one * ES, bg, "Kura_1");
            PlaceUV(e, PKura, 43, 47, 90, Vector3.one * ES, bg, "Kura_2");
            Well(e, bg, -12, 48);
            Umaya(e, bg, 28, 12);
        }
        return "buildings done: " + e.group + " " + sb;
    }

    // 井戸(合成)
    static void Well(Estate e, Transform parent, float u, float v)
    {
        var g = new GameObject("Ido");
        g.transform.SetParent(parent, false);
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 uhat = (fB - fA).normalized; Vector2 vhat = InwardNormal(e, e.front);
        Vector2 p = gate2 + uhat * u + vhat * v;
        float y = PadAt(e, p);
        g.transform.position = new Vector3(p.x, y, p.y);
        var curb = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        curb.name = "curb"; curb.transform.SetParent(g.transform, false);
        curb.transform.localScale = new Vector3(1.3f, 0.35f, 1.3f);
        curb.transform.localPosition = new Vector3(0, 0.35f, 0);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        curb.GetComponent<Renderer>().sharedMaterial = stone;
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.38f, 0.28f, 0.18f);
        for (int i = 0; i < 2; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.12f, 1.1f, 0.12f);
            post.transform.localPosition = new Vector3(i == 0 ? -0.85f : 0.85f, 1.1f, 0);
            post.GetComponent<Renderer>().sharedMaterial = wood;
        }
        var beam = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        beam.name = "beam"; beam.transform.SetParent(g.transform, false);
        beam.transform.localScale = new Vector3(0.09f, 0.95f, 0.09f);
        beam.transform.localEulerAngles = new Vector3(0, 0, 90);
        beam.transform.localPosition = new Vector3(0, 2.1f, 0);
        beam.GetComponent<Renderer>().sharedMaterial = wood;
        Undo.RegisterCreatedObjectUndo(g, "well");
    }

    // 厩/中間長屋: knagaya l+r ペア単独棟
    static void Umaya(Estate e, Transform parent, float u, float v)
    {
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 uhat = (fB - fA).normalized; Vector2 vhat = InwardNormal(e, e.front);
        Vector2 c = gate2 + uhat * u + vhat * v;
        float y = PadAt(e, c);
        // 走り=街路平行, 表(+Z)は敷地内(門と逆=vhat)
        float psi = Mathf.Atan2(vhat.x, vhat.y) * Mathf.Rad2Deg;
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        var g = new GameObject("Umaya");
        g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "umaya");
        var m1 = Place(PKnagayaL, Vector3.zero, psi, Vector3.one * ES, g.transform, "u0");
        var m2 = Place(PKnagayaR, Vector3.zero, psi, Vector3.one * ES, g.transform, "u1");
        Vector2 p1 = c - negRight * (PITCH * 0.5f);
        Vector2 p2 = c + negRight * (PITCH * 0.5f);
        m1.transform.position = new Vector3(p1.x, y, p1.y);
        m2.transform.position = new Vector3(p2.x, y, p2.y);
        SeatBottom(m1, y - 0.10f); SeatBottom(m2, y - 0.10f);
    }

    // ---------- Stage 4: garden ----------
    static string[] Pines = {
        EdoAssets.JG.PineBig01,
        EdoAssets.JG.PineBig02,
        EdoAssets.JG.PineBig03 };
    static string[] Sakuras = {
        EdoAssets.JG.SakuraBig01,
        EdoAssets.JG.SakuraBig05 };
    static string[] Shrubs = {
        EdoAssets.JC.Azalea01,
        EdoAssets.JC.Azalea03,
        EdoAssets.JC.Azalea04,
        EdoAssets.JG.Boxwood01 };
    static string[] Rocks = {
        EdoAssets.JG.Rock01,
        EdoAssets.JG.Rock02,
        EdoAssets.JG.Rock03 };
    const string PTobi = EdoAssets.JG.TobiIshi01;
    const string PKasuga = EdoAssets.Own.KasugaLantern;
    const string PYukimi = EdoAssets.Own.YukimiLantern;

    // ガーデンゾーン: 敷地内で建物/壁から離れた点にランダム植栽
    public static string Stage4_Garden(string groupName, int seed)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        // 旧Garden及び過去バグのスラッシュ名オブジェクトを一掃(やり直し用)
        var dead = new List<GameObject>();
        foreach (Transform ch in root.transform) if (ch.name == "Garden" || ch.name.StartsWith("Garden/")) dead.Add(ch.gameObject);
        foreach (var d in dead) UnityEngine.Object.DestroyImmediate(d);
        var gg = Group(e.group, "Garden");
        var trees = Group(e.group, "Garden/Trees");
        var shrubs = Group(e.group, "Garden/Shrubs");
        var rocks = Group(e.group, "Garden/Rocks");
        var path = Group(e.group, "Garden/Path");
        var props = Group(e.group, "Garden/Props");
        var rnd = new System.Random(seed);
        // obstacles: 建物と門のみ(外周長屋はAABBが膨張して内部を覆うので使わず、境界マージンで避ける)
        var obs = new List<Bounds>();
        foreach (Transform sub in root.transform)
            if (sub.name == "Buildings" || sub.name == "Omotemon")
                foreach (Transform ch in sub) { var rb = RB(ch.gameObject); if (rb.size.sqrMagnitude > 0.01f) obs.Add(rb); }
        // 境界マージン: 長屋辺は躯体が内側~8m、築地塀辺は~2m
        float EdgeMargin(Vector2 p)
        {
            float best = float.MaxValue; float bm = 7.5f;
            for (int i = 0; i < e.poly.Length; i++)
            {
                var a = e.poly[i]; var b2 = e.poly[(i + 1) % e.poly.Length];
                var d = b2 - a; float len = d.magnitude; d /= len;
                float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
                float dd = (p - (a + d * t)).magnitude;
                if (dd < best) { best = dd; bm = (i == e.front || e.nagayaEdges.Contains(i)) ? 8.5f : 3.0f; }
            }
            return bm;
        }
        Func<Vector2, float, bool> clear = (p, m) =>
        {
            if (!EdoGeom.PIP(e.poly, p)) return false;
            if (DistToPolyEdge(e.poly, p) < EdgeMargin(p)) return false;
            foreach (var b in obs)
                if (p.x > b.min.x - m && p.x < b.max.x + m && p.y > b.min.z - m && p.y < b.max.z + m) return false;
            return true;
        };
        // ゾーン: 奥庭 = 門から遠い側 → 敷地重心より v が大きい領域を優先
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 vhat = InwardNormal(e, e.front);
        Vector2 cen = Vector2.zero; foreach (var p in e.poly) cen += p; cen /= e.poly.Length;
        float vCen = Vector2.Dot(cen - gate2, vhat);
        var bb = new Bounds(new Vector3(cen.x, 0, cen.y), Vector3.zero);
        foreach (var p in e.poly) bb.Encapsulate(new Vector3(p.x, 0, p.y));
        int nPine = e.gateType == "nagayamon" ? 16 : 9;
        int placed = 0, guard = 0;
        while (placed < nPine && guard++ < 800)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            float v = Vector2.Dot(p - gate2, vhat);
            if (v < vCen * 0.7f && rnd.NextDouble() < 0.75) continue; // 前庭は疎
            if (!clear(p, 2.5f)) continue;
            float y = PadAt(e, p);
            float sc = 1.65f * (0.9f + 0.5f * (float)rnd.NextDouble());
            var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, trees, "Pine_" + placed);
            SeatBottom(go, y - 0.05f);
            placed++;
        }
        // 桜の一群 (奥の一隅)
        Vector2 skC = Vector2.zero; bool found = false;
        for (int i = 0; i < 200 && !found; i++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (Vector2.Dot(p - gate2, vhat) > vCen * 1.15f && clear(p, 3f)) { skC = p; found = true; }
        }
        if (found)
            for (int i = 0; i < 3; i++)
            {
                var p = skC + new Vector2((float)rnd.NextDouble() * 8 - 4, (float)rnd.NextDouble() * 8 - 4);
                if (!clear(p, 2f)) continue;
                float y = PadAt(e, p);
                float sc = 1.4f * (0.9f + 0.4f * (float)rnd.NextDouble());
                var go = Place(Sakuras[rnd.Next(Sakuras.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, trees, "Sakura_" + i);
                SeatBottom(go, y - 0.05f);
            }
        // 岩組 1-2 clusters
        int nClu = e.gateType == "nagayamon" ? 2 : 1;
        for (int cIdx = 0; cIdx < nClu; cIdx++)
        {
            for (int i = 0; i < 200; i++)
            {
                var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
                if (Vector2.Dot(p - gate2, vhat) < vCen && !e.group.Contains("Toki")) continue;
                if (!clear(p, 2f)) continue;
                float y = PadAt(e, p);
                int cnt = 3 + rnd.Next(2);
                for (int r = 0; r < cnt; r++)
                {
                    var rp = p + new Vector2((float)rnd.NextDouble() * 3.4f - 1.7f, (float)rnd.NextDouble() * 3.4f - 1.7f);
                    float rs = (r == 0 ? 3.2f : 1.6f) * (0.8f + 0.5f * (float)rnd.NextDouble());
                    var rg = Place(Rocks[rnd.Next(Rocks.Length)], new Vector3(rp.x, y, rp.y), (float)rnd.NextDouble() * 360f, Vector3.one * rs, rocks, "Iwa_" + cIdx + "_" + r);
                    SeatBottom(rg, PadAt(e, rp) - 0.25f);
                }
                break;
            }
        }
        // ツツジ・下草
        int nShrub = e.gateType == "nagayamon" ? 22 : 12;
        for (int i = 0, g2 = 0; i < nShrub && g2 < 600; g2++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (!clear(p, 1.2f)) continue;
            float y = PadAt(e, p);
            float sc = 0.9f + 0.7f * (float)rnd.NextDouble();
            var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * sc, shrubs, "Shrub_" + i);
            SeatBottom(go, y - 0.04f);
            i++;
        }
        // 飛石: 門 → 玄関 のゆるいベジェ
        var bld = root.transform.Find("Buildings");
        Transform main = bld != null ? (bld.Find("Shuoku") ?? bld.Find("OmoteGoten")) : null;
        if (main != null)
        {
            var m2 = new Vector2(main.position.x, main.position.z);
            Vector2 g0 = gate2 + vhat * 3.5f;
            Vector2 g1 = m2 - vhat * 9f;
            Vector2 ctrl = (g0 + g1) * 0.5f + new Vector2(-vhat.y, vhat.x) * 3.2f;
            int steps = Mathf.Max(4, Mathf.RoundToInt((g1 - g0).magnitude / 2.4f));
            for (int i = 0; i <= steps; i++)
            {
                float tt = (float)i / steps;
                Vector2 p = (1 - tt) * (1 - tt) * g0 + 2 * (1 - tt) * tt * ctrl + tt * tt * g1;
                p += new Vector2((float)rnd.NextDouble() * 0.5f - 0.25f, (float)rnd.NextDouble() * 0.5f - 0.25f);
                float y = PadAt(e, p);
                var go = Place(PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, path, "Tobi_" + i);
                SeatBottom(go, y + 0.02f);
            }
        }
        // 灯籠
        int nLan = e.gateType == "nagayamon" ? 3 : 2;
        for (int i = 0, g3 = 0; i < nLan && g3 < 300; g3++)
        {
            var p = new Vector2(Mathf.Lerp(bb.min.x, bb.max.x, (float)rnd.NextDouble()), Mathf.Lerp(bb.min.z, bb.max.z, (float)rnd.NextDouble()));
            if (Vector2.Dot(p - gate2, vhat) < vCen * 0.8f) continue;
            if (!clear(p, 1.5f)) continue;
            float y = PadAt(e, p);
            string lp = (i % 2 == 0) ? PKasuga : PYukimi;
            if (AssetDatabase.LoadAssetAtPath<GameObject>(lp) == null) lp = EdoAssets.JC.StoneBasket;
            var go = Place(lp, new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.35f, props, "Lantern_" + i);
            SeatBottom(go, y - 0.03f);
            i++;
        }
        // 邸内稲荷 (旗本=北東鬼門 / 大名=庭の一隅) — 朱鳥居+小祠
        Inari(e, props, rnd);
        return "garden done: " + e.group;
    }

    static void Inari(Estate e, Transform parent, System.Random rnd)
    {
        // 北東端に最も近い敷地内候補点
        Vector2 ne = new Vector2(9999, 9999); Vector2 best = Vector2.zero; float bestScore = float.MinValue;
        var bbc = Vector2.zero; foreach (var p in e.poly) bbc += p; bbc /= e.poly.Length;
        for (int i = 0; i < 300; i++)
        {
            var bbMin = new Vector2(e.poly.Min(p => p.x), e.poly.Min(p => p.y));
            var bbMax = new Vector2(e.poly.Max(p => p.x), e.poly.Max(p => p.y));
            var p2 = new Vector2(Mathf.Lerp(bbMin.x, bbMax.x, (float)rnd.NextDouble()), Mathf.Lerp(bbMin.y, bbMax.y, (float)rnd.NextDouble()));
            if (!EdoGeom.PIP(e.poly, p2) || DistToPolyEdge(e.poly, p2) < 4f) continue;
            float score = p2.x + p2.y; // 北東(x大z大)
            if (score > bestScore) { bestScore = score; best = p2; }
        }
        if (bestScore == float.MinValue) return;
        float y = PadAt(e, best);
        var g = new GameObject("Inari");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(best.x, y, best.y);
        Undo.RegisterCreatedObjectUndo(g, "inari");
        var shu = new Material(Shader.Find("Universal Render Pipeline/Lit")); shu.color = new Color(0.78f, 0.15f, 0.08f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        // 鳥居
        for (int i = 0; i < 2; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "t_post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.18f, 1.25f, 0.18f);
            post.transform.localPosition = new Vector3(i == 0 ? -0.9f : 0.9f, 1.25f, -2.2f);
            post.GetComponent<Renderer>().sharedMaterial = shu;
        }
        var kasagi = GameObject.CreatePrimitive(PrimitiveType.Cube);
        kasagi.name = "t_kasagi"; kasagi.transform.SetParent(g.transform, false);
        kasagi.transform.localScale = new Vector3(2.6f, 0.16f, 0.2f);
        kasagi.transform.localPosition = new Vector3(0, 2.5f, -2.2f);
        kasagi.GetComponent<Renderer>().sharedMaterial = shu;
        var nuki = GameObject.CreatePrimitive(PrimitiveType.Cube);
        nuki.name = "t_nuki"; nuki.transform.SetParent(g.transform, false);
        nuki.transform.localScale = new Vector3(2.2f, 0.12f, 0.14f);
        nuki.transform.localPosition = new Vector3(0, 2.05f, -2.2f);
        nuki.GetComponent<Renderer>().sharedMaterial = shu;
        // 祠: 石基壇 + 木祠 + 切妻(cube回転)
        var kidan = GameObject.CreatePrimitive(PrimitiveType.Cube);
        kidan.name = "kidan"; kidan.transform.SetParent(g.transform, false);
        kidan.transform.localScale = new Vector3(1.5f, 0.4f, 1.2f);
        kidan.transform.localPosition = new Vector3(0, 0.2f, 0);
        kidan.GetComponent<Renderer>().sharedMaterial = stone;
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.30f, 0.18f);
        var hokora = GameObject.CreatePrimitive(PrimitiveType.Cube);
        hokora.name = "hokora"; hokora.transform.SetParent(g.transform, false);
        hokora.transform.localScale = new Vector3(0.9f, 0.9f, 0.8f);
        hokora.transform.localPosition = new Vector3(0, 0.85f, 0);
        hokora.GetComponent<Renderer>().sharedMaterial = wood;
        for (int i = 0; i < 2; i++)
        {
            var roof = GameObject.CreatePrimitive(PrimitiveType.Cube);
            roof.name = "roof" + i; roof.transform.SetParent(g.transform, false);
            roof.transform.localScale = new Vector3(1.2f, 0.06f, 0.75f);
            roof.transform.localPosition = new Vector3(0, 1.5f, i == 0 ? -0.28f : 0.28f);
            roof.transform.localEulerAngles = new Vector3(i == 0 ? -35 : 35, 0, 0);
            roof.GetComponent<Renderer>().sharedMaterial = wood;
        }
    }

    // ---------- Stage 5: splat ----------
    public static string Stage5_Splat()
    {
        var t = T(); var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -430, x1 = -135, z0 = 88, z1 = 435;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h); // [z,x,layer]
        int L = td.alphamapLayers;
        int changed = 0;
        foreach (var e in Estates)
        {
            int N = e.poly.Length;
            Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
            Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
            Vector2 vhat = InwardNormal(e, e.front);
            Vector2 cen = Vector2.zero; foreach (var p in e.poly) cen += p; cen /= e.poly.Length;
            float vCen = Vector2.Dot(cen - gate2, vhat);
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                    float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                    var p = new Vector2(wx, wz);
                    if (!EdoGeom.PIP(e.poly, p)) continue;
                    float v = Vector2.Dot(p - gate2, vhat);
                    float uAbs = Mathf.Abs(Vector2.Dot(p - gate2, (fB - fA).normalized));
                    float bare, grass, dirt;
                    if (v < vCen * 0.65f && uAbs < 30) { bare = 0.8f; grass = 0.06f; dirt = 0.14f; } // 白洲前庭
                    else
                    {
                        float noise = Mathf.PerlinNoise(wx * 0.11f, wz * 0.11f);
                        grass = Mathf.Lerp(0.42f, 0.72f, noise); bare = 0.08f; dirt = 1f - grass - bare;
                    }
                    float sum = bare + grass + dirt;
                    for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
                    A[zz, xx, 0] = dirt / sum; A[zz, xx, 1] = grass / sum; A[zz, xx, 2] = bare / sum;
                    changed++;
                }
        }
        td.SetAlphamaps(ix0, iz0, A);
        return "splat cells=" + changed;
    }

    // ---------- QA: OBB clearance ----------
    public static string QA_Clearance(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root == null) return "no group";
        var sb = new System.Text.StringBuilder();
        var bld = root.transform.Find("Buildings");
        if (bld == null) return "no buildings";
        var items = new List<Transform>();
        foreach (Transform c in bld) items.Add(c);
        // 建物 vs 敷地境界: まず bounds で粗く、怪しい時だけ実メッシュ点
        foreach (var it in items)
        {
            var b = RB(it.gameObject);
            float coarse = float.MaxValue;
            for (int cx = 0; cx < 2; cx++) for (int cz = 0; cz < 2; cz++)
            {
                var p2 = new Vector2(cx == 0 ? b.min.x : b.max.x, cz == 0 ? b.min.z : b.max.z);
                float d = DistToPolyEdge(e.poly, p2);
                if (!EdoGeom.PIP(e.poly, p2)) d = -d;
                if (d < coarse) coarse = d;
            }
            if (coarse > 1.0f) continue; // AABBは過大なのでこれで十分安全
            float worst = float.MaxValue;
            foreach (var p in SamplePts(it))
            {
                var p2 = new Vector2(p.x, p.z);
                float d = DistToPolyEdge(e.poly, p2);
                if (!EdoGeom.PIP(e.poly, p2)) d = -d;
                if (d < worst) worst = d;
            }
            if (worst < 1.0f) sb.AppendLine("⚠ " + it.name + " boundary dist=" + worst.ToString("F2"));
        }
        // 建物同士: AABB overlap → 頂点最小距離
        for (int i = 0; i < items.Count; i++)
            for (int j = i + 1; j < items.Count; j++)
            {
                var bi = RB(items[i].gameObject); var bj = RB(items[j].gameObject);
                bi.Expand(1.0f);
                if (!bi.Intersects(bj)) continue;
                float md = MeshMinDist(items[i], items[j]);
                if (md < 0.5f) sb.AppendLine("⚠ " + items[i].name + " x " + items[j].name + " meshDist=" + md.ToString("F2"));
            }
        return sb.Length == 0 ? "QA clean: " + groupName : sb.ToString();
    }
    static float MeshMinDist(Transform a, Transform b)
    {
        var pa = SamplePts(a); var pb = SamplePts(b);
        float m = float.MaxValue;
        foreach (var p in pa) foreach (var q in pb) { float d = Vector3.Distance(p, q); if (d < m) m = d; }
        return m;
    }
    static List<Vector3> SamplePts(Transform t)
    {
        var pts = new List<Vector3>();
        var mfs = t.GetComponentsInChildren<MeshFilter>();
        int perFilter = Mathf.Max(4, 240 / Mathf.Max(1, mfs.Length)); // 全体~240点に制限
        foreach (var mf in mfs)
        {
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var vts = mesh.vertices;
            for (int i = 0; i < vts.Length; i += Mathf.Max(1, vts.Length / perFilter)) pts.Add(mf.transform.TransformPoint(vts[i]));
        }
        if (pts.Count > 300)
        {
            var thin = new List<Vector3>();
            for (int i = 0; i < pts.Count; i += pts.Count / 300 + 1) thin.Add(pts[i]);
            return thin;
        }
        return pts;
    }

    // ---------- gate junction fix ----------
    // 番所を門の実体端に密着させ、前面を門前面と面一に。左右サブランを番所(無ければ門)の実体端へ突き付ける。
    public static string FixGateJunctions(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        if (root == null) return "no group";
        var sb = new System.Text.StringBuilder();
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 runAxis = (fB - fA).normalized;
        Vector2 fout = -InwardNormal(e, e.front);
        var monGrp = root.transform.Find("Omotemon");
        var kak = root.transform.Find("Kakoi");
        if (monGrp == null || kak == null) return "missing groups";
        Transform mon = null; var banshos = new List<Transform>();
        foreach (Transform c in monGrp)
        {
            if (c.name.StartsWith("Bansho")) banshos.Add(c);
            else mon = c;
        }
        if (mon == null) return "no mon";
        float basePad = PadAt(e, Vector2.Lerp(fA, fB, e.gateT));
        // 門の実体(壁高帯)
        float gMn, gMx; ProjExtent(mon.gameObject, runAxis, basePad + 0.5f, basePad + 4.5f, null, out gMn, out gMx);
        float gFmn, gFmx; ProjExtent(mon.gameObject, fout, basePad + 0.2f, basePad + 4.5f, null, out gFmn, out gFmx);
        // 番所: 門端に密着・前面を門前面(外側実体)に合わせる
        float banEdgeLo = gMn, banEdgeHi = gMx;
        for (int i = 0; i < banshos.Count; i++)
        {
            var ban = banshos[i];
            float side = (banshos.Count == 1) ? 1f : (i == 0 ? 1f : -1f);
            float bMn, bMx; ProjExtent(ban.gameObject, runAxis, basePad + 0.2f, basePad + 4f, null, out bMn, out bMx);
            float bFmn, bFmx; ProjExtent(ban.gameObject, fout, basePad + 0.2f, basePad + 4f, null, out bFmn, out bFmx);
            float shiftU = side > 0 ? (gMx - 0.15f) - bMn : (gMn + 0.15f) - bMx;
            // h_mon: 門前面と面一(門躯体が塀線より前に出るので番所も自然に張り出す)
            // nagayamon: 門前面=塀面なので「格子出」として +1.7m 張り出させる
            float proud = e.gateType == "nagayamon" ? 1.7f : 0f;
            float shiftV = (gFmx + proud) - bFmx;
            ban.position += new Vector3(runAxis.x * shiftU + fout.x * shiftV, 0, runAxis.y * shiftU + fout.y * shiftV);
            SeatBottom(ban.gameObject, basePad - 0.05f);
            float nMn, nMx; ProjExtent(ban.gameObject, runAxis, basePad + 0.2f, basePad + 4f, null, out nMn, out nMx);
            if (side > 0) banEdgeHi = Mathf.Max(banEdgeHi, nMx); else banEdgeLo = Mathf.Min(banEdgeLo, nMn);
            sb.AppendLine("bansho" + i + " side=" + side + " shiftU=" + shiftU.ToString("F2") + " shiftV=" + shiftV.ToString("F2"));
        }
        // 前辺の長屋モジュールを門中心からの符号で2群に分け、群ごとに突き付けシフト
        var lows = new List<Transform>(); var highs = new List<Transform>();
        float gateC = (gMn + gMx) * 0.5f;
        foreach (Transform c in kak)
        {
            if (!c.name.StartsWith("NG_F" + e.front)) continue;
            float mMn, mMx; ProjExtent(c.gameObject, runAxis, basePad + 0.5f, basePad + 4.0f, null, out mMn, out mMx);
            if ((mMn + mMx) * 0.5f < gateC) lows.Add(c); else highs.Add(c);
        }
        if (lows.Count > 0)
        {
            float best = float.MinValue;
            foreach (var m in lows) { float mMn, mMx; ProjExtent(m.gameObject, runAxis, basePad + 0.5f, basePad + 4.0f, null, out mMn, out mMx); if (mMx > best) best = mMx; }
            float shift = (banEdgeLo + 0.2f) - best;
            foreach (var m in lows) m.position += new Vector3(runAxis.x * shift, 0, runAxis.y * shift);
            sb.AppendLine("low subrun n=" + lows.Count + " shift=" + shift.ToString("F2"));
        }
        if (highs.Count > 0)
        {
            float best = float.MaxValue;
            foreach (var m in highs) { float mMn, mMx; ProjExtent(m.gameObject, runAxis, basePad + 0.5f, basePad + 4.0f, null, out mMn, out mMx); if (mMn < best) best = mMn; }
            float shift = (banEdgeHi - 0.2f) - best;
            foreach (var m in highs) m.position += new Vector3(runAxis.x * shift, 0, runAxis.y * shift);
            sb.AppendLine("high subrun n=" + highs.Count + " shift=" + shift.ToString("F2"));
        }
        return sb.ToString();
    }

    // 前辺ライン上の未被覆区間を築地塀で埋める(門番所実体・長屋実体・隣接長屋躯体4mを被覆とみなす)
    public static string CloseFrontLine(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 runAxis = (fB - fA).normalized;
        float len = (fB - fA).magnitude;
        Vector2 fout = -InwardNormal(e, e.front);
        var kak = root.transform.Find("Kakoi");
        var monGrp = root.transform.Find("Omotemon");
        float basePad = PadAt(e, Vector2.Lerp(fA, fB, e.gateT));
        float T(Vector2 w) { return Vector2.Dot(w - fA, runAxis); }
        var cover = new List<(float lo, float hi)>();
        var sb = new System.Text.StringBuilder();
        // 門+番所
        foreach (Transform c in monGrp)
        {
            float mn, mx; ProjExtent(c.gameObject, runAxis, basePad + 0.4f, basePad + 4.2f, null, out mn, out mx);
            if (mn == float.MaxValue) continue;
            float off = Vector2.Dot(fA, runAxis);
            cover.Add((mn - off, mx - off));
        }
        // 前辺長屋(はみ出し削除つき)
        var toKill = new List<GameObject>();
        foreach (Transform c in kak)
        {
            if (!c.name.StartsWith("NG_F" + e.front)) continue;
            float mn, mx; ProjExtent(c.gameObject, runAxis, basePad + 0.4f, basePad + 4.2f, null, out mn, out mx);
            if (mn == float.MaxValue) continue;
            float off = Vector2.Dot(fA, runAxis);
            float lo = mn - off, hi = mx - off;
            // 隣接辺が長屋でない側へ 1.2m 超はみ出す物は削除
            int prevE = (e.front + N - 1) % N, nextE = (e.front + 1) % N;
            bool prevNag = e.nagayaEdges.Contains(prevE), nextNag = e.nagayaEdges.Contains(nextE);
            if ((lo < -1.2f && !prevNag) || (hi > len + 1.2f && !nextNag)) { toKill.Add(c.gameObject); sb.AppendLine("kill overshoot " + c.name + " [" + lo.ToString("F1") + "," + hi.ToString("F1") + "]"); continue; }
            cover.Add((lo, hi));
        }
        foreach (var g in toKill) UnityEngine.Object.DestroyImmediate(g);
        // 隣接長屋辺の躯体(奥行き~4.2m)が前辺の端を覆う
        {
            int prevE = (e.front + N - 1) % N, nextE = (e.front + 1) % N;
            if (e.nagayaEdges.Contains(prevE)) cover.Add((-0.5f, 4.2f));
            if (e.nagayaEdges.Contains(nextE)) cover.Add((len - 4.2f, len + 0.5f));
        }
        cover.Sort((x, y) => x.lo.CompareTo(y.lo));
        // ギャップ抽出→dobei充填
        float cur = 0.05f; int fills = 0;
        var gaps = new List<(float, float)>();
        foreach (var iv in cover)
        {
            if (iv.lo > cur + 0.3f) gaps.Add((cur, iv.lo));
            cur = Mathf.Max(cur, iv.hi);
        }
        if (cur < len - 0.3f) gaps.Add((cur, len - 0.05f));
        foreach (var g in gaps)
        {
            Vector2 a = fA + runAxis * (g.Item1 - 0.15f);
            Vector2 b = fA + runAxis * (g.Item2 + 0.15f);
            DobeiRun(kak, a, b, fout, "HeiFill_" + e.front + "_" + fills, NaturalMode, basePad, Vector2.zero, -1);
            fills++;
            sb.AppendLine("fill gap [" + g.Item1.ToString("F1") + "," + g.Item2.ToString("F1") + "]");
        }
        return sb.Length == 0 ? "front line closed (no gaps)" : sb.ToString();
    }

    // 囲い一式の作り直し(このセッションで生成した Kakoi/Omotemon のみ破棄)
    public static string RebuildEnclosure(string groupName)
    {
        var root = GameObject.Find(groupName);
        if (root != null)
        {
            var k = root.transform.Find("Kakoi"); if (k != null) UnityEngine.Object.DestroyImmediate(k.gameObject);
            var m = root.transform.Find("Omotemon"); if (m != null) UnityEngine.Object.DestroyImmediate(m.gameObject);
        }
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage2_Enclosure(groupName));
        sb.AppendLine(FixGateJunctions(groupName));
        sb.AppendLine(CloseFrontLine(groupName));
        return sb.ToString();
    }

    // ---------- screenshots ----------
    public static string Shot(string file, Vector3 pos, Vector3 lookAt, bool ortho, float orthoSize, int wpx, int hpx)
    {
        var go = new GameObject("TempShotCam");
        try
        {
            var cam = go.AddComponent<Camera>();
            go.transform.position = pos;
            go.transform.LookAt(lookAt);
            cam.orthographic = ortho;
            if (ortho) cam.orthographicSize = orthoSize;
            cam.fieldOfView = 60;
            cam.nearClipPlane = 0.3f; cam.farClipPlane = 3000f;
            var rt = new RenderTexture(wpx, hpx, 24);
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(wpx, hpx, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, wpx, hpx), 0, 0);
            tex.Apply();
            RenderTexture.active = null;
            cam.targetTexture = null;
            File.WriteAllBytes(file, tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(rt);
            UnityEngine.Object.DestroyImmediate(tex);
            return "saved " + file;
        }
        finally { UnityEngine.Object.DestroyImmediate(go); }
    }
}
