// 岡部筑前守(和泉岸和田藩5万3千石・譜代雁間)上屋敷 — 全面再構成 v3 (2026-08-14)
//
// 【v3 でやり直した理由】ユーザー差し戻し。v2 は
//   (1) 建屋を「台地の平場に載る分」だけ置いて敷地の大半を空地にした
//   (2) 御殿複合を表門の45°軸に合わせたため敷地形・外周長屋と向きが揃わなかった
//   越前福井藩上屋敷の再現3D(ユーザー提示)では敷地ほぼ全体に建屋が載り、外周塀と建物の向きが揃う。
//   v1/v2 の成果は削除せず SetActive(false) で保存する(§A-1)。
//
// 【区割りの典拠 = ユーザー下書き(2026-08-14, EdoSketch)】確度U。色は EdoSketch.Palette:
//   赤(0)=長屋  黄(1)=屋敷エリア(連続御殿複合)  桃(4)=庭園  緑(3)=塀  白(5)=表門前スペース
//   ・表門 = 東辺(三べ坂沿い) z≒1001。下書きの三角マークが表門の位置指定。
//     ⚠ 2026-08-12 の考証では「表門=北東辺(切絵図の文字の頭)」としていたが、
//        ユーザーの区割り指定を優先する。北東の隅切り辺は長屋になる。
//   ・長屋 = 南辺全部 + 東辺全部(表門の開口を除く) + 北東の隅切り辺 + 内部の南北二列(x=-558/-572)
//   ・塀   = 西辺・北辺(溜池の汀と土井/松平との隣地境)
//   ・屋敷エリアは台地と東西の低地にまたがる。ユーザー指示:
//     「高地と低地でつながっていますが、この部分は廊下と階段とかで繋げてください」
//     → 段の間は渡り廊下(Roka)と石段(Kaidan)で一続きにする。
//   ・「連続御殿複合の屋敷内にも廊下を設置して建物内を移動できるように」(2026-08-14 追加指示)
//     → 棟と棟の間にも渡り廊下を通す。
//
// 【格式の判断】御成門・能舞台・御成風呂は作らない。御成対応は原則として家門・大藩の装置で、
//   [福井図]で御成門を持つ越前松平は家門。譜代雁間5.3万石の当家に御成セットの典拠はない。
//   【典拠: estate-types.md 上屋敷の項/当屋敷の一次史料は未確認】
//
// 【地形】§B-1。段は「建物が載る大きな平場」で、雛壇リボンではない。
//   主郭25.5 / 東三段22.0・18.0・14.5 / 表門前13.5 / 西低地9.5。
//   西斜面(x -602..-576)は勾配41〜65%で平場にできない → 階段廊下と法面・庭のみ。
//   切盛 clamp = 切4.0 / 盛5.0(菊地2003「1〜4mが多い」/紀伊家紀尾井町の盛土5.0mが上限実例)。
//   backup = scratchpad/okabe_v3_backup.bin
//
// ⚠ MCP タイムアウト後の再送で多重実行が起きる。地形ステージはマーカーで、
//   構造ステージは「作る前に消す」で冪等にしてある。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using B = EdoSanbezakaBuilder;
using NT = EdoNishiTameikeBuilder;
using SK = EdoSannoKitaBuilder;

public static class EdoOkabeYashikiBuilder
{
    public const string GN = "Edo_Yashiki_OkabeChikuzen";
    const float ES = 1.818f;
    const float CUT_MAX = 5.5f, FILL_MAX = 5.0f;
    // 表門 = **長屋門**(指図 其八)。大名屋敷の表門は石高と家格で形式が決まり、
    // 5万石以上は長屋門[表門格式表]。冠木門は焼失後の再建など簡素な場合の形式で、
    // 大名の上屋敷の表門にはならない。番所は長屋門の躯体に組み込まれているので別に建てない。
    // 【典拠: 格式表(二次) / 当屋敷の一次史料は未確認】
    const string PKmon = EdoAssets.Eg.Nagayamon;
    // 門は 1.08 倍に起こす(指図 其八ノ二 ③)。素の全高 5.10 は東辺の長屋(5.51)より低く、
    // 表門の棟が長屋の棟に負けていた(18.60 < 18.91)。1.08 倍で棟 19.01 となり門が勝つ。
    const float MON_SCALE = 1.08f;
    const float MON_HALF = 12.14f;      // 長屋門の半幅(22.48 × 1.08 ÷ 2)。塀の切り位置はここから出す

    // ---------- 段(平場)の定義: x範囲 / z範囲 / 高さ ----------
    public struct Terr { public float x0, x1, z0, z1, y; public string name; }
    public static Terr[] Terraces()
    {
        return new[] {
            new Terr{ name="Shukaku", x0=-566f, x1=-455f, z0=946f, z1=1058f, y=25.5f },
            new Terr{ name="TE",      x0=-455f, x1=-425f, z0=946f, z1=1058f, y=19.5f },
            new Terr{ name="Monzen",  x0=-425f, x1=-374f, z0=946f, z1=1058f, y=13.5f },
            new Terr{ name="Chudan",  x0=-592f, x1=-566f, z0=950f, z1=1052f, y=19.5f },
            new Terr{ name="TW1",     x0=-647f, x1=-592f, z0=950f, z1=1052f, y=11.5f },
        };
    }
    // 石垣(土留め)の芯線 = 外面。天端は上段のレベル、scale.y は 4.0m/1.0 の丸数字。
    // 走り方向の左(local -X)に躯体2.4mが出るので、高い側が左になるよう a→b を取る。
    /// <summary>na/nb は天端に載せる家臣長屋の範囲。石垣は境界まで延ばすが、長屋は
    /// 其六 で決めた長さのまま据える(石垣を延ばした分だけ長屋が伸びると別物になる)。</summary>
    public struct Wall { public Vector2 a, b, na, nb; public float coping, sy; public string name;
        /// <summary>石段の開口の芯 z ＝ 法面の芯(Kai.NoriZ)。</summary>
        public float gapZ;
        /// <summary>開口の半幅 ＝ 芯 → 坂の土留めの**外面**(Kai.GapHalf)。
        /// 主石垣の端面がここにぴったり突き付く(指図 其十 ②)。</summary>
        public float gapHalf; }
    public static Wall[] Walls()
    {
        return new[] {
            // ⚠ 2026-08-16、**4本とも走りを反転した**(指図 其九「勾配は外向き」)。
            //   駒のローカル箱は X[-2.40,0]・勾配は X=-2.40(底)→ -1.40(天端) の面に付く。
            //   つまり**傾いた法は躯体の側**にあり、芯線(X=0)の面は鉛直。
            //   旧向きは躯体を高い側の盛土に埋めていたので、露出していたのは鉛直面だけで、
            //   石垣が「板」に見えていた。躯体が低い側=進行方向の左に来るよう反転する。
            //   反転後: 芯線が高い側の縁、法肩 = 芯線 + 1.4×s(低い側へ)、法尻 = 芯線 + 2.4×s。
            // 東: 主郭25.5 → 東中段19.5 → 表門前13.5。北→南へ走る(左=東=低い側)。開口は参道 z=1001
            // ⚠ 走りは**敷地の境界まで**伸ばす(指図 其九)。旧値 z 947〜1056 は北で 30〜40m 足りず、
            //   段の縁が北縁で土のまま露出していた。境界の z は多角形と x=const の交点から取る。
            new Wall{ name="IG_E1", a=new Vector2(-455f, 1087.9f), b=new Vector2(-455f, 947f), coping=25.5f, sy=1.5f, gapZ=1001f, gapHalf=3.30f,
                      na=new Vector2(-455f, 1056f), nb=new Vector2(-455f, 947f) },
            new Wall{ name="IG_E2", a=new Vector2(-425f, 1095.9f), b=new Vector2(-425f, 947f), coping=19.5f, sy=1.5f, gapZ=1001f, gapHalf=3.30f,
                      na=new Vector2(-425f, 1056f), nb=new Vector2(-425f, 947f) },
            // 西: 主郭25.5 → 中段19.5 → 西低地11.5。南→北へ走る(左=西=低い側)。開口は北縁 z=1043
            // ⚠ 開口は v5 で 1036 → 1043 へ北へ寄せた。直階段(9〜12m)が長局棟・御用部屋棟に
            //   ぶつからないよう、石段を棟の北面(z=1037.08)より北へ移したため
            new Wall{ name="IG_W1", a=new Vector2(-566f, 944.3f), b=new Vector2(-566f, 1069.8f), coping=25.5f, sy=1.5f, gapZ=1045.8f, gapHalf=2.32f,
                      na=new Vector2(-566f, 949f), nb=new Vector2(-566f, 1052f) },
            new Wall{ name="IG_W2", a=new Vector2(-592f, 942.6f), b=new Vector2(-592f, 1065.7f), coping=19.5f, sy=2.0f, gapZ=1045.8f, gapHalf=2.32f,
                      na=new Vector2(-592f, 949f), nb=new Vector2(-592f, 1052f) },
        };
    }

    // =========================================================================
    // 外周の土留め石垣(指図 其九 ①)
    //
    // 【相似スケール】localScale は **(s, s, s)**。(1, sy, 1) は石のテクスチャを縦に伸ばし、
    //   勾配角を高さごとに変えてしまう(実測 7.1°〜26.6°)。相似なら勾配は一定 **14.04°**。
    //     壁高 = 4.0×s ／ 底の厚み = 2.4×s ／ 天端の幅 = 1.4×s ／ coping = position.y + 4.0×s
    //     ピッチ = 1.800×s(継ぎ目ごとに 0.20×s 重なる)
    //
    // 【据えは法肩から逆算する】其六 で確定した外周線(長屋の外壁面・土塀の面)は動かせない。
    //     法肩 = 外周線 → 芯線 = 法肩 − 1.4×s(author する多角形) → 法尻 = 法肩 + 1.0×s
    //   石垣の裾は外周線より 1.0×s だけ外へ出る。実際の縄張りも境界杭は法尻で取る。
    //
    // 【勾配は外向き】芯線側の面は鉛直で、勾配は躯体側=進行方向の左に付く。
    //   よって **outw が走りの左に来るよう a→b の向きを決める**(必要なら run を反転)。
    // =========================================================================
    /// <summary>run のピボット線 → 外周線(法肩) の符号付きオフセット(外向きが ＋)。
    /// **実測値**(2026-08-16、部材の頂点を run 線へ射影して測った):
    ///   長屋   外面 −1.044 ／ 内面 −5.396（躯体は run 線の内側に丸ごと収まる）
    ///   築地塀 外面 +0.575 ／ 内面 −0.775（在庫の2枚重ね。幅 1.35）
    ///   竹垣   ±0.026
    /// ⚠ 以前 1.632 を「run 線から外周線まで」と書いていたが、あれは**長屋の面と塀の面の差**
    ///   (1.044 + 0.575 = 1.619)で、run 線からの距離ではなかった。
    /// 長屋は外壁面を法肩と面一に、塀は外面を法肩から 0.30(犬走り)控える。</summary>
    public static float FaceOff(Kakoi k)
    {
        if (k == Kakoi.Nagaya) return -1.044f;          // 面一
        if (k == Kakoi.Tsuiji) return 0.575f + 0.30f;   // 外面 + 犬走り
        if (k == Kakoi.None) return 0f;                 // 囲い無し。外周線 = 敷地境そのもの
        return 0.30f;                                   // 竹垣
    }
    public struct PWall { public string run, name; public float s; }
    public static PWall[] PerimeterWalls()
    {
        // s は「天端 − 外6m の自然地盤」を 0.25 刻みで切り上げたもの(指図 其九 表①)
        return new[] {
            new PWall{ run="Hei_S_Cd", name="IG_S_Cd", s=0.75f },   // 必要 2.25 → 壁高 3.0
            new PWall{ run="Hei_S_Sk", name="IG_S_Sk", s=1.50f },   //      5.57 →      6.0
            new PWall{ run="Hei_S_Te", name="IG_S_Te", s=0.50f },   //      1.81 →      2.0
            new PWall{ run="Hei_S_Mz", name="IG_S_Mz", s=0.50f },   //      1.42 →      2.0
            new PWall{ run="NG_E_S",   name="IG_E_S",  s=0.50f },   //      1.54 →      2.0
            new PWall{ run="Take_W3",  name="IG_W3",   s=0.75f },   //      2.42 →      3.0
            // 北辺(指図 其十一) — 段に造成したぶんを土留めする。s は「天端 − 外6m の土井側の地盤」
            new PWall{ run="Hei_N1",   name="IG_N1",   s=0.75f },   //      2.18 →      3.0
            new PWall{ run="Hei_N2",   name="IG_N2",   s=1.75f },   //      6.22 →      7.0
            new PWall{ run="Hei_N3",   name="IG_N3",   s=1.75f },   //      6.85 →      7.0
            new PWall{ run="Hei_N4",   name="IG_N4",   s=1.00f },   //      3.87 →      4.0
        };
    }

    /// <summary>北辺の段の**継ぎ目を受ける返しの石垣**(指図 其十一)。
    ///
    /// 段の天端が run の継ぎ目で 6m 落ちるので、そこに境界と直交する土留めが要る。
    /// 南辺では郭の石垣(IG_W2 など)が境界まで伸びていて自然に返しを兼ねていたが、
    /// 北辺には郭の石垣が来ていないので、専用に立てる。
    /// 継ぎ目から**内へ 15m**、天端は高い側の run に合わせる。</summary>
    public struct NRet { public string name; public int joint; public float coping, s; }
    public static NRet[] NorthReturns()
    {
        return new[] {
            new NRet{ name="IG_NR1", joint=0, coping=27.0f, s=1.50f },  // R1(21.0)|R2(27.0) 段差 6.0
            new NRet{ name="IG_NR2", joint=1, coping=27.0f, s=1.50f },  // R2(27.0)|R3(21.0) 段差 6.0
            new NRet{ name="IG_NR3", joint=2, coping=21.0f, s=1.75f },  // R3(21.0)|R4(14.5) 段差 6.5(P[7] の折れ)
        };
    }
    /// <summary>返しの石垣の据え位置 — 継ぎ目の点から、両 run の外向きの**二等分線の逆**(＝内向き)へ。</summary>
    public static void NorthReturnLine(int joint, out Vector2 a, out Vector2 b)
    {
        var rs = new List<Run>();
        foreach (var r in Runs()) if (r.name.StartsWith("Hei_N")) rs.Add(r);
        var lo = rs[joint]; var hi = rs[joint + 1];
        a = lo.b;                                   // 継ぎ目の点
        var inw = -(lo.outw + hi.outw).normalized;  // 内向き
        b = a + inw * 15f;
    }
    /// <summary>その run に付く外周石垣の s。付かない run は 0(芯線 = 外周線)。</summary>
    public static float WallScaleFor(string runName)
    {
        foreach (var q in PerimeterWalls()) if (q.run == runName) return q.s;
        return 0f;
    }

    // =========================================================================
    // 指図(Docs/Sashizu/okabe_sashizu.html)を**江戸間の柱割り**に載せて持つ。図面と実装をズラさない。
    //
    // 【ユーザー裁定 2026-08-14】指図のメートル値でなく**間割りを正**とし、指図の方を書き換える。
    //   ・指図の畳数は寸法の従属変数だった。面積÷1.65256(江戸間の畳1枚)で13棟中12棟が
    //     記載畳数と±1畳以内に一致する ⇒ 畳数からは独立した拘束が出ない
    //     (唯一の例外 NagatsuboneW の464畳は幅12m時代の残り。ブックマーク1で10mへ狭めた分が
    //      指図に反映されていなかった)
    //   ・指図自身が主郭を「約59間×56間」と書いており、丸めの方向と一致する
    //   ・Mune()/Roka() は整数間しか受けない。端数を残すと柱・障子・畳・屋根のモジュールが端で崩れる
    //   丸めで動く量は最大 ±0.91m(NagatsuboneW の幅・Shoin の奥行)。
    //
    //   主郭グリッド: x = -457 - U*KEN / z = 955 + V*KEN  (U は西へ・V は北へ増える) 59×56間
    //   西の下郭     : x = -648 + U*KEN / z = 948 + V*KEN  (U は東へ・V は北へ増える)
    //   ⚠ 二つのフレームは 191m 離れており 105.06間 と整数にならない。段が石垣で切れていて
    //     北縁の外廊下でしか繋がらないので、グリッドは郭ごとに別に張る。
    //
    // 【Blk の矩形 = 入側を含む棟の外形】指図の身舎に一間の入側を**四方へ**回したもの
    //   (ユーザー裁定: 指図が「入側が各棟の外周を巡り、隣の棟の入側と辺を共有して直に繋がる」
    //    と書いているため。前後だけにすると妻側の白壁が廊下に面する)。
    //   kw/kd = 外形の間数(U方向 = 世界X / V方向 = 世界Z)。身舎はそれぞれ -2 間。
    // =========================================================================
    public const float KEN = 1.818f;                    // 江戸間 1間 = 6尺
    public struct Blk
    {
        public float x0, z0, x1, z1, y; public string name;
        public int kw, kd;          // 間数(0 なら間割りに乗らない矩形 = 参道など)
        /// <summary>落とす高欄。0=両側とも立てる / 1=東(南北の廊下では x1 側) / 2=西(x0 側)。
        /// 階段廊下の端へ正面から継ぐ廊下は、継ぐ面の高欄を落とさないと通れない</summary>
        public int koranOff;
        public int MoyaW { get { return kw - 2; } }
        public int MoyaD { get { return kd - 2; } }
    }
    static Blk SG(int U0, int V0, int U1, int V1, float y, string n)   // 主郭
    {
        return new Blk { x0 = -457f - U1 * KEN, x1 = -457f - U0 * KEN,
                         z0 = 955f + V0 * KEN,  z1 = 955f + V1 * KEN,
                         y = y, name = n, kw = U1 - U0, kd = V1 - V0 };
    }
    static Blk WG(int U0, int V0, int U1, int V1, float y, string n)   // 西の下郭
    {
        return new Blk { x0 = -648f + U0 * KEN, x1 = -648f + U1 * KEN,
                         z0 = 948f + V0 * KEN,  z1 = 948f + V1 * KEN,
                         y = y, name = n, kw = U1 - U0, kd = V1 - V0 };
    }
    static Blk KO(Blk b, int off) { b.koranOff = off; return b; }
    /// <summary>x だけマス目から外す下郭の廊下。**階段廊下の端は石垣の面(メートル)で決まる**ので、
    /// 取り付きの x をマス目に取ると 0.2〜0.4m の隙間が床に残る。z はマス目のまま。</summary>
    static Blk WGz(float x0, float x1, int V0, int V1, float y, string n)
    {
        return new Blk { x0 = x0, x1 = x1,
                         z0 = 948f + V0 * KEN, z1 = 948f + V1 * KEN,
                         y = y, name = n,
                         kw = Mathf.RoundToInt((x1 - x0) / KEN), kd = V1 - V0 };
    }

