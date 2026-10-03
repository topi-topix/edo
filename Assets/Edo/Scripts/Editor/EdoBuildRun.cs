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

    /// <summary>**切土の法の法肩までの水平距離**(2026-09-26・EDO-0437)。法尻 <paramref name="toe"/>(面の縁・面の高さ <paramref name="floorY"/>)から
    /// 面の外 <paramref name="outward"/> へ、法 1:<paramref name="batter"/>(水平/鉛直)の面 floorY + t/batter が**造成前の地山**
    /// <paramref name="natural"/>(x,z)(正典は base_dem・規則13)に届く最初の t を <paramref name="step"/> 刻みで取り、刻みの中を一次で詰める。
    /// 法尻で地山が面以下なら 0(法が無い)。<paramref name="maxDist"/> までに届かなければ NaN。
    /// ⭐ 描かれた地形(2m 格子)では幅 0.5m 級の法の折れは読めない ── 設計面を焼く design_y と同じ交わり(法の面 × 地山)で測る。
    /// ⛔ 紙の座標(json の a・b)で塀を置かない。
    /// 当たる先: 切土の法の上(背の側)に建てる柵・板塀の走り(山王 前庭の南の板塀 `Ita_ZSE`)。法の上に据える物すべて。</summary>
    public static float CutShoulder(Vector2 toe, Vector2 outward, float floorY, float batter, Func<float, float, float> natural,
                                    float maxDist = 8f, float step = 0.02f)
    {
        Vector2 n = outward.normalized; float k = batter <= 1e-4f ? 1e4f : 1f / batter;
        float g0 = natural(toe.x, toe.y); if (float.IsNaN(g0)) return float.NaN;
        float prev = g0 - floorY; if (prev <= 0f) return 0f;   // 地山 − 法の面(正 = まだ法の下)
        for (float t = step; t <= maxDist + 1e-4f; t += step)
        {
            Vector2 q = toe + n * t; float g = natural(q.x, q.y); if (float.IsNaN(g)) return float.NaN;
            float cur = g - (floorY + t * k);
            if (cur <= 0f) return t - step + step * prev / Mathf.Max(1e-6f, prev - cur);
            prev = cur;
        }
        return float.NaN;
    }

    /// <summary>**法肩の線が下り始める所**(2026-09-26・EDO-0437 第6巡)。法尻の線上の点 <paramref name="toe0"/> から走り <paramref name="along"/> へ
    /// 0.05m 刻みで進み、各点で <see cref="CutShoulder"/> の法肩の高さ(法の面 floorY + t/batter)を測って、それまでの最高から
    /// <paramref name="eps"/> を超えて落ちた最初の点の一つ手前までの距離を返す(<paramref name="maxD"/> まで落ちなければ maxD)。
    /// 法が無い(地山が面以下)点は法肩 = 面の高さ(= 落ちた)と読む。<paramref name="profile"/> に 0.25m ごとの法肩の高さを返す。
    /// ⭐ 塀の端を「法肩が相手(袖・土留め)へ向けて下り始める所」で止めるための物差し ── ⛔ 紙の点や相手の面からの一定の離れで打ち切らない。
    /// 当たる先: 切土の法肩の上に建てる板塀・柵の端(山王 前庭の南の板塀 `Ita_ZSE` の西の端)。法の上に据える run の端すべて。</summary>
    public static float ShoulderLevelEnd(Vector2 toe0, Vector2 along, Vector2 outward, float floorY, float batter, Func<float, float, float> natural,
                                         float maxD, float eps, System.Text.StringBuilder profile = null, Func<float, float, float> drawn = null)
    {
        // ⭐ <paramref name="drawn"/>(描かれた地表)を渡すと、法肩の点の高さは地山の法肩と描かれた地表の低い方 ── 造成(石段の口の切り下げ)は
        //   造成前の地山 base_dem に載っていないので、地山だけでは袖へ向けて下る法肩が読めない(第6巡の実測: 地山の法肩は 17.04→17.01 で平ら)
        Vector2 d = along.normalized; float k = batter <= 1e-4f ? 1e4f : 1f / batter;
        float best = float.NegativeInfinity, last = 0f;
        for (float s = 0f; s <= maxD + 1e-4f; s += 0.05f)
        {
            float t = CutShoulder(toe0 + d * s, outward, floorY, batter, natural);
            float hs = float.IsNaN(t) ? float.NaN : floorY + t * k;
            if (!float.IsNaN(hs) && drawn != null) { Vector2 q = toe0 + d * s + outward.normalized * t; float dy = drawn(q.x, q.y); if (!float.IsNaN(dy)) hs = Mathf.Min(hs, dy); }
            if (profile != null && Mathf.Abs(s / 0.25f - Mathf.Round(s / 0.25f)) < 1e-3f)
                profile.Append(s.ToString("F2") + ":" + (float.IsNaN(hs) ? "NaN" : hs.ToString("F2")) + " ");
            if (float.IsNaN(hs)) return last;
            if (hs < best - eps) return last;
            best = Mathf.Max(best, hs); last = s;
        }
        return maxD;
    }

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
    /// <summary>長屋の鎖を門の開口の縁から門へ差し込む量[m](隙間 &gt; めり込み・EDO-0468)。【U】門の柱と長屋の妻の厚みの内。</summary>
    const float NAGAYA_GATE_TUCK = 0.25f;

    /// <summary>長屋の鎖の端から隅まで、隣の塀を折って回す足(EDO-0500)。corner = 区画の隅・chainEnd = 鎖の端(どちらも辺の線の上)・
    /// inset = 長屋の外面が線から内へ入る量[m]・outward = 長屋の辺の外向き。</summary>
    public class NagayaLeg { public Vector2 corner, chainEnd, outward; public float inset; }

    /// <summary>長屋どうしの出隅に据える隅長屋(EDO-0500 2026-10-01 施主指摘「角用の長屋にしないと屋根が変な重なり・窓が途中で途切れる」)。
    /// key = 区画の隅(二辺の共有点)/ face = 二辺の長屋の外面の線の交点(隅長屋のピボット)/ psi = 隅を高い s 端に持つ辺の外向き方位
    /// (= 隅長屋の +X の腕の辺)/ armX・armZ = その辺・隣の辺の腕の外面の長さ。二辺の NagayaRun がそれぞれ自分の腕を書き、
    /// 据えるのは <see cref="NagayaKadoPlace"/>。</summary>
    public class NagayaKado
    {
        public Vector2 key, face; public float psi = float.NaN, armX = -1f, armZ = -1f, baseY, deg = 90f;
        public bool tsumaX, tsumaZ;                                     // 腕の先が在庫の棟に継がない(門・塀の折れへ当たる)⇒ 妻で閉じる
        public GameObject nbrX, nbrZ;                                   // 腕の先に継ぐ在庫の棟(+X の腕・−Z の腕)
    }
    /// <summary>隅長屋の腕の下限[m](部材方の実測 4.79 ── 2 つ目の窓の先までは詰めない)。</summary>
    public const float NAGAYA_KADO_ARM_MIN = 4.80f;

    static NagayaKado KadoAt(List<NagayaKado> ks, Vector2 key)
    {
        var k = ks.FirstOrDefault(x => (x.key - key).sqrMagnitude < 1e-4f);
        if (k == null) { k = new NagayaKado { key = key }; ks.Add(k); }
        return k;
    }

    /// <summary>二辺の腕が揃った隅に隅長屋(<see cref="EdoAssets.Own.NagayaKado90"/>)を据える。position = 外面の交点 / yaw = +X の腕の辺の外向き。
    /// 足元は鎖の駒と同じく触れている所で据えて根入れする(規則21)。焼いていない腕の組は据えずに焼く手を返す。</summary>
    public static List<string> NagayaKadoPlace(Transform parent, List<NagayaKado> ks, string prefix)
    {
        var notes = new List<string>(); int i = 0;
        foreach (var k in ks)
        {
            if (float.IsNaN(k.psi) || k.armX < 0f || k.armZ < 0f) { notes.Add(string.Format("隅({0:F1},{1:F1}) ⚠ 片方の腕しか無い ── 隅長屋を据えない", k.key.x, k.key.y)); continue; }
            // 腕は cm へ切り上げ(+0.5cm)── 腕の先を在庫の棟へ 0.5〜1.5cm 差して、丸めで隙を開けない(r7 で 7.5mm 開いた・隙は許容0)
            float aZ = Mathf.Ceil(k.armZ * 100f + 0.5f) / 100f, aX = Mathf.Ceil(k.armX * 100f + 0.5f) / 100f;
            Func<bool, bool, string> tsumaOf = (z, x) => (z ? "Z" : "") + (x ? "X" : "");
            Func<string, string> bakeCmd = t => string.Format("blender --background --python Tools/Blender/build_nagaya_kado.py -- --deg {0:F1} --arms {1:F2},{2:F2}{3} --render",
                k.deg, aZ, aX, t.Length > 0 ? " --tsuma " + (t == "ZX" ? "both" : t == "Z" ? "negZ" : "posX") : "");
            string tsuma = tsumaOf(k.tsumaZ, k.tsumaX);
            string path = EdoAssets.Own.NagayaKado(k.deg, aZ, aX, tsuma);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            {
                notes.Add(string.Format("隅({0:F1},{1:F1}) ⛔ 隅長屋が焼いてない: {2}", k.key.x, k.key.y, bakeCmd(tsuma)));
                continue;
            }
            Func<string, GameObject> placeSeat = p =>
            {
                var g = Place(p, new Vector3(k.face.x, k.baseY, k.face.y), k.psi, Vector3.one, parent, prefix + "_kado" + i);
                if (NaturalMode)
                {
                    try { SeatOnGround(g, 0.10f, 600); } catch (System.Exception) { SeatBottom(g, k.baseY - 0.10f); }
                    var rt = RootToBed(g, Ground, 0.25f);
                    if (!float.IsNaN(rt.hi) && rt.hi > 0f) g.transform.position -= Vector3.up * rt.hi;
                }
                else SeatBottom(g, k.baseY - 0.10f);
                return g;
            };
            var go = placeSeat(path);
            // ⭐ 坂の長屋は棟を段違いにして段を妻で閉じる(r8・EDO-0500 ── 低い方へ揃えると門の側で下段の窓が 0.30m 土に切られ、
            //    門の屋根が隅長屋の上に出た。揃えずに別々に据えると 0.80m の段で切り口が覗いた)。
            //    ⛔ ピボットで比べない(規則21)── 実メッシュの下端で段を測る。段が SEAT_STEP 以下なら低い方へ揃えて埋める。
            const float SEAT_STEP = 0.10f;
            float yb = RB(go).min.y;
            bool stepX = k.nbrX != null && Mathf.Abs(RB(k.nbrX).min.y - yb) > SEAT_STEP;
            bool stepZ = k.nbrZ != null && Mathf.Abs(RB(k.nbrZ).min.y - yb) > SEAT_STEP;
            string t2 = tsumaOf(k.tsumaZ || stepZ, k.tsumaX || stepX);
            if (t2 != tsuma)
            {
                string p2 = EdoAssets.Own.NagayaKado(k.deg, aZ, aX, t2);
                if (AssetDatabase.LoadAssetAtPath<GameObject>(p2) == null)
                    notes.Add(string.Format("隅({0:F1},{1:F1}) ⛔ 段の妻の版が焼いてない(段で切り口が覗く): {2}", k.key.x, k.key.y, bakeCmd(t2)));
                else { UnityEngine.Object.DestroyImmediate(go); go = placeSeat(p2); tsuma = t2; yb = RB(go).min.y; }
            }
            i++;
            string howX = "", howZ = "";
            foreach (var nb in new[] { k.nbrX, k.nbrZ })
            {
                if (nb == null) continue;
                float d = RB(nb).min.y - yb;
                string how;
                if (Mathf.Abs(d) <= SEAT_STEP)
                {
                    float lo = Mathf.Min(yb, RB(nb).min.y);
                    nb.transform.position += Vector3.up * (lo - RB(nb).min.y);
                    go.transform.position += Vector3.up * (lo - RB(go).min.y); yb = lo;
                    how = string.Format("土台を {0:F2} に揃えた", lo);
                }
                else how = string.Format("段 {0:+0.00;-0.00}m を妻で閉じた", d);
                if (nb == k.nbrX) howX = how; else howZ = how;
            }
            notes.Add(string.Format("隅({0:F1},{1:F1}) 隅長屋 内角 {4:F1}°・腕 {2:F2}×{3:F2}m{5} を外面の交点へ据えた(土台の下端 {6:F2})・北/−Z の継ぎ {7}・+X の継ぎ {8}",
                                    k.key.x, k.key.y, aZ, aX, k.deg, tsuma.Length > 0 ? "・妻 " + tsuma : "", yb,
                                    howZ.Length > 0 ? howZ : "なし", howX.Length > 0 ? howX : "なし"));
        }
        return notes;
    }

    public static List<GameObject> NagayaRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, float baseY,
        Vector2 gapC, float gapHalf, string prefix, Vector2[] keepInside = null, float gateTuck = NAGAYA_GATE_TUCK,
        bool closeA = false, bool closeB = false, List<NagayaLeg> legs = null, bool nagA = false, bool nagB = false,
        List<NagayaKado> kados = null, Vector2 nOutA = default(Vector2), Vector2 nOutB = default(Vector2))
    {
        // ⭐ kados = 隣が長屋の隅に隅長屋を据える(EDO-0500 2026-10-01)。その端は妻を置かず、鎖の端数を隅長屋の腕で吸う
        //    (腕 ≥ NAGAYA_KADO_ARM_MIN)。妻を相手の胴へ突っ込む旧作法は屋根が重なり窓が途中で切れた(施主指摘)。
        // ⭐ nagA / nagB = 端 A / B の隅の隣が**長屋**。鎖も埋めの塀も、隣の長屋の外面の線(この辺と同じ入り)より隅の側へ出さない
        //    ── 二本の長屋の外面が隅の一点で出会う L に納める(2026-10-01 観理院 北東 EDO-0500 ── 東の長屋の北の妻が
        //    北の長屋の面より 1.6m 北へ飛び出し、北の長屋の埋めの低い塀が東の長屋の面から 3.6m 突き出ていた・施主指摘)。
        // ⭐ closeA / closeB = 端 A / B の隅で隣の辺が**塀**(長屋でない・囲わないでない)。そこの端数は長屋の側で埋めず、
        //    `legs` へ「隅の点・鎖の端・長屋の外面の入り」を返す ── 隣の塀を長屋の外面の線で折り、鎖の端まで**同じ塀**で回す
        //    (呼び手が塀の鎖に足を足す)。2026-10-01 観理院 EDO-0500 ── 中央寄せの端数は隣も長屋のときだけ重なって閉じ、
        //    隣が練塀だと南東に 1.02m の素通し。低い板塀で埋めると練塀と丈が合わず、練塀の端が長屋の面より 1.5m 出た(施主指摘)。
        // ⭐ gateTuck = 門の脇で鎖を門へ差す量。類型ビルダーは長屋の駒の札から渡す(EdoBuild.FenceBite・EDO-0491)。既定は従来の 0.25。
        bool followGround = NaturalMode; // 自然地形モードでは各ピースを地面に追従
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg; // 表+Zを外へ
        // run 方向はローカル -X: right=(cosψ,-sinψ) → -right=(-cosψ, sinψ)
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        Vector2 sA = A; Vector2 rdir = dir;
        bool closeLo = closeA, closeHi = closeB;       // 走りの s=0 / s=len の端
        bool nagLo = nagA, nagHi = nagB;
        Vector2 nOutLo = nOutA, nOutHi = nOutB;                            // 隣の辺の外向き(隅の内角を出す)
        if (Vector2.Dot(dir, negRight) < 0) { sA = B; rdir = -dir; closeLo = closeB; closeHi = closeA; nagLo = nagB; nagHi = nagA; nOutLo = nOutB; nOutHi = nOutA; }
        var ouN = outward.normalized;
        // 隅の外面の交点までの走り = 入り / tan(φ/2)(φ = 二辺の外向きのなす角。直角で入りと同じ ── 90.9° の隅で 0.026m 違う)
        Func<Vector2, float> cornerK = no => no.sqrMagnitude < 1e-6f ? 1f
            : 1f / Mathf.Tan(0.5f * Mathf.Acos(Mathf.Clamp(Vector2.Dot(ouN, no.normalized), -1f, 1f)));
        // 開口で区間を割る(壁の実面を開口の縁で止める。旧実装の±3.9m逃げは廃止=門の開口幅を保つ)
        var segs = new List<float[]>();
        if (gapHalf > 0)
        {
            float gT = Vector2.Dot(gapC - sA, rdir);
            if (gT - gapHalf > 0f) segs.Add(new float[] { 0f, Mathf.Min(gT - gapHalf, len) });
            if (gT + gapHalf < len) segs.Add(new float[] { Mathf.Max(gT + gapHalf, 0f), len });
        }
        else segs.Add(new float[] { 0f, len });
        // 隣が長屋の隅は、外面の入り(駒を一つ線の上に仮置きして実メッシュの足元の帯で測る)だけ区間を詰める
        float lim0 = 0f, lim1 = len, nagDepth = 0f, insV = 0f;   // nagDepth = 長屋の壁の奥行(隣の長屋の胴が隅の端数を覆う長さ)
        if ((nagLo || nagHi) && segs.Count > 0)
        {
            var pm = sA + rdir * (len * 0.5f);
            var probe = Place(PKnagayaC, new Vector3(pm.x, baseY, pm.y), psi, new Vector3(ES, ES, ES), parent, prefix + "_probe");
            VerifyFlipOutward(new List<GameObject> { probe }, outward, prefix);
            float pMn, pMx; float py0 = RB(probe).min.y; var pou = outward.normalized;
            ProjExtent(probe, pou, py0 - 0.01f, py0 + 1.0f,
                       nm => { var l = nm.ToLower(); return l.Contains("wall") || l.Contains("namako") || l.Contains("dodai"); }, out pMn, out pMx);
            UnityEngine.Object.DestroyImmediate(probe);
            float ins = pMx > float.MinValue ? Mathf.Max(0f, Vector2.Dot(sA, pou) - pMx) : 0f;
            nagDepth = pMx > float.MinValue ? pMx - pMn : 0f; insV = ins;
            if (nagLo) lim0 = ins * cornerK(nOutLo);
            if (nagHi) lim1 = len - ins * cornerK(nOutHi);
            segs = segs.Select(q => new[] { Mathf.Max(q[0], lim0), Mathf.Min(q[1], lim1) }).Where(q => q[1] > q[0]).ToList();
        }
        var mc = NagayaMeasure(PKnagayaC);
        var ml = NagayaMeasure(PKnagayaL);
        var mr = NagayaMeasure(PKnagayaR);
        float Wc = mc.W;                               // 実測 8.065m
        int idx = 0;                                   // 命名は run 通しの prefix_k(従来互換)
        int fill = 0;
        var fillRuns = new List<List<GameObject>>();   // 門の脇の端数を埋めた塀(鎖を建ててから外面を長屋の外面へ合わせる)
        var legS = new List<float[]>();                // 塀で回す足 [隅の s, 鎖の端の s](EDO-0500)
        var lone = new List<GameObject>();             // 孤立1棟(妻の無い c)── 両端妻へ差し替える(EDO-0500)
        foreach (var seg in segs)
        {
            float L = seg[1] - seg[0];
            bool gEnd0 = gapHalf > 0 && seg == segs[0] && segs.Count > 1 || gapHalf > 0 && segs.Count == 1 && seg[1] < lim1 - 0.01f;
            bool gStart0 = gapHalf > 0 && seg == segs[segs.Count - 1] && seg[0] > lim0 + 0.01f;
            bool kLo = kados != null && nagLo && seg[0] < lim0 + 0.01f;
            bool kHi = kados != null && nagHi && seg[1] > lim1 - 0.01f;
            if (kLo || kHi)
            {
                float tk = (gEnd0 || gStart0) ? gateTuck : 0f;
                float Lk = L + tk;
                int nk = (kLo ? 1 : 0) + (kHi ? 1 : 0);
                if (Lk >= nk * NAGAYA_KADO_ARM_MIN)
                {
                    int nn = Mathf.Max(0, Mathf.FloorToInt((Lk - nk * NAGAYA_KADO_ARM_MIN) / Wc));
                    // 隅長屋の側の端は妻の無い c、反対の端(門・塀の折れ)は従来どおり妻
                    Func<int, int, string> pathK = (k, nT) =>
                        (k == 0 && !kLo) ? PKnagayaL : (k == nT - 1 && !kHi) ? PKnagayaR : PKnagayaC;
                    float tot = 0f;
                    while (true)
                    {
                        tot = 0f; for (int k = 0; k < nn; k++) { var p3 = pathK(k, nn); tot += (p3 == PKnagayaL ? ml : p3 == PKnagayaR ? mr : mc).W; }
                        if (nn == 0 || Lk - tot >= nk * NAGAYA_KADO_ARM_MIN - 0.01f) break;
                        nn--;
                    }
                    float aLo = 0f, aHi = 0f, cur;
                    if (kLo && kHi) { aLo = aHi = (Lk - tot) * 0.5f; cur = seg[0] + aLo; }
                    else if (kLo) { cur = seg[1] + (gEnd0 ? tk : 0f) - tot; aLo = cur - seg[0]; }
                    else { cur = seg[0] - (gStart0 ? tk : 0f); aHi = seg[1] - (cur + tot); }
                    var ou0 = outward.normalized;
                    NagayaKado kdHi = null, kdLo = null;
                    if (kHi)
                    {
                        kdHi = KadoAt(kados, sA + rdir * len); kdHi.psi = psi; kdHi.armX = aHi; kdHi.baseY = baseY; kdHi.face = sA + rdir * lim1 - ou0 * insV;
                        kdHi.deg = nOutHi.sqrMagnitude < 1e-6f ? 90f : 180f - Mathf.Acos(Mathf.Clamp(Vector2.Dot(ou0, nOutHi.normalized), -1f, 1f)) * Mathf.Rad2Deg;
                        kdHi.tsumaX = nn == 0;                                  // 腕の先に継ぐ棟が無い(門・塀へ当たる)⇒ 妻で閉じる
                    }
                    if (kLo) { kdLo = KadoAt(kados, sA); kdLo.armZ = aLo; kdLo.tsumaZ = nn == 0; }
                    bool cLoK = legs != null && closeLo && seg[0] < lim0 + 0.01f && !gStart0;
                    bool cHiK = legs != null && closeHi && seg[1] > lim1 - 0.01f && !gEnd0;
                    if (cLoK) legS.Add(new[] { 0f, cur });
                    if (cHiK) legS.Add(new[] { len, cur + tot });
                    for (int k = 0; k < nn; k++)
                    {
                        string path = pathK(k, nn);
                        var m = path == PKnagayaL ? ml : path == PKnagayaR ? mr : mc;
                        var c2 = sA + rdir * (cur + m.hi);
                        var go = Place(path, new Vector3(c2.x, baseY, c2.y), psi, new Vector3(ES, ES, ES), parent, prefix + "_" + idx);
                        if (followGround)
                        {
                            try { SeatOnGround(go, 0.10f, 600); } catch (System.Exception) { SeatBottom(go, baseY - 0.10f); }
                            var rt = RootToBed(go, Ground, 0.25f);
                            if (!float.IsNaN(rt.hi) && rt.hi > 0f) go.transform.position -= Vector3.up * rt.hi;
                        }
                        else SeatBottom(go, baseY - 0.10f);
                        made.Add(go); idx++; cur += m.W;
                        if (k == 0 && kdLo != null) kdLo.nbrZ = go;           // 低い s 端の隅 = 隅長屋の −Z の腕
                        if (k == nn - 1 && kdHi != null) kdHi.nbrX = go;      // 高い s 端の隅 = 隅長屋の +X の腕
                    }
                    continue;
                }
            }
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
            // ⭐ 門の脇は鎖を開口の縁へ突き付け、端数は隅の側へ寄せて塀で埋める(2026-09-28 観理院 EDO-0468 ──
            //    中央寄せでは表門の両脇に 1.0〜1.2m、隅に 1.24m の素通しが開いた。隙は許容0)。
            //    門の無い区間は従来どおり中央寄せ(端数は両隅が受ける・隣の辺の駒と重なって閉じる)。
            bool gateAtEnd = gapHalf > 0 && seg == segs[0] && segs.Count > 1 || gapHalf > 0 && segs.Count == 1 && seg[1] < lim1 - 0.01f;
            bool gateAtStart = gapHalf > 0 && seg == segs[segs.Count - 1] && seg[0] > lim0 + 0.01f;
            //    門の側は開口の縁から NAGAYA_GATE_TUCK だけ門へ差し込む(隙間 > めり込み ── 平面で斜めに 0.10〜0.19m 開いた)。
            float tuck = (gateAtEnd || gateAtStart) ? gateTuck : 0f;
            float rem = L - total + tuck;
            float cursor = gateAtEnd ? seg[0] + rem : gateAtStart ? seg[0] - tuck : seg[0] + rem * 0.5f;
            // ⭐ 端の隅の隣が塀なら、端数はその隅へ寄せて長屋の側では埋めない(隣の塀が回って来る・legs)。両方なら中央。
            bool useLegs = legs != null;
            bool cLo = useLegs && closeLo && seg[0] < lim0 + 0.01f && !gateAtStart;
            bool cHi = useLegs && closeHi && seg[1] > lim1 - 0.01f && !gateAtEnd;
            if (!gateAtEnd && !gateAtStart && (cLo ^ cHi)) cursor = cHi ? seg[0] : seg[0] + rem;
            if (cLo) legS.Add(new[] { 0f, cursor });
            if (cHi) legS.Add(new[] { len, cursor + total });
            // 隣が長屋の隅へ寄せた端数は、隣の長屋の胴(奥行)に収まるなら埋めない ── 低い塀が長屋の妻の前に覗く(北東 EDO-0500)
            bool hidByNag = gateAtEnd && nagLo && seg[0] < lim0 + 0.01f && rem <= nagDepth
                         || gateAtStart && nagHi && seg[1] > lim1 - 0.01f && rem <= nagDepth;
            if ((gateAtEnd && !cLo || gateAtStart && !cHi) && rem >= 0.30f && !hidByNag)
            {
                float f0 = gateAtEnd ? seg[0] : seg[1] - (rem - tuck), f1 = gateAtEnd ? seg[0] + rem : seg[1];
                if (gateAtStart) f0 = cursor + total;
                var fl = DobeiRun(parent, sA + rdir * f0, sA + rdir * f1, outward, prefix + "_fill" + fill, followGround, baseY, Vector2.zero, -1);
                fillRuns.Add(fl);
                fill++;
            }
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
                if (followGround)
                {
                    try { SeatOnGround(go, 0.10f, 600); } catch (System.Exception) { SeatBottom(go, pieceBase - 0.10f); }
                    // ⭐ 根入れ(docs/oki-kata.md §0a)── 触れている所は上手の 1 点なので、8m の駒の下手が斜面で浮く
                    //    (2026-09-28 観理院の東の長屋 最悪 0.874m・EDO-0468)。下端の当たりのいちばん浮いた所まで沈め、上手は埋めて隠す。
                    var rt = RootToBed(go, Ground, 0.25f);
                    if (!float.IsNaN(rt.hi) && rt.hi > 0f) go.transform.position -= Vector3.up * rt.hi;
                }
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
                if (n == 1) lone.Add(go);
                cursor += m.W;                         // 継ぎ目は必ず面一
            }
        }
        // namako(表)が外向きかを数値検証、逆なら180°回して面位置を復元
        if (made.Count > 0) VerifyFlipOutward(made, outward, prefix);
        // ⭐ 区間に在庫の一棟しか入らない「孤立1棟」は妻の無い c だと両端が切り口のまま中が素通しに見える
        //    (2026-10-02 施主指摘・観理院 表門の西脇 nagaya_7_0・EDO-0500)。両端妻の一棟へ差し替える。
        for (int i = 0; i < made.Count; i++)
            if (lone.Contains(made[i])) made[i] = SwapTsuma2(made[i], rdir, outward, prefix);
        // ⭐ 端数の塀の外面を長屋の壁の外面へ合わせる(規則5 面で合わせる・2026-09-28 観理院 EDO-0468 ──
        //    塀は区画の線の上、長屋の壁は線から内に立ち、隅で 0.65〜1.7m 開いた)。足元の帯(下端から 1.0m)で測る ── 笠と軒は外へ出るので拾わない。
        if (made.Count > 0 && fillRuns.Count > 0)
        {
            float nMn, nMx; float y0 = RB(made[0]).min.y;
            var ou = outward.normalized;
            ProjExtent(made[Mathf.Min(1, made.Count - 1)], ou, y0 - 0.01f, y0 + 1.0f,
                       NagBand(made[Mathf.Min(1, made.Count - 1)]), out nMn, out nMx);
            if (nMx > float.MinValue)
                foreach (var run in fillRuns)
                    foreach (var p in run)
                    {
                        float fMn, fMx; float py = RB(p).min.y;
                        ProjExtent(p, ou, py - 0.01f, py + 1.0f, nm => true, out fMn, out fMx);
                        if (fMx > float.MinValue) p.transform.position -= new Vector3(ou.x, 0f, ou.y) * (fMx - nMx);
                        // 寄せた先の地面で据え直す(根入れ ── 下端のいちばん浮いた所まで沈める)
                        if (followGround) { var rt = RootToBed(p, Ground, 0.10f); if (!float.IsNaN(rt.hi) && rt.hi > 0f) p.transform.position -= Vector3.up * rt.hi; }
                    }
        }
        // ⭐ 塀で回す足: 長屋の外面(足元の帯)が区画の線からどれだけ内に入るかを実メッシュで測って返す(EDO-0500)
        if (legs != null && made.Count > 0 && legS.Count > 0)
        {
            float nMn, nMx; float y0 = RB(made[0]).min.y;
            var ou = outward.normalized;
            ProjExtent(made[Mathf.Min(1, made.Count - 1)], ou, y0 - 0.01f, y0 + 1.0f,
                       NagBand(made[Mathf.Min(1, made.Count - 1)]), out nMn, out nMx);
            if (nMx > float.MinValue)
                foreach (var ls in legS)
                    legs.Add(new NagayaLeg { corner = sA + rdir * ls[0], chainEnd = sA + rdir * ls[1], inset = Vector2.Dot(sA, ou) - nMx, outward = ou });
        }
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

    /// <summary>孤立1棟の在庫 c を両端妻の一棟(<see cref="EdoAssets.Own.NagayaTsuma2"/>)へ差し替える(EDO-0500)。
    /// 置き場は c の駒の実メッシュで決める ── 足元の帯(下端から 1.0m)の走りの両端の中央・外面(帯の最も外)・下端を測り、
    /// 差し替えた駒の同じ帯をそこへ突き付ける(規則21: 基準点で合わせない)。長さは c の帯の長さを cm に切り上げ(隙より埋め)。
    /// 焼いてなければ c のまま残し、焼く手を警告に出す。</summary>
    static GameObject SwapTsuma2(GameObject c, Vector2 rdir, Vector2 outward, string prefix)
    {
        var ou = outward.normalized; var rd = rdir.normalized;
        Func<string, bool> band = nm => { var l = nm.ToLower(); return l.Contains("wall") || l.Contains("namako") || l.Contains("dodai"); };
        float y0 = RB(c).min.y, s0, s1, o0, o1;
        ProjExtent(c, rd, y0 - 0.01f, y0 + 1.0f, band, out s0, out s1);
        ProjExtent(c, ou, y0 - 0.01f, y0 + 1.0f, band, out o0, out o1);
        if (s1 <= s0) return c;
        float len = Mathf.Ceil((s1 - s0) * 100f) / 100f;
        string path = EdoAssets.Own.NagayaTsuma2(len);
        if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
        {
            Debug.LogWarning(prefix + ": ⛔ 両端妻の長屋が焼いてない(孤立1棟 " + c.name + " は c のまま): blender --background --python Tools/Blender/build_nagaya_kado.py -- --straight " + len.ToString("F2") + " --render");
            return c;
        }
        var t = Place(path, c.transform.position, c.transform.eulerAngles.y, Vector3.one, c.transform.parent, c.name);
        float ty0 = RB(t).min.y, u0, u1, v0, v1;
        ProjExtent(t, rd, ty0 - 0.01f, ty0 + 1.0f, null, out u0, out u1);
        ProjExtent(t, ou, ty0 - 0.01f, ty0 + 1.0f, null, out v0, out v1);
        float ds = (s0 + s1) * 0.5f - (u0 + u1) * 0.5f, dout = o1 - v1;
        t.transform.position += new Vector3(rd.x * ds + ou.x * dout, y0 - ty0, rd.y * ds + ou.y * dout);
        UnityEngine.Object.DestroyImmediate(c);
        return t;
    }

    /// <summary>長屋の駒の足元の帯(壁・海鼠・土台)を拾う名前の篩。両端妻の一棟は FBX が一つのメッシュで
    /// 駒の根(名前は nagaya_k)に載るので篩わない(帯は高さの窓 下端+1.0m で切る)。</summary>
    static Func<string, bool> NagBand(GameObject probe)
    {
        var mf = probe.GetComponentInChildren<MeshFilter>();
        if (mf != null && mf.sharedMesh != null && mf.sharedMesh.name.StartsWith("Nagaya_Tsuma2")) return null;
        return nm => { var l = nm.ToLower(); return l.Contains("wall") || l.Contains("namako") || l.Contains("dodai"); };
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

    // ---------- 斜面なりの走り(EDO-0398・2026-09-23) ----------
    //  ⭐ 斜面に連ねる駒は **水平の長さでなく地表の道のり**で割る。水平で割って駒を傾けると、
    //     駒の水平の張り出しが pitch·cosθ に縮み、継ぎ目が毎回 pitch(1−cosθ) だけ開く
    //     (実測 2026-09-23・山王 `Saku_SW` の 30° の斜面で 0.19〜0.31m の素通しが 4 箇所)。
    //  ⭐ 継ぎ目は **駒の丈の中ほど**で合わせる。足元(ピボットの高さ)で合わせると、折れ目で
    //     頭どうしが丈 × Δsinθ(同 0.41m)重なる。中ほどで合わせるとその半分が上下に振り分かる。

    /// <summary>部材のローカル Y の実寸。<b>根入れ</b>(原点より下にある分)と<b>丈の中ほど</b>を取るために測る。
    /// ⛔ 定数で持たない(部材を替えた途端に継ぎ目と据えが破れる)。</summary>
    public struct RunHeightM
    {
        public float lo, hi;
        /// <summary>丈の中ほど(ローカル Y)。継ぎ目を合わせる高さ。</summary>
        public float Mid { get { return (lo + hi) * 0.5f; } }
        /// <summary>部材が自分で持っている根入れ[m](原点より下。柵の柱なら土に入る分)。</summary>
        public float Root { get { return Mathf.Max(0f, -lo); } }
        public float H { get { return hi - lo; } }
    }
    static readonly Dictionary<string, RunHeightM> _runHeightM = new Dictionary<string, RunHeightM>();

    /// <summary>部材のローカル Y の実寸を測る(結果は綴りごとに憶える)。</summary>
    public static RunHeightM RunMeasureY(string path)
    {
        RunHeightM m;
        if (_runHeightM.TryGetValue(path, out m)) return m;
        var pts = BodyAt(path, Vector3.zero, 0f, true);
        if (pts.Count == 0) throw new Exception("RunMeasureY: no mesh in " + path);
        float lo = float.MaxValue, hi = float.MinValue;
        foreach (var v in pts) { lo = Mathf.Min(lo, v.y); hi = Mathf.Max(hi, v.y); }
        m = new RunHeightM { lo = lo, hi = hi };
        _runHeightM[path] = m;
        return m;
    }

    /// <summary>**据わった駒を、その駒自身の丈の中ほど(継ぎ目の高さ)で切った断面**(世界座標)。
    /// 切る面は駒の**自分の座標系**の水平面 ── <see cref="PlaceOnChord"/> が勾配なりに傾けた駒でも、
    /// 継ぎ目が合う高さ(<see cref="RunHeightM.Mid"/>)で切れる。三角形と面の交わりで取るので、
    /// 頂点の無い高さでも柱の実形が出る(<see cref="SectionAt"/> と同じ理)。
    /// <para>⭐ **囲いの run が線の上に居るか・端が届いているか**を測るのに使う(2026-09-23・EDO-0413)。
    /// ⛔ 駒の外接矩形(<see cref="RB"/>)で測らない ── 斜面で傾けた駒は頭と足が走りの前後へ
    /// 丈 × sinθ はみ出すので、線の上に正しく据わった run でも外接矩形の芯は片寄る
    /// (山王 `Saku_SW` 0.053m / `Saku_Sando` 0.029m。この断面で測ると両端・横とも 0.000m)。</para></summary>
    public static List<Vector3> MidSection(GameObject go)
    {
        var L = new List<Vector3>();
        var root = go.transform;
        var mfs = go.GetComponentsInChildren<MeshFilter>();
        var toRoot = new List<Matrix4x4>();
        float lo = float.MaxValue, hi = float.MinValue;
        foreach (var mf in mfs)
        {
            var rr = mf.GetComponent<Renderer>();
            var m = root.worldToLocalMatrix * mf.transform.localToWorldMatrix;
            toRoot.Add(m);
            if (mf.sharedMesh == null || rr == null || !rr.enabled) continue;
            foreach (var v in mf.sharedMesh.vertices)
            { float y = m.MultiplyPoint3x4(v).y; if (y < lo) lo = y; if (y > hi) hi = y; }
        }
        if (lo > hi) return L;
        float mid = (lo + hi) * 0.5f;
        for (int f = 0; f < mfs.Length; f++)
        {
            var mf = mfs[f]; var rr = mf.GetComponent<Renderer>();
            if (mf.sharedMesh == null || rr == null || !rr.enabled) continue;
            var vs = mf.sharedMesh.vertices;
            var w = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) w[i] = toRoot[f].MultiplyPoint3x4(vs[i]);
            var tri = mf.sharedMesh.triangles;
            for (int i = 0; i + 2 < tri.Length; i += 3)
                for (int e = 0; e < 3; e++)
                {
                    Vector3 p = w[tri[i + e]], q = w[tri[i + (e + 1) % 3]];
                    if ((p.y - mid) * (q.y - mid) > 0f) continue;
                    float dy = q.y - p.y;
                    if (Mathf.Abs(dy) < 1e-7f) continue;
                    L.Add(root.TransformPoint(Vector3.Lerp(p, q, (mid - p.y) / dy)));
                }
        }
        return L;
    }

    /// <summary>折れ線 <paramref name="poly"/>(xz)の上で点 <paramref name="p"/> に最も近い所の
    /// **道のり** <paramref name="s"/> と**符号付きの横のずれ** <paramref name="lat"/>(走りの左が +)。
    /// 端の辺は外へ <paramref name="ext"/>[m] まで延ばして測る ── 端を越えた点は s &lt; 0 / s &gt; 全長 で返る
    /// (端が届いているかを見るため)。⚠ 延長は短く縛る ── 縛らないと、境内を回る run(`Ita_Keidai`)で
    /// 始まり側の駒が 54m 先の終わりの辺の延長線へ吸われ、端が 62m 越えていると出た(2026-09-23 実測)。</summary>
    public static void PolylineParam(List<Vector2> poly, Vector2 p, out float s, out float lat, float ext = 1.0f)
    {
        s = 0f; lat = 0f;
        float best = float.MaxValue, acc = 0f;
        for (int i = 0; i + 1 < poly.Count; i++)
        {
            Vector2 a = poly[i], b = poly[i + 1];
            float len = Vector2.Distance(a, b);
            if (len < 1e-6f) continue;
            Vector2 d = (b - a) / len;
            float t = Vector2.Dot(p - a, d);
            bool first = i == 0, last = i + 2 >= poly.Count;
            float tc = first && t < 0f ? Mathf.Max(t, -ext)
                     : last && t > len ? Mathf.Min(t, len + ext)
                     : Mathf.Clamp(t, 0f, len);
            float dist = Vector2.Distance(p, a + d * tc);
            if (dist < best - 1e-6f)
            { best = dist; s = acc + tc; lat = Vector2.Dot(p - a, new Vector2(-d.y, d.x)); }
            acc += len;
        }
    }

    /// <summary>**地表なりの折れ線へ割る。**辺 a→b を、<b>描かれている地表</b>に沿った実長(道のり)で
    /// <paramref name="span"/> ごとに割り、継ぎ目の点(世界座標・高さは地表)を返す。
    /// 駒はこの点から点へ張るので、傾けても継ぎ目が開かない。
    ///
    /// <para>⭐ 継ぎ目の高さは隣どうしで <paramref name="smooth"/> 巡だけ均して、折れ目の角を複数の継ぎ目へ散らす
    /// (地形の折れをそのまま拾うと、一つの継ぎ目に 20〜24° が集まる)。均しは
    /// <paramref name="floatMax"/>(上)/ <paramref name="buryMax"/>(下)で縛る ── 呼び手は**部材の根入れ**を渡すこと。
    /// 上は根入れ = 「足を地面から出さない」、下はその倍 = 「足元が土に隠れるのは構わない」。
    /// ⚠ 巡を増やすほど縛りに当たった継ぎ目へ折れが集まる(実測: 3 巡で悪化)。既定の 2 巡から上げない。</para>
    ///
    /// <para>⛔ 地表は <see cref="Ground"/>(描かれている面)で引く — <see cref="GroundGrid"/> は斜面で ±(1m×勾配) の嘘。</para></summary>
    public static List<Vector3> GroundPolyline(Vector2 a, Vector2 b, float span,
                                               float floatMax, float buryMax, int smooth = 2)
    {
        var outp = new List<Vector3>();
        float L = Vector2.Distance(a, b);
        if (L < 1e-4f || span < 1e-4f)
        {
            outp.Add(new Vector3(a.x, Ground(a.x, a.y), a.y));
            outp.Add(new Vector3(b.x, Ground(b.x, b.y), b.y));
            return outp;
        }
        Vector2 dir = (b - a) / L;
        int M = Mathf.Max(2, Mathf.CeilToInt(L / 0.25f));
        float step = L / M;
        var probe = Probe();
        var gy = new float[M + 1]; var arc = new float[M + 1];
        for (int i = 0; i <= M; i++) { Vector2 p = a + dir * (step * i); gy[i] = probe.At(p.x, p.y); }
        for (int i = 1; i <= M; i++)
        {
            float dh = gy[i] - gy[i - 1];
            arc[i] = arc[i - 1] + Mathf.Sqrt(step * step + dh * dh);
        }
        float S = arc[M];
        int N = Mathf.Max(1, Mathf.RoundToInt(S / span));
        var js = new float[N + 1]; var jy = new float[N + 1]; var baseY = new float[N + 1];
        int cur = 0;
        for (int k = 0; k <= N; k++)
        {
            float t = S * k / N;
            while (cur < M - 1 && arc[cur + 1] < t) cur++;
            float den = arc[cur + 1] - arc[cur];
            float f = den > 1e-6f ? Mathf.Clamp01((t - arc[cur]) / den) : 0f;
            js[k] = (cur + f) * step;
            jy[k] = Mathf.Lerp(gy[cur], gy[cur + 1], f);
            baseY[k] = jy[k];
        }
        for (int it = 0; it < smooth && N >= 2; it++)
        {
            var ny = (float[])jy.Clone();
            for (int k = 1; k < N; k++)
            {
                float v = 0.25f * jy[k - 1] + 0.5f * jy[k] + 0.25f * jy[k + 1];
                ny[k] = Mathf.Clamp(v, baseY[k] - buryMax, baseY[k] + floatMax);
            }
            jy = ny;
        }
        for (int k = 0; k <= N; k++) { Vector2 p = a + dir * js[k]; outp.Add(new Vector3(p.x, jy[k], p.y)); }
        return outp;
    }

    /// <summary>**走りを床の段(鉛直の落ち)で割る**(2026-09-26・EDO-0430 山王 `Ita_Keidai` の柵 × 御供所の郭の土留め)。
    /// 辺 a→b に沿って床の高さ <paramref name="heightAt"/> を <paramref name="res"/> ごとに引き、隣どうしで <paramref name="jump"/> を超えて
    /// 変わる所(= 土留めの天端の縁・段の小口 ── 勾配ではなく落ち)を二分で 0.005m まで詰め、そこで辺を割って返す。
    /// 落ちの縁から <paramref name="minLen"/> 未満の切れ端は捨てる(隣の辺の端の柱が受ける)。手前の区間は落ちの手前の側で終わり、
    /// 次の区間は向こうの側で始まる(端の高さを引くと、それぞれ自分の側の床が出る)。
    /// ⭐ 座で据える走り(<see cref="SeatOrBed"/>)は継ぎ目ごとに高さを取るので、落ちを跨ぐ弦は一本で 0.95m 落ちる斜めの駒になり、
    /// 丈の中ほどで継ぐ(<see cref="PlaceOnChord"/>)ため足元が前後の駒へ 0.23m めり込み・反対の足が 0.15m 浮いた。
    /// 割れば各区間は平らに据わり、落ちでは上の区間の端の柱と下の区間の頭の柱が段違いに立つ。
    /// 当たる先: 座(`seat`)で据える柵・板塀の走りが土留め・石段の小口を跨ぐすべて(山王 Stage4 の柵)。</summary>
    public static List<Vector2[]> SplitAtBedSteps(Vector2 a, Vector2 b, Func<float, float, float> heightAt, float jump,
                                                  float res = 0.05f, float minLen = 0.10f)
    {
        var outp = new List<Vector2[]>();
        float L = Vector2.Distance(a, b);
        if (L < 1e-4f) { outp.Add(new[] { a, b }); return outp; }
        Vector2 dir = (b - a) / L;
        int M = Mathf.Max(1, Mathf.CeilToInt(L / res));
        var cuts = new List<Vector2>();   // (落ちの手前, 向こう)── 0.005m 以内に詰めた二分の括り。手前の区間は x で終わり、次は y で始まる
        float prev = heightAt(a.x, a.y);
        for (int i = 1; i <= M; i++)
        {
            float s1 = L * i / M; Vector2 p = a + dir * s1; float h = heightAt(p.x, p.y);
            if (!float.IsNaN(prev) && !float.IsNaN(h) && Mathf.Abs(h - prev) > jump)
            {
                float lo = L * (i - 1) / M, hi = s1, h0 = prev;
                for (int it = 0; it < 12 && hi - lo > 0.005f; it++)
                {
                    float mid = (lo + hi) * 0.5f; Vector2 q = a + dir * mid; float hm = heightAt(q.x, q.y);
                    if (!float.IsNaN(hm) && Mathf.Abs(hm - h0) > jump * 0.5f) hi = mid; else lo = mid;
                }
                cuts.Add(new Vector2(lo, hi));
            }
            prev = h;
        }
        float s0 = 0f;
        cuts.Add(new Vector2(L, L));
        foreach (var c in cuts)
        {
            if (c.x - s0 >= minLen) outp.Add(new[] { a + dir * s0, a + dir * c.x });
            s0 = c.y;
        }
        if (outp.Count == 0) outp.Add(new[] { a, b });
        return outp;
    }

    /// <summary>**弦に沿って駒を据える。**継ぎ目 <paramref name="j0"/>→<paramref name="j1"/> に張るよう、
    /// yaw = 走り・roll = 弦の勾配・走り方向の伸縮 = 弦の実長(斜距離)で置く。
    /// 継ぎ目は駒の**丈の中ほど**(<see cref="RunMeasureY"/> の Mid)で合う ──
    /// 走り方向へ Mid·sin(roll) 送るだけで、隣の駒との食い違いが頭と足へ半分ずつ振り分かる。
    /// <para>⛔ 足元で継がない(折れ目で頭が丈 × Δsinθ 重なる)。⛔ 水平の長さで伸縮しない(継ぎ目が開く)。</para></summary>
    public static GameObject PlaceOnChord(string path, Vector3 j0, Vector3 j1, Transform parent, string name)
    {
        float spanLocal = RunMeasure(path).W;
        var rh = RunMeasureY(path);
        Vector2 h0 = new Vector2(j0.x, j0.z), h1 = new Vector2(j1.x, j1.z);
        float du = Vector2.Distance(h0, h1), dy = j1.y - j0.y;
        Vector2 dir = du > 1e-6f ? (h1 - h0) / du : Vector2.right;
        float chord = Mathf.Sqrt(du * du + dy * dy);
        float yaw = Mathf.Atan2(-dir.y, dir.x) * Mathf.Rad2Deg;
        float roll = Mathf.Atan2(dy, du) * Mathf.Rad2Deg;
        float shift = rh.Mid * Mathf.Sin(roll * Mathf.Deg2Rad);
        var pos = new Vector3((j0.x + j1.x) * 0.5f + dir.x * shift,
                              (j0.y + j1.y) * 0.5f,
                              (j0.z + j1.z) * 0.5f + dir.y * shift);
        var go = Place(path, pos, yaw, new Vector3(chord / spanLocal, 1f, 1f), parent, name);
        if (Mathf.Abs(roll) > 0.01f)
            go.transform.rotation = Quaternion.Euler(0, yaw, 0) * Quaternion.Euler(0, 0, roll);
        return go;
    }

    /// <summary>**弦に張る(実測版)**(2026-09-27・EDO-0477 P2)。<see cref="PlaceOnChord"/> と同じく継ぎ目 <paramref name="j0"/>→<paramref name="j1"/> に
    /// 勾配なりに張るが、**ピボットを使わない** ── 駒の実メッシュの走りの中央・丈の中ほどを測り、その点を弦の中点(足元から丈の中ほどまで上げた所)へ
    /// 置く。足元の線が弦に乗り、隣の駒とは丈の中ほどで継ぐ。奥行は据えた駒の実測の厚みの中央を <paramref name="latLine"/>(outward への射影)へ寄せる。
    /// <paramref name="unitScale"/> は丈と厚みの倍率(edogoyomi の obj は ES)。
    /// <para>⭐ 表(ローカル +Z)を <paramref name="outward"/> へ向けたいなら j0→j1 を (−dir.y, dir.x)·outward > 0 の順で渡す(<see cref="ChordFacing"/>)。</para>
    /// 当たる先: 類型の板塀・練塀の run(<see cref="DobeiRun"/>・<see cref="NeribeiRun"/> の地形なり)。</summary>
    public static GameObject PlaceOnChordMeasured(string path, Vector3 j0, Vector3 j1, Vector2 outward, float latLine,
                                                  float unitScale, Transform parent, string name, float ext0 = 0f, float ext1 = 0f)
    {
        var rx = RunMeasure(path); var ry = RunMeasureY(path);
        Vector2 h0 = new Vector2(j0.x, j0.z), h1 = new Vector2(j1.x, j1.z);
        float du = Vector2.Distance(h0, h1), dy = j1.y - j0.y;
        Vector2 dir = du > 1e-6f ? (h1 - h0) / du : Vector2.right;
        float chord = Mathf.Sqrt(du * du + dy * dy);
        float yaw = Mathf.Atan2(-dir.y, dir.x) * Mathf.Rad2Deg;
        float roll = Mathf.Atan2(dy, du) * Mathf.Rad2Deg;
        // ⭐ ext0/ext1 = 継ぎ目の外へ伸ばす長さ(折れの継ぎ目で隣と重ねる ── 隙間>めり込み)
        float sx = (chord + ext0 + ext1) / rx.W;
        var yawQ = Quaternion.Euler(0f, yaw, 0f);
        var cdir = chord > 1e-6f ? (j1 - j0) / chord : Vector3.right;
        var anchorL = new Vector3((rx.lo + rx.hi) * 0.5f, ry.Mid, 0f);                 // 実メッシュの走りの中央・丈の中ほど
        var anchorW = (j0 + j1) * 0.5f + cdir * ((ext1 - ext0) * 0.5f)
                    + Vector3.up * ((ry.Mid - ry.lo) * unitScale);                      // 弦の中点(足元)から丈の中ほどまで
        GameObject go;
        if (Mathf.Abs(roll) < 0.05f)
        {
            var scale = new Vector3(sx, unitScale, unitScale);
            var pos = anchorW - yawQ * Vector3.Scale(scale, anchorL);
            go = Place(path, pos, yaw, scale, parent, name);
            go.transform.rotation = yawQ; go.transform.position = pos;
        }
        else
        {
            // ⭐ 勾配の弦は**剪断で張る** ── 柱は鉛直のまま、駒の走りだけを弦に沿わせる(2026-09-28・EDO-0472)。
            //    ⛔ 2026-09-28 まで駒を roll で回していたので、柱が傾き、上端が丈 × sin(roll) だけ弦の低い端の外へ倒れて
            //    走りの端(区画の角)を越えた(十坊 4・5・9 の角の板塀 8 駒が区画の外へ 0.61〜0.85m)。
            //    Unity の transform は剪断を持てないので、M = R(φ)·Σ·R(θ)(2×2 の特異値分解・走り×丈の面)を
            //    枠(yaw だけ・倍率 1 ── RootToBed 等が測る局所の上 = 世界の上)→ 中(R(φ)・Σ)→ 駒(R(θ))の三段に割る。
            //    当たる先: DobeiRun・NeribeiRun の地形なりの枝(類型の板塀・生垣付き板塀・石垣+塀・練塀の全区画)。
            float r = roll * Mathf.Deg2Rad;
            float a = sx * Mathf.Cos(r), c = sx * Mathf.Sin(r), dd = unitScale;  // 列 = 局所 x・y の像(走り・上)
            float E = (a + dd) * 0.5f, F = (a - dd) * 0.5f, G = c * 0.5f, H = c * 0.5f;
            float Q = Mathf.Sqrt(E * E + H * H), R = Mathf.Sqrt(F * F + G * G);
            float s1 = Q + R, s2 = Q - R, a1 = Mathf.Atan2(G, F), a2 = Mathf.Atan2(H, E);
            float th = (a2 - a1) * 0.5f * Mathf.Rad2Deg, ph = (a2 + a1) * 0.5f * Mathf.Rad2Deg;
            var qPh = Quaternion.Euler(0f, 0f, ph); var qTh = Quaternion.Euler(0f, 0f, th);
            var sig = new Vector3(s1, s2, unitScale);
            var pos = anchorW - yawQ * (qPh * Vector3.Scale(sig, qTh * anchorL));
            go = new GameObject(name);
            go.transform.SetParent(parent, true);
            go.transform.position = pos; go.transform.rotation = yawQ; go.transform.localScale = Vector3.one;
            var mid = new GameObject("剪断");
            mid.transform.SetParent(go.transform, false);
            mid.transform.localRotation = qPh; mid.transform.localScale = sig;
            var piece = Place(path, Vector3.zero, 0f, Vector3.one, mid.transform, name + "_駒");
            piece.transform.localPosition = Vector3.zero; piece.transform.localRotation = qTh; piece.transform.localScale = Vector3.one;
            Undo.RegisterCreatedObjectUndo(go, "place " + name);
        }
        float lmn, lmx;
        ProjExtent(go, outward, float.MinValue, float.MaxValue, null, out lmn, out lmx);
        float d = latLine - (lmn + lmx) * 0.5f;
        go.transform.position += new Vector3(outward.x * d, 0f, outward.y * d);
        return go;
    }

    /// <summary>地形なりの走りの根入れの深さの上限[m](山王の板塀の代 −0.60 と同じ ── 2026-09-27 施主「基本は埋める」)。
    /// これより深く埋めないと着かない所(崖・急な横断勾配)は浮きのまま残して刷る(崖の線は塀を建てない所 ── 呼び手が決める)。</summary>
    public const float CHORD_ROOT_MAX = 0.60f;

    /// <summary>**弦の走りを根入れで収める**(2026-09-28・EDO-0477)。継ぎ目 <paramref name="js"/> に駒を弦で張り(<paramref name="placeSeg"/>)、
    /// 各駒の**下端**(<see cref="RootToBed"/> ── 当たり = 見えている地表)の浮きを測って、浮いた駒の両端の継ぎ目をその分だけ下げて張り直す。
    /// 継ぎ目は隣の駒と共有したまま動かすので、天端は一続きの折れ線のまま(段々にならない)。収まるまで(最大 6 巡)回す。
    /// ⛔ 芯の線だけで地面に合わせると、塀の厚み方向に地面が傾く所で低い側の縁が浮いた(観理院 辺2・辺3 で 1m あたり 0.2〜0.6m の横断勾配・
    /// 最大 0.29m)。当たる先: 地形なりの練塀(<see cref="NeribeiRun"/>)・板塀(<see cref="DobeiRun"/>)── 類型の全区画の囲い。</summary>
    public static List<GameObject> RootChordRun(List<Vector3> js, Func<int, Vector3, Vector3, List<GameObject>> placeSeg, out float worstFloat, out float deepest,
                                                List<int> breaks = null)
    {
        int m = js.Count - 1; var drop = new float[js.Count];
        var segs = new List<GameObject>[m];
        Func<float, float, float> bed = (x, z) => Ground(x, z);
        worstFloat = 0f; deepest = 0f;
        for (int it = 0; it < 6; it++)
        {
            for (int k = 0; k < m; k++)
            {
                if (segs[k] != null) foreach (var g in segs[k]) UnityEngine.Object.DestroyImmediate(g);
                segs[k] = placeSeg(k, js[k] - Vector3.up * drop[k], js[k + 1] - Vector3.up * drop[k + 1]);
            }
            bool moved = false; worstFloat = 0f;
            var need = new float[js.Count];
            for (int k = 0; k < m; k++)
            {
                float hi = 0f;
                foreach (var g in segs[k]) { var r = RootToBed(g, bed, 0.05f); if (!float.IsNaN(r.hi)) hi = Mathf.Max(hi, r.hi); }
                worstFloat = Mathf.Max(worstFloat, hi);
                if (hi > 0.002f) { need[k] = Mathf.Max(need[k], hi); need[k + 1] = Mathf.Max(need[k + 1], hi); }
            }
            if (breaks != null && breaks.Count >= 2)
            {
                // ⭐ 一直線の区間(breaks の間)は**区間ごと下げる**(2026-09-28 施主「塀が地形に合わせて滑らかに波打つ」)。
                //    ⛔ 継ぎ目を一つずつ下げると天端が折れ線に戻る。区間の両端を区間の中の最悪の浮きだけ下げ、中は両端から線形に取る。
                var bn = new float[js.Count];
                for (int r = 0; r + 1 < breaks.Count; r++)
                {
                    float rn = 0f; for (int j = breaks[r]; j <= breaks[r + 1]; j++) rn = Mathf.Max(rn, need[j]);
                    bn[breaks[r]] = Mathf.Max(bn[breaks[r]], rn); bn[breaks[r + 1]] = Mathf.Max(bn[breaks[r + 1]], rn);
                }
                for (int r = 0; r + 1 < breaks.Count; r++)
                {
                    int b0 = breaks[r], b1 = breaks[r + 1];
                    float d0 = Mathf.Min(CHORD_ROOT_MAX, drop[b0] + bn[b0]), d1 = Mathf.Min(CHORD_ROOT_MAX, drop[b1] + bn[b1]);
                    for (int j = b0; j <= b1; j++)
                    {
                        float nd = b1 > b0 ? Mathf.Lerp(d0, d1, (float)(j - b0) / (b1 - b0)) : d0;
                        need[j] = Mathf.Max(0f, nd - drop[j]);
                    }
                }
            }
            for (int j = 0; j < js.Count; j++)
            {
                float nd = Mathf.Min(CHORD_ROOT_MAX, drop[j] + need[j]);
                if (nd > drop[j] + 0.001f) { drop[j] = nd; moved = true; }
            }
            if (!moved) break;
        }
        foreach (var d in drop) deepest = Mathf.Max(deepest, d);
        var all = new List<GameObject>(); foreach (var sg in segs) all.AddRange(sg);
        return all;
    }

    /// <summary>**天端を一続きごとに一直線に取る継ぎ目**(2026-09-28・EDO-0477 施主「塀が地形に合わせて滑らかに波打ってる」)。
    /// a→b の地表を 0.25m ごとに読み、始点から**一直線のまま下端が浮かず・根入れ <see cref="CHORD_ROOT_MAX"/> 以内に収まる所まで**区間を延ばす
    /// (下端の線は地表 − <paramref name="root"/> を越えない最も高い直線)。収まらなくなった所で折り、次の区間は前の終わりの高さから続ける。
    /// 区間の中は道のり <paramref name="span"/> ほどの駒に等分し、継ぎ目は直線の上に置く。<paramref name="breaks"/> は折れの継ぎ目の番号(両端を含む)。
    /// ⛔ 1 駒ごとに地表へ弦を張ると天端が波打ち、傾きの違う駒の継ぎ目に V の隙が開いた(観理院・山王社の前庭から)。
    /// 当たる先: 地形なりの練塀・板塀(<see cref="NeribeiRun"/>・<see cref="DobeiRun"/>)── 類型の全区画の囲い。</summary>
    public static List<Vector3> StraightRunJoints(Vector2 a, Vector2 b, float span, float root, out List<int> breaks)
    {
        var outp = new List<Vector3>(); breaks = new List<int>();
        float L = Vector2.Distance(a, b);
        Vector2 dir = L > 1e-6f ? (b - a) / L : Vector2.right;
        int M = Mathf.Max(2, Mathf.CeilToInt(L / 0.25f)); float step = L / M;
        var probe = Probe();
        var g = new float[M + 1];
        for (int i = 0; i <= M; i++) { var p = a + dir * (step * i); g[i] = probe.At(p.x, p.y); }
        int s = 0; float y0 = g[0] - root;
        outp.Add(new Vector3(a.x, y0, a.y)); breaks.Add(0);
        while (s < M)
        {
            float mLo = float.MinValue, mHi = float.MaxValue; int e = s;
            for (int i = s + 1; i <= M; i++)
            {
                float t = step * (i - s);
                float hi = Mathf.Min(mHi, (g[i] - root - y0) / t);              // 下端が地表 − root を越えない
                float lo = Mathf.Max(mLo, (g[i] - CHORD_ROOT_MAX - y0) / t);    // 根入れが上限を越えない
                if (lo > hi && e > s) break;                                    // この点を入れると一直線で収まらない
                mHi = hi; mLo = lo; e = i;
                if (lo > hi) break;                                             // 一歩目から収まらない(崖)── 浮かせない側を採って折る
            }
            // 傾きは浮かない側の上限(= どこかで根入れ root で地表に当たる、最も浅く埋まる直線)
            float te = step * (e - s), ye = y0 + mHi * te;
            // 区間 s..e を道のり span ほどに等分
            float du = te, dy = ye - y0;
            int n = Mathf.Max(1, Mathf.RoundToInt(Mathf.Sqrt(du * du + dy * dy) / span));
            for (int k = 1; k <= n; k++)
            {
                float f = (float)k / n; var p = a + dir * (step * s + te * f);
                outp.Add(new Vector3(p.x, y0 + dy * f, p.y));
            }
            breaks.Add(outp.Count - 1);
            s = e; y0 = ye;
        }
        return outp;
    }

    /// <summary>折れの継ぎ目で隣の駒へ重ねる長さ[m] ── 丈の半分 × 傾きの差 + 0.02(隙間>めり込み・駒どうしの埋め込みは数えない)。</summary>
    public static float KinkOverlap(List<Vector3> js, List<int> breaks, int j, float height)
    {
        if (j <= 0 || j >= js.Count - 1 || !breaks.Contains(j)) return 0f;
        Func<Vector3, Vector3, float> ang = (p, q) => Mathf.Atan2(q.y - p.y, Vector2.Distance(new Vector2(p.x, p.z), new Vector2(q.x, q.z)));
        float d = Mathf.Abs(ang(js[j], js[j + 1]) - ang(js[j - 1], js[j]));
        if (d < 1e-4f) return 0f;
        // ⭐ 重ねは隣の弦の半分まで(硬い)── 折れが急だと tan が膨らみ、駒が隣の弦を越えて走りの端(区画の角)の外へ出た
        //    (十坊2 の西の辺の北の角で 2.24m・EDO-0495)。当たる先: 地形なりの板塀・生垣付き板塀・石垣+塀・練塀(DobeiRun/NeribeiRun)と旧山王の TW_*/SB_*。
        Func<Vector3, Vector3, float> run = (p, q) => Vector2.Distance(new Vector2(p.x, p.z), new Vector2(q.x, q.z));
        float cap = 0.5f * Mathf.Min(run(js[j - 1], js[j]), run(js[j], js[j + 1]));
        return Mathf.Min(height * 0.5f * Mathf.Tan(Mathf.Min(d, 1.4f)) + 0.02f, cap);
    }

    /// <summary>弦 j0→j1 に張った駒の表(ローカル +Z)が <paramref name="outward"/> を向くか。</summary>
    public static bool ChordFacing(Vector3 j0, Vector3 j1, Vector2 outward)
    {
        Vector2 d = new Vector2(j1.x - j0.x, j1.z - j0.z);
        return Vector2.Dot(new Vector2(-d.y, d.x), outward) > 0f;
    }

    /// <summary>地形なりの走りで、継ぎ目を足元から沈める根入れ[m]。⭐ 継ぎ目の均しの上限にも同じ値を使う
    /// (<see cref="GroundPolyline"/> の floatMax)ので、継ぎ目で足が地面から出ることはない。旧来の SeatOnGround(go, 0.10) と同じ値。</summary>
    const float SLOPE_ROOT = 0.10f;

    /// <summary>駒を走り方向 <paramref name="dir"/> の実寸で <paramref name="startAbs"/>(世界の xz を dir へ射影した値)へ突き付ける。
    /// 奥行は実測した厚みの中央を「線から latOff だけ内」へ。返る <paramref name="mn"/>/<paramref name="mx"/> は
    /// 据えたあとの端の**実測値**(次の駒はこの mx へ突き付ける)。
    /// ⛔ bounds の中心へ合わせない。奥行と走りは**連立で一度に**寄せる ── 駒は原点で生まれて数百 m 動くので、外向きと走りが
    /// 直交していないと(呼び手が走りの端を線の向きへ延ばした斜めの継ぎ)、順に動かしたとき走りの移動が奥行を角度 × 距離だけ崩す
    /// (観理院の石垣の頭の継ぎ 1.4° で 6.7m 横へ流れた・2026-09-28 EDO-0477)。直交なら従来と同じ結果。</summary>
    static void ButtOnRun(GameObject go, Vector2 A, Vector2 dir, Vector2 outward, float latOff, float startAbs,
                          out float mn, out float mx)
    {
        float lmn, lmx;
        ProjExtent(go, outward, float.MinValue, float.MaxValue, null, out lmn, out lmx);
        ProjExtent(go, dir, float.MinValue, float.MaxValue, null, out mn, out mx);
        float tLat = (Vector2.Dot(A, outward) + latOff) - (lmn + lmx) * 0.5f;
        float tRun = startAbs - mn;
        float c = Vector2.Dot(outward, dir), den = 1f - c * c;
        float a = den > 1e-6f ? (tLat - c * tRun) / den : tLat, b = den > 1e-6f ? (tRun - c * tLat) / den : tRun;
        var v = outward * a + dir * b;
        go.transform.position += new Vector3(v.x, 0f, v.y);
        mn += tRun; mx += tRun;
    }

    // ---------- dobei run (表裏ペア) ----------
    // 走り方向: 区間を pitch に等分し、駒の実寸(RunMeasure)を pitch へ伸縮して、前の駒の実測の端へ突き付ける。
    // ⚠ 表(side 0)が鎖の主。裏(side 1)は表の端の実測に揃える(裏は 0.20m 内側へ寄る)。
    // ⭐ 開口(門)があれば**辺を開口で区切ってから**区間ごとに割る(NeribeiRun と同じ)。板の端は開口の縁
    //    = 呼び手が門構えの実測の妻面から採った幅に来る。⛔ 2026-09-27 まで辺全体を等割りし、開口に掛かる板を
    //    丸ごと抜いていた — 門の脇に最大で板 1 枚(≈3m)の隙が空いた(施主指摘・十坊の写真・EDO-0474)。
    const float DOBEI_PITCH = 2.982f;
    const float DOBEI_MIN_PIECE = 0.05f;   // これより短い端数は板にならない(開口の縁の丸めの誤差)
    public static List<GameObject> DobeiRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        bool followGround, float flatBase, Vector2 gapC, float gapHalf)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        var segs = new List<float[]>();
        if (gapHalf > 0)
        {
            float gT = Vector2.Dot(gapC - A, dir);
            if (gT - gapHalf > DOBEI_MIN_PIECE) segs.Add(new float[] { 0f, Mathf.Min(gT - gapHalf, len) });
            if (gT + gapHalf < len - DOBEI_MIN_PIECE) segs.Add(new float[] { Mathf.Max(gT + gapHalf, 0f), len });
        }
        else segs.Add(new float[] { 0f, len });
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        float a0 = Vector2.Dot(A, dir);
        float W = RunMeasure(PHei).W;
        int k = 0;
        float lat0 = Vector2.Dot(A, outward);
        foreach (var seg in segs)
        {
            float L = seg[1] - seg[0];
            // ⭐ 地形なりの run は**地表の道のりで割り、駒を弦に張る**(2026-09-27・EDO-0477 P2 ── 山王の柵 EDO-0398 の型を共有へ)。
            //   ⛔ 2026-09-27 まで駒は水平のまま「触れている箇所」(= 斜面の上手の端)で据えていたので、下手の端が
            //   勾配 × 駒の長さだけ宙に浮いた(観理院の西の斜面で 133 駒中 35 駒が 5cm 超・最大 1.74m・EDO-0466/0431)。
            //   天端は区間ごとに一続きの線になり、段々にならない(施主の規則「天端は一続きごとに一直線」)。
            //   当たる先: 類型の板塀・生垣付き板塀・石垣+塀・既定の囲い(followGround = NaturalMode)と、地形なりで呼ぶ旧山王ビルダーの TW_*/SB_*。
            if (followGround)
            {
                // ⭐ 天端は一続きごとに一直線(StraightRunJoints)・折れの継ぎ目は重ねる(KinkOverlap)── 2026-09-28 施主「波打ってる」「隙間」
                List<int> brk;
                var js = StraightRunJoints(A + dir * seg[0], A + dir * seg[1], DOBEI_PITCH, SLOPE_ROOT, out brk);
                float hH = (RunMeasureY(PHei).hi - RunMeasureY(PHei).lo) * ES;
                int k0 = k; float wf, dp;
                made.AddRange(RootChordRun(js, (j, j0, j1) =>
                {
                    var two = new List<GameObject>();
                    bool fwd = ChordFacing(j0, j1, outward);
                    float e0 = KinkOverlap(js, brk, j, hH), e1 = KinkOverlap(js, brk, j + 1, hH);
                    for (int side = 0; side < 2; side++)
                    {
                        bool f = side == 0 ? fwd : !fwd;
                        two.Add(PlaceOnChordMeasured(PHei, f ? j0 : j1, f ? j1 : j0, outward, lat0 + (side == 0 ? 0f : -0.2f), ES,
                                                     parent, prefix + "_" + (k0 + j) + (side == 0 ? "f" : "b"), f ? e0 : e1, f ? e1 : e0));
                    }
                    return two;
                }, out wf, out dp, brk));
                k += js.Count - 1;
                continue;
            }
            // ⭐ 区間を板で**割り切る**(端数を残さない)。短い区間は 1 枚を縮めて埋める。
            int n = Mathf.Max(1, Mathf.RoundToInt(L / DOBEI_PITCH));
            float pitch = L / n;
            float sx = pitch / W;
            bool chained = false; float prevEnd = 0f;
            for (int j = 0; j < n; j++, k++)
            {
            var c2 = A + dir * (seg[0] + pitch * (j + 0.5f));
            float baseY = flatBase;
            float startAbs = chained ? prevEnd : a0 + seg[0] + pitch * j;
            for (int side = 0; side < 2; side++)
            {
                float ry = side == 0 ? psi : psi + 180f;
                var go = Place(PHei, Vector3.zero, ry, new Vector3(sx, ES, ES), parent,
                    prefix + "_" + k + (side == 0 ? "f" : "b"));
                float mn, mx;
                ButtOnRun(go, A, dir, outward, side == 0 ? 0.0f : -0.2f, startAbs, out mn, out mx);
                if (side == 0) { prevEnd = mx; chained = true; }
                SeatBottom(go, baseY - 0.10f);   // 平らな座(地形なりは上の弦の枝)
                made.Add(go);
            }
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
        float lat0 = Vector2.Dot(A, outward);
        foreach (var seg in segs)
        {
            float L = seg[1] - seg[0];
            if (L < bodyLen * 0.5f) continue;    // 一枚も入らない端数は置かない(呼び手が別途埋める)
            // ⭐ 地形なりは**地表の道のりで割り、駒を弦に張る**(2026-09-27・EDO-0477 P2。DobeiRun と同じ型)。
            //   ⛔ 水平の駒を上手の端で据えると下手が宙に浮く(観理院・十坊の練塀 6.2〜6.8m 浮き・EDO-0431)。
            //   妻塞ぎ(Dobei2mEnd)は小口がローカル x の低い側にあるので、弦の j0 を**自由端**に取る(回転の向きを外向きの算術に頼らない)。
            if (followGround)
            {
                // ⭐ 天端は一続きごとに一直線(StraightRunJoints)・折れの継ぎ目は重ねる(KinkOverlap)── 2026-09-28 施主「波打ってる」「隙間」
                List<int> brk;
                var js = StraightRunJoints(A + dir * seg[0], A + dir * seg[1], bodyLen, SLOPE_ROOT, out brk);
                int m = js.Count - 1;
                bool cLo = gapHalf > 0 && seg[0] > 0.01f;
                bool cHi = gapHalf > 0 && seg[1] < len - 0.01f && !(m == 1 && cLo);
                float hH = RunMeasureY(EdoAssets.Own.Dobei2m).hi - RunMeasureY(EdoAssets.Own.Dobei2m).lo;
                int idx0 = idx; float wf, dp;
                made.AddRange(RootChordRun(js, (k, j0, j1) =>
                {
                    bool atLo = k == 0 && cLo, atHi = k == m - 1 && cHi;
                    string path = (atLo || atHi) ? EdoAssets.Own.Dobei2mEnd : EdoAssets.Own.Dobei2m;
                    bool f = atLo ? true : atHi ? false : ChordFacing(j0, j1, outward);
                    float e0 = KinkOverlap(js, brk, k, hH), e1 = KinkOverlap(js, brk, k + 1, hH);
                    return new List<GameObject> { PlaceOnChordMeasured(path, f ? j0 : j1, f ? j1 : j0, outward, lat0, 1f, parent, prefix + "_" + (idx0 + k), f ? e0 : e1, f ? e1 : e0) };
                }, out wf, out dp, brk));
                idx += m;
                continue;
            }
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
                SeatBottom(go, flatBase - 0.10f);   // 平らな座(地形なりは上の弦の枝)
                made.Add(go); idx++;
            }
        }
        return made;
    }

    // ---------- 段塀(2026-09-29・EDO-0477 施主裁定1=B)----------
    // ⭐ 屋敷の練塀は**傾けない**。区間ごとに笠を水平にし、区切りで段を付ける(段塀)。区間の中で地面が下がる所は、
    //    塀の下の布石(腰の石)の見えで受ける ── 地面は盛りも削りもしない(unity-buke-yashiki/references/perimeter.md
    //    「塀は傾けない」・考証: 金剛寺の築地塀の段の妻と貝形【A】・登り塀は城の作法)。
    //    ⛔ それまでは地形なりに駒を弦へ張って傾け(StraightRunJoints)、斜面で笠がガタガタに上下した(施主 2026-09-28)。
    // 区切り方(施主裁定1=B → 施主裁定 2026-09-29 ③): 区間ごとに塀の座 W を**選び**、布石と根入れで区間の中の起伏を受ける。
    //    硬い条件: 区間の芯の地面の最も低い所まで布石が届く(W ≤ 最低 + 布石の丈 − DAN_STONE_EMBED)・最も高い所へ
    //    埋める深さ ≤ DAN_BURY_MAX(W ≥ 最高 − DAN_BURY_MAX)。急で最短の区間(1間)でも収まらない所だけ、埋めを深くして浮かせない。
    //    狙い(柔らかい・罰): 区間の数を少なく / **半端な段(DAN_STEP_MIN 未満)を作らない** / 段は DAN_STEP_MAX 以下 /
    //    段の高さを揃える(段の二乗を足す ── 同じ落ちを同じ数で割るなら等分が最小)/ 座は標準の根入れ(最高 − DAN_BURY)に近く /
    //    段を区画の角から DAN_CORNER_CLEAR 離す / **片側が平場(前庭など水平に均した面)に面する所に段を切らない**。
    //    ⛔ 段を「どこに置いても同じ値段」と数えると、同じ落ちの段が平場の前へ出た ── 山王社の前庭に面する観理院の西の塀に
    //    0.57m の段が 2 つ(2026-09-29 EDO-0477・施主裁定③「前庭に面する所は一続きに水平」)。段は斜面に面する所へ寄せる。
    //    ⛔ 2026-09-29 まで「区間の起伏 ≤ DAN_STEP(0.60)」を硬い条件にし、座を「最高 − DAN_BURY」に固定していた ──
    //    石垣の足元でわずかに下がる地面が 0.49・0.58 の半端な段を立て、前庭から段々に見えた(観理院の西・施主 2026-09-29
    //    「微妙な段差ができるのも気持ち悪い」)。布石(丈 1.3m)が受けられる起伏まで一区間にして、座を選んで段を揃える。
    // 当たる先: 類型の全区画の練塀(buildKakoi が辺の鎖ごとに DanPlan を引いて FenceRun へ渡す)。
    public const float DAN_STEP = 0.60f;          // (旧)段の目安[m]【施主裁定1=B】── いまは段の数の見積りの註にだけ使う
    public const float DAN_STEP_MIN = 0.70f;      // 半端な段の線[m] ── これ未満の段は作らない(狙い)【施主裁定 2026-09-29 ③「半端な段(0.5m 前後)0」】
                                                  // ⛔ 0.50 にすると 0.50・0.65 の段が残った(観理院の北の角)── 裁定図の段は 0.81・0.83
    public const float DAN_STEP_MAX = 1.00f;      // 段の上限[m](狙い)── 段が妻を大きく見せすぎない
    public const float DAN_MIN_SEC = 1.818f;      // 区間の最短 = 1間【施主裁定1=B】
    public const float DAN_MAX_SEC = 40f;         // 区間の最長[m](perimeter.md)
    public const float DAN_BURY = 0.10f;          // 塀の根入れ[m](標準)
    public const float DAN_BURY_MAX = 0.35f;      // 区間の最も高い地面へ塀の下端を埋めてよい深さ[m](硬い)── 塀の見えの丈 2.5m の 1 割半
    public const float DAN_STONE_EMBED = 0.05f;   // 布石の下端を地面へ入れる深さ[m](硬い)
    public const float DAN_GATE_SODE = 5.454f;    // 門の柱の外へ左右とも水平に出す塀の長さ[m] = 3間(硬い)【施主 2026-10-03 案A・長さは推定 P】
    public const float DAN_CORNER_CLEAR = 1.0f;   // 段を区画の角から離す[m](狙い)
    public const float DAN_FLAT_NEAR = 3.0f, DAN_FLAT_FAR = 5.0f; // 平場かを見る帯[m](塀の芯から片側。布石・法の肩の先)
    public const float DAN_FLAT_ALONG = 1.0f;     // 平場かを見る道のりの幅[m](節の前後)
    public const float DAN_FLAT_MARGIN = 3.0f;    // 段を平場の端から離す[m](狙い)── 平場の縁の手前に段が出て前庭から見えた(観理院 z863)
    public const float DAN_FLAT_TOL = 0.05f;      // 平場とみなす地面の高低[m](均した面の誤差)
    const float DAN_Q = 0.909f;                   // 区切りの刻み = 半間
    const float DAN_FLOAT_TOL = 0.01f;            // 段塀の下端の浮きの線[m] ── 超えれば布石。検査の「塀の下端の浮き」の線と同じ
    const float DAN_DS = 0.10f;                   // 地面の標本の刻み[m]
    const float DAN_WQ = 0.05f;                   // 座の候補の刻み[m]

    /// <summary>段塀の一区間(鎖の道のり a〜b・塀の座 W = 塀の下端の高さ)。</summary>
    public struct DanSec { public float a, b, W; }

    /// <summary>折れ線(区画の辺の鎖)に段塀の区切りと座を引く。道のりは折れ線の頭から。
    /// 動的計画(状態 = 区切りの節 × 座の候補)で「区間の数 + 段の二乗 + 半端な段・大きすぎる段・角の段・標準から外れた座の罰」
    /// を最小にする。硬い条件は冒頭の註(布石が届く・埋めが DAN_BURY_MAX 以内)。
    /// <para><paramref name="gates"/> = 門の口(鎖の道のり x=始め・y=終わり)。⭐ 門は**水平な区間の真ん中**に立てる(EDO-0514・施主 2026-10-03 案A)──
    /// 門の柱の外へ左右とも DAN_GATE_SODE(3間)は区切りを置かない(硬い)ので、門の左右の塀は門と同じ高さで同じ長さだけ出る。段はその外。
    /// 門の口の地面は塀が立たないので見ない。左右 3間 の起伏が布石と根入れで受けきれない坂は、浮かせず埋めを深くして ⚠ を刷る。
    /// ⛔ 2026-10-03 まで門を知らず、区切りが坂の高さだけで決まって門が平らな区間の片寄りに立った(樹下の表門・施主「アンバランス」)。
    /// ⛔ 同日の一つ目の直し「段を門の柱で切る」は退けた ── 門の左右で塀の高さが変わる作りは実例が無い(施主「見たことがない」)。
    /// 当たる先: 類型の練塀で門を持つ全区画。</para></summary>
    public static List<DanSec> DanPlan(IList<Vector2> chain, out string note, IList<Vector2> gates = null)
    {
        var segL = new List<float>(); float L = 0f;
        for (int i = 0; i + 1 < chain.Count; i++) { float l = Vector2.Distance(chain[i], chain[i + 1]); segL.Add(l); L += l; }
        var outp = new List<DanSec>(); note = "";
        if (L < 1e-3f) return outp;
        var sy = RunMeasureY(EdoAssets.Own.Dobei2mNunoishi); float stoneH = sy.hi - sy.lo;
        float reach = stoneH - DAN_STONE_EMBED;
        // 足跡の地面の標本 ── 芯と両脇(布石の実測の半厚)。塀と布石は区画の線を芯に据わる(ButtOnRun の latOff 0)ので、
        //    検査(RootToBed = 足跡の全部)と同じ幅を見る。⛔ 芯だけを見ると脇の低い地面で布石の下が 0.02〜0.04m 浮いた
        //    (観理院の西の崖の肩・2026-09-29 EDO-0477)。
        float half;
        {
            var bp = BodyAt(EdoAssets.Own.Dobei2mNunoishi, Vector3.zero, 0f, true);
            float zl = float.MaxValue, zh = float.MinValue; foreach (var q in bp) { zl = Mathf.Min(zl, q.z); zh = Mathf.Max(zh, q.z); }
            half = bp.Count > 0 ? (zh - zl) * 0.5f : 0f;
        }
        int ns = Mathf.Max(2, Mathf.CeilToInt(L / DAN_DS) + 1);
        var gsLo = new float[ns]; var gsHi = new float[ns]; var ss = new float[ns];
        for (int k = 0; k < ns; k++)
        {
            float s = Mathf.Min(L, k * DAN_DS); ss[k] = s;
            var p = ChainAt(chain, segL, s); var d = ChainDir(chain, segL, s); var nrm = new Vector2(-d.y, d.x);
            float lo = float.MaxValue, hi = float.MinValue;
            foreach (float o in new[] { 0f, half, -half })
            {
                var q = p + nrm * o; float g = Ground(q.x, q.y);
                if (!float.IsNaN(g)) { lo = Mathf.Min(lo, g); hi = Mathf.Max(hi, g); }
            }
            if (lo > hi) { lo = k > 0 ? gsLo[k - 1] : 0f; hi = k > 0 ? gsHi[k - 1] : 0f; }
            gsLo[k] = lo; gsHi[k] = hi;
        }
        // 区切りの節(半間)と角の道のり
        int N = Mathf.Max(1, Mathf.CeilToInt(L / DAN_Q - 1e-3f));
        var E = new float[N + 1]; for (int k = 0; k <= N; k++) E[k] = Mathf.Min(k * DAN_Q, L);
        var corners = new List<float>(); { float c = 0f; for (int i = 0; i + 1 < segL.Count; i++) { c += segL[i]; corners.Add(c); } }
        int qMin = Mathf.Max(1, Mathf.RoundToInt(DAN_MIN_SEC / DAN_Q)), qMax = Mathf.Max(qMin, Mathf.FloorToInt(DAN_MAX_SEC / DAN_Q));
        // 門の口(塀が立たない)── 地面を見ない・左右 DAN_GATE_SODE に区切りを置かない(EDO-0514)
        var gs = new List<Vector2>();
        if (gates != null) foreach (var g in gates) { float g0 = Mathf.Clamp(Mathf.Min(g.x, g.y), 0f, L), g1 = Mathf.Clamp(Mathf.Max(g.x, g.y), 0f, L); if (g1 - g0 > 1e-3f) gs.Add(new Vector2(g0, g1)); }
        Func<float, bool> inGate = sv => { foreach (var g in gs) if (sv > g.x + 1e-3f && sv < g.y - 1e-3f) return true; return false; };
        // 節の間ごとの地面の最低・最高(区間の範囲は節の間を足して引く)
        var nLo = new float[N]; var nHi = new float[N];
        for (int k = 0; k < N; k++)
        {
            float lo = float.MaxValue, hi = float.MinValue;
            for (int m = 0; m < ns; m++) if (ss[m] >= E[k] - 1e-4f && ss[m] <= E[k + 1] + 1e-4f && !inGate(ss[m])) { lo = Mathf.Min(lo, gsLo[m]); hi = Mathf.Max(hi, gsHi[m]); }
            nLo[k] = lo; nHi[k] = hi;
        }
        var nearCorner = new bool[N + 1];
        for (int k = 0; k <= N; k++) foreach (var cc in corners) if (Mathf.Abs(E[k] - cc) < DAN_CORNER_CLEAR) { nearCorner[k] = true; break; }
        // 門の左右 DAN_GATE_SODE の内には区切りを置かない(硬い・EDO-0514)
        var noCut = new bool[N + 1];
        for (int k = 1; k < N; k++) foreach (var g in gs) if (E[k] > g.x - DAN_GATE_SODE + 1e-3f && E[k] < g.y + DAN_GATE_SODE - 1e-3f) { noCut[k] = true; break; }
        // 片側が平場に面する節(その側の帯の地面が前後 DAN_FLAT_ALONG の間で DAN_FLAT_TOL 以内に揃う)と、そこから DAN_FLAT_MARGIN 内の節
        var flatAt = new bool[N + 1];
        for (int k = 0; k <= N; k++)
            foreach (float sd in new[] { 1f, -1f })
            {
                float lo = float.MaxValue, hi = float.MinValue; bool ok = true;
                foreach (float ds in new[] { -DAN_FLAT_ALONG, 0f, DAN_FLAT_ALONG })
                {
                    float s = Mathf.Clamp(E[k] + ds, 0f, L);
                    var p = ChainAt(chain, segL, s); var d = ChainDir(chain, segL, s); var nrm = new Vector2(-d.y, d.x) * sd;
                    foreach (float o in new[] { DAN_FLAT_NEAR, DAN_FLAT_FAR })
                    {
                        var q = p + nrm * o; float g = Ground(q.x, q.y);
                        if (float.IsNaN(g)) { ok = false; break; }
                        lo = Mathf.Min(lo, g); hi = Mathf.Max(hi, g);
                    }
                    if (!ok) break;
                }
                if (ok && hi - lo <= DAN_FLAT_TOL) { flatAt[k] = true; break; }
            }
        var nearFlat = new bool[N + 1];
        for (int k = 1; k < N; k++)
            for (int m = 0; m <= N; m++) if (flatAt[m] && Mathf.Abs(E[m] - E[k]) <= DAN_FLAT_MARGIN + 1e-3f) { nearFlat[k] = true; break; }
        // 状態: 節 j に終わる区間の座の候補
        var stW = new List<float>[N + 1]; var stC = new List<float>[N + 1]; var stPi = new List<int>[N + 1]; var stPk = new List<int>[N + 1];
        for (int k = 0; k <= N; k++) { stW[k] = new List<float>(); stC[k] = new List<float>(); stPi[k] = new List<int>(); stPk[k] = new List<int>(); }
        int forced = 0;
        for (int j = 1; j <= N; j++)
        {
            float lo = float.MaxValue, hi = float.MinValue;
            for (int i = j - 1; i >= Mathf.Max(0, j - qMax); i--)
            {
                lo = Mathf.Min(lo, nLo[i]); hi = Mathf.Max(hi, nHi[i]);
                int q = j - i;
                if (q < qMin && i != 0 && j != N) continue;
                if (i > 0 && stW[i].Count == 0) continue;
                if (i > 0 && noCut[i]) continue;                // 門の左右には区切りを置かない(硬い)
                bool gateSec = false;                            // 門の左右の帯をちょうど覆う区間 ── 坂でも退けず埋めを深くする
                foreach (var g in gs)
                    if (E[i] <= Mathf.Max(0f, g.x - DAN_GATE_SODE) + 1e-3f && E[j] >= Mathf.Min(L, g.y + DAN_GATE_SODE) - 1e-3f
                        && q <= Mathf.CeilToInt((g.y - g.x + 2f * DAN_GATE_SODE) / DAN_Q) + 2) { gateSec = true; break; }
                float wMin = hi - DAN_BURY_MAX, wMax = lo + reach, wStd = hi - DAN_BURY;
                var cands = new List<float>();
                if (wMin <= wMax)
                {
                    for (float w = Mathf.Ceil(wMin / DAN_WQ) * DAN_WQ; w <= wMax + 1e-4f; w += DAN_WQ) cands.Add(w);
                    if (wStd >= wMin && wStd <= wMax) cands.Add(wStd);
                    if (cands.Count == 0) cands.Add(wMax);
                }
                else if (q <= qMin || gateSec) cands.Add(wMax);   // 急で最短でも収まらない ── 浮かせず埋めを深くする(硬い条件の例外)
                else continue;
                foreach (var W in cands)
                {
                    float pen0 = 1f + 0.5f * Mathf.Abs(W - wStd) + (wMin > wMax ? 2f : 0f);
                    if (i == 0)
                    {
                        float c0 = pen0;
                        Push(stW[j], stC[j], stPi[j], stPk[j], W, c0, 0, -1);
                        continue;
                    }
                    int bestK = -1; float best = float.MaxValue;
                    for (int kk = 0; kk < stW[i].Count; kk++)
                    {
                        float d = Mathf.Abs(W - stW[i][kk]), pen = d * d;
                        if (d > 0.005f)
                        {
                            if (d < DAN_STEP_MIN - DAN_FLOAT_TOL) pen += 5f;
                            if (d > DAN_STEP_MAX) pen += 10f * (d - DAN_STEP_MAX) + 2f;
                            if (nearCorner[i]) pen += 30f;
                            if (nearFlat[i]) pen += 8f;
                        }
                        float c = stC[i][kk] + pen;
                        if (c < best) { best = c; bestK = kk; }
                    }
                    Push(stW[j], stC[j], stPi[j], stPk[j], W, best + pen0, i, bestK);
                }
            }
        }
        if (stW[N].Count == 0)
        {
            note = "⚠ 段塀の区切りが引けない ── 一区間で建てた";
            float lo0 = float.MaxValue, hi0 = float.MinValue; for (int k = 0; k < N; k++) { lo0 = Mathf.Min(lo0, nLo[k]); hi0 = Mathf.Max(hi0, nHi[k]); }
            outp.Add(new DanSec { a = 0f, b = L, W = Mathf.Min(hi0 - DAN_BURY, lo0 + reach) }); return outp;
        }
        {
            int kb = 0; for (int kk = 1; kk < stC[N].Count; kk++) if (stC[N][kk] < stC[N][kb]) kb = kk;
            int j = N, k = kb;
            while (j > 0)
            {
                int i = stPi[j][k], pk = stPk[j][k];
                outp.Insert(0, new DanSec { a = E[i], b = E[j], W = stW[j][k] });
                j = i; k = pk; if (j > 0 && k < 0) break;
            }
        }
        // 同じ座の隣り合う区間は一つに畳む(段 0 の区切りは建てる側で意味が無い)
        for (int k = outp.Count - 1; k > 0; k--)
            if (Mathf.Abs(outp[k].W - outp[k - 1].W) < 0.005f) { outp[k - 1] = new DanSec { a = outp[k - 1].a, b = outp[k].b, W = outp[k - 1].W }; outp.RemoveAt(k); }
        float mx = 0f, mnStep = float.MaxValue; int nStep = 0, nCorner = 0, nSmall = 0, nFlat = 0;
        for (int k = 0; k + 1 < outp.Count; k++)
        {
            float d = Mathf.Abs(outp[k + 1].W - outp[k].W); if (d > 1e-3f) { nStep++; mnStep = Mathf.Min(mnStep, d); if (d < DAN_STEP_MIN - DAN_FLOAT_TOL) nSmall++; if (nearFlat[Mathf.Clamp(Mathf.RoundToInt(outp[k].b / DAN_Q), 0, N)]) nFlat++; }
            mx = Mathf.Max(mx, d);
            foreach (var cc in corners) if (Mathf.Abs(outp[k].b - cc) < DAN_CORNER_CLEAR) { nCorner++; break; }
        }
        for (int k = 0; k < outp.Count; k++)
        {
            float lo = float.MaxValue, hi = float.MinValue;
            for (int m = 0; m < ns; m++) if (ss[m] >= outp[k].a - 1e-4f && ss[m] <= outp[k].b + 1e-4f && !inGate(ss[m])) { lo = Mathf.Min(lo, gsLo[m]); hi = Mathf.Max(hi, gsHi[m]); }
            if (outp[k].W < hi - DAN_BURY_MAX - 0.01f || outp[k].W > lo + reach + 0.01f) forced++;
        }
        note = string.Format("段塀 {0:F0}m を {1} 区間・段 {2}・段 {3:F2}〜{4:F2}m(半端な段の線 {5:F2}・上限 {6:F2}){7}{8}{9}{10}{11}", L, outp.Count, nStep,
                             nStep > 0 ? mnStep : 0f, mx, DAN_STEP_MIN, DAN_STEP_MAX,
                             nSmall > 0 ? string.Format("・⚠ 半端な段 {0}(狙い)", nSmall) : "",
                             nCorner > 0 ? string.Format("・⚠ 角から {0:F1}m 以内の段 {1}(狙い)", DAN_CORNER_CLEAR, nCorner) : "",
                             forced > 0 ? string.Format("・⚠ 布石と根入れで受けきれない急な区間 {0}(埋めを深くした)", forced) : "",
                             nFlat > 0 ? string.Format("・⚠ 平場に面する段 {0}(狙い)", nFlat) : "",
                             gs.Count > 0 ? string.Format("・門 {0} を水平な区間の中に置いた(左右 {1:F2}m・硬い)", gs.Count, DAN_GATE_SODE) : "");
        return outp;
    }

    /// <summary>DanPlan の状態を足す。同じ座(刻みの内)の候補が既にあれば安い方だけ残す。</summary>
    static void Push(List<float> W, List<float> C, List<int> Pi, List<int> Pk, float w, float c, int pi, int pk)
    {
        for (int k = 0; k < W.Count; k++)
            if (Mathf.Abs(W[k] - w) < 1e-3f) { if (c < C[k]) { C[k] = c; Pi[k] = pi; Pk[k] = pk; } return; }
        W.Add(w); C.Add(c); Pi.Add(pi); Pk.Add(pk);
    }

    static Vector2 ChainDir(IList<Vector2> chain, List<float> segL, float s)
    {
        for (int i = 0; i < segL.Count; i++)
        {
            if (s <= segL[i] || i == segL.Count - 1) return (chain[i + 1] - chain[i]).normalized;
            s -= segL[i];
        }
        return Vector2.right;
    }

    static Vector2 ChainAt(IList<Vector2> chain, List<float> segL, float s)
    {
        for (int i = 0; i < segL.Count; i++)
        {
            if (s <= segL[i] || i == segL.Count - 1) return chain[i] + (chain[i + 1] - chain[i]) * Mathf.Clamp01(segL[i] > 1e-6f ? s / segL[i] : 0f);
            s -= segL[i];
        }
        return chain[chain.Count - 1];
    }

    /// <summary>練塀を段塀で建てる。<paramref name="secs"/> は A からの道のりの区間(座 W)。駒は水平に据え(笠は区間ごとに水平)、
    /// 段の上手の端と開口の脇は妻を塞いだ駒(Dobei2mEnd)。駒の下の地面が座より下がる所は布石を据える(天端 = 据えた塀の下端を測って合わせる)。</summary>
    public static List<GameObject> NeribeiStepRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        IList<DanSec> secs, Vector2 gapC, float gapHalf, out string note)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float bodyLen = RunMeasure(EdoAssets.Own.Dobei2m).W;
        float stoneLen = RunMeasure(EdoAssets.Own.Dobei2mNunoishi).W;
        float stoneH = RunMeasureY(EdoAssets.Own.Dobei2mNunoishi).hi - RunMeasureY(EdoAssets.Own.Dobei2mNunoishi).lo;
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
        var inN = -outward.normalized;
        int idx = 0, nStone = 0; float worstShow = 0f, deepStone = 0f;
        foreach (var seg in segs)
        {
            if (seg[1] - seg[0] < bodyLen * 0.25f) continue;
            // 区間を開口で切る。端の短い切れ端(駒の 1/4 未満)は隣の区間へ寄せる。
            var sub = new List<Vector3>();   // (x0, x1, W)
            foreach (var d in secs)
            {
                float x0 = Mathf.Max(seg[0], d.a), x1 = Mathf.Min(seg[1], d.b);
                if (x1 - x0 > 1e-3f) sub.Add(new Vector3(x0, x1, d.W));
            }
            if (sub.Count == 0) continue;
            sub[0] = new Vector3(seg[0], sub[0].y, sub[0].z); sub[sub.Count - 1] = new Vector3(sub[sub.Count - 1].x, seg[1], sub[sub.Count - 1].z);
            for (int k = sub.Count - 1; k >= 0 && sub.Count > 1; k--)
            {
                if (sub[k].y - sub[k].x >= bodyLen * 0.25f) continue;
                if (k > 0) sub[k - 1] = new Vector3(sub[k - 1].x, sub[k].y, sub[k - 1].z);
                else sub[1] = new Vector3(sub[k].x, sub[1].y, sub[1].z);
                sub.RemoveAt(k);
            }
            bool gapLo = gapHalf > 0 && seg[0] > 0.01f, gapHi = gapHalf > 0 && seg[1] < len - 0.01f;
            bool chained = false; float prevEnd = 0f;
            for (int si = 0; si < sub.Count; si++)
            {
                float x0 = sub[si].x, x1 = sub[si].y, W = sub[si].z, L = x1 - x0;
                // 妻を塞ぐ端: 開口の脇・段の上手(隣の区間より高い側)
                bool capLo = (si == 0 && gapLo) || (si > 0 && W > sub[si - 1].z + 0.05f);
                bool capHi = (si == sub.Count - 1 && gapHi) || (si < sub.Count - 1 && W > sub[si + 1].z + 0.05f);
                int n = Mathf.Max(1, Mathf.RoundToInt(L / bodyLen));
                float pitch = L / n;
                for (int k = 0; k < n; k++)
                {
                    bool closeLo = k == 0 && capLo, closeHi = k == n - 1 && capHi && !(n == 1 && closeLo);
                    string path = (closeLo || closeHi) ? EdoAssets.Own.Dobei2mEnd : EdoAssets.Own.Dobei2m;
                    float sx = pitch / RunMeasure(path).W;
                    var go = Place(path, Vector3.zero, closeHi ? psi + 180f : psi, new Vector3(sx, 1f, 1f), parent, prefix + "_" + idx);
                    float startAbs = chained ? prevEnd : a0 + x0 + pitch * k;
                    float mn, mx;
                    ButtOnRun(go, A, dir, outward, 0f, startAbs, out mn, out mx);
                    prevEnd = mx; chained = true;
                    SeatBottom(go, W);
                    made.Add(go); idx++;
                    // 布石: 塀の下端の足跡を地面に当て(RootToBed ── 検査と同じ測り)、浮きが線 DAN_FLOAT_TOL を超えれば据える。
                    //    天端 = 据えた塀の下端(実測)。⛔ 2026-09-29 まで「芯と両面を 0.25m 刻み・端 5cm を除く・線 0.02」で測り、
                    //    検査(足跡の全部・線 0.01)と食い違って端の 1.3cm の浮きを残した(観理院 dobei_1_0・EDO-0477)。
                    var rootG = RootToBed(go, Ground, 0.05f);
                    if (float.IsNaN(rootG.hi) || rootG.hi <= DAN_FLOAT_TOL) continue;
                    float wb = RB(go).min.y, gmin = wb - rootG.hi;
                    var st = Place(EdoAssets.Own.Dobei2mNunoishi, Vector3.zero, psi, new Vector3((mx - mn) / stoneLen, 1f, 1f), parent, prefix + "_" + (idx - 1) + "_ishi");
                    float smn, smx;
                    ButtOnRun(st, A, dir, outward, 0f, mn, out smn, out smx);
                    var srb = RB(st); st.transform.position += new Vector3(0f, wb - srb.max.y, 0f);
                    made.Add(st); nStone++;
                    worstShow = Mathf.Max(worstShow, wb - gmin);
                    if (wb - gmin > stoneH - 0.05f) deepStone = Mathf.Max(deepStone, wb - gmin);
                }
            }
        }
        note = string.Format("布石 {0} 駒(見え最大 {1:F2}m){2}", nStone, worstShow,
                             deepStone > 0f ? string.Format("・⛔ 布石の丈 {0:F2} より地面が下がる所 {1:F2}m(石の下が浮く)", stoneH, deepStone) : "");
        return made;
    }

    // ---------- 板塀/穂垣 run — 片面ポリゴンなので表裏の対で置く ----------
    // asset: 5枚スパンOBJ。走りは DobeiRun と同じ実寸カーソル。パネル毎に接地。
    /// <remarks>据えは DobeiRun と同じ — **触れている箇所**を測る(規則21)。失敗したときだけ bounds の底(EDO-0342)。
    /// <para><paramref name="pair"/>=false / <paramref name="unitScale"/>=1 は **実ジオメトリの両面もの・実寸FBX**用
    /// (例: 竹矢来 <see cref="EdoAssets.Own.Typ.Takeyarai"/>)。既定(true / ES)は今までどおり
    /// 片面ポリゴンの ES 倍 obj(穂垣・板塀)— 既存の呼び手はバイト等価で不変(EDO-0363)。</para></remarks>
    public static List<GameObject> PanelRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        string assetPath, Vector2 gapC, float gapHalf, bool pair = true, float unitScale = ES, IList<GameObject> beds = null,
        Func<float, float, float> bedAt = null, string splitPost = null, string splitBoard = null)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        // ⭐ 開口(門)は**辺を開口の縁で区切ってから**区間ごとに張る(2026-09-27・EDO-0477 P2。DobeiRun の EDO-0474 と同じ型)。
        //   ⛔ それまでは辺全体を等割りし開口に掛かる駒を丸ごと抜いていた — 門の脇に最大で駒 1 枚ぶんの隙が空く。
        //   当たる先: 開口を渡す呼び手(類型の竹矢来)。開口を渡さない呼び手(山王の板塀)は不変。
        if (gapHalf > 0)
        {
            float gT = Vector2.Dot(gapC - A, dir);
            if (gT - gapHalf > DOBEI_MIN_PIECE)
                made.AddRange(PanelRun(parent, A, A + dir * Mathf.Min(gT - gapHalf, len), outward, prefix, assetPath, Vector2.zero, -1f,
                                       pair, unitScale, beds, bedAt, splitPost, splitBoard));
            if (gT + gapHalf < len - DOBEI_MIN_PIECE)
                made.AddRange(PanelRun(parent, A + dir * Mathf.Max(gT + gapHalf, 0f), B, outward, prefix + "_g", assetPath, Vector2.zero, -1f,
                                       pair, unitScale, beds, bedAt, splitPost, splitBoard));
            return made;
        }
        bool fits = true;
        // スパン実測(unitScale基準・既定はES)
        float spanLocal = RunMeasure(assetPath).W;
        float spanES = spanLocal * unitScale;
        if (spanES < 0.5f) spanES = 7.49f;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / (spanES - 0.15f)));
        // ⭐ 床の起伏で割る(bedAt を渡した run・2026-09-26・EDO-0437 第5巡): 駒ごとに足の線の床の高さから最小二乗の弦を引き、
        //   弦からの外れの幅(上 + 下)が根入れ 0.10 を超える駒があれば、駒の数を増やす(硬い条件: 足の浮き 0 ── 弦に張って触れる所で
        //   据え、根入れだけ沈めたとき、浮きは 外れの幅 − 根入れ)。下限の長さ = 部材の長さの 0.4(柱の間が詰まり過ぎない)。
        //   割っても収まらない駒は ⚠(呼び手が刷る)── 床の落ち(法の縁・袖の際)は割り方でなく走りの端の決め方の話。
        if (bedAt != null)
        {
            int nMax = Mathf.Max(n, Mathf.FloorToInt(len / (spanES * 0.4f)));
            for (int nn = n; nn <= nMax; nn++)
            {
                n = nn; float pt = len / nn; bool ok = true;
                for (int k = 0; k < nn && ok; k++)
                {
                    double qx = 0, qy = 0, qxx = 0, qxy = 0; int cnt = 0; var ys = new List<Vector2>();
                    for (float u = 0.05f; u <= pt - 0.05f + 1e-4f; u += 0.1f)
                    {
                        // ⭐ 足の幅(表裏の対の奥行 0.12 + 柱の厚み)の床の最も高い所で測る(第6巡)── 芯の一本だけで測ると、法肩の横の勾配で
                        //   柱の足が 0.10 浮いた(前庭の南の板塀 `Ita_ZSE`: 芯の外れ 0.10 以内で 1 枚と読んだが、柱の足の外れは 0.20)。
                        //   柱が触れるのは足の下の最も高い所 ⇒ 浮きの物差しは足の幅の最大。
                        Vector2 q0 = A + dir * (pt * k + u); float y = float.NaN;
                        foreach (float lat in new[] { 0.06f, 0f, -0.06f, -0.12f, -0.18f })
                        { Vector2 q = q0 + outward.normalized * lat; float yy = bedAt(q.x, q.y); if (!float.IsNaN(yy) && (float.IsNaN(y) || yy > y)) y = yy; }
                        if (float.IsNaN(y)) continue;
                        qx += u; qy += y; qxx += u * u; qxy += u * y; cnt++; ys.Add(new Vector2(u, y));
                    }
                    double den = cnt * qxx - qx * qx; if (cnt < 3 || Math.Abs(den) < 1e-9) continue;
                    double sl = (cnt * qxy - qx * qy) / den, ic = (qy - sl * qx) / cnt;
                    float lo = float.MaxValue, hi = float.MinValue;
                    foreach (var v in ys) { float r = v.y - (float)(ic + sl * v.x); lo = Mathf.Min(lo, r); hi = Mathf.Max(hi, r); }
                    if (hi - lo > 0.10f) ok = false;
                }
                fits = ok;
                if (ok) break;
            }
            // ⭐ 割っても足の床の外れが根入れを超える run は、柱と板を分けた組で張る(2026-09-26・EDO-0437 第7巡)──
            //   柱を1本ずつ床に据え、板を両隣の柱の間に掛ける(PostBoardRun)。当たる先: bedAt を渡す板塀の run のうち、一体の駒では
            //   柱の足が浮く・埋まる所すべて(山王 前庭の南の板塀 `Ita_ZSE`)。組を渡さない呼び手は従来どおり(割った一体の駒で ⚠)。
            if (!fits && splitPost != null && splitBoard != null)
                return PostBoardRun(parent, A, B, outward, prefix, splitPost, splitBoard, bedAt, 0.10f, pair);
        }
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
            for (int side = 0; side < (pair ? 2 : 1); side++)
            {
                float ry = side == 0 ? psi : psi + 180f;
                var go = Place(assetPath, Vector3.zero, ry, new Vector3(sx, unitScale, unitScale), parent,
                    prefix + "_" + k + (side == 0 ? "f" : "b"));
                float mn, mx;
                ButtOnRun(go, A, dir, outward, side == 0 ? 0.0f : -0.12f, startAbs, out mn, out mx);
                if (side == 0) { prevEnd = mx; chained = true; }
                if (bedAt != null) SeatPanelOnBed(go, A, dir, mn, mx, bedAt, 0.10f);
                else { try { SeatOnGround(go, 0.10f, 600); } catch (Exception) { SeatBottom(go, baseY - 0.10f); } }
                // ⭐ 足の下に土留め・石垣の駒が居れば、その天端の**触れている箇所**に載せる(2026-09-26・EDO-0437 第3巡)──
                //   地面(土留めの天端の下へ納めた皮)で据えると足が天端の石の中へ 0.24m 沈み、石が板へ 0.6m 入った(山王 前庭の北 Ita_ZN・Ita_ZNE)。
                //   上げるだけ(地面へは沈めたまま)。当たる先: 板塀・穂垣の run が土留め・石垣の天端の上を通る所すべて。
                if (beds != null) RestOnBeds(go, beds);
                made.Add(go);
            }
        }
        return made;
    }

    /// <summary>**柱と板を分けた組で板塀の run を張る**(2026-09-26・EDO-0437 第7巡)。一体の駒(柱5本)を傾けても柱の足の床の外れが
    /// 根入れを超える run(法肩の折れ・<see cref="PanelRun"/> の割りで収まらない所)に使う。
    /// <para>1. 端の柱は外形(根元の台を含む)の端を run の端 A/B に突き付ける。間の柱は柱身の芯を等分(柱間 ≈ 板の幅 + 柱身の幅・どちらも実メッシュで測る)。
    /// 2. 柱は1本ずつ**根元の台の底**(柱身の断面の外へ出る頂点の最下)を、台の足跡の下の床の最も高い所へ合わせ、根入れ <paramref name="root"/> だけ沈める
    /// (地中の継ぎ足しが根入れの取り代なので、足跡の起伏が 継ぎ足し − 根入れ までは浮かない)。
    /// 3. 板は水平のまま両隣の柱身の面から面へ掛ける(走りの向きだけ伸縮)。高さは板の足跡の下の床の最も高い所 + 元の組の離れ
    /// (板の下端 − 台の底 − 根入れ・実メッシュで測る)── 板の下端を床に埋めない。傾けない(端の小口が柱の面から開かない)。
    /// ⛔ 基準点で位置を決めない ── 走りは柱身の断面・外形の射影、高さは台の底と板の下端の頂点で測る(規則21)。
    /// 当たる先: <see cref="PanelRun"/> に組を渡した板塀の run のうち、一体の駒で足が浮く所すべて。</para></summary>
    public static List<GameObject> PostBoardRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        string postPath, string boardPath, Func<float, float, float> bedAt, float root, bool pair = true)
    {
        var made = new List<GameObject>();
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        float a0 = Vector2.Dot(A, dir);
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        float boardW = RunMeasure(boardPath).W;
        // 元の組の離れ = 板の下端 − 台の底(どちらも回さず置いた実メッシュで測る)
        float boardLo = RunMeasureY(boardPath).lo;
        float taiLoLocal, bodyHalfLocal;
        {
            var pr = Place(postPath, Vector3.zero, 0f, Vector3.one, parent, "_probe");
            var sec = MidSection(pr); float bx0 = float.MaxValue, bx1 = float.MinValue;
            foreach (var w in sec) { bx0 = Mathf.Min(bx0, w.x); bx1 = Mathf.Max(bx1, w.x); }
            bodyHalfLocal = (bx1 - bx0) * 0.5f; float bcx = (bx0 + bx1) * 0.5f;
            taiLoLocal = float.MaxValue;
            foreach (var mf in pr.GetComponentsInChildren<MeshFilter>())
                foreach (var v in mf.sharedMesh.vertices)
                { var l = pr.transform.InverseTransformPoint(mf.transform.TransformPoint(v)); if (Mathf.Abs(l.x - bcx) > bodyHalfLocal + 0.005f) taiLoLocal = Mathf.Min(taiLoLocal, l.y); }
            UnityEngine.Object.DestroyImmediate(pr);
        }
        float clear = boardLo - taiLoLocal - root;
        for (int side = 0; side < (pair ? 2 : 1); side++)
        {
            float ry = side == 0 ? psi : psi + 180f; float latOff = side == 0 ? 0f : -0.12f; string sfx = side == 0 ? "f" : "b";
            // 柱の外形と柱身の芯の関係を、この向きで一本置いて測る
            var probe = Place(postPath, Vector3.zero, ry, Vector3.one, parent, "_probe");
            float fmn, fmx; ButtOnRun(probe, A, dir, outward, latOff, a0, out fmn, out fmx);
            float bmn = float.MaxValue, bmx = float.MinValue;
            foreach (var w in MidSection(probe)) { float q = w.x * dir.x + w.z * dir.y; bmn = Mathf.Min(bmn, q); bmx = Mathf.Max(bmx, q); }   // MidSection は世界座標
            UnityEngine.Object.DestroyImmediate(probe);
            float bc = (bmn + bmx) * 0.5f, bodyW = bmx - bmn, fl = fmn - bc, fh = fmx - bc;
            float c0 = a0 - fl, cn = a0 + len - fh, span = cn - c0;
            int nb = Mathf.Max(1, Mathf.RoundToInt(span / (boardW + bodyW)));
            float p = span / nb;
            for (int k = 0; k <= nb; k++)
            {
                var go = Place(postPath, Vector3.zero, ry, Vector3.one, parent, prefix + "_h" + k + sfx);
                float mn, mx; ButtOnRun(go, A, dir, outward, latOff, c0 + p * k + fl, out mn, out mx);
                // 台の底と足跡(柱身の断面の外へ出る頂点)
                float taiLo = float.MaxValue, fl2 = float.NaN; var sec = MidSection(go);
                float s0 = float.MaxValue, s1 = float.MinValue;
                foreach (var w in sec) { float q = w.x * dir.x + w.z * dir.y; s0 = Mathf.Min(s0, q); s1 = Mathf.Max(s1, q); }
                var foot = new List<Vector3>();
                foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
                    foreach (var v in mf.sharedMesh.vertices)
                    {
                        var w = mf.transform.TransformPoint(v); float q = w.x * dir.x + w.z * dir.y;
                        if (q < s0 - 0.005f || q > s1 + 0.005f) { foot.Add(w); taiLo = Mathf.Min(taiLo, w.y); }
                    }
                foreach (var w in foot) { float b = bedAt(w.x, w.z); if (!float.IsNaN(b) && (float.IsNaN(fl2) || b > fl2)) fl2 = b; }
                if (float.IsNaN(fl2) || taiLo == float.MaxValue) { try { SeatOnGround(go, root, 600); } catch (Exception) { } }
                else go.transform.position += new Vector3(0f, fl2 - root - taiLo, 0f);
                made.Add(go);
            }
            for (int k = 0; k < nb; k++)
            {
                float f0 = c0 + p * k + bodyW * 0.5f, f1 = c0 + p * (k + 1) - bodyW * 0.5f;
                var go = Place(boardPath, Vector3.zero, ry, new Vector3((f1 - f0) / boardW, 1f, 1f), parent, prefix + "_i" + k + sfx);
                float mn, mx; ButtOnRun(go, A, dir, outward, latOff, f0, out mn, out mx);
                // 板の足跡の下の床の最も高い所(走りに沿って 0.1m ごと・板の厚みの両面)
                var rb = RB(go); Vector2 cen = new Vector2(rb.center.x, rb.center.z); Vector2 nrm = new Vector2(-dir.y, dir.x);
                float lat = Vector2.Dot(cen - A, nrm), th = Mathf.Abs(rb.extents.x * nrm.x) + Mathf.Abs(rb.extents.z * nrm.y);
                float fmax = float.NaN;
                for (float u = mn; u <= mx + 1e-4f; u += 0.1f)
                    foreach (float dl in new[] { -th, 0f, th })
                    { Vector2 q = A + dir * (Mathf.Min(u, mx) - a0) + nrm * (lat + dl); float b = bedAt(q.x, q.y); if (!float.IsNaN(b) && (float.IsNaN(fmax) || b > fmax)) fmax = b; }
                if (!float.IsNaN(fmax)) go.transform.position += new Vector3(0f, fmax + clear - rb.min.y, 0f);
                made.Add(go);
            }
        }
        return made;
    }

    /// <summary>**光付け(削り合わせ)の印** = 部材の局所 y ≤ これ の頂点(<see cref="EdoAssets.Own.ItabeiJifuku"/>・<see cref="EdoAssets.Own.ItabeiHashiraHk"/> の下端の格子)。</summary>
    public const float SCRIBE_MARK = -0.599f;
    /// <summary>削りは部材の上端の手前これだけで止める(面が裏返らない)。</summary>
    public const float SCRIBE_TOP_STOP = 0.02f;
    /// <summary>光付けの結果(床との隙の実測)。</summary>
    public struct Scribe
    {
        /// <summary>削った頂点の数・床が代より深く届かなかった頂点の数(⚠ 浮く)。</summary>
        public int moved, shortN;
        /// <summary>当たりの標本の数・跨ぎ(床が NaN ── 目地の上)で測らなかった標本の数・下端を割り足した辺の数(<see cref="SplitEdges"/> ── 隙が狙いを超えた所だけ)。</summary>
        public int atariN, spanN, refined;
        /// <summary>下端の線 − 床(標本ごと)の最小・最大[m]。最小 &lt; 0 = 床へ入る・最大 &gt; 0 = 浮く(野面の目地の際は目地の底との差)。</summary>
        public float lo, hi;
        /// <summary>最大の隙の点。</summary>
        public Vector3 hiAt;
    }

    /// <summary>床の引きを升 <paramref name="cell"/> で覚える(同じ升は一度だけ引く・升の中の点は升の芯の値)。光付けの標本は駒ごとに万を超え、
    /// 野面の相手(<see cref="AtariBed"/>)は一点に 17 本の縦線を引くので、覚えないと 1 run に 10 分を超えた(2026-09-27 実測)。</summary>
    public static Func<float, float, float> MemoBed(Func<float, float, float> bedAt, float cell)
    {
        var memo = new Dictionary<long, float>();
        return (x, z) =>
        {
            int i = Mathf.RoundToInt(x / cell), j = Mathf.RoundToInt(z / cell); long k = ((long)i << 32) ^ (uint)j;
            float v; if (!memo.TryGetValue(k, out v)) { v = bedAt(i * cell, j * cell); memo[k] = v; } return v;
        };
    }

    /// <summary>光付けの狙い[m]: 削った後の下端と当たりの隙がこれを超える三角形だけ、最も長い辺を割って削り直す(合格線 ±0.01 の手前)。
    /// 割る辺はこれより短くしない(<see cref="SCRIBE_REFINE_MIN"/> の 2 倍未満の辺は割らない)・削り直しは <see cref="SCRIBE_REFINE_PASSES"/> 回まで。</summary>
    public const float SCRIBE_GAP_TARGET = 0.008f, SCRIBE_REFINE_MIN = 0.003f;
    public const int SCRIBE_REFINE_PASSES = 14;
    static long ScribePK(Vector3 p) { return ((long)Mathf.RoundToInt(p.x * 20000f) * 73856093L) ^ ((long)Mathf.RoundToInt(p.y * 20000f) * 19349663L) ^ ((long)Mathf.RoundToInt(p.z * 20000f) * 83492791L); }
    static long ScribeEK(long x, long y) { if (x > y) { var z = x; x = y; y = z; } return x * 1000003L ^ y; }
    /// <summary>**辺を半分に割る**(光付けの割り足し・2026-09-27 EDO-0437)。<paramref name="want"/> = 割る辺(両端の**メッシュの座標の位置**の鍵
    /// <see cref="ScribeEK"/>)。同じ位置の辺を持つ全ての三角形(全サブメッシュ・見え面の下の縁も)で一緒に割る ⇒ 継ぎ目に口(T 字の割れ)を開けない。
    /// 一つの三角形は一度に一辺だけ(残りは次の削り直しで拾う)。属性(法線・uv・uv2)は両端の中点。返り値 = 割った辺の数。</summary>
    public static int SplitEdges(Mesh m, HashSet<long> want)
    {
        var V = new List<Vector3>(m.vertices); var Nn = new List<Vector3>(m.normals);
        var U = new List<Vector2>(m.uv); var U2 = new List<Vector2>(m.uv2);
        bool hasN = Nn.Count == V.Count, hasU = U.Count == V.Count, hasU2 = U2.Count == V.Count;
        int sub = m.subMeshCount; var S = new List<int>[sub]; for (int i = 0; i < sub; i++) S[i] = new List<int>(m.GetTriangles(i));
        var triEdges = new Dictionary<long, List<long>>();   // 辺 → 三角形(si<<32|t)
        for (int si = 0; si < sub; si++)
            for (int t = 0; t + 2 < S[si].Count; t += 3)
                for (int e = 0; e < 3; e++)
                {
                    long ek = ScribeEK(ScribePK(V[S[si][t + e]]), ScribePK(V[S[si][t + (e + 1) % 3]]));
                    if (!want.Contains(ek)) continue;
                    List<long> l; if (!triEdges.TryGetValue(ek, out l)) { l = new List<long>(); triEdges[ek] = l; } l.Add(((long)si << 32) | (uint)t);
                }
        var busy = new HashSet<long>(); var take = new Dictionary<long, long>(); int total = 0;
        foreach (var kv in triEdges)
        {
            bool ok = true; foreach (var tt in kv.Value) if (busy.Contains(tt)) { ok = false; break; }
            if (!ok) continue; foreach (var tt in kv.Value) { busy.Add(tt); take[tt] = kv.Key; }
            total++;
        }
        if (total == 0) return 0;
        var mid = new Dictionary<long, int>();
        Func<int, int, int> Mid = (i0, i1) =>
        {
            long k = i0 < i1 ? ((long)i0 << 32) | (uint)i1 : ((long)i1 << 32) | (uint)i0; int r;
            if (mid.TryGetValue(k, out r)) return r;
            r = V.Count; V.Add((V[i0] + V[i1]) * 0.5f);
            if (hasN) Nn.Add((Nn[i0] + Nn[i1]).normalized); if (hasU) U.Add((U[i0] + U[i1]) * 0.5f); if (hasU2) U2.Add((U2[i0] + U2[i1]) * 0.5f);
            mid[k] = r; return r;
        };
        for (int si = 0; si < sub; si++)
        {
            var tl = S[si]; var outL = new List<int>(tl.Count + 64);
            for (int t = 0; t + 2 < tl.Count; t += 3)
            {
                long tk = ((long)si << 32) | (uint)t; long ek;
                if (!take.TryGetValue(tk, out ek)) { outL.Add(tl[t]); outL.Add(tl[t + 1]); outL.Add(tl[t + 2]); continue; }
                int e = 0; for (; e < 3; e++) if (ScribeEK(ScribePK(V[tl[t + e]]), ScribePK(V[tl[t + (e + 1) % 3]])) == ek) break;
                int i0 = tl[t + e], i1 = tl[t + (e + 1) % 3], i2 = tl[t + (e + 2) % 3], mm = Mid(i0, i1);
                outL.Add(i0); outL.Add(mm); outL.Add(i2); outL.Add(mm); outL.Add(i1); outL.Add(i2);
            }
            S[si] = outL;
        }
        m.indexFormat = V.Count > 65000 ? UnityEngine.Rendering.IndexFormat.UInt32 : m.indexFormat;
        m.SetVertices(V); if (hasN) m.SetNormals(Nn); if (hasU) m.SetUVs(0, U); if (hasU2) m.SetUVs(1, U2);
        for (int si = 0; si < sub; si++) m.SetTriangles(S[si], si);
        return total;
    }

    /// <summary>**部材の下端を床へ光付けする**(削り合わせ・2026-09-27 EDO-0437 施主裁定 案A)。部材の局所 y ≤ <see cref="SCRIBE_MARK"/> の頂点
    /// (下端の格子)を、その下の床 <paramref name="bedAt"/>(世界の x,z → 高さ)へ上げる。手本は `Tools/Blender/build_itabei_jifuku.py` の scribe()。
    /// <para>1. 削る頂点を**格子点**(局所 x,z が同じ ── 面ごとに割れた頂点は一緒に動かす)にまとめ、下端の面(3 頂点とも格子点の三角形)を集める。
    /// 2. 三角形の中に <paramref name="step"/> 刻みの標本を取り、それぞれの床の高さを引く(**標本は部材の足跡の中だけ** ── 足跡の外の高い床で持ち上げない)。
    /// 3. 格子点の高さ = その点の床から始め、三角形の中で下端の面が床より下になる標本があれば、重みの大きい頂点から上げる
    /// (上げは周りの三角形の床の最大まで)。**走りと厚みの両方向で**食い込み 0 にする。
    /// 4. 上げは部材の上端 − <see cref="SCRIBE_TOP_STOP"/> で止める。床が代(下端)より深い格子点は動かさない(⚠ 浮き ── shortN)。
    /// 5. uv += uv2·Δy で木理を直し、uv2 を消し、<see cref="EdoSolidMesh.Save"/> で資産にして差し替える。</para>
    /// ⭐ **当たりの作法**(docs/oki-kata.md §0a・2026-09-27 施主): <paramref name="bedAt"/> は**接すると決めた相手の面**だけを返す(<see cref="AtariBed"/>)。
    /// NaN の所は**跨ぎ**(目地の上)── 標本は据えにも測りにも使わず(<see cref="Scribe.spanN"/>)、跨ぎの格子点は周りの当たりの格子点から均して
    /// まっすぐ渡す。返る lo/hi は**当たりの標本だけ**の実測。
    /// ⚠ 旧(2026-09-27 前半)は厚みの列ごとに窓 [z − 列の間隔, z + 列の間隔] の床の**最大**で列を上げていた ⇒ 厚みの向きに傾いた床では
    /// 勾配 × 0.037 だけ浮き(法肩の柱 +0.016)、石の天端の目地が厚みの途中に掛かると隣の列との間の面が天端へ 0.16 食い込んだ(前庭の板塀 `Ita_ZN`)。
    /// ⛔ 基準点で高さを決めない ── 下端は床の標本(触れている箇所)で決まる。⛔ 部材を傾けない(y 軸は世界の上のまま)。
    /// 当たる先: 光付けの代を持つ部材の全て(板塀の地覆・柱 ── 山王 前庭の板塀 `Ita_Z*`・`Ita_Niou_N`、以後の地覆の在る板塀・柵)。</summary>
    public static Scribe ScribeToBed(GameObject go, Func<float, float, float> bedAt, string meshName, float step = 0.0025f)
    {
        var res = new Scribe { lo = float.NaN, hi = float.NaN };
        var mf = go.GetComponentInChildren<MeshFilter>(); if (mf == null || mf.sharedMesh == null) return res;
        var m = UnityEngine.Object.Instantiate(mf.sharedMesh);
        Transform gt = go.transform, mt = mf.transform;
        int refined = 0;
        // 削っては隙を測り、狙い(SCRIBE_GAP_TARGET)を超える三角形の最も長い辺だけ割って、元の形から削り直す ⇒ 点は隙の出る所にだけ増える(施主「点数は出来るかぎり少なく」)
        for (int pass = 0; ; pass++)
        {
        res = new Scribe { lo = float.NaN, hi = float.NaN, refined = refined };
        var vs = m.vertices; var uv = m.uv; var uv2 = m.uv2; var tris = m.triangles;
        var L = new Vector3[vs.Length];                  // 部材(go)の局所
        float ytop = float.MinValue;
        for (int i = 0; i < vs.Length; i++) { L[i] = gt.InverseTransformPoint(mt.TransformPoint(vs[i])); ytop = Mathf.Max(ytop, L[i].y); }
        // 格子点(局所 x,z)→ 同じ位置の頂点
        var nodeOf = new int[vs.Length]; var key = new Dictionary<long, int>();
        var nX = new List<float>(); var nZ = new List<float>(); var nH0 = new List<float>(); var nV = new List<List<int>>();
        for (int i = 0; i < vs.Length; i++)
        {
            nodeOf[i] = -1; if (L[i].y > SCRIBE_MARK) continue;
            long k = ((long)Mathf.RoundToInt(L[i].x * 10000f) << 32) ^ (uint)Mathf.RoundToInt(L[i].z * 10000f);
            int n; if (!key.TryGetValue(k, out n)) { n = nX.Count; key[k] = n; nX.Add(L[i].x); nZ.Add(L[i].z); nH0.Add(L[i].y); nV.Add(new List<int>()); }
            nV[n].Add(i); nodeOf[i] = n;
        }
        int N = nX.Count;
        if (N == 0) { UnityEngine.Object.DestroyImmediate(m); return res; }
        // 床(局所 y)── 世界の x,z の床の高さを局所へ(y 軸は世界の上のまま)
        Func<float, float, float> BedL = (lx, lz) =>
        {
            var w = gt.TransformPoint(new Vector3(lx, 0f, lz)); float b = bedAt(w.x, w.z);
            return float.IsNaN(b) ? float.NaN : gt.InverseTransformPoint(new Vector3(w.x, b, w.z)).y;
        };
        // 下端の面(3 頂点とも格子点・足跡に面積の在るもの)と、その中の標本
        var seen = new HashSet<long>(); var T = new List<int[]>();
        var sTri = new List<int>(); var sW = new List<Vector3>(); var sB = new List<float>(); var sP = new List<Vector2>();
        float sxw = (gt.TransformVector(Vector3.right)).magnitude, szw = (gt.TransformVector(Vector3.forward)).magnitude;
        for (int t = 0; t + 2 < tris.Length; t += 3)
        {
            int a = nodeOf[tris[t]], b = nodeOf[tris[t + 1]], c = nodeOf[tris[t + 2]];
            if (a < 0 || b < 0 || c < 0 || a == b || b == c || a == c) continue;
            int p0 = Mathf.Min(a, Mathf.Min(b, c)), p2 = Mathf.Max(a, Mathf.Max(b, c)), p1 = a + b + c - p0 - p2;
            long tk = ((long)p0 * N + p1) * N + p2; if (!seen.Add(tk)) continue;
            Vector2 A = new Vector2(nX[a] * sxw, nZ[a] * szw), B = new Vector2(nX[b] * sxw, nZ[b] * szw), C = new Vector2(nX[c] * sxw, nZ[c] * szw);
            float area = Mathf.Abs((B.x - A.x) * (C.y - A.y) - (C.x - A.x) * (B.y - A.y)) * 0.5f; if (area < 1e-9f) continue;
            int ti = T.Count; T.Add(new[] { a, b, c });
            float el = Mathf.Max((B - A).magnitude, Mathf.Max((C - B).magnitude, (A - C).magnitude));
            int ns = Mathf.Max(1, Mathf.CeilToInt(el / step));
            for (int i = 0; i <= ns; i++)
                for (int j = 0; j <= ns - i; j++)
                {
                    float w0 = (float)i / ns, w1 = (float)j / ns, w2 = 1f - w0 - w1;
                    float lx = nX[a] * w0 + nX[b] * w1 + nX[c] * w2, lz = nZ[a] * w0 + nZ[b] * w1 + nZ[c] * w2;
                    float bl = BedL(lx, lz); if (float.IsNaN(bl)) { res.spanN++; continue; }   // 跨ぎ(当たりの相手が無い)は据えにも測りにも使わない
                    sTri.Add(ti); sW.Add(new Vector3(w0, w1, w2)); sB.Add(bl); sP.Add(new Vector2(lx, lz));
                }
        }
        // 格子点の高さ = その点の床から。上げの上限 = 周りの三角形の床の最大
        var h = new float[N]; var cap = new float[N];
        var span = new bool[N]; int nSpan = 0;
        for (int n = 0; n < N; n++) { float b = BedL(nX[n], nZ[n]); span[n] = float.IsNaN(b); if (span[n]) nSpan++; h[n] = span[n] ? nH0[n] : b; cap[n] = h[n]; }
        var tS0 = new int[T.Count]; var tS1 = new int[T.Count];
        for (int s = 0; s < sTri.Count; s++)
        {
            var tr = T[sTri[s]]; for (int q = 0; q < 3; q++) cap[tr[q]] = Mathf.Max(cap[tr[q]], sB[s]);
            if (s == 0 || sTri[s] != sTri[s - 1]) tS0[sTri[s]] = s; tS1[sTri[s]] = s + 1;
        }
        // 跨ぎの格子点(目地の上)は床が無い ── 周りの三角形の当たりの標本(石の肩)の**最も低い床**から始める(上げの上限は周りの床の最大 = 他の格子点と同じ)。
        //   周りに標本の無い点(目地の真ん中)は、後で周りの格子点から均して渡す ⇒ 下端は石の肩まで沿い、目地の上はまっすぐ(大工の光付けと同じ)
        var spanLo = new float[N]; for (int n = 0; n < N; n++) spanLo[n] = float.NaN;
        for (int s = 0; s < sTri.Count; s++) { var tr = T[sTri[s]]; for (int q = 0; q < 3; q++) { int n = tr[q]; if (span[n] && (float.IsNaN(spanLo[n]) || sB[s] < spanLo[n])) spanLo[n] = sB[s]; } }
        for (int n = 0; n < N; n++) if (span[n] && !float.IsNaN(spanLo[n])) h[n] = spanLo[n];
        for (int it = 0; it < 400; it++)
        {
            bool changed = false;
            for (int ti = 0; ti < T.Count; ti++)
            {
                var tr = T[ti]; float worst = 1e-6f; Vector3 ww = Vector3.zero;
                for (int s = tS0[ti]; s < tS1[ti]; s++)
                {
                    var w = sW[s]; float d = sB[s] - (h[tr[0]] * w.x + h[tr[1]] * w.y + h[tr[2]] * w.z);
                    if (d > worst) { worst = d; ww = w; }
                }
                if (worst <= 1e-6f) continue;
                // 重みの大きい頂点から上げる(上限まで・残りを次へ)
                var ord = new[] { 0, 1, 2 }; var wv = new[] { ww.x, ww.y, ww.z };
                Array.Sort(ord, (p, q) => wv[q].CompareTo(wv[p]));
                float rest = worst;
                foreach (int q in ord)
                {
                    if (wv[q] < 1e-4f || rest <= 1e-7f) continue;
                    int n = tr[q]; float up = Mathf.Max(0f, Mathf.Min(rest / wv[q], cap[n] - h[n]));
                    if (up > 0f) { h[n] += up; rest -= up * wv[q]; changed = true; }
                }
            }
            if (!changed) break;
        }
        if (nSpan > 0 && nSpan < N)
        {
            var nb = new List<int>[N]; for (int n = 0; n < N; n++) nb[n] = new List<int>();
            foreach (var tr in T) for (int q = 0; q < 3; q++) { int u = tr[q], v = tr[(q + 1) % 3]; if (!nb[u].Contains(v)) nb[u].Add(v); if (!nb[v].Contains(u)) nb[v].Add(u); }
            var free = new bool[N]; var known = new bool[N];
            for (int n = 0; n < N; n++) { free[n] = span[n] && float.IsNaN(spanLo[n]); known[n] = !free[n]; }
            for (int it = 0; it < 4 * N; it++)
            {
                bool any = false;
                for (int n = 0; n < N; n++)
                {
                    if (!free[n]) continue; float sum = 0f; int c = 0;
                    foreach (int v in nb[n]) if (known[v]) { sum += h[v]; c++; }
                    if (c > 0) { float nv = sum / c; if (!known[n] || Mathf.Abs(nv - h[n]) > 1e-6f) any = true; h[n] = nv; known[n] = true; }
                }
                if (!any) break;
            }
        }
        // 動かす(床が代より深い格子点は動かさない)
        var dY = new Dictionary<int, float>();
        for (int n = 0; n < N; n++)
        {
            if (h[n] < nH0[n] - 1e-6f) { res.shortN++; h[n] = nH0[n]; continue; }
            h[n] = Mathf.Min(h[n], ytop - SCRIBE_TOP_STOP);
            foreach (int vi in nV[n]) dY[vi] = h[n] - nH0[n];
            res.moved++;
        }
        // 下端の面と床の差(標本ごと)・三角形ごとの最悪の隙
        var tWorst = new float[T.Count];
        for (int s = 0; s < sTri.Count; s++)
        {
            var tr = T[sTri[s]]; var w = sW[s];
            float d = h[tr[0]] * w.x + h[tr[1]] * w.y + h[tr[2]] * w.z - sB[s]; res.atariN++;
            if (Mathf.Abs(d) > tWorst[sTri[s]]) tWorst[sTri[s]] = Mathf.Abs(d);
            if (float.IsNaN(res.lo) || d < res.lo) res.lo = d;
            if (float.IsNaN(res.hi) || d > res.hi) { res.hi = d; res.hiAt = gt.TransformPoint(new Vector3(sP[s].x, sB[s], sP[s].y)); }
        }
        // 隙が狙いを超えた三角形の最も長い辺を割って削り直す(元の形のメッシュ m はまだ動かしていない)
        if (pass < SCRIBE_REFINE_PASSES)
        {
            var want = new HashSet<long>();
            for (int ti = 0; ti < T.Count; ti++)
            {
                if (tWorst[ti] <= SCRIBE_GAP_TARGET) continue;
                var tr = T[ti]; int ea = 0; float best = -1f;
                for (int q = 0; q < 3; q++)
                {
                    int u = tr[q], v = tr[(q + 1) % 3];
                    float el = new Vector2((nX[u] - nX[v]) * sxw, (nZ[u] - nZ[v]) * szw).magnitude; if (el > best) { best = el; ea = q; }
                }
                if (best < 2f * SCRIBE_REFINE_MIN) continue;
                want.Add(ScribeEK(ScribePK(vs[nV[tr[ea]][0]]), ScribePK(vs[nV[tr[(ea + 1) % 3]][0]])));
            }
            int k = want.Count == 0 ? 0 : SplitEdges(m, want);
            if (k > 0) { refined += k; continue; }
        }
        bool hasUv2 = uv2 != null && uv2.Length == vs.Length, hasUv = uv != null && uv.Length == vs.Length;
        foreach (var kv in dY)
        {
            var l2 = L[kv.Key]; l2.y += kv.Value;
            vs[kv.Key] = mt.InverseTransformPoint(gt.TransformPoint(l2));
            if (hasUv && hasUv2) uv[kv.Key] += uv2[kv.Key] * kv.Value;
        }
        m.vertices = vs; if (hasUv) m.uv = uv;
        try { m.uv2 = null; } catch (Exception) { m.uv2 = new Vector2[0]; }   // 削り終えたら uv2 を消す(ライトマップの UV と取り違えない)
        m.RecalculateBounds(); m.RecalculateNormals(); m.RecalculateTangents();
        mf.sharedMesh = EdoSolidMesh.Save(m, meshName);
        return res;
        }
    }

    /// <summary>**浮きと根入れの帯の真ん中へ据える**(硬い ±<paramref name="tol"/>)。<see cref="RootToBed"/> で測った下端 − 相手 の
    /// 最小・最大の幅が 2×tol に収まるなら、駒を幅の真ん中まで上下に動かして測り直し true を返す(<paramref name="s"/> は測り直した値)。
    /// 収まらなければ動かさず false。⭐ 下端の最も低い当たりを 0 に揃えると、高い当たりの側に幅ぶんの浮きが残る
    /// (2026-10-02 新町 rb の表店 0.012m)。当たる先: 類型ビルダーの造成の後の棟の据え直し(全区画の棟・基壇で受けた棟も)。</summary>
    /// <param name="maxSink">帯に収まらないとき、浮きを消すために相手へ沈めてよい深さ[m](0 なら沈めない)。
    /// 布石の基壇で受けた棟は石の天端の起伏が帯を超えるので、浮きの分だけ下げて石へ埋める(据えは埋めて隠すが基本・2026-09-27 施主)。</param>
    public static bool RecentreInBand(GameObject go, ref Scribe s, Func<float, float, float> bedAt, float tol, float maxSink = 0f)
    {
        if (float.IsNaN(s.lo) || float.IsNaN(s.hi)) return false;
        float mid;
        if (s.hi - s.lo <= 2f * tol) mid = (s.hi + s.lo) * 0.5f;
        else if (maxSink > 0f && s.lo - (s.hi - tol * 0.5f) >= -maxSink) mid = s.hi - tol * 0.5f;
        else return false;
        go.transform.position -= new Vector3(0f, mid, 0f);
        s = RootToBed(go, bedAt, 0.1f);
        return !float.IsNaN(s.hi) && s.hi <= tol && s.lo >= -Mathf.Max(tol, maxSink);
    }

    /// <summary>**根入れで据える**(埋めて隠す・2026-09-27 施主「基本は埋める、違和感が見える所だけ光付け」── docs/oki-kata.md §0a)。
    /// 部材の形は変えない(共有のメッシュのまま)。下端(局所の最も低い y)より下は相手(石・地面)の中に隠れる。測るのは**当たり**
    /// (<paramref name="bedAt"/> が NaN でない所 = 石の天端・見えている地表)だけで、足跡の中を <paramref name="step"/> 刻みに引き、
    /// 下端 − 相手 を返す(最大 &gt; 0 = 浮き・最小 = 最も深い根入れ)。跨ぎ(目地の上)は測らない。
    /// 当たる先: <see cref="PostBoardRunScribed"/> の地覆・柱(scribe=false)。以後、代(下へ延ばした部分)を持つ部材の据え全て。</summary>
    public static Scribe RootToBed(GameObject go, Func<float, float, float> bedAt, float step = 0.01f, Func<MeshFilter, bool> only = null)
    {
        // ⭐ 測るのは**下端に届いている駒の足跡だけ**(2026-09-28 EDO-0477 施主「接すると決めた所以外をなぜ測る」)。
        //    ⛔ 2026-09-28 まで全メッシュの外形の四角を下端の高さで引き、棟では屋根の軒の出の下の地面まで「浮き」に数えた
        //    (観理院の護摩堂 0.018m ── 縁も壁も 0.000)。
        var res = new Scribe { lo = float.NaN, hi = float.NaN };
        Transform gt = go.transform; float yb = float.MaxValue;
        var boxes = new List<float[]>();   // 駒ごとの局所 [x0,x1,z0,z1,y0]
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null || (only != null && !only(mf))) continue;
            // ⭐ 足跡の箱は**下端から ROOT_TOUCH 以内の頂点**だけで作る(2026-09-28 EDO-0477)。
            //    ⛔ 全頂点の箱では、笠・軒と一体の 1 メッシュの駒(練塀 Dobei2m・長屋)で箱が笠の幅まで広がり、笠の下の
            //    石垣の見え面を「浮き 0.93m」と測って、観理院の西の石垣の上の塀を一続きごと 1m 沈めた。
            var ls = new List<Vector3>(); float y0 = float.MaxValue;
            foreach (var v in mf.sharedMesh.vertices) { var l = gt.InverseTransformPoint(mf.transform.TransformPoint(v)); ls.Add(l); y0 = Mathf.Min(y0, l.y); }
            if (y0 == float.MaxValue) continue;
            float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
            float yTol = ROOT_TOUCH / Mathf.Max(1e-6f, gt.TransformVector(Vector3.up).magnitude);
            foreach (var l in ls)
            { if (l.y > y0 + yTol) continue; x0 = Mathf.Min(x0, l.x); x1 = Mathf.Max(x1, l.x); z0 = Mathf.Min(z0, l.z); z1 = Mathf.Max(z1, l.z); }
            boxes.Add(new[] { x0, x1, z0, z1, y0 }); yb = Mathf.Min(yb, y0);
        }
        if (yb == float.MaxValue) return res;
        float sxw = gt.TransformVector(Vector3.right).magnitude, szw = gt.TransformVector(Vector3.forward).magnitude;
        float syw = Mathf.Max(1e-6f, gt.TransformVector(Vector3.up).magnitude);
        foreach (var bx in boxes)
        {
            if ((bx[4] - yb) * syw > ROOT_TOUCH) continue;   // 下端に届いていない駒(床・柱・壁・屋根)は当たりでない
            int nx = Mathf.Max(1, Mathf.CeilToInt((bx[1] - bx[0]) * sxw / step)), nz = Mathf.Max(1, Mathf.CeilToInt((bx[3] - bx[2]) * szw / step));
            for (int i = 0; i <= nx; i++)
                for (int j = 0; j <= nz; j++)
                {
                    var w = gt.TransformPoint(new Vector3(bx[0] + (bx[1] - bx[0]) * i / nx, bx[4], bx[2] + (bx[3] - bx[2]) * j / nz));
                    float b = bedAt(w.x, w.z); if (float.IsNaN(b)) { res.spanN++; continue; }
                    float d = w.y - b; res.atariN++;
                    if (float.IsNaN(res.lo) || d < res.lo) res.lo = d;
                    if (float.IsNaN(res.hi) || d > res.hi) { res.hi = d; res.hiAt = new Vector3(w.x, b, w.z); }
                    if (d > 0.01f) res.shortN++;
                }
        }
        return res;
    }

    /// <summary>**硬い・地面(浮き 0)**: 駒の下端の当たり(<see cref="RootToBed"/>)を相手 <paramref name="bedAt"/> で測り、
    /// 最も浮いた当たりが相手に触れる所まで上下に動かす(下端 − 相手 の最大 = 0)。他の当たりは相手に埋まる(据えは埋めて隠す)。
    /// 返すのは動かした後に測り直した値。当たる先: 杭・柱で立つ柵(EDO-0502 岡部の汀の木柵 ── 設計面 Graded で据えて、
    /// 2m 格子の地表が区画線の際で外の低い節点へ下りる所で 32/46 駒・最大 1.59m 浮いた)。</summary>
    public static Scribe SinkToBed(GameObject go, Func<float, float, float> bedAt, float step = 0.05f)
    {
        var rt = RootToBed(go, bedAt, step);
        if (float.IsNaN(rt.hi)) return rt;
        go.transform.position -= Vector3.up * rt.hi;
        return RootToBed(go, bedAt, step);
    }

    /// <summary>駒の**見える丈**[m] = 全高 − 下端の最も深い根入れ(<see cref="RootToBed"/> の最小が負の分)。
    /// 法の上に立つ戸・門で「開く姿になるか」を測る(戸の丈と比べる・EDO-0502 岡部の潜り戸 0.54m)。測れなければ NaN。</summary>
    public static float VisibleAboveBed(GameObject go, Func<float, float, float> bedAt, float step = 0.05f)
    {
        var rt = RootToBed(go, bedAt, step);
        if (float.IsNaN(rt.lo)) return float.NaN;
        var b = RB(go);
        return b.size.y + Mathf.Min(0f, rt.lo);
    }

    /// <summary>駒の腰(壁体の最低点から <paramref name="bandH"/> まで)の全頂点が区画の多角形の外へ出る最大[m](0 = 内)。</summary>
    public static float WaistOutside(GameObject go, Vector2[] poly, float bandH = 1.2f)
    {
        return OutsideBy(LowBandPoints(go.transform, bandH), poly, Vector2.zero);
    }

    /// <summary><see cref="RootToBed"/> が「下端に届いている」とみなす駒の下端の差[m]。【U】部材の継ぎの誤差より大きく、床の厚み(0.28)より小さく。</summary>
    const float ROOT_TOUCH = 0.05f;

    /// <summary>**柱・板・地覆の組で板塀の run を張り、地覆と柱の下端を床へ光付けする**(2026-09-27・EDO-0437 施主裁定 案A「板を石の天端・地面まで下ろす」)。
    /// <para>1. 柱の間の割りは <see cref="PostBoardRun"/> と同じ(端の柱は外形の端を A/B に突き付け・間は柱身の芯を等分・柱間 = 板の幅 + 柱身の幅を実メッシュで測る)。
    /// 2. 板と地覆は同じ変換で置く(地覆は板の真下に納まる枠 ── 部材の約束)。高さは**間ごとに地覆の足跡の下の床の最も高い所**へ板の y=0 を合わせる
    /// (地覆の下端 −0.600 が光付けの代 ⇒ 間の床の起伏が 0.6 までは届く)。
    /// 3. 柱は両隣の間の高い方の y=0 に合わせる(板の笠木と柱の頭の納まりを高い側で取る)。
    /// 4. 既定(<paramref name="scribe"/>=false)は**根入れ** <see cref="RootToBed"/> ── 形を変えず、地覆と柱の代(下端 −0.600)を石・地面の中へ埋めて隠す。
    /// 見た目に違和感が出る所だけ scribe=true で <see cref="ScribeToBed"/>(光付け)。どちらも当たりとの隙の最悪を <paramref name="log"/> へ
    /// (2026-09-27 施主「基本は埋める・違和感が見える所だけ光付け」。光付けは石の段の足の楔 1.5cm が点を足しても縮まず、1 駒 50〜100 秒かかった)。</para>
    /// ⛔ 走りの位置は柱身の断面・外形の射影で決める(規則21)。⛔ 板を傾けない。
    /// 当たる先: 地覆の組で張る板塀の全て(山王 前庭の板塀 `Ita_ZN`・`Ita_ZNE`・`Ita_ZSW`・`Ita_ZSE`・`Ita_Niou_N`)。</summary>
    public static List<GameObject> PostBoardRunScribed(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
        string postPath, string boardPath, string jifukuPath, Func<float, float, float> bedAt, bool pair, System.Text.StringBuilder log, bool scribe = false)
    {
        var made = new List<GameObject>();
        bedAt = MemoBed(bedAt, 0.00125f);   // 光付けと割り足しは同じ点を何度も引く ── 相手の面を 1.25mm の升で覚える
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude; Vector2 nrm = new Vector2(-dir.y, dir.x);
        float a0 = Vector2.Dot(A, dir);
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        float boardW = RunMeasure(boardPath).W;
        float gLo = float.NaN, gHi = float.NaN; Vector3 gHiAt = Vector3.zero; int shortN = 0, nScr = 0, nAtari = 0, nSpan = 0, nRef = 0;
        Action<Scribe> Tally = s =>
        {
            nScr++; shortN += s.shortN; nAtari += s.atariN; nSpan += s.spanN; nRef += s.refined;
            if (!float.IsNaN(s.lo) && (float.IsNaN(gLo) || s.lo < gLo)) gLo = s.lo;
            if (!float.IsNaN(s.hi) && (float.IsNaN(gHi) || s.hi > gHi)) { gHi = s.hi; gHiAt = s.hiAt; }
        };
        for (int side = 0; side < (pair ? 2 : 1); side++)
        {
            float ry = side == 0 ? psi : psi + 180f; float latOff = side == 0 ? 0f : -0.12f; string sfx = side == 0 ? "f" : "b";
            var probe = Place(postPath, Vector3.zero, ry, Vector3.one, parent, "_probe");
            float fmn, fmx; ButtOnRun(probe, A, dir, outward, latOff, a0, out fmn, out fmx);
            float bmn = float.MaxValue, bmx = float.MinValue;
            foreach (var w in MidSection(probe)) { float q = w.x * dir.x + w.z * dir.y; bmn = Mathf.Min(bmn, q); bmx = Mathf.Max(bmx, q); }
            UnityEngine.Object.DestroyImmediate(probe);
            float bc = (bmn + bmx) * 0.5f, bodyW = bmx - bmn, fl = fmn - bc, fh = fmx - bc;
            float c0 = a0 - fl, cn = a0 + len - fh, span = cn - c0;
            int nb = Mathf.Max(1, Mathf.RoundToInt(span / (boardW + bodyW)));
            float p = span / nb;
            var y0 = new float[nb];
            for (int k = 0; k < nb; k++)
            {
                float f0 = c0 + p * k + bodyW * 0.5f, f1 = c0 + p * (k + 1) - bodyW * 0.5f;
                var sx = new Vector3((f1 - f0) / boardW, 1f, 1f);
                var ita = Place(boardPath, Vector3.zero, ry, sx, parent, prefix + "_i" + k + sfx);
                float mn, mx; ButtOnRun(ita, A, dir, outward, latOff, f0, out mn, out mx);
                var jf = Place(jifukuPath, Vector3.zero, ry, sx, parent, prefix + "_j" + k + sfx);
                jf.transform.SetPositionAndRotation(ita.transform.position, ita.transform.rotation);
                // 間の床 = 地覆の足跡(実メッシュの走り × 厚み)の下の床の最も高い所
                float s0 = float.MaxValue, s1 = float.MinValue, t0 = float.MaxValue, t1 = float.MinValue;
                foreach (var mf in jf.GetComponentsInChildren<MeshFilter>())
                    foreach (var v in mf.sharedMesh.vertices)
                    { var w = mf.transform.TransformPoint(v); Vector2 q = new Vector2(w.x, w.z); float s = Vector2.Dot(q, dir), t = Vector2.Dot(q, nrm); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); t0 = Mathf.Min(t0, t); t1 = Mathf.Max(t1, t); }
                float fmax = float.NaN;
                for (float s = s0; s <= s1 + 1e-4f; s += 0.02f)
                    for (int c = 0; c <= 2; c++)
                    { Vector2 q = dir * Mathf.Min(s, s1) + nrm * (t0 + (t1 - t0) * c / 2f); float b = bedAt(q.x, q.y); if (!float.IsNaN(b) && (float.IsNaN(fmax) || b > fmax)) fmax = b; }
                y0[k] = float.IsNaN(fmax) ? ita.transform.position.y : fmax;
                foreach (var g in new[] { ita, jf }) { var ps = g.transform.position; ps.y = y0[k]; g.transform.position = ps; }
                Tally(scribe ? ScribeToBed(jf, bedAt, "Jifuku_" + prefix + "_" + k + sfx) : RootToBed(jf, bedAt));
                made.Add(ita); made.Add(jf);
            }
            for (int k = 0; k <= nb; k++)
            {
                var go = Place(postPath, Vector3.zero, ry, Vector3.one, parent, prefix + "_h" + k + sfx);
                float mn, mx; ButtOnRun(go, A, dir, outward, latOff, c0 + p * k + fl, out mn, out mx);
                float yy = Mathf.Max(k > 0 ? y0[k - 1] : float.MinValue, k < nb ? y0[k] : float.MinValue);
                var ps = go.transform.position; ps.y = yy; go.transform.position = ps;
                Tally(scribe ? ScribeToBed(go, bedAt, "Hashira_" + prefix + "_" + k + sfx) : RootToBed(go, bedAt));
                made.Add(go);
            }
        }
        if (log != null)
            log.AppendLine("    " + prefix + ": 地覆の組で" + (scribe ? "光付け " : "根入れ ") + nScr + " 駒 ── 当たりの標本 " + nAtari + "・跨ぎ(目地の上・測らない) " + nSpan + "・細かく割った辺 " + nRef + " / 当たりの下端 − 相手 最小 " + gLo.ToString("F3") + " / 最大 " + gHi.ToString("F3") +
                           "m @(" + gHiAt.x.ToString("F2") + ", " + gHiAt.y.ToString("F2") + ", " + gHiAt.z.ToString("F2") + ")" +
                           (shortN > 0 ? (scribe ? " / ⚠ 床が代より深く届かない頂点 " : " / ⚠ 浮き(+0.01 超)の標本 ") + shortN : ""));
        return made;
    }

    /// <summary>**板塀の駒を描かれた地表の弦に張って据える**(2026-09-26・EDO-0437 第5巡)。駒の走り [<paramref name="mn"/>, <paramref name="mx"/>]
    /// (<paramref name="dir"/> への射影)の足の線に沿う床の高さ <paramref name="bedAt"/> の最小二乗の直線(弦)の勾配だけ走りの向きに傾け、実メッシュの**触れている箇所**
    /// (<see cref="ContactOn"/>)を床に合わせてから根入れ <paramref name="root"/> だけ沈める。
    /// ⭐ 床は描かれた地表(縁の皮の升では皮 ── <see cref="Drawn"/>)で引く。⛔ 穴の升の下の見えない地形で据えない
    /// (切土の法肩の板塀 `Ita_ZSE` が 6.2m 一枚を水平のまま地形で据えられ、柱の足が 0.18 浮き 0.21 埋まった)。
    /// 当たる先: 座の無い板塀・穂垣の run が傾いた地表に建つ所すべて(座の在る run は従来どおり)。</summary>
    public static void SeatPanelOnBed(GameObject go, Vector2 A, Vector2 dir, float mn, float mx, Func<float, float, float> bedAt, float root)
    {
        float a0 = Vector2.Dot(A, dir);
        // 弦 = 駒の足の線(駒の外形の奥行の中ほど)に沿って 0.1m ごとに引いた床の高さの最小二乗の直線 ──
        //   両端の二点だけで引くと、端が法の縁・袖の際の落ちに掛かって弦が逆へ傾いた(第5巡の実測 3.6°)
        var rb = RB(go); Vector2 cen = new Vector2(rb.center.x, rb.center.z);
        Vector2 nrm = new Vector2(-dir.y, dir.x); float lat = Vector2.Dot(cen - A, nrm);
        double sx = 0, sy = 0, sxx = 0, sxy = 0; int cnt = 0;
        for (float u = mn + 0.05f; u <= mx - 0.05f + 1e-4f; u += 0.1f)
        {
            Vector2 q = A + dir * (u - a0) + nrm * lat; float y = bedAt(q.x, q.y); if (float.IsNaN(y)) continue;
            float t = u - mn; sx += t; sy += y; sxx += t * t; sxy += t * y; cnt++;
        }
        double den = cnt * sxx - sx * sx;
        if (cnt >= 3 && Math.Abs(den) > 1e-9 && mx - mn > 0.1f)
        {
            float slope = (float)((cnt * sxy - sx * sy) / den);
            float roll = Mathf.Atan(slope) * Mathf.Rad2Deg;
            if (Mathf.Abs(roll) > 0.05f)
            {
                Vector3 d3 = new Vector3(dir.x, 0f, dir.y); Vector3 ax = Vector3.Cross(d3, Vector3.up);
                var c = RB(go).center;
                float smn0 = float.NaN; { var sec0 = MidSection(go); foreach (var w in sec0) { float q = Vector2.Dot(new Vector2(w.x, w.z), dir); if (float.IsNaN(smn0) || q < smn0) smn0 = q; } }
                go.transform.RotateAround(c, ax, roll);
                // 傾けると走りの端が cos だけ縮む ── 始まりの端を傾ける前の位置へ戻す。
                //   ⭐ 端は**丈の中ほどの断面**(<see cref="MidSection"/>・検査と同じ物差し)で測る(2026-09-26・EDO-0437 第4巡)。
                //   ⛔ 全頂点の射影の最小で戻さない ── 傾けた駒は頭か足の角が 丈/2·sinθ 前へ出て、その角を端へ合わせると駒全体が
                //   走りの先へ 丈/2·sinθ ずれる(前庭の南の板塀 Ita_ZSE +0.055・Ita_ZSW +0.025)。当たる先: 傾けて据える板塀・穂垣の駒すべて。
                var sec = MidSection(go);
                if (sec.Count > 0 && !float.IsNaN(smn0))
                { float smn = float.MaxValue; foreach (var w in sec) smn = Mathf.Min(smn, Vector2.Dot(new Vector2(w.x, w.z), dir)); go.transform.position += d3 * (smn0 - smn); }
                else { float nmn, nmx; ProjExtent(go, dir, float.MinValue, float.MaxValue, null, out nmn, out nmx); go.transform.position += d3 * (mn - nmn); }
            }
        }
        Vector3 at; int n;
        float gap = ContactOn(go, bedAt, out at, out n, 0.01f, 4000);
        if (float.IsNaN(gap)) { try { SeatOnGround(go, root, 600); } catch (Exception) { } return; }
        go.transform.position -= new Vector3(0f, gap + root, 0f);
    }

    /// <summary>**駒の足の下に在る受けの駒(土留め・石垣)の天端に載せる**(2026-09-26・EDO-0437 第3巡)。<paramref name="beds"/> のうち
    /// 外接箱が平面で重なる物について <see cref="RestGap"/>(面で測る鉛直の触れている箇所)の最小を取り、負(めり込み)なら
    /// その分だけ上げる(0 = 接する)。⛔ 下げない(地面へ沈めた据えは保つ)。返り値 = 上げた量(0 = 動かさない)。
    /// 当たる先: 板塀・穂垣・柵の足が土留め・石垣の天端に載る所すべて(山王 前庭の北の板塀)。</summary>
    public static float RestOnBeds(GameObject go, IList<GameObject> beds)
    {
        var b0 = RB(go); float cm = float.NaN;
        foreach (var bd in beds)
        {
            if (bd == null || bd == go || !bd.activeInHierarchy) continue;
            var bb = RB(bd);
            if (bb.max.x < b0.min.x || bb.min.x > b0.max.x || bb.max.z < b0.min.z || bb.min.z > b0.max.z) continue;
            Vector3 at; int n; float c = RestGap(go, null, bd, null, out at, out n);
            if (!float.IsNaN(c) && (float.IsNaN(cm) || c < cm)) cm = c;
        }
        if (float.IsNaN(cm) || cm >= 0f) return 0f;
        go.transform.position += new Vector3(0f, -cm, 0f);
        return -cm;
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
        float baseY, Vector2 gapC, float gapHalf, string prefix, out string note, IList<DanSec> dan = null)
    {
        switch (kind)
        {
            case "none":
                note = "囲わない(表の fence=none)";
                return new List<GameObject>();

            case "yarai":
            {
                // 竹矢来(EDO-0363・部材方が新造)— **透け**が意匠。⛔ 表裏の対で置かない(格子が二重になり藪に見える)、
                // ⛔ ES 倍しない(Eg.* の obj と違い自前で焼いた実寸FBX)。1スパン1枚・伸縮は走りだけ。
                var made = PanelRun(parent, A, B, outward, prefix, EdoAssets.Own.Typ.Takeyarai, gapC, gapHalf,
                                    pair: false, unitScale: 1f);
                float h = made.Count > 0 ? RB(made[0]).size.y : float.NaN;   // ⭐ 据えた駒の実メッシュから測る
                note = string.Format("竹矢来 {0}枚(駒の丈 {1:F2}m・見付の充実率30.4% — 板塀・穂垣の100%と20m先でも判別可・EDO-0363)",
                                     made.Count, h);
                return made;
            }

            case "tategoshi":
            {
                // 竪格子の柵(町木戸の袖と同じ意匠・丈 2.12=7尺)── 町屋の表店の列の端の空きを閉じる型
                // (EDO-0503 施主「門前町の入り口の区切りで使ってるような仕切り」)。両面の実寸FBX・1間ちょうど(EdoAssets.Own.TategoshiSaku)。
                // ⚠ 端柱は足さない ── 端は店の妻と隣の塀へ食い込ませて隠す。
                var made = PanelRun(parent, A, B, outward, prefix, EdoAssets.Own.TategoshiSaku(2.12f), gapC, gapHalf,
                                    pair: false, unitScale: 1f);
                // ⭐ 駒は掘立の根入れ 0.26 を持つ(札 yBottom −0.26)。PanelRun は下端を地面に当てるので、根入れぶん沈めて
                //    地覆の下端を当たりの最も高い地面へ揃える(埋めて隠す)。⛔ 沈めないと地覆が 0.16〜0.25m 浮いた(2026-10-02 実測)。
                const float NEIRE = 0.26f;
                foreach (var g in made)
                {
                    try { SeatOnGround(g, NEIRE, 1200); } catch (Exception) { }
                    // 駒の幅の中で地面が下がる所でも浮かせない ── 下端と地面の隙の最大(hi)が根入れ −NEIRE を超えれば、その分沈める
                    //   ⛔ 坂の柵で 0.221m 浮いた(門前3・2026-10-03)
                    var sc = RootToBed(g, Ground, 0.05f);
                    if (!float.IsNaN(sc.hi) && sc.hi > -NEIRE + 0.002f) g.transform.position += Vector3.down * (sc.hi + NEIRE);
                }
                // ⭐ 一続きの柵は天端を一直線に揃える ── 最も低い駒の高さへ下げ、坂の上手は余分に埋める
                //    (施主 2026-10-03「高さがガタついてる」「少し地面に埋めてしまってもいい」)。⛔ 駒ごとに坂なりに据えると天端が段々になった。
                //    ただし段差が LEVEL_MAX を超える坂では一直線にしない(上手が 1.5m 埋まった・門前3)── 駒ごとの段のまま据える。
                //    ⛔ 足元の地面をならす型は採らない ── 擦り付けが先に建てた隣の板塀の足元まで届き、浮かせた(門前1 で 0.55m)。
                const float LEVEL_MAX = 0.30f;
                float lowY = made.Count > 0 ? made.Min(g => g.transform.position.y) : 0f;
                float rise = made.Count > 0 ? made.Max(g => g.transform.position.y) - lowY : 0f;
                bool level = rise <= LEVEL_MAX;
                if (level) foreach (var g in made) { var p = g.transform.position; p.y = lowY; g.transform.position = p; }
                float h = made.Count > 0 ? RB(made[0]).size.y - NEIRE : float.NaN;
                note = string.Format("竪格子の柵 {0}枚(地上の丈 {1:F2}m・根入れ {2:F2}・{3})", made.Count, h, NEIRE,
                                     level ? string.Format("天端を揃えて上手を最大 {0:F2}m 余分に埋めた", rise)
                                           : string.Format("坂で段差 {0:F2}m が {1:F2} を超えるので駒ごとの段で据えた", rise, LEVEL_MAX));
                return made;
            }

            case "mokusaku":
            {
                // 木柵(杭と横板の板柵・丈 1.52)── 町屋の表店の列の端の空きを閉じる型(EDO-0503 施主「木の柵じゃない？」)。
                // 両面の実寸FBX(EdoAssets.Own.HoriSaku)。⛔ 丸太の腰高柵(SakuKoshidaka)は材が灰色で鉄柵に見えた(2026-10-02 実見)。
                // ⚠ 端柱は足さない ── 端は店の妻と隣の塀へ食い込ませて隠す。
                var made = PanelRun(parent, A, B, outward, prefix, EdoAssets.Own.HoriSaku, gapC, gapHalf,
                                    pair: false, unitScale: 1f);
                float h = made.Count > 0 ? RB(made[0]).size.y : float.NaN;
                note = string.Format("木柵 {0}枚(駒の丈 {1:F2}m)", made.Count, h);
                return made;
            }

            case "kenninji":
            {
                // 建仁寺垣(丈 1.5・割竹の目隠しの垣)── 町屋の表店の列の端の空きを閉じる型(EDO-0503 施主「柵とか竹垣レベル」)。
                // 両面の実寸FBX(EdoAssets.Own.KenninjiGaki)。⚠ 端柱は足さない ── この型の端は店の妻と隣の塀へ食い込ませて隠す。
                var made = PanelRun(parent, A, B, outward, prefix, EdoAssets.Own.KenninjiGaki(1.5f), gapC, gapHalf,
                                    pair: false, unitScale: 1f);
                float h = made.Count > 0 ? RB(made[0]).size.y : float.NaN;
                note = string.Format("建仁寺垣 {0}枚(駒の丈 {1:F2}m)", made.Count, h);
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
                    note = string.Format("板塀 {0}枚 + 生垣 {1}株(ツツジの後列+ツゲの前列の塊・後列は塀の**触れている箇所**まで寄せた・帯の内の勾配 {2:P0} は法面と見ない・EDO-0475)",
                                         made.Count, ni, grade);
                }
                return made;
            }

            case "dobei":
                note = null;   // EDO-0351: 練塀の一体物(Dobei2m)が在る。板塀代用は誤りだった(EDO-0318 ⑤ の訂正)
                // ⭐ 段塀(2026-09-29 EDO-0477 施主裁定1=B)── 呼び手が区切り(DanPlan)を渡したときは傾けずに段で建てる
                if (dan != null && dan.Count > 0) return NeribeiStepRun(parent, A, B, outward, prefix, dan, gapC, gapHalf, out note);
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

    /// <summary>生垣を植えてはならない所(棟・門構えの外接箱)。囲いを建てる呼び手(類型ビルダーの造成後の建て直し)が
    /// 入れて、建て終えたら null に戻す。null なら避けない(棟の前の一巡目)。EDO-0475</summary>
    public static List<Bounds> PlantAvoid = null;

    /// <summary>生垣・林縁帯の株を植えてよい区画の輪郭(世界の x,z)。囲いを建てる呼び手が入れて、建て終えたら null に戻す。
    /// 条件は**硬い**(区域侵犯は許容0): 株の外接箱の足跡の四隅が一つでも輪郭の外に出る株は植えない。
    /// ⛔ 2026-10-01 まで辺ごとに「塀の内へ寄せる」だけで隣の辺を見ず、鋭い角(十坊8 の 39°)や辺の端(十坊2)で
    /// 株が隣の区画・道へ 1.2〜2.3m 出た(EDO-0495)。当たる先: 類型の生垣付き板塀(ita+ikegaki)と林縁帯の全区画。</summary>
    public static Vector2[] PlantInside = null;

    static bool OutsidePlot(GameObject go)
    {
        if (PlantInside == null || PlantInside.Length < 3) return false;
        var b = RB(go);
        const float m = 0.05f;   // 葉先の丸めの許し
        foreach (var q in new[] { new Vector2(b.min.x + m, b.min.z + m), new Vector2(b.max.x - m, b.min.z + m),
                                  new Vector2(b.max.x - m, b.max.z - m), new Vector2(b.min.x + m, b.max.z - m) })
            if (!EdoGeom.PIP(PlantInside, q)) return true;
        return false;
    }

    /// <summary>生垣の後列(主)の一株の型。⭐ 設計は庭方(2026-09-29 EDO-0475・scratchpad の EDO0475_ikegaki_design)。
    /// 江戸の寺の生垣は濃緑小葉の常緑(マサキ・イヌツゲ・カシ)が類型【B】だが在庫に無く、**ツツジ(花無し・暗いオリーブ緑)で見立てる【P】**。
    /// 水平と高さの倍率の幅は型ごと(A04 は横に張るので水平を絞る)。</summary>
    struct IkeKind { public string path; public float hLo, hHi, vLo, vHi; }
    static IkeKind[] _ikeBack;
    static IkeKind[] IkeBack
    {
        get
        {
            if (_ikeBack == null) _ikeBack = new[]
            {
                new IkeKind { path = EdoAssets.JG.Azalea(1), hLo = 0.62f, hHi = 0.72f, vLo = 1.10f, vHi = 1.30f },
                new IkeKind { path = EdoAssets.JG.Azalea(3), hLo = 0.55f, hHi = 0.65f, vLo = 0f,    vHi = 0f },   // vHi=0 は等倍(高さも水平と同じ倍率)
                new IkeKind { path = EdoAssets.JG.Azalea(4), hLo = 0.50f, hHi = 0.56f, vLo = 1.00f, vHi = 1.12f },
            };
            return _ikeBack;
        }
    }
    /// <summary>生垣の色の寄せ【P・庭方】。パックの材は触らず Edo 側の複製の _BaseColor に掛ける ── 暗く青みへ。</summary>
    static readonly Color IKE_TINT_BACK = new Color(0.85f, 0.92f, 0.85f);
    static readonly Color IKE_TINT_FRONT = new Color(0.70f, 0.80f, 0.68f);

    /// <summary>**在庫の材の色を寄せた複製を着せる。**複製は <c>Assets/Edo/Materials/M_Tint_&lt;元の材&gt;_&lt;色&gt;.mat</c> に一度だけ作る
    /// (⛔ パックの材を書き換えない ── 再 import で消え、他の邸の同じ木まで色が変わる)。
    /// ⛔ コードの <c>new Material</c> を資産にせず着せない(プレハブの m_Materials が null になりマゼンタ・EDO-0301)。</summary>
    static readonly Dictionary<string, Material> _tintCache = new Dictionary<string, Material>();
    public static void TintFoliage(GameObject go, Color tint)
    {
        string hex = ColorUtility.ToHtmlStringRGB(tint);
        foreach (var r in go.GetComponentsInChildren<Renderer>(true))
        {
            var ms = r.sharedMaterials; bool ch = false;
            for (int i = 0; i < ms.Length; i++)
            {
                var m = ms[i];
                if (m == null || m.name.StartsWith("M_Tint_")) continue;
                string key = m.name.Replace(' ', '_') + "_" + hex;
                Material t;
                if (!_tintCache.TryGetValue(key, out t) || t == null)
                {
                    string p = EdoAssets.Own.Mat("M_Tint_" + key);
                    t = AssetDatabase.LoadAssetAtPath<Material>(p);
                    if (t == null)
                    {
                        t = new Material(m);
                        foreach (var prop in new[] { "_BaseColor", "_Color" })
                            if (t.HasProperty(prop))
                            {
                                var c = t.GetColor(prop);
                                t.SetColor(prop, new Color(c.r * tint.r, c.g * tint.g, c.b * tint.b, c.a));
                            }
                        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(p));
                        AssetDatabase.CreateAsset(t, p);
                    }
                    _tintCache[key] = t;
                }
                ms[i] = t; ch = true;
            }
            if (ch) r.sharedMaterials = ms;
        }
    }

    /// <summary>据えた株の実メッシュを辺の向き <paramref name="dir"/> へ投げた幅(中心からの前後)。⭐ 外接箱で測らない(yaw を振った株で膨らむ)。</summary>
    static void SpanAlong(GameObject go, Vector2 dir, out float lo, out float hi)
    {
        var pts = Body(go.transform, 600, true);
        float c = Vector2.Dot(new Vector2(go.transform.position.x, go.transform.position.z), dir);
        lo = float.MaxValue; hi = float.MinValue;
        foreach (var p in pts) { float d = p.x * dir.x + p.z * dir.y - c; if (d < lo) lo = d; if (d > hi) hi = d; }
        if (lo > hi) { lo = -0.5f; hi = 0.5f; }
    }

    static bool HitsAvoid(GameObject go)
    {
        if (PlantAvoid == null || PlantAvoid.Count == 0) return false;
        var b = RB(go);
        b.Expand(new Vector3(-0.3f, 0f, -0.3f));   // 葉先が軒下へ掛かるのは許す(据えの芯が棟に入るのを退ける)
        foreach (var a in PlantAvoid)
            if (b.min.x < a.max.x && b.max.x > a.min.x && b.min.z < a.max.z && b.max.z > a.min.z) return true;
        return false;
    }

    /// <summary>板塀の内側に**生垣**を植える(EDO-0475 で作り直し・設計は庭方 2026-09-29)。
    /// <para>⛔ 2026-09-29 まで 1 間の箱の駒(<c>Ikegaki_1.818.fbx</c>)を 1 間ピッチで並べていて、施主に「緑の四角い箱」「気持ち悪い」
    /// 「ショボすぎる」と言われた。いまは**在庫の低木を不揃いに密に植えて**生垣に見せる:</para>
    /// <para>① **後列(主・連続)** ツツジ A01:A03:A04 = 5:3:2【P】。芯々 = 隣り合う 2 株の**実測の樹冠幅**の平均 × 0.75 ± 0.12m
    /// (樹冠が 2〜3 割重なり向こうが抜けない)。奥行は塀の内側の葉へ <see cref="Abut(GameObject,GameObject,Vector3,float,out Vector3,out int,float,int,bool)"/>
    /// で**触れている箇所**まで寄せ、0.03〜0.22m 戻す(塀を葉が抜けない)。頂は塀の天端より 0〜0.35m 低く(越えれば丈を詰める)。
    /// 同じ型を隣に置かない。走りの両端の株は A04(横に張る・隅を埋める)、門の開口の脇は A01 を低く(袖を段に落とす)。</para>
    /// <para>② **前列(裾)** ツゲの一株を 3・5・7 の奇数の塊で、走りの 45〜60% を覆う(塊の間 1.5〜4m)【B 刈込は塊・奇数】。
    /// 芯は後列の芯より 0.55〜0.80m 手前。門の開口の角には 1 株。</para>
    /// <para>③ 開口の縁から樹冠の端まで 0.3〜0.5m 空ける。株の側面はどこも葉なので箱の小口は出ない。
    /// ④ 足元は根入れ(<see cref="RootPlant"/>)。塀際の帯を叩き土の印(<see cref="NiwaGroundZone"/> tataki)で塗り、草を抜く。
    /// ⑤ 色は <see cref="TintFoliage"/> で暗く寄せる。種は辺の座標から(版を跨いで同じ姿)。
    /// 棟・門構え(<see cref="PlantAvoid"/>)に芯が掛かる株は植えない。硬い条件 = 根入れ ≤ <see cref="CHORD_ROOT_MAX"/>・棟に掛けない / 柔らかい = 芯々・丈・覆う割合。
    /// 当たる先: 類型の生垣付き板塀(ita+ikegaki)の全区画(いま十坊 10 区画)。返り値 = 植えた株の数(後列+前列)。</para></summary>
    static int IkegakiRow(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix,
                          List<GameObject> fence, Vector2 gapC, float gapHalf)
    {
        if (fence == null || fence.Count == 0) return 0;
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        if (len < 1.0f) return 0;
        var toFence = new Vector3(outward.x, 0f, outward.y);
        var inner = fence.Where(f => f.name.EndsWith("b")).ToList();   // 塀の内側の葉(DobeiRun の裏の駒)
        if (inner.Count == 0) inner = fence;
        var rnd = new System.Random(Mathf.RoundToInt((A.x * 13.7f + A.y * 3.1f + B.x * 19.3f + B.y * 47.1f) * 100f) & 0x7fffffff);
        Func<float, float, float> U = (a, b) => a + (float)rnd.NextDouble() * (b - a);
        Func<Vector2, float> dOf = p => Vector2.Dot(p - A, -outward);   // 塀の線から内へ

        // 区切り: 門の開口(+ 0.3〜0.5m の空き)で走りを割る
        var segs = new List<float[]>();   // {s0, s1, s0 が開口側か, s1 が開口側か}
        if (gapHalf > 0f)
        {
            float gT = Vector2.Dot(gapC - A, dir);
            float clrA = U(0.3f, 0.5f), clrB = U(0.3f, 0.5f);
            if (gT - gapHalf - clrA > 0.5f) segs.Add(new[] { 0f, gT - gapHalf - clrA, 0f, 1f });
            if (len - (gT + gapHalf + clrB) > 0.5f) segs.Add(new[] { gT + gapHalf + clrB, len, 1f, 0f });
        }
        else segs.Add(new[] { 0f, len, 0f, 0f });

        Func<Vector2, GameObject> nearFence = c =>
        {
            GameObject near = null; float bd = float.MaxValue;
            foreach (var f in inner)
            {
                var fp = f.transform.position;
                float d = (new Vector2(fp.x, fp.z) - c).sqrMagnitude;
                if (d < bd) { bd = d; near = f; }
            }
            return near;
        };

        int made = 0, idx = 0;
        var backT = new List<float>(); var backD = new List<float>(); var backFront = new List<float>();
        var zoneQuads = new List<Vector3>();
        foreach (var sg in segs)
        {
            float s0 = sg[0], s1 = sg[1];
            bool gateA = sg[2] > 0f, gateB = sg[3] > 0f;
            // ── ① 後列 ──
            int prevK = -1; float prevT = float.NaN, prevHi = 0f, prevW = 0f;
            for (int guard = 0; guard < 400; guard++)
            {
                float remain = float.IsNaN(prevT) ? s1 - s0 : s1 - (prevT + prevHi);
                if (remain < 0.35f) break;
                bool first = float.IsNaN(prevT), last = remain < 2.0f;
                bool atGate = (first && gateA) || (last && gateB);
                bool atEnd = (first && !gateA && s0 < 1e-3f) || (last && !gateB && s1 > len - 1e-3f);
                int k;
                if (atGate) k = 0;                                   // 門の脇 = A01 を低く(袖を段に落とす)
                else if (atEnd) k = 2;                               // 走りの両端 = A04 で隅を埋める
                else
                {
                    do
                    {
                        int r = rnd.Next(10);
                        k = r < 5 ? 0 : r < 8 ? 1 : 2;
                    } while (k == prevK);
                }
                if (k == prevK) k = (k + 1) % 3;
                var kd = IkeBack[k];
                float sh = U(kd.hLo, kd.hHi);                        // 倍率は型ごとの絶対値(庭方の設計値)
                float sv = kd.vHi > 0f ? U(kd.vLo, kd.vHi) : sh;
                if (k == 0 && atGate) sv = U(0.95f, 1.05f);          // 袖の株は低く(丈 ≈1.2m)
                var c0 = A + dir * (float.IsNaN(prevT) ? s0 : prevT) - outward * 2.5f;
                var go = Place(kd.path, new Vector3(c0.x, 0f, c0.y), U(0f, 360f), new Vector3(sh, sv, sh), parent,
                               prefix + "_" + (idx++));
                if (go == null) break;
                float lo, hi; SpanAlong(go, dir, out lo, out hi);
                float w = hi - lo;
                float tc = float.IsNaN(prevT) ? s0 - lo : prevT + 0.75f * (prevW + w) * 0.5f + U(-0.12f, 0.12f);
                if (tc + hi > s1 + 0.05f)
                {
                    tc = s1 - hi;
                    if (!float.IsNaN(prevT) && tc - prevT < 0.35f * (prevW + w)) { UnityEngine.Object.DestroyImmediate(go); break; }
                }
                var c = A + dir * tc - outward * 2.5f;
                go.transform.position = new Vector3(c.x, go.transform.position.y, c.y);
                try { SeatOnGround(go, 0.05f, 400); } catch (Exception) { }
                var nf = nearFence(c);
                if (nf != null) { Vector3 at; int cn; Abut(go, nf, toFence, U(0.03f, 0.22f), out at, out cn, 0.30f, 500); }
                try { SeatOnGround(go, 0.05f, 400); } catch (Exception) { }
                // 頂は塀の天端より 0〜0.35m 低く ── 越えれば丈を詰めて据え直す(柔らかい条件)
                if (nf != null)
                {
                    float top = RB(nf).max.y - U(0f, 0.35f);
                    var gb = RB(go);
                    if (gb.max.y > top && gb.size.y > 0.1f)
                    {
                        float want = Mathf.Max(0.8f, top - gb.min.y);
                        var s = go.transform.localScale; s.y *= want / gb.size.y; go.transform.localScale = s;
                        try { SeatOnGround(go, 0.05f, 400); } catch (Exception) { }
                    }
                }
                prevT = tc; prevHi = hi; prevW = w; prevK = k;          // 植えられなくても間は進める(同じ所で回らない)
                if (HitsAvoid(go) || !RootPlant(go, CHORD_ROOT_MAX) || OutsidePlot(go)) { UnityEngine.Object.DestroyImmediate(go); continue; }
                TintFoliage(go, IKE_TINT_BACK);
                var p2 = new Vector2(go.transform.position.x, go.transform.position.z);
                backT.Add(tc); backD.Add(dOf(p2));
                float flo, fhi; SpanAlong(go, -outward, out flo, out fhi);
                backFront.Add(dOf(p2) + fhi);
                made++;
            }

            // ── ② 前列(ツゲの奇数の塊)──
            Func<float, float> depthAt = t =>
            {
                if (backT.Count == 0) return 1.2f;
                int bi = 0; float bd = float.MaxValue;
                for (int i = 0; i < backT.Count; i++) { float d = Mathf.Abs(backT[i] - t); if (d < bd) { bd = d; bi = i; } }
                return backD[bi];
            };
            Action<float, string> plantFront = (t, nm) =>
            {
                var c = A + dir * t - outward * (depthAt(t) + U(0.55f, 0.80f));
                float s = U(1.0f, 1.25f);
                var go = Place(EdoAssets.JG.BoxwoodSingle(1 + rnd.Next(3)), new Vector3(c.x, 0f, c.y), U(0f, 360f),
                               Vector3.one * s, parent, nm);
                if (go == null) return;
                try { SeatOnGround(go, 0.03f, 300); } catch (Exception) { }
                if (HitsAvoid(go) || !RootPlant(go, CHORD_ROOT_MAX) || OutsidePlot(go)) { UnityEngine.Object.DestroyImmediate(go); return; }
                TintFoliage(go, IKE_TINT_FRONT);
                made++;
            };
            float cur = s0 + U(0.3f, 2.0f);
            if (gateA) { plantFront(s0 + 0.35f, prefix + "_f" + (idx++)); cur = s0 + U(1.5f, 3.0f); }
            while (cur < s1 - 0.6f)
            {
                int n = new[] { 3, 5, 7 }[rnd.Next(3)];
                float t = cur;
                for (int j = 0; j < n && t < s1 - 0.4f; j++)
                {
                    plantFront(t, prefix + "_f" + (idx++));
                    t += U(0.6f, 0.8f) + U(-0.1f, 0.1f);
                }
                cur = t + U(1.5f, 4.0f);
            }
            if (gateB && cur - U(1.5f, 4.0f) < s1 - 1.2f) plantFront(s1 - 0.35f, prefix + "_f" + (idx++));

            // ── ④ 足元の帯(塀際から後列の樹冠の前 + 0.6m・叩き土)──
            float dz = backFront.Count > 0 ? backFront.Average() + 0.6f : 1.8f;
            var q0 = A + dir * s0; var q1 = A + dir * s1;
            foreach (var q in new[] { q0, q1, q1 - outward * dz, q0 - outward * dz })
                zoneQuads.Add(new Vector3(q.x, 0f, q.y));
            backT.Clear(); backD.Clear(); backFront.Clear();
        }
        if (zoneQuads.Count >= 4)
        {
            var zg = new GameObject(prefix + "_Ground_tataki");
            zg.transform.SetParent(parent, false);
            var z = zg.AddComponent<NiwaGroundZone>();
            z.kind = "tataki"; z.quads = zoneQuads;
        }
        return made;
    }

    /// <summary>林縁帯の低木を斜面へ埋めてよい深さの上限[m]【U】── 法面の帯に据える物なので生垣(<see cref="CHORD_ROOT_MAX"/>)より深く許す。</summary>
    const float RINEN_ROOT_MAX = 1.00f;

    /// <summary>**植えた駒(生垣・林縁帯の低木)を根入れで据える**(2026-09-28・EDO-0472)。
    /// <see cref="SeatOnGround"/> は最寄りの 1 点を地表に着けるだけなので、斜面では 1.8m の生垣の下手の端が勾配ぶん浮いた
    /// (十坊 10 区画で生垣 217 駒・林縁帯 14 駒が浮き・最悪 2.63m)。下端の足跡(<see cref="RootToBed"/> ── 当たり = 見えている地表)の
    /// 最大の浮きだけ沈めて、上手を土に埋める(埋めて隠すのが基本・docs/oki-kata.md §4)。
    /// 条件は**硬い**: 沈める量が <paramref name="maxRoot"/> を越える所(駒が崖の縁・石垣の天端の縁を跨いで宙に出る)は植えない → false。
    /// 当たる先: <see cref="IkegakiRow"/>・<see cref="RinenBand"/> ── 類型の生垣付き板塀(ita+ikegaki)の全区画。</summary>
    public static bool RootPlant(GameObject go, float maxRoot)
    {
        var rt = RootToBed(go, Ground, 0.10f);
        if (float.IsNaN(rt.hi) || rt.hi <= 0f) return true;
        if (rt.hi > maxRoot) return false;
        go.transform.position -= Vector3.up * (rt.hi + 0.005f);
        return true;
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
            if (!RootPlant(go, RINEN_ROOT_MAX) || OutsidePlot(go)) { UnityEngine.Object.DestroyImmediate(go); continue; }
            placed.Add(c);
            made++;
        }
        return made;
    }
}
