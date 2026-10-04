using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 植栽の置き方(算出物の撒いた点を一本ずつ据える)── EDO-0533 S8 で岡部の邸ビルダー(PlantFromImpl)から移した。
//   ⭐ 規則21: 置く・測る・据えるは EdoBuild の関数だけ。邸ビルダーは「どの点に何を」だけを持つ。
//   当たる先: 岡部 Stage5_Nishi(PlantFromImpl)・土井 Stage8_Shokusai。山王・松江松平の植栽は別の口(EdoBuildUeru・類型)。
public static partial class EdoBuild
{
    /// <summary>植栽の部材のキーを在庫のパスに解く。**キーは指図(算出物)が持ち、ここは辞書を引くだけ。**
    /// 書式は `族.名.寸法.個体`(例 `JG.Pine.Big.2` / `Own.Jouryoku.Mid.1`)か括弧の個体(`Own.TsuruFuji(1)`)。
    /// 寸法が `Small/Mid` の選択肢・個体が `1-3` の範囲なら `seedName` から決まる物を選ぶ(乱数ではない)。
    /// ⛔ **どの在庫の木がどの樹種を代表するかは在庫方の判断**で、ここで決めない。解けなければ null。</summary>
    public static string PlantPathByKey(string key, string seedName)
    {
        if (string.IsNullOrEmpty(key)) return null;
        // ⛔ **括弧を先に落とす。**つるは `Own.TsuruFuji(1)` の形で来るので、素朴に '.' で割ると
        //   名が「TsuruFuji(1)」になって辞書に当たらない(2026-09-04 に S3 が例外で落ちた型と同じ)。
        string head0 = key; int paren = -1;
        int lp0 = key.IndexOf('(');
        if (lp0 >= 0)
        {
            int rp0 = key.LastIndexOf(')');
            head0 = key.Substring(0, lp0);
            int.TryParse(key.Substring(lp0 + 1, Mathf.Max(0, (rp0 < 0 ? key.Length : rp0) - lp0 - 1)).Trim(), out paren);
        }
        var t = head0.Split('.');
        if (t.Length < 2) return null;
        string fam = t[0], nm = t[1];
        string size = t.Length > 2 ? t[2] : "Mid";
        // ⚠ 寸法は `Small/Mid` のように**選択肢**で来ることがある。⛔ そのままパスに入れない(2026-09-04 S5)
        if (size.IndexOf('/') >= 0)
        {
            var alt = size.Split('/');
            size = alt[PlantHash(seedName + "sz") % alt.Length];
        }
        // ⚠ 個体は `1` か `1-3`(範囲)。⛔ 1本の層を1個体で埋めない ── 範囲なら名前から決まる個体
        int idx = 1;
        if (t.Length > 3)
        {
            string it = t[3];
            int dash = it.IndexOf('-');
            if (dash > 0)
            {
                int lo2, hi2;
                if (int.TryParse(it.Substring(0, dash), out lo2) &&
                    int.TryParse(it.Substring(dash + 1), out hi2) && hi2 >= lo2)
                    idx = lo2 + (PlantHash(seedName) % (hi2 - lo2 + 1));
            }
            else int.TryParse(it, out idx);
        }
        if (paren > 0) idx = paren;          // 括弧の個体が最優先
        if (idx < 1) idx = 1;
        if (fam == "NM")
        {
            if (nm == "MapleBush")  return EdoAssets.NM.MapleBush(idx);
            if (nm == "GreyWillow") return EdoAssets.NM.GreyWillow(idx);
            // 草地の草叢(ススキ)。名は `GrassMeadow01`、寸法の欄が**変種**("detailed"/"cross")。
            if (nm.StartsWith("GrassMeadow"))
            {
                string fam2 = nm.Substring("GrassMeadow".Length);
                string variant = (size == "Mid") ? "" : size;     // 既定の "Mid" は無印扱い
                var ixs = EdoAssets.NM.GrassMeadowIndices(fam2, variant);
                if (ixs.Length == 0) return null;
                // ⛔ 連番と決めつけない — 実在する番号は EdoAssets が持つ(02 の無印は 1 が無い)
                int pick = (paren > 0 || (t.Length > 3)) && idx >= 1 && System.Array.IndexOf(ixs, idx) >= 0
                         ? idx : ixs[PlantHash(seedName + "g") % ixs.Length];
                return EdoAssets.NM.GrassMeadow(fam2, variant, pick);
            }
            return null;
        }
        if (fam == "JG")
        {
            if (nm == "Pine")    return EdoAssets.JG.Pine(size, idx);
            if (nm == "Bamboo")  return EdoAssets.JG.Bamboo(size, idx);   // ヤダケの代用(丈で縮める)
            if (nm == "Boxwood") return EdoAssets.JG.Boxwood(idx);
            if (nm == "Fern")    return EdoAssets.JG.Fern(idx);
        }
        else if (fam == "JC")
        {
            // 在庫の城パックの躑躅(`JC.Azalea01` / `Azalea03` / `Azalea04` ── 名の数字が型番・A 02 は無い)。松江松平の算出物が名指す(EDO-0554)
            if (nm.StartsWith("Azalea")) { int k; if (int.TryParse(nm.Substring(6), out k)) return EdoAssets.JG.Azalea(k); }
        }
        else if (fam == "Own")
        {
            if (nm == "Jouryoku") return EdoAssets.Own.Jouryoku(size, idx);
            if (nm == "Matsu")   return EdoAssets.Own.Matsu(size, idx);
            if (nm == "Teiboku") return EdoAssets.Own.Teiboku(size, idx);
            // ⚠ **同じ "Mid" でも樹種で樹高が違う**(エノキ13.5 / ムクノキ12 / ケヤキ14.5)── 寸法の呼びを樹種を跨いで揃えない
            if (nm == "Enoki")    return EdoAssets.Own.Enoki(size, idx);
            if (nm == "Mukunoki") return EdoAssets.Own.Mukunoki(size, idx);
            if (nm == "Keyaki")   return EdoAssets.Own.Keyaki(size, idx);
            // つる3種。⚠ 寸法の呼びを持たず**個体だけ**
            if (nm == "TsuruFuji")   return EdoAssets.Own.TsuruFuji(idx);
            if (nm == "TsuruTeika")  return EdoAssets.Own.TsuruTeika(idx);
            if (nm == "TsuruKizuta") return EdoAssets.Own.TsuruKizuta(idx);
            if (nm == "Momiji")   return EdoAssets.Own.Momiji(size, idx);
            if (nm == "Ume")      return EdoAssets.Own.Ume(size, idx);
        }
        return null;
    }

