// 類型の庭 — 寺社の境内(garden=keidai)。2026-09-27・EDO-0477 P5。
//
// 意匠は庭方の設計(2026-09-27・全文 UserData/EDO0477_survey/G_niwa_keidai.json)。⛔ 意匠を実装側で作り変えない(規則17)。
//   地表 … 参道(寺=白洲 / 社家・坊=叩き土)・本堂の前の白洲(寺 = 桁行+2間 × min(4間, 前庭)/ 社家・坊 = 式台前 桁行+1間 × 2間)
//          ・棟の軒から 3m と井戸まわりは叩き土・林と縁の帯の下は林床(rinsho)・残りは草(塗らない)
//   層   … 境内木・縁の帯・斜面の林・墓地の囲み・低木と下草
//   点景 … 手水鉢 1・献灯の一対(本堂の前・参道の左右)・井戸 1
// ⛔ 置き方の算術(退避・芯々・据え・乱れ)はここに書かない — EdoBuildNiwa.cs の持ち場(規則21)。
// ⭐ 木の控えは施主の規則(2026-09-23)── 幹の芯は区画の線と囲いから 2.0m(NiwaSet.TREE_KEEP)・
//    高木は壁のある棟から 3 間(KEIDAI_TALL_FROM_WALL)・樹冠は区画の線を越えて張り出してよい。
// 当たる先: 類型表の寺社 16 区画(kind = temple / bo / shake)。

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static partial class EdoTypologyBuilder
{
    /// <summary>高木の幹の芯から、壁のある棟の壁体までの控え[m] = 3 間(施主の規則・山王 EDO-0401 の型)。</summary>
    const float KEIDAI_TALL_FROM_WALL = 3f * 1.818f;
    /// <summary>「斜面」とみなす勾配(1:4)。これより急な庭域は閉じた林で覆う(施主: 斜面は木でしっかり覆う)。</summary>
    const float KEIDAI_SLOPE = 0.25f;

    struct KeidaiK { public float bandW, bandPitch; public int bandCap, keidaiboku; }

    /// <summary>kind ごとの係数(庭方の設計 k)。</summary>
    static KeidaiK KeidaiFor(string kind, float area)
    {
        switch (kind)
        {
            case "temple": return new KeidaiK { bandW = 6.0f, bandPitch = 30f, bandCap = 90, keidaiboku = 3 };
            case "shake":  return new KeidaiK { bandW = 5.0f, bandPitch = 35f, bandCap = 60, keidaiboku = 1 };
            default:       return new KeidaiK { bandW = 4.0f, bandPitch = 40f, bandCap = 30, keidaiboku = area >= 1500f ? 1 : 0 };
        }
    }

    /// <summary>庭域の点の勾配(±1m の差の大きい方 ÷ 2m)。造成の後の地表で測る。</summary>
    static float KeidaiSlope(Vector2 p)
    {
        float gx = Mathf.Abs(EdoBuild.Ground(p.x + 1f, p.y) - EdoBuild.Ground(p.x - 1f, p.y)) * 0.5f;
        float gz = Mathf.Abs(EdoBuild.Ground(p.x, p.y + 1f) - EdoBuild.Ground(p.x, p.y - 1f)) * 0.5f;
        return Mathf.Max(gx, gz);
    }

    /// <summary>寺社の境内の庭。<paramref name="mune"/> は据わった棟、<paramref name="half"/> は参道の帯の片幅。</summary>
    static void NiwaKeidai(Spec s, Transform grp, EdoBuild.NiwaField f, Vector2[] poly, Edge front,
                           System.Random rnd, List<Transform> mune, Vector2 gateC, float half, Vector2 sandoB,
                           List<string> want, List<string> got, List<string> log)
    {
        string kind = s.kind ?? "bo";
        bool temple = kind == "temple";
        float area = Mathf.Abs(EdoGeom.SignedArea(poly));
        var k = KeidaiFor(kind, area);
        var tree = EdoBuild.NiwaSet.Tree; var chu = EdoBuild.NiwaSet.Chuboku;
        var shrub = EdoBuild.NiwaSet.Shrub; var kusa = EdoBuild.NiwaSet.Kusa;
        var vDir = -front.outward; var uDir = new Vector2(vDir.y, -vDir.x);

        // 壁のある棟の壁体(屋根を除く)── 高木の控え 3 間を測る相手
        var occBody = new EdoBuild.NiwaOcc();
        foreach (var t in mune) occBody.AddBody(t, 300, false);
        Func<Vector2, bool> tallOk = p => occBody.Dist(p, KEIDAI_TALL_FROM_WALL + 1f) >= KEIDAI_TALL_FROM_WALL;

        // 本堂(主屋)の表の面 ── 前の白洲・献灯・手水の基準。⛔ 基準点で測らない(規則21)── 壁体の実頂点を参道の軸へ射影する。
        var hall = mune.FirstOrDefault(t => t.name.StartsWith("Honden")) ?? mune[0];
        float hv0 = float.MaxValue, hu0 = float.MaxValue, hu1 = float.MinValue;
        foreach (var w in EdoBuild.BodyExRoof(hall, 600))
        {
            var q = new Vector2(w.x, w.z) - gateC;
            hv0 = Mathf.Min(hv0, Vector2.Dot(q, vDir));
            float u = Vector2.Dot(q, uDir); hu0 = Mathf.Min(hu0, u); hu1 = Mathf.Max(hu1, u);
        }
        float hallFaceW = hu1 - hu0, hallUc = (hu0 + hu1) * 0.5f;

        // ── 地表(印を置くだけ・⛔ 地形には触らない ── 塗るのは EdoGardenSurfacePaint)──
        //    参道は Niwa() が帯の印を置いた(寺=白洲)。社家・坊の参道は叩き土へ差し替える。
        if (!temple)
        {
            var sz = grp.Find("Ground_shirasu");
            var z = sz != null ? sz.GetComponent<NiwaGroundZone>() : null;
            if (z != null) { z.kind = "tataki"; sz.name = "Ground_tataki_sando"; }
        }
        float maeW = hallFaceW + (temple ? 2f : 1f) * ES;
        float maeD = temple ? Mathf.Min(4f * ES, Mathf.Max(0f, hv0 - 1f)) : Mathf.Min(2f * ES, Mathf.Max(0f, hv0 - 1f));
        float maeArea = 0f;
        if (maeD > 0.5f)
        {
            var c0 = gateC + uDir * hallUc + vDir * (hv0 - maeD);
            var quad = new[] { c0 - uDir * maeW * 0.5f, c0 + uDir * maeW * 0.5f,
                               c0 + uDir * maeW * 0.5f + vDir * maeD, c0 - uDir * maeW * 0.5f + vDir * maeD };
            var go = new GameObject("Ground_shirasu_maeniwa");
            go.transform.SetParent(grp, false);
            var zn = go.AddComponent<NiwaGroundZone>();
            zn.kind = "shirasu";
            foreach (var q in quad) zn.quads.Add(new Vector3(q.x, 0f, q.y));
            foreach (var p in poly) zn.clip.Add(new Vector3(p.x, 0f, p.y));
            maeArea = maeW * maeD;
            f.AddBand(c0 + vDir * (maeD * 0.5f) - uDir * maeW * 0.5f, c0 + vDir * (maeD * 0.5f) + uDir * maeW * 0.5f, maeD * 0.5f);   // 白洲にも木を入れない
        }
        var tsuchi = f.Cells.Where(p => f.Eaves.Dist(p, 4f) <= 3f).ToList();
        AddGroundZone(grp, "tataki", tsuchi);

        // ── 層 ① 斜面の林(閉じた林)── 急な庭域の点を塊で埋める。⭐ 下る側は地形が決める(点の勾配で採る)
        var slope = f.Cells.Where(p => KeidaiSlope(p) >= KEIDAI_SLOPE).ToList();
        float slopeArea = slope.Count * f.Cell * f.Cell;
        {
            float rr = MaxCrown(LinPal) * tree.ScaleHi;
            int nForest = Mathf.Min(NIWA_BUDGET / 2, Mathf.RoundToInt(slopeArea / (Mathf.PI * rr * rr) * 1.6f));
            var pool = slope.Where(tallOk).ToList();
            var mix = LinMix(rnd, DeShare(nForest));
            int made = 0, tried = 0;
            while (tried < nForest && f.Komas.Count < NIWA_BUDGET)
            {
                var site = TakeSite(pool, rnd, f, rr, tree);
                if (site == null) break;
                int n = rnd.NextDouble() < 2.0 / 3.0 ? 3 : 5; tried += n;
                made += EdoBuild.NiwaClump(grp, "Shamenrin", f, site.Value, LinPal, n, rnd, tree, "斜面の林", mix).Count;
            }
            want.Add("斜面の林 " + tried); got.Add("斜面の林 " + made);
            log.Add(string.Format("    斜面の林: 勾配 1:4 より急な庭域 {0:F0}m² → {1}/{2}本(幹は壁のある棟から 3 間・囲いと区画の線から {3:F1}m)",
                                  slopeArea, made, tried, EdoBuild.NiwaSet.TREE_KEEP));
        }

        // ── 層 ② 縁の帯(囲いの内側の面から TREE_KEEP 〜 TREE_KEEP + 帯の幅)── 門の辺は空ける
        var bandPts = new List<Vector2>();
        {
            float lo = EdoBuild.NiwaSet.TREE_KEEP, hi = lo + k.bandW;
            float per = Perimeter(poly);
            int sites = Mathf.Max(1, Mathf.RoundToInt(per / k.bandPitch));
            bool fromWall; int blind;
            bandPts = EdoBuild.NiwaWallBandSites(f, lo, hi, sites, rnd,
                          p => EdoGeom.DistToEdge(p, front.a, front.b) < hi + 1.5f, out fromWall, out blind);
            var mix = LinMix(rnd, DeShare(k.bandCap));
            int made = 0, tried = 0;
            foreach (var p in bandPts)
            {
                if (made >= k.bandCap || f.Komas.Count >= NIWA_BUDGET) break;
                if (!tallOk(p)) continue;
                int n = rnd.NextDouble() < 2.0 / 3.0 ? 3 : 5; tried += n;
                made += EdoBuild.NiwaClump(grp, "Enbo", f, p, LinPal, n, rnd, tree, "縁の帯", mix).Count;
            }
            want.Add("縁の帯 " + tried); got.Add("縁の帯 " + made);
            log.Add(string.Format("    縁の帯: 周長 {0:F0}m ÷ {1:F0} = {2}箇所 → {3}/{4}本(囲いの実メッシュから {5:F1}〜{6:F1}m・上限 {7}{8})",
                                  per, k.bandPitch, bandPts.Count, made, tried, lo, hi, k.bandCap,
                                  fromWall ? "" : "・⚠ 囲いが無く区画の線から"));
        }

        // ── 層 ③ 境内木(本堂の脇と背の大木)── 参道と本堂の前は空ける
        {
            var pool = f.Cells.Where(p =>
            {
                var q = p - gateC;
                if (Vector2.Dot(q, vDir) < hv0 - 1f && Mathf.Abs(Vector2.Dot(q, uDir) - hallUc) < maeW * 0.5f + 2f) return false;   // 本堂の前
                return tallOk(p) && occBody.Dist(p, 25f) <= 20f;
            }).ToList();
            Layer(grp, "境内木", f, pool, LinEv, k.keidaiboku, rnd, tree, want, got);
        }

        // ── 層 ④ 墓地の囲み(墓地の実メッシュから 1.5〜4m に中木)──
        var bochi = mune.FirstOrDefault(t => t.name.StartsWith("Bochi"));
        if (bochi != null)
        {
            var ob = new EdoBuild.NiwaOcc(); ob.AddBody(bochi, 300, false);
            var ring = f.Cells.Where(p => { float d = ob.Dist(p, 5f); return d >= 1.5f && d <= 4f; }).ToList();
            float bper = 2f * (EdoBuild.ProjSpan(bochi.gameObject, uDir) + EdoBuild.ProjSpan(bochi.gameObject, vDir));
            Layer(grp, "墓地の囲み", f, ring, ChubokuPal, Mathf.Clamp(Mathf.RoundToInt(bper / 6f), 3, 9), rnd, chu, want, got);
        }

        // ── 層 ⑤ 低木・下草 ── 塀際と棟の隅。⭐ 本数は周長と庭域の従属値
        {
            var hei = f.Cells.Where(p => f.Walls.Dist(p, 5f) <= EdoBuild.NiwaSet.TREE_KEEP + 1.5f).ToList();
            Layer(grp, "塀際の低木", f, hei, TeibokuPal, Mathf.Clamp(Mathf.FloorToInt(Perimeter(poly) / 20f), 3, 15), rnd, shrub, want, got);
            var near = f.Cells.Where(p => { float d = f.Eaves.Dist(p, 6f); return d >= 0.5f && d <= 4f; }).ToList();
            Layer(grp, "棟まわりの低木", f, near, TeibokuPal, Mathf.Clamp(Mathf.FloorToInt(f.Area / 250f), 2, 12), rnd, shrub, want, got);
            var under = new List<Vector2>(slope); under.AddRange(bandPts);
            Layer(grp, "下草", f, under.Count > 0 ? under : new List<Vector2>(f.Cells), ShidaPal,
                  Mathf.Clamp(Mathf.FloorToInt(f.Area / 120f), 4, 30), rnd, kusa, want, got);
        }

        // 林床の地表 ── 林と縁の帯の駒の足もと(印だけ)
        {
            var rin = new List<Vector2>();
            foreach (var km in f.Komas)
                if (km.layer == "斜面の林" || km.layer == "縁の帯" || km.layer == "境内木") rin.Add(km.trunk);
            AddGroundZone(grp, "rinsho", rin, 3.0f);
        }

        // ── 点景 ── 献灯の一対(本堂の前・参道の左右)・手水鉢・井戸
        {
            var o = EdoBuild.NiwaSet.Stone;
            float r = EdoBuild.CrownR(EdoAssets.Eg.ToroKasuga) * ES;
            float vAt = hv0 - Mathf.Min(3f, Mathf.Max(1.2f, maeD * 0.6f));
            int made = 0;
            for (int sd = -1; sd <= 1; sd += 2)
            {
                var p = gateC + vDir * vAt + uDir * (hallUc + sd * (half + 1.2f + r));
                if (f.Put(grp, EdoAssets.Eg.ToroKasuga, p, JYaw(front.outward), ES, 0f, "Kenntou_" + (sd < 0 ? "L" : "R"), "献灯", o) != null) made++;
            }
            want.Add("献灯 2(一対)"); got.Add("献灯 " + made);
            if (made == 1) log.Add("    ⚠ 献灯が片方しか据わらない — 一対にならない(据わった方も残す・柔らかい)");

            var chozuPool = f.Cells.Where(p =>
            {
                var q = p - gateC; float v = Vector2.Dot(q, vDir), u = Mathf.Abs(Vector2.Dot(q, uDir) - hallUc);
                return v > hv0 * 0.4f && v < hv0 - 1f && u > half + 1f && u < half + 5f;
            }).ToList();
            float rc = EdoBuild.CrownR(EdoAssets.Own.DoiChozu);
            var cs = TakeSite(chozuPool, rnd, f, rc, o);
            bool chozu = cs != null && f.Put(grp, EdoAssets.Own.DoiChozu, cs.Value, JYaw(uDir), 1f, 0f, "Chozu", "手水鉢", o) != null;
            want.Add("手水鉢 1"); got.Add("手水鉢 " + (chozu ? 1 : 0));

            var hallC = gateC + vDir * hv0 + uDir * hallUc;
            var katte = f.Cells.Where(p => Vector2.Dot(p - hallC, vDir) > 0f).ToList();
            NiwaIdo(grp, f, katte, rnd, 1, want, got, log);
        }
        log.Add(string.Format("    地表: 参道 = {0}・本堂の前の白洲 {1:F1}×{2:F1}m({3:F0}m²)・棟の軒から 3m の叩き土 {4}点・林床は林の足もと",
                              temple ? "白洲" : "叩き土", maeW, maeD, maeArea, tsuchi.Count));
    }
}