    // 棟の外形(身舎 + 四方の入側)。指図の身舎寸法との差は okabe_sashizu.html 其二の表に載せた
    public static Blk[] Muneya()
    {
        return new[] {
            //     U0 V0  U1 V1            身舎(間)   指図(m)      差(m)
            SG( 1,20, 11,35, 25.5f, "Genkan"),      //  8x13  14x24  +0.54/-0.37
            SG(13, 7, 27,29, 25.5f, "Ohiroma"),     // 12x20  22x36  -0.18/+0.36
            SG(13,36, 27,54, 25.5f, "Shoin"),       // 12x16  22x30  -0.18/-0.91
            SG(30, 7, 44,29, 25.5f, "Nakaoku"),     // 12x20  22x36  -0.18/+0.36
            SG(30,36, 44,54, 25.5f, "Daidokoro"),   // 12x16  22x30  -0.18/-0.91
            SG(47,22, 58,38, 25.5f, "Okumuki"),     //  9x14  16x26  +0.36/-0.55
            SG(47, 3, 58,16, 25.5f, "Nagatsubone"), //  9x11  16x20  +0.36/ 0
            WG( 4, 3, 15,13, 11.5f, "Katte"),       //  9x8   16x14  +0.36/+0.54
            WG( 4,15, 15,41, 11.5f, "ShimoGoten"),  //  9x24  16x44  +0.36/-0.37
            WG( 4,43, 13,49, 11.5f, "Yudono"),      //  7x4   12x8   +0.73/-0.73
            WG(18,15, 29,32, 11.5f, "Jochu"),       //  9x15  16x28  +0.36/-0.73
            WG(18,35, 26,49, 11.5f, "Goyobeya"),    //  6x12  11x22  -0.09/-0.18
            WG(34,12, 42,49, 19.5f, "NagatsuboneW"),//  6x35  10x64  +0.91/-0.37  家臣長屋との隙間(bm1 23-24)
        };
    }

    // 渡廊下 — 幅1間・長さ n間。**両端は棟の壁面に突き付ける**(屋根が両端0.30長く、
    // 棟の軒0.90と1.20重なる。離すと取り合いに隙間が出る)。EdoGotenKit.Roka で建てる。
    //   ⚠ 1間(1.818m)のリンクは成立しない — 両端で1.20ずつ計2.40m重なり、廊下長を超える。
    //     指図の2m隙間は2間(3.64m)へ広げた(L_GenkanOhiroma / LW_KatteShimo / LW_ShimoYudono)。
    public static Blk[] GotenLinks()
    {
        return new[] {
            SG(11,25, 13,26, 25.5f, "L_GenkanOhiroma"),    // 2間
            SG(27,28, 30,29, 25.5f, "L_OhiromaNakaoku"),   // 3間
            SG(27,36, 30,37, 25.5f, "L_ShoinDaidokoro"),   // 3間
            SG(20,29, 21,36, 25.5f, "L_OhiromaShoin"),     // 7間 坪庭の西縁
            SG(37,29, 38,36, 25.5f, "L_NakaokuDaidokoro"), // 7間 坪庭の東縁
            SG(44,25, 47,26, 25.5f, "L_Jouguchi"),         // 3間 御錠口(奥向へ入る唯一の廊下)
            SG(52,16, 53,22, 25.5f, "L_OkuNagatsubone"),   // 6間
            SG(57,38, 58,48, 25.5f, "L_ShimoKuruwa"),      // 10間 西縁の外廊下 → 登廊W1へ
            WG( 4,13,  5,15, 11.5f, "LW_KatteShimo"),      // 2間
            WG( 4,41,  5,43, 11.5f, "LW_ShimoYudono"),     // 2間
            WG(15,23, 18,24, 11.5f, "LW_ShimoJochu"),      // 3間
            WG(23,32, 24,35, 11.5f, "LW_JochuGoyo"),       // 3間
            WG(13,48, 18,49, 11.5f, "LW_Kita1"),           // 5間 湯殿 → 御用部屋棟(西低地の北縁)
            // 登廊の取り付き(2026-08-15) — 登廊は石段の上に屋根を架けただけなので、
            // その**両端から棟・外廊下までの数m**は別に廊下を通さないと屋外が残る。
            // 段の芯(z=1043)へ向けて北へ振り、そこで東西の廊下に継ぐ。
            SG(58,47, 60,48, 25.5f, "LW_Kita6"),           // 2間 西縁の外廊下 → 登廊W1の上端(正面から)
            // 下端側は階段の**西の端**へ回り込ませる。階段の走りに掛けると側面に付き当たる
            KO(WGz(-576.818f, -575.0f, 49, 52, 19.5f, "LW_Kita7"), 1),   // 3間 長局棟 → 登廊W1の下端
            KO(WGz(-586.546f, -584.728f, 49, 52, 19.5f, "LW_Kita8"), 2), // 3間 長局棟の北西 → 北へ振る
            WGz(-592.0f, -586.546f, 51, 52, 19.5f, "LW_Kita9"),          // 3間 西へ → 登廊W2の上端
            KO(WGz(-605.818f, -604.0f, 49, 52, 11.5f, "LW_Kita10"), 1),  // 3間 御用部屋棟 → 登廊W2の下端
            // 方針B(指図 其十 ②) — 登廊に踊り場が付いて下端が西へ出たぶんを継ぐ。
            // 既存の LW_Kita7/10 は棟に取り付いているので動かさず、**東西の継ぎ足し**で延ばす。
            // 帯は登廊と同じ V51..52(= 階段廊下の一間)。長さは踊り場の間数と同じ。
            WGz(-580.454f, -575.0f, 51, 52, 19.5f, "LW_Kita7b"),         // 3間 登廊W1の下端 → LW_Kita7
            WGz(-609.454f, -604.0f, 51, 52, 11.5f, "LW_Kita10b"),        // 3間 登廊W2の下端 → LW_Kita10
            // ⚠ v5: 石段に取り付いていた LW_Kita2/3/6(と v4 の LW_Kita5)は全部廃した。
            //   **郭をまたぐ石段は廊下ではなく屋外の通路**へ改めたため(指図 v5)。
            //   直階段は法面ごと棟の北へ寄せてあり、旧リンクの位置は今は法面の中にある。
        };
    }

    // 表門 → 玄関の参道は**屋根を架けない**(v5)。
    // 【考証 2026-08-15】武家屋敷の表門〜玄関は砂利敷の前庭(白洲)で、屋根付きの廊下は架けない。
    //   ・門を入った正面が玄関式台 [鈴木1985 確度A / historical-layout.md]
    //   ・前庭は主に開けておく(白洲・馬場感)。門から御殿前まで15〜20m [gardens-ponds.md]
    //   ・屋根付きの通路で前庭を横切るのは寝殿造の中門廊や社寺の回廊の形式で、
    //     書院造の武家屋敷には無い。玄関側で屋根が架かるのは式台・車寄せまで。
    //   v4 で敷いた L_HigashiEn / L_Sando19 / L_Sando13 は典拠が無いので撤去した
    //   (ユーザー指摘 2026-08-15「表門から屋根付き廊下って江戸時代にあったのでしょうか」)。
    //   参道は Stage9 で白洲の中に踏み分け帯として塗るだけにする。

    // 庭(指図と同じ矩形)。白洲を塗るときにここは芝のまま残す
    public static Blk[] Gardens()
    {
        return new[] {
            SG( 0, 0, 11,20, 25.5f, "NiwaOmoteE"),  SG(11, 0, 44, 7, 25.5f, "NiwaOmoteS"),
            SG( 0,36, 11,56, 25.5f, "NiwaShoin"),   SG(21,29, 37,36, 25.5f, "Tsubo"),
            SG(47,38, 58,53, 25.5f, "NiwaOkuUchi"),
        };
    }
    // 石段 — **直階段**(v5)。折返しは廃した(ユーザー指示 2026-08-15)。
    //   ・折返しは下端が上端と同じ側へ戻るので「廊下がそのまま段になる」が成り立たない
    //   ・段の下に地面が無く**宙に浮いて**いた
    // v5 では下段の上に**盛土の法面**(Stage1 が造成)を作り、その上に段を据える。
    // 勾配は蹴上0.30 / 踏面0.45 = 1:1.5 で統一。走りは世界X、xTop が上端。
    // 幅4mに段板(1.98m)を2枚並べる。
    public const float KERI = 0.30f, FUMI = 0.45f;   // 蹴上 / 踏面
    // 法面は**両脇を石垣で留める**(v6)。段の芯から NORI_HALF までが平場、その外に石垣が立ち、
    // 石垣の背後だけ NORI_FEATHER で下段へ落とす。合わせて 2*(3.5+1.5)=10m ＝ 石垣の開口±5.0m。
    // ⚠ ハイトマップは約2m刻みなので、フェザーを 0 にしても地形は 2m かけて落ちる。
    //   石垣を平場の縁(段の芯±3.5m)へ置くのは、その甘い縁を隠して稜線を立てるため。
    // ⚠ NORI_HALF はグローバル定数をやめ **Kai.noriHalf** へ移した(指図 其十 ②)。
    //   其七 の 3.1 は「幅6.2mの法面に石階段と木階段を並べて入れる」という前提の値だったが、
    //   その前提自体がユーザー裁定で撤回された(法面は石階段だけのもの)。東 2.58 / 西 1.60。
    public const float SAKA_T = 0.72f;               // 坂の土留め部材の厚み(笠石を含む)
    public const float NORI_FEATHER = 1.5f;          // 土留めの内面から下段へ落とす幅
    // ⚠ 平場は土留めの**内面**(NORI_HALF)で止める。ハイトマップは約2m刻みで垂直な縁を
    //   作れないので、外面まで満たすと 2〜4m の土手が石垣の外へ回り込んで面を埋める
    //   (v7 で外面まで満たして実際にそうなった)。内面止めでも足元に土手の裾は残るが、
    //   石垣の大半は出る — これはハイトマップの分解能の限界で、部材側では直せない。
    // 坂の土留めは郭の石垣(躯体2.40m・天端1.40m)より薄く、天端は**斜めに一直線**で下がる。
    // Castle Wall の段々では実物の石段の袖にならないので専用の部材を起こした
    // (ユーザー指摘 2026-08-15。EdoAssets.Own.IshigakiSaka / build_ishigaki_saka.py)。
    // 部材の厚みは 0.72m(笠石を含む)。
    public struct Kai
    {
        public float xTop, xBot, z0, z1, yTop, yBot; public string name;
        /// <summary>法面の芯から**土留めの内面**まで(指図 其十 ②)。東西で値が違うのでグローバル定数をやめた。
        /// 石段の幅の半分 + 肩 0.60。東 = 1.98 + 0.60 = 2.58 / 西 = 0.99 + 0.60 = 1.59 → 1.60。</summary>
        public float noriHalf;
        /// <summary>登廊の踊り場の間数(方針B)。石垣の**法尻まで水平に渡ってから**降り始める。
        /// 床は坂上で天端 +0.62 しかないので、そのまま降りると天端より下へ潜って跨げない。</summary>
        public int odoriKen;
        /// <summary>登廊(屋根付きの階段廊下)にする段は、屋根FBXのタグを入れる。
        /// 表門からの参道(E1/E2)は**公的動線なので屋根を架けない** — 前庭は開けた白洲。
        /// 屋根を架けるのは郭と郭を結ぶ内部動線(W1/W2)だけ。</summary>
        public string noboriro;
        public float Run { get { return Mathf.Abs(xBot - xTop); } }
        public float Drop { get { return yTop - yBot; } }
        /// <summary>走り方向の正規化位置(0=上端 1=下端)。範囲外は clamp しない</summary>
        public float U(float x) { return (x - xTop) / (xBot - xTop); }
        public float Level(float u) { return Mathf.Lerp(yTop, yBot, Mathf.Clamp01(u)); }
        /// <summary>法面(盛土)の芯。石段の芯と同じ。</summary>
        public float NoriZ { get { return (z0 + z1) * 0.5f; } }
        /// <summary>石垣の開口の半幅 = 芯 → 坂の土留めの**外面**。</summary>
        public float GapHalf { get { return noriHalf + SAKA_T; } }
        // ---- 登廊(方針B) ----
        /// <summary>踊り場の外端 = 降り始める x。石垣の法尻より外。</summary>
        public float NbTop { get { return xTop + Mathf.Sign(xBot - xTop) * odoriKen * KEN; } }
        /// <summary>登廊の下端。踊り場のぶんだけ石段より外へ出る。</summary>
        public float NbBot { get { return NbTop + (xBot - xTop); } }
    }
    // 石段は**東=段板2枚(3.96m)の参道 / 西=1枚(1.98m)** で、肩は左右 0.60m(指図 其十 ②)。
    // 西は登廊の帯(下郭のマス目 V51..52)を動かせないので、**法面のほうを北へ 2.80m 移した**。
    //   屋根の北軒 1043.19 → 南の土止めの外面 1043.48(犬走り 0.29)→ 内面 1044.20
    //   → 石段 1044.81〜1046.79(芯 1045.80) → 北の土止め 内面 1047.40 / 外面 1048.12
    public static Kai[] Kaidans()
    {
        return new[] {
            // 東: 表門からの参道。石垣の開口(芯 z=1001)を出て下段へ 9m で降りる。登廊は架けない
            new Kai{ name="Ishidan_E1", xTop=-455f, xBot=-446f, z0=999f,    z1=1003f,   yTop=25.5f, yBot=19.5f, noriHalf=2.58f },
            new Kai{ name="Ishidan_E2", xTop=-425f, xBot=-416f, z0=999f,    z1=1003f,   yTop=19.5f, yBot=13.5f, noriHalf=2.58f },
            // 西: 郭の北縁。法面の芯 z=1045.80(旧 1043.00)。登廊は土止めの外(南)で柱に載る
            // ⚠ 踊り場は 2 間(3.636m)だと石垣の法尻(x −569.6)まで 0.04m しか余らず、
            //   階段廊下と一番上の柱が石垣の裾に 0.05m 触れた(実測)。3 間で 1.85m 逃がす
            new Kai{ name="Ishidan_W1", xTop=-566f, xBot=-575f, z0=1043.8f, z1=1047.8f, yTop=25.5f, yBot=19.5f, noriHalf=1.60f, noboriro="W1", odoriKen=3 },
            new Kai{ name="Ishidan_W2", xTop=-592f, xBot=-604f, z0=1043.8f, z1=1047.8f, yTop=19.5f, yBot=11.5f, noriHalf=1.60f, noboriro="W2", odoriKen=3 },
        };
    }

    // =========================================================================
    // 登廊(のぼりろう) — 屋根付きの階段廊下
    //
    // 【なぜ】郭と郭は 6〜8m の段差で、そこを渡るのに一度屋外へ出て石段を降りるのは
    //   屋敷の内部動線として不自然(ユーザー指摘 2026-08-15)。西の2本(主郭→中段→西低地)を
    //   屋根で覆い、御殿から出ずに降りられるようにする。**表門からの参道(E1/E2)は覆わない** —
    //   前庭は開けた白洲、というのが指図 v5 の結論なので、公的動線に屋根は架けない。
    //
    // 【作り】石段と坂の土留めはそのまま床・欄干として使い、上に柱と屋根を架けるだけ。
    //   屋根は平らな切妻を斜長ぶん作り(build_goten_roof.py -- noboriro)、据えるときに
    //   勾配ぶん傾ける。傾けるので軒も棟も坂と平行に走る = 頭上の高さが一定になる。
    // =========================================================================
    // 法面の平場(幅4.4m)の中で、屋外の石段と階段廊下を**並べて**置く。
    //   北側 +1.15 … 屋外用の石段(段板1枚 1.98m)
    //   南側 -1.25 … 階段廊下(幅一間 1.818m)。取り付きの廊下(LW_Kita6/9)の z 帯もここ
    // 階段廊下の帯は**下郭のマス目(WG V51..52 = z 1040.718..1042.536)にスナップ**する。
    // ⚠ 端数の位置に置くと取り付きの廊下がマス目に乗らず、階段の**側面**に付き当たる。
    //   側面には高欄が回っているので、寄せても通れない(ユーザー指摘 2026-08-15)。
    //   取り付きは必ず階段の**端**へ、同じ帯で、正面から継ぐこと。
    /// <summary>階段廊下の中心 z。**絶対値**で持つ(指図 其十 ②)。
    /// 下郭のマス目 WG V51..52 = z 1040.718〜1042.536 の芯。法面の芯を動かしても、ここは動かさない —
    /// 動かすと取り付きの廊下を全部引き直すことになる。屋根はここ ±1.565 = 1040.06〜1043.19。</summary>
    const float NOBORI_ZC = 1041.627f;
    // ⚠ ISHIDAN_Z は撤廃した(指図 其十 ②)。石段は**法面の芯そのもの**に置く。
    //   其七 の +1.60 は「同じ法面に木階段を同居させる」前提のオフセットだった。

