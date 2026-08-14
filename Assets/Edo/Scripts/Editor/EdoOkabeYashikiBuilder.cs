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
    // 表門 = 冠木門形式の k_mon(EdoSanbezakaBuilder には無い)
    const string PKmon = EdoAssets.Eg.Kmon;

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
    public struct Wall { public Vector2 a, b; public float coping, sy; public string name; public float gapZ; }
    public static Wall[] Walls()
    {
        return new[] {
            // 東: 主郭25.5 → 東中段19.5 → 表門前13.5。南→北へ走る(左=西=高い側)。開口は参道 z=1001
            new Wall{ name="IG_E1", a=new Vector2(-455f, 947f), b=new Vector2(-455f, 1056f), coping=25.5f, sy=1.5f, gapZ=1001f },
            new Wall{ name="IG_E2", a=new Vector2(-425f, 947f), b=new Vector2(-425f, 1056f), coping=19.5f, sy=1.5f, gapZ=1001f },
            // 西: 主郭25.5 → 中段19.5 → 西低地11.5。北→南へ走る(左=東=高い側)。開口は北縁 z=1036
            new Wall{ name="IG_W1", a=new Vector2(-566f, 1052f), b=new Vector2(-566f, 949f), coping=25.5f, sy=1.5f, gapZ=1036f },
            new Wall{ name="IG_W2", a=new Vector2(-592f, 1052f), b=new Vector2(-592f, 949f), coping=19.5f, sy=2.0f, gapZ=1036f },
        };
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
            SG(57,38, 58,47, 25.5f, "L_ShimoKuruwa"),      // 9間 西縁の外廊下 → 石段W1へ
            WG( 4,13,  5,15, 11.5f, "LW_KatteShimo"),      // 2間
            WG( 4,41,  5,43, 11.5f, "LW_ShimoYudono"),     // 2間
            WG(15,23, 18,24, 11.5f, "LW_ShimoJochu"),      // 3間
            WG(23,32, 24,35, 11.5f, "LW_JochuGoyo"),       // 3間
            // 北縁の外廊下 = 各棟の入側の続き。段を跨ぐ所は石段(手組み資産)に突き付ける
            WG(13,48, 18,49, 11.5f, "LW_Kita1"),           // 5間 湯殿 → 御用部屋棟
            WG(26,48, 28,49, 11.5f, "LW_Kita2"),           // 2間 御用部屋棟 → 石段W2の下端
            WG(30,48, 34,49, 19.5f, "LW_Kita3"),           // 4間 石段W2の上端 → 長局棟
                                                           // ⚠ 3間だと石段の上端(x=-592)に0.36m届かず廊下が切れる
            SG(58,44, 60,45, 25.5f, "LW_Kita6"),           // 2間 石段W1の上端 → 西縁の外廊下
            // ⚠ 長局棟の東面 → 石段W1 は廊下を架けない(v3 の LW_Kita5 を廃した)。
            //   ・棟の外形は x=-571.644、石段の段板は x=-571.245 から。その差 0.4m は
            //     棟が四方に回している濡縁(0.89m)が既に埋めている — 帯を足すと二重になる。
            //   ・1間でも渡廊下を架けると屋根の大棟(床+2.503=22.62)が折返しの下り
            //     (x=-570 付近で段裏 21.28)を突き破る。高欄だけでも 21.28 で接する。
            //   実際に歩く道は「濡縁 → 中段の地面 → 石段W1の下端(x=-566, z=1037)」で、
            //   5m は屋外を渡る。石段の折返しがこの取り合いを許さない(石段は手組み資産)。
        };
    }

    // 郭をまたぐ外の道(白洲の参道・主郭東縁の取付き)。
    // 二つの郭のグリッドが 191m 離れていて整数間にならず、間は手組みの石段が受けるので、
    // GotenLinks のように間割りへは乗せず**一本ずつ起点と間数を書く**。
    // v4 で Village Kit の RokaRect から EdoGotenKit.Roka(御殿と同じ部材)へ差し替えた。
    //
    // 【石段側の1間は屋根を伏せる(openKen)】折返し石段の踊り場は参道の床から 2.7〜3.0m 上に
    //   あり、廊下の大棟(床+2.503)とぶつかる。石段に取り付く側の1間を落縁(床+高欄のみ)に
    //   すると、屋根の妻(端で0.30出る)が最寄りの段から 1.27m 逃げて当たらない。
    //   実際、廊下が石段へ開いて一段下りるのは指図どおりの納まりでもある。
    public struct Path
    {
        public float x0, zC, y;     // 西端 / 中心線のz / 段のレベル
        public int ken;             // 総間数
        public int openS, openE;    // 西端・東端の落縁(屋根なし)の間数
        public bool colS, colE;     // 両端の柱通り(棟に突き付ける側・宙に出る側は false)
        public string name;
        public float x1 { get { return x0 + ken * KEN; } }
        public float z0 { get { return zC - KEN * 0.5f; } }
        public float z1 { get { return zC + KEN * 0.5f; } }
    }
    public static Path[] PathLinks()
    {
        return new[] {
            // 主郭の東縁: 玄関棟の東面(U=1)→ 石段E1の上端。床が石段E1の最上段に 0.06 かぶる
            new Path{ name="L_HigashiEn", x0=-457f-1*KEN, zC=1001f, y=25.5f, ken=2,
                      colS=false, colE=true },
            // 東中段(19.5)の参道: 石段E1の footprint の東端 → 石段E2の上端。
            // 両端とも石段に開くので落縁。東端は IG_E2 の天端から 0.45 出て最上段の上に架かる
            new Path{ name="L_Sando19", x0=-450f, zC=1001f, y=19.5f, ken=14,
                      openS=1, openE=1, colS=true, colE=false },
            // 表門前段(13.5)の参道: 石段E2の footprint の東端 → 白洲を東へ。
            // 東端は表門(x=-381)まで届かない — 供待・厩の帯の手前で切る(指図に廊下は無い)
            new Path{ name="L_Sando13", x0=-420f, zC=1001f, y=13.5f, ken=13,
                      openS=1, colS=true, colE=true },
        };
    }
    // 庭(指図と同じ矩形)。白洲を塗るときにここは芝のまま残す
    public static Blk[] Gardens()
    {
        return new[] {
            SG( 0, 0, 11,20, 25.5f, "NiwaOmoteE"),  SG(11, 0, 44, 7, 25.5f, "NiwaOmoteS"),
            SG( 0,36, 11,56, 25.5f, "NiwaShoin"),   SG(21,29, 37,36, 25.5f, "Tsubo"),
            SG(47,38, 58,53, 25.5f, "NiwaOkuUchi"),
        };
    }
    // 折返し石段 (rect / 上端レベル / 下端レベル / 降りる向き)
    public struct Kai { public float x0, z0, x1, z1, yTop, yBot; public bool east; public string name; }
    public static Kai[] Kaidans()
    {
        return new[] {
            new Kai{ x0=-455f, z0=999f, x1=-450f, z1=1003f, yTop=25.5f, yBot=19.5f, east=true,  name="Kaidan_E1" },
            new Kai{ x0=-425f, z0=999f, x1=-420f, z1=1003f, yTop=19.5f, yBot=13.5f, east=true,  name="Kaidan_E2" },
            new Kai{ x0=-571f, z0=1034f, x1=-566f, z1=1038f, yTop=25.5f, yBot=19.5f, east=false, name="Kaidan_W1" },
            new Kai{ x0=-598.5f, z0=1034f, x1=-592f, z1=1038f, yTop=19.5f, yBot=11.5f, east=false, name="Kaidan_W2" },
        };
    }

    // 表門(下書きの三角マーク) と その外向き
    public static readonly Vector2 GATE = new Vector2(-381.0f, 1001.0f);
    public static Vector2 GateOut() { return (-B.InwardNormal(SK.OKABE, 10)).normalized; }
    public static float YawGate() { var o = GateOut(); return Mathf.Atan2(o.x, o.y) * Mathf.Rad2Deg; }

    // 外周長屋・塀・内部長屋の芯線(下書きを垂直水平に正規化)
    public struct Run { public Vector2 a, b, outw; public string name; public bool nagaya; }
    public static Run[] Runs()
    {
        var P = SK.OKABE;
        Func<int, Vector2> eo = i => -B.InwardNormal(P, i);
        var d10 = (P[0] - P[10]).normalized;              // 東辺の走り(北→南)
        return new[] {
            new Run{ name="NG_S0", a=P[3], b=P[2], outw=eo(2), nagaya=true },   // 南辺(西)
            new Run{ name="NG_S1", a=P[2], b=P[1], outw=eo(1), nagaya=true },   // 南辺(中)
            new Run{ name="NG_S2", a=P[1], b=P[0], outw=eo(0), nagaya=true },   // 南辺(東)
            new Run{ name="NG_E_S", a=P[0], b=GATE + d10 * 6.5f, outw=eo(10), nagaya=true },  // 東辺 南半
            new Run{ name="NG_E_N", a=GATE - d10 * 6.5f, b=P[10], outw=eo(10), nagaya=true }, // 東辺 北半
            new Run{ name="NG_NE",  a=P[10], b=P[9], outw=eo(9), nagaya=true },  // 北東の隅切り辺
            new Run{ name="Hei_N1", a=P[9], b=P[8], outw=eo(8), nagaya=false },
            new Run{ name="Hei_N2", a=P[8], b=P[7], outw=eo(7), nagaya=false },
            new Run{ name="Hei_N3", a=P[7], b=P[6], outw=eo(6), nagaya=false },
            new Run{ name="Hei_W1", a=P[6], b=P[5], outw=eo(5), nagaya=false },
            new Run{ name="Hei_W2", a=P[5], b=P[4], outw=eo(4), nagaya=false },
            new Run{ name="Hei_W3", a=P[4], b=P[3], outw=eo(3), nagaya=false },
        };
    }

    static string BAK = "/private/tmp/claude-501/-Users-toshio-project-edo-unity/"
        + "0481f3c6-e686-419e-90e8-8fbaf448079d/scratchpad/okabe_v3_backup.bin";
    // 廊下・参道の部材は EdoAssets.Goten(御殿と同じキット)。Village Kit の床・柱・屋根は
    // v4 で全廃した — 御殿と並べると質が揃わない、というユーザー裁定(2026-08-15)
    const string PStep = EdoAssets.Own.DanishiStep;
    const float STEP_HALF = 0.245f;     // 段板(P_DanishiStep2m)の走り方向の実寸 0.49 の半分
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

    static float G(float x, float z) { return B.Ground(x, z); }
    static Transform Grp(string n) { return B.Group(GN, n); }
    static void Clear(Transform t) { var l = new List<Transform>(); foreach (Transform c in t) l.Add(c); foreach (var c in l) UnityEngine.Object.DestroyImmediate(c.gameObject); }
    static float DistSeg(Vector2 p, Vector2 a, Vector2 b)
    { var d = b - a; float L = d.magnitude; if (L < 1e-4f) return (p - a).magnitude; d /= L; float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, L); return (p - (a + d * t)).magnitude; }

    // =========================================================================
    // Stage 0/1: バックアップと段の造成
    // =========================================================================
    public static string Stage0_Backup()
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        int bx0 = IX(-700f), bx1 = IX(-370f), bz0 = IZ(930f), bz1 = IZ(1100f);
        int bw = bx1 - bx0 + 1, bh = bz1 - bz0 + 1;
        var bak = td.GetHeights(bx0, bz0, bw, bh);
        using (var w = new System.IO.BinaryWriter(System.IO.File.Open(BAK, System.IO.FileMode.Create)))
        { w.Write(bx0); w.Write(bz0); w.Write(bw); w.Write(bh);
          for (int z = 0; z < bh; z++) for (int x = 0; x < bw; x++) w.Write(bak[z, x]); }
        return "backup " + bw + "x" + bh;
    }

    public static string Stage1_Grade()
    {
        var mk = GameObject.Find("OKABE_GRADED_v4");
        if (mk != null) return "grade: SKIP (already graded v4)";
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<int, float> WX = ix => tp.x + ix * ts.x / (hres - 1);
        Func<int, float> WZ = iz => tp.z + iz * ts.z / (hres - 1);
        Func<float, float> HtoW = hn => hn * ts.y + tp.y;
        Func<float, float> WtoH = wy => (wy - tp.y) / ts.y;
        var terr = Terraces();
        int x0 = IX(-660f), x1 = IX(-368f), z0 = IZ(938f), z1 = IZ(1070f);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        int n = 0; float cmax = 0, fmax = 0;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            float wx = WX(x0 + x), wz = WZ(z0 + z);
            var p = new Vector2(wx, wz);
            if (!B.PIP(SK.OKABE, p)) continue;
            // 隣地の囲い(土井/松平所有)がある辺 4..7 は 9m、他は 1.4m あける
            float em = float.MaxValue;
            for (int i = 0; i < SK.OKABE.Length; i++)
                em = Mathf.Min(em, DistSeg(p, SK.OKABE[i], SK.OKABE[(i + 1) % SK.OKABE.Length]) - ((i >= 4 && i <= 7) ? 9f : 1.4f));
            if (em < 0f) continue;
            // どの段に属するか + 段の内側への距離
            float best = -1f, bestD = -1f;
            foreach (var tr in terr)
            {
                if (wx < tr.x0 || wx > tr.x1 || wz < tr.z0 || wz > tr.z1) continue;
                float d = Mathf.Min(Mathf.Min(wx - tr.x0, tr.x1 - wx), Mathf.Min(wz - tr.z0, tr.z1 - wz));
                if (d > bestD) { bestD = d; best = tr.y; }
            }
            if (best < 0f) continue;
            // 段の境目では隣の段と噛み合うので、フェザーは段の縁3m + 敷地際4m だけ
            float k = Mathf.SmoothStep(0f, 1f, Mathf.Min(Mathf.Clamp01(bestD / 3f + 0.34f), Mathf.Clamp01(em / 4f)));
            if (k <= 0.001f) continue;
            float cur = HtoW(H[z, x]);
            // 石垣の近傍は clamp しない — 地面を壁に合わせる(unity-modular-stonewall §3)
            bool nearWall = false;
            foreach (var wl in Walls()) if (DistSeg(p, wl.a, wl.b) < 7f) { nearWall = true; break; }
            float tgt = nearWall ? best : Mathf.Clamp(best, cur - CUT_MAX, cur + FILL_MAX);
            float nw = Mathf.Lerp(cur, tgt, k);
            if (nw < cur) cmax = Mathf.Max(cmax, cur - nw); else fmax = Mathf.Max(fmax, nw - cur);
            H[z, x] = WtoH(nw); n++;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        // ⚠ マーカーは active のままにする。GameObject.Find は非アクティブを見つけないので
        //    SetActive(false) にするとガードが毎回すり抜けて多重造成する(2026-08-14 に実際に起きた)。
        mk = new GameObject("OKABE_GRADED_v4");
        var yg = GameObject.Find(GN); if (yg != null) mk.transform.SetParent(yg.transform, false);
        return "grade cells=" + n + " cutMax=" + cmax.ToString("F2") + " fillMax=" + fmax.ToString("F2");
    }

    // =========================================================================
    // Stage 2: 全再接地(石段・飛石・廊下は除外 — 設計レベルで据えてある)
    // =========================================================================
    public static string Stage2_Reseat()
    {
        int n = 0;
        var yg = GameObject.Find(GN);
        var roots = new List<Transform>();
        foreach (Transform g in yg.transform)
            if (g.name != "Roka" && g.name != "Garden" && g.name != "Ishigaki"
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
    // Stage 3: v1/v2 の撤去(削除しない)
    // =========================================================================
    public static string Stage3_Retire()
    {
        int n = 0;
        var yg = GameObject.Find(GN);
        foreach (var gname in new[] { "Buildings", "Garden", "Service", "Kakoi", "Omotemon" })
        {
            var g = yg.transform.Find(gname);
            if (g == null || g.childCount == 0) continue;
            string rn = gname + "_v2_retired";
            var keep = yg.transform.Find(rn);
            if (keep == null)
            { var go = new GameObject(rn); Undo.RegisterCreatedObjectUndo(go, "retire"); go.transform.SetParent(yg.transform, false); keep = go.transform; }
            var kids = new List<Transform>(); foreach (Transform c in g) kids.Add(c);
            foreach (var c in kids) { c.SetParent(keep, true); c.gameObject.SetActive(false); n++; }
            keep.gameObject.SetActive(false);
        }
        return "retired " + n;
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
        foreach (var r in Runs())
        {
            if ((r.b - r.a).magnitude < 6f) continue;
            if (r.nagaya) { var l = NT.NagayaRun(kak, r.a, r.b, r.outw, 0f, Vector2.zero, -1, r.name); nm += l.Count; }
            else NT.DobeiRun(kak, r.a, r.b, r.outw, r.name, true, 0, Vector2.zero, -1);
        }
        sb.AppendLine("nagaya modules=" + nm);
        // 表門(k_mon + 両番所) — 東辺、下書きの三角マーク位置
        float gh = B.PlaceGate(PKmon, mon, GATE, GateOut(), 2, "Kmon", sb);
        // 隅櫓 [福井図: 上屋敷格の外周装置] — 敷地の南東隅・南西隅
        Yagura(kak, new Vector2(-378.5f, 950.5f), new Vector2(0.83f, -0.56f), "Sumiyagura_SE");
        Yagura(kak, new Vector2(-643.5f, 940.5f), new Vector2(-0.72f, -0.69f), "Sumiyagura_SW");
        return sb.ToString();
    }
    static void Yagura(Transform parent, Vector2 p, Vector2 bis, string nm)
    {
        var ex = parent.Find(nm); if (ex != null) UnityEngine.Object.DestroyImmediate(ex.gameObject);
        float psi = Mathf.Atan2(bis.x, bis.y) * Mathf.Rad2Deg;
        float y = G(p.x, p.y);
        var go = B.Place(PKnagayaC, new Vector3(p.x, y, p.y), psi, new Vector3(ES * 0.55f, ES, ES), parent, nm);
        var rb = B.RB(go); go.transform.position += new Vector3(p.x - rb.center.x, 0, p.y - rb.center.z);
        rb = B.RB(go); go.transform.position += new Vector3(0, (y + 0.85f) - rb.min.y, 0);
    }

    // =========================================================================
    // Stage 4b: 石垣(段の土留め) + 天端に載る家臣長屋2列
    //   unity-modular-stonewall §2/§3: ピッチ1.800(0.20重ね) / 1本の壁に position.y と scale.y は1値ずつ /
    //   coping = position.y + 4.0*scale.y / 躯体2.4mは走りの左(local -X)に出る。
    // =========================================================================
    const string P_CW = EdoAssets.JC.CastleWall;
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
            int n = Mathf.Max(2, Mathf.RoundToInt((L - 2f) / 1.8f) + 1);
            int made = 0;
            for (int i = 0; i < n; i++)
            {
                float t = 2f + 1.8f * i;
                if (t > L + 0.4f) break;
                if (Mathf.Abs(t - gapT) < 4.0f) continue;          // 階段の開口(§4: 1本のrunから切り取る)
                var p = w.a + d * t;
                var go = (GameObject)PrefabUtility.InstantiatePrefab(pre, ig);
                Undo.RegisterCreatedObjectUndo(go, "cw"); go.name = w.name + "_" + i;
                go.transform.position = new Vector3(p.x, posY, p.y);
                go.transform.rotation = Quaternion.Euler(0, yaw, 0);
                go.transform.localScale = new Vector3(1f, w.sy, 1f);
                made++;
            }
            sb.AppendLine(w.name + " pieces=" + made + " posY=" + posY.ToString("F2") + " sy=" + w.sy.ToString("F2") + " coping=" + w.coping.ToString("F2"));
        }
        // 家臣長屋2列 — 西の石垣A/Bの天端に載せる(下書きの赤線2本)
        // perimeter.md: なまこ壁の外面を天端の外面と面一(0.00〜0.20m)、土台底 = 天端 − 1.59m
        bool nm0 = NT.NaturalMode; NT.NaturalMode = false;
        foreach (var w in Walls())
        {
            if (!w.name.StartsWith("IG_W")) continue;
            Vector2 outw = new Vector2(-1f, 0f);                    // 西向き
            var mods = NT.NagayaRun(kn, w.a + new Vector2(2.2f, 0), w.b + new Vector2(2.2f, 0), outw,
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
                    float crestOuter = w.a.x * outw.x;
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
            BuildMune(bg, m);
            area += (m.x1 - m.x0) * (m.z1 - m.z0);
            moya += m.MoyaW * m.MoyaD * KEN * KEN;
            sb.AppendLine(string.Format("  {0,-13} 身舎 {1,2}x{2,-2}間 + 入側 / 屋根 {3}x{4}間",
                m.name, m.MoyaW, m.MoyaD, Mathf.Max(m.kw, m.kd), Mathf.Min(m.kw, m.kd)));
        }
        sb.AppendLine(string.Format("goten 棟={0} 外形={1:F0}m2(身舎 {2:F0}m2 = {3:F0}畳)",
            Muneya().Length, area, moya, moya / (0.909f * KEN)));
        return sb.ToString();
    }

    /// <summary>棟を1つ建てる。外形の長辺が桁行(ローカルX)に来るよう寝かせ、寸法の合う屋根を載せる。</summary>
    static void BuildMune(Transform parent, Blk m)
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
    }

    // =========================================================================
    // Stage 6: 廊下 — 渡廊下・外廊下・参道・折返し石段
    //   ⚠ **入側はここでは作らない**。四方の入側は Mune() が棟の一部として組む(v4)。
    //     ここで帯を重ねて敷くと床と柱が二重になって z-fighting する。
    //   渡廊下は EdoGotenKit.Roka。両端は棟に突き付けるので端の柱通りは落とす
    //   (棟の柱と同じ位置に立つため)。
    //   参道(郭をまたぐ外の道)も v4 で同じキットへ。石段に取り付く1間は屋根を伏せた
    //   落縁にする — 折返しの踊り場が廊下の大棟の高さに来るため(PathLinks の注記)。
    // =========================================================================
    public static string Stage6_Roka()
    {
        var rk = Grp("Roka"); Clear(rk);
        int nr = 0;
        foreach (var l in GotenLinks()) { BuildRoka(rk, l); nr++; }
        int np = 0;
        foreach (var l in PathLinks()) { BuildPath(rk, l); np++; }
        int nk = 0;
        foreach (var k in Kaidans()) { Kaidan(rk, k); nk++; }
        return "roka 渡廊下=" + nr + " 参道=" + np + " kaidan=" + nk + " / " + RokaConnectivity();
    }

    /// <summary>指図の不変条件「廊下は一続き」を機械で確かめる。
    /// 通れる面 = 棟の入側の環(外形から身舎を抜く)+ その外を巡る濡縁 + 渡廊下 + 参道 + 石段。
    /// ラスタに落として4近傍で連結成分を数える。**1個でなければ廊下がどこかで切れている**。
    /// 段を跨ぐ所は石段が橋渡しするので、高さは見ずXZ平面で判定してよい。
    ///
    /// ⚠ これは**平面の近似**であって「歩ける」の証明ではない。折返し石段は下端が上端と
    ///   同じ側に戻るので、矩形が重なっていても実際は段の下をくぐる — 石段W1の下端
    ///   (x=-566, z=1037)は長局棟の濡縁の 5m 東にあり、その間は中段の地面を歩く。</summary>
    [MenuItem("Edo/岡部筑前守上屋敷/廊下の連結を検査")]
    public static void CheckRokaMenu() { Debug.Log("[Okabe] " + RokaConnectivity()); }
    public static string RokaConnectivity()
    {
        const float cell = 0.45f;
        var band = new List<Rect>(); var hole = new List<Rect>();
        foreach (var m in Muneya())
        {
            // 濡縁(0.89m)は Mune() が四方に回すので、踏める面は外形より一回り大きい
            band.Add(Rect.MinMaxRect(m.x0 - NUREEN, m.z0 - NUREEN, m.x1 + NUREEN, m.z1 + NUREEN));
            hole.Add(Rect.MinMaxRect(m.x0 + KEN, m.z0 + KEN, m.x1 - KEN, m.z1 - KEN));
        }
        foreach (var l in GotenLinks()) band.Add(Rect.MinMaxRect(l.x0, l.z0, l.x1, l.z1));
        foreach (var l in PathLinks()) band.Add(Rect.MinMaxRect(l.x0, l.z0, l.x1, l.z1));
        // 石段の矩形は**段の芯**の走り。段板は走り方向に 0.49 あるので上下端で 0.245 ずつはみ出す。
        // 参道はその実寸へ突き付けてあるので、芯の矩形のままだと 0.18m の嘘の切れ目が出る
        foreach (var k in Kaidans())
            band.Add(Rect.MinMaxRect(k.x0 - STEP_HALF, k.z0, k.x1 + STEP_HALF, k.z1));
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
        var sb = new System.Text.StringBuilder();
        sb.Append("廊下 " + (total * cell * cell).ToString("F0") + "m2 連結成分=" + comps.Count);
        if (comps.Count != 1)
        {
            for (int i = 0; i < comps.Count; i++) sb.Append(i == 0 ? " [" : " / ").Append((comps[i] * cell * cell).ToString("F0") + "m2");
            sb.Append("]  ⚠ 廊下が切れている");
            Debug.LogWarning("[Okabe] 廊下が" + comps.Count + "つに割れている。段の取付きの重なりを確かめる");
        }
        return sb.ToString();
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
        var g = alongX
            ? EdoGotenKit.Roka(l.name, parent, new Vector3(l.x0, l.y, l.z0), 0f, n,
                               GOTEN_FLOOR, colStart: false, colEnd: false)
            : EdoGotenKit.Roka(l.name, parent, new Vector3(l.x1, l.y, l.z0), 270f, n,
                               GOTEN_FLOOR, colStart: false, colEnd: false);
        Undo.RegisterCreatedObjectUndo(g, "roka");
    }

    /// <summary>参道を1本。石段側の openS/openE 間は屋根を伏せた落縁にし、
    /// 残りを1本の切妻屋根の廊下(EdoGotenKit.Roka)で通す。走りは +X 固定。</summary>
    static void BuildPath(Transform parent, Path p)
    {
        var g = new GameObject(p.name); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "path");
        int mid = p.ken - p.openS - p.openE;
        if (mid < 2)
            Debug.LogWarning("[Okabe] " + p.name + ": 屋根を架ける区間が" + mid + "間 — 2間未満は成立しない");
        if (p.openS > 0) Ochien(g.transform, "En_W", p.x0, p.zC, p.y, p.openS);
        if (mid > 0)
        {
            var r = EdoGotenKit.Roka(p.name + "_Roka", g.transform,
                                     new Vector3(p.x0 + p.openS * KEN, p.y, p.z0), 0f, mid,
                                     GOTEN_FLOOR,
                                     colStart: p.openS > 0 || p.colS,
                                     colEnd: p.openE > 0 || p.colE);
            Undo.RegisterCreatedObjectUndo(r, "roka");
        }
        if (p.openE > 0)
            Ochien(g.transform, "En_E", p.x1 - p.openE * KEN, p.zC, p.y, p.openE);
    }

    /// <summary>落縁 — 屋根も桁も無い板敷きの縁。床(1間角)+ 両縁の高欄だけ。
    /// 廊下が石段へ開く所に使う(桁だけ残すと骨組みが宙に浮いて見える)。</summary>
    static void Ochien(Transform parent, string nm, float x0, float zC, float lv, int ken)
    {
        var g = new GameObject(nm); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "ochien");
        float y = lv + GOTEN_FLOOR;
        for (int i = 0; i < ken; i++)
        {
            float cx = x0 + (i + 0.5f) * KEN;
            Put(g.transform, EdoAssets.Goten.FloorBoard, new Vector3(cx, y, zC), 0f);
            Put(g.transform, EdoAssets.Goten.Koran, new Vector3(cx, y, zC - KEN * 0.5f), 0f);
            Put(g.transform, EdoAssets.Goten.Koran, new Vector3(cx, y, zC + KEN * 0.5f), 180f);
        }
    }

    static void Put(Transform parent, string path, Vector3 pos, float ry)
    {
        var src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (src == null) { Debug.LogError("[Okabe] 見つからない: " + path); return; }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
        Undo.RegisterCreatedObjectUndo(go, "part");
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(0f, ry, 0f);
    }

    // 折返し石段: 二流れ+踊り場。蹴上0.30m
    static void Kaidan(Transform parent, Kai k)
    {
        var g = new GameObject(k.name); g.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(g, "kaidan");
        var pre = AssetDatabase.LoadAssetAtPath<GameObject>(PStep);
        int n = Mathf.Max(2, Mathf.RoundToInt((k.yTop - k.yBot) / 0.30f));
        int half = n / 2;
        float runLen = (k.x1 - k.x0);
        float wHalf = (k.z1 - k.z0) * 0.5f;
        float dir = k.east ? 1f : -1f;
        float xStart = k.east ? k.x0 : k.x1;
        for (int i = 0; i <= n; i++)
        {
            bool first = i <= half;
            int ii = first ? i : (n - i);
            float t = (float)ii / Mathf.Max(1, half);
            float px = xStart + dir * (runLen * t);
            float pz = first ? (k.z0 + wHalf * 0.5f) : (k.z1 - wHalf * 0.5f);
            float lvl = Mathf.Lerp(k.yTop, k.yBot, (float)i / n);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pre, g.transform);
            Undo.RegisterCreatedObjectUndo(go, "st"); go.name = "S_" + i;
            go.transform.rotation = Quaternion.Euler(0, 90f, 0);
            var rb = B.RB(go);
            go.transform.position += new Vector3(px - rb.center.x, lvl - rb.max.y, pz - rb.center.z);
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
        foreach (var gn in new[] { "Buildings", "Service", "Kakoi", "Omotemon", "Roka" })
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
            bool inTerr = false;
            foreach (var tr in terr) if (wx > tr.x0 && wx < tr.x1 && wz > tr.z0 && wz < tr.z1) inTerr = true;
            if (!inTerr) continue;
            bool inG = false;
            foreach (var g in gard) if (wx > g.x0 - 1f && wx < g.x1 + 1f && wz > g.z0 - 1f && wz < g.z1 + 1f) inG = true;
            float bare, grass, dirt;
            if (inG) { grass = 0.72f; dirt = 0.20f; bare = 0.08f; }
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