    /// <summary>名前から決まる安定した非負の整数。⛔ 乱数ではない(`string.GetHashCode` は .NET の版で変わるので使わない)。</summary>
    public static int PlantHash(string s2)
    {
        int h = 17;
        if (s2 != null) for (int i = 0; i < s2.Length; i++) h = unchecked(h * 31 + s2[i]);
        return h < 0 ? -h : h;
    }

    static readonly Dictionary<string, float> _plantNatH = new Dictionary<string, float>();
    /// <summary>部材の**素の丈**[m](据えた現物の外接の高さ)。丈を算出物の値へ合わせる倍率に使う。一度測って覚える。</summary>
    public static float PlantNaturalHeight(string path, Transform parent)
    {
        float h;
        if (_plantNatH.TryGetValue(path, out h)) return h;
        var probe = Place(path, new Vector3(0, -9999f, 0), 0f, Vector3.one, parent, "__probe");
        h = probe == null ? 0f : RB(probe).size.y;
        if (probe != null) Object.DestroyImmediate(probe);
        _plantNatH[path] = h;
        return h;
    }

    /// <summary>層の名 → 据えるときの沈め(<see cref="NiwaSet"/> の SinkLo ── 低木 0.03・中木/高木 0.15)。
    /// ⛔ 0 で据えない ── 根元の当たりが地表にちょうど載るだけで、格子ごとの最下点で測ると +0.025〜0.036 浮いた(岡部 第14巡)。</summary>
    public static float PlantSink(string layer)
    {
        return layer == "低木" ? NiwaSet.Shrub.SinkLo : layer == "中木" ? NiwaSet.Chuboku.SinkLo : NiwaSet.Tree.SinkLo;
    }

