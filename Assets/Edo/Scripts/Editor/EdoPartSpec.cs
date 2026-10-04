using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

/// <summary>**部材の札**(取り合いのデータ)── 部材ごとに一度だけ定め、組み立ては読むだけ(EDO-0491・2026-09-29 施主「ベストプラクティスに基づいた開発に」)。
/// <para>⭐ Unity の定石(ソケット/接続点)に倣う: 部材が「どこで地面に立ち・どこが正面で・袖がどこへ突き付き・どこを通るか」を
/// **データとして持つ**。⛔ 組み立ての最中に生メッシュを帯や材の名で推し量らない ── 段ごとに別の物差しで測って食い違い、
/// 十坊の門の脇に 1.9m の隙が出た(門を測る物差しが 5 本あった・EDO-0491)。</para>
/// <para>**座標の約束**: 資産の局所座標(倍率を掛ける前)。+X = 門口・走りの方向 / +Z = 外(通り)/ 原点 = ピボット。
/// 置いた駒の世界へは <c>transform.TransformPoint</c> で写す(置くときの倍率 <see cref="Spec.unitScale"/> が掛かる)。
/// `foot` の Vector2 は (x, z)。</para>
/// <para>**作り方は二通り・中身は同じ形**: 自前の部材は Blender が作図の値から書く(`vklib.write_spec`・source=`blender:…`)。
/// 在庫の部材は <see cref="Bake"/> が資産の断面から一度だけ測って案を書き、検め画像で確かめてからコミットする(source=`baked:…`)。
/// どちらも <see cref="Verify"/>(実メッシュとの一致・硬い)が見張る。→ `docs/oki-kata.md` §8</para></summary>
public static class EdoPartSpec
{
    [Serializable] public class Jamb { public float x, z0, z1, y0, y1; }
    [Serializable] public class Span { public float x0, x1, sillY; }   // sillY = 敷居の土台の底からの差(局所・切り下げた扉口は負)
    [Serializable] public class Box { public float x0, x1, z0, z1, y0, y1; }

    /// <summary>札。`kind` = gate / bansho / fence。欄の意味は種別ごと(使わない欄は 0 / null)。</summary>
    [Serializable]
    public class Spec
    {
        public string prefab;          // 資産の道(EdoAssets の値と一致すること)
        public string kind;            // gate / bansho / fence
        public string source;          // blender:<script>(<引数>) / baked:<日付> <関数>
        public float unitScale = 1f;   // 置くときの倍率(在庫の edogoyomi = ES 1.818・自前 = 1)
        public float yBottom;          // 最下点(局所)。自前の門は沓石が敷居より 0.26 下
        // ── 門・番所 ──
        public List<Vector2> foot = new List<Vector2>();   // 地面に立つ所の平面の外形(凸包・局所 x,z)。区画線の判定はこれだけ
        public float front, back;      // 壁体(袖の帯)の正面 +Z・背面 −Z
        public Jamb jambL, jambR;      // 袖が突き付く脇の面(L = −X 側・R = +X 側)。帯の中で**いちばん内へ引っ込む段**
        public Span passage;           // 通り口(門だけ)。参道・庭・本堂の軸はこの芯を読む
        public Span passageKuguri;     // 潜戸の口(長屋門の脇・無ければ null か x1<=x0)。基壇の口・扉の下端はこれも見る
        public Box eave;               // 軒込みの外形(刷るだけ・判定に使わない ── 裁定A)
        public List<string> contact = new List<string>();   // 地面に着ける部材(メッシュ名)。空 = 下端から ROOT_TOUCH の全部。
                                                            // 扉(下に隙があって正)・根入れの飾りを外すときだけ書く(EDO-0491 在庫の冠木門)
        // ── 塀の駒(走りは局所 X)──
        public float faceOut, faceIn;  // 足元の断面の z の外端・内端(局所)
        public float copingOverhang;   // 笠木・軒の走り方向の出(外形の端 − 壁の本体の端・局所)
        public float height;           // 丈(局所)
    }

    /// <summary>袖の帯[m・世界]= 地面から塀が門に当たる高さ(板塀・練塀・長屋の壁の丈の内)。
    /// この帯より上は門と塀の取り合いにも区画の線にも関わらない(軒は越えてよい・裁定A)。</summary>
    public const float BAND_LO = 0.30f, BAND_HI = 1.80f, BAND_STEP = 0.25f;
    /// <summary>足元の断面の高さ[m・世界・最下点から]。</summary>
    public const float FOOT_Y = 0.05f;
    /// <summary>札と実メッシュの食い違いの許容[m・世界](硬い)。</summary>
    public const float VERIFY_TOL = 0.02f;

