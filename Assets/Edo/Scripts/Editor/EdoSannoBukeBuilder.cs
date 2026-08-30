// 山王社周辺・武家地+社家ビルダー (2026-08-11)
//   赤=樹下近江守(神主) 黄=社人八家 水=山王坂参道 緑=丹羽左京大夫長富(二本松藩10万700石)
//   紫=京極備中守高富(峯山藩1万1144石) 白=内藤紀伊守信親(村上藩5万90石)
// 【考証 2026-08-11 Web調査(NDL1286657 IIIF実見+CODH Map#7+溜池遺跡発掘報告ほか)】
//   ・丹羽=上屋敷(直違紋を原画像実見, 7-081)。外様大広間詰。**表門=東辺**(下の訂正 2026-08-31)。
//     跡地=衆議院議員会館+官邸の一部。溜池遺跡発掘(都埋文258)で家臣長屋・蔵・池跡・境界石垣を確認。
//   ・京極=上屋敷(四つ目結紋実見, 7-082)。菊間詰(譜代格)。**表門=東辺**(下の訂正 2026-08-31)。
//   ・内藤=上屋敷(下がり藤紋実見, 7-083)。譜代。当主=内藤信親(紀伊守, 嘉永4〜文久2老中)。
//     表門=北西向き(文字の頭)。南東辺は溜池水際に直接面する。跡地=山王パークタワー一帯。
//   ・社人八家=切絵図原画像で短冊8枚を判読: 西宮頼母/千勝隼人/千勝主水/金丸靱負/小川織部/谷左近/
//     遠藤伊賀/伯耆大学(社家6+巫女2=8戸と整合)。短冊は小路に面する。
//   ・樹下近江守=神主(祝部氏, 代々近江守)。薬医門級の屋根付き門+式台玄関の母屋+土塀【類型】。
//   ・山王坂=永田馬場から南西へ下り社頭へ至る表参道(現・山王坂と同経路)。切絵図に鳥居2基
//     (一の鳥居=永田町寄り/二の鳥居=門前町・観理院手前=既設)。門前町=参道が折れる辻の北西の小さなL字。
// 【⛔ 訂正 2026-08-31 — EDO-0072(丹羽セッションの再考証)】
//   ・**丹羽・京極の表門は東辺が正しい。** NDL1286657(尾張屋版「外櫻田繪圖」)を IIIF 実見し
//     PIL rotate(-90, expand=True) でシーン方位へ補正すると、丹羽・京極とも**文字の頭は東を指す**。
//     ⛔ 旧注記「丹羽=北東の通り(山王坂)沿い」「京極は切絵図では丹羽と同じ北の通りに面する」は撤回。
//   ・⭕ **実装は最初から東辺で正しい**(下の L66/L69/L71・Stage4_Niwa・Stage5_Kyogoku)。
//     誤っていたのはこのヘッダ注記だけで、コードには手を入れていない。
//   ・⭐ これで**切絵図と下書きが一致**した。従前の「配置は下書き優先」(=切絵図を上書きする扱い)は不要。
//   ・⚠ **京極側の図と実装が同じ前提で正しいかは未確認**(丹羽セッションの申し送り)。
//   ・⚠ **内藤も同じ病を持つ疑い(当方が発見・未解決)**: 上の注記は「表門=北西向き(文字の頭)」だが、
//     L66 と Stage6 の実装は「北辺東寄り x≈-106・**北向き**」。どちらが正かは切絵図の再実見が要る。
//     ⛔ 丹羽・京極と同型(ヘッダだけ旧説)の可能性が高いので、注記を根拠に実装を動かさないこと。
// 【地形】丹羽/京極境の近代掘削(ホテル/ビル基礎跡)はラプラシアン緩和で復元済(2026-08-11,
//   backup=scratchpad/niwa_kyogoku_backup_844_889_77x41.bin)。他は現地形追従・造成ゼロ。
//   ⛔ **訂正 2026-08-31 — この「造成ゼロ」は丹羽では成り立たない。** 発掘報告(都埋文258『溜池遺跡』
//     抄録)に「丹羽家屋敷が西側の低地を**順次埋め立て造成**して屋敷化」の記述がある。
//     NaturalMode=true の前提と矛盾する。⚠ 京極・内藤にも同種の造成記録が無いか要確認。
//     ⛔ この矛盾を残したまま3邸の面の高さを既成事実にしない(EDO-0072)。
// 【敷地内構成】各屋敷の指図は未発見のため一般類型(典拠: 格式論+発掘の長屋地区の存在)。
//   丹羽の池跡は発掘で確認されるが位置・形状不明のため未再現。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoSannoBukeBuilder
{
    const string PHei = EdoAssets.Eg.DobeiCenter;
    const string PKmon = EdoAssets.Eg.Kmon;
    const string PNmon = EdoAssets.Eg.Nagayamon;
    const string PKabuki = EdoAssets.Eg.Kabukimon;
    const string PBansho = EdoAssets.Eg.Bansho;
    const string PKura = EdoAssets.Eg.Kura;
    const string PKido = EdoAssets.Eg.KidoOpen;
    const string PItabei5 = EdoAssets.Eg.Itabei5;
    const string PHouse = EdoAssets.VK.House;
    const string PHouseB = EdoAssets.VK.HouseB;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PBigHouse = EdoAssets.VK.BigHouse;
    const string PManor = EdoAssets.VK.Manor;
    const string PShop01 = EdoAssets.Eg.Shop01;
    const string PShop02 = EdoAssets.Eg.Shop02;
    static string[] Pines = {
        EdoAssets.JG.PineBig01,
        EdoAssets.JG.PineBig02,
        EdoAssets.JG.PineBig03 };
    static string[] Shrubs = {
        EdoAssets.JC.Azalea01,
        EdoAssets.JC.Azalea03,
        EdoAssets.JG.Boxwood01 };
    static string[] Bamboo = {
        EdoAssets.JG.BambooBig01,
        EdoAssets.JG.BambooBig02 };
    const string PTobi = EdoAssets.JG.TobiIshi01;
    const string PKasuga = EdoAssets.Own.KasugaLantern;
    public const float ES = 1.818f;

    // ---------- 区画(正典 = docs/Sashizu/parcels.json / CLAUDE.md 規則10) ----------
    // 2026-08-26 json採用(ユーザー裁定)。JUGE は 6→8点(NE角に z948 のノッチ=辺5,6 が増えた。
    // 岡部共有の北辺は旧辺4→新辺4 のまま 1:1 対応)。二重定義は 2026-08-26 解消 —
    // 旧代用の sannosha_juge 矩形を削除し sannobuke_juge に一本化(category=jisha。
    // シーンの実体はこの区画=当ビルダー Stage1 の建て方に沿っていた)。
    public static Vector2[] JUGE { get { return EdoParcels.Get("sannobuke_juge"); } }
    public static Vector2[] SHANIN { get { return EdoParcels.Get("sannobuke_shanin"); } }
    // 2026-08-11改訂(ユーザー下書き第2版+門印=三角形):
    //   丹羽・京極の表門=東辺(東の永田町方面の南北通りへ)、内藤の表門=北辺東寄り(x≈-106)北向き。
    //   内藤と丹羽SW/京極は背中合わせ(間に道なし。共有塀は内藤が受け持つ)。
    // 丹羽: 0=E腕S(京極N共有) 1=SW塊E(京極W共有) 2=SW塊S(内藤N共有=skip) 3=SW塊W 4=(z813.9のノッチ)
    //       5=W(通り沿い長屋) 6=N(山王坂) 7=E(表門)
    public static Vector2[] NIWA { get { return EdoParcels.Get("sannobuke_niwa"); } }
    // 京極: 0=W(丹羽共有=skip) 1=N(丹羽共有=skip) 2=E(表門) 3=S(内藤共有=skip)
    public static Vector2[] KYOGOKU { get { return EdoParcels.Get("sannobuke_kyogoku"); } }
    // 内藤: 0..8=SW周(堀端)。2026-08-26 json採用で 11→12点 — 北辺(z≈677.7)が
    //   x=-126.79 で辺9+辺10 に割れた(表門 x≈-106 は辺9 側のまま)。旧辺10(W)→辺11。
    public static Vector2[] NAITO { get { return EdoParcels.Get("sannobuke_naito"); } }
    // 山王坂コリドー(splat用)
    static readonly Vector2[] SANDO_AXIS = { new Vector2(-371f, 894f), new Vector2(-131f, 899f) };

    // ---------- helpers ----------
    static float Ground(float x, float z) { return EdoBuild.Ground(x, z); }
    static GameObject Place(string path, Vector3 pos, float ry, Vector3 scale, Transform parent, string name)
    { return EdoNishiTameikeBuilder.Place(path, pos, ry, scale, parent, name); }
    static Bounds RB(GameObject go) { return EdoNishiTameikeBuilder.RB(go); }
    static void SeatBottom(GameObject go, float y) { EdoNishiTameikeBuilder.SeatBottom(go, y); }
    static Transform Group(string root, string child)
    {
        var r = GameObject.Find(root);
        if (r == null) { r = new GameObject(root); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EdoYashikiPrefab.EnsureEditable(r);   // ★ プレハブ化済みなら解く(でないと組み替えが黙って失敗する)
        var cur = r.transform;
        if (string.IsNullOrEmpty(child)) return cur;
        foreach (var seg in child.Split('/'))
        {
            var nx = cur.Find(seg);
            if (nx == null) { var g = new GameObject(seg); Undo.RegisterCreatedObjectUndo(g, "grp"); g.transform.SetParent(cur, false); nx = g.transform; }
            cur = nx;
        }
        return cur;
    }
    static Material Mat(Color c) { var m = new Material(Shader.Find("Universal Render Pipeline/Lit")); m.color = c; return m; }
    static void CenterSeat(GameObject go, float x, float z, float sink = 0.12f)
    {
        var b = RB(go);
        go.transform.position += new Vector3(x - b.center.x, 0, z - b.center.z);
        b = RB(go);
        float gmn = float.MaxValue;
        for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++)
            gmn = Mathf.Min(gmn, Ground(b.center.x + i * b.extents.x, b.center.z + j * b.extents.z));
        go.transform.position += new Vector3(0, (gmn - sink) - b.min.y, 0);
    }
    // 独立門+番所(kagami内側検証つき)。fout=門の外向き
    static float PlaceGate(string path, Transform monGrp, Vector2 gate, Vector2 fout, int bansho, string name, System.Text.StringBuilder sb)
    {
        float basePad = Ground(gate.x, gate.y);
        Vector2 inw = -fout;
        float psiIn = Mathf.Atan2(inw.x, inw.y) * Mathf.Rad2Deg;
        var mon = Place(path, Vector3.zero, psiIn, Vector3.one * ES, monGrp, name);
        CenterSeat(mon, gate.x, gate.y, 0.05f);
        float kmn = float.MaxValue, kmx = float.MinValue;
        foreach (var mf in mon.GetComponentsInChildren<MeshFilter>())
        {
            if (!mf.gameObject.name.ToLower().Contains("kagami")) continue;
            foreach (var vtx in mf.sharedMesh.vertices)
            { var wp = mf.transform.TransformPoint(vtx); float pr = wp.x * inw.x + wp.z * inw.y; kmn = Mathf.Min(kmn, pr); kmx = Mathf.Max(kmx, pr); }
        }
        if (kmn != float.MaxValue)
        {
            var mc = RB(mon).center;
            if ((kmn + kmx) * 0.5f < mc.x * inw.x + mc.z * inw.y)
            { mon.transform.rotation *= Quaternion.Euler(0, 180, 0); CenterSeat(mon, gate.x, gate.y, 0.05f); sb.AppendLine(name + " flipped"); }
        }
        // 実体半幅
        float wmn = float.MaxValue, wmx = float.MinValue;
        Vector2 uh = new Vector2(fout.y, -fout.x);
        foreach (var mf in mon.GetComponentsInChildren<MeshFilter>())
            foreach (var vtx in mf.sharedMesh.vertices)
            {
                var wp = mf.transform.TransformPoint(vtx);
                if (wp.y < basePad + 0.5f || wp.y > basePad + 4.5f) continue;
                float pr = (wp.x - gate.x) * uh.x + (wp.z - gate.y) * uh.y;
                wmn = Mathf.Min(wmn, pr); wmx = Mathf.Max(wmx, pr);
            }
        float gateHalf = Mathf.Max(Mathf.Abs(wmn), Mathf.Abs(wmx));
        for (int i = 0; i < bansho; i++)
        {
            float side = (bansho == 1) ? 1f : (i == 0 ? 1f : -1f);
            float extrude = path == PNmon ? 1.7f : 0.5f;   // 長屋門は格子出
            Vector2 bp = gate + uh * (side * (gateHalf + 3.4f)) + fout * extrude;
            float bg2 = Ground(bp.x, bp.y);
            var ban = Place(PBansho, new Vector3(bp.x, bg2, bp.y), psiIn + 180f, Vector3.one * ES, monGrp, name + "_Bansho" + i);
            SeatBottom(ban, bg2 - 0.05f);
            var f3 = ban.transform.forward;
            if (f3.x * fout.x + f3.z * fout.y < 0)
                ban.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(fout.x, fout.y) * Mathf.Rad2Deg, 0);
        }
        sb.AppendLine(name + " halfW=" + gateHalf.ToString("F2"));
        return gateHalf;
    }
    // 前辺=門の左右2セグメントの塀
    static void FrontWall(Transform kak, Vector2 a, Vector2 b, Vector2 outw, Vector2 gate, float gateHalf, string prefix)
    {
        Vector2 dir = (b - a).normalized;
        Vector2 gL = gate - dir * (gateHalf - 0.15f), gR = gate + dir * (gateHalf - 0.15f);
        if (Vector2.Distance(a, gL) > 1.6f && Vector2.Dot(gL - a, dir) > 0)
            EdoNishiTameikeBuilder.DobeiRun(kak, a, gL, outw, prefix + "_L", true, 0, Vector2.zero, -1);
        if (Vector2.Distance(gR, b) > 1.6f && Vector2.Dot(b - gR, dir) > 0)
            EdoNishiTameikeBuilder.DobeiRun(kak, gR, b, outw, prefix + "_R", true, 0, Vector2.zero, -1);
    }
    // OBB制約付き再配置(建物クリーンアップ)
    public static string FixGroup(string grp, Vector2[] poly, string[] names, float[] margins, float buriedCap)
    {
        var sb = new System.Text.StringBuilder();
        var root = GameObject.Find(grp); if (root == null) return "no group";
        var bld = root.transform.Find("Buildings"); if (bld == null) return "no buildings";
        var obsB = new List<Bounds>();
        var mg = root.transform.Find("Omotemon");
        if (mg != null) foreach (Transform m in mg) { var rb = RB(m.gameObject); if (rb.size.sqrMagnitude > 0.01f) obsB.Add(rb); }
        float bxMin = poly.Min(p => p.x), bxMax = poly.Max(p => p.x), bzMin = poly.Min(p => p.y), bzMax = poly.Max(p => p.y);
        for (int bi = 0; bi < names.Length; bi++)
        {
            var it = bld.Find(names[bi]); if (it == null) continue;
            float mnx, mxx, mnz, mxz, mny;
            EdoSannoJuboBuilder.ObbFootprint(it, out mnx, out mxx, out mnz, out mxz, out mny);
            if (mnx == float.MaxValue) continue;
            var pts = new List<Vector3>();
            for (int i = 0; i <= 3; i++) for (int j = 0; j <= 3; j++)
            { if (i > 0 && i < 3 && j > 0 && j < 3) continue; pts.Add(new Vector3(Mathf.Lerp(mnx, mxx, i / 3f), mny, Mathf.Lerp(mnz, mxz, j / 3f))); }
            var curC = it.TransformPoint(new Vector3((mnx + mxx) / 2, mny, (mnz + mxz) / 2));
            bool ok0 = true; float bur0 = float.MinValue;
            foreach (var lp in pts)
            {
                var wp = it.TransformPoint(lp);
                var p2 = new Vector2(wp.x, wp.z);
                if (!EdoGeom.PIP(poly, p2) || EdoGeom.DistToPolyEdge(poly, p2) < margins[bi] * 0.75f) ok0 = false;
                float g = Ground(wp.x, wp.z);
                bur0 = Mathf.Max(bur0, g - wp.y);
            }
            if (ok0 && bur0 <= buriedCap) { obsB.Add(RB(it.gameObject)); continue; }
            float bestScore = float.MaxValue; Vector2 best = Vector2.zero; bool found = false;
            for (float cx = bxMin; cx <= bxMax; cx += 1.5f)
                for (float cz = bzMin; cz <= bzMax; cz += 1.5f)
                {
                    var delta = new Vector3(cx - curC.x, 0, cz - curC.z);
                    bool ok = true; float mn = float.MaxValue, mx = float.MinValue;
                    foreach (var lp in pts)
                    {
                        var wp = it.TransformPoint(lp) + delta;
                        var p2 = new Vector2(wp.x, wp.z);
                        if (!EdoGeom.PIP(poly, p2) || EdoGeom.DistToPolyEdge(poly, p2) < margins[bi]) { ok = false; break; }
                        float g = Ground(wp.x, wp.z);
                        mn = Mathf.Min(mn, g); mx = Mathf.Max(mx, g);
                    }
                    if (!ok) continue;
                    float hw = (mxx - mnx) * Mathf.Abs(it.localScale.x) * 0.5f, hd = (mxz - mnz) * Mathf.Abs(it.localScale.z) * 0.5f;
                    float rad = Mathf.Max(hw, hd) + 0.8f;
                    foreach (var ob in obsB)
                    {
                        if (ob.size.sqrMagnitude < 0.01f) continue;
                        float ddx = Mathf.Max(Mathf.Abs(cx - ob.center.x) - ob.extents.x, 0);
                        float ddz = Mathf.Max(Mathf.Abs(cz - ob.center.z) - ob.extents.z, 0);
                        if (Mathf.Sqrt(ddx * ddx + ddz * ddz) < rad * 0.8f) { ok = false; break; }
                    }
                    if (!ok) continue;
                    float score = (mx - mn) * 4f + Vector2.Distance(new Vector2(cx, cz), new Vector2(curC.x, curC.z)) * 0.10f;
                    if (score < bestScore) { bestScore = score; best = new Vector2(cx, cz); found = true; }
                }
            if (!found) { sb.AppendLine("✗ " + grp + "/" + names[bi] + " 解なし"); obsB.Add(RB(it.gameObject)); continue; }
            sb.AppendLine(grp + "/" + names[bi] + " -> " + EdoSannoJuboBuilder.MoveToObb(grp, "Buildings/" + names[bi], best.x, best.y));
            obsB.Add(RB(it.gameObject));
        }
        return sb.ToString();
    }
    // 井戸(合成)
    static void Well(Transform parent, float x, float z)
    {
        float y = Ground(x, z);
        var g = new GameObject("Ido");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "well");
        var stone = Mat(new Color(0.55f, 0.55f, 0.52f));
        var wood = Mat(new Color(0.38f, 0.28f, 0.18f));
        var curb = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        curb.name = "curb"; curb.transform.SetParent(g.transform, false);
        curb.transform.localScale = new Vector3(1.3f, 0.35f, 1.3f);
        curb.transform.localPosition = new Vector3(0, 0.35f, 0);
        curb.GetComponent<Renderer>().sharedMaterial = stone;
        for (int i = 0; i < 2; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.12f, 1.1f, 0.12f);
            post.transform.localPosition = new Vector3(i == 0 ? -0.85f : 0.85f, 1.1f, 0);
            post.GetComponent<Renderer>().sharedMaterial = wood;
        }
    }
    // 石鳥居(明神鳥居, 合成) — ShaBuilderと同型
    static void Torii(Transform parent, string name, float x, float z, Vector2 passDir)
    {
        float y = Ground(x, z);
        var g = new GameObject(name);
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(x, y, z);
        Undo.RegisterCreatedObjectUndo(g, "torii");
        var stone = Mat(new Color(0.62f, 0.61f, 0.58f));
        float H = 7.6f, W = 6.6f;
        var posts = new GameObject[2];
        for (int i = 0; i < 2; i++)
        {
            var p = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            p.name = "hashira" + i; p.transform.SetParent(g.transform, false);
            p.transform.position = g.transform.position + new Vector3(0, H * 0.5f - 0.2f, (i == 0 ? -W : W) * 0.5f);
            p.transform.localScale = new Vector3(0.64f, H * 0.5f, 0.64f);
            p.transform.rotation = Quaternion.Euler(0, 0, i == 0 ? -3f : 3f);
            p.GetComponent<Renderer>().sharedMaterial = stone;
            posts[i] = p;
            var k = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            k.name = "kamehara" + i; k.transform.SetParent(g.transform, false);
            k.transform.position = g.transform.position + new Vector3(0, 0.25f, (i == 0 ? -W : W) * 0.5f);
            k.transform.localScale = new Vector3(0.98f, 0.25f, 0.98f);
            k.GetComponent<Renderer>().sharedMaterial = stone;
        }
        Action<string, Vector3, Vector3> box = (nm, pos, sc) =>
        {
            var b = GameObject.CreatePrimitive(PrimitiveType.Cube);
            b.name = nm; b.transform.SetParent(g.transform, false);
            b.transform.position = g.transform.position + pos; b.transform.localScale = sc;
            b.GetComponent<Renderer>().sharedMaterial = stone;
        };
        box("shimaki", new Vector3(0, H - 0.55f, 0), new Vector3(0.55f, 0.5f, W + 1.7f));
        box("kasagi", new Vector3(0, H, 0), new Vector3(0.62f, 0.5f, W + 2.6f));
        box("nuki", new Vector3(0, H - 1.75f, 0), new Vector3(0.4f, 0.42f, W + 1.1f));
        box("gakuzuka", new Vector3(0, H - 1.15f, 0), new Vector3(0.35f, 0.75f, 0.5f));
        // 柱の並び軸 ⊥ 通行方向 に合わせる
        var sep = posts[1].transform.position - posts[0].transform.position; sep.y = 0; sep.Normalize();
        var want = new Vector3(-passDir.y, 0, passDir.x);
        float delta = Vector3.SignedAngle(sep, want, Vector3.up);
        g.transform.rotation = Quaternion.AngleAxis(delta, Vector3.up) * g.transform.rotation;
    }

    // ---------- Stage 0: 旧樹下邸・旧門前町の撤去 ----------
    public static string Stage0_Demolish()
    {
        var sb = new System.Text.StringBuilder();
        foreach (var n in new string[] { "Edo_Sanno_JugeYashiki", "Edo_Sanno_Monzencho" })
        {
            var g = GameObject.Find(n);
            if (g != null) { UnityEngine.Object.DestroyImmediate(g); sb.AppendLine("destroyed " + n); }
        }
        return sb.ToString();
    }

    // ---------- Stage 1: 樹下近江守邸(新区画) ----------
    public static string Stage1_Juge()
    {
        const string G = "Edo_Sanno_JugeYashiki";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Juge";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        Vector2 gate = new Vector2(-388f, 912.1f);   // 南辺東寄り(参道の辻へ最短)
        Vector2 fout = new Vector2(0.008f, -1f).normalized;
        float gateHalf = PlaceGate(PKabuki, monGrp, gate, fout, 0, "Mon", sb);
        int N = JUGE.Length;
        // 辺4 = JUGE[4]→[5](-528.9,956.7)→(-389.0,958.2) 139.9m は**岡部筑前守邸との共有境界**。
        // (2026-08-26 json採用。旧辺4 140.6m と 1:1 対応 — skip は辺4 のまま。json で増えた
        //  NE角のノッチ辺5,6 は樹下側の塀として建てる)
        // ⚠ **岡部が持つ**(ユーザー裁定 2026-08-19、確度U)。北辺 = 土井との境(指図 其十一)と同じ規則。
        //   裏づけは「囲いは1条」の所見のみ([丸の内三丁目] 確度A) — どちらが担うかの規則は史料未確認。
        //   ここを建てていたので岡部の Hei_S_Sk/Te/Mz と**二重**になっていた(間隔 1.06〜1.12m)。
        //   しかも岡部側は主郭が 1.4〜7.2m 高く IG_S_Sk(壁高 8.0m)が立つ。その法尻は
        //   境界線を 2.8m 越えて樹下側へ出る(法尻 z≈944.1 < 境界 z≈946.0)ので、
        //   この塀は石垣の裾に**干渉**してもいた。塀は擁壁の天端に載るもので、法尻には立たない。
        for (int i = 0; i < N; i++)
        {
            if (i == 4) continue;                       // 岡部共有 = 岡部所有 skip
            Vector2 a = JUGE[i], b = JUGE[(i + 1) % N];
            Vector2 outw = -EdoGeom.InwardNormal(JUGE, i);
            if (i == 0)
                FrontWall(kak, a, b, outw, gate, gateHalf + 0.5f, "Hei_F");
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        var bg = Group(G, "Buildings");
        // 式台玄関の母屋(門正対)+台所+物置+井戸
        var shu = Place(PHouse, Vector3.zero, 180f, Vector3.one * 0.95f, bg, "Shuoku");
        CenterSeat(shu, -390f, 928f);
        var dai = Place(PSmallHouse, Vector3.zero, 90f, Vector3.one * 0.7f, bg, "Daidokoro");
        CenterSeat(dai, -378.5f, 935f);
        var mono = Place(PKura, Vector3.zero, 90f, Vector3.one * ES * 0.8f, bg, "Monooki");
        CenterSeat(mono, -408f, 934f);
        Well(bg, -400f, 924f);
        // 庭: 東半=刈込+飛石、西半=松林(山際の社叢続き)
        var gg = Group(G, "Garden");
        var rnd = new System.Random(3110);
        for (int i = 0, gd = 0; i < 14 && gd < 600; gd++)
        {
            float px = Mathf.Lerp(-508f, -378f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(915f, 944f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!EdoGeom.PIP(JUGE, p2) || EdoGeom.DistToPolyEdge(JUGE, p2) < 2.5f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2f && px < rb2.max.x + 2f && pz > rb2.min.z - 2f && pz < rb2.max.z + 2f) { nearB = true; break; } }
            if (nearB) continue;
            bool west = px < -430f;
            float y = Ground(px, pz);
            if (west || rnd.NextDouble() < 0.4)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.6f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.6f * (float)rnd.NextDouble()), gg, "Karikomi_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        for (float tt = 0; tt <= 1.001f; tt += 0.12f)
        {
            Vector2 p = Vector2.Lerp(gate + new Vector2(0, 2.5f), new Vector2(-390f, 921f), tt);
            float y = Ground(p.x, p.y);
            var go = Place(PTobi, new Vector3(p.x, y + 0.03f, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * 1.85f, gg, "Tobi_" + tt);
            SeatBottom(go, y + 0.02f);
        }
        return sb.ToString() + "juge done";
    }

    // ---------- Stage 2: 社人八家 ----------
    static readonly string[] ShaninNames = { "Nishinomiya", "ChikatsuHayato", "ChikatsuMondo", "Kanamaru", "Ogawa", "TaniSakon", "EndoIga", "HokiDaigaku" };
    public static string Stage2_Shanin()
    {
        const string G = "Edo_Sanno_Shanin8";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Shanin";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var root = Group(G, null);
        // 短冊分割: 西辺(通り側) P0(-372.8,661.5)→P1(-373.6,809.5) を8等分
        Vector2 wA = SHANIN[0], wB = SHANIN[1];
        Vector2 eA = SHANIN[3], eB = SHANIN[2];   // 東辺(南→北)
        var rnd = new System.Random(888);
        for (int lot = 0; lot < 8; lot++)
        {
            float t0 = lot / 8f, t1 = (lot + 1) / 8f, tc = (t0 + t1) / 2;
            Vector2 w0 = Vector2.Lerp(wA, wB, t0), w1 = Vector2.Lerp(wA, wB, t1), wc = Vector2.Lerp(wA, wB, tc);
            Vector2 e0 = Vector2.Lerp(eA, eB, t0), e1 = Vector2.Lerp(eA, eB, t1), ec = Vector2.Lerp(eA, eB, tc);
            var lotGrp = Group(G, ShaninNames[lot]);
            Vector2 outW = new Vector2(-1f, 0.005f).normalized;
            // 表(西)の板塀: 木戸開口(中央2.2m)
            Vector2 gL = Vector2.Lerp(w0, w1, 0.5f) - (w1 - w0).normalized * 1.1f;
            Vector2 gR = Vector2.Lerp(w0, w1, 0.5f) + (w1 - w0).normalized * 1.1f;
            EdoSannoJuboBuilder.PanelRun(lotGrp, w0, gL, outW, "Itabei_L", PItabei5, Vector2.zero, -1);
            EdoSannoJuboBuilder.PanelRun(lotGrp, gR, w1, outW, "Itabei_R", PItabei5, Vector2.zero, -1);
            // 裏(東)の板塀は列全体で一度(lot0のみ)
            if (lot == 0)
                EdoSannoJuboBuilder.PanelRun(lotGrp, eA, eB, new Vector2(1f, 0f), "Itabei_Back", PItabei5, Vector2.zero, -1);
            // 母屋(平屋, 西向き)
            var house = Place(PSmallHouse, Vector3.zero, -90f, Vector3.one * 0.72f, lotGrp, "Shuoku");
            Vector2 hc = wc + new Vector2(9.5f, 0);
            CenterSeat(house, hc.x, hc.y);
            // 裏の生垣・木
            float px = wc.x + 20f + (float)rnd.NextDouble() * 4f, pz = wc.y + ((float)rnd.NextDouble() * 6f - 3f);
            if (EdoGeom.PIP(SHANIN, new Vector2(px, pz)))
            {
                float y = Ground(px, pz);
                var tr = Place(rnd.NextDouble() < 0.4 ? Bamboo[rnd.Next(2)] : Pines[rnd.Next(Pines.Length)],
                    new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * 1.35f, lotGrp, "Tree");
                SeatBottom(tr, y - 0.05f);
            }
        }
        sb.AppendLine("shanin 8 lots done");
        return sb.ToString();
    }

    // ---------- Stage 3: 山王坂(一の鳥居・並木・門前町L字・木戸) ----------
    public static string Stage3_Sando()
    {
        const string G = "Edo_Sanno_Monzencho";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Sando/Monzen";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var root = Group(G, null);
        var sando = Group("Edo_Sanno_Sha", "Sando");
        // 一の鳥居(参道東端, 通行=参道軸)
        Vector2 axis = (SANDO_AXIS[1] - SANDO_AXIS[0]).normalized;
        Torii(sando, "IchinoTorii", -140f, 898.8f, axis);
        // 参道並木(松, 両縁)
        var nm = Group("Edo_Sanno_Sha", "Sando/Namiki");
        var rnd = new System.Random(1211);
        for (float t = 18f; t < 228f; t += 14f)
        {
            Vector2 c = SANDO_AXIS[0] + axis * t;
            foreach (float s in new float[] { -11.5f, 11.5f })
            {
                Vector2 p = c + new Vector2(-axis.y, axis.x) * s + new Vector2((float)rnd.NextDouble() * 1.6f - 0.8f, (float)rnd.NextDouble() * 1.6f - 0.8f);
                float y = Ground(p.x, p.y);
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(p.x, y, p.y), (float)rnd.NextDouble() * 360f, Vector3.one * (1.7f * (0.9f + 0.35f * (float)rnd.NextDouble())), nm, "Namiki_" + t + "_" + s);
                SeatBottom(go, y - 0.05f);
            }
        }
        // 門前町: 辻の北西の小さなL字(参道北縁の南向き4戸+小路東縁の西向き3戸)
        var mS1 = MonzenMat("M_Shop01", EdoAssets.Eg.TexShop01);
        var mS2 = MonzenMat("M_Shop02", EdoAssets.Eg.TexShop02);
        int n = 0;
        for (int i = 0; i < 4; i++)
        {
            float x = -366f + i * 7.7f;
            float y = Ground(x, 916.5f);
            bool big = (n % 3 == 1);
            var go = Place(big ? PShop02 : PShop01, new Vector3(x, y, 916.5f), 180f, Vector3.one * ES, root, "Monzen_" + n);
            SeatBottom(go, y - 0.10f);
            foreach (var r in go.GetComponentsInChildren<Renderer>()) r.sharedMaterial = big ? mS2 : mS1;
            n++;
        }
        for (int i = 0; i < 3; i++)
        {
            float z = 921f + i * 7.7f;
            float y = Ground(-368.5f, z);
            bool big = (n % 3 == 1);
            var go = Place(big ? PShop02 : PShop01, new Vector3(-368.5f, y, z), -90f, Vector3.one * ES, root, "Monzen_" + n);
            SeatBottom(go, y - 0.10f);
            foreach (var r in go.GetComponentsInChildren<Renderer>()) r.sharedMaterial = big ? mS2 : mS1;
            n++;
        }
        // 木戸: 参道の門前町東端と、一の鳥居先
        foreach (var kd in new float[][] { new float[] { -334f, 896.2f }, new float[] { -152f, 898.6f } })
        {
            float yaw = Mathf.Atan2(axis.x, axis.y) * Mathf.Rad2Deg;
            var kido = Place(PKido, Vector3.zero, yaw, Vector3.one * ES, root, "Kido_" + kd[0]);
            CenterSeat(kido, kd[0], kd[1], 0.05f);
        }
        sb.AppendLine("monzen houses=" + n);
        return sb.ToString();
    }
    static Material MonzenMat(string name, string texPath)
    {
        string matPath = EdoAssets.Own.Mat(name);
        var m = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (m != null) return m;
        m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
        if (tex != null) m.mainTexture = tex;
        System.IO.Directory.CreateDirectory("Assets/Edo/Materials");
        AssetDatabase.CreateAsset(m, matPath);
        return m;
    }

    // ---------- Stage 4: 丹羽左京大夫上屋敷 ----------
    public static string Stage4_Niwa()
    {
        const string G = "Edo_Yashiki_NiwaSakyo";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Niwa";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        // 表門=東辺 z≈839, 東向き(門印=三角形)。独立門+両番所(10万石外様大広間)
        Vector2 nA = NIWA[7], nB = NIWA[0];   // 辺7(E): (-131.1,883.5)→(-129.2,802.3)
        Vector2 nDir = (nB - nA).normalized;
        Vector2 gate = nA + nDir * ((839f - nA.y) / nDir.y);
        Vector2 fout = -EdoGeom.InwardNormal(NIWA, 7);
        float gateHalf = PlaceGate(PKmon, monGrp, gate, fout, 2, "Kmon", sb);
        int N = NIWA.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = NIWA[i], b = NIWA[(i + 1) % N];
            Vector2 outw = -EdoGeom.InwardNormal(NIWA, i);
            if (i == 7)
                FrontWall(kak, a, b, outw, gate, gateHalf + 0.5f, "Hei_F");
            else if (i == 2) continue;   // 内藤北塀が受け持つ(背中合わせ)
            else if (i == 5)
                EdoNishiTameikeBuilder.NagayaRun(kak, a, b, outw, 0, Vector2.zero, -1, "NG_W");  // 谷側の通り沿い=盲長屋
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        // 御殿群(台地 h27-28): 表御殿は東の表門に正対、蔵・台所は奥(西)
        var bg = Group(G, "Buildings");
        var og = Place(PBigHouse, Vector3.zero, 90f, Vector3.one, bg, "OmoteGoten");
        CenterSeat(og, -168f, 839f);
        var ok = Place(PHouse, Vector3.zero, 90f, Vector3.one, bg, "OkuGoten");
        CenterSeat(ok, -205f, 855f);
        var yk = Place(PHouseB, Vector3.zero, 0f, Vector3.one, bg, "Yakusho");
        CenterSeat(yk, -160f, 866f);
        var dd = Place(PSmallHouse, Vector3.zero, 90f, Vector3.one, bg, "Daidokoro");
        CenterSeat(dd, -205f, 822f);
        for (int i = 0; i < 3; i++)
        {
            var kr = Place(PKura, Vector3.zero, 0f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, -240f - i * 8f, 845f - i * 6f);
        }
        // 家臣長屋(発掘の長屋地区に対応): 表門の南、東縁内側に2棟
        var n1 = Place(EdoAssets.Eg.KnagayaL, Vector3.zero, 0f, Vector3.one * ES, bg, "KashinNagaya_L");
        CenterSeat(n1, -148f, 812f);
        var n2 = Place(EdoAssets.Eg.KnagayaR, Vector3.zero, 0f, Vector3.one * ES, bg, "KashinNagaya_R");
        CenterSeat(n2, -140.2f, 812f);
        Well(bg, -190f, 828f);
        // 庭(池は発掘で存在確認されるが位置不明=未再現)
        var gg = Group(G, "Garden");
        var rnd = new System.Random(107);
        for (int i = 0, gd = 0; i < 22 && gd < 900; gd++)
        {
            float px = Mathf.Lerp(-370f, -134f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(680f, 880f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!EdoGeom.PIP(NIWA, p2) || EdoGeom.DistToPolyEdge(NIWA, p2) < 4f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float y = Ground(px, pz);
            if (rnd.NextDouble() < 0.72)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.65f * (0.9f + 0.5f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.7f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        return sb.ToString() + "niwa done";
    }

    // ---------- Stage 5: 京極備中守上屋敷 ----------
    public static string Stage5_Kyogoku()
    {
        const string G = "Edo_Yashiki_KyogokuBitchu";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Kyogoku";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        // 表門=東辺 z≈747, 東向き(門印=三角形)。長屋門+格子出番所1(1.1万石)
        Vector2 sA = KYOGOKU[2], sB = KYOGOKU[3];  // 辺2(E): (-129.2,802.3)→(-123.7,680.0)
        Vector2 sDir = (sB - sA).normalized;
        Vector2 gate = sA + sDir * ((747f - sA.y) / sDir.y);
        Vector2 fout = -EdoGeom.InwardNormal(KYOGOKU, 2);
        float gateHalf = PlaceGate(PNmon, monGrp, gate, fout, 1, "Nagayamon", sb);
        int N = KYOGOKU.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = KYOGOKU[i], b = KYOGOKU[(i + 1) % N];
            Vector2 outw = -EdoGeom.InwardNormal(KYOGOKU, i);
            if (i == 2)
                FrontWall(kak, a, b, outw, gate, gateHalf + 0.5f, "Hei_F");
            else continue;    // W/N=丹羽、S=内藤の塀が受け持つ(背中合わせ)
        }
        var bg = Group(G, "Buildings");
        var shu = Place(PHouse, Vector3.zero, 90f, Vector3.one, bg, "Goten");
        CenterSeat(shu, -158f, 747f);
        var dd = Place(PSmallHouse, Vector3.zero, 0f, Vector3.one * 0.85f, bg, "Daidokoro");
        CenterSeat(dd, -175f, 768f);
        var kr = Place(PKura, Vector3.zero, 0f, Vector3.one * ES, bg, "Kura_1");
        CenterSeat(kr, -182f, 728f);
        Well(bg, -172f, 752f);
        var gg = Group(G, "Garden");
        var rnd = new System.Random(11144);
        for (int i = 0, gd = 0; i < 10 && gd < 500; gd++)
        {
            float px = Mathf.Lerp(-292f, -126f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(686f, 796f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!EdoGeom.PIP(KYOGOKU, p2) || EdoGeom.DistToPolyEdge(KYOGOKU, p2) < 3.5f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float y = Ground(px, pz);
            if (rnd.NextDouble() < 0.7)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.6f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.6f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        return sb.ToString() + "kyogoku done";
    }

    // ---------- Stage 6: 内藤紀伊守上屋敷 ----------
    public static string Stage6_Naito()
    {
        const string G = "Edo_Yashiki_NaitoKii";
        var exist = GameObject.Find(G);
        if (exist != null && exist.transform.childCount > 0) return "SKIP Naito";
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = true;
        var kak = Group(G, "Kakoi");
        var monGrp = Group(G, "Omotemon");
        // 表門=北辺東寄り x≈-106, 北向き(門印=三角形)。独立門+両番所(譜代5万石・老中)
        Vector2 a9 = NAITO[9], a10 = NAITO[10];   // 辺9(N): (-88.9,677.7)→(-126.79,677.7)。表門 x≈-106 はこの辺上(2026-08-26 json採用で北辺が辺9+10に割れた)
        Vector2 nDir = (a10 - a9).normalized;
        Vector2 gate = a9 + nDir * Mathf.Abs((-106f - a9.x) / Mathf.Abs(nDir.x));
        Vector2 fout = -EdoGeom.InwardNormal(NAITO, 9);
        float gateHalf = PlaceGate(PKmon, monGrp, gate, fout, 2, "Kmon", sb);
        int N = NAITO.Length;
        for (int i = 0; i < N; i++)
        {
            Vector2 a = NAITO[i], b = NAITO[(i + 1) % N];
            Vector2 outw = -EdoGeom.InwardNormal(NAITO, i);
            if (i == 9)
                FrontWall(kak, a, b, outw, gate, gateHalf + 0.5f, "Hei_F");
            else
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }
        var bg = Group(G, "Buildings");
        // 表御殿=Manor。facadeを北の表門に正対(facade+35.2偏心→OBB中心=facadeの31.2m奥)
        var manor = Place(PManor, Vector3.zero, 0f, Vector3.one, bg, "OmoteGoten");
        CenterSeat(manor, -110f, 628f);
        var okg = Place(PHouse, Vector3.zero, 0f, Vector3.one, bg, "OkuGoten");
        CenterSeat(okg, -160f, 612f);
        var yks = Place(PHouseB, Vector3.zero, 90f, Vector3.one, bg, "Yakusho");
        CenterSeat(yks, -140f, 660f);
        var dd = Place(PSmallHouse, Vector3.zero, 90f, Vector3.one, bg, "Daidokoro");
        CenterSeat(dd, -185f, 640f);
        for (int i = 0; i < 3; i++)
        {
            var kr = Place(PKura, Vector3.zero, 90f, Vector3.one * ES, bg, "Kura_" + (i + 1));
            CenterSeat(kr, -235f - i * 8f, 640f - i * 4f);
        }
        // 中間長屋(knagaya l+r)
        var m1 = Place(EdoAssets.Eg.KnagayaL, Vector3.zero, 0f, Vector3.one * ES, bg, "ChugenNagaya_L");
        CenterSeat(m1, -290f, 655f);
        var m2 = Place(EdoAssets.Eg.KnagayaR, Vector3.zero, 0f, Vector3.one * ES, bg, "ChugenNagaya_R");
        CenterSeat(m2, -282.2f, 655f);
        Well(bg, -170f, 630f);
        // 庭: 台地東の高台=奥庭、南の水際=溜池を望む景(池は作らない)
        var gg = Group(G, "Garden");
        var rnd = new System.Random(5090);
        for (int i = 0, gd = 0; i < 30 && gd < 1200; gd++)
        {
            float px = Mathf.Lerp(-368f, -60f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(520f, 670f, (float)rnd.NextDouble());
            var p2 = new Vector2(px, pz);
            if (!EdoGeom.PIP(NAITO, p2) || EdoGeom.DistToPolyEdge(NAITO, p2) < 4f) continue;
            bool nearB = false;
            foreach (Transform c in bg) { var rb2 = RB(c.gameObject); if (px > rb2.min.x - 2.5f && px < rb2.max.x + 2.5f && pz > rb2.min.z - 2.5f && pz < rb2.max.z + 2.5f) { nearB = true; break; } }
            if (nearB) continue;
            float y = Ground(px, pz);
            if (rnd.NextDouble() < 0.7)
            {
                var go = Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.65f * (0.9f + 0.5f * (float)rnd.NextDouble())), gg, "Pine_" + i);
                SeatBottom(go, y - 0.05f);
            }
            else
            {
                var go = Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.7f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
                SeatBottom(go, y - 0.04f);
            }
            i++;
        }
        return sb.ToString() + "naito done";
    }

    // ---------- Stage 7: スプラット ----------
    public static string Stage7_Splat()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -520, x1 = -50, z0 = 505, z1 = 955;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        // 道: 東の南北通り(丹羽・京極の表門前→内藤北東縁に沿って虎ノ門方面へ)・堀端通り
        Vector2[] midRoad = { new Vector2(-128.5f, 890f), new Vector2(-126f, 803f), new Vector2(-121.5f, 747f),
            new Vector2(-118.5f, 683f), new Vector2(-98f, 679.5f), new Vector2(-82f, 663f), new Vector2(-62f, 600f), new Vector2(-48f, 558f) };
        Vector2[] shoreRoad = { new Vector2(-374f, 653f), new Vector2(-358.5f, 598f), new Vector2(-332f, 571f), new Vector2(-288f, 540f),
            new Vector2(-221f, 517f), new Vector2(-157.5f, 510.8f), new Vector2(-92f, 520.3f), new Vector2(-50f, 534.9f) };
        Func<Vector2, Vector2[], float> dPoly = (p, pts) =>
        {
            float m = float.MaxValue;
            for (int i = 0; i < pts.Length - 1; i++) m = Mathf.Min(m, EdoGeom.DistToEdge(p, pts[i], pts[i + 1]));
            return m;
        };
        Vector2[][] parcels = { JUGE, SHANIN, NIWA, KYOGOKU, NAITO };
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                float bare = -1, grass = 0, dirt = 0;
                bool skip = false;
                foreach (var jb in EdoSannoJuboBuilder.Parcels) if (EdoGeom.PIP(jb.poly, p)) { skip = true; break; }
                if (!skip)
                {
                    // 観理院・境内は既存のまま
                    var KAN = new Vector2[] { new Vector2(-389.4f, 735.3f), new Vector2(-421.6f, 732.5f), new Vector2(-426.2f, 851.4f), new Vector2(-409.7f, 888.1f), new Vector2(-390.2f, 888.3f) };
                    if (EdoGeom.PIP(KAN, p)) skip = true;
                    if (wx < -426f && wz < 908f) skip = true;   // 山王山・境内側は触らない
                }
                if (skip) continue;
                bool inSando = (wz > 884f && wz < 909f && wx > -372f && wx < -128f);
                float dm = dPoly(p, midRoad), ds = dPoly(p, shoreRoad);
                Vector2[] inP = null;
                foreach (var pp in parcels) if (EdoGeom.PIP(pp, p)) { inP = pp; break; }
                if (inSando)
                {
                    float dAxis = dPoly(p, SANDO_AXIS);
                    if (dAxis < 4.5f) { bare = 0.66f; grass = 0.06f; dirt = 0.28f; }
                    else { bare = 0.34f; grass = 0.24f; dirt = 0.42f; }
                }
                else if (inP != null)
                {
                    if (inP == SHANIN)
                    { bare = 0.30f; grass = 0.25f; dirt = 0.45f; }        // 社家の庭・畑
                    else
                    {
                        float noise = Mathf.PerlinNoise(wx * 0.11f, wz * 0.11f);
                        grass = Mathf.Lerp(0.38f, 0.65f, noise); bare = 0.14f; dirt = 1f - grass - bare;
                    }
                }
                else if (dm < 3.2f || ds < 3.2f) { bare = 0.55f; grass = 0.05f; dirt = 0.40f; }
                else if (dm < 4.8f || ds < 4.8f) { bare = 0.30f; grass = 0.25f; dirt = 0.45f; }
                else if (wz > 909f && wz < 950f && wx > -374f && wx < -300f)
                { bare = 0.45f; grass = 0.18f; dirt = 0.37f; }            // 門前町の地面
                else if (wz > 666f && wz < 694f && wx > -348f && wx < -95f)
                {   // 旧・内藤/京極間の道の塗り戻し(現区割りでは背中合わせ)
                    float noise = Mathf.PerlinNoise(wx * 0.09f, wz * 0.09f);
                    grass = Mathf.Lerp(0.32f, 0.58f, noise); bare = 0.12f; dirt = 1f - grass - bare;
                }
                if (bare < 0) continue;
                float sum = bare + grass + dirt;
                for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
                A[zz, xx, 0] = dirt / sum; A[zz, xx, 1] = grass / sum; A[zz, xx, 2] = bare / sum;
                changed++;
            }
        td.SetAlphamaps(ix0, iz0, A);
        return "splat cells=" + changed;
    }

    // ---------- 一括 ----------
    public static string BuildAll()
    {
        EdoNishiTameikeBuilder.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage0_Demolish());
        sb.AppendLine(Stage1_Juge());
        sb.AppendLine(Stage2_Shanin());
        sb.AppendLine(Stage3_Sando());
        sb.AppendLine(Stage4_Niwa());
        sb.AppendLine(Stage5_Kyogoku());
        sb.AppendLine(Stage6_Naito());
        sb.AppendLine(Stage7_Splat());
        return sb.ToString();
    }
}
