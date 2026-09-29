// 類型ビルダー — 揺らぎ(EDO-0476・施主裁定 2026-09-27)。
//
// ⭐ **何が狂っていたか**(施主 2026-09-27「すべての坊がほぼ同じ・類型のビルダーがしょぼ過ぎる」):
//    同じ型の区画は表の欄が同じで、ビルダーに乱数の揺らぎが無かった ── 十坊 10 筆が同じ駒・同じ並びで建った。
//    武家の小旗本 6 筆も同じ。町屋は種が列の名(Omotedana0)だけで、24 区画が同じ順で同じ組を引いていた。
//
// ⭐ 決まり(施主裁定):
//    ・種は**区画 id**(EdoBuild.Seed)── 同じ区画は何度建て直しても同じ姿(決定的)。
//    ・揺らぎの幅は**表に書く**(`docs/Sashizu/typology.json` の `defaults.yuragi`)。幅は確度 U。
//    ・⛔ 区画の欄に確度 S/A/B/P が付いた値は揺らさない(史料値が勝つ・規則7)。
// ⛔ このファイルに置き方の算術を書かない(規則21)。ここに書くのは「表のどの幅から何を選ぶか」だけ。
// ⛔ パスの literal を書かない(規則12)。駒の名 → パスは EdoAssets.VK の定数へ引く。

using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;

public static partial class EdoTypologyBuilder
{
    /// <summary>揺らいだ欄の覚書(区画 id → 「何を何から何へ」)。建てた log に刷る(規則19)。</summary>
    static readonly Dictionary<string, List<string>> _yuNote = new Dictionary<string, List<string>>();

    /// <summary>差し替える前の駒(区画 id#Plan の何棟目 → パス)。差し替えた駒が入らないとき元へ戻すため。</summary>
    static readonly Dictionary<string, string> _yuOrig = new Dictionary<string, string>();

    /// <summary>Plan の <paramref name="k"/> 棟目を揺らぎで差し替えたなら、元の駒のパス。差し替えていなければ null。</summary>
    static string YuOrig(Spec s, int k)
    {
        string o; return s != null && _yuOrig.TryGetValue(s.id + "#" + k, out o) ? o : null;
    }

    /// <summary>区画 id と用途から決まる乱数。⛔ 用途ごとに種を分ける ── 一つの乱数を使い回すと、
    /// 前段で引く回数が変わっただけで後段の姿が全部入れ替わる。</summary>
    static System.Random YuRng(string id, string what)
    {
        return new System.Random(EdoBuild.Seed((id ?? "") + ":yuragi:" + what));
    }

    /// <summary>[0,1) の決まった値(区画 id と鍵から)。</summary>
    static float YuUnit(string id, string key)
    {
        return (EdoBuild.Seed((id ?? "") + ":yuragi:" + key) % 100003) / 100003f;
    }

    /// <summary>表の `defaults.yuragi` の、この型に当たる塊。jisha は kind の塊。無ければ null(揺らさない)。</summary>
    static Dictionary<string, object> YuLeaf(string type, string kind)
    {
        if (_defs == null) return null;
        object yv; if (!_defs.TryGetValue("yuragi", out yv)) return null;
        var d = yv as Dictionary<string, object>; if (d == null) return null;
        object bv;
        switch (type)
        {
            case "buke":    d.TryGetValue("buke", out bv); return bv as Dictionary<string, object>;
            case "machiya": d.TryGetValue("machiya", out bv); return bv as Dictionary<string, object>;
            case "jisha":
                if (!d.TryGetValue("jisha", out bv)) return null;
                d = bv as Dictionary<string, object>; if (d == null) return null;
                switch (kind)
                {
                    case "bo":     d.TryGetValue("bo", out bv); break;
                    case "temple": d.TryGetValue("temple", out bv); break;
                    case "shake":  d.TryGetValue("shake", out bv); break;
                    default: return null;
                }
                return bv as Dictionary<string, object>;
        }
        return null;
    }

    static Dictionary<string, object> YuLeaf(Spec s) { return s == null ? null : YuLeaf(s.type, s.kind); }

    /// <summary>その欄が史料値か(確度 S/A/B/P)。⭐ 史料値は揺らさない。確度が書いていない欄は U 扱い(表の `_` の約束)。</summary>
    static bool YuFirm(Dictionary<string, object> row, string field)
    {
        object cv; if (!row.TryGetValue("cert", out cv)) return false;
        var c = cv as Dictionary<string, object>; if (c == null) return false;
        object v; if (!c.TryGetValue(field, out v) || v == null) return false;
        string k = v.ToString();
        return k == "S" || k == "A" || k == "B" || k == "P";
    }