    static Dictionary<string, Spec> _byPrefab;

    /// <summary>資産の道から札を引く。無ければ null(⛔ 呼ぶ側は推し量りで置かずに退ける ── 硬い)。</summary>
    public static Spec Get(string prefabPath)
    {
        if (_byPrefab == null) Reload();
        Spec s; return prefabPath != null && _byPrefab.TryGetValue(prefabPath, out s) ? s : null;
    }

    public static void Reload()
    {
        _byPrefab = new Dictionary<string, Spec>();
        if (!Directory.Exists(EdoAssets.PartSpecs.Dir)) return;
        foreach (var f in Directory.GetFiles(EdoAssets.PartSpecs.Dir, "*.json"))
        {
            if (f.Replace('\\', '/') == EdoAssets.PartSpecs.GateKinds) continue;
            var s = JsonUtility.FromJson<Spec>(File.ReadAllText(f));
            if (s != null && !string.IsNullOrEmpty(s.prefab)) _byPrefab[s.prefab] = s;
        }
    }

    public static string FileFor(string prefabPath) { return EdoAssets.PartSpecs.Dir + Path.GetFileNameWithoutExtension(prefabPath) + ".json"; }

    public static void Save(Spec s)
    {
        Directory.CreateDirectory(EdoAssets.PartSpecs.Dir);
        File.WriteAllText(FileFor(s.prefab), JsonUtility.ToJson(s, true) + "\n");
        _byPrefab = null;
    }

    /// <summary>類型表の門の語 → 札のファイル名(拡張子なし)。`gate_kinds.json` = {"kinds":[{"kind":..,"spec":..}]}</summary>
    [Serializable] public class GateKind { public string kind, spec; }
    [Serializable] class GateKindTable { public List<GateKind> kinds = new List<GateKind>(); }
    public static List<GateKind> GateKinds()
    {
        if (!File.Exists(EdoAssets.PartSpecs.GateKinds)) return new List<GateKind>();
        return JsonUtility.FromJson<GateKindTable>(File.ReadAllText(EdoAssets.PartSpecs.GateKinds)).kinds;
    }

    // ───────────────────────── 世界へ写す ─────────────────────────
    public static Vector2 W(Transform t, float x, float z, float y = 0f) { var p = t.TransformPoint(new Vector3(x, y, z)); return new Vector2(p.x, p.z); }
    public static Vector2[] FootWorld(Spec s, Transform t) { return s.foot.Select(q => W(t, q.x, q.y, s.yBottom)).ToArray(); }
    /// <summary>脇の面(帯の芯の高さ・z の中ほど)を世界の xz へ。</summary>
    public static Vector2 JambWorld(Transform t, Jamb j) { return W(t, j.x, (j.z0 + j.z1) * 0.5f, (j.y0 + j.y1) * 0.5f); }
    public static Vector2 PassageCenterWorld(Spec s, Transform t) { return W(t, (s.passage.x0 + s.passage.x1) * 0.5f, 0f); }
    /// <summary>正面の芯を世界の xz へ(通り口の芯の前)。</summary>
    public static Vector2 FrontWorld(Spec s, Transform t) { float x = s.passage != null ? (s.passage.x0 + s.passage.x1) * 0.5f : 0f; return W(t, x, s.front); }
    public static float FootArea(Spec s, Transform t)
    {
        var p = FootWorld(s, t); float a = 0f;
        for (int i = 0; i < p.Length; i++) { var u = p[i]; var v = p[(i + 1) % p.Length]; a += u.x * v.y - v.x * u.y; }
        return Mathf.Abs(a) * 0.5f;
    }

