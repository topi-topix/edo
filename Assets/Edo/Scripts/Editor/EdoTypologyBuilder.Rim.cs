// 類型の崖の縁の石垣(Stage 4y・2026-09-28・EDO-0477 施主裁定A「石垣を積み、その上に塀」)。
//
// 区画の縁の外(背)が造成した平場より EdoBuild.RIM_MIN 以上高い区間を測り、塀の真下を平場まで削って野面の石垣を積む。
// 塀はその区間を石垣の天端に平らに載せる(buildKakoi が rims を読む)。⛔ 置く・測る・削る算術はここに書かない — EdoBuildRim.cs /
// EdoBuildNozura.cs の持ち場(規則21)。石垣の意匠は山王の野面の乱積み(施主が試作 A を採った型・unity-modular-stonewall)。
// 納まり: 石垣の**背(控えの奥)を区画の線に**揃える ⇒ 駒は区画の中に納まり、塀は線の上で天端の奥の端と背の土に跨って立つ。
// 当たる先: 類型の全区画の崖の縁(観理院の西の境が最初 ── 山王社の前庭 14.5 と本堂の平場 9.5 の間)。

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static partial class EdoTypologyBuilder
{
    /// <summary>塀の厚みの半分[m]。<see cref="Rim"/> が練塀の駒の実メッシュから測って入れる(既定は測る前の仮)。</summary>
    static float RIM_WALL_HALF = 0.21f;

    /// <summary>辺 <paramref name="e"/> の囲いを区画の角で頂点の先へ延ばす長さ(始点 <paramref name="atA"/>・終点 <paramref name="atB"/>)。
    /// 型は <see cref="EdoBuild.CornerReach"/>(区画の角の塀の口を閉じる・EDO-0477 P2 隅)。隣の辺が長屋でも延ばす(長屋の妻に隠れる)。</summary>
    static void CornerReaches(List<Edge> edges, Edge e, string kind, out float atA, out float atB)
    {
        atA = atB = 0f;
        float hOut, hIn; EdoBuild.FenceFaceOffsets(kind, out hOut, out hIn);
        if (hOut <= 0f && hIn <= 0f) return;
        var d = (e.b - e.a).normalized;
        var prev = edges.FirstOrDefault(x => x != e && (x.b - e.a).sqrMagnitude < 1e-4f);
        var next = edges.FirstOrDefault(x => x != e && (x.a - e.b).sqrMagnitude < 1e-4f);
        if (prev != null) atA = EdoBuild.CornerReach((prev.b - prev.a), d, prev.outward, hOut, hIn);
        if (next != null) atB = EdoBuild.CornerReach(d, (next.b - next.a), e.outward, hOut, hIn);
    }

    static string Rim(Spec s, Transform root, Vector2[] poly, List<Edge> edges, Edge front, List<Edge> machiyaFronts,
                      List<Vector2[]> pads, List<float> padY, List<EdoBuild.RimRun> rims, out EdoBuild.BedIndex bed)
    {
        var sb = new System.Text.StringBuilder();
        var ishi = Group("Ishigaki", root);
        for (int c = ishi.childCount - 1; c >= 0; c--) UnityEngine.Object.DestroyImmediate(ishi.GetChild(c).gameObject);
        rims.Clear(); bed = null;
        var use = edges.Select(e => e.mine && !machiyaFronts.Contains(e)
                                    && EnclosureFor(s, e, e == front) != "nagaya" && EnclosureFor(s, e, e == front) != "none").ToList();
        string rep;
        rims.AddRange(EdoBuild.RimRetainRuns(edges.Select(e => e.a).ToList(), edges.Select(e => e.b).ToList(),
                                             edges.Select(e => e.outward).ToList(), use, pads, padY, out rep));
        if (rims.Count == 0) return "  崖の縁の石垣: なし" + (rep.Length > 0 ? "\n" + rep.TrimEnd() : "");
        sb.AppendLine("  崖の縁の石垣: " + rims.Count + " 本");
        sb.Append(rep);

        // 焼いてある見付(4.80 は焼いてあれば足す)
        var heights = new List<float> { 0.30f, 0.60f, 0.90f, 1.20f, 1.50f, 1.80f, 2.10f, 2.40f };
        string projRoot = System.IO.Directory.GetParent(Application.dataPath).FullName;
        if (System.IO.File.Exists(System.IO.Path.Combine(projRoot, EdoAssets.Own.SannoNozura(4.8f, 0f, 0)))) heights.Add(4.80f);
        // ⭐ 天端の線 = 区画の線を、石垣の背(控えの奥)の深さだけ内へ寄せた線 ── 駒の実メッシュから測る(見え面 +Z・背は −Z)
        float needMax = rims.Max(r => r.crest - r.foot);
        float hPick = heights.FirstOrDefault(h => h >= needMax - 1e-3f); if (hPick <= 0f) hPick = heights[heights.Count - 1];
        if (needMax > heights[heights.Count - 1] + 1e-3f)
            sb.AppendLine(string.Format("    ⛔ 見付 {0:F2}m に届く駒が焼いていない(最高 {1:F2})── 石垣は天端から {1:F2} までしか石が無い", needMax, heights[heights.Count - 1]));
        float back = 0f;
        foreach (var v in EdoBuild.BodyAt(EdoAssets.Own.SannoNozura(hPick, 0f, 0), Vector3.zero, 0f, true)) back = Mathf.Max(back, -v.z);
        float off = back + 0.02f;
        // 塀の厚みの半分(練塀の駒の**足元の水平断面** ── 走りは X。座に当たるのは足元の下見板)
        //   ⛔ 全頂点の幅で採らない: 笠の瓦は壁体と一つのメッシュで屋根の名が付かず、屋根の総幅 1.00 を拾って 0.50 と出た。
        {
            float z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var v in EdoBuild.SectionAt(EdoAssets.Own.Dobei2m, Vector3.zero, 0f, 0.05f, false)) { z0 = Mathf.Min(z0, v.z); z1 = Mathf.Max(z1, v.z); }
            if (z1 > z0) RIM_WALL_HALF = (z1 - z0) * 0.5f;
        }
        sb.AppendLine(string.Format("    天端の線 = 区画の線を内へ {0:F2}m(駒 H{1:F2} の背の深さ {2:F2} + 0.02)・塀の厚みの半分 {3:F2}(実測)", off, hPick, back, RIM_WALL_HALF));

        Func<Vector2, Vector2, Vector2> inward = (p, q) =>
        {
            var d = (q - p).normalized; var n = new Vector2(-d.y, d.x);
            return EdoGeom.PIP(poly, (p + q) * 0.5f + n * 0.2f) ? n : -n;
        };
        // ⭐ 駒は区画の中に納める(区域侵犯は許容0)── 据えた駒の実メッシュが線の外へ出た量だけ天端の線を内へ寄せて据え直す
        //   (背の裏石の不揃い・折れの外の隅は背の深さだけでは読めない ── 観理院 1 巡目 最悪 0.23m・折れの所)。
        List<KeyValuePair<GameObject, Vector2>> got = null;
        for (int pass = 0; pass < 3; pass++)
        {
            for (int c = ishi.childCount - 1; c >= 0; c--) UnityEngine.Object.DestroyImmediate(ishi.GetChild(c).gameObject);
            var segs = new List<EdoBuild.NozuraSeg>();
            for (int ri = 0; ri < rims.Count; ri++)
            {
                var r = rims[ri];
                r.crestLine = EdoBuild.OffsetPolyline(r.line, off, inward);
                string cut = EdoBuild.CutBeforeRim(poly, r, back);
                if (pass == 0) sb.AppendLine("    " + cut);
                float crest = r.crest, foot = r.foot;
                for (int i = 0; i + 1 < r.crestLine.Count; i++)
                    segs.Add(new EdoBuild.NozuraSeg { name = "Rim" + ri + "_" + i, a = r.crestLine[i], b = r.crestLine[i + 1],
                                                      crestAt = _ => crest, footAt = (x, z) => foot });
            }
            var nz = new System.Text.StringBuilder();
            got = EdoBuild.PlaceNozuraNet(segs, EdoBuild.Ground, null, back + 0.3f, ishi,
                (h, g, i) => EdoAssets.Own.SannoNozura(h, g, i), (h, i) => EdoAssets.Own.SannoNozuraKado(h, i),
                (up, i) => EdoAssets.Own.SannoNozuraDan(up, i), (up, i) => EdoAssets.Own.SannoNozuraKiri(up, i),
                null, heights.ToArray(), new List<GameObject>(), nz);
            float worst = 0f;
            foreach (var kv in got)
                foreach (var v in EdoBuild.Body(kv.Key.transform, 999999))
                { var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(poly, q)) worst = Mathf.Max(worst, EdoGeom.DistToPolyEdge(poly, q)); }
            if (worst <= 0.005f || pass == 2)
            {
                foreach (var ln in nz.ToString().Split('\n')) if (ln.Trim().Length > 0) sb.AppendLine("  " + ln.TrimEnd());
                sb.AppendLine(string.Format("    駒が区画の線の外へ出る量 {0:F3}m(天端の線は区画の線から内へ {1:F2}m・{2} 巡目){3}", worst, off, pass + 1, worst > 0.005f ? " ⛔ 納まらない" : ""));
                break;
            }
            off += worst + 0.02f;
        }
        bed = new EdoBuild.BedIndex(got.Select(kv => kv.Key));
        sb.Append(string.Format("    石垣 {0} 駒・床の索引 {1} 面", got.Count, bed.Tris));
        return sb.ToString();
    }
}
