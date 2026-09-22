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

    // ---------- 練塀 run(一体物・EDO-0351) ----------
    // DobeiRun(表裏2枚の板塀)と違い Dobei2m は1駒で厚みを持つ一体物なので、side ループは無い。
    // 走り方向は RunMeasure/ButtOnRun の実寸カーソル(PanelRun と同じ idiom)。
    // 開口(門)の脇で塀が行き止まる自由端だけ Dobei2mEnd(妻塞ぎ)に差し替える —
    // 辺の外側の隅(区画の角)は塀の Kado 留め継ぎが未解決なので、従来どおり開放のまま置く
    // (DobeiRun にも無かった隅の扱いをここで新たに約束しない・kado-mitre-parts.md)。
    public static List<GameObject> NeribeiRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        bool followGround, float flatBase, Vector2 gapC, float gapHalf)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float bodyLen = RunMeasure(EdoAssets.Own.Dobei2m).W;
        var segs = new List<float[]>();
        if (gapHalf > 0)
        {
            float gT = Vector2.Dot(gapC - A, dir);
            if (gT - gapHalf > 0f) segs.Add(new float[] { 0f, Mathf.Min(gT - gapHalf, len) });
            if (gT + gapHalf < len) segs.Add(new float[] { Mathf.Max(gT + gapHalf, 0f), len });
        }
        else segs.Add(new float[] { 0f, len });
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        float a0 = Vector2.Dot(A, dir);
        int idx = 0;
        foreach (var seg in segs)
        {
            float L = seg[1] - seg[0];
            if (L < bodyLen * 0.5f) continue;    // 一枚も入らない端数は置かない(呼び手が別途埋める)
            int n = Mathf.Max(1, Mathf.RoundToInt(L / bodyLen));
            float pitch = L / n;
            // 開口に面した端だけ閉じる。両端とも開口に面す(n==1 の短い残り)ときは低位側を優先。
            bool capLo = gapHalf > 0 && seg[0] > 0.01f;
            bool capHi = gapHalf > 0 && seg[1] < len - 0.01f && !(n == 1 && capLo);
            bool chained = false; float prevEnd = 0f;
            for (int k = 0; k < n; k++)
            {
                bool close = (k == 0 && capLo) || (k == n - 1 && capHi);
                bool mirror = close && !(k == 0 && capLo);   // 高位側の妻塞ぎは回転で足りる(EdoAssets.Own.Dobei2mEnd の注記)
                string path = close ? EdoAssets.Own.Dobei2mEnd : EdoAssets.Own.Dobei2m;
                float pieceLen = RunMeasure(path).W;
                float sx = pitch / pieceLen;
                float ry = mirror ? psi + 180f : psi;
                var go = Place(path, Vector3.zero, ry, new Vector3(sx, 1f, 1f), parent, prefix + "_" + idx);
                float startAbs = chained ? prevEnd : a0 + seg[0] + pitch * k;
                float mn, mx;
                ButtOnRun(go, A, dir, outward, 0f, startAbs, out mn, out mx);
                prevEnd = mx; chained = true;
                if (followGround) { try { SeatOnGround(go, 0.10f, 600); } catch (Exception) { SeatBottom(go, flatBase - 0.10f); } }
                else SeatBottom(go, flatBase - 0.10f);
                made.Add(go); idx++;
            }
        }
        return made;
    }

    // ---------- 板塀/穂垣 run — 片面ポリゴンなので表裏の対で置く ----------
    // asset: 5枚スパンOBJ。走りは DobeiRun と同じ実寸カーソル。パネル毎に接地。
    /// <remarks>据えは DobeiRun と同じ — **触れている箇所**を測る(規則21)。失敗したときだけ bounds の底(EDO-0342)。</remarks>
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
                try { SeatOnGround(go, 0.10f, 600); } catch (Exception) { SeatBottom(go, baseY - 0.10f); }
                made.Add(go);
            }
        }
        return made;
    }

    // ══════════════════════════════════════════════════════════════════════
    //  囲いの作り分け (EDO-0324・2026-09-21)
    //  ⛔ 「どの区画が何を持つか」はここに書かない — それは類型表と EdoTypologyBuilder の持ち場。
    //     ここに書くのは **置く・測る・突き付ける・据える** だけ(規則21)。
    // ══════════════════════════════════════════════════════════════════════

    /// <summary>辺 A→B に**種別どおりの囲い**を建てる。
    /// ⛔ 2026-09-21 まで種別は捨てられていて、ita / dobei / ita+ikegaki / ishigaki+hei / yarai / boji / kui の
    /// **7 種が全部おなじ板塀**で建っていた(EDO-0324)。
    /// <para><paramref name="note"/> に「何で建てたか・何を代用したか」を必ず返す — ⛔ 黙って代用しない(規則7・19)。
    /// 既定(<paramref name="kind"/> が null や未知の語)は**今までどおりの板塀**で、呼び手を変えない限り姿は変わらない。</para></summary>
    public static List<GameObject> FenceRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string kind,
        float baseY, Vector2 gapC, float gapHalf, string prefix, out string note)
    {
        switch (kind)
        {
            case "none":
                note = "囲わない(表の fence=none)";
                return new List<GameObject>();

            case "yarai":
            {
                // 竹矢来の駒は在庫に無い。穂垣(片面ポリゴン・5スパン)を表裏の対で立てる。
                var made = PanelRun(parent, A, B, outward, prefix, EdoAssets.Eg.Hogaki5, gapC, gapHalf);
                float h = made.Count > 0 ? RB(made[0]).size.y : float.NaN;   // ⭐ 据えた駒の実メッシュから測る
                note = string.Format("竹矢来=穂垣で代用 {0}枚(実丈 {1:F2}m)⚠ 竹矢来(交叉させた竹)の駒は在庫に無い — EDO-0318",
                                     made.Count, h);
                return made;
            }

            case "boji":
                // 傍示杭 = 境を示す**標**。杭列より疎に、太い1径で立てる。
                return KuiRun(parent, A, B, outward, prefix, gapC, gapHalf, 5f, new float[] { 0.18f }, "傍示杭", out note);

            case "kui":
                return KuiRun(parent, A, B, outward, prefix, gapC, gapHalf, 1f, new float[] { 0.12f, 0.15f, 0.18f }, "杭列", out note);

            case "ita+ikegaki":
            {
                var made = DobeiRun(parent, A, B, outward, prefix, NaturalMode, baseY, gapC, gapHalf);
                // ⭐ EDO-0171: 辺の内側が法面(地形が現に傾いている)なら、1間ピッチの生垣(並木)ではなく
                //    山王社叢 帯3(南面)の rinen 設計値をそのまま使った**連続の林縁帯**で覆う。
                //    ⛔ 生垣のままだと、法尻に接する坊(常明院・智乗院)の前で山が下半分だけ裸に見える
                //    (2026-09-08 山王庭方 → 掲示板 EDO-0171・2026-09-21 施主指示で担当typology)。
                float rise, grade;
                bool slope = EdgeFacesSlope(A, B, outward, out rise, out grade);
                if (slope)
                {
                    int nr = RinenBand(parent, A, B, outward, prefix + "rin", gapC, gapHalf);
                    note = string.Format("板塀 {0}枚 + 法面の林縁帯 {1}本(帯の内 0.91〜4.55m の勾配 {2:P0}・高低差 {3:F2}m"
                                        + " ⇒ 生垣でなく山王社叢 帯3 rinen の設計値 丈1.8〜2.5m・5〜7本/100m² で連続して覆った。EDO-0171)",
                                         made.Count, nr, grade, rise);
                }
                else
                {
                    int ni = IkegakiRow(parent, A, B, outward, prefix + "ike", made, gapC, gapHalf);
                    note = string.Format("板塀 {0}枚 + 生垣 {1}駒(生垣は塀の**触れている箇所**まで寄せた・帯の内の勾配 {2:P0} は法面と見ない)",
                                         made.Count, ni, grade);
                }
                return made;
            }

            case "dobei":
                note = null;   // EDO-0351: 練塀の一体物(Dobei2m)が在る。板塀代用は誤りだった(EDO-0318 ⑤ の訂正)
                return NeribeiRun(parent, A, B, outward, prefix, NaturalMode, baseY, gapC, gapHalf);

            case "ishigaki+hei":
                note = "⚠ 腰の石垣は unity-modular-stonewall の run の持ち場 — いまは**塀だけ**建てた";
                return DobeiRun(parent, A, B, outward, prefix, NaturalMode, baseY, gapC, gapHalf);

            case "ita":
                note = null;
                return DobeiRun(parent, A, B, outward, prefix, NaturalMode, baseY, gapC, gapHalf);

            default:
                note = kind == null ? null : ("⚠ 知らない囲いの種別 \"" + kind + "\" — 板塀で建てた");
                return DobeiRun(parent, A, B, outward, prefix, NaturalMode, baseY, gapC, gapHalf);
        }
    }

    /// <summary>**杭列**(傍示杭・杭)。⛔ 連続の塀にしない — **間を空けて立てる**。
    /// <para>芯々 = <paramref name="pitchKen"/> 間(江戸間 1 間 = 1.818m は CLAUDE.md の不変値)。
    /// ⚠ 何間置きかは史料が無い【確度 U】— 杭列は 1 間、傍示杭は**標**なので 5 間に採った。
    /// 隙は**据えた杭の実幅を測って**刷るので、駒を替えれば刷る値も変わる。</para>
    /// 径は <paramref name="dias"/> を混ぜ、yaw は全周へ振る(⛔ 1 種を等間隔に並べない — `EdoAssets.Own.Kui` の注記)。
    /// 据えは <see cref="SeatBuried"/> の 1/3 埋め — 杭は地面に**刺さる**物で、底を地面に置く物ではない。
    /// ⛔ ピボット(杭は頭が原点で −Y へ 1.55 垂れる)で高さを決めない(規則21)。</summary>
    public static List<GameObject> KuiRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        Vector2 gapC, float gapHalf, float pitchKen, float[] dias, string label, out string note)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / (ES * pitchKen)));
        float pitch = len / n;
        // ⭐ 種は**辺の座標**から作る(版を跨いで同じ姿になる)。⛔ string.GetHashCode は実行ごとに撹拌される。
        var rnd = new System.Random(Mathf.RoundToInt((A.x * 7.3f + A.y * 11.9f + B.x * 29.1f + B.y * 53.7f) * 100f) & 0x7fffffff);
        float gT = gapHalf > 0 ? Vector2.Dot(gapC - A, dir) : 0f;
        for (int k = 0; k <= n; k++)
        {
            float t = pitch * k;
            if (gapHalf > 0 && Mathf.Abs(t - gT) < gapHalf) continue;          // 門の開口は空ける
            var c = A + dir * t;
            var go = Place(EdoAssets.Own.Kui(dias[rnd.Next(dias.Length)]), new Vector3(c.x, 0f, c.y),
                           (float)rnd.NextDouble() * 360f, Vector3.one, parent, prefix + "_" + k);
            if (go == null) continue;
            try { SeatBuried(go, 1f / 3f, 200); }
            catch (Exception) { UnityEngine.Object.DestroyImmediate(go); continue; }
            made.Add(go);
        }
        // ⭐ 刷る丈は**地面から上に出ている分**(頭の高さ − 真下の地表)。
        //    ⛔ メッシュの高さ(1.55m)を刷らない — 1/3 は地中で、見える丈ではない(検査の文言と実装を合わせる)。
        float w = 0f, ex = 0f;
        foreach (var go in made)
        {
            var b = RB(go);
            w = Mathf.Max(w, Mathf.Max(b.size.x, b.size.z));
            ex = Mathf.Max(ex, b.max.y - Ground(b.center.x, b.center.z));
        }
        note = string.Format("{0} {1}本(芯々 {2:F2}m = {3:F0}間【U】・杭の実幅 {4:F2}m ⇒ 隙 {5:F2}m・露出丈 {6:F2}m・{7})",
                             label, made.Count, pitch, pitchKen, w, pitch - w, ex,
                             dias.Length > 1 ? "径" + dias.Length + "種を混ぜ yaw を振った" : "yaw を振った");
        return made;
    }

    /// <summary>板塀の内側に**生垣**(1 間モジュール)を並べる。走りは 1 間ピッチ
    /// (駒の実幅 1.91m は葉の持ち出し込みで、**突き付けるのは 1 間の木口**)。
    /// 奥行は塀の**触れている箇所**まで <see cref="Abut(GameObject,GameObject,Vector3,float,out Vector3,out int,float,int,bool)"/> で寄せる
    /// — ⛔ 外接箱 + 定数で寄せない(規則21)。返り値 = 据えた駒の数。</summary>
    static int IkegakiRow(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
                          List<GameObject> fence, Vector2 gapC, float gapHalf)
    {
        if (fence == null || fence.Count == 0) return 0;
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        int n = Mathf.FloorToInt(len / ES);
        if (n < 1) return 0;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        var toFence = new Vector3(outward.x, 0f, outward.y);
        float head = (len - ES * n) * 0.5f;
        float gT = gapHalf > 0 ? Vector2.Dot(gapC - A, dir) : 0f;
        // ⭐ 突き付ける相手は塀の**内側の葉**(DobeiRun は表裏の対で置き、裏の駒の名が "b" で終わる)。
        var inner = fence.Where(f => f.name.EndsWith("b")).ToList();
        if (inner.Count == 0) inner = fence;
        int made = 0;
        for (int k = 0; k < n; k++)
        {
            float t = head + ES * (k + 0.5f);
            if (gapHalf > 0 && Mathf.Abs(t - gT) < gapHalf + ES * 0.5f) continue;   // 門の開口は空ける
            // 仮置きは塀の内側へ引いた所。⭐ 位置は置いたあと**測って**決める(この 1.6m は姿に残らない)。
            var c = A + dir * t - outward * 1.6f;
            var go = Place(EdoAssets.Own.Ikegaki(k == 0 || k == n - 1), new Vector3(c.x, 0f, c.y), psi,
                           Vector3.one, parent, prefix + "_" + k);
            if (go == null) continue;
            try { SeatOnGround(go, 0.05f, 300); } catch (Exception) { }
            GameObject near = null; float bd = float.MaxValue;
            foreach (var f in inner)
            {
                float d = Vector3.Distance(f.transform.position, go.transform.position);
                if (d < bd) { bd = d; near = f; }
            }
            if (near != null) { Vector3 at; int cn; Abut(go, near, toFence, 0f, out at, out cn, 0.30f, 400); }
            try { SeatOnGround(go, 0.05f, 300); } catch (Exception) { }
            made++;
        }
        return made;
    }

    /// <summary>辺の**内側**(据える帯そのもの)が法面かを、地形を実測して判定する(EDO-0171)。
    /// ⛔ 座標や区画の並びから推さない(規則9・11)— 生垣を据える帯(辺の内側 0.5〜2.5間)の
    /// 両端で地表を測り、その高低差と勾配だけで決める。⚠ 閾値は当方の見当【U】(斜面の下限)—
    /// `unity-buke-yashiki` の「斜面は木でしっかり覆い、途中の柵は置かない」(2026-09-06 施主基準)の
    /// 対象になる急さの目安で、実機のレンダで見て要調整。</summary>
    const float RINEN_RISE_MIN = 1.0f;
    const float RINEN_GRADE_MIN = 0.30f;
    static bool EdgeFacesSlope(Vector2 A, Vector2 B, Vector2 outward, out float rise, out float grade)
    {
        var mid = (A + B) * 0.5f;
        float lo = 0.5f * ES, hi = 2.5f * ES;                  // 生垣/林縁帯と同じ刻み(0.91〜4.55m・内側)
        float h0 = Ground(mid.x - outward.x * lo, mid.y - outward.y * lo);
        float h1 = Ground(mid.x - outward.x * hi, mid.y - outward.y * hi);
        rise = Mathf.Abs(h1 - h0);
        grade = rise / (hi - lo);
        return rise >= RINEN_RISE_MIN && grade >= RINEN_GRADE_MIN;
    }

    static string[] _rinenPal;
    /// <summary>法面の林縁帯の低木。⭐ 丈 1.8〜2.5m は `Own.Teiboku` の H20(2.0m)/H24(2.4m) の2段で受ける
    /// (H12/H16 は範囲の下)。個体は部材方の在庫どおり 1〜3。</summary>
    static string[] RinenPal
    {
        get
        {
            if (_rinenPal == null) _rinenPal = new[]
            {
                EdoAssets.Own.Teiboku("H20", 1), EdoAssets.Own.Teiboku("H20", 2), EdoAssets.Own.Teiboku("H20", 3),
                EdoAssets.Own.Teiboku("H24", 1), EdoAssets.Own.Teiboku("H24", 2),
            };
            return _rinenPal;
        }
    }

    /// <summary>法面の**林縁帯**(低木。EDO-0171)。⭐ 数値は山王社叢 帯3(南面)の `rinen` の設計値を
    /// そのまま使う(庭方 2026-09-08 十六巡目 C-2・`docs/Sashizu/sanno_sashizu.json`
    /// `slopeBands[2].rinen` — fromKen 0.5〜toKen 2.5・teibokuPer100 [5,7]・teibokuH [1.8,2.5])。
    /// 掲示板 EDO-0171 で山王庭方が「続きとして揃えるなら引いてください」と渡した値をそのまま写した
    /// (⛔ 新しい丈・密度を発明しない)。
    /// <para>⛔ <see cref="IkegakiRow"/>(1 間ピッチの並木)の代わりに呼ぶ — 法面は塊でなく
    /// **連続して**覆う(2026-09-06 施主基準「途中の柵は置かない」と同じ「隙を作らない」思想)。
    /// 据えるのは辺の内側 0.5〜2.5間の帯へ乱数で撒くだけで、Abut のような取り合いは持たない
    /// (低木は塀に突き付ける物ではない)。</para></summary>
    static int RinenBand(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
                         Vector2 gapC, float gapHalf)
    {
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float lo = 0.5f * ES, hi = 2.5f * ES;
        float depth = hi - lo;
        if (len < 0.5f) return 0;
        // ⭐ 種は辺の座標から作る(版を跨いで同じ姿になる・KuiRun と同じ作法)。
        var rnd = new System.Random(Mathf.RoundToInt((A.x * 5.1f + A.y * 17.3f + B.x * 23.7f + B.y * 41.9f) * 100f) & 0x7fffffff);
        float density = Mathf.Lerp(5f, 7f, (float)rnd.NextDouble());     // 5〜7本/100m²(sanno rinen そのまま)
        int n = Mathf.Max(1, Mathf.RoundToInt(len * depth / 100f * density));
        float gT = gapHalf > 0 ? Vector2.Dot(gapC - A, dir) : 0f;
        const float MIN_SEP = 1.5f;                        // H20/H24 の樹冠(実測 1.8〜2.2m)が触れない間隔
        var placed = new List<Vector2>();
        int made = 0;
        for (int tries = 0; tries < n * 15 && made < n; tries++)
        {
            float t = (float)rnd.NextDouble() * len;
            if (gapHalf > 0 && Mathf.Abs(t - gT) < gapHalf) continue;    // 門の開口は空ける
            float d = lo + (float)rnd.NextDouble() * depth;
            var c = A + dir * t - outward * d;                          // 塀の内側(生垣と同じ向き)
            bool clear = true;
            foreach (var p in placed) if (Vector2.Distance(p, c) < MIN_SEP) { clear = false; break; }
            if (!clear) continue;
            var path = RinenPal[rnd.Next(RinenPal.Length)];
            var go = Place(path, new Vector3(c.x, 0f, c.y), (float)rnd.NextDouble() * 360f,
                          Vector3.one, parent, prefix + "_" + made);
            if (go == null) continue;
            try { SeatOnGround(go, 0.05f, 300); } catch (Exception) { UnityEngine.Object.DestroyImmediate(go); continue; }
            placed.Add(c);
            made++;
        }
        return made;
    }
}