    static float YuF(Dictionary<string, object> d, string k, float dflt)
    {
        object v; if (d == null || !d.TryGetValue(k, out v) || v == null) return dflt;
        double o; return double.TryParse(v.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out o) ? (float)o : dflt;
    }

    static List<object> YuL(Dictionary<string, object> d, string k)
    {
        object v; if (d == null || !d.TryGetValue(k, out v)) return null;
        return v as List<object>;
    }

    static void YuSay(string id, string what)
    {
        List<string> l; if (!_yuNote.TryGetValue(id, out l)) _yuNote[id] = l = new List<string>();
        if (!l.Contains(what)) l.Add(what);
    }

    /// <summary>建てた log に刷る一行(揺らいだ欄の一覧)。揺らぎが無ければ「揺らぎ無し」と刷る ── 黙らない(規則19)。</summary>
    static string YuNote(Spec s)
    {
        List<string> l;
        if (s == null || !_yuNote.TryGetValue(s.id, out l) || l.Count == 0)
            return "\n    揺らぎ(EDO-0476): 無し" + (YuLeaf(s) == null ? "(表の defaults.yuragi にこの型の幅が無い)" : "");
        return "\n    揺らぎ(EDO-0476・区画の種・幅は確度U): " + string.Join(" / ", l.ToArray());
    }

    // ───────────────────────── 表の欄(LoadTable の Fill の後)─────────────────────────

    /// <summary>**表の欄を揺らす。**LoadTable が既定を差した後に呼ぶ。今は坊の囲い(`enclosure`)だけ ──
    /// 囲いは Stage 2 が <c>s.enclosure</c> を読むので、Spec を起こす前に欄を差し替える。
    /// ⛔ 確度 S/A/B/P の欄は触らない。</summary>
    static void YuragiFields(string id, Dictionary<string, object> row)
    {
        _yuNote.Remove(id);
        string type = S(row, "type");
        var d = YuLeaf(type, S(row, "kind"));
        if (d == null) return;
        var enc = YuL(d, "enclosure");
        if (enc != null && enc.Count > 1 && !YuFirm(row, "enclosure"))
        {
            string cur = S(row, "enclosure");
            // ⭐ 表の値が幅の中に在るときだけ揺らす ── 幅の外の値は誰かが書き分けた物
            if (cur == null || enc.Any(e => e != null && e.ToString() == cur))
            {
                string pick = enc[YuRng(id, "enclosure").Next(enc.Count)].ToString();
                if (pick != cur) { row["enclosure"] = pick; YuSay(id, string.Format("囲い {0}→{1}", cur ?? "—", pick)); }
                else YuSay(id, "囲い " + pick + "(そのまま)");
            }
        }
    }

    // ───────────────────────── 武家(Plan / Omoya)─────────────────────────

    static string YuKomaName(string path)
    {
        if (path == EdoAssets.VK.BigHouse) return "BigHouse";
        if (path == EdoAssets.VK.House) return "House";
        if (path == EdoAssets.VK.HouseA) return "HouseA";
        if (path == EdoAssets.VK.HouseB) return "HouseB";
        if (path == EdoAssets.VK.SmallHouse) return "SmallHouse";
        if (path == EdoAssets.VK.Manor) return "Manor";
        return null;
    }

    static string YuKomaPath(string name)
    {
        switch (name)
        {
            case "BigHouse":   return EdoAssets.VK.BigHouse;
            case "House":      return EdoAssets.VK.House;
            case "HouseA":     return EdoAssets.VK.HouseA;
            case "HouseB":     return EdoAssets.VK.HouseB;
            case "SmallHouse": return EdoAssets.VK.SmallHouse;
            case "Manor":      return EdoAssets.VK.Manor;
        }
        return null;
    }

    /// <summary>**主屋級の駒を同じ格の駒へ差し替える**(表の `yuragi.buke.koma`)。<paramref name="k"/> は Plan の何棟目か。
    /// 付属(蔵・厩・小屋)と、表に幅の無い駒はそのまま返す。</summary>
    static string YuKoma(Spec s, string path, int k)
    {
        if (s == null || s.type != "buke") return path;
        string nm = YuKomaName(path); if (nm == null) return path;
        var d = YuLeaf(s);
        object kv; if (d == null || !d.TryGetValue("koma", out kv)) return path;
        var koma = kv as Dictionary<string, object>; if (koma == null) return path;
        object lv; if (!koma.TryGetValue(nm, out lv)) return path;
        var l = lv as List<object>; if (l == null || l.Count < 2) return path;
        string pick = l[YuRng(s.id, "koma" + k).Next(l.Count)].ToString();
        string p = YuKomaPath(pick) ?? path;
        _yuOrig[s.id + "#" + k] = path;
        YuSay(s.id, string.Format("{0}棟目 {1}→{2}", k + 1, nm, pick));
        return p;
    }