    /// <summary>登廊(方針B・指図 其十 ②)。
    ///
    /// 【方針B】木階段は<b>盛土の坂に載せない</b>。石段の法面(両側を土留めで留めた盛土)は
    ///   石階段だけのもので、木階段はその南を<b>柱で宙に浮いて</b>降りる(懸造り)。
    ///   石垣には木階段のための開口を<b>開けない</b> — 天端を跨いで外へ出る。
    ///
    /// 【なぜ踊り場が要るか】床は坂上で 天端 +0.62 しかないので、そのまま 33.7° で降りると
    ///   0.93m 進んだところで床が天端より下に潜り、跨げない。<b>石垣の法尻まで水平に渡ってから</b>
    ///   降り始める。踊り場の柱は天端に、坂の柱は下郭の地面に立つ。</summary>
    static void Noboriro(Transform parent, Kai k)
    {
        if (string.IsNullOrEmpty(k.noboriro)) return;
        var g = new GameObject(k.name + "_Noboriro"); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "noboriro");
        float zc = NOBORI_ZC;                                  // 帯は絶対値。法面の芯とは別物
        float pitch = Mathf.Atan2(k.Drop, k.Run) * Mathf.Rad2Deg;
        bool east = k.xBot > k.xTop;
        float dir = Mathf.Sign(k.xBot - k.xTop);
        float xNb = k.NbTop, xNbBot = k.NbBot;                 // 降り始め / 下端
        float floorTop = k.yTop + GOTEN_FLOOR;

        // ---- 踊り場(水平) — 郭の縁から石垣の法尻まで。屋根つき一間の渡廊下 ----
        if (k.odoriKen > 0)
        {
            float ox0 = Mathf.Min(k.xTop, xNb), oz0 = zc - KEN * 0.5f;
            var od = EdoGotenKit.Roka(k.name + "_Odoriba", g.transform,
                new Vector3(ox0, k.yTop, oz0), 0f, k.odoriKen, GOTEN_FLOOR,
                koranS: true, koranN: true, colStart: false, colEnd: false);
            Undo.RegisterCreatedObjectUndo(od, "odoriba");
            // 束は入れない — 下は石垣の躯体なので、地面まで落とすと壁を貫く。
            // 郭の縁の一対だけ天端に立てる
            float sy0 = GOTEN_FLOOR / EdoAssets.Goten.DoorH;
            for (int s0 = 0; s0 < 2; s0++)
                Put(g.transform, EdoAssets.Goten.Column,
                    new Vector3(k.xTop, k.yTop, zc + (s0 == 0 ? -KEN * 0.5f : KEN * 0.5f)), 0f, sy0);
        }

