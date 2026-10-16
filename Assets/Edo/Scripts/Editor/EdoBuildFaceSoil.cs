// EdoBuild — 見え面・溝の床の上に出た土を真上から数える(2026-10-16・EDO-0502 第147巡・施主の写真 r146_kado_P15
//   「台の石の前に地面の土が三角の歯の形で連続」・r146_kado_P40「隣の棟の足元に土の楔」)。⛔ 測るだけ ── 直さない
//   (直しは地面を書く側: SinkGroundUnderParts の天端の縁・SinkGroundUnderMizo の底の裏の無い駒)。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>**見え面の上の土・溝の中の土を真上から数える**(第147巡)。
    /// 駒ごとに外接の箱の中を <paramref name="step"/> の格子で真上から光線を打ち、最初に当たる駒の面を読む(他の駒の下の点は数えない)。
    /// <para>石垣・土留め(<paramref name="walls"/>):当たった面が見え面(法線の水平の成分 ≥ 0.25・上を向く)で、そこの描かれた地表(<see cref="Ground"/>)が面より 0.02 を超えて高い
    /// かつ面に沿う両脇 0.3 の地表のどちらよりも 0.05 を超えて高い(土の線が尖る ── 根入れ・坂は数えない)⇒ 「見え面の土」(天端の縁の歯・盛りの楔)。野面の光線の検め(<see cref="NozuraSeamReport"/>)は野面の駒の前向きでしか見ず、
    /// 城の石垣の台(局所 −X が見え面)と前の地表 +0.3 より下の歯を数えていなかった。</para>
    /// <para>溝・桝(<paramref name="mizos"/>):当たった面が上を向き(法線 y ≥ 0.9)駒の天端より 0.08 以上低い(溝の床)所で、地表が床より 0.02 を超えて高い ⇒ 「溝の中の土」。</para>
    /// 【硬】どちらも 0(許容 0 の被り)。⟶ 返す: 一行の要約(件数・最悪・駒の上位)。<paramref name="tsv"/> を渡せば明細を書く。
    /// 当たる先: 石垣・土留め・溝を細かい地形の上に据える邸すべて(岡部 GroundQA ── 土井・松江松平を細かい地形へ移すとき)。</summary>
    /// <summary>見え面の点 (x, z) の「前の地表」── 面の法線の水平の向き <paramref name="fo"/> へ 0.05 刻みで、真上に駒 <paramref name="g"/> が無くなる所 +0.15 の地表
    /// (そこの真上に別の駒〔<paramref name="owner"/> の内〕が在れば、その最初に当たる面の高い方)。4m 歩いても駒の下なら NaN。当たる先: <see cref="SoilOverFacesReport"/>(根入れを数えない)。</summary>
    static float FrontGroundOf(float x, float z, Vector2 fo, GameObject g, Dictionary<Collider, GameObject> owner)
    {
        for (float d = 0.05f; d <= 4f; d += 0.05f)
        {
            float qx = x + fo.x * d, qz = z + fo.y * d; bool mine = false;
            foreach (var hh in Physics.RaycastAll(new Vector3(qx, 400f, qz), Vector3.down, 800f)) { GameObject o; if (owner.TryGetValue(hh.collider, out o) && o == g) { mine = true; break; } }
            if (mine) continue;
            float ex = d + 0.15f, fx = x + fo.x * ex, fz = z + fo.y * ex; float gy = Ground(fx, fz);
            foreach (var hh in Physics.RaycastAll(new Vector3(fx, 400f, fz), Vector3.down, 800f)) if (owner.ContainsKey(hh.collider) && !(hh.collider is TerrainCollider) && (float.IsNaN(gy) || hh.point.y > gy)) gy = hh.point.y;
            return gy;
        }
        return float.NaN;
    }
    public static string SoilOverFacesReport(IList<GameObject> walls, IList<GameObject> mizos, float step = 0.10f, string tsv = null)
    {
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        var tmp = new List<MeshCollider>(); var kind = new Dictionary<Collider, int>(); var owner = new Dictionary<Collider, GameObject>();
        var all = new List<KeyValuePair<GameObject, int>>();
        Action<IList<GameObject>, int> add = (gs, k) =>
        {
            if (gs == null) return;
            foreach (var g in gs)
            {
                if (g == null || !g.activeInHierarchy) continue; bool any = false;
                if (k == 0 && g.name.Contains("_Tooshi")) continue;   // 奥を通す埋めた駒(const.abutOrder「土に埋め・根入れと同じ扱い」)は見え面を持たない
                foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
                {
                    if (mf.sharedMesh == null) continue; var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
                    var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; tmp.Add(mc); kind[mc] = k; owner[mc] = g; any = true;
                }
                if (any) all.Add(new KeyValuePair<GameObject, int>(g, k));
            }
        };
        add(walls, 0); add(mizos, 1);
        int nFace = 0, nMizo = 0, nEmbed = 0, nCrest = 0; float wFace = 0f, wMizo = 0f; Vector3 atFace = Vector3.zero, atMizo = Vector3.zero;
        var byPiece = new Dictionary<string, int>(); var sbT = tsv != null ? new System.Text.StringBuilder() : null;
        try
        {
            Physics.SyncTransforms();
            foreach (var kv in all)
            {
                var g = kv.Key; var bb = RB(g); float top = bb.max.y;
                for (float x = bb.min.x + 0.5f * step; x < bb.max.x; x += step)
                    for (float z = bb.min.z + 0.5f * step; z < bb.max.z; z += step)
                    {
                        var hs = Physics.RaycastAll(new Vector3(x, top + 1f, z), Vector3.down, bb.size.y + 2f);
                        if (hs.Length == 0) continue;
                        Array.Sort(hs, (a, b) => a.distance.CompareTo(b.distance));
                        RaycastHit h = default(RaycastHit); bool got = false;
                        foreach (var hh in hs) { if (hh.collider is TerrainCollider) continue; if (!kind.ContainsKey(hh.collider)) continue; h = hh; got = true; break; }
                        if (!got || owner[h.collider] != g) continue;   // 他の駒の下(上の駒が覆う)・自分に当たらない点は数えない
                        float gy = Ground(x, z); if (float.IsNaN(gy)) continue;
                        float dep = gy - h.point.y; if (dep <= 0.02f) continue;
                        float nh = new Vector2(h.normal.x, h.normal.z).magnitude;
                        if (kv.Value == 0)
                        {
                            if (nh < 0.25f || h.normal.y <= 0f) continue;   // 見え面(法の面)だけ ── 天端の上の土は別の作法(裏石の帯の土)
                            //   根入れ(地表の下に埋まる見え面の足)・面に沿う坂は数えない ── 面の点の地表が、面に沿う向き(法線の水平に直角)の両脇 0.3 の地表の
                            //   どちらよりも 0.05 を超えて高い所(土の線が尖る = 歯・楔)だけ
                            var fo = new Vector2(h.normal.x, h.normal.z) / nh; var tl = new Vector2(-fo.y, fo.x);
                            float gL = Ground(x + tl.x * 0.3f, z + tl.y * 0.3f), gR = Ground(x - tl.x * 0.3f, z - tl.y * 0.3f);
                            if (float.IsNaN(gL) || float.IsNaN(gR) || gy - Mathf.Max(gL, gR) <= 0.05f) continue;
                            //   ⭐ 第148巡: 根入れ(見え面の足が前の地表の下に埋まる所)を数えない ── 面の点の地表が「見え面の前の地表」(面の法線の水平の向きへ、真上に
                            //   この駒が無くなる所 +0.15 の地表・その上に別の石垣の駒が在ればその天端の高い方)より 0.05 を超えて高い所だけ(第147巡の 1891 のうち 939 は前の地表以下 ── 根入れ)。
                            //   天端の帯(駒の天端 −0.15 より上の面で地表が天端 +0.02 以下)の土は裏石の帯の土(別の作法)なので数えない
                            if (h.point.y >= top - 0.15f && gy <= top + 0.02f) { nCrest++; continue; }
                            float fr = FrontGroundOf(x, z, fo, g, owner); if (!float.IsNaN(fr) && gy <= fr + 0.05f) { nEmbed++; continue; }
                            nFace++; if (dep > wFace) { wFace = dep; atFace = h.point; }
                        }
                        else
                        {
                            if (h.normal.y < 0.9f || h.point.y > top - 0.08f) continue;   // 溝の床だけ(縁石の天端・板の上面は数えない)
                            nMizo++; if (dep > wMizo) { wMizo = dep; atMizo = h.point; }
                        }
                        int c0; byPiece.TryGetValue(g.name, out c0); byPiece[g.name] = c0 + 1;
                        if (sbT != null) sbT.AppendLine((kv.Value == 0 ? "F" : "M") + "\t" + g.name + "\t" + x.ToString("F2", ci) + "\t" + z.ToString("F2", ci) + "\t" + h.point.y.ToString("F3", ci) + "\t" + dep.ToString("F3", ci));
                    }
            }
        }
        finally { foreach (var mc in tmp) if (mc != null) UnityEngine.Object.DestroyImmediate(mc); }
        if (sbT != null) System.IO.File.WriteAllText(tsv, sbT.ToString());
        var pcs = new List<KeyValuePair<string, int>>(byPiece); pcs.Sort((a, b) => b.Value.CompareTo(a.Value));
        var sb = new System.Text.StringBuilder("見え面・溝の床の上の土(真上から " + step.ToString("0.00", ci) + " 格子・【硬】0): 見え面の土 " + nFace
            + (nFace > 0 ? "(最悪 " + wFace.ToString("F2", ci) + " @(" + atFace.x.ToString("F1", ci) + "," + atFace.z.ToString("F1", ci) + "))" : "")
            + " / 溝の中の土 " + nMizo + (nMizo > 0 ? "(最悪 " + wMizo.ToString("F2", ci) + " @(" + atMizo.x.ToString("F1", ci) + "," + atMizo.z.ToString("F1", ci) + "))" : "")
            + ((nFace + nMizo) == 0 ? " ⭕" : " ⛔") + "(数えない: 前の地表以下の根入れ " + nEmbed + "・天端の帯の土 " + nCrest + ")");
        for (int i = 0; i < Mathf.Min(8, pcs.Count); i++) sb.Append((i == 0 ? "\n    " : "・") + pcs[i].Key + " " + pcs[i].Value);
        return sb.ToString();
    }
}