    /// <summary>付属の向きの足し[度](表の `yuragi.buke.fuzoku_yaw`)。主屋級の駒(VK の家)は門へ向けたまま 0。</summary>
    static float YuYaw(Spec s, string path, string label)
    {
        if (s == null || s.type != "buke" || YuKomaName(path) != null) return 0f;
        var d = YuLeaf(s);
        object yv; if (d == null || !d.TryGetValue("fuzoku_yaw", out yv)) return 0f;
        var l = yv as List<object>;
        if (l == null || l.Count == 0) return 0f;
        float y = YuF(new Dictionary<string, object> { { "v", l[YuRng(s.id, "yaw:" + label).Next(l.Count)] } }, "v", 0f);
        if (Mathf.Abs(y) > 0.5f) YuSay(s.id, string.Format("{0} を {1:0}° 振った", label, y));
        return y;
    }

    /// <summary>置き場の候補の点数に足す揺らぎ[m](表の `yuragi.buke.okiba_m`)── 点の座標から決まる(並べ替えの比較で毎回同じ値)。</summary>
    static float YuOkiba(Spec s, Vector2 p)
    {
        if (s == null || s.type != "buke") return 0f;
        var d = YuLeaf(s);
        object mv; if (d == null || !d.TryGetValue("okiba_m", out mv)) return 0f;
        float m = YuF(d, "okiba_m", 0f);
        if (m <= 0f) return 0f;
        return m * YuUnit(s.id, "okiba:" + Mathf.RoundToInt(p.x * 2f) + "," + Mathf.RoundToInt(p.y * 2f));
    }

    // ───────────────────────── 町屋(Machiya)─────────────────────────

    /// <summary>表店の組を引く種(表の `yuragi.machiya.tana_mix`)。true なら区画 id から・false なら列の名だけ(従来)。</summary>
    static int YuTanaSeed(Spec s, string prefix)
    {
        var d = YuLeaf(s);
        object tv; bool mix = d != null && d.TryGetValue("tana_mix", out tv) && tv != null && tv.ToString().ToLowerInvariant() == "true";
        if (mix) YuSay(s.id, "表店の組は区画の種で引いた");
        return EdoBuild.Seed((mix ? s.id + ":" : "") + prefix);
    }

    // ───────────────────────── 寺社(JishaOmoya)─────────────────────────

    /// <summary>附属の置き場の点数の揺らぎ[m](表の `yuragi.jisha.<kind>.okiba_m`・無ければ <paramref name="dflt"/>)。</summary>
    static float YuJishaOkiba(Spec s, float dflt) { return YuF(YuLeaf(s), "okiba_m", dflt); }

    /// <summary>本堂の帯の倍率 [下, 上](表の `hall_band`)。無ければ既定の 0.85〜1.25。</summary>
    static Vector2 YuHallBand(Spec s)
    {
        var l = YuL(YuLeaf(s), "hall_band");
        if (l == null || l.Count < 2) return new Vector2(0.85f, 1.25f);
        var d = new Dictionary<string, object> { { "a", l[0] }, { "b", l[1] } };
        return new Vector2(YuF(d, "a", 0.85f), YuF(d, "b", 1.25f));
    }

    /// <summary>坊の主屋の間数の幅(表の `main_hall_w` / `main_hall_d`)。幅が無ければ null。</summary>
    static int[] YuHallRange(Spec s)
    {
        var d = YuLeaf(s);
        var w = YuL(d, "main_hall_w"); var dd = YuL(d, "main_hall_d");
        if (w == null || w.Count < 2 || dd == null || dd.Count < 2) return null;
        var t = new Dictionary<string, object> { { "w0", w[0] }, { "w1", w[1] }, { "d0", dd[0] }, { "d1", dd[1] } };
        return new[] { (int)YuF(t, "w0", 0f), (int)YuF(t, "w1", 0f), (int)YuF(t, "d0", 0f), (int)YuF(t, "d1", 0f) };
    }

    /// <summary>庫裏の間数(表の `kuri` の候補から種で)。候補が無ければ null(従来の本堂の大きさで選ぶ)。</summary>
    static float[] YuKuri(Spec s)
    {
        var l = YuL(YuLeaf(s), "kuri");
        if (l == null || l.Count == 0) return null;
        var one = l[YuRng(s.id, "kuri").Next(l.Count)] as List<object>;
        if (one == null || one.Count < 2) return null;
        var t = new Dictionary<string, object> { { "w", one[0] }, { "d", one[1] } };
        return new[] { YuF(t, "w", 0f), YuF(t, "d", 0f) };
    }
}