    /// <summary>**算出物の撒いた点に一本据える。**仮置き → 丈を `wantH` へ(一様の倍率・`wantH` ≤ 0.1 なら素の丈)→
    /// 傾け(`tiltDeg`・世界 xz の向き `tiltDirWorld`)→ 幹の足を点へ寄せ、足の当たりで描かれた地表へ据える(<see cref="SeatPlantAt"/>)。
    /// ⛔ 外接の底・ピボットで据えない。⛔ 丈を丸めない・上限を当て直さない(生成器が噛ませた後の値)。
    /// 戻りは置いた物。<paramref name="seated"/> は据えが許容(埋没 ≤ <paramref name="buryMax"/>・根元の浮き 0)に入ったか。
    /// ⭐⭐ **硬い条件(許容0)を破る木は建てない**(docs/oki-kata.md §4a ── 2026-10-05 EDO-0533)。据わらなければ消して null を返し
    /// <paramref name="refused"/> = true(部材が引けない null と分ける)。⛔ 2026-10-05 まで据わらない木も置いたまま「検査で数える」とし、
    /// 土井 西の谷の斜面_落葉0017(埋没 1.07)・南の崖_低木0019(1.30)が建っていた ── 斜面で根張りの帯の幅 × 勾配が上限を越える点。
    /// 当たる先: 算出物の植栽を据える全邸(土井 Stage8・岡部 PlantFromImpl・松江松平 Niwa の算出物)。</summary>
    public static GameObject PlantAtPoint(string path, Vector2 trunkXZ, float wantH, float tiltDeg, Vector2 tiltDirWorld,
                                          string layer, Transform parent, string name, DrawnGround drawn,
                                          out bool seated, out float bury, out float flt, out bool refused,
                                          float buryMax = 1.0f, float floatMax = 0.7f)
    {
        seated = false; refused = false; bury = flt = float.NaN;
        float y = Ground(trunkXZ.x, trunkXZ.y);              // 仮置き ── 据えは下の SeatPlantAt(幹の足の当たり)
        var go = Place(path, new Vector3(trunkXZ.x, y, trunkXZ.y), 0f, Vector3.one, parent, name);
        if (go == null) return null;
        float nat = PlantNaturalHeight(path, parent);
        if (wantH > 0.1f && nat > 0.1f) go.transform.localScale = Vector3.one * (wantH / nat);
        if (Mathf.Abs(tiltDeg) > 0.01f)
        {
            Vector2 w2 = tiltDirWorld.sqrMagnitude > 1e-12f ? tiltDirWorld.normalized : Vector2.up;
            go.transform.rotation = Quaternion.AngleAxis(tiltDeg, new Vector3(w2.y, 0f, -w2.x));
        }
        seated = SeatPlantAt(go, trunkXZ, PlantSink(layer ?? ""), out bury, out flt, buryMax, floatMax, drawn);
        if (!seated) { Object.DestroyImmediate(go); refused = true; return null; }
        return go;
    }

    /// <summary>旧の形(<paramref name="seated"/> だけ返す)。据わらない木は建てない(null)── 部材が引けない null と分けるなら refused を返す形を使う。</summary>
    public static GameObject PlantAtPoint(string path, Vector2 trunkXZ, float wantH, float tiltDeg, Vector2 tiltDirWorld,
                                          string layer, Transform parent, string name, DrawnGround drawn,
                                          out bool seated, out float bury, out float flt,
                                          float buryMax = 1.0f, float floatMax = 0.7f)
    {
        bool refused;
        return PlantAtPoint(path, trunkXZ, wantH, tiltDeg, tiltDirWorld, layer, parent, name, drawn, out seated, out bury, out flt, out refused, buryMax, floatMax);
    }

    /// <summary>据えた木の**幹径**[m]。根元の少し上(`y0`〜`y1` m)の帯で、幹の芯からの半径の非ゼロの 25 分位を 2 倍する。
    /// ⚠ 分布は二峰(幹の低い塊と葉・低い枝の高い塊)── 高い分位は葉を拾う(2026-09-04 クロマツ 13.7m: p30 0.414 が幹・p90 1.755 が葉)。
    /// ⛔ 既定値で埋めない — つるを絡めてよい木かどうかがこの値で決まる。測れなければ 0。</summary>
    public static float PlantTrunkDiameter(GameObject host, float y0, float y1)
    {
        var b = RB(host);
        float baseY = b.min.y;
        Vector2 axis = new Vector2(host.transform.position.x, host.transform.position.z);
        var rs = new List<float>();
        foreach (var mf in host.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var m = mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            for (int i = 0; i < vs.Length; i++)
            {
                var w = m.MultiplyPoint3x4(vs[i]);
                float dy = w.y - baseY;
                if (dy < y0 || dy > y1) continue;
                float r = (new Vector2(w.x, w.z) - axis).magnitude;
                if (r < 0.01f) continue;          // 軸上の退化点(枝の付け根・板ポリの芯)は数えない
                rs.Add(r);
            }
        }
        if (rs.Count == 0) return 0f;
        rs.Sort();
        return 2f * rs[Mathf.Clamp(Mathf.RoundToInt(rs.Count * 0.25f) - 1, 0, rs.Count - 1)];
    }
}