        // ---- 階段廊下(木の段) — 原点は坂上・上段の廊下の床。走りはローカル -Z ----
        var kr = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Goten.KaidanRoka(k.Run, k.Drop));
        if (kr == null)
        {
            Debug.LogError("[Okabe] 階段廊下が無い: " + EdoAssets.Goten.KaidanRoka(k.Run, k.Drop)
                + " — blender ... build_goten_kaidan.py -- <走り> <落差>");
        }
        else
        {
            var go2 = (GameObject)PrefabUtility.InstantiatePrefab(kr, g.transform);
            Undo.RegisterCreatedObjectUndo(go2, "kaidanroka"); go2.name = "KaidanRoka";
            go2.transform.position = new Vector3(xNb, floorTop, zc);
            go2.transform.rotation = Quaternion.Euler(0f, east ? 270f : 90f, 0f);
        }
        // ---- 柱 — 廊下の両縁。**地面から屋根裏まで一本**で通す(懸造り) ----
        // ⚠ 旧版は法面(盛土)の上に 0.9m の束を立てていた。方針B では下に盛土が無いので、
        //   下郭の地面まで通す。W1 で最長 6.6m、W2 で 8.6m になる。
        int n = Mathf.Max(2, Mathf.RoundToInt(k.Run / KEN));
        float above = EdoGotenKit.ROKA_EAVE + EdoGotenKit.ROKA_KETA;   // 床から屋根裏まで
        for (int i = 0; i <= n; i++)
        {
            float u = (float)i / n;
            float px = Mathf.Lerp(xNb, xNbBot, u), lv = k.Level(u) + GOTEN_FLOOR;
            for (int s2 = 0; s2 < 2; s2++)
            {
                float pz = zc + (s2 == 0 ? -KEN * 0.5f : KEN * 0.5f);
                float gy = G(px, pz);                       // 実際の地盤
                float h = (lv + above) - gy;
                if (h < 0.3f) continue;
                Put(g.transform, EdoAssets.Goten.Column, new Vector3(px, gy, pz),
                    0f, h / EdoAssets.Goten.DoorH);
            }
        }
        // ---- 屋根 — 平らな切妻(幅一間)を斜長ぶん作ってあるので、勾配ぶん倒して据える ----
        var roof = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Goten.RoofNoboriro(k.noboriro));
        if (roof == null)
        {
            Debug.LogError("[Okabe] 登廊の屋根が無い: " + EdoAssets.Goten.RoofNoboriro(k.noboriro));
            return;
        }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(roof, g.transform);
        Undo.RegisterCreatedObjectUndo(go, "roof"); go.name = "Roof";
        go.transform.position = new Vector3((xNb + xNbBot) * 0.5f,
            (k.yTop + k.yBot) * 0.5f + GOTEN_FLOOR + EdoGotenKit.ROKA_EAVE, zc);
        // Euler(0,yaw,roll) = Ry(yaw)*Rz(roll)。Rz が先に大棟を倒し、Ry が坂下へ向ける
        go.transform.rotation = Quaternion.Euler(0f, east ? 0f : 180f, -pitch);
        if (dir == 0f) Debug.LogError("[Okabe] 登廊の走りが 0: " + k.name);
    }

    const float ROOF_RATIO = 0.5456f;   // 屋根の勾配比(build_goten_roof の RATIO)

    /// <summary>石段の法面の高さ。段の下に地面を作るための盛土の楔。
    /// 戻り値 = その点での重み(0 なら法面の外)。段板は法面より 0.15 上に出る。</summary>
    public static float NoriHeight(float wx, float wz, out float h)
    {
        h = 0f; float best = 0f;
        foreach (var k in Kaidans())
        {
            float u = k.U(wx);
            if (u < 0f || u > 1f) continue;
            float zc = k.NoriZ;
            float dz = Mathf.Max(0f, Mathf.Abs(wz - zc) - k.noriHalf);
            float w = Mathf.SmoothStep(0f, 1f, 1f - Mathf.Clamp01(dz / NORI_FEATHER));
            if (w <= best) continue;
            // 段の芯線(蹴上の中ほど)を地面にすると、踏面が 0.15 出て蹴上が見える
            float ends = Mathf.SmoothStep(0f, 1f, Mathf.Min(u, 1f - u) / 0.06f);
            best = w; h = k.Level(u) - 0.15f * ends;
        }
        return best;
    }

    /// <summary>法面の両脇を留める「坂の土留め」の据え付け。
    /// **一枚物で天端が勾配どおりに斜めに下がる部材**を左右に1本ずつ置く
    /// (Tools/Blender/build_ishigaki_saka.py で生成。EdoAssets.Own.IshigakiSaka)。
    ///
    /// ⚠ v6 は Castle Wall を1.8m刻みで据えて天端を段々に下げていた。実物の石段の袖は
    ///   一直線の斜めで、段々では左右で段の位置がずれてちらつく
    ///   (ユーザー指摘 2026-08-15 + 妙義神社本殿の石段の写真)。
    ///
    /// 部材は芯線を挟んで左右対称(±0.36)なので、芯線を平場の縁から半分だけ外へ出す。
    /// 原点 = 坂上の端・下段の地面。ローカル **-Z** が坂下を向くよう yaw を決める。</summary>
    public struct SakaWall { public Vector3 pos; public float yaw; public string asset, name; }
    public static List<SakaWall> NoriWalls()
    {
        const float HALF_T = SAKA_T * 0.5f;             // 部材の半厚(笠石を含む)
        var outp = new List<SakaWall>();
        foreach (var k in Kaidans())
        {
            float zc = k.NoriZ;
            // ⚠ 走りは部材のローカル **-Z**。Blender の +Y は Unity の -Z へ落ちる
            //   (export_fbx の axis_forward='-Z' / axis_up='Y')。+Z のつもりで yaw を
            //   決めると坂が逆へ伸びる(実際にやった)
            float yaw = k.xBot > k.xTop ? 270f : 90f;
            string a = EdoAssets.Own.IshigakiSaka(k.Run, k.Drop);
            for (int side = 0; side < 2; side++)
            {
                float zw = zc + (side == 1 ? 1f : -1f) * (k.noriHalf + HALF_T);
                outp.Add(new SakaWall{ pos = new Vector3(k.xTop, k.yBot, zw), yaw = yaw,
                                       asset = a, name = k.name + (side == 1 ? "_N" : "_S") });
            }
        }
        return outp;
    }

    [MenuItem("Edo/岡部筑前守上屋敷/坂の土留めのマテリアルをremap")]
    public static void RemapSakaMaterials()
    {
        int n = 0;
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Edo/Models/Ishigaki" }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var imp = AssetImporter.GetAtPath(path) as ModelImporter;
            if (imp == null) continue;
            imp.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            imp.SearchAndRemapMaterials(ModelImporterMaterialName.BasedOnMaterialName,
                                        ModelImporterMaterialSearch.Everywhere);
            AssetDatabase.WriteImportSettingsIfDirty(path);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            if (imp.GetExternalObjectMap().Count > 0) n++;
            else Debug.LogWarning("[Okabe] マテリアルが当たらなかった: " + path);
        }
        AssetDatabase.SaveAssets();
        Debug.Log("[Okabe] 坂の土留めのマテリアル remap: " + n + "件");
    }

    // 表門(下書きの三角マーク) と その外向き    // 表門(下書きの三角マーク) と その外向き
    // ⚠ 下書きの三角マークは外周線 P[0]→P[10] から **2.25m 内へ外れて**いた(実測 2026-08-15)。
    //   その点で run を切ると芯が 1.2°傾き、棟は外周線の方位で置くので長屋の街路面が
    //   **棟ごとに 0.37m の鋸歯**になり、門へ向かって 1.83m 内へ流れた(指図 其八ノ二 ①)。
    //   GATE は**外周線の上**に取る。門の直交位置は下の SeatGate で長屋の面へ揃える。
    public static readonly Vector2 GATE = new Vector2(-378.76f, 1001.24f);
    public static Vector2 GateOut() { return (-B.InwardNormal(SK.OKABE, 10)).normalized; }
    public static float YawGate() { var o = GateOut(); return Mathf.Atan2(o.x, o.y) * Mathf.Rad2Deg; }

    // 外周長屋・塀・内部長屋の芯線(下書きを垂直水平に正規化)
    // =========================================================================
    // 外周(指図 其六) — run は「郭ごとに割って一本一天端」。地形追従で置かない。
    //
    // 【天端 top】その run が面する郭の高さ。段の外(北辺・西辺)は生地形の中央値を
    //   0.5m 刻みに丸めたもの。run の中では**一定**で、段差は run の継ぎ目で落とす。
    //   ⚠ 地面に一枚ずつ落とすと、一本の run の中で天端が最大 17.7m 振れる(2026-08-15 実測)。
    //
    // 【種別 kind】格式の要る面ほど築地塀、裏手ほど長屋
    //   [追川2017→宮崎1994]「築地塀こそが正式…表長屋は略式で薄礼」→「表門に連なる塀に
    //   長屋塀を構築することを避けた」。加賀藩本郷邸(確度A)も表門の通り側に長屋が無い。
    //   ・東辺(三べ坂・表門)   = **長屋塀**        確度B ← 表門が長屋門(格式表)なので連続させる
    //   ・南辺(山王社の境内)   = 築地塀            確度B ← 神社へ生活の場を向けるのは薄礼
    //   ・北辺(隣地)           = 長屋塀            確度B ← ここが長屋の置き場所
    //   ・西辺(溜池・庭園帯)   = 竹垣              確度? ← 塀で閉じると外廊下から望む景を塞ぐ
    //     典拠: 広重「赤坂桐畑」に対岸の木の柵。ただし寺群の囲いの可能性が高く類推にとどまる
    //   【典拠: 一般類型 / 当屋敷の一次史料は未確認】
    // =========================================================================
    /// <summary>None = **囲いを建てない辺**(指図 其十 ③)。土井邸との共有境界がこれ。
    /// run そのものは残す — 造成が「境界の高さ」としてこの top を使うので、消すと法面の行き先が無くなる。</summary>
    public enum Kakoi { Tsuiji = 0, Nagaya = 1, Takegaki = 2, None = 3 }
    public struct Run
    {
        public Vector2 a, b, outw; public string name;
        public Kakoi kind; public float top;      // top = 天端(この run を通して一定)
        public bool nagaya { get { return kind == Kakoi.Nagaya; } }
    }
    /// <summary>外周の run。指図 其六 の表と同じ順・同じ値。</summary>
    public static Run[] Runs()
    {
        var P = SK.OKABE;
        Func<int, Vector2> eo = i => -B.InwardNormal(P, i);
        var d10 = (P[0] - P[10]).normalized;              // 東辺の走り(北→南)
        // 南辺は郭の境(x=-592/-566/-455/-425)で割る。辺 P3→P2→P1→P0 の上の点を x から求める
        Func<Vector2, Vector2, float, Vector2> px = (u, v, X) =>
            Vector2.Lerp(u, v, Mathf.Clamp01((X - u.x) / (v.x - u.x)));
        var s3_2 = new Func<float, Vector2>(X => px(P[3], P[2], X));
        var s2_1 = new Func<float, Vector2>(X => px(P[2], P[1], X));
        var s1_0 = new Func<float, Vector2>(X => px(P[1], P[0], X));
        return new[] {
            // ---- 南辺(山王社) 築地塀。郭ごとに割る ----
            new Run{ name="Hei_S_W",  a=P[3],          b=s3_2(-592f), outw=eo(2), kind=Kakoi.Tsuiji, top=11.5f },
            new Run{ name="Hei_S_Cd", a=s3_2(-592f),   b=s2_1(-566f), outw=eo(2), kind=Kakoi.Tsuiji, top=19.5f },
            new Run{ name="Hei_S_Sk", a=s2_1(-566f),   b=s1_0(-455f), outw=eo(1), kind=Kakoi.Tsuiji, top=25.5f },
            new Run{ name="Hei_S_Te", a=s1_0(-455f),   b=s1_0(-425f), outw=eo(0), kind=Kakoi.Tsuiji, top=19.5f },
            new Run{ name="Hei_S_Mz", a=s1_0(-425f),   b=P[0],        outw=eo(0), kind=Kakoi.Tsuiji, top=13.5f },
            // ---- 東辺(三べ坂・表門) **長屋塀**。表門が長屋門なので門から長屋が連続する ----
            // ⚠ 一度ここを築地塀にしたが誤り(2026-08-15、ユーザー指摘)。
            //   根拠にした [追川2017→宮崎1994]「表門に連なる塀に長屋塀を避けた」と加賀藩本郷邸は
            //   **102万石の国持大名=放れ門**の話で、そもそも長屋門ではない。
            //   格式表が5万石以上に長屋門を定める以上、門から長屋が連続するのが筋。
            //   **門の形式と辺の囲いの種別は必ず整合させる。**
            // 塀の切り位置は**門の実寸から**出す。±6.5 の決め打ちだと門の躯体(幅22.5m)を貫通した
            new Run{ name="NG_E_S",  a=P[0], b=GATE + d10 * MON_HALF, outw=eo(10), kind=Kakoi.Nagaya, top=13.5f },
            new Run{ name="NG_E_N",  a=GATE - d10 * MON_HALF, b=P[10], outw=eo(10), kind=Kakoi.Nagaya, top=13.5f },
            // ---- 北東の隅切り〜北辺(隣地) 長屋塀。40m 以下に割る ----
            new Run{ name="NG_NE",    a=P[10], b=P[9], outw=eo(9), kind=Kakoi.Nagaya, top=13.5f },
            new Run{ name="NG_N1",    a=P[9],  b=P[8], outw=eo(8), kind=Kakoi.Nagaya, top=15.5f },
            // ---- 北辺 P[8]→P[7]→P[6] = 土井大隅守邸との共有境界。**築地塀・4段**(指図 其十一) ----
            // 【誰が持つか】ユーザー裁定 2026-08-16(確度U)。**史料では決まらなかった** —
            //   屋敷境の囲いを「どちらが担うか」の規則は公開範囲で確認できていない
            //   (`sources.md` の未解決項)。裏づけがあるのは**囲いは1条**という所見だけ
            //   ([丸の内三丁目] 確度A: 隣り合う2家の屋敷境に引かれたのは1条の区画溝)。
            //   → **岡部が持ち、土井側のこの辺の囲いは削除**して1条にする。
            // 【なぜ4本しかないか】築地塀は**版築**(水平の層を積む)なので一枚の壁面は水平にしかならない。
            //   地形なりに上下させない(ユーザー指摘 2026-08-16)。境界は延長 184.7m・高低差 17.8m の
            //   尾根越えなので、**石垣で段に造成し、その天端に塀を水平に載せる**。
            //   段の割りは「最大の石垣を最小化」して解いた結果(最大 6.9m)。s は境界に沿った距離。
            //     R1 s   0〜 20  天端 21.0   R2 s  20〜130  天端 27.0
            //     R3 s 130〜155  天端 21.0   R4 s 155〜185  天端 14.5(P[7] で折れるので必ずここで割る)
            new Run{ name="Hei_N1", a=P[8], b=Vector2.Lerp(P[8],P[7],0.12897f), outw=eo(7), kind=Kakoi.Tsuiji, top=21.0f },
            new Run{ name="Hei_N2", a=Vector2.Lerp(P[8],P[7],0.12897f), b=Vector2.Lerp(P[8],P[7],0.83829f), outw=eo(7), kind=Kakoi.Tsuiji, top=27.0f },
            new Run{ name="Hei_N3", a=Vector2.Lerp(P[8],P[7],0.83829f), b=P[7], outw=eo(7), kind=Kakoi.Tsuiji, top=21.0f },
            new Run{ name="Hei_N4", a=P[7], b=P[6], outw=eo(6), kind=Kakoi.Tsuiji, top=14.5f },
            // ---- 西辺(溜池・庭園帯) 竹垣 ----
            new Run{ name="Take_W1", a=P[6], b=P[5], outw=eo(5), kind=Kakoi.Takegaki, top=8.7f },
            new Run{ name="Take_W2", a=P[5], b=P[4], outw=eo(4), kind=Kakoi.Takegaki, top=8.5f },
            new Run{ name="Take_W3", a=P[4], b=P[3], outw=eo(3), kind=Kakoi.Takegaki, top=8.0f },
        };
    }

    // 着工前の地形。**無ければ書き、あれば触らない**(Stage0_Backup)。
    // v12 = 指図 其十 の造成やり直しの直前(2026-08-16 20:0x)に取ったもの。
    static string BAK = "/private/tmp/claude-501/-Users-toshio-project-edo-unity/"
        + "76eabbdb-8a14-44cf-9da1-c2e82fcacb00/scratchpad/okabe_before_v12.bin";
    // 廊下・参道の部材は EdoAssets.Goten(御殿と同じキット)。Village Kit の床・柱・屋根は
    // v4 で全廃した — 御殿と並べると質が揃わない、というユーザー裁定(2026-08-15)
    const string PStep = EdoAssets.Own.DanishiStep;
    const float NUREEN = 0.89f;         // 濡縁(Goten_Nureen_1ken)が棟の外形から出る寸法
    const string PKnagayaC = EdoAssets.Eg.KnagayaC;
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

    /// <summary>表門 → 玄関の参道の帯(v5)。中心線 z=1001・幅6m、表門(-381)から玄関棟の東面(-458.8)まで。
    /// 屋根付き廊下を廃した代わりに、ここを開けておく(白洲の踏み分け)。植栽もここには置かない。</summary>
    public static bool InSando(float x, float z, float margin)
    {
        return z > 998f - margin && z < 1004f + margin && x > -459f - margin && x < -379f + margin;
    }

    static float G(float x, float z) { return B.Ground(x, z); }
    static Transform Grp(string n) { return B.Group(GN, n); }
    static void Clear(Transform t) { var l = new List<Transform>(); foreach (Transform c in t) l.Add(c); foreach (var c in l) UnityEngine.Object.DestroyImmediate(c.gameObject); }
    static float DistSeg(Vector2 p, Vector2 a, Vector2 b)
    { var d = b - a; float L = d.magnitude; if (L < 1e-4f) return (p - a).magnitude; d /= L; float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, L); return (p - (a + d * t)).magnitude; }

    // =========================================================================
    // Stage 0/1: バックアップと段の造成
    // =========================================================================
    /// <summary>着工前の地形を .bin へ。**無いときだけ書く**(指図 其十 ①)。
    /// ⚠ 旧版は走るたび上書きしていたので、造成済みの(壊れた)地形がバックアップに化けていた
    ///   — 実際 2026-08-16 16:48 の版は既に造成後の地形だった。バックアップは一度きり。</summary>
    public static string Stage0_Backup()
    {
        if (System.IO.File.Exists(BAK)) return "backup: 既にある(上書きしない) " + BAK;
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        // 窓は Stage1_Grade と揃える(揃えないと造成した外側を戻せない)
        int bx0 = IX(-700f), bx1 = IX(-366f), bz0 = IZ(930f), bz1 = IZ(1102f);
        int bw = bx1 - bx0 + 1, bh = bz1 - bz0 + 1;
        var bak = td.GetHeights(bx0, bz0, bw, bh);
        var dir = System.IO.Path.GetDirectoryName(BAK);
        if (!System.IO.Directory.Exists(dir)) System.IO.Directory.CreateDirectory(dir);
        using (var w = new System.IO.BinaryWriter(System.IO.File.Open(BAK, System.IO.FileMode.Create)))
        { w.Write(bx0); w.Write(bz0); w.Write(bw); w.Write(bh);
          for (int z = 0; z < bh; z++) for (int x = 0; x < bw; x++) w.Write(bak[z, x]); }
        return "backup " + bw + "x" + bh;
    }

    // =========================================================================
    // 設計面(指図 其十 ①) — 敷地の**内側 100%** に高さを与える三層。
    //
    //   ① 段(Terraces)      … 矩形の中は設計値そのまま
    //   ② 外周帯(BAND_FLAT) … 石垣の芯線から内へ 9m は run の天端で平ら
    //   ③ **法面**(新設)    … ①にも②にも属さない所は、
    //                          「最寄りの段の高さ」と「最寄りの run の天端」を距離で内挿する
    //
    // 【なぜ③が要るか】旧版は①②の外を `continue` で**一度も触らなかった**。段の矩形は
    //   z 946〜1058 / x −647〜−374 しかないのに敷地は z 936.8〜1096.3 / x −694.7〜−373 で、
    //   北で最大 38m・西で最大 43m が素地形のまま残り、段の縁と生地形が垂直にぶつかっていた。
    //   これが「地形の変な隆起や窪み」(下書き赤)と「西低地から溜池への段差」(同 白)の正体。
    //
    // 【帯は線分から測る】旧版の帯の判定は run の**直線**からの符号付き距離 din だけで、
    //   線分の範囲を見ていなかった。din は run の走り方向へ無限に伸びるので、ボロノイ胞が
    //   郭の中央まで届く北辺の斜めの run が、その天端(12.5 / 15.5)を主郭の中まで引き込み、
    //   主郭を斜めに 8m 掘っていた(溝A・溝B)。**max(din, bd)** で測れば線分から離れた時点で
    //   帯を外れる。
    // =========================================================================
    public const float BAND_FLAT = 9f;      // 芯線から内へ、run の天端で平らにする幅

    /// <summary>隣地と地続きの辺(Kakoi.None)の境界高さ。**相手の地面に合わせる**。
    ///
    /// 塀が無い以上、こちらと向こうの地面は連続していなければならない。run ごとに一定の天端を
    /// 使うと、隣り合う run の継ぎ目に段差が立つ(実測: <c>Sakai_N2a</c> 21.5 と <c>N2b</c> 26.0 の
    /// 継ぎ目に 4.5m)。境界の最寄り点から**外へ 6m** の実地形を拾えば、土井側の地面
    /// (18.7 → 26.6 → 14.1 → 9.5)へなめらかに擦り付く。
    ///
    /// ⚠ 造成の窓は敷地多角形の内側だけなので、外 6m の地形は**こちらの造成で動かない**。
    ///   よって DesignY は依然として冪等。</summary>
    static float BoundaryY(Run r, Vector2 p)
    {
        var d = r.b - r.a; float L = d.magnitude; if (L < 1e-4f) return r.top;
        d /= L;
        float u = Mathf.Clamp(Vector2.Dot(p - r.a, d), 0f, L);
        var q = r.a + d * u + r.outw * 6f;
        return G(q.x, q.y);
    }

    /// <summary>敷地内の一点の設計高さ。**現況の地形に一切依存しない絶対値**
    /// (隣地と地続きの辺だけは相手の地面を読むが、そこは造成の窓の外なので動かない)。
    /// これが冪等性の根拠 — 何度造成しても同じ結果になる。</summary>
    public static float DesignY(Vector2 p)
    {
        var runs = Runs(); var terr = Terraces();
        // ---- 最寄りの run(ボロノイ)と、その芯線から内への距離 ----
        int bi = 0; float bd = float.MaxValue;
        for (int i = 0; i < runs.Length; i++)
        { float dd = DistSeg(p, runs[i].a, runs[i].b); if (dd < bd) { bd = dd; bi = i; } }
        float rcore = FaceOff(runs[bi].kind) - 1.4f * WallScaleFor(runs[bi].name);
        float din = rcore - Vector2.Dot(p - runs[bi].a, runs[bi].outw);
        // 帯の内縁からの距離。**max(din, bd)** が肝 — bd を噛ませることで
        // 「直線の帯だが線分からは遠い」セルを弾く
        float dInner = Mathf.Max(0f, Mathf.Max(din, bd) - BAND_FLAT);
        float yR = runs[bi].kind == Kakoi.None ? BoundaryY(runs[bi], p) : runs[bi].top;
        // ---- 最寄りの段(矩形)と、そこまでの距離(中にいれば 0) ----
        float yT = 0f, dT = float.MaxValue;
        foreach (var tr in terr)
        {
            float dx = Mathf.Max(Mathf.Max(tr.x0 - p.x, p.x - tr.x1), 0f);
            float dz = Mathf.Max(Mathf.Max(tr.z0 - p.y, p.y - tr.z1), 0f);
            float d = Mathf.Sqrt(dx * dx + dz * dz);
            if (d < dT) { dT = d; yT = tr.y; }
        }
        // ---- 三層の合成 ----
        // dT=0 かつ dInner>0 → 段の中     / dInner=0 かつ dT>0 → 帯の中
        // どちらも >0 → 法面(距離で内挿) / どちらも 0 → 帯と段が重なる所(天端は一致させてある)
        float y = (dT + dInner < 1e-4f) ? yT : Mathf.Lerp(yT, yR, dT / (dT + dInner));
        // ---- 石段の法面(盛土の楔) — 段の上に重ねる ----
        float nori; float wn = NoriHeight(p.x, p.y, out nori);
        if (wn > 0f) y = Mathf.Lerp(y, nori, wn);
        return y;
    }

    /// <summary>造成。**設計面へ一発で持っていく**(指図 其十 ①)。
    ///
    /// ⚠ 旧版には二つの履歴依存があり、一度壊れた地形が自己修復しなかった:
    ///   ・<c>Clamp(best, cur−5.5, cur+5.0)</c> … 現況からの差分で頭打ち。8m の溝は 5m しか埋まらない
    ///   ・<c>OKABE_GRADED_vNN</c> マーカー   … 二回目以降は SKIP。実質一回きり
    ///   設計面が絶対値になった以上どちらも不要。**切盛の量は報告するだけ**にする。</summary>
    public static string Stage1_Grade()
    {
        // 旧マーカーは掃除する(もう使わない)
        foreach (var nm in new[] { "OKABE_GRADED_v4", "OKABE_GRADED_v5", "OKABE_GRADED_v6", "OKABE_GRADED_v7",
                                   "OKABE_GRADED_v8", "OKABE_GRADED_v9", "OKABE_GRADED_v10", "OKABE_GRADED_v11" })
        { var o = GameObject.Find(nm); if (o != null) UnityEngine.Object.DestroyImmediate(o); }
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<int, float> WX = ix => tp.x + ix * ts.x / (hres - 1);
        Func<int, float> WZ = iz => tp.z + iz * ts.z / (hres - 1);
        // 窓は敷地の外接矩形を丸ごと覆う
        int x0 = IX(-700f), x1 = IX(-366f), z0 = IZ(930f), z1 = IZ(1102f);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        int n = 0; float cmax = 0, fmax = 0;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            var p = new Vector2(WX(x0 + x), WZ(z0 + z));
            if (!B.PIP(SK.OKABE, p)) continue;          // 敷地の外は一切触らない
            float cur = H[z, x] * ts.y + tp.y;
            float y = DesignY(p);
            if (y < cur) cmax = Mathf.Max(cmax, cur - y); else fmax = Mathf.Max(fmax, y - cur);
            H[z, x] = (y - tp.y) / ts.y; n++;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        // ⚠ ここで出るのは「**いまの地形からの移動量**」であって切盛量ではない。壊れた地形を
        //   直す回は大きく出るのが正しい。設計の妥当性(切盛が 1〜4m に収まるか)は
        //   **設計面 vs 素地形**で見ること — 指図 其十 ①の表がそれ。
        return "grade cells=" + n + " 今回の移動量: 下げ最大=" + cmax.ToString("F2") + " 上げ最大=" + fmax.ToString("F2");
    }

    /// <summary>造成の検査(指図 其十 ①)。敷地内の全セルで |地形 − 設計面| を測る。
    /// PerimeterQA(天端)・GroundQA(足元)・GateQA・JointQA に次ぐ **5 本目の軸**。
    /// これが無いと「直したはずが直っていない」を目視で見逃す。</summary>
    [MenuItem("Edo/岡部筑前守上屋敷/造成を検査 GradeQA")]
    public static void GradeQAMenu() { Debug.Log("[Okabe] " + GradeQA()); }
    public static string GradeQA()
    {
        const float TOL = 0.30f;
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        // ⚠ **ハイトマップの格子の上で測る**。SampleHeight を任意の座標で呼ぶと双一次補間が
        //   入り、石垣の線や石段の法面のような急な段で 0.1m のズレが 2m の差に化ける
        //   (実測: 格子から 0.12m ずらして測っただけで 228 セルが「超過」に見えた)。
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        int x0 = IX(-700f), x1 = IX(-366f), z0 = IZ(930f), z1 = IZ(1102f);
        var H = td.GetHeights(x0, z0, x1 - x0 + 1, z1 - z0 + 1);
        int bad = 0, all = 0; float mx = 0f; Vector2 worst = Vector2.zero;
        for (int z = 0; z <= z1 - z0; z++) for (int x = 0; x <= x1 - x0; x++)
        {
            var p = new Vector2(tp.x + (x0 + x) * ts.x / (hres - 1), tp.z + (z0 + z) * ts.z / (hres - 1));
            if (!B.PIP(SK.OKABE, p)) continue;
            all++;
            float d = Mathf.Abs((H[z, x] * ts.y + tp.y) - DesignY(p));
            if (d > TOL) bad++;
            if (d > mx) { mx = d; worst = p; }
        }
        return string.Format("造成QA 敷地内 {0} セル / 許容 {1:F2}m ｜ 超過 {2} ({3:F1}%) 最大 {4:F2}m @({5:F0},{6:F0}) {7}",
            all, TOL, bad, bad * 100f / Mathf.Max(1, all), mx, worst.x, worst.y, bad > 0 ? "✗" : "✔");
    }

    // =========================================================================
    // Stage 2: 全再接地(設計レベルで据えてあるものは除外)
    //
    // ⚠ **Buildings(御殿の棟)を再接地してはいけない**(2026-08-15 に発覚)。
    //   棟は「床が地面から 0.62 上がり、濡縁がその 0.28 下に回る」高床で、いちばん低い
    //   ジオメトリは地面ではなく濡縁である。再接地はその濡縁を地面へ沈めるので、
    //   **棟だけが 0.44m 下がって廊下との間に段差ができていた**(ユーザー指摘)。
    //   棟・渡廊下・石段はすべて段のレベルに対して設計値で据える。地面に合わせるのは
    //   Village Kit の土蔵・厩・門など、床の高さを持たない物だけ。
    // =========================================================================
    public static string Stage2_Reseat()
    {
        int n = 0;
        var yg = GameObject.Find(GN);
        var roots = new List<Transform>();
        foreach (Transform g in yg.transform)
            // ⚠ 設計レベルで据えるものは全部除外する。**Kakoi/Omotemon も外周の天端で据える**
            //   ようになった(指図 其六)ので、再接地すると run ごとの一定天端が壊れる
            //   — 2026-08-15、棟でやったのと同じ罠を外周でも踏んだ
            if (g.name != "Roka" && g.name != "Ishidan" && g.name != "Buildings"
                && g.name != "Garden" && g.name != "Ishigaki" && g.name != "Kakoi"
                && g.name != "Omotemon"
                && g.name != "KachuNagaya" && !g.name.EndsWith("_retired")) roots.Add(g);
        var sha = GameObject.Find("Edo_Sanno_Sha"); if (sha != null) roots.Add(sha.transform);
        foreach (var grp in roots)
            foreach (Transform c in grp)
            {
                if (!c.gameObject.activeSelf) continue;
                if (c.name.StartsWith("Ishidan") || c.name.StartsWith("Tobi") || c.name.StartsWith("Roka")) continue;
                var p = new Vector2(c.position.x, c.position.z);
                if (!B.PIP(SK.OKABE, p)) continue;
                if (ReseatOne(c, 0.10f)) n++;
            }
        return "reseat " + n;
    }
    static bool ReseatOne(Transform tr, float sink)
    {
        Vector3 mn = Vector3.one * float.MaxValue, mx = Vector3.one * float.MinValue; bool any = false;
        foreach (var mf in tr.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            foreach (var v in mf.sharedMesh.vertices)
            { var lp = tr.InverseTransformPoint(mf.transform.TransformPoint(v)); mn = Vector3.Min(mn, lp); mx = Vector3.Max(mx, lp); any = true; }
        }
        if (!any) return false;
        float gmn = float.MaxValue, bot = float.MaxValue;
        for (int i = 0; i <= 2; i++) for (int j = 0; j <= 2; j++)
        {
            var wp = tr.TransformPoint(new Vector3(Mathf.Lerp(mn.x, mx.x, i / 2f), mn.y, Mathf.Lerp(mn.z, mx.z, j / 2f)));
            gmn = Mathf.Min(gmn, G(wp.x, wp.z)); bot = Mathf.Min(bot, wp.y);
        }
        float dy = (gmn - sink) - bot;
        if (Mathf.Abs(dy) < 0.005f) return false;
        tr.position += new Vector3(0, dy, 0); return true;
    }

    // =========================================================================
    // Stage 3: 旧版の撤去(削除する)
    //
    // ⚠ 2026-08-16 に方針変更。以前はここで `<名前>_v2_retired` へ退避し
    //   SetActive(false) で残していたが、**非表示のままシーンに残り続けて
    //   毎コミット LFS に積まれる**。実際に v1/v2 の2世代が溜まり、
    //   103,615オブジェクト＝シーンの35%・PrefabInstanceブロックの68.5%を占めて
    //   シーンを 246MB まで肥大させていた(2026-08-15 実測、同日ユーザー判断で削除)。
    //
    //   **旧版の保管庫は git の履歴**。見比べたければ当該コミットのシーンから取り出す。
    //   シーンに置き続けるのは保管ではなく、ただの重しだった。
    //   方針は memory:handbuilt-assets-are-canon / docs/maintenance/scene-size.md
    // =========================================================================
    public static string Stage3_Retire()
    {
        int n = 0, old = 0;
        var yg = GameObject.Find(GN);

        // 過去の方式で溜まった *_retired があれば、まとめて消す
        var stale = new List<GameObject>();
        foreach (Transform c in yg.transform) if (c.name.EndsWith("_retired")) stale.Add(c.gameObject);
        foreach (var s in stale) { old += s.GetComponentsInChildren<Transform>(true).Length; UnityEngine.Object.DestroyImmediate(s); }

        foreach (var gname in new[] { "Buildings", "Garden", "Service", "Kakoi", "Omotemon" })
        {
            var g = yg.transform.Find(gname);
            if (g == null || g.childCount == 0) continue;
            var kids = new List<Transform>(); foreach (Transform c in g) kids.Add(c);
            foreach (var c in kids) { UnityEngine.Object.DestroyImmediate(c.gameObject); n++; }
        }
        return $"removed {n}" + (old > 0 ? $" (旧 *_retired {old} も掃除)" : "");
    }

    // =========================================================================
    // Stage 4: 外周長屋・築地塀・表門・隅櫓
    // =========================================================================
    public static string Stage4_Perimeter()
    {
        NT.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        var kak = Grp("Kakoi"); Clear(kak);
        var mon = Grp("Omotemon"); Clear(mon);
        int nm = 0;
        // ⚠ **地形追従で置かない**(指図 其六)。run ごとに一つの天端で据える。
        //   追従させると一本の run の中で天端が最大 17.7m 振れて、棟が段々になる
        NT.NaturalMode = false;
        foreach (var r in Runs())
        {
            if ((r.b - r.a).magnitude < 6f) continue;
            if (r.kind == Kakoi.None) continue;         // 隣地との共有境界。囲いは相手の所有(指図 其十 ③)
            if (r.kind == Kakoi.Nagaya)
            { var l = NT.NagayaRun(kak, r.a, r.b, r.outw, r.top, Vector2.zero, -1, r.name); nm += l.Count; }
            else if (r.kind == Kakoi.Tsuiji)
                NT.DobeiRun(kak, r.a, r.b, r.outw, r.name, false, r.top, Vector2.zero, -1);
            else
                TakegakiRun(kak, r);
        }
        NT.NaturalMode = true;
        sb.AppendLine("nagaya modules=" + nm);
        sb.Append(PerimeterQA());
        // 表門(k_mon + 両番所) — 東辺、下書きの三角マーク位置
        float gh = B.PlaceGate(PKmon, mon, GATE, GateOut(), 0, "Nagayamon", sb);   // 番所は門に組み込み済み
        SeatGate(mon, kak, sb);
        // 表門も段の高さへ。地面に置くと 0.56m 沈んで両袖の塀とずれる(指図 其六 ④)
        foreach (Transform c in mon)
        {
            var rb = B.RB(c.gameObject); if (rb.size == Vector3.zero) continue;
            c.position += new Vector3(0f, 13.5f - rb.min.y, 0f);
        }
        TightenToGate(kak, mon, sb);
        // 隅櫓 [福井図: 上屋敷格の外周装置] — 敷地の南東隅・南西隅
        Yagura(kak, new Vector2(-378.5f, 950.5f), new Vector2(0.83f, -0.56f), "Sumiyagura_SE", 13.5f);
        Yagura(kak, new Vector2(-643.5f, 940.5f), new Vector2(-0.72f, -0.69f), "Sumiyagura_SW", 11.5f);
        return sb.ToString();
    }
    /// <summary>y の帯[y0,y1]にある頂点の、外向き nout への射影の最大 = **街路側の面**。
    /// 帯を軒より下に取るのが要点。全体の bbox で測ると軒の出が混ざり、AABB の角で測ると
    /// 棟が方位から数度ずれているだけで 1.2m も過大に出る(2026-08-15 実測)。</summary>
    static float FacePerp(GameObject go, Vector2 nout, float y0, float y1)
    {
        float mx = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            var ms = mf.sharedMesh; if (ms == null) continue;
            foreach (var v in ms.vertices)
            {
                var wp = mf.transform.TransformPoint(v);
                if (wp.y < y0 || wp.y > y1) continue;
                float pr = wp.x * nout.x + wp.z * nout.y;
                if (pr > mx) mx = pr;
            }
        }
        return mx;
    }

    /// <summary>表門の据え直し(指図 其八ノ二)。**長屋門は門の左右がそのまま長屋になる形式**なので、
    /// 門だけが街路へ出ていたら形式として誤り。① 走りは GATE(外周線上)、
    /// ② 街路側の**壁面**を左右の長屋の壁面へ揃える(面一)、③ 1.08 倍で棟を長屋の上に出す。
    /// ⚠ 面差は目で見て分からない(3.7m 出ていたのを何度も見落として指摘された)。数値で合わせる。</summary>
    static void SeatGate(Transform mon, Transform kak, System.Text.StringBuilder sb)
    {
        var g = mon.Find("Nagayamon"); if (g == null) { sb.AppendLine("表門が無い"); return; }
        g.localScale *= MON_SCALE;                                                    // ③
        var rb = B.RB(g.gameObject);
        g.position += new Vector3(GATE.x - rb.center.x, 13.5f - rb.min.y, GATE.y - rb.center.z);  // ①
        // ↑ 面を測る前に段の高さへ上げておく。y がずれていると壁の帯が腰石や軒に掛かって 6cm 狂う
        Vector2 nout = GateOut();
        const float WY0 = 14.0f, WY1 = 16.0f;                     // 軒より下・腰より上の帯
        var d10 = (SK.OKABE[0] - SK.OKABE[10]).normalized;
        Transform n1 = null, n2 = null; float d1 = 1e9f, d2 = 1e9f;
        foreach (Transform t in kak)                              // 門の左右に来る長屋を拾う
        {
            if (!t.name.StartsWith("NG_E_")) continue;
            var c = B.RB(t.gameObject).center; var c2 = new Vector2(c.x, c.z);
            float dd = Vector2.Distance(c2, GATE);
            if (Vector2.Dot(c2 - GATE, d10) > 0f) { if (dd < d1) { d1 = dd; n1 = t; } }
            else { if (dd < d2) { d2 = dd; n2 = t; } }
        }
        if (n1 == null || n2 == null) { sb.AppendLine("表門の隣の長屋が拾えない"); return; }
        float tgt = 0.5f * (FacePerp(n1.gameObject, nout, WY0, WY1) + FacePerp(n2.gameObject, nout, WY0, WY1));
        float now = FacePerp(g.gameObject, nout, WY0, WY1), moved = 0f;
        // 測る → 動かす を 2 回。1 回だと 0.06m 残る(帯に入る頂点の行が動いた分だけ変わるため)
        for (int i = 0; i < 2; i++)
        {
            float dz = tgt - FacePerp(g.gameObject, nout, WY0, WY1);
            g.position += new Vector3(nout.x, 0f, nout.y) * dz; moved += dz;
        }
        sb.AppendLine(string.Format("表門を据え直し: 壁面を {0:F2}m 内へ({1}/{2} と面一・残差{3:F3}m)",
                                    -moved, n1.name, n2.name, tgt - FacePerp(g.gameObject, nout, WY0, WY1)));
    }

    /// <summary>頂点ベースで、帯[y0,y1]における走り方向 dir の [min,max]。</summary>
    static Vector2 RunExtent(GameObject go, Vector2 origin, Vector2 dir, float y0, float y1)
    {
        float mn = 1e9f, mx = -1e9f;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            var ms = mf.sharedMesh; if (ms == null) continue;
            foreach (var v in ms.vertices)
            {
                var wp = mf.transform.TransformPoint(v);
                if (wp.y < y0 || wp.y > y1) continue;
                float s = (wp.x - origin.x) * dir.x + (wp.z - origin.y) * dir.y;
                if (s < mn) mn = s; if (s > mx) mx = s;
            }
        }
        return new Vector2(mn, mx);
    }

    /// <summary>長屋の run を**両端いっぱいに詰める**(ユーザー指摘 2026-08-15「長屋門と長屋の間に隙間」)。
    /// NagayaRun は run 長にモジュールの整数個を割り付けるので、端数がそのまま端の隙間になる。
    /// 実測すると**長屋の run 全部**が同じ癖で、a 端に 0.54m の隙間・b 端に 0.16m の重なり
    /// → run どうしの継ぎ目が **0.38m 開く**。門との継ぎ目(南0.34/北1.04)はその一例にすぎず、
    /// 北辺の 9 箇所も同じだった。築地塀・竹垣は元から 0.00(端数を自前で吸っている)。
    /// 直し方は**棟の間隔だけを伸縮**して端を合わせる。棟自体は拡縮しない(格子が歪む)。
    /// 棟どうしは 1.2m 重なっているので、間隔を 0.2m 広げても継ぎ目は開かない。
    /// 表門に接する端だけは run の端でなく**門の壁面**に合わせる(門は run より 0.18m 外に出る)。</summary>
    static void TightenToGate(Transform kak, Transform mon, System.Text.StringBuilder sb)
    {
        var g = mon.Find("Nagayamon");
        var P = SK.OKABE; Vector2 eOrg = P[0], eDir = (P[10] - P[0]).normalized;
        var gx = g == null ? Vector2.zero : RunExtent(g.gameObject, eOrg, eDir, 14.0f, 16.0f);
        float worst = 0f; string worstName = "";
        foreach (var r in Runs())
        {
            if (r.kind != Kakoi.Nagaya) continue;
            Vector2 dir = (r.b - r.a).normalized; float len = (r.b - r.a).magnitude;
            float y0 = r.top + 0.5f, y1 = r.top + 2.5f;            // 帯は run の天端から取る
            var mods = new List<Transform>();
            foreach (Transform t in kak) if (t.name.StartsWith(r.name + "_")) mods.Add(t);
            if (mods.Count < 2) continue;
            // 目標: run の両端いっぱい。ただし表門に接する端は**門の壁面**に合わせる
            float T0 = 0f, T1 = len;
            if (g != null && r.name == "NG_E_S") T1 = Vector2.Dot(eOrg + eDir * gx.x - r.a, dir);
            if (g != null && r.name == "NG_E_N") T0 = Vector2.Dot(eOrg + eDir * gx.y - r.a, dir);
            var sp = new List<float>();                            // 各棟のピボットの走り位置
            foreach (var t in mods) sp.Add(Vector2.Dot(new Vector2(t.position.x, t.position.z) - r.a, dir));
            float c0 = 1e9f, c1 = -1e9f;
            foreach (var t in mods)
            { var e = RunExtent(t.gameObject, r.a, dir, y0, y1); c0 = Mathf.Min(c0, e.x); c1 = Mathf.Max(c1, e.y); }
            if (c0 > 1e8f) continue;
            float pLo = Mathf.Min(sp[0], sp[sp.Count - 1]), pHi = Mathf.Max(sp[0], sp[sp.Count - 1]);
            if (pHi - pLo < 0.5f) continue;
            float e0 = pLo - c0, e1 = c1 - pHi;                     // ピボットから棟の端までの出
            float scale = ((T1 - e1) - (T0 + e0)) / (pHi - pLo);
            for (int i = 0; i < mods.Count; i++)
            {
                float ns = (T0 + e0) + (sp[i] - pLo) * scale;
                var p = r.a + dir * ns;
                mods[i].position = new Vector3(p.x, mods[i].position.y, p.y);
            }
            float gap = Mathf.Max(c0 - T0, T1 - c1);
            if (gap > worst) { worst = gap; worstName = r.name; }
        }
        sb.AppendLine(string.Format("長屋の継ぎ目を詰めた: 直前の最大隙間 {0:F2}m ({1})", worst, worstName));
    }

    /// <summary>外周の**継ぎ目**の QA — run ごとに、部材が run の両端をどこまで覆っているか。
    /// 天端(PerimeterQA)・面(GateQA)が合っていても、走り方向の端数は別に残る。
    /// 正の値 = 隙間、負の値 = 重なり(重なりは可)。</summary>
    public static string JointQA()
    {
        var yg = GameObject.Find(GN); if (yg == null) return "継ぎ目QA: グループが無い";
        var kak = yg.transform.Find("Kakoi"); if (kak == null) return "継ぎ目QA: Kakoi が無い";
        const float TOL = 0.10f;
        float worst = 0f; string wn = ""; int over = 0; var lines = new List<string>();
        foreach (var r in Runs())
        {
            Vector2 dir = (r.b - r.a).normalized; float len = (r.b - r.a).magnitude;
            float mn = 1e9f, mx = -1e9f;
            foreach (Transform t in kak)
            {
                if (t.name != r.name && !t.name.StartsWith(r.name + "_")) continue;
                var e = RunExtent(t.gameObject, r.a, dir, -1000f, 1000f);
                if (e.x > 1e8f) continue;
                mn = Mathf.Min(mn, e.x); mx = Mathf.Max(mx, e.y);
            }
            if (mn > 1e8f) { lines.Add(r.name + " 部材なし"); continue; }
            float ga = mn, gb = len - mx, g = Mathf.Max(ga, gb);
            if (g > TOL) { over++; lines.Add(string.Format("{0} a={1:F2} b={2:F2}", r.name, ga, gb)); }
            if (g > worst) { worst = g; wn = r.name; }
        }
        return string.Format("継ぎ目QA run={0} 隙間超過={1} 最大={2:F2}m({3}){4}",
                             Runs().Length, over, worst, wn,
                             over > 0 ? "\n  " + string.Join(" / ", lines.ToArray()) : "");
    }

    /// <summary>東辺の QA — 街路面の振れ(鋸歯)と、門と長屋の面差・棟差。
    /// 天端の PerimeterQA では鋸歯も面差も出ない(どちらも高さは合っている)。</summary>
    public static string GateQA()
    {
        var yg = GameObject.Find(GN); if (yg == null) return "東辺QA: グループが無い";
        var kak = yg.transform.Find("Kakoi"); var mon = yg.transform.Find("Omotemon");
        if (kak == null || mon == null) return "東辺QA: 外周が無い";
        Vector2 nout = GateOut();
        const float WY0 = 14.0f, WY1 = 16.0f;
        float mn = 1e9f, mx = -1e9f, ridge = -1e9f; int n = 0;
        foreach (Transform t in kak)
        {
            if (!t.name.StartsWith("NG_E_")) continue;
            float f = FacePerp(t.gameObject, nout, WY0, WY1);
            mn = Mathf.Min(mn, f); mx = Mathf.Max(mx, f);
            ridge = Mathf.Max(ridge, B.RB(t.gameObject).max.y); n++;
        }
        var g = mon.Find("Nagayamon");
        float gf = g == null ? 0f : FacePerp(g.gameObject, nout, WY0, WY1);
        float gr = g == null ? 0f : B.RB(g.gameObject).max.y;
        // 門と長屋の**継ぎ目**(走り方向の隙間)。面と棟が合っていても、ここは別に開く
        var P = SK.OKABE; Vector2 org = P[0], dir = (P[10] - P[0]).normalized;
        var gx = g == null ? Vector2.zero : RunExtent(g.gameObject, org, dir, WY0, WY1);
        float sHi = -1e9f, nLo = 1e9f;
        foreach (Transform t in kak)
        {
            if (t.name.StartsWith("NG_E_S_")) sHi = Mathf.Max(sHi, RunExtent(t.gameObject, org, dir, WY0, WY1).y);
            else if (t.name.StartsWith("NG_E_N_")) nLo = Mathf.Min(nLo, RunExtent(t.gameObject, org, dir, WY0, WY1).x);
        }
        return string.Format("東辺QA 長屋{0}棟 街路面の振れ={1:F2}m(許容0.10) 門の面差={2:+0.00;-0.00}m 棟 門{3:F2}/長屋{4:F2} 差{5:+0.00;-0.00}m 門との継ぎ目 南{6:+0.00;-0.00}m 北{7:+0.00;-0.00}m",
                             n, mx - mn, gf - mx, gr, ridge, gr - ridge, gx.x - sHi, nLo - gx.y);
    }

    /// <summary>竹垣の run — 水際・庭園帯の囲い。1.05m のモジュールを走りに沿って並べる。
    /// 塀と違って**低く抜けている**のが要点(外廊下から溜池を望む景を塞がない)。</summary>
    static void TakegakiRun(Transform parent, Run r)
    {
        var src = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Eg.TakeGaki);
        if (src == null) { Debug.LogError("[Okabe] 竹垣が無い: " + EdoAssets.Eg.TakeGaki); return; }
        var g = new GameObject(r.name); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "takegaki");
        Vector2 d = (r.b - r.a); float len = d.magnitude; d /= len;
        // ⚠ この部材は **長手が local Z(1.039)・厚みが local X(0.053)・高さ Y(0.900)**。
        //   塀や長屋の流儀で「表(+Z)を外へ」向けると、パネルが壁に対して**直角**に並ぶ
        //   (2026-08-15 実際にそうなった)。+Z を**走りの向き**へ合わせること。
        float yaw = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
        const float MOD = 1.039f, SC = 1.65f;      // 高0.9 → 1.49m へ起こす
        int n = Mathf.Max(1, Mathf.RoundToInt(len / (MOD * SC)));
        float kz = len / (n * MOD);                // 走り方向にちょうど len を埋める
        for (int i = 0; i < n; i++)
        {
            var p = r.a + d * (len * i / n);       // ピボットはパネルの端(mesh z 0..1.039)
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src, g.transform);
            Undo.RegisterCreatedObjectUndo(go, "tk"); go.name = "TK_" + i;
            go.transform.position = new Vector3(p.x, r.top, p.y);
            go.transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            go.transform.localScale = new Vector3(1f, SC, kz);
        }
    }

    /// <summary>外周のQA — run ごとに「据えた部材の天端の最大−最小」を出す。
    /// 指図 其六の不変条件「一本の run は一つの天端」を機械で確かめる。
    /// 目視では棟の段々を見落とす(実際に 17.7m 振れていたのを見落としていた)。</summary>
    [MenuItem("Edo/岡部筑前守上屋敷/外周の天端を検査")]
    public static void PerimeterQAMenu() { Debug.Log("[Okabe] " + PerimeterQA()); }
    public static string PerimeterQA()
    {
        // 0.10 は部材の作り由来の差(長屋は棟キャップと本体で 0.06 ずれる)。
        // 据え方の誤りはこれよりずっと大きく出る(直す前は 17.7m)
        const float TOL = 0.10f;
        var yg = GameObject.Find(GN); if (yg == null) return "外周QA: グループが無い";
        var kak = yg.transform.Find("Kakoi"); if (kak == null) return "外周QA: Kakoi が無い";
        var runNames = new List<string>(); foreach (var r in Runs()) runNames.Add(r.name);
        var top = new Dictionary<string, Vector2>();   // run -> (min,max)
        foreach (Transform c in kak)
        {
            // run 名は Runs() と突き合わせる(文字列を切るとサフィックスまで削れる)
            string nm = null;
            foreach (var rn in runNames)
                if (c.name.StartsWith(rn) && (nm == null || rn.Length > nm.Length)) nm = rn;
            if (nm == null) continue;                  // 隅櫓など run でないものは対象外
            var b = B.RB(c.gameObject); if (b.size == Vector3.zero) continue;
            if (!top.ContainsKey(nm)) top[nm] = new Vector2(b.max.y, b.max.y);
            else top[nm] = new Vector2(Mathf.Min(top[nm].x, b.max.y), Mathf.Max(top[nm].y, b.max.y));
        }
        var sb = new System.Text.StringBuilder("外周QA run=" + top.Count);
        int bad = 0; float worst = 0; string worstName = "";
        foreach (var kv in top)
        {
            float d = kv.Value.y - kv.Value.x;
            if (d > worst) { worst = d; worstName = kv.Key; }
            if (d > TOL) { bad++; Debug.LogWarning(string.Format(
                "[Okabe] 外周 {0}: 天端が {1:F2}m 振れている(許容 {2:F2})", kv.Key, d, TOL)); }
        }
        sb.Append(" 振れ超過=" + bad + " 最大=" + worst.ToString("F2") + "m(" + worstName + ")");
        if (bad > 0) sb.Append(" ⚠");
        return sb.ToString();
    }

    /// <summary>足元の検査(指図 其九)。PerimeterQA(天端の振れ)・GateQA・JointQA に次ぐ **4本目の軸**。
    /// 天端QA が通ったまま 19 run 中 17 run が地面から外れていた — 天端だけ見ても足元は分からない。
    ///   ・囲いの部材: 底面 Y − 地形(外+2.5m / 内−2.5m)。許容 0.30m
    ///   ・外周石垣  : 露出高 = 天端 − 法尻位置の地形。壁高の 25% 以上、かつ 1.0m 以上
    /// </summary>
    [MenuItem("Edo/岡部筑前守上屋敷/足元を検査 GroundQA")]
    public static void GroundQAMenu() { Debug.Log("[Okabe] " + GroundQA()); }
    public static string GroundQA()
    {
        const float TOL = 0.30f, PROBE = 2.5f;
        var yg = GameObject.Find(GN); if (yg == null) return "足元QA: グループが無い";
        var kak = yg.transform.Find("Kakoi"); if (kak == null) return "足元QA: Kakoi が無い";
        var runs = Runs();
        var worst = new Dictionary<string, float>(); var wname = new Dictionary<string, string>();
        foreach (Transform c in kak)
        {
            if (!c.gameObject.activeInHierarchy) continue;
            string nm = null;
            foreach (var r in runs)
                if (c.name.StartsWith(r.name) && (nm == null || r.name.Length > nm.Length)) nm = r.name;
            if (nm == null) continue;
            Vector2 outw = Vector2.zero, ra = Vector2.zero; float core = 0f;
            foreach (var r in runs) if (r.name == nm)
            { outw = r.outw; ra = r.a; core = FaceOff(r.kind) - 1.4f * WallScaleFor(r.name); break; }
            var bb = B.RB(c.gameObject); if (bb.size == Vector3.zero) continue;
            var ctr = new Vector2(bb.center.x, bb.center.z);
            // ⚠ **芯線から内へ 2.5m** を測る。部材の中心から内へ 2.5m ではない。
            //   外向きは測らない — 芯線より外は石垣の躯体か素の地形で、部材の底と揃って
            //   いないのが当たり前(揃っていたら石垣が要らない)。外側は下の「露出」が受け持つ。
            //   部材中心から測ると、石垣の天端の下(= 石垣が覆い隠す素地)を拾って誤判定する。
            float sdc = Vector2.Dot(ctr - ra, outw);
            var s0 = ctr + outw * ((core - PROBE) - sdc);
            float dmax = bb.min.y - G(s0.x, s0.y);
            if (!worst.ContainsKey(nm) || Mathf.Abs(dmax) > Mathf.Abs(worst[nm]))
            { worst[nm] = dmax; wname[nm] = c.name; }
        }
        var sb = new System.Text.StringBuilder("足元QA 囲い run=" + worst.Count + " 許容" + TOL.ToString("F2") + "m\n");
        int bad = 0;
        foreach (var r in runs)
        {
            if (!worst.ContainsKey(r.name)) continue;
            float d = worst[r.name]; bool ng = Mathf.Abs(d) > TOL; if (ng) bad++;
            sb.AppendLine(string.Format("  {0,-9} {1,6:F2}m {2} {3} ({4})",
                r.name, d, d > 0 ? "浮き" : "埋没", ng ? "✗" : "✔", wname[r.name]));
        }
        sb.AppendLine("  → 超過 " + bad + " / " + worst.Count);
        // ---- 外周石垣の露出 ----
        var byName = new Dictionary<string, Run>(); foreach (var r in runs) byName[r.name] = r;
        sb.AppendLine("外周石垣の露出(壁高の25%以上 かつ 1.0m 以上)");
        int badw = 0;
        foreach (var q in PerimeterWalls())
        {
            Run r; if (!byName.TryGetValue(q.run, out r)) continue;
            Vector2 d0 = (r.b - r.a); float L = d0.magnitude; d0 /= L;
            Vector2 core = r.a + r.outw * (FaceOff(r.kind) - 1.4f * q.s);
            float lo = float.MaxValue, hi = float.MinValue;
            for (int i = 0; i <= 20; i++)
            {
                var p = core + d0 * (L * i / 20f) + r.outw * (2.4f * q.s);   // 法尻
                float e = r.top - G(p.x, p.y);
                lo = Mathf.Min(lo, e); hi = Mathf.Max(hi, e);
            }
            float need = Mathf.Max(1.0f, 4f * q.s * 0.25f);
            bool ng = lo < need; if (ng) badw++;
            sb.AppendLine(string.Format("  {0,-9} s={1:F2} 壁高{2,4:F1} 露出 {3,5:F2}〜{4,5:F2}m 要{5:F2} {6}",
                q.name, q.s, 4f * q.s, lo, hi, need, ng ? "✗" : "✔"));
        }
        sb.Append("  → 露出不足 " + badw + " / " + PerimeterWalls().Length);
        if (bad > 0 || badw > 0) sb.Append("  ⚠");
        return sb.ToString();
    }

    /// <summary>隅櫓。**隣の run の天端に合わせる**(地面に置かない) — 指図 其六 ④。
    /// 地面に置くと、直した塀と 1〜2m ずれて隅だけ沈む/浮く。</summary>
    static void Yagura(Transform parent, Vector2 p, Vector2 bis, string nm, float baseY)
    {
        var ex = parent.Find(nm); if (ex != null) UnityEngine.Object.DestroyImmediate(ex.gameObject);
        float psi = Mathf.Atan2(bis.x, bis.y) * Mathf.Rad2Deg;
        float y = baseY;
        var go = B.Place(PKnagayaC, new Vector3(p.x, y, p.y), psi, new Vector3(ES * 0.55f, ES, ES), parent, nm);
        var rb = B.RB(go); go.transform.position += new Vector3(p.x - rb.center.x, 0, p.y - rb.center.z);
        // 天端に据えるので土台の底を baseY に合わせる(地面に置くときの +0.85 の沈め込みは要らない)
        rb = B.RB(go); go.transform.position += new Vector3(0, y - rb.min.y, 0);
    }

    // =========================================================================
    // Stage 4b: 石垣(段の土留め) + 天端に載る家臣長屋2列
    //   unity-modular-stonewall §2/§3: ピッチ1.800(0.20重ね) / 1本の壁に position.y と scale.y は1値ずつ /
    //   coping = position.y + 4.0*scale.y / 躯体2.4mは走りの左(local -X)に出る。
    // =========================================================================
    const string P_CW = EdoAssets.JC.CastleWall;

    /// <summary>外周の土留め石垣(指図 其九 ①)。据えは**法肩から逆算する**。
    /// 法肩 = 外周線(run 線から外へ FaceOff(kind)) → 芯線 = 法肩 − 1.4×s → 法尻 = 法肩 + 1.0×s。
    /// 勾配は外向きなので、**outw が走りの左に来るよう** a→b の向きを取る(躯体は左に出る)。</summary>
    static string BuildPerimeterWalls(Transform ig, GameObject pre)
    {
        var sb = new System.Text.StringBuilder();
        var byName = new Dictionary<string, Run>();
        foreach (var r in Runs()) byName[r.name] = r;
        foreach (var q in PerimeterWalls())
        {
            Run r;
            if (!byName.TryGetValue(q.run, out r)) { Debug.LogError("[Okabe] run が無い: " + q.run); continue; }
            Vector2 a = r.a, b = r.b;
            Vector2 d = b - a; float L = d.magnitude; d /= L;
            // 走りの左 = (-d.y, d.x)。躯体はここに出る。outw と逆なら a↔b を入れ替える
            if (Vector2.Dot(new Vector2(-d.y, d.x), r.outw) < 0f) { var t0 = a; a = b; b = t0; d = -d; }
            float yaw = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
            Vector2 core = a + r.outw * (FaceOff(r.kind) - 1.4f * q.s);   // 芯線 = 法肩 − 1.4×s
            float posY = r.top - 4f * q.s;
            int idx = 0;
            int made = PlaceCW(ig, pre, q.name, core, d, 0f, L, posY, q.s, yaw, ref idx);
            sb.AppendLine(string.Format("{0}({1}) pieces={2} s={3:F2} posY={4:F2} coping={5:F2} 壁高={6:F2} 天端={7:F2} 底={8:F2}",
                q.name, q.run, made, q.s, posY, r.top, 4f * q.s, 1.4f * q.s, 2.4f * q.s));
        }
        return sb.ToString();
    }

    /// <summary>石垣の駒を走り座標 <b>[t0, t1] にぴったり</b>敷き詰める(指図 其十 ②)。
    ///
    /// 駒のローカル箱は走り方向に <b>[pos − 2.0×s, pos]</b> — ピボットが走りの手前端にある
    /// (実測 2026-08-16: <c>IG_W1_37</c> は pos z=1047.20 で箱 Z[1044.20, 1047.20])。
    /// したがって pos = t0 + 2.0×s から並べれば最初の駒の端面が t0 に乗り、
    /// 最後に pos = t1 の駒を足せば端面が t1 に乗る。**開口の縁はこれで狙える**。
    /// スキップ方式では縁がピッチの格子にしか来られない。</summary>
    static int PlaceCW(Transform ig, GameObject pre, string nm, Vector2 a, Vector2 d,
                       float t0, float t1, float posY, float s, float yaw, ref int idx)
    {
        float pit = 1.8f * s, len0 = 2f * s;
        if (t1 - t0 < len0 - 0.01f) return 0;          // 駒1個も入らない
        var ts = new List<float>();
        for (float t = t0 + len0; t <= t1 - 0.25f * pit; t += pit) ts.Add(t);
        ts.Add(t1);                                     // 端面を t1 に合わせる仕舞いの駒
        foreach (var t in ts)
        {
            var p = a + d * t;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pre, ig);
            Undo.RegisterCreatedObjectUndo(go, "cw"); go.name = nm + "_" + (idx++);
            go.transform.position = new Vector3(p.x, posY, p.y);
            go.transform.rotation = Quaternion.Euler(0, yaw, 0);
            go.transform.localScale = new Vector3(s, s, s);   // 相似。(1,sy,1) にしない
        }
        return ts.Count;
    }

    public static string Stage4b_Ishigaki()
    {
        var ig = Grp("Ishigaki"); Clear(ig);
        var kn = Grp("KachuNagaya"); Clear(kn);
        var sb = new System.Text.StringBuilder();
        var pre = AssetDatabase.LoadAssetAtPath<GameObject>(P_CW);
        foreach (var w in Walls())
        {
            Vector2 d = (w.b - w.a); float L = d.magnitude; d /= L;
            float yaw = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
            float posY = w.coping - 4f * w.sy;
            float gapT = Vector2.Dot(new Vector2(w.a.x, w.gapZ) - w.a, d);   // 階段開口の走り座標
            // ⚠ **開口はスキップで開けない**(指図 其十 ②)。駒のローカル箱は走り方向に
            //   [pos − 2.0×s, pos] で、ピボットが走りの手前端にある。旧版は pos を駒の中心と
            //   みなして |t − gapT| < 半幅 の駒を飛ばしていたので、開口が 1.0×s ずれ、
            //   縁がピッチ 1.8×s に量子化されていた(実測: W1 は幅 5.10・芯が 1.35m ずれ、
            //   石段の上9段が駒に 1.39m 食い込んでいた)。
            //   **開口の縁を起点に、外へ向かって並べる**。端の駒の端面が縁にぴったり乗る。
            int idx = 0, made = 0;
            float tA = gapT - w.gapHalf, tB = gapT + w.gapHalf;
            if (tA <= 0f && tB >= L)              // 開口がこの run を丸ごと食う
                { }
            else if (tA <= 0f || tB >= L)         // 開口が端にかかる = 片側だけ
                made += PlaceCW(ig, pre, w.name, w.a, d, Mathf.Max(0f, tB), Mathf.Min(L, tA <= 0f ? L : tA),
                                posY, w.sy, yaw, ref idx);
            else
            {
                made += PlaceCW(ig, pre, w.name, w.a, d, 0f, tA, posY, w.sy, yaw, ref idx);
                made += PlaceCW(ig, pre, w.name, w.a, d, tB, L,  posY, w.sy, yaw, ref idx);
            }
            sb.AppendLine(string.Format("{0} pieces={1} s={2:F2} posY={3:F2} coping={4:F2} 開口 z {5:F2}〜{6:F2}(幅{7:F2})",
                w.name, made, w.sy, posY, w.coping, w.gapZ - w.gapHalf, w.gapZ + w.gapHalf, w.gapHalf * 2f));
        }
        sb.Append(BuildPerimeterWalls(ig, pre));
        // 北辺の段の継ぎ目を受ける返しの石垣(指図 其十一)
        foreach (var q in NorthReturns())
        {
            Vector2 ra, rb; NorthReturnLine(q.joint, out ra, out rb);
            Vector2 rd = (rb - ra); float rL = rd.magnitude; rd /= rL;
            // 躯体は走りの左に出る。低い段の側へ倒したいので、必要なら反転する
            var left = new Vector2(-rd.y, rd.x);
            var rs = new List<Run>(); foreach (var r in Runs()) if (r.name.StartsWith("Hei_N")) rs.Add(r);
            var lowOut = (rs[q.joint].top < rs[q.joint + 1].top ? rs[q.joint] : rs[q.joint + 1]);
            var toLow = (lowOut.a + lowOut.b) * 0.5f - ra;
            if (Vector2.Dot(left, toLow) < 0f) { var t0 = ra; ra = rb; rb = t0; rd = -rd; }
            int ri = 0;
            int rn = PlaceCW(ig, pre, q.name, ra, rd, 0f, rL, q.coping - 4f * q.s, q.s,
                             Mathf.Atan2(rd.x, rd.y) * Mathf.Rad2Deg, ref ri);
            sb.AppendLine(string.Format("{0} pieces={1} s={2:F2} coping={3:F1} 壁高={4:F1} 長さ={5:F1}",
                q.name, rn, q.s, q.coping, 4f * q.s, rL));
        }
        // 石段の法面の両脇(v7) — 天端が斜めに通る一枚物。左右に1本ずつ
        int nn = 0;
        foreach (var q in NoriWalls())
        {
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(q.asset);
            if (src == null) { Debug.LogError("[Okabe] 坂の土留めが無い: " + q.asset
                + " — blender --background --python Tools/Blender/build_ishigaki_saka.py で生成する"); continue; }
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src, ig);
            Undo.RegisterCreatedObjectUndo(go, "saka"); go.name = "IG_" + q.name;
            go.transform.position = q.pos;
            go.transform.rotation = Quaternion.Euler(0, q.yaw, 0);
            nn++;
        }
        sb.AppendLine("坂の土留め pieces=" + nn);

        // 家臣長屋2列 — 西の石垣A/Bの天端に載せる(下書きの赤線2本)
        // perimeter.md: なまこ壁の外面を天端の外面と面一(0.00〜0.20m)、土台底 = 天端 − 1.59m
        bool nm0 = NT.NaturalMode; NT.NaturalMode = false;
        foreach (var w in Walls())
        {
            if (!w.name.StartsWith("IG_W")) continue;
            Vector2 outw = new Vector2(-1f, 0f);                    // 西向き
            // 石垣は境界まで延ばしたが、長屋は其六 の長さ(na/nb)のまま据える
            var mods = NT.NagayaRun(kn, w.na + new Vector2(2.2f, 0), w.nb + new Vector2(2.2f, 0), outw,
                w.coping - 1.49f, new Vector2(w.a.x, w.gapZ), 4.5f, "KN_" + w.name);
            // なまこ外面を天端外面(= 壁の芯線 x = w.a.x)へ面一に寄せる
            if (mods.Count > 0)
            {
                float sum = 0; int c = 0;
                foreach (var m in mods)
                {
                    float mx = float.MinValue;
                    foreach (var mf in m.GetComponentsInChildren<MeshFilter>())
                    {
                        if (!mf.gameObject.name.ToLower().Contains("namako")) continue;
                        foreach (var v in mf.sharedMesh.vertices)
                        { var wp = mf.transform.TransformPoint(v); mx = Mathf.Max(mx, wp.x * outw.x + wp.z * outw.y); }
                    }
                    if (mx > float.MinValue) { sum += mx; c++; }
                }
                if (c > 0)
                {
                    // 法肩 = 芯線 + 1.4×s（露出側 = outw 方向）。相似スケールにしたので芯線ではなく法肩に面一
                    float crestOuter = w.a.x * outw.x + 1.4f * w.sy;
                    float shift = 0.02f - (crestOuter - sum / c);
                    foreach (var m in mods) m.transform.position += new Vector3(-outw.x * shift, 0, -outw.y * shift);
                    sb.AppendLine("KN_" + w.name + " modules=" + mods.Count + " flushShift=" + shift.ToString("F3"));
                }
            }
        }
        NT.NaturalMode = nm0;
        return sb.ToString();
    }

    // =========================================================================
    // Stage 5: 連続御殿複合 — 御殿部材キットで棟を組む(EdoGotenKit)
    //
    // 【v4 で作り直した理由】v3 は Village Kit の一軒家プレハブを身舎の矩形に敷き詰めていた。
    //   プレハブは壁で閉じた箱なので、入側(廊下)から見ると障子でなく壁が見える(ユーザー裁定
    //   2026-08-14)。Blender で起こした部材から棟を組み直す。
    //
    // 【屋根 = (a) の取り合い】谷や隅は作らない。各棟は独立した入母屋で、接続は低い切妻の渡廊下。
    //   大棟は桁行に架かるので、外形の長辺が棟のローカルX(桁行)に来るよう yaw で寝かせる。
    //   屋根FBXは寸法ごとに1本生成してある(Goten_Roof_Irimoya_<桁行>x<梁間>ken)。
    // =========================================================================
    const float GOTEN_FLOOR = 0.62f;    // 床高(地面から)

    public static string Stage5_Goten()
    {
        var sb = new System.Text.StringBuilder();
        var bg = Grp("Buildings"); Clear(bg);
        float area = 0, moya = 0;
        foreach (var m in Muneya())
        {
            var mune = BuildMune(bg, m);
            if (m.name == "Genkan") Kurumayose(mune.transform, m);
            area += (m.x1 - m.x0) * (m.z1 - m.z0);
            moya += m.MoyaW * m.MoyaD * KEN * KEN;
            sb.AppendLine(string.Format("  {0,-13} 身舎 {1,2}x{2,-2}間 + 入側 / 屋根 {3}x{4}間",
                m.name, m.MoyaW, m.MoyaD, Mathf.Max(m.kw, m.kd), Mathf.Min(m.kw, m.kd)));
        }
        sb.AppendLine(string.Format("goten 棟={0} 外形={1:F0}m2(身舎 {2:F0}m2 = {3:F0}畳)",
            Muneya().Length, area, moya, moya / (0.909f * KEN)));
        return sb.ToString();
    }

    // =========================================================================
    // 車寄せ(式台) — 表門からの参道が着く唯一の「屋根の架かる」場所。
    //
    // v5 で前庭の屋根付き参道を撤去した(武家屋敷の前庭は開けた白洲)。書院造で屋根が
    // 架かるのは玄関側の**式台・車寄せ**までなので、それをここで作る。
    //
    // 【形】3間×1間の向拝。大棟は壁と平行(南北)に通し、渡廊下と同じ低い切妻を使う —
    //   妻入り(棟が東西)にすると屋根が玄関棟の軒を越えて谷が要る。谷は作らない
    //   (ユーザー裁定 2026-08-14「雁行の取り合いは (a) 渡廊下の低い切妻で処理する」)。
    //   大棟の天端 = 床+2.503 で、玄関棟の軒先(床+2.577)の下をくぐる。
    // 【床】式台は玄関の床から一段(0.30)下がる。地面からは 0.32 で、沓脱の段板を前に置く。
    // 【濡縁】入口の3間は濡縁(高欄つき)を外す — 残すと高欄が式台を塞ぐ。
    // =========================================================================
    const float SHIKIDAI_DROP = 0.30f;      // 玄関の床からの下がり
    const int KURUMA_BAY = 4, KURUMA_KEN = 3;  // 玄関棟のローカル間(南から)/ 間口

    static void Kurumayose(Transform mune, Blk m)
    {
        float lv = m.y, fl = GOTEN_FLOOR - SHIKIDAI_DROP;
        float xw = m.x1;                                    // 玄関棟の東面
        float z0 = m.z0 + KURUMA_BAY * KEN;
        float colH = EdoGotenKit.ROKA_EAVE + EdoGotenKit.ROKA_KETA;
        var g = new GameObject("Kurumayose"); g.transform.SetParent(mune, true);
        g.transform.position = Vector3.zero; g.transform.rotation = Quaternion.identity;
        Undo.RegisterCreatedObjectUndo(g, "kurumayose");

        // 入口の3間の濡縁を外す(高欄が式台を塞ぐ)
        int cut = 0;
        var kill = new List<GameObject>();
        foreach (Transform c in mune)
        {
            if (!c.name.Contains("Nureen")) continue;
            var p = c.position;
            if (Mathf.Abs(p.x - xw) > 0.10f) continue;
            if (p.z < z0 - 0.05f || p.z > z0 + KURUMA_KEN * KEN + 0.05f) continue;
            kill.Add(c.gameObject);
        }
        foreach (var o in kill) { Undo.DestroyObjectImmediate(o); cut++; }
        if (cut != KURUMA_KEN)
            Debug.LogWarning("[Okabe] 車寄せ: 外した濡縁が" + cut + "枚(期待 " + KURUMA_KEN + ")");

        for (int j = 0; j < KURUMA_KEN; j++)
        {
            float zc = z0 + (j + 0.5f) * KEN;
            Put(g.transform, EdoAssets.Goten.FloorBoard, new Vector3(xw + KEN * 0.5f, lv + fl, zc), 0f, 1f);
            Put(g.transform, EdoAssets.Goten.Beam,
                new Vector3(xw + KEN, lv + fl + colH - EdoAssets.Goten.BeamH, zc), 0f, 1f);
        }
        for (int j = 0; j <= KURUMA_KEN; j++)
            Put(g.transform, EdoAssets.Goten.Column, new Vector3(xw + KEN, lv + fl, z0 + j * KEN),
                0f, colH / EdoAssets.Goten.DoorH);
        // 大棟を南北へ。ピボット=向拝の中心・軒先レベル
        Put(g.transform, EdoAssets.Goten.RoofKirizuma(KURUMA_KEN),
            new Vector3(xw + KEN * 0.5f, lv + fl + EdoGotenKit.ROKA_EAVE, z0 + KURUMA_KEN * KEN * 0.5f), 90f, 1f);
        // 沓脱 — 式台の前に段板2枚
        var pre = AssetDatabase.LoadAssetAtPath<GameObject>(PStep);
        for (int j = 0; j < 2; j++)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pre, g.transform);
            Undo.RegisterCreatedObjectUndo(go, "kutsunugi"); go.name = "Kutsunugi_" + j;
            go.transform.rotation = Quaternion.Euler(0, 90f, 0);
            var rb = B.RB(go);
            float pz = z0 + KURUMA_KEN * KEN * 0.5f + (j == 0 ? -1.0f : 1.0f);
            go.transform.position += new Vector3((xw + KEN + 0.45f) - rb.center.x,
                                                 (lv + 0.16f) - rb.max.y, pz - rb.center.z);
        }
    }

    static void Put(Transform parent, string path, Vector3 pos, float ry, float sy)
    {
        var src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (src == null) { Debug.LogError("[Okabe] 見つからない: " + path); return; }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
        Undo.RegisterCreatedObjectUndo(go, "part");
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(0f, ry, 0f);
        if (!Mathf.Approximately(sy, 1f)) go.transform.localScale = new Vector3(1f, sy, 1f);
    }

    /// <summary>棟を1つ建てる。外形の長辺が桁行(ローカルX)に来るよう寝かせ、寸法の合う屋根を載せる。</summary>
    static GameObject BuildMune(Transform parent, Blk m)
    {
        int kLong = Mathf.Max(m.kw, m.kd), kShort = Mathf.Min(m.kw, m.kd);
        string roof = EdoAssets.Goten.RoofIrimoya_(kLong, kShort);
        GameObject g;
        if (m.kw >= m.kd)
            // 桁行が世界X。原点は南西角
            g = EdoGotenKit.Mune(m.name, parent, new Vector3(m.x0, m.y, m.z0), 0f,
                                 m.MoyaW, m.MoyaD, 1, GOTEN_FLOOR, roof, iriX: 1);
        else
            // 桁行が世界Z。yaw=270 でローカルX→世界+Z / ローカルZ→世界-X。原点は南東角
            g = EdoGotenKit.Mune(m.name, parent, new Vector3(m.x1, m.y, m.z0), 270f,
                                 m.MoyaD, m.MoyaW, 1, GOTEN_FLOOR, roof, iriX: 1);
        Undo.RegisterCreatedObjectUndo(g, "mune");
        return g;
    }

    // =========================================================================
    // Stage 6: 廊下 — 渡廊下・外廊下・参道・折返し石段
    //   ⚠ **入側はここでは作らない**。四方の入側は Mune() が棟の一部として組む(v4)。
    //     ここで帯を重ねて敷くと床と柱が二重になって z-fighting する。
    //   渡廊下は EdoGotenKit.Roka。両端は棟に突き付けるので端の柱通りは落とす
    //   (棟の柱と同じ位置に立つため)。
    //   ⚠ v5: 表門からの参道(L_Sando*)は撤去した。武家屋敷の前庭に屋根付きの通路は
    //     架けない — 考証は PathLinks の跡の注記を見よ。石段も廊下ではなくなり、
    //     別グループ Ishidan で法面の上に据える。
    // =========================================================================
    public static string Stage6_Roka()
    {
        var rk = Grp("Roka"); Clear(rk);
        int nr = 0;
        foreach (var l in GotenLinks()) { BuildRoka(rk, l); nr++; }
        // 石段は v5 から**廊下ではない**(郭をまたぐ屋外の通路)。別グループに出す
        var id = Grp("Ishidan"); Clear(id);
        int nk = 0;
        int nb = 0;
        foreach (var k in Kaidans()) { Kaidan(id, k); nk++; if (!string.IsNullOrEmpty(k.noboriro)) { Noboriro(id, k); nb++; } }
        return "roka 渡廊下=" + nr + " 石段=" + nk + " 登廊=" + nb + " / " + RokaConnectivity();
    }

    /// <summary>指図の不変条件「廊下は**郭ごとに**一続き」を機械で確かめる。
    /// 通れる面 = 棟の入側の環(外形から身舎を抜く)+ その外を巡る濡縁 + 渡廊下・外廊下。
    /// ラスタに落として4近傍で連結成分を数え、**郭(=段のレベル)ごとに1個**であることを見る。
    ///
    /// ⚠ v5 で不変条件を弱めた。石段は**廊下ではなく屋外の通路**へ改めたので、郭と郭は
    ///   廊下では繋がらない(指図 v5「郭をまたぐのは屋外の石段」)。v4 までは石段を帯に
    ///   加えて全体で1個を要求していたが、折返し石段では下端が上端と同じ側へ戻るため
    ///   矩形が重なっても実際には歩けず、検査が嘘をついていた。</summary>
    [MenuItem("Edo/岡部筑前守上屋敷/廊下の連結を検査")]
    public static void CheckRokaMenu() { Debug.Log("[Okabe] " + RokaConnectivity()); }
    public static string RokaConnectivity()
    {
        var sb = new System.Text.StringBuilder();
        int bad = 0;
        foreach (var lv in new[] { 25.5f, 19.5f, 11.5f })
        {
            int nc; float area;
            var big = KuruwaComponents(lv, out nc, out area);
            sb.Append(string.Format("{0}郭 {1:F0}m2 成分={2}{3} / ",
                lv.ToString("F1"), area, nc, nc == 1 ? "" : " ⚠" + big));
            if (nc != 1) bad++;
        }
        if (bad > 0) Debug.LogWarning("[Okabe] " + bad + "つの郭で廊下が割れている: " + sb);
        return sb.ToString().TrimEnd(' ', '/');
    }
    static string KuruwaComponents(float level, out int ncomp, out float area)
    {
        const float cell = 0.45f;
        var band = new List<Rect>(); var hole = new List<Rect>();
        foreach (var m in Muneya())
        {
            if (!Mathf.Approximately(m.y, level)) continue;
            // 濡縁(0.89m)は Mune() が四方に回すので、踏める面は外形より一回り大きい
            band.Add(Rect.MinMaxRect(m.x0 - NUREEN, m.z0 - NUREEN, m.x1 + NUREEN, m.z1 + NUREEN));
            hole.Add(Rect.MinMaxRect(m.x0 + KEN, m.z0 + KEN, m.x1 - KEN, m.z1 - KEN));
        }
        foreach (var l in GotenLinks())
            if (Mathf.Approximately(l.y, level)) band.Add(Rect.MinMaxRect(l.x0, l.z0, l.x1, l.z1));
        const float minx = -660f, minz = 940f;
        int nx = 645, nz = 267;      // 290m x 120m / 0.45
        var ok = new bool[nx, nz]; int total = 0;
        for (int i = 0; i < nx; i++)
            for (int j = 0; j < nz; j++)
            {
                var p = new Vector2(minx + (i + 0.5f) * cell, minz + (j + 0.5f) * cell);
                bool inB = false; foreach (var r in band) if (r.Contains(p)) { inB = true; break; }
                if (!inB) continue;
                bool inH = false; foreach (var r in hole) if (r.Contains(p)) { inH = true; break; }
                if (inH) continue;
                ok[i, j] = true; total++;
            }
        var seen = new bool[nx, nz]; var comps = new List<int>();
        var st = new Stack<Vector2Int>();
        for (int i = 0; i < nx; i++)
            for (int j = 0; j < nz; j++)
            {
                if (!ok[i, j] || seen[i, j]) continue;
                int n = 0; st.Push(new Vector2Int(i, j)); seen[i, j] = true;
                while (st.Count > 0)
                {
                    var c = st.Pop(); n++;
                    for (int d = 0; d < 4; d++)
                    {
                        int a = c.x + (d == 0 ? 1 : d == 1 ? -1 : 0), b = c.y + (d == 2 ? 1 : d == 3 ? -1 : 0);
                        if (a < 0 || b < 0 || a >= nx || b >= nz || !ok[a, b] || seen[a, b]) continue;
                        seen[a, b] = true; st.Push(new Vector2Int(a, b));
                    }
                }
                comps.Add(n);
            }
        comps.Sort(); comps.Reverse();
        ncomp = comps.Count; area = total * cell * cell;
        var s2 = new System.Text.StringBuilder();
        for (int i = 0; i < comps.Count; i++) s2.Append(i == 0 ? "[" : " / ").Append((comps[i] * cell * cell).ToString("F0"));
        return s2.Append("]").ToString();
    }

    /// <summary>渡廊下を1本。長辺が桁行(ローカルX)、短辺(1間)が幅。</summary>
    static void BuildRoka(Transform parent, Blk l)
    {
        bool alongX = l.kw >= l.kd;
        int n = alongX ? l.kw : l.kd;
        if ((alongX ? l.kd : l.kw) != 1)
            Debug.LogWarning("[Okabe] " + l.name + ": 渡廊下の幅が1間でない");
        if (n < 2)
            Debug.LogWarning("[Okabe] " + l.name + ": 1間の渡廊下は成立しない(屋根が両端1.20ずつ重なる)");
        // yaw270(南北の廊下)では local z=0 が世界の x1 側(東)、z=K が x0 側(西)
        bool kS = !(l.koranOff == 1), kN = !(l.koranOff == 2);
        var g = alongX
            ? EdoGotenKit.Roka(l.name, parent, new Vector3(l.x0, l.y, l.z0), 0f, n,
                               GOTEN_FLOOR, koranS: kS, koranN: kN, colStart: false, colEnd: false)
            : EdoGotenKit.Roka(l.name, parent, new Vector3(l.x1, l.y, l.z0), 270f, n,
                               GOTEN_FLOOR, koranS: kS, koranN: kN, colStart: false, colEnd: false);
        Tsuka(g.transform, l.x0, l.z0, alongX, n, l.y);
        Undo.RegisterCreatedObjectUndo(g, "roka");
    }

    /// <summary>床束 — 高床の下を地面まで受ける 短い柱。
    /// ⚠ EdoGotenKit の柱は**床レベルから上**にしか立たない。棟は濡縁が縁を隠すので目立たないが、
    ///   渡廊下は縁が無いので、床が 0.62 の高さで**宙に浮いて見える**(ユーザー指摘 2026-08-15、
    ///   西低地の廊下)。上の柱と同じ通りに、地面から床までの束を入れる。</summary>
    static void Tsuka(Transform parent, float x0, float z0, bool alongX, int n, float lv)
    {
        float sy = GOTEN_FLOOR / EdoAssets.Goten.DoorH;
        for (int i = 0; i <= n; i++)
            for (int j = 0; j < 2; j++)
            {
                float cx = alongX ? x0 + i * KEN : x0 + j * KEN;
                float cz = alongX ? z0 + j * KEN : z0 + i * KEN;
                Put(parent, EdoAssets.Goten.Column, new Vector3(cx, lv, cz), 0f, sy);
            }
    }

    // 石段を1本。直階段 — 蹴上0.30/踏面0.45 の段板を法面の上に据える。
    // 段板(1.98m)は幅4mに2枚並べる。踏面の天端が設計レベル、法面はその 0.15 下を通る。
    static void Kaidan(Transform parent, Kai k)
    {
        var g = new GameObject(k.name); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "ishidan");
        var pre = AssetDatabase.LoadAssetAtPath<GameObject>(PStep);
        int n = Mathf.Max(2, Mathf.RoundToInt(k.Drop / KERI));
        float dir = Mathf.Sign(k.xBot - k.xTop);
        float tread = k.Run / n;
        float zc = k.NoriZ, halfW = (k.z1 - k.z0) * 0.25f;   // 段板2枚の中心
        // 西(登廊のある段)は段板1枚 1.98m。東の参道は2枚並べて 3.96m。
        // ⚠ どちらも**法面の芯そのもの**に置く(指図 其十 ②で ISHIDAN_Z を撤廃)
        bool solo = !string.IsNullOrEmpty(k.noboriro);
        for (int i = 1; i <= n; i++)
        {
            float lvl = k.yTop - k.Drop * i / n;
            float px = k.xTop + dir * (i - 0.5f) * tread;
            for (int sdup = 0; sdup < (solo ? 1 : 2); sdup++)
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(pre, g.transform);
                Undo.RegisterCreatedObjectUndo(go, "st"); go.name = "S_" + i + "_" + sdup;
                go.transform.rotation = Quaternion.Euler(0, 90f, 0);   // 長手(1.98)を Z へ
                var rb = B.RB(go);
                float pz = solo ? zc : zc + (sdup == 0 ? -halfW : halfW);
                go.transform.position += new Vector3(px - rb.center.x, lvl - rb.max.y, pz - rb.center.z);
            }
        }
    }

    // =========================================================================
    // Stage 7: 服務棟(蔵・厩・稲荷・井戸)
    // =========================================================================
    public static string Stage7_Service()
    {
        var sv = Grp("Service"); Clear(sv);
        float yaw = YawGate();
        // 土蔵群 = 西低地(勝手向きの下段) [福井図: 土蔵は御殿から離した下側の空地]
        for (int i = 0; i < 4; i++)
        {
            var kr = B.Place(B.PKura, Vector3.zero, 90f, Vector3.one * ES, sv, "Kura_W" + (i + 1));
            var rb = B.RB(kr);
            float cx = -614f + (i % 2) * 9f, cz = 960f + (i / 2) * 9f;   // 下御殿棟に刺さらない位置(bm1 19-22)
            kr.transform.position += new Vector3(cx - rb.center.x, 0, cz - rb.center.z);
            rb = B.RB(kr); kr.transform.position += new Vector3(0, (G(cx, cz) - 0.15f) - rb.min.y, 0);
        }
        B.Well(sv, -609f, 955f);   // 土蔵群の南。v3 の -632,1010 は下御殿棟の中だった(v4 で棟が実体になった)
        foreach (Transform c in sv) if (c.name == "Ido") { c.name = "Ido_Kura"; break; }
        // 表門前(13.5m段) = 厩 + 供待 [西川1959: 厩は表門まわりの帯]
        Umaya(sv, new Vector2(-393f, 1026f), 90f, "Umaya");
        var tm = B.Place(B.PSmallHouse, Vector3.zero, yaw, Vector3.one, sv, "Tomomachi");
        { var rb = B.RB(tm); tm.transform.position += new Vector3(-393f - rb.center.x, 0, 976f - rb.center.z);
          rb = B.RB(tm); tm.transform.position += new Vector3(0, (G(-393f, 976f) - 0.12f) - rb.min.y, 0); }
        // 邸内稲荷 = 鬼門(北東)。主郭の北東寄り
        Inari(sv, new Vector2(-461f, 1050f));
        B.Well(sv, -539.5f, 1015f);   // 台所棟と奥向棟の間の空地。v3 の -523,985 は中奥棟の中だった
        foreach (Transform c in sv) if (c.name == "Ido") { c.name = "Ido_Katte"; break; }
        return "service ok";
    }
    static void Umaya(Transform parent, Vector2 c, float psi, string nm)
    {
        const float PITCH = 7.81f;
        var g = new GameObject(nm); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "umaya");
        float rad = psi * Mathf.Deg2Rad;
        Vector2 negRight = new Vector2(-Mathf.Cos(rad), Mathf.Sin(rad));
        var m1 = B.Place(B.PKnagayaL, Vector3.zero, psi, Vector3.one * ES, g.transform, "u0");
        var m2 = B.Place(B.PKnagayaR, Vector3.zero, psi, Vector3.one * ES, g.transform, "u1");
        Vector2 p1 = c - negRight * (PITCH * 0.5f), p2 = c + negRight * (PITCH * 0.5f);
        float y = Mathf.Min(G(p1.x, p1.y), G(p2.x, p2.y));
        m1.transform.position = new Vector3(p1.x, y, p1.y); m2.transform.position = new Vector3(p2.x, y, p2.y);
        var b1 = B.RB(m1); m1.transform.position += new Vector3(0, (y - 0.10f) - b1.min.y, 0);
        var b2 = B.RB(m2); m2.transform.position += new Vector3(0, (y - 0.10f) - b2.min.y, 0);
    }
    static void Inari(Transform parent, Vector2 pos)
    {
        float y = G(pos.x, pos.y);
        var g = new GameObject("Inari"); g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(pos.x, y, pos.y);
        Undo.RegisterCreatedObjectUndo(g, "inari");
        Func<Color, Material> M = c => { var m = new Material(Shader.Find("Universal Render Pipeline/Lit")); m.color = c; return m; };
        var shu = M(new Color(0.78f, 0.15f, 0.08f)); var stone = M(new Color(0.55f, 0.55f, 0.52f)); var wood = M(new Color(0.42f, 0.30f, 0.18f));
        for (int i = 0; i < 2; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "t_post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.18f, 1.25f, 0.18f);
            post.transform.localPosition = new Vector3(i == 0 ? -0.9f : 0.9f, 1.25f, -2.2f);
            post.GetComponent<Renderer>().sharedMaterial = shu;
        }
        var ka = GameObject.CreatePrimitive(PrimitiveType.Cube); ka.name = "t_kasagi"; ka.transform.SetParent(g.transform, false);
        ka.transform.localScale = new Vector3(2.6f, 0.16f, 0.2f); ka.transform.localPosition = new Vector3(0, 2.5f, -2.2f);
        ka.GetComponent<Renderer>().sharedMaterial = shu;
        var nu = GameObject.CreatePrimitive(PrimitiveType.Cube); nu.name = "t_nuki"; nu.transform.SetParent(g.transform, false);
        nu.transform.localScale = new Vector3(2.2f, 0.12f, 0.14f); nu.transform.localPosition = new Vector3(0, 2.05f, -2.2f);
        nu.GetComponent<Renderer>().sharedMaterial = shu;
        var kd = GameObject.CreatePrimitive(PrimitiveType.Cube); kd.name = "kidan"; kd.transform.SetParent(g.transform, false);
        kd.transform.localScale = new Vector3(1.5f, 0.4f, 1.2f); kd.transform.localPosition = new Vector3(0, 0.2f, 0);
        kd.GetComponent<Renderer>().sharedMaterial = stone;
        var ho = GameObject.CreatePrimitive(PrimitiveType.Cube); ho.name = "hokora"; ho.transform.SetParent(g.transform, false);
        ho.transform.localScale = new Vector3(0.9f, 0.9f, 0.8f); ho.transform.localPosition = new Vector3(0, 0.85f, 0);
        ho.GetComponent<Renderer>().sharedMaterial = wood;
        for (int i = 0; i < 2; i++)
        {
            var rf = GameObject.CreatePrimitive(PrimitiveType.Cube);
            rf.name = "roof" + i; rf.transform.SetParent(g.transform, false);
            rf.transform.localScale = new Vector3(1.3f, 0.06f, 0.65f);
            rf.transform.localPosition = new Vector3(0, 1.45f, i == 0 ? -0.28f : 0.28f);
            rf.transform.localEulerAngles = new Vector3(i == 0 ? -25f : 25f, 0, 0);
            rf.GetComponent<Renderer>().sharedMaterial = wood;
        }
    }

    // =========================================================================
    // Stage 8: 庭園(下書きの桃色帯) + 中庭の植栽
    // =========================================================================
    public static string Stage8_Garden()
    {
        var gg = Grp("Garden"); Clear(gg);
        var rnd = new System.Random(53115);
        var obst = new List<Bounds>();
        foreach (var gn in new[] { "Buildings", "Service", "Kakoi", "Omotemon", "Roka", "Ishidan" })
        { var g = GameObject.Find(GN).transform.Find(gn); if (g == null) continue;
          foreach (Transform c in g) { if (!c.gameObject.activeSelf) continue; var b = B.RB(c.gameObject); b.Expand(new Vector3(3f, 200f, 3f)); obst.Add(b); } }
        var mus = Muneya();
        int n = 0;
        for (int i = 0, guard = 0; i < 150 && guard < 12000; guard++)
        {
            float px = Mathf.Lerp(-694f, -374f, (float)rnd.NextDouble());
            float pz = Mathf.Lerp(938f, 1094f, (float)rnd.NextDouble());
            var p = new Vector2(px, pz);
            if (!B.PIP(SK.OKABE, p) || B.DistToPolyEdge(SK.OKABE, p) < 5f) continue;
            if (InSando(px, pz, 2f)) continue;                 // 参道は開けておく(v5)
            float dummy; if (NoriHeight(px, pz, out dummy) > 0f) continue;   // 石段の法面には植えない
            bool inMune = false;
            foreach (var mu in mus) if (px > mu.x0 - 4f && px < mu.x1 + 4f && pz > mu.z0 - 4f && pz < mu.z1 + 4f) inMune = true;
            if (inMune) continue;
            bool hit = false;
            foreach (var ob in obst) if (px > ob.min.x && px < ob.max.x && pz > ob.min.z && pz < ob.max.z) { hit = true; break; }
            if (hit) continue;
            float y = G(px, pz);
            GameObject go;
            if (y < 14f) go = B.Place(Bamboo[rnd.Next(2)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.5f * (0.9f + 0.4f * (float)rnd.NextDouble())), gg, "Take_" + i);
            else if (rnd.NextDouble() < 0.66) go = B.Place(Pines[rnd.Next(Pines.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (1.65f * (0.9f + 0.5f * (float)rnd.NextDouble())), gg, "Pine_" + i);
            else go = B.Place(Shrubs[rnd.Next(Shrubs.Length)], new Vector3(px, y, pz), (float)rnd.NextDouble() * 360f, Vector3.one * (0.9f + 0.7f * (float)rnd.NextDouble()), gg, "Shrub_" + i);
            var rb = B.RB(go); go.transform.position += new Vector3(0, (y - 0.05f) - rb.min.y, 0);
            i++; n++;
        }
        return "plants=" + n;
    }

    // =========================================================================
    // Stage 9: 郭の内側を白洲(砂利)に塗る。芝のままだと村に見える
    // =========================================================================
    public static string Stage9_Splat()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((-660f - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((-370f - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((940f - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((1060f - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        var terr = Terraces(); var gard = Gardens();
        int changed = 0;
        for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++)
        {
            float wx = tp.x + (ix0 + xx + 0.5f) * cell, wz = tp.z + (iz0 + zz + 0.5f) * cell;
            var p = new Vector2(wx, wz);
            if (!B.PIP(SK.OKABE, p)) continue;
            // 段の矩形を 3m 広げる — 外周の囲いの足元まで白洲を塗る(指図 其六 ⑤)。
            // 敷地ポリゴンの内側だけが対象なので、外へはみ出さない
            const float SPLAT_PAD = 3f;
            bool inTerr = false;
            foreach (var tr in terr)
                if (wx > tr.x0 - SPLAT_PAD && wx < tr.x1 + SPLAT_PAD
                 && wz > tr.z0 - SPLAT_PAD && wz < tr.z1 + SPLAT_PAD) inTerr = true;
            if (!inTerr) continue;
            bool inG = false;
            foreach (var g in gard) if (wx > g.x0 - 1f && wx < g.x1 + 1f && wz > g.z0 - 1f && wz < g.z1 + 1f) inG = true;
            // 表門 → 玄関の参道(v5)。屋根付き廊下の代わりに、白洲の中の踏み分け帯として塗る
            float bare, grass, dirt;
            if (InSando(wx, wz, 0f)) { dirt = 0.72f; bare = 0.28f; grass = 0f; }   // 踏み固められた道
            else if (inG) { grass = 0.72f; dirt = 0.20f; bare = 0.08f; }
            else { bare = 0.70f; dirt = 0.24f; grass = 0.06f; }
            float sum = bare + grass + dirt;
            for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
            A[zz, xx, 0] = dirt / sum; A[zz, xx, 1] = grass / sum; A[zz, xx, 2] = bare / sum;
            changed++;
        }
        td.SetAlphamaps(ix0, iz0, A);
        return "splat cells=" + changed;
    }

    // =========================================================================
    [MenuItem("Edo/岡部筑前守上屋敷を再構成 v3")]
    public static void RunAllMenu() { Debug.Log(RunAll()); }
    public static string RunAll()
    {
        NT.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage0_Backup());
        sb.AppendLine(Stage1_Grade());
        sb.AppendLine(BuildStructures());
        return sb.ToString();
    }
    // 地形を触らない部分。全ステージ冪等。
    public static string BuildStructures()
    {
        NT.NaturalMode = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage3_Retire());
        sb.AppendLine(Stage4_Perimeter());
        sb.AppendLine(Stage4b_Ishigaki());
        sb.AppendLine(Stage5_Goten());
        sb.AppendLine(Stage6_Roka());
        sb.AppendLine(Stage7_Service());
        sb.AppendLine(Stage8_Garden());
        sb.AppendLine(Stage9_Splat());
        sb.AppendLine(Stage2_Reseat());
        UnityEditor.SceneManagement.EditorSceneManager.MarkAllScenesDirty();
        return sb.ToString();
    }
}
