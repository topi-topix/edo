// 囲いの run — 長屋・土塀・板塀を辺に沿って並べる (EdoBuild の partial・2026-09-21)
//   EDO-0299 ④: EdoNishiTameikeBuilder / EdoSannoJuboBuilder を廃止するにあたり、
//   手で建てた敷地(山王社・山王武家・松平大和守)が呼んでいた run をここへ引き取った。
//   ⛔ 部材の基準点で位置を決めない(規則21)。据えるのは **触れている箇所** — SeatOnGround を使う。
//   2026-09-21 (EDO-0302): DobeiRun / PanelRun の走り方向は**実寸カーソル**へ寄せた。部材の頂点から走り方向の実寸を測り
//     (RunMeasure)、その実寸がピッチにちょうど収まるよう伸縮し、**前の駒の端の実測**へ突き付けて置く。
//     bounds の中心には合わせない。MoveToObb(呼び手なし・OBB の中心で置く)は廃止した。
//   作法の正典 docs/oki-kata.md / 部材の並べ方 Tools/Skills/unity-buke-yashiki/references/perimeter.md
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static partial class EdoBuild
{
    const string PKnagayaC = EdoAssets.Eg.KnagayaC;
    const string PKnagayaL = EdoAssets.Eg.KnagayaL;
    const string PKnagayaR = EdoAssets.Eg.KnagayaR;
    const string PHei      = EdoAssets.Eg.DobeiCenter;

    /// <summary>自然地形モード: true なら造成せず、駒は一枚ずつ地面へ据える。
    /// ユーザー指示 2026-08-08(榎坂保全)。⚠ 静的な状態なので、run を呼ぶ前に必ず立てること。</summary>
    public static bool NaturalMode = true;

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

    // ---------- nagaya run ----------
    // 部材の壁実寸(走り方向)。edogoyomi knagaya の壁 = n_wall/namako/n_dodai。ES 適用後の値をキャッシュ。
    public struct NagModule { public float lo, hi; public float W { get { return hi - lo; } } }

    static readonly Dictionary<string, NagModule> _nagMeasure = new Dictionary<string, NagModule>();

    /// <summary>部材をES倍で仮置きして壁(wall/namako/dodai)のローカルX実寸を測る。
    /// 実測: c=8.065m / l・r=7.910m(妻側が0.155m狭い)。屋根の反り・鬼は端で出るので使わない。</summary>
    public static NagModule NagayaMeasure(string path)
    {
        NagModule m;
        if (_nagMeasure.TryGetValue(path, out m)) return m;
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
        go.transform.position = Vector3.zero;
        go.transform.rotation = Quaternion.identity;
        go.transform.localScale = Vector3.one * ES;
        float mn = float.MaxValue, mx = float.MinValue;
        foreach (var r in go.GetComponentsInChildren<Renderer>())
        {
            string n = r.gameObject.name.ToLower();
            if (!(n.Contains("wall") || n.Contains("namako") || n.Contains("dodai"))) continue;
            mn = Mathf.Min(mn, r.bounds.min.x); mx = Mathf.Max(mx, r.bounds.max.x);
        }
        UnityEngine.Object.DestroyImmediate(go);
        m = new NagModule { lo = mn, hi = mx };
        _nagMeasure[path] = m;
        return m;
    }

    // A->B: 走り。outward: 敷地外向き法線。baseY: 土台レベル。gapC/gapHalf: 開口(世界座標中心/半幅) 無ければ gapHalf<=0
    /// <summary>実寸カーソル方式(2026-08-26 Phase 4a 統一・ユーザー承認済み)。
    /// 部材の壁実寸(c=8.065 / l・r=7.910)を実行時に測り、突き付けで積み上げる。
    /// 契約は EdoMatsudairaDewaBuilder.NagayaChain と同じ: 鎖は区間の中央に寄せ、端数は隅・開口が受ける。
    /// 連続グループの端は妻部材 l/r(孤立1棟は c)。gapC/gapHalf は従来同様、開口としてグループを分ける。
    /// (旧実装は屋根幅由来 PITCH=7.81 の span 均等割りで、全継ぎ目が 0.25〜1.47m 食い込んでいた)
    /// 作法は スキル unity-buke-yashiki の references/perimeter.md「ピッチは壁の実寸」。</summary>
    /// <param name="keepInside">⭐ 収めたい区画(世界 xz)。渡すと、**壁体が区画の外へ出る駒は置かない**
    /// — 奥行のある長屋は、自分の辺には収まっていても**角が鋭いところで隣の辺を跨ぐ**
    /// (2026-09-21 実測: 溜池西・三べ坂西・溜池北の5区画で 0.83〜1.88m 外へ)。
    /// その区間は薄い塀で埋める(置き方の4手④「端数は伸縮側へ流す」・`docs/oki-kata.md`)。
    /// null なら従来どおり検めない。</param>
    public static List<GameObject> NagayaRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, float baseY,
        Vector2 gapC, float gapHalf, string prefix, Vector2[] keepInside = null)
    {
        bool followGround = NaturalMode; // 自然地形モードでは各ピースを地面に追従
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg; // 表+Zを外へ
        // run 方向はローカル -X: right=(cosψ,-sinψ) → -right=(-cosψ, sinψ)
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        Vector2 sA = A; Vector2 rdir = dir;
        if (Vector2.Dot(dir, negRight) < 0) { sA = B; rdir = -dir; }
        // 開口で区間を割る(壁の実面を開口の縁で止める。旧実装の±3.9m逃げは廃止=門の開口幅を保つ)
        var segs = new List<float[]>();
        if (gapHalf > 0)
        {
            float gT = Vector2.Dot(gapC - sA, rdir);
            if (gT - gapHalf > 0f) segs.Add(new float[] { 0f, Mathf.Min(gT - gapHalf, len) });
            if (gT + gapHalf < len) segs.Add(new float[] { Mathf.Max(gT + gapHalf, 0f), len });
        }
        else segs.Add(new float[] { 0f, len });
        var mc = NagayaMeasure(PKnagayaC);
        var ml = NagayaMeasure(PKnagayaL);
        var mr = NagayaMeasure(PKnagayaR);
        float Wc = mc.W;                               // 実測 8.065m
        int idx = 0;                                   // 命名は run 通しの prefix_k(従来互換)
        int fill = 0;
        foreach (var seg in segs)
        {
            float L = seg[1] - seg[0];
            // ⛔ **一棟も入らない区間に丸ごとの長屋を置かない。**長屋は長さが固定なので、置けば
            //    区間の外へはみ出す(2026-09-21 実測: 三べ坂の五島邸で辺9の一棟が区画の外へ 1.53m。
            //    区域侵犯は許容0・規則4)。端数は**伸縮する塀**へ流す(置き方の4手④)。
            if (L < Wc - 0.30f)
            {
                if (L >= 1.2f)
                {
                    DobeiRun(parent, sA + rdir * seg[0], sA + rdir * seg[1], outward,
                             prefix + "_fill" + fill, followGround, baseY, Vector2.zero, -1);
                    fill++;
                }
                continue;
            }
            int n = Mathf.Max(1, Mathf.FloorToInt(L / Wc));   // ⛔ Round では最後の一棟がはみ出す
            // rdir ∥ ローカル-X に揃えてあるので flip 無し: 低s端=l / 高s端=r。孤立1棟は c。
            Func<int, string> pathAt = k =>
            {
                if (n > 1 && k == 0) return PKnagayaL;
                if (n > 1 && k == n - 1) return PKnagayaR;
                return PKnagayaC;
            };
            Func<string, NagModule> modOf = p2 => p2 == PKnagayaL ? ml : (p2 == PKnagayaR ? mr : mc);
            float total = 0f;
            for (int k = 0; k < n; k++) total += modOf(pathAt(k)).W;
            float cursor = seg[0] + (L - total) * 0.5f; // 鎖は区間中央寄せ(端数は隅・開口が受ける)
            for (int k = 0; k < n; k++)
            {
                string path = pathAt(k);
                var m = modOf(path);
                // ローカル +X = -rdir → s = pivot_s - x。壁 [pivot_s-hi, pivot_s-lo] → pivot_s = cursor + hi
                float sPiv = cursor + m.hi;
                var c2 = sA + rdir * sPiv;
                var cm = sA + rdir * (cursor + m.W * 0.5f); // 接地の標本は部材中心で
                // 自然地形モードでは、モジュール足元スパン(走り±4m)の地面最小値に据える(尻上がり回避)
                float pieceBase = baseY;
                if (followGround)
                {
                    float g0 = Ground(cm.x - rdir.x * 4f, cm.y - rdir.y * 4f);
                    float g1 = Ground(cm.x + rdir.x * 4f, cm.y + rdir.y * 4f);
                    float gc = Ground(cm.x, cm.y);
                    pieceBase = Mathf.Min(g0, Mathf.Min(g1, gc));
                }
                var go = Place(path, new Vector3(c2.x, pieceBase, c2.y), psi, new Vector3(ES, ES, ES), parent, prefix + "_" + idx);
                // ⛔ 底(bounds.min.y)を「足元の地形の最小」へ落とさない — 起伏のある区画で駒が埋まる
                //    (2026-09-21 実測: 山王の内藤邸で 37 枚・最悪 2.74m)。**触れている箇所**を測って据える
                //    (CLAUDE.md 規則21)。地形追従でないとき(天端を run の seat で通すとき)は設計の座のまま。
                if (followGround) { try { SeatOnGround(go, 0.10f, 600); } catch (System.Exception) { SeatBottom(go, pieceBase - 0.10f); } }
                else SeatBottom(go, pieceBase - 0.10f);
                // ⛔ 壁体が区画の外へ出る駒は置かない(区域侵犯は許容0・規則4)。薄い塀で埋め直す。
                if (keepInside != null && OutsideParcel(go.transform, keepInside))
                {
                    UnityEngine.Object.DestroyImmediate(go);
                    DobeiRun(parent, sA + rdir * cursor, sA + rdir * (cursor + m.W), outward,
                             prefix + "_in" + idx, followGround, baseY, Vector2.zero, -1);
                    idx++; cursor += m.W; continue;
                }
                made.Add(go); idx++;
                cursor += m.W;                         // 継ぎ目は必ず面一
            }
        }
        // namako(表)が外向きかを数値検証、逆なら180°回して面位置を復元
        if (made.Count > 0) VerifyFlipOutward(made, outward, prefix);
        return made;
    }

    /// <summary>駒の**壁体**(屋根・軒を外した頂点)が区画の外へ出ているか。
    /// ⛔ 軒では判定しない — 軒は越えてよい(2026-09-21 施主裁定A・`docs/oki-kata.md` §4)。
    /// 塀は境界線の上に立つので 0.60m の遊びを持つ。</summary>
    static bool OutsideParcel(Transform t, Vector2[] poly)
    {
        foreach (var w in Body(t, 300, false))
        {
            var q = new Vector2(w.x, w.z);
            if (!EdoGeom.PIP(poly, q) && EdoGeom.DistToPolyEdge(poly, q) > 0.60f) return true;
        }
        return false;
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

    // ---------- 走り方向の実寸カーソル (塀・板塀) ----------
    // 部材の走り方向(ローカルX)の実寸。倍率1・回転なしで仮置きして頂点から測る(NagayaMeasure の塀版)。
    // 屋根・軒・垂木を含む全メッシュの範囲 — 塀は壁と屋根が同じ長さで、突き付ける面は屋根ごとの端になる。
    public struct RunModule { public float lo, hi; public float W { get { return hi - lo; } } }

    static readonly Dictionary<string, RunModule> _runMeasure = new Dictionary<string, RunModule>();

    public static RunModule RunMeasure(string path)
    {
        RunModule m;
        if (_runMeasure.TryGetValue(path, out m)) return m;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(Load(path));
        go.transform.position = Vector3.zero;
        go.transform.rotation = Quaternion.identity;
        go.transform.localScale = Vector3.one;
        float mn, mx;
        ProjExtent(go, new Vector2(1f, 0f), float.MinValue, float.MaxValue, null, out mn, out mx);
        UnityEngine.Object.DestroyImmediate(go);
        if (mx <= mn) throw new Exception("RunMeasure: no mesh in " + path);
        m = new RunModule { lo = mn, hi = mx };
        _runMeasure[path] = m;
        return m;
    }

    /// <summary>駒を走り方向 <paramref name="dir"/> の実寸で <paramref name="startAbs"/>(世界の xz を dir へ射影した値)へ突き付ける。
    /// 奥行は実測した厚みの中央を「線から latOff だけ内」へ。返る <paramref name="mn"/>/<paramref name="mx"/> は
    /// 据えたあとの端の**実測値**(次の駒はこの mx へ突き付ける)。
    /// ⛔ bounds の中心へ合わせない — 奥行を先に、走りを最後に寄せるので、走りの端は必ず startAbs に来る。</summary>
    static void ButtOnRun(GameObject go, Vector2 A, Vector2 dir, Vector2 outward, float latOff, float startAbs,
                          out float mn, out float mx)
    {
        float lmn, lmx;
        ProjExtent(go, outward, float.MinValue, float.MaxValue, null, out lmn, out lmx);
        float dLat = (Vector2.Dot(A, outward) + latOff) - (lmn + lmx) * 0.5f;
        go.transform.position += new Vector3(outward.x * dLat, 0f, outward.y * dLat);
        ProjExtent(go, dir, float.MinValue, float.MaxValue, null, out mn, out mx);
        float dRun = startAbs - mn;
        go.transform.position += new Vector3(dir.x * dRun, 0f, dir.y * dRun);
        mn += dRun; mx += dRun;
    }

    // ---------- dobei run (表裏ペア) ----------
    // 走り方向: 区間を pitch に等分し、駒の実寸(RunMeasure)を pitch へ伸縮して、前の駒の実測の端へ突き付ける。
    // ⚠ 表(side 0)が鎖の主。裏(side 1)は表の端の実測に揃える(裏は 0.20m 内側へ寄る)。
    public static List<GameObject> DobeiRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        bool followGround, float flatBase, Vector2 gapC, float gapHalf)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / 2.982f));
        float pitch = len / n;
        float sx = pitch / RunMeasure(PHei).W;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        float a0 = Vector2.Dot(A, dir);
        bool chained = false; float prevEnd = 0f;
        for (int k = 0; k < n; k++)
        {
            var c2 = A + dir * (pitch * (k + 0.5f));
            if (gapHalf > 0)
            {
                float gT = Vector2.Dot(gapC - A, dir);
                if (Mathf.Abs(pitch * (k + 0.5f) - gT) < gapHalf + pitch * 0.5f - 0.01f) { chained = false; continue; }
            }
            float baseY = flatBase;
            if (followGround)
            {
                float g1 = Ground(c2.x - dir.x * pitch * 0.5f, c2.y - dir.y * pitch * 0.5f);
                float g2 = Ground(c2.x + dir.x * pitch * 0.5f, c2.y + dir.y * pitch * 0.5f);
                baseY = Mathf.Max(g1, g2);
            }
            float startAbs = chained ? prevEnd : a0 + pitch * k;
            for (int side = 0; side < 2; side++)
            {
                float ry = side == 0 ? psi : psi + 180f;
                var go = Place(PHei, Vector3.zero, ry, new Vector3(sx, ES, ES), parent,
                    prefix + "_" + k + (side == 0 ? "f" : "b"));
                float mn, mx;
                ButtOnRun(go, A, dir, outward, side == 0 ? 0.0f : -0.2f, startAbs, out mn, out mx);
                if (side == 0) { prevEnd = mx; chained = true; }
                // ⛔ 底を「足元の地形」へ落とさない — **触れている箇所**を測って据える(規則21・2026-09-21)
                if (followGround) { try { SeatOnGround(go, 0.10f, 600); } catch (System.Exception) { SeatBottom(go, baseY - 0.10f); } }
                else SeatBottom(go, baseY - 0.10f);
                made.Add(go);
            }
        }
        return made;
    }

    // ---------- 板塀/穂垣 run — 片面ポリゴンなので表裏の対で置く ----------
    // asset: 5枚スパンOBJ。走りは DobeiRun と同じ実寸カーソル。パネル毎に接地。
    public static List<GameObject> PanelRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        string assetPath, Vector2 gapC, float gapHalf)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        // スパン実測(ES基準)
        float spanLocal = RunMeasure(assetPath).W;
        float spanES = spanLocal * ES;
        if (spanES < 0.5f) spanES = 7.49f;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / (spanES - 0.15f)));
        float pitch = len / n;
        float sx = pitch / spanLocal;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        float a0 = Vector2.Dot(A, dir);
        bool chained = false; float prevEnd = 0f;
        for (int k = 0; k < n; k++)
        {
            var c2 = A + dir * (pitch * (k + 0.5f));
            if (gapHalf > 0)
            {
                float gT = Vector2.Dot(gapC - A, dir);
                if (Mathf.Abs(pitch * (k + 0.5f) - gT) < gapHalf + pitch * 0.5f - 0.01f) { chained = false; continue; }
            }
            float g1 = Ground(c2.x - dir.x * pitch * 0.5f, c2.y - dir.y * pitch * 0.5f);
            float g2 = Ground(c2.x + dir.x * pitch * 0.5f, c2.y + dir.y * pitch * 0.5f);
            float baseY = Mathf.Max(g1, g2);
            float startAbs = chained ? prevEnd : a0 + pitch * k;
            for (int side = 0; side < 2; side++)
            {
                float ry = side == 0 ? psi : psi + 180f;
                var go = Place(assetPath, Vector3.zero, ry, new Vector3(sx, ES, ES), parent,
                    prefix + "_" + k + (side == 0 ? "f" : "b"));
                float mn, mx;
                ButtOnRun(go, A, dir, outward, side == 0 ? 0.0f : -0.12f, startAbs, out mn, out mx);
                if (side == 0) { prevEnd = mx; chained = true; }
                SeatBottom(go, baseY - 0.10f);
                made.Add(go);
            }
        }
        return made;
    }
}