    // ───────────────────────── 焼き付け(在庫の部材・一度だけ)─────────────────────────
    /// <summary>資産の局所の三角形(倍率・置き場を掛けない)を列挙する。</summary>
    static IEnumerable<Vector3[]> Tris(GameObject asset)
    {
        var root = asset.transform.worldToLocalMatrix;
        foreach (var mf in asset.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mf.sharedMesh == null) continue;
            var rr = mf.GetComponent<Renderer>(); if (rr == null || !rr.enabled) continue;
            var m = root * mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices; var tri = mf.sharedMesh.triangles;
            var w = new Vector3[vs.Length];
            for (int i = 0; i < vs.Length; i++) w[i] = m.MultiplyPoint3x4(vs[i]);
            for (int i = 0; i + 2 < tri.Length; i += 3) yield return new[] { w[tri[i]], w[tri[i + 1]], w[tri[i + 2]] };
        }
    }

    static List<Vector3> Cut(List<Vector3[]> tris, float y)
    {
        var L = new List<Vector3>();
        foreach (var t in tris)
            for (int e = 0; e < 3; e++)
            {
                Vector3 p = t[e], q = t[(e + 1) % 3];
                if ((p.y - y) * (q.y - y) > 0f) continue;
                float dy = q.y - p.y; if (Mathf.Abs(dy) < 1e-7f) continue;
                L.Add(Vector3.Lerp(p, q, (y - p.y) / dy));
            }
        return L;
    }

    /// <summary>資産の断面から札の案を作る(置かない・資産の局所)。<paramref name="kind"/> = gate / bansho / fence。
    /// ⭐ 帯は**世界の m**で決め、倍率で局所へ割る(在庫の OBJ は ES 倍して置く)。</summary>
    public static Spec Measure(string prefabPath, string kind, float unitScale, out string note)
    {
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        if (asset == null) throw new Exception("資産が無い: " + prefabPath);
        var tris = Tris(asset).ToList();
        var s = new Spec { prefab = prefabPath, kind = kind, unitScale = unitScale };
        float yb = float.MaxValue, yt = float.MinValue, x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        foreach (var t in tris) foreach (var p in t)
        { yb = Mathf.Min(yb, p.y); yt = Mathf.Max(yt, p.y); x0 = Mathf.Min(x0, p.x); x1 = Mathf.Max(x1, p.x); z0 = Mathf.Min(z0, p.z); z1 = Mathf.Max(z1, p.z); }
        s.yBottom = yb; s.height = yt - yb;
        s.eave = new Box { x0 = x0, x1 = x1, z0 = z0, z1 = z1, y0 = yb, y1 = yt };
        float k = 1f / unitScale;
        var notes = new List<string>();

        // 足元
        var foot = Cut(tris, yb + FOOT_Y * k);
        if (foot.Count < 3) foot = Cut(tris, yb + BAND_LO * k);
        if (foot.Count >= 3)
        {
            var xz = foot.Select(p => new Vector2(p.x, p.z)).ToArray();
            s.foot = EdoGeom.HullXZ(xz).Select(i => xz[i]).ToList();
        }
        else notes.Add("⛔ 足元の断面が取れない");

        if (kind == "fence")
        {
            s.faceOut = foot.Count > 0 ? foot.Max(p => p.z) : z1;
            s.faceIn = foot.Count > 0 ? foot.Min(p => p.z) : z0;
            var mid = Cut(tris, yb + s.height * 0.5f);
            if (mid.Count > 0) s.copingOverhang = Mathf.Max(0f, Mathf.Max(mid.Min(p => p.x) - x0, x1 - mid.Max(p => p.x)));
            note = string.Format("{0}: 厚み {1:F3}m・笠木の出 {2:F3}m・丈 {3:F2}m", Path.GetFileName(prefabPath),
                                 (s.faceOut - s.faceIn) * unitScale, s.copingOverhang * unitScale, s.height * unitScale);
            return s;
        }

        // 袖の帯: 段ごとの左右の端 → いちばん内へ引っ込む段
        float bHi = Mathf.Min(BAND_HI * k, s.height * 0.95f);
        float fr = float.MinValue, bk = float.MaxValue, jl = float.MinValue, jr = float.MaxValue;
        var bandPts = new List<Vector3>();
        for (float y = BAND_LO * k; y <= bHi + 1e-4f; y += BAND_STEP * k)
        {
            var sec = Cut(tris, yb + y);
            if (sec.Count == 0) continue;
            bandPts.AddRange(sec);
            jl = Mathf.Max(jl, sec.Min(p => p.x));
            jr = Mathf.Min(jr, sec.Max(p => p.x));
            fr = Mathf.Max(fr, sec.Max(p => p.z));
            bk = Mathf.Min(bk, sec.Min(p => p.z));
        }
        if (bandPts.Count == 0) { note = "⛔ 袖の帯に断面が無い: " + prefabPath; return s; }
        s.front = fr; s.back = bk;
        float tolX = 0.15f * k;
        Func<float, Jamb> jamb = jx =>
        {
            var near = bandPts.Where(p => Mathf.Abs(p.x - jx) <= tolX).ToList();
            return new Jamb { x = jx, z0 = near.Min(p => p.z), z1 = near.Max(p => p.z), y0 = yb + BAND_LO * k, y1 = yb + bHi };
        };
        s.jambL = jamb(jl); s.jambR = jamb(jr);

        if (kind == "gate")
        {
            // 通り口 = 門の芯(原点)を挟む、**奥行 0.2m 以上の塊(柱・壁)**の間の空き。高さ 0.2 / 0.5 / 1.0m の断面の共通部分。
            // ⭐ 奥行の薄い塊(扉の板・召合せの金物・閂・奥行 0.15m 前後)は通り口を塞がない物と見る(在庫の門 5 種の実測・2026-09-29)。
            float left = float.MinValue, right = float.MaxValue;
            foreach (float wy in new[] { 0.2f, 0.5f, 1.0f })
            {
                var sec = Cut(tris, yb + wy * k).OrderBy(p => p.x).ToList();
                int i0 = 0;
                for (int i = 1; i <= sec.Count; i++)
                    if (i == sec.Count || sec[i].x - sec[i - 1].x > 0.05f * k)
                    {
                        var g = sec.GetRange(i0, i - i0); i0 = i;
                        if ((g.Max(p => p.z) - g.Min(p => p.z)) < 0.20f * k) continue;
                        float gx0 = g.First().x, gx1 = g.Last().x;
                        if (gx1 < 0f) left = Mathf.Max(left, gx1);
                        else if (gx0 > 0f) right = Mathf.Min(right, gx0);
                        else { notes.Add("⛔ 門の芯に柱・壁が立っている(高さ " + wy + "m)"); }
                    }
            }
            if (left == float.MinValue || right == float.MaxValue) notes.Add("⛔ 通り口の両脇の柱が取れない");
            else s.passage = new Span { x0 = left, x1 = right };
        }
        note = string.Format("{0}: 正面 {1:F3}・背面 {2:F3}・脇 L {3:F3} R {4:F3}{5}・足元 {6} 点{7}",
            Path.GetFileName(prefabPath), s.front * unitScale, s.back * unitScale, s.jambL.x * unitScale, s.jambR.x * unitScale,
            s.passage != null ? string.Format("・通り口 {0:F3}〜{1:F3}", s.passage.x0 * unitScale, s.passage.x1 * unitScale) : "",
            s.foot.Count, notes.Count > 0 ? " " + string.Join(" ", notes.ToArray()) : "");
        return s;
    }

    /// <summary>在庫の部材の札を焼いて書く(source=baked)。⭐ 書いたら検め画像(<see cref="RenderCheck"/>)で確かめてからコミットする。</summary>
    public static string Bake(string prefabPath, string kind, float unitScale)
    {
        string note;
        var s = Measure(prefabPath, kind, unitScale, out note);
        s.source = "baked:" + DateTime.Now.ToString("yyyy-MM-dd") + " EdoPartSpec.Measure(帯 " + BAND_LO + "〜" + BAND_HI + "m)";
        Save(s);
        return note;
    }

    /// <summary>在庫の部材で札を焼く物(門5種・番所・門の脇に来る塀の端の駒)。自前の部材(薬医門・山門・棟門・練塀・竹矢来)の門は
    /// Blender の write_spec が書く ── ここに足さない。⚠ 練塀の端 `Dobei2mEnd` と竹矢来は自前だが Blender の札がまだ無いので、それまでここで焼く。</summary>
    static readonly (string path, string kind, float scale)[] KIT =
    {
        (EdoAssets.Eg.Kmon, "gate", EdoBuild.ES), (EdoAssets.Eg.Nagayamon, "gate", EdoBuild.ES), (EdoAssets.Eg.Hmon, "gate", EdoBuild.ES),
        (EdoAssets.Eg.Kabukimon, "gate", EdoBuild.ES), (EdoAssets.Eg.KidoOpen, "gate", EdoBuild.ES),
        (EdoAssets.Eg.Bansho, "bansho", EdoBuild.ES),
        (EdoAssets.Eg.DobeiCenter, "fence", EdoBuild.ES), (EdoAssets.Eg.KnagayaC, "fence", EdoBuild.ES),
        (EdoAssets.Own.Dobei2mEnd, "fence", 1f), (EdoAssets.Own.Typ.Takeyarai, "fence", 1f),
    };

    [MenuItem("Edo/部材/取り合いの札を焼く(在庫の門・番所・塀の端)")]
    public static void BakeKitMenu() { Debug.Log(BakeKit()); }

    /// <summary>在庫の部材の札を焼き、検め画像を `UserData/EDO0491/specs/` に撮る。⭐ 画像を見て確かめてからコミットする。</summary>
    public static string BakeKit()
    {
        var lines = new List<string>();
        foreach (var k in KIT)
        {
            try
            {
                lines.Add(Bake(k.path, k.kind, k.scale));
                RenderCheck(Get(k.path), "UserData/EDO0491/specs/" + Path.GetFileNameWithoutExtension(k.path) + ".png");
            }
            catch (Exception ex) { lines.Add("⛔ " + Path.GetFileName(k.path) + ": " + ex.Message); }
        }
        return "在庫の部材の札を焼いた(検め画像 UserData/EDO0491/specs/):\n  " + string.Join("\n  ", lines.ToArray());
    }

    // ───────────────────────── 検め(硬い)─────────────────────────
    /// <summary>札と実メッシュが食い違っていないか(許容 <see cref="VERIFY_TOL"/> m・世界)。返り値 = 食い違いの一覧(空 = 合格)。
    /// 在庫を取り込み直した・Blender で作り直して札を直し忘れた、を捕まえる。</summary>
    public static List<string> Verify(Spec s)
    {
        var bad = new List<string>();
        string note; Spec m;
        try { m = Measure(s.prefab, s.kind, s.unitScale, out note); }
        catch (Exception ex) { bad.Add(ex.Message); return bad; }
        float u = s.unitScale;
        Action<string, float, float> cmp = (name, a, b) => { if (Mathf.Abs(a - b) * u > VERIFY_TOL) bad.Add(string.Format("{0}: 札 {1:F3} / 実 {2:F3}", name, a * u, b * u)); };
        cmp("最下点", s.yBottom, m.yBottom);
        if (s.kind == "fence") { cmp("外の面", s.faceOut, m.faceOut); cmp("内の面", s.faceIn, m.faceIn); cmp("笠木の出", s.copingOverhang, m.copingOverhang); return bad; }
        cmp("正面", s.front, m.front); cmp("背面", s.back, m.back);
        if (s.jambL == null || s.jambR == null) bad.Add("脇の面が無い");
        else { cmp("脇 L", s.jambL.x, m.jambL.x); cmp("脇 R", s.jambR.x, m.jambR.x); }
        if (s.foot == null || s.foot.Count < 3) bad.Add("足元が無い");
        else
        {
            float fx0 = s.foot.Min(p => p.x), fx1 = s.foot.Max(p => p.x), fz0 = s.foot.Min(p => p.y), fz1 = s.foot.Max(p => p.y);
            cmp("足元 x0", fx0, m.foot.Min(p => p.x)); cmp("足元 x1", fx1, m.foot.Max(p => p.x));
            cmp("足元 z0", fz0, m.foot.Min(p => p.y)); cmp("足元 z1", fz1, m.foot.Max(p => p.y));
        }
        if (s.kind == "gate" && s.passage == null) bad.Add("通り口が無い");
        return bad;
    }

    [MenuItem("Edo/部材/札を検める(全部)")]
    public static void VerifyAllMenu() { Debug.Log(VerifyAll()); }

    public static string VerifyAll()
    {
        Reload();
        var lines = new List<string>(); int ng = 0;
        foreach (var s in _byPrefab.Values.OrderBy(v => v.prefab))
        {
            var b = Verify(s);
            if (b.Count > 0) ng++;
            lines.Add((b.Count == 0 ? "⭕ " : "⛔ ") + Path.GetFileName(s.prefab) + (b.Count == 0 ? "" : " — " + string.Join(" / ", b.ToArray())));
        }
        foreach (var gk in GateKinds())
            if (!File.Exists(EdoAssets.PartSpecs.Dir + gk.spec + ".json")) { ng++; lines.Add("⛔ 門の語 " + gk.kind + " の札が無い: " + gk.spec); }
        return "部材の札の検め: " + (ng == 0 ? "⭕ 全部通った" : "⛔ " + ng + " 件") + "\n  " + string.Join("\n  ", lines.ToArray());
    }

    // ───────────────────────── 検め画像 ─────────────────────────
    /// <summary>札の線を重ねた平面の検め画像(上から・袖の帯の断面を灰・足元を緑・脇を赤・正面/背面を青・通り口を黄)。
    /// ⭐ 焼いた札は必ずこれを見てからコミットする(作った本人が目で確かめる)。</summary>
    public static string RenderCheck(Spec s, string outPng, int px = 900)
    {
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(s.prefab);
        var tris = Tris(asset).ToList();
        var pts = new List<Vector3>();
        float k = 1f / s.unitScale;
        for (float y = BAND_LO * k; y <= Mathf.Min(BAND_HI * k, s.height * 0.95f) + 1e-4f; y += BAND_STEP * k) pts.AddRange(Cut(tris, s.yBottom + y));
        var e = s.eave;
        float x0 = e.x0 - 0.3f * k, x1 = e.x1 + 0.3f * k, z0 = e.z0 - 0.3f * k, z1 = e.z1 + 0.3f * k;
        float sc = px / Mathf.Max(x1 - x0, z1 - z0);
        int W = Mathf.CeilToInt((x1 - x0) * sc), H = Mathf.CeilToInt((z1 - z0) * sc);
        var tex = new Texture2D(W, H, TextureFormat.RGB24, false);
        var bg = new Color(0.97f, 0.96f, 0.93f);
        var px2 = Enumerable.Repeat(bg, W * H).ToArray();
        Action<float, float, Color> dot = (x, z, c) =>
        {
            int ix = Mathf.RoundToInt((x - x0) * sc), iz = Mathf.RoundToInt((z - z0) * sc);
            for (int a = -1; a <= 1; a++) for (int b = -1; b <= 1; b++)
            { int X = ix + a, Z = iz + b; if (X >= 0 && X < W && Z >= 0 && Z < H) px2[Z * W + X] = c; }
        };
        Action<float, float, float, float, Color> line = (ax, az, bx, bz, c) =>
        { int n = Mathf.CeilToInt(Mathf.Max(Mathf.Abs(bx - ax), Mathf.Abs(bz - az)) * sc) + 1; for (int i = 0; i <= n; i++) dot(Mathf.Lerp(ax, bx, i / (float)n), Mathf.Lerp(az, bz, i / (float)n), c); };
        line(e.x0, e.z0, e.x1, e.z0, new Color(.75f, .75f, .75f)); line(e.x1, e.z0, e.x1, e.z1, new Color(.75f, .75f, .75f));
        line(e.x1, e.z1, e.x0, e.z1, new Color(.75f, .75f, .75f)); line(e.x0, e.z1, e.x0, e.z0, new Color(.75f, .75f, .75f));
        foreach (var p in pts) dot(p.x, p.z, new Color(.35f, .35f, .35f));
        for (int i = 0; i < s.foot.Count; i++) { var a = s.foot[i]; var b = s.foot[(i + 1) % s.foot.Count]; line(a.x, a.y, b.x, b.y, new Color(.1f, .6f, .2f)); }
        if (s.kind != "fence")
        {
            line(e.x0, s.front, e.x1, s.front, new Color(.15f, .35f, .85f)); line(e.x0, s.back, e.x1, s.back, new Color(.15f, .35f, .85f));
            if (s.jambL != null) line(s.jambL.x, s.jambL.z0, s.jambL.x, s.jambL.z1, new Color(.85f, .1f, .1f));
            if (s.jambR != null) line(s.jambR.x, s.jambR.z0, s.jambR.x, s.jambR.z1, new Color(.85f, .1f, .1f));
            if (s.passage != null) line(s.passage.x0, 0f, s.passage.x1, 0f, new Color(.95f, .75f, .05f));
        }
        tex.SetPixels(px2); tex.Apply();
        Directory.CreateDirectory(Path.GetDirectoryName(outPng));
        File.WriteAllBytes(outPng, tex.EncodeToPNG());
        UnityEngine.Object.DestroyImmediate(tex);
        return outPng;
    }
}
