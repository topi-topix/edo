#!/usr/bin/env python3
"""図の**字面**を機械で測り、重なり・枠外・**塗りへの潜り**・**小さすぎる字**を潰す。

⭐⭐ **なぜ機械で測るのか。** 2026-09-08 の検図で「文字どうしの重なり 49組/13面・
枠外へ出る文字 67件/24面」が出た。⛔ **目で一つずつ潰すと次の巡でまた増える** —
図版は毎巡ふえ、文字は設計値から組み立てられるので**値が変わるたびに幅が変わる**。
⇒ ⭕ **測る道具を図の中に置き、件数を刷る。**

⛔⛔ **2026-09-08 第5巡で分かったこと: 「重なり 0 件」は「読める」ではなかった。**
検図方が Chrome へ渡して**字あり/字なしの2枚を画素で引き算**したところ、
**銘が10件、そもそも紙に乗っていなかった** — ⚠ **後から描く塗りに上書きされて消えていた**
(f08 は面の高さの銘が5つまるごと不可視)。⭐ 原因の形は同じで、
**`text` × `text` しか測らない物差しには「文字が塗りに覆われる」が構造的に見えない**。
⇒ **0 件は「無い」ではなく「探していない」。**⭕ この版で三つ足した:

  ① **潜り(覆われた銘)** — `text` より**後ろ**に、その字面と交わる**不透明な塗り**があるか。
     ⛔ 再レンダは要らない — **描画順の照合**で出る。⭕ 直しは `relayout` が
     **銘を面の末尾へまとめて送る**(= 常に最後に描く)。
     ⚠ 「塗り」は**線の帯・`style` の fill・曲線 path・`use`** まで含む(下記 第6巡)。
  ② **字送りの下限** — 和字を含む字面の**実効 px**(基準の窓での見え方)が `MIN_EFF` 未満。
     ⛔ 「書いてある」と「読める」は別物で、⚠ **字を小さくするほど重なりの検査には
     当たらなくなる**(宣言された寸法で箱を組むため)= 検査の向きが読めなさを罰していない。
  ③ **推定幅の安全率** — 1字の em を最小二乗で解き直した(下表)。⛔ 一般約物を 0.5em と
     見誤っており、**+92% の過小**で 8件/5面が枠から出ていた。

【この道具の物差し(近似であることを隠さない)】
指図は SVG を**ブラウザに渡す前に**組む。⛔ 生成器はフォントを持たないので、
**字送りは近似**である。⭐ 値は検図方が 1,012 字面の `getBBox()` から**最小二乗で解いた実測**:
和字/記号 0.984 / 数字 0.569 / 一般約物 0.962 / 空白 0.376 em。
⚠ それでも 1〜3% は残るので、**`SAFE` を掛けて安全側へ倒す**。
⇒ 名乗れるのは「**この物差しで 0 件**」であって「重なっていない」ではない。
⭕ 裏は検図方がレンダして目で取る。⭐ **道具の非対称**(機械は全面を網羅できるが精度が粗い /
目は精度が高いが 43 面を毎巡は見られない)を、そのまま役の分担にしてある。

⛔⛔ **2026-09-08 第6巡: 「墨が乗っている」は「読める」ではなかった。**
検図方が**宣言色 × 直下の地色**の WCAG コントラスト比を測ったところ、
**229 件が和文の下限(4.5:1)を割り、最悪は 1.04**(ほぼ同色)。⚠⚠ **前巡に「潜り」から
救い出した銘が、そのまま最悪側に着地していた** — ⛔ 救い出す先の色を測っていなかった。
⇒ ⭕ ⑤ **銘のコントラスト**を足し、直しは `haloize` が**自動で白フチを回す**
(⛔ 一つずつ手で色を選ばない — 色を手で選ぶと、地色が動いた次の巡でまた沈む)。

⛔⛔ **同じ巡で分かったこと: 潜りの検査には抜け道が6通りあった**(検図方 中1)。
**うち2通りは当図に現に在る形**(`stroke-width` 62.7px の道の帯 95 本・曲線を含む塗り)。
⚠⚠ 検図方の診断が重い — 「**0 件を保証していたのは検査ではなく `relayout` の
『銘を末尾へ送る』直しのほうで、検査は構造的に 0 しか返せない位置にいた**」。
⇒ `paint_layers` を **「紙を塗り得る全要素」**(太い線・`style` の fill・曲線 path・`use`)
へ広げ、**その4通りを破壊試験の束⑥〜⑨で毎回鳴らす**。
⚠ **それでもなお、この図で 0 件が続くのは末尾送りのおかげ**である(検査が効くのは
`transform`/`opacity`/`mask` の群に残った銘と、末尾送りが壊れた巡)。⛔ 混同しない。

【この版でも測っていないこと(⛔ 次の巡へそのまま渡す)】
⛔ **窓の幅**: 実効 px は `VIEW_W`(基準の窓)での値。⚠ 窓を狭めれば svg は縮み、
   字はそのぶん小さくなる(`.fig svg{width:100%}`)。⇒ **狭い窓での読めなさは測っていない**。
⛔ **半透明の重ね掛け**: 1枚ずつが `ALPHA_MIN` 未満なら「覆い」と数えない(束⑪が実証)。
⛔ **字の一部だけの覆い**: 1字の `COVER_FR` 未満は数えない(束⑫が実証)。
⛔ **円弧(`A`)と `transform` を持つ群**: 座標を解いていない(当図には 0 個)。
⛔ **コントラストは「宣言色 × 合成した地色」**であって**画素ではない** — ⚠ アンチエイリアス・
   フチの太さ・字画の細さは見ていない。⭕ 裏は検図方がレンダして目で取る。
⛔ **字の形**: 字送りは幅だけで、⚠ **合字・縦組み・約物の詰め**は見ていない。

【字の大きさと寄せは `sashizu.css` が正典】
⛔ 表をここに書き写さない(CLAUDE.md 絶対規則4)。`sashizu.css` を読んで組み立てる。
⚠ CSS のクラス規則は presentation attribute に勝つので、**`style=` で上書きした分だけ**が
クラスの既定を覆す(生成器の `T()` がそう出している)。

【使い方】
    doc, rep = svg_layout.relayout(doc)   # 直してから
    rep2     = svg_layout.check(doc)      # 直った図を測る(rep2 が刷る値)
"""
import html as _html
import math
import os
import re

CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css")

_RE_SVG = re.compile(r'(<svg\b[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"[^>]*>)(.*?)(</svg>)', re.S)
_RE_TXT = re.compile(r'<text\b([^>]*)>(.*?)</text>', re.S)
# ⛔⛔ **属性名に数字と `:` が入る**(`x1` `y2` `xlink:href`)。⚠ 2026-09-08 まで
#   `[a-zA-Z-]+` で拾っており、**線の端点 `x1…y2` が一つも取れていなかった** —
#   ⚠ 線を「覆わない物」として外していたので**誰も気づかなかった**(検図方 中1)。
_RE_ATT = re.compile(r'([a-zA-Z][\w:.-]*)="([^"]*)"')
_RE_RULE = re.compile(r'\.([A-Za-z][\w-]*)\s*\{([^}]*)\}')

TOL = 0.5          # px。この物差しの粗さより小さい当たりは数えない
MIN_AREA = 0.5     # px²。角がかすめるだけの当たりは数えない
PAD = 4.0          # px。枠の内側にこれだけ残す

# ⭐ **推定幅の安全率。** 1字の em を実測で入れ替えてもなお 1〜3% は残る
#   (書体・字詰め・端末)。⛔ 端数を「たぶん入る」で通さない。
SAFE = 1.06
_WS = [1.0]        # ⚠ **破壊試験だけが振る**。既定 1.0(⛔ 生成では触らない)

# ⭐ **基準の窓での svg の実表示幅[px]。** `sashizu.css` の `.wrap{max-width:1120;padding:0 24}`
#   と `.fig{padding:14}` から 1120 − 24×2 − 14×2 = 1044。⚠ **これより狭い窓は測っていない。**
VIEW_W = 1044.0
MIN_EFF = 8.5      # px。和字を含む字面の実効 px の下限(これ未満は「読めない」)

# ⭐ 覆いの判定。⛔ 半透明の薄掛けは「覆い」と呼ばない
ALPHA_MIN = 0.5    # 塗りの実効不透明度がこれ以上なら覆う物とみなす
COVER_FR = 0.6     # 1字の箱のこれだけが塗りの下なら、その字は乗っていない
STROKE_MIN = 1.5   # px。⭐ これ以上の太さの線は**紙を塗る**(⛔ 線を「塗りでない」と見ない)

# ⭐⭐ **銘のコントラストの下限**(2026-09-08 検図方 高2)。WCAG 2.x の**和文の通常字**の下限。
#   ⛔ **「墨が乗っている」は「読める」ではない** — 潜りから救い出した銘が
#   `#615C4E` on `#505B64`(比 1.04 = ほぼ同色)に着地していた。
CR_MIN = 4.5
# ⭐ 白フチ(`paint-order:stroke`)の太さ。字の大きさに従わせる(⛔ 一つずつ選ばない)。
HALO_W = (2.4, 3.5)     # px。下限・上限
HALO_FS = 0.30          # 字の大きさに対する割合
REF_NEAR = 24.0    # px。⭐ **拾い上げてよいのは、元の位置の近くに物が描かれている銘だけ**


# ---------------------------------------------------------------- 文書の記法が図へ漏れる
# ⭐⭐⭐ **2026-09-08 検図方 中1。**⛔⛔ **断面 20 面の凡例が
#   `破線=<b>江戸期の復元地盤</b>` と、`<b>` `</b>` を字として刷っていた** —
#   ⚠⚠ **断面の読み方を説明する当の一行**で、しかも**「字面を機械で 0 件にした」と
#   名乗る図**である。⇒ この一行が壊れていると、その名乗り全体が疑われる。
# ⛔ 従前の字面の5項目は**どれも「タグが字になった」を見ていなかった**
#   (重なり・枠外・潜り・小字・コントラストは、どれも**字の置き場所と色**の物差し)。
# ⇒ ⭕ **第6項**として、`svg > text` に**文書の記法**が残っていないかを毎回測る。
_MK = (
    ("タグ", re.compile(r'</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*?)?/?>')),
    ("実体参照", re.compile(r'&(?:[a-zA-Z][a-zA-Z0-9]{1,9}|#\d{1,6}|#[xX][0-9a-fA-F]{1,6});')),
    ("太字", re.compile(r'\*\*')),
    ("引用符", re.compile(r'`')),
    ("リンク", re.compile(r'\[[^\[\]\n]*\]\([^()\s]*\)')),
)
_RE_MK_CODE = re.compile(r'`([^`\n]+)`')


def plain(s):
    """**文書の記法を図の字へ直す。**⛔ `T()` はこれを通してから紙へ刷る。

    ⚠ **剥がすだけにしない** — ``` `frmEnro.pts` ``` の引用符を落とすと
    「どこまでが名前か」が消える。⇒ ⭕ **〈 〉**(和文の引用の約物)へ替える。
    ⛔ タグ・実体参照・太字・リンクは**落とす**(図に太字の段もリンクも無い)。
    ⚠ **不動点まで回す** — 落とした跡が新しい記法の形になることがある(`<b<b>>`)。
    """
    for _ in range(4):
        t = _MK[4][1].sub(lambda m: m.group(0)[1:m.group(0).index("]")], s)
        t = _RE_MK_CODE.sub('〈\\1〉', t).replace("`", "")
        t = _MK[0][1].sub("", t)
        t = _MK[1][1].sub("", t)
        t = t.replace("**", "")
        if t == s:
            return t
        s = t
    return s


def markup_hits(s):
    """その字面に残る記法の印。⛔ **裸の `<` `>` は数えない** — ⚠ 「梁間 &lt; 3.0」の
    ような不等号は正しい字である。⇒ **タグの形**(`</?英字…>`)だけを拾う。

    ⚠ **`plain()` と対で持つ** — `markup_hits(plain(s))` は必ず空(下の束⑮が毎回試す)。
    """
    return [nm for nm, rx in _MK if rx.search(s)]


# ---------------------------------------------------------------- 記法が本文へ漏れる
# ⭐⭐⭐ **2026-09-08 第8巡・検図方。⛔⛔ 上の第6項の母集団は `svg > text` の字面だけで、
#   html の本文と表は1字も入っていなかった。**⚠⚠ そのため「記法を紙へ刷らない」と掲げた
#   当の巡が、同じ紙へ **literal な `\n` を 21・生のバッククォートを +40・字になった
#   `<b>` を 8** ふやして通った。⛔ **限界の明示でも断っていない第三の面**だった
#   (明示していたのは「`T()` を通る銘は恒真 / 効くのは生の `<text>`」まで)。
# ⇒ ⭕ **母集団を文書全体へ広げる。**⛔ 個別に3つ潰して終わりにしない —
#   広げれば ⑴`\n` も ⑵バッククォートも ⑶タグ漏れも**毎巡自動で捕まる**。
#
# ⚠ **図の字面とは腕が違う**(同じ物差しを両面へ当てない)。html では:
#   ・生の `<b>` は**正しい記法**(紙には出ない)⇒ 数えない。
#     字として出るのは**エスケープされた形** `&lt;b&gt;` のほう。
#   ・実体参照も同じで、字として出るのは `&amp;nbsp;` のほう。
#   ・`\n` `\t` は json の注記が2文字のまま流れてくる形(⚠ 図の字面には出ない口)。
_MK_DOC = (
    ("タグ", re.compile(r'&lt;/?[a-zA-Z][a-zA-Z0-9]*(?:\s[^&<>]{0,80}?)?/?&gt;')),
    ("実体参照", re.compile(r'&amp;(?:[a-zA-Z][a-zA-Z0-9]{1,9}|#\d{1,6}|#[xX][0-9a-fA-F]{1,6});')),
    ("行送り", re.compile(r'\\[nrt]')),
    ("太字", re.compile(r'\*\*|~~')),
    ("引用符", re.compile(r'`')),
    # ⛔ **家の典拠記法 `[西川1959](A)` をリンクに数えない**(⚠ 当図に 17 出現)。
    #   ⇒ 括弧の中が **URL か path に見える物だけ**を「刷られたリンク」と読む。
    ("リンク", re.compile(r'\[[^\[\]\n]*\]\((?:[a-zA-Z][a-zA-Z0-9+.-]*:|\.{0,2}/)[^()\s]*\)')),
)

# ⭐ **リンクに数えなかった「家の典拠記法」の数**。⛔ 除いた物の数も手で書かない —
#   ⚠ 「当図に 17 出現」と地の文へ書くと、次の巡に古びる(規則19)。
_RE_CITE = re.compile(r'\[[^\[\]\n]*\]\([^()\s]*\)')

# ⭐⭐ **`<code>` の中も「別枠として」数える**(2026-09-08 第8巡)。⛔⛔ **除いた面を
#   「数えていない」で済ませない** — ⚠ 当図の紙には `<code>` の中に**生の引用符 12・
#   literal な `\n` 3・`**` 2・字になったタグ 21** が現に在る。⭕ それは**欠陥ではなく
#   記法そのものの引用**だが、⛔ **0 でない物を 0 と読ませない**ので件数を刷る。
#   ⚠⚠ **同時にこれは穴でもある** — 欠陥がこの面へ入り込めば、欠陥として鳴らない。
DOC_QUOTE = "引用(<code> の中)"

_RE_DOC_TAG = re.compile(r'<!--.*?-->|<[^<>]*>', re.S)
_DOC_SKIP = ("svg", "style", "script")      # 中の字は紙の本文ではない
_DOC_CELL = ("td", "th")                    # 面の仕分け(表 / 本文)


def doc_markup(doc):
    """**文書全体**(html の本文と表)に、記法が字として残っていないか。

    ⛔ **`<code>` の中は数えない** — ⚠ そこは**記法そのものを引用している**面で、
      `<code>&lt;b&gt;</code>` は欠陥ではなく説明である。
    ⛔⛔ **これは穴でもある** — 欠陥が `<code>` の中に入り込めば見えない。
      ⇒ 除いた span と字数を**必ず一緒に刷る**(下の束⑥が毎回この穴を実演する)。
    ⚠ **`<svg>` の中は見ない** — そちらは `check()` の第6項(`plain()` と対)が測る。

    返すのは {面: {腕: [(記法, 前後)]}} と、測った母集団の大きさ。
    """
    face = {"本文": {}, "表": {}, DOC_QUOTE: {}}
    nodes = chars = code_spans = code_chars = cite = 0
    _open = _skip = 0
    for txt, _tag, st in _doc_scan(doc):
        _open, _skip = st["code"], st["skip"]
        if txt is None or not txt.strip() or st["skip"]:
            if txt is None and _tag is not None and st["opened"] == "code":
                code_spans += 1
            continue
        if st["code"]:
            code_chars += len(txt)
            fc = face[DOC_QUOTE]          # ⭐ **引用の面も数える**(⛔ 欠陥には数えない)
        else:
            nodes += 1
            chars += len(txt)
            fc = face["表" if st["cell"] else "本文"]
        for nm, rx in _MK_DOC:
            for h in rx.finditer(txt):
                fc.setdefault(nm, []).append(
                    (h.group(0), txt[max(0, h.start() - 34):h.end() + 26]))
        if fc is not face[DOC_QUOTE]:
            cite += sum(1 for h in _RE_CITE.finditer(txt)
                        if not _MK_DOC[5][1].match(h.group(0)))
    return {"cite": cite, "face": face, "nodes": nodes, "chars": chars,
            "codeSpans": code_spans, "codeChars": code_chars,
            # ⛔⛔ **閉じていない `<code>` は母集団を静かに飲み込む**(2026-09-08 第8巡に踏んだ)。
            #   ⚠ `_pending` の注記へ生の `<code>` を1つ書いただけで、⚠⚠ **以降の紙が
            #   まるごと「引用の面」に落ち**、本文の字面が 16,942 → 10,421 へ減った。
            #   ⭐ 束①〜④が鳴って捕まったが、⛔ **名前の付いた失敗にしておく。**
            "codeOpen": _open, "skipOpen": _skip,
            "quoted": sum(len(v) for v in face[DOC_QUOTE].values()),
            "n": sum(len(v) for f in ("本文", "表") for v in face[f].values())}


def _doc_scan(doc):
    """html を「タグの外の字」と「タグ」に割って歩く。⛔ 物差しと直しで**同じ歩き方**を使う。

    ⚠ 産むのは `(字 or None, タグ or None, 状態)`。状態は `<svg>/<style>/<script>` の
    深さ `skip`・`<code>` の深さ `code`・`<td>/<th>` の深さ `cell`。
    """
    st = {"skip": 0, "code": 0, "cell": 0, "opened": None}
    pos = 0
    for m in _RE_DOC_TAG.finditer(doc):
        if m.start() > pos:
            yield doc[pos:m.start()], None, st
        pos = m.end()
        tag = m.group(0)
        st["opened"] = None
        if not tag.startswith("<!--"):
            nm9 = re.match(r'<\s*(/?)\s*([a-zA-Z][\w-]*)', tag)
            if nm9 and not (nm9.group(1) != "/" and tag.rstrip().endswith("/>")):
                shut, el = nm9.group(1) == "/", nm9.group(2).lower()
                d9 = -1 if shut else 1
                if el in _DOC_SKIP:
                    st["skip"] = max(0, st["skip"] + d9)
                elif not st["skip"]:
                    if el == "code":
                        st["code"] = max(0, st["code"] + d9)
                        st["opened"] = "code" if not shut else None
                    elif el in _DOC_CELL:
                        st["cell"] = max(0, st["cell"] + d9)
        yield None, tag, st
    if pos < len(doc):
        yield doc[pos:], None, st


_RE_DOC_CODE = re.compile(r'`([^`\n]+)`')


def docify(doc):
    """⭐⭐ **本文の `名` を `<code>名</code>` へ替える**(2026-09-08 第8巡・裁定1)。

    ⛔⛔ **図の側だけ記法を剥がして、本文は生のまま刷る、をやめる** — ⚠ 第7巡まで
      本文には**生のバッククォートが 1,916 個**あり、⭐ 考証方は「従前からの家の書き方」と
      証言した。⇒ ⭕ **禁じるのでも見逃すのでもなく、html の正しい器へ移す。**
      これで引用の約物が**図は〈 〉/ 本文は `<code>`** の一対になり、
      ⛔ **どちらの面にも生の記法が出ない**(第7巡の低3)。
    ⛔ **`<svg>` と `<code>` の中は触らない** — 前者は `plain()` の持ち場、
      後者は**記法そのものを引用している面**(``` `名` ``` を字として見せている所がある)。
    ⚠ 対になっていない裸のバッククォートは替えられない ⇒ **物差しの側が鳴る**(それでよい)。
    """
    out, n = [], 0
    for txt, tag, st in _doc_scan(doc):
        if tag is not None:
            out.append(tag)
            continue
        if st["skip"] or st["code"]:
            out.append(txt)
            continue
        t2, k = _RE_DOC_CODE.subn(r'<code>\1</code>', txt)
        out.append(t2)
        n += k
    return "".join(out), n


def doc_markup_counts(r, faces=("本文", "表")):
    """面ごと・腕ごとの件数。⛔ 順を他所で並べ替えない。"""
    return [(f, [(nm, len(r["face"][f].get(nm, ()))) for nm, _rx in _MK_DOC])
            for f in faces]


_DOC_PROBE = ("凡例=&lt;b&gt;江戸期の復元地盤&lt;/b&gt;", "余白 &amp;nbsp; 100 m",
              "一行目。\\n二行目。", "**太い字**", "点線の円=`at` の半径の帯",
              "[題](http://x/y)")


def doc_markup_probes(doc):
    """⭐⭐ **広げた母集団が生きていることを毎回見せる**(規則19)。⛔ 乱数を使わない。

    ⚠ 差し込むのは**紙のいちばん後ろ**(⛔ 既存の要素を書き換えない=冪等)。
    返すのは `[(題, 実測(本文, 表, `<code>` の中), 期待)]`。
    """
    def _n(dc):
        r = doc_markup(dc)
        return (sum(len(v) for v in r["face"]["本文"].values()),
                sum(len(v) for v in r["face"]["表"].values()), r["quoted"])
    base = _n(doc)

    def _d(dc):
        g = _n(dc)
        return (g[0] - base[0], g[1] - base[1], g[2] - base[2])

    six = "".join(_DOC_PROBE)
    out = [("① ⭐⭐ **6通りの記法(タグ/実体参照/行送り/太字/引用符/リンク)を"
            "本文の段落へ刷る** — ⚠ **本文で6件鳴る**",
            _d(doc + "<p>" + six + "</p>"), ("≥6", "0", "0")),
           ("② ⭐⭐ **同じ6通りを表のセルへ刷る** — ⚠ **表で6件鳴る**"
            "(⛔ 本文では鳴らない=面の仕分けが生きている)",
            _d(doc + "<table><tr><td>" + six + "</td></tr></table>"), ("0", "≥6", "0")),
           ("③ ⭐ **`\\n` を1つだけ本文へ刷る**(=第7巡が `_pending` の注記へ入れた形)"
            " — ⚠ **1件鳴る**",
            _d(doc + "<p>…恒真にした。\\n⛔ 次の文</p>"), ("1", "0", "0")),
           ("④ ⭐ **生のバッククォートを1対だけ本文へ刷る**(=本文 1,916 個の形)"
            " — ⚠ **2件鳴る**",
            _d(doc + "<p>正典は `svg_layout.plain()` である</p>"), ("2", "0", "0")),
           ("⑤ ⛔ **家の典拠記法 `[西川1959](A)` を刷る** — "
            "⛔ **鳴らない**(⚠ リンクに数えない・当図に 17 出現)",
            _d(doc + "<p>[西川1959](A) と [福井図](B・図の目測)</p>"), ("0", "0", "0")),
           ("⑥ ⛔⛔ **同じ6通りを `<code>` の中へ刷る** — ⛔ **欠陥としては鳴らない"
            "(既知の穴)**。⭕ ただし**引用の面では6件数える** — "
            "⚠ **除いた面を「数えていない」で済ませない**",
            _d(doc + "<p><code>" + six + "</code></p>"), ("0", "0", "≥6")),
           ("⑦ いまの紙(基準)— ⛔ **鳴らない**", _d(doc), ("0", "0", "0"))]
    return out


# ---------------------------------------------------------------- 字の物差し
def css_classes(path=CSS):
    """`sashizu.css` → {クラス名: (font-size, text-anchor, letter-spacing[em])}。"""
    t = open(path, encoding="utf-8").read()
    out = {}
    for m in _RE_RULE.finditer(t):
        body = m.group(2)
        fs = re.search(r"font-size:\s*([\d.]+)px", body)
        an = re.search(r"text-anchor:\s*(\w+)", body)
        ls = re.search(r"letter-spacing:\s*([\d.]+)em", body)
        if fs or an or ls:
            out[m.group(1)] = (float(fs.group(1)) if fs else None,
                               an.group(1) if an else None,
                               float(ls.group(1)) if ls else 0.0)
    return out


def css_fills(path=CSS):
    """`sashizu.css` → {クラス名: fill の宣言}。⛔ 色をここに書き写さない(CSS が正典)。"""
    t = open(path, encoding="utf-8").read()
    out = {}
    for m in _RE_RULE.finditer(t):
        f = re.search(r"fill:\s*([^;}]+)", m.group(2))
        if f:
            out[m.group(1)] = f.group(1).strip()
    return out


def css_vars(path=CSS):
    """`:root` の `--token` → 値。⛔ 図の色は CSS の変数で書かれているので、まずこれを解く。"""
    t = open(path, encoding="utf-8").read()
    m = re.search(r":root\s*\{([^}]*)\}", t, re.S)
    return {k: v.strip() for k, v in re.findall(r"--([\w-]+):\s*([^;]+);", m.group(1))} if m else {}


_VARS = [None]


def rgb(c, depth=0):
    """色の宣言 → (r, g, b)。⛔ **測れない色は None を返す**(⚠ 既定値へ倒さない)。

    ⚠ `url(#…)`(パターン)と `none` は **None** = 「色が無い/測れない」。
    """
    if _VARS[0] is None:
        _VARS[0] = css_vars()
    c = (c or "").strip()
    if not c or depth > 4:
        return None
    m = re.match(r"var\(--([\w-]+)\s*(?:,[^)]*)?\)", c)
    if m:
        return rgb(_VARS[0].get(m.group(1)), depth + 1)
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) != 6 or re.search(r"[^0-9a-fA-F]", h):
            return None
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r"rgba?\(([^)]*)\)", c)
    if m:
        v = [q.strip() for q in m.group(1).split(",")]
        if len(v) >= 3:
            try:
                return tuple(int(round(float(q))) for q in v[:3])
            except ValueError:
                return None
    return {"white": (255, 255, 255), "black": (0, 0, 0)}.get(c.lower())


def lum(c):
    """相対輝度(WCAG 2.x)。"""
    def f(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def cratio(a, b):
    """コントラスト比(1.0〜21.0)。"""
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _over(c, base, a):
    """`c` を不透明度 `a` で `base` の上へ重ねた色。"""
    return tuple(a * c[k] + (1.0 - a) * base[k] for k in range(3))


def _adv(ch):
    """1字の字送り[em]。⭐ 2026-09-08、検図方が 1,012 字面の実測から解き直した値。

    ⛔ **一般約物(— … ‥)を 0.5 と見誤っていた** — 実測 0.962 で **+92% の過小**。
    ⚠ 空白も 0.28 → 0.376、数字も 0.556 → 0.569 が実測。⭕ 安全側へ丸めて持つ。
    """
    o = ord(ch)
    if ch == " ":
        return 0.38                                # 実測 0.376
    if o < 0x300:                                  # 欧文・数字・約物
        if ch in ".,:;'`|!ilj()[]{}/\\-":
            return 0.32
        if ch.isdigit():
            return 0.57                            # 実測 0.569
        if ch.isupper():
            return 0.68
        return 0.56
    if 0x2000 <= o <= 0x206F:                      # 一般約物(— … ‥)
        return 1.0                                 # 実測 0.962 ⇒ 安全側へ 1.0
    if 0x2190 <= o <= 0x2BFF:                      # 記号(→ ⛔ ⭐ ⭕ ⚠ ①②)
        return 1.0
    return 1.0                                     # 和字・全角(実測 0.984)


def adv_px(ch, fs, ls=0.0):
    """1字ぶんの送り[px]。⛔ `text_w` と同じ安全率を掛ける(2つの物差しを持たない)。"""
    return fs * (_adv(ch) + ls) * SAFE * _WS[0]


def text_w(s, fs, ls=0.0):
    return fs * (sum(_adv(c) for c in s) + ls * max(0, len(s) - 1)) * SAFE * _WS[0]


def has_kana(s):
    """和字(仮名・漢字・全角)を含むか。⚠ 欧字と数字だけの識別子は下限の対象にしない。"""
    return any(0x3000 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF
               or 0xFF00 <= ord(c) <= 0xFFEF for c in s)


ASC, DESC = 0.78, 0.18     # 基線からの上下[em]


class Tx(object):
    """1個の `<text>`。"""

    __slots__ = ("i", "span", "att", "s", "cls", "fs", "an", "ls", "x", "y",
                 "lines", "drop", "moved", "x0", "y0", "par", "kept", "pin")

    def __init__(self, i, span, att, s, cls, fs, an, ls, x, y, par=-1):
        self.i, self.span, self.att, self.s = i, span, att, s
        # ⭐⭐ **`data-pin="1"` は「動かしてはいけない銘」**(2026-09-08 庭方 ⑵)。
        #   ⛔⛔ **丸の中の数字を寄せると、数字だけが丸から離れて浮く** — ⚠ 庭の主図で
        #   汀 #5 が**バッジ半径の 1.8 倍**離れ、空の白丸に別の銘が重なっていた。
        #   ⇒ ⭕ **先に置いて場所を主張し、当たった相手のほうを動かす。**
        self.pin = att.get("data-pin") == "1"
        self.cls, self.fs, self.an, self.ls = cls, fs, an, ls
        self.x, self.y = x, y
        self.x0, self.y0 = x, y      # ⭐ **もとの位置**(寄せた量はここからの差で数える)
        self.par = par               # 親の `<g>` の番号(-1 = svg 直下)
        self.lines = [s]
        self.drop = False
        self.kept = False        # 枠の外へ丸ごと出ていたが、他に無い銘なので落とさなかった
        self.moved = 0.0

    @property
    def lh(self):
        return self.fs * 1.18

    def w(self, s=None):
        return text_w(self.s if s is None else s, self.fs, self.ls)

    def box_of(self, s, y):
        w = self.w(s)
        x0 = self.x if self.an == "start" else (
            self.x - w / 2.0 if self.an == "middle" else self.x - w)
        return (x0, y - self.fs * ASC, x0 + w, y + self.fs * DESC)

    def char_boxes(self, s, y):
        """1字ずつの箱。⭐ **潜りは字ごとに測る** — ⚠ 「前庭 21.9」の『前庭』だけが
        塗りに隠れて『21.9』だけ残る、という消え方をするため。"""
        b = self.box_of(s, y)
        x = b[0]
        out = []
        for ch in s:
            w = adv_px(ch, self.fs, self.ls)
            out.append((ch, (x, b[1], x + w, b[3])))
            x += w
        return out

    def ys(self):
        """行ごとの基線 y。下端に近い文字は**上へ**積む(枠から落とさない)。"""
        n = len(self.lines)
        if n == 1:
            return [self.y]
        return [self.y - (n - 1 - k) * self.lh for k in range(n)]

    def boxes(self):
        return [self.box_of(s, y) for s, y in zip(self.lines, self.ys())]

    def eff(self, W):
        """基準の窓での実効 px。⚠ **窓がこれより狭ければさらに小さい**(測っていない)。"""
        return self.fs * VIEW_W / W


def parse(body, cls_tab, parents=None):
    out = []
    for i, m in enumerate(_RE_TXT.finditer(body)):
        a = dict(_RE_ATT.findall(m.group(1)))
        cls = a.get("class", "")
        fs, an, ls = cls_tab.get(cls, (None, None, 0.0))
        fs = fs or 12.0
        an = an or "start"
        st = a.get("style", "")
        m2 = re.search(r"font-size:\s*([\d.]+)px", st)
        if m2:
            fs = float(m2.group(1))
        m3 = re.search(r"text-anchor:\s*(\w+)", st)
        if m3:
            an = m3.group(1)
        par = parents.get(m.start(), -1) if parents else -1
        out.append(Tx(i, m.span(), a, _html.unescape(m.group(2)), cls, fs, an, ls,
                      float(a.get("x", 0.0)), float(a.get("y", 0.0)), par))
    return out


# ---------------------------------------------------------------- 図形の読み取り
_RE_EL = re.compile(r'<(text|rect|polygon|polyline|path|circle|line|use|g|/g|defs|/defs'
                    r'|clipPath|/clipPath|pattern|/pattern)\b([^>]*?)(/?)>', re.S)
_RE_NUM = re.compile(r'-?[\d.]+(?:[eE]-?\d+)?')


def _alpha(a):
    try:
        return float(a.get("opacity", 1.0) or 1.0) * float(a.get("fill-opacity", 1.0) or 1.0)
    except ValueError:
        return 1.0


def _poly_area(p):
    s = 0.0
    for i in range(len(p)):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % len(p)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _clip_box(poly, box):
    """Sutherland–Hodgman。⛔ 乱数もサンプリングも使わない(決定的・厳密)。"""
    x0, y0, x1, y1 = box
    edges = [(lambda q: q[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
             (lambda q: q[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
             (lambda q: q[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
             (lambda q: q[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1))]
    p = poly
    for ins, inter in edges:
        if not p:
            return []
        out = []
        n = len(p)
        for i in range(n):
            a, b = p[i], p[(i + 1) % n]
            ia, ib = ins(a), ins(b)
            if ia:
                out.append(a)
                if not ib:
                    out.append(inter(a, b))
            elif ib:
                out.append(inter(a, b))
        p = out
    return p


_BEZ_N = 12        # 曲線を折る数。⛔ 曲線を「測れない」で見逃さない(2026-09-08 検図方 中1)


def _bez(p, n=_BEZ_N):
    """de Casteljau で曲線を折線へ。`p` = 制御点(3点=2次 / 4点=3次)。⛔ 乱数を使わない。"""
    out = []
    for k in range(1, n + 1):
        t = k / float(n)
        q = list(p)
        while len(q) > 1:
            q = [((1 - t) * q[i][0] + t * q[i + 1][0], (1 - t) * q[i][1] + t * q[i + 1][1])
                 for i in range(len(q) - 1)]
        out.append(q[0])
    return out


def _path_polys(d):
    """path を多角形へ。⭐ **曲線(C/S/Q/T)も折って測る**(2026-09-08 検図方 中1)。

    ⛔⛔ 従前は曲線が出たら **None**(=測れない)を返し、⚠ 呼び側が `or []` で
    **「覆わない」に倒していた** — ⇒ **曲線を1つ含む塗りは検査を素通りできた**
    (検図方が変異 (d) で実証: 画素 0.00 = 完全に消えるのに 0 件)。
    ⚠ **円弧(A)だけはまだ測れない** — ⛔ 出たら None を返して申告する(当図には 0 本)。
    """
    toks = re.findall(r'[A-Za-z]|-?[\d.]+(?:[eE]-?\d+)?', d)
    polys, cur = [], []
    x = y = sx = sy = 0.0
    px = py = None                  # 直前の制御点(S/T の鏡像に要る)
    i, cmd = 0, None
    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t):
            cmd = t
            i += 1
            if cmd in ("Z", "z"):
                if cur:
                    polys.append(cur)
                    cur = []
                x, y = sx, sy
                continue
            if cmd in ("A", "a"):
                return None         # ⛔ 円弧は測れない — **黙って通さない**
            if cmd not in ("M", "m", "L", "l", "H", "h", "V", "v",
                           "C", "c", "S", "s", "Q", "q", "T", "t"):
                return None
            if i >= len(toks):
                break
        if cmd in ("C", "c", "S", "s", "Q", "q", "T", "t"):
            rel = cmd.islower()
            need = {"C": 6, "S": 4, "Q": 4, "T": 2}[cmd.upper()]
            v = [float(q) for q in toks[i:i + need]]
            if len(v) < need:
                break
            i += need
            pts = [(v[k], v[k + 1]) for k in range(0, need, 2)]
            if rel:
                pts = [(x + a, y + b) for a, b in pts]
            mirror = (2 * x - px, 2 * y - py) if px is not None else (x, y)
            if cmd.upper() == "C":
                c1, c2, e = pts
            elif cmd.upper() == "S":
                c1, (c2, e) = mirror, pts
            elif cmd.upper() == "Q":
                (c1, e), c2 = pts, None
            else:                                   # T = 2次の鏡像(制御点なし)
                c1, c2, e = mirror, None, pts[0]
            seg = ([(x, y), c1, c2, e] if c2 is not None else [(x, y), c1, e])
            if not cur:
                cur = [(x, y)]
            cur.extend(_bez(seg))
            px, py = (c2 or c1)
            x, y = e
            continue
        px = py = None
        if cmd in ("M", "m"):
            if cur:
                polys.append(cur)
                cur = []
            nx, ny = float(toks[i]), float(toks[i + 1])
            i += 2
            x, y = (nx, ny) if cmd == "M" else (x + nx, y + ny)
            sx, sy = x, y
            cur = [(x, y)]
            cmd = "L" if cmd == "M" else "l"
        elif cmd in ("L", "l"):
            nx, ny = float(toks[i]), float(toks[i + 1])
            i += 2
            x, y = (nx, ny) if cmd == "L" else (x + nx, y + ny)
            cur.append((x, y))
        elif cmd in ("H", "h"):
            nx = float(toks[i])
            i += 1
            x = nx if cmd == "H" else x + nx
            cur.append((x, y))
        elif cmd in ("V", "v"):
            ny = float(toks[i])
            i += 1
            y = ny if cmd == "V" else y + ny
            cur.append((x, y))
        else:
            return None
    if cur:
        polys.append(cur)
    return [p for p in polys if len(p) >= 3]


def _shape_polys(tag, a):
    """塗りとして紙を覆う多角形。⛔ 線(`line`)と塗り無しは覆わない。"""
    if tag == "rect":
        try:
            x, y = float(a.get("x", 0)), float(a.get("y", 0))
            w, h = float(a.get("width", 0)), float(a.get("height", 0))
        except ValueError:
            return []
        return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]] if w > 0 and h > 0 else []
    if tag in ("polygon", "polyline"):
        v = [float(q) for q in _RE_NUM.findall(a.get("points", ""))]
        p = list(zip(v[0::2], v[1::2]))
        return [p] if len(p) >= 3 else []
    if tag == "circle":
        try:
            cx, cy, r = float(a.get("cx", 0)), float(a.get("cy", 0)), float(a.get("r", 0))
        except ValueError:
            return []
        if r <= 0:
            return []
        return [[(cx + r * math.cos(k * math.pi / 12), cy + r * math.sin(k * math.pi / 12))
                 for k in range(24)]]
    if tag == "path":
        return _path_polys(a.get("d", "")) or []
    return []


def _outline(tag, a):
    """輪郭の頂点列(**線を帯にする**ため)。⛔ 閉じた図形は最後の辺も閉じる。"""
    if tag == "line":
        try:
            return [[(float(a.get("x1", 0)), float(a.get("y1", 0))),
                     (float(a.get("x2", 0)), float(a.get("y2", 0)))]]
        except ValueError:
            return []
    if tag == "polyline":
        v = [float(q) for q in _RE_NUM.findall(a.get("points", ""))]
        p = list(zip(v[0::2], v[1::2]))
        return [p] if len(p) >= 2 else []
    if tag == "path":
        return [p + [p[0]] if a.get("d", "").rstrip()[-1:] in ("Z", "z") else p
                for p in (_path_polys(a.get("d", "")) or [])]
    ps = _shape_polys(tag, a)
    return [p + [p[0]] for p in ps]


def _stroke_polys(tag, a):
    """**線が塗る帯**。⭐⭐ 2026-09-08 検図方 中1 — ⛔⛔ 従前は `line` を「覆わない物」として
    無条件に外しており、⚠ **当図に現に在る `stroke-width` 62.7px の道の帯**(95本)は
    銘を丸ごと消しても 0 件だった(検図方の変異 (a) は画素 0.00 = 完全に消えた)。
    ⇒ **太さを持つ線は紙を塗る。**⛔ 「線だから」で外さない。

    ⚠ 継ぎ目(join)は**頂点に一辺 `w` の正方形**を置いて塞ぐ(近似・安全側)。
    ⚠ **破線も帯として数える**(⛔ 「隙間があるから読める」とは言えない)= 安全側。
    """
    st = a.get("stroke", "")
    stl = a.get("style", "")
    m = re.search(r"(?:^|[;\s])stroke:\s*([^;\"]+)", stl)
    if m:
        st = m.group(1).strip()
    if st in ("", "none"):
        return []
    try:
        w = float(a.get("stroke-width", 1.0))
    except ValueError:
        w = 1.0
    if w < STROKE_MIN:
        return []
    out = []
    h = w / 2.0
    for pts in _outline(tag, a):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            dx, dy = x2 - x1, y2 - y1
            n = math.hypot(dx, dy)
            if n < 1e-9:
                continue
            ux, uy = -dy / n * h, dx / n * h
            out.append([(x1 + ux, y1 + uy), (x2 + ux, y2 + uy),
                        (x2 - ux, y2 - uy), (x1 - ux, y1 - uy)])
        for (qx, qy) in pts[1:-1]:                  # 継ぎ目を塞ぐ
            out.append([(qx - h, qy - h), (qx + h, qy - h), (qx + h, qy + h), (qx - h, qy + h)])
    return out


def _stroke_alpha(a):
    try:
        return float(a.get("opacity", 1.0) or 1.0) * float(a.get("stroke-opacity", 1.0) or 1.0)
    except ValueError:
        return 1.0


def _decl_fill(a):
    """`fill` の宣言。⭐ **`style` の中の `fill:` も拾う**(2026-09-08 検図方 中1 の変異 (c))。

    ⛔⛔ 従前は `fill` **属性**しか見ておらず、⚠ `style="fill:…"` で塗った矩形は
    銘を完全に消しても 0 件だった。
    """
    st = a.get("style", "")
    m = re.search(r"(?:^|[;\s])fill:\s*([^;\"]+)", st)
    return (m.group(1) if m else a.get("fill", "")).strip()


def _defs_els(body):
    """`id` を持つ図形(`<defs>` の中も外も)→ (tag, 属性)。⭐ `<use>` の解決に要る。"""
    out = {}
    for m in re.finditer(r'<(rect|polygon|polyline|path|circle|line)\b([^>]*?)/?>', body, re.S):
        a = dict(_RE_ATT.findall(m.group(2)))
        if a.get("id"):
            out[a["id"]] = (m.group(1), a)
    return out


def _shift(polys, dx, dy):
    return [[(x + dx, y + dy) for x, y in p] for p in polys]


def _signed_area(p):
    s = 0.0
    for i in range(len(p)):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % len(p)]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _wind(pt, ring):
    """巻き数(nonzero 判定用)。"""
    x, y = pt
    w = 0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if y1 <= y < y2 or y2 <= y < y1:
            xx = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xx > x:
                w += 1 if y2 > y1 else -1
    return w


def in_shape(pt, rings, rule="nonzero"):
    """⭐⭐ **穴のある図形を「塗ってある」と誤らない**(2026-09-08)。

    ⛔⛔ **1つの `path` の副輪郭(subpath)を別々の図形として数えていた** — ⚠ 当図の
    **区画の外を隠す面**は「外枠 + 逆回りの敷地」の 2 輪郭・`fill-rule="evenodd"` で、
    **敷地の中まで塗ってあることになっていた**。⇒ 銘の地色が紙色に見え、
    ⚠ **実際には濃い地の上に在る銘が「読める」と判定されていた**(其五「厩の郭 17.9」)。
    """
    if rule == "evenodd":
        return sum(1 for r in rings if _pip(pt, r)) % 2 == 1
    return sum(_wind(pt, r) for r in rings) != 0


def shape_clip_area(rings, box):
    """箱に掛かる塗りの面積。⚠ **穴は逆回り**なので符号つきで足して打ち消す。"""
    if len(rings) == 1:
        cp = _clip_box(rings[0], box)
        return _poly_area(cp) if cp else 0.0
    tot = 0.0
    for r in rings:
        cp = _clip_box(r, box)
        if cp:
            tot += _signed_area(cp)
    return abs(tot)


def paint_layers(els, defs=None):
    """**紙を塗り得る全要素**を描画順で返す — `[(描画順, 図形の列, 色 or None, 不透明度, 塗り規則)]`。

    ⚠ 1つの図形は**輪郭の列**(外と穴)を持つ — ⛔ 副輪郭をばらして別の図形にしない。

    ⭐⭐ 2026-09-08 検図方 中1 への答え。⛔⛔ 従前の条件は「`fill` **属性**を持つ非 `line` 要素」で、
    検図方が**抜け道を6通り実証**した(うち2通りは当図に現に在る形)。⇒ 口を4つ広げた:
      ⑴ **太い線**(`line`/`polyline`/輪郭)を帯として数える
      ⑵ **`style="fill:…"`** の塗り
      ⑶ **曲線(C/S/Q/T)を含む `path`** の塗り
      ⑷ **`<use>`** で貼った図形(`x`/`y` の平行移動まで)
    ⚠ **残る穴は正直に書く** — ⛔ 半透明の重ね掛け(1枚ずつは `ALPHA_MIN` 未満)と
      ⛔ 字の一部だけを覆う帯(`COVER_FR` 未満)、⛔ 円弧(`A`)、⛔ `transform` の群。
    """
    out = []

    def _put(i9, shapes, col, al, rule):
        sh = []
        for rings in shapes:
            xs = [q[0] for r in rings for q in r]
            ys = [q[1] for r in rings for q in r]
            if not xs:
                continue
            sh.append((rings, (min(xs), min(ys), max(xs), max(ys))))
        if sh:
            out.append((i9, sh, col, al, rule))

    for i9, e in enumerate(els):
        tag, _pos, a, _g = e
        if tag == "text":
            continue
        if tag == "use":
            ref = re.sub(r"^#", "", a.get("href", "") or a.get("xlink:href", ""))
            src = (defs or {}).get(ref)
            if not src:
                continue
            tag2, a2 = src
            try:
                dx, dy = float(a.get("x", 0)), float(a.get("y", 0))
            except ValueError:
                dx = dy = 0.0
            for shapes, col, al, rule in _one_layer(tag2, a2):
                _put(i9, [_shift(r, dx, dy) for r in shapes], col,
                     al * (float(a.get("opacity", 1.0) or 1.0)), rule)
            continue
        for shapes, col, al, rule in _one_layer(tag, a):
            _put(i9, shapes, col, al, rule)
    return out


def _one_layer(tag, a):
    """1要素が紙へ置く層 — `[(図形の列, 色, 不透明度, 塗り規則)]`。

    ⚠ **塗りは1図形(輪郭の列)**、⚠ **線の帯は1本ずつ別の図形**(重なりを打ち消さないため)。
    """
    lay = []
    f = _decl_fill(a)
    if f not in ("", "none") and tag != "line":
        pg = _shape_polys(tag, a)
        if pg:
            lay.append(([pg], rgb(f), _alpha(a), a.get("fill-rule", "nonzero")))
    sp = _stroke_polys(tag, a)
    if sp:
        st = a.get("stroke", "")
        m = re.search(r"(?:^|[;\s])stroke:\s*([^;\"]+)", a.get("style", ""))
        lay.append(([[q] for q in sp], rgb(m.group(1) if m else st),
                    _stroke_alpha(a), "nonzero"))
    return lay


def _scan_els(body):
    """面の中の要素を**描画順**で拾う。⛔ `<defs>/<pattern>/<clipPath>` の中は紙に出ない。

    戻り: `(els, parents, groups)`
      els     = [(tag, 位置, 属性, 親の番号)] — text も含む(描画順の照合に要る)
      parents = {text の開始位置: 親の番号}
      groups  = {番号: (開き札の属性, 閉じ札の位置)}
    """
    els, parents, groups = [], {}, {}
    stack, gid, indefs = [-1], 0, 0
    for em in _RE_EL.finditer(body):
        tag, astr = em.group(1), em.group(2)
        if tag in ("defs", "pattern", "clipPath"):
            indefs += 1
            continue
        if tag in ("/defs", "/pattern", "/clipPath"):
            indefs -= 1
            continue
        if indefs > 0:
            continue
        if tag == "g":
            gid += 1
            groups[gid] = (dict(_RE_ATT.findall(astr)), None)
            stack.append(gid)
            continue
        if tag == "/g":
            g = stack.pop()
            if g in groups:
                groups[g] = (groups[g][0], em.start())
            continue
        els.append((tag, em.start(), dict(_RE_ATT.findall(astr)), stack[-1]))
        if tag == "text":
            parents[em.start()] = stack[-1]
    return els, parents, groups


def _clip_defs(body):
    """`<clipPath id=…>` → その中身の文字列。"""
    return {m.group(1): m.group(2)
            for m in re.finditer(r'<clipPath[^>]*\bid="([^"]+)"[^>]*>(.*?)</clipPath>', body, re.S)}


def _group_open(att, clips, W, H):
    """その `<g>` から銘を**外へ出してよい**か。

    ⭕ 出してよいのは「紙の見え方を変えない群」だけ — ⛔ `transform`/`opacity`/`mask`/
    `filter`/`style` を持つ群からは出さない。⚠ `clip-path` は**枠いっぱいの矩形**なら
    (= 単に画枠で切っているだけなので)出してよい。
    """
    for k in att:
        if k not in ("clip-path", "id", "class"):
            return False
    cp = att.get("clip-path", "")
    if not cp:
        return True
    m = re.match(r'url\(#([^)]+)\)', cp)
    if not m or m.group(1) not in clips:
        return False
    inner = clips[m.group(1)]
    rs = re.findall(r'<rect\b([^>]*)>', inner)
    if len(rs) != 1 or "<path" in inner or "<polygon" in inner or "<circle" in inner:
        return False
    a = dict(_RE_ATT.findall(rs[0]))
    try:
        x, y = float(a.get("x", 0)), float(a.get("y", 0))
        w, h = float(a.get("width", 0)), float(a.get("height", 0))
    except ValueError:
        return False
    return x <= 0.01 and y <= 0.01 and x + w >= W - 0.01 and y + h >= H - 0.01


# ---------------------------------------------------------------- 是正
_BRK = "、。・)】」』/ →—"          # ここの直後で折る


def wrap(t, avail):
    """幅 `avail` に収まるよう折り返す。⛔ 語の途中で折るのは最後の手段。

    ⚠ **文中の改行は硬い折れ目**として先に割る(和文の注記に素で入っている)。
    """
    if "\n" in t.s:
        out = []
        for seg in t.s.split("\n"):
            out.extend(_wrap1(t, seg.strip(), avail) if seg.strip() else [""])
        return [x for x in out if x != ""] or [t.s]
    return _wrap1(t, t.s, avail)


def _wrap1(t, s0, avail):
    if text_w(s0, t.fs, t.ls) <= avail or avail < t.fs * 3:
        return [s0]
    lines, cur, last = [], "", -1
    for ch in s0:
        if text_w(cur + ch, t.fs, t.ls) > avail and cur:
            if last > 0 and last < len(cur) - 1:
                lines.append(cur[:last + 1])
                cur = cur[last + 1:]
            else:
                lines.append(cur)
                cur = ""
            last = -1
        cur += ch
        if ch in _BRK:
            last = len(cur) - 1
    if cur:
        lines.append(cur)
    return lines or [s0]


def clamp(t, W, H):
    """箱が枠に収まるよう x と y を寄せる(寄せ方は変えない)。"""
    bs = t.boxes()
    dx = 0.0
    lo = min(b[0] for b in bs) + dx
    hi = max(b[2] for b in bs) + dx
    if lo < PAD:
        dx += PAD - lo
    hi = max(b[2] for b in bs) + dx
    if hi > W - PAD:
        dx -= hi - (W - PAD)
    if min(b[0] for b in bs) + dx < PAD:            # 幅が枠より広い(折れなかった)
        dx = PAD - min(b[0] for b in bs)
    t.x += dx
    ys = t.ys()
    dy = 0.0
    if min(ys) - t.fs * ASC < PAD:
        dy = PAD - (min(ys) - t.fs * ASC)
    if max(ys) + t.fs * DESC + dy > H - PAD:
        dy = (H - PAD) - (max(ys) + t.fs * DESC)
    t.y += dy


def _ov(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _hits(bs, placed):
    return sum(_ov(a, b) for a in bs for b in placed)


def deoverlap(ts, W, H):
    """当たったら**縦へ寄せる**。⛔ 乱数を使わない(決定的)。

    ⭐ 置く順は**幅の広い順**(同幅は文書順)。⚠ 文書順に置くと、最後に来る長い注記が
    先に置かれた短い銘に阻まれて**動く先を失う** — 動かすべきは短い銘のほうである。
    """
    placed = []
    for t in ts:                     # ⭐ **釘付けの銘が先に場所を取る**(⛔ 動かさない)
        if not t.drop and t.pin:
            placed.extend(t.boxes())
    for t in sorted([q for q in ts if not q.drop and not q.pin],
                    key=lambda q: (-max(b[2] - b[0] for b in q.boxes()), q.i)):
        if not _hits(t.boxes(), placed):
            placed.extend(t.boxes())
            continue
        base_y, base_x = t.y, t.x
        cands = []
        for k in range(1, 9):                       # まず縦へ(1/2 行ずつ)
            for sg in (1, -1):
                cands.append((0.0, sg * k * t.lh * 0.5))
        for k in range(1, 9):                       # それでも駄目なら横も
            for sg in (1, -1):
                for dy in (0.0, t.lh, -t.lh, 2 * t.lh, -2 * t.lh):
                    cands.append((sg * k * 6.0, dy))
        for k in range(9, 61):                      # 最後は縦へ大きく探す
            for sg in (1, -1):
                cands.append((0.0, sg * k * t.lh * 0.5))
        best, bestpen = None, None
        for dx, dy in cands:
            t.x, t.y = base_x + dx, base_y + dy
            clamp(t, W, H)
            pen = _hits(t.boxes(), placed)
            d = abs(t.x - base_x) + abs(t.y - base_y)
            if pen <= 0.0:
                best = (t.x, t.y)
                break
            if bestpen is None or (pen, d) < bestpen:
                bestpen, best = (pen, d), (t.x, t.y)
        t.x, t.y = best
        placed.extend(t.boxes())


def _emit(t):
    att = dict(t.att)
    out = []
    for s, y in zip(t.lines, t.ys()):
        a = '<text'
        for k in ("class", "x", "y", "style"):
            if k == "x":
                a += ' x="%.1f"' % t.x
            elif k == "y":
                a += ' y="%.1f"' % y
            elif k in att:
                a += ' %s="%s"' % (k, att[k])
        for k, v in att.items():
            if k not in ("class", "x", "y", "style"):
                a += ' %s="%s"' % (k, v)
        out.append(a + ">%s</text>" % _html.escape(s, quote=False))
    return "".join(out)


def _fig_strings(doc, tab):
    """面ごとの字面の集合。⭐ **落としてよいかの判定に要る** — 枠外へ丸ごと出た字でも、
    ⛔ **その銘が他の面のどこにも無ければ、落とすと情報が消える。**"""
    out = []
    for m in _RE_SVG.finditer(doc):
        out.append(set(t.s for t in parse(m.group(4), tab)))
    return out


def _near_shape(box, boxes, r=REF_NEAR):
    """箱の近く(距離 `r` 以内)に**何か描かれている**か。⭐ 銘は指す物の脇に置かれる。"""
    for b in boxes:
        dx = max(b[0] - box[2], box[0] - b[2], 0.0)
        dy = max(b[1] - box[3], box[1] - b[3], 0.0)
        if math.hypot(dx, dy) <= r:
            return True
    return False


def relayout(doc, cls_tab=None):
    """重なり・枠外・潜り・**読めない色**を潰した文書を返す。⭕ 冪等(2度掛けても同じ)。"""
    tab = cls_tab or css_classes()
    figstr = _fig_strings(doc, tab)
    rep = {"dropped": 0, "wrapped": 0, "moved": 0, "grown": 0, "figs": 0,
           "droppedList": [], "movedMax": 0.0, "movedFar": 0,
           "kept": 0, "keptList": [], "keptMoveMax": 0.0,
           "reordered": 0, "reordFigs": 0,
           "orphan": 0, "orphanList": [],
           "halo": 0, "haloFigs": 0, "haloResid": 0, "haloResidList": []}
    out, at = [], 0
    for m in _RE_SVG.finditer(doc):
        W, H = float(m.group(2)), float(m.group(3))
        body = m.group(4)
        els, parents, groups = _scan_els(body)
        clips = _clip_defs(body)
        ts = parse(body, tab, parents)
        # ⭐ **この面に物が描かれている所**(= 銘の指す先が在り得る所)。
        #   ⛔⛔ **紙の外へ出た図形は「描かれている」に数えない** — ⚠ svg は枠で切るので、
        #   枠外の図形は**読者には見えない**。⇒ **枠と交わる分だけを、枠で切って持つ。**
        #   (⚠ これを入れないと、枠外へ落ちた銘のすぐ隣に**同じく枠外の図形**が在るせいで
        #    「指す物が在る」と誤判定する。)
        drawn = []
        for _i9, shapes, _c, _al, _rule in paint_layers(els, _defs_els(body)):
            for _rings, bb in shapes:
                if bb[2] < 0 or bb[0] > W or bb[3] < 0 or bb[1] > H:
                    continue
                drawn.append((max(bb[0], 0.0), max(bb[1], 0.0),
                              min(bb[2], W), min(bb[3], H)))
        rep["figs"] += 1
        fi = rep["figs"] - 1
        for t in ts:
            b = t.box_of(t.s, t.y)
            if b[2] < 0 or b[0] > W or b[3] < 0 or b[1] > H:
                # ⭐⭐ **枝は三つ**(2026-09-08 検図方 中2)。⛔⛔ 「落とすか拾うか」の二択が
                #   誤りだった — ⚠ **拾い上げた銘が、指す物の無い白紙の上に朱で浮いていた**
                #   (其十二 断面⑲: 面に描かれていない棟の谷の銘が地盤の 500 単位上に着地)。
                #   ⚠ 朱は指摘色なので、**白紙の上の朱は「ここに問題がある」と読まれる**。
                #   ⇒ ① 他の面に同じ銘が在れば落とす(情報は消えない)
                #      ② **拾う前に、元の位置の近くに物が描かれているかを見る** —
                #        何も描かれていなければ**指す物がこの面に無い**ので、拾わずに落とす(誤配)
                #      ③ どちらでもなければ枠内へ拾う。
                #   ⚠ **順は「落とす条件が先」** — ⛔ 誤配の枝を先に置くと、
                #     ①で落ちるはずの銘まで誤配に数えてしまい、二つの壊れ方が混ざる。
                elsewhere = any(t.s in s for j, s in enumerate(figstr) if j != fi)
                if elsewhere:
                    t.drop = True
                    rep["dropped"] += 1
                    rep["droppedList"].append((rep["figs"], t.s))
                    continue
                if not _near_shape(b, drawn):
                    t.drop = True
                    rep["orphan"] += 1
                    rep["orphanList"].append((rep["figs"], t.s))
                    continue
                t.kept = True
                rep["kept"] += 1
                rep["keptList"].append((rep["figs"], t.s))
            t.lines = wrap(t, W - 2 * PAD)
            if len(t.lines) > 1:
                rep["wrapped"] += 1
        # ⭐ **下端の注記が折れた分だけ枠を下へ伸ばす。** ⛔ 図の上へ被せて逃げない —
        #   折った注記を絵の上に積むと、字は読めても**絵が読めなくなる**。
        grow = sum((len(t.lines) - 1) * t.lh for t in ts
                   if not t.drop and len(t.lines) > 1 and t.y > H - 3 * t.lh)
        if grow:
            for t in ts:
                if not t.drop and t.y > H - 3 * t.lh:
                    t.y += grow
                    t.y0 += grow          # ⚠ 枠を伸ばした分は「寄せた」に数えない
            H = float(math.ceil(H + grow))   # ⚠ viewBox は整数で出す(丸めで冪等が崩れる)
            rep["grown"] += 1
        for t in ts:
            if not t.drop:
                clamp(t, W, H)
        deoverlap(ts, W, H)
        # ⭐⭐ **「寄せた」は最初の位置からの実移動で数える**(2026-09-08 検図方 中4)。
        #   ⛔⛔ 従前は `deoverlap` の移動だけを数え、**`clamp`(枠内へ押し込む横移動)を
        #   数えていなかった** — ⚠ 押し込みのほうが「銘が指す物から離れる」危険は大きい。
        #   ⚠ **枠の外から拾い上げた銘は別勘定**にする — 何百 px も動くのは当たり前で、
        #   ⛔ 混ぜると「寄せの最大」が読めなくなる(上の行が別に数えている)。
        for t in ts:
            if t.drop:
                continue
            t.moved = abs(t.x - t.x0) + abs(t.y - t.y0)
            if t.kept:
                rep["keptMoveMax"] = max(rep["keptMoveMax"], t.moved)
                continue
            if t.moved > 0.05:
                rep["moved"] += 1
        rep["movedMax"] = max([rep["movedMax"]]
                              + [t.moved for t in ts if not t.drop and not t.kept])
        rep["movedFar"] += sum(1 for t in ts if not t.drop and not t.kept and t.moved > 40.0)
        # ⭐⭐ **銘は最後にまとめて描く**(2026-09-08 検図方 高2)。
        #   ⛔⛔ 従前は作図した順のまま出していたので、**後から描く面の塗りが銘を上塗り**して
        #   いた(f08 は面の高さの銘が5つまるごと不可視)。⇒ 面の末尾へ送る。
        #   ⚠ **紙の見え方を変える群**(transform/opacity/mask など)からは出さない。
        keep_in = {}
        tail = []
        for t in ts:
            if t.drop:
                continue
            g = t.par
            if g != -1 and not _group_open(groups.get(g, ({}, None))[0], clips, W, H):
                keep_in.setdefault(g, []).append(t)
            else:
                tail.append(t)
        rep["reordered"] += len(tail)
        acts = [(t.span[0], t.span[1], None) for t in ts]
        for g, lst in keep_in.items():
            p = groups[g][1]
            if p is not None:
                acts.append((p, p, lst))
        acts.sort(key=lambda a: a[0])
        nb, prev = [], 0
        for a0, a1, lst in acts:
            nb.append(body[prev:a0])
            if lst:
                nb.append("".join(_emit(q) for q in lst))
            prev = a1
        nb.append(body[prev:])
        nb.append("".join(_emit(q) for q in tail))
        if tail:
            rep["reordFigs"] += 1
        out.append(doc[at:m.start()])
        head = m.group(1)
        if H != float(m.group(3)):
            head = head.replace('viewBox="0 0 %s %s"' % (m.group(2), m.group(3)),
                                'viewBox="0 0 %s %.0f"' % (m.group(2), H))
        out.append(head + "".join(nb) + m.group(5))
        at = m.end()
    out.append(doc[at:])
    return haloize("".join(out), tab, rep), rep


# ---------------------------------------------------------------- 読めない色を直す
_RE_HALO = re.compile(r"paint-order:stroke;stroke:[^;\"]+;stroke-width:[\d.]+px;?")
_RE_TAG = re.compile(r'<text\b[^>]*>')


def _strip_halo(body):
    """**この道具が当てたフチ**(`data-halo`)だけ外す。⛔ 作図が手で入れたフチは触らない。"""
    def f(mm):
        s = mm.group(0)
        if 'data-halo="1"' not in s:
            return s
        s = s.replace(' data-halo="1"', '')
        s = _RE_HALO.sub("", s)
        return s.replace(' style=""', '').replace(';"', '"')
    return _RE_TAG.sub(f, body)


def haloize(doc, tab=None, rep=None):
    """⭐⭐ **地色に沈んだ銘へ白フチを回す**(2026-09-08 検図方 高2)。

    ⛔⛔ **前巡「潜り」から救い出した銘が、読めない色に着地していた** — 宣言色 × 直下の地色の
    コントラスト比が **1.04**(ほぼ同色)の銘まで在った。⚠ **「墨が乗っている」は「読める」ではない。**
    ⭐ 直しは**一つずつ色を選ばない** — ⛔ 手で選んだ色は次に地色が動けばまた沈む。
    ⇒ **下限(`CR_MIN`)を割った銘に、字の色から見て遠いほうの地(紙 or 墨)でフチを回す。**
    ⚠ フチは**字を囲って地から切り離す**ので、以後その銘の地色は**フチの色**になる
    (`text_contrast` はそう読む)。⛔ 下の塗りの色を変えたのではない。
    ⭕ 冪等 — 当てたフチには `data-halo="1"` の印が付き、次の巡で外してから測り直す。
    """
    tab = tab or css_classes()
    fills = css_fills()
    cands = [c for c in (rgb("var(--paper)"), rgb("var(--ink)")) if c]
    out, at = [], 0
    for m in _RE_SVG.finditer(doc):
        body = _strip_halo(m.group(4))
        els, parents, _g = _scan_els(body)
        ts = parse(body, tab, parents)
        layers = paint_layers(els, _defs_els(body))
        order = {e[1]: i9 for i9, e in enumerate(els) if e[0] == "text"}
        edits, n9 = [], 0
        for t in ts:
            if halo_of(t) is not None:              # 作図が手で入れたフチ
                continue
            w9 = text_contrast(t, order.get(t.span[0], 0), layers, fills)
            if w9 is None or w9[0] >= CR_MIN - 1e-9:
                continue
            col = w9[1]
            hl = max(cands, key=lambda c: cratio(col, c)) if cands else (255, 255, 255)
            wpx = min(HALO_W[1], max(HALO_W[0], t.fs * HALO_FS))
            frag = "paint-order:stroke;stroke:#%02X%02X%02X;stroke-width:%.1fpx" % (
                hl[0], hl[1], hl[2], wpx)
            tag = body[t.span[0]:t.span[1]]
            head = tag[:tag.index(">") + 1]
            if 'style="' in head:
                nh = head.replace('style="', 'style="%s;' % frag, 1)
            else:
                nh = head[:-1].rstrip("/") + ' style="%s"' % frag + head[-1:]
            nh = nh[:-1].rstrip("/") + ' data-halo="1"' + nh[-1:]
            edits.append((t.span[0], t.span[0] + len(head), nh))
            n9 += 1
            if rep is not None and cratio(col, hl) < CR_MIN - 1e-9:
                rep["haloResid"] += 1
                rep["haloResidList"].append((cratio(col, hl), t.s))
        for a0, a1, s in sorted(edits, reverse=True):
            body = body[:a0] + s + body[a1:]
        if rep is not None:
            rep["halo"] += n9
            rep["haloFigs"] += 1 if n9 else 0
        out.append(doc[at:m.start()])
        out.append(m.group(1) + body + m.group(5))
        at = m.end()
    out.append(doc[at:])
    return "".join(out)


# ---------------------------------------------------------------- 検査
def check(doc, cls_tab=None):
    """⛔ 直した後の文書を測る。返すのは**件数と実例**。

    測るのは六つ — ⑴ 字どうしの重なり ⑵ 枠の外 ⑶ **塗りに潜った銘** ⑷ **小さすぎる字**
    ⑸ **地色との コントラストが下限を割る銘**(2026-09-08 検図方 高2)
    ⑹ **文書の記法が字になって刷られた銘**(2026-09-08 検図方 中1)。
    """
    tab = cls_tab or css_classes()
    fills = css_fills()
    ov, of, cv, tn, lc, mk, figs, nt = [], [], [], [], [], [], 0, 0
    unmeas = ami = 0
    for m in _RE_SVG.finditer(doc):
        figs += 1
        W, H = float(m.group(2)), float(m.group(3))
        body = m.group(4)
        els, parents, groups = _scan_els(body)
        ts = parse(body, tab, parents)
        tpos = {t.span[0]: t for t in ts}
        layers = paint_layers(els, _defs_els(body))
        bs = []
        for t in ts:
            for b in t.boxes():
                bs.append((b, t.s))
            if has_kana(t.s) and t.eff(W) < MIN_EFF - 1e-9:
                tn.append((figs, t.eff(W), t.s))
            hm = markup_hits(t.s)          # ⑹ **記法が字になっている**
            if hm:
                mk.append((figs, "/".join(hm), t.s))
        nt += len(bs)
        for j in range(len(bs)):
            for k in range(j + 1, len(bs)):
                a = _ov(bs[j][0], bs[k][0])
                if a > MIN_AREA:
                    ov.append((figs, a, bs[j][1], bs[k][1]))
        for b, s in bs:
            d = max(-b[0], -b[1], b[2] - W, b[3] - H)
            if d > TOL:
                of.append((figs, d, s))
        # ⑶ **潜り** — 描画順で自分より後ろにある不透明な塗りが、字の箱を覆っているか。
        #   ⛔ **z 順は文書順**(親の群は関係ない)ので、群の中の銘も外の塗りに覆われる。
        paints = [(i9, sh, rule) for i9, sh, _c, al, rule in layers if al >= ALPHA_MIN]
        for i9, e in enumerate(els):
            if e[0] != "text":
                continue
            t = tpos.get(e[1])
            if t is None:
                continue
            for line, y in zip(t.lines, t.ys()):
                cb = t.char_boxes(line, y)
                hit = []
                for j9, shapes, _rule in paints:
                    if j9 <= i9:
                        continue
                    for rings, bb in shapes:
                        if (bb[2] < cb[0][1][0] or bb[0] > cb[-1][1][2]
                                or bb[3] < cb[0][1][1] or bb[1] > cb[0][1][3]):
                            continue
                        for k9, (ch, box) in enumerate(cb):
                            if k9 in hit or ch == " ":
                                continue
                            ar = (box[2] - box[0]) * (box[3] - box[1])
                            if ar <= 0:
                                continue
                            if shape_clip_area(rings, box) / ar >= COVER_FR:
                                hit.append(k9)
                if hit:
                    cv.append((figs, line, len(hit), len(line),
                               "".join(cb[k9][0] for k9 in sorted(set(hit)))))
            # ⑸ **コントラスト** — 宣言色 × **その字の直下の地色**(重ねを合成して解く)。
            w9 = text_contrast(t, i9, layers, fills)
            if w9 is None:
                unmeas += 1                    # ⛔ 宣言色そのものが解けない(0 件のはず)
                continue
            if w9[3]:
                ami += 1                       # ⚠ 網掛けの下の色で測った
            if w9[0] < CR_MIN - 1e-9:
                lc.append((figs, w9[0], t.s, w9[1], w9[2]))
    return {"figs": figs, "texts": nt, "overlap": ov, "outframe": of,
            "covered": cv, "tiny": tn, "lowcr": lc, "markup": mk,
            "unmeas": unmeas, "ami": ami,
            "ovFigs": len(set(x[0] for x in ov)),
            "ofFigs": len(set(x[0] for x in of)),
            "cvFigs": len(set(x[0] for x in cv)),
            "tnFigs": len(set(x[0] for x in tn)),
            "lcFigs": len(set(x[0] for x in lc)),
            "mkFigs": len(set(x[0] for x in mk))}


def text_fill(t, fills):
    """その銘の**宣言色**。⛔ 既定へ倒さない — 解けなければ None(=測れないと申告)。"""
    st = t.att.get("style", "")
    m = re.search(r"(?:^|[;\s])fill:\s*([^;\"]+)", st)
    c = (m.group(1).strip() if m else t.att.get("fill") or fills.get(t.cls) or "#000000")
    return rgb(c)


def halo_of(t):
    """白フチ(`paint-order:stroke`)の色。⛔ 細い縁取りは「フチ」と呼ばない。"""
    st = t.att.get("style", "")
    if "paint-order" not in st or "stroke" not in st:
        return None
    m = re.search(r"(?:^|[;\s])stroke:\s*([^;\"]+)", st)
    w = re.search(r"stroke-width:\s*([\d.]+)", st)
    if not m or (w and float(w.group(1)) < 2.0):
        return None
    return rgb(m.group(1).strip())


def backdrop(box, i9, layers, base=None):
    """箱の中心の**直下の地色** → `(色, 網掛けが掛かっていたか)`。

    描画順で自分より前の層を**合成**して解く。⛔ 不透明な層で打ち切らない —
    ⚠ 半透明の重ねは実際に地色を変える。
    ⭐ **色の解けない層(`url(#…)` の網掛け)は「地色」に数えず、下の色をそのまま採る** —
      ⚠ 当図の網掛けは **0.8px の線を 9px 間隔で引いた疎な刻み**(石垣・斜路)なので、
      **下の色が透ける**。⛔ ただし**測れなかったことは隠さない** — 第2の戻り値で申告し、
      図がその件数を刷る。
    """
    px, py = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    cur = base if base is not None else rgb("var(--paper2)") or (255, 255, 255)
    amimi = False
    for j9, shapes, col, al, rule in layers:
        if j9 >= i9 or al <= 0.004:
            continue
        for rings, bb in shapes:
            if px < bb[0] or px > bb[2] or py < bb[1] or py > bb[3]:
                continue
            if not in_shape((px, py), rings, rule):
                continue
            if col is None:
                amimi = True
                break
            cur = _over(col, cur, min(1.0, al))
            break
    return cur, amimi


def _pip(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x1 + (y - y1) * (x2 - x1) / (y2 - y1) > x:
                inside = not inside
    return inside


def text_contrast(t, i9, layers, fills):
    """その銘の**いちばん悪い**コントラスト比 → `(比, 宣言色, 地色)`。⛔ 平均で均さない。

    ⭐ **字ごとに測る** — ⚠ 「厩の郭 17.9」の『厩の郭』だけが暗い塗りに乗る、という沈み方をする。
    ⭐ **白フチが在れば地色はフチの色** — フチが字を紙色で囲うので、下の塗りには依らない。
    ⚠ 第4の値は「**網掛けの下の色で測った**」の印(⛔ 測れなかったことを隠さない)。
    """
    col = text_fill(t, fills)
    if col is None:
        return None
    hl = halo_of(t)
    if hl is not None:
        return (cratio(col, hl), col, hl, False)
    worst, ami = None, False
    for line, y in zip(t.lines, t.ys()):
        for ch, b in t.char_boxes(line, y):
            if ch == " ":
                continue
            bg, a9 = backdrop(b, i9, layers)
            ami = ami or a9
            v = cratio(col, bg)
            if worst is None or v < worst[0]:
                worst = (v, col, tuple(int(round(q)) for q in bg))
    return None if worst is None else (worst + (ami,))


def counts(r):
    """`check` の六つの件数。⛔ 順を他所で並べ替えない。"""
    return (len(r["overlap"]), len(r["outframe"]), len(r["covered"]), len(r["tiny"]),
            len(r.get("lowcr", ())), len(r.get("markup", ())))


# ---------------------------------------------------------------- 破壊試験
def probes(doc, raw=None, cls_tab=None):
    """⭐⭐ **この検査が生きていることを毎回見せる**(規則19)。

    ⛔⛔ **「0 件」だけを刷ると、検査が死んでいても 0 と読める。**⇒ ⭕ 直した文書へ
    **わざと欠陥を差し込み**、鳴ることを確かめる。⛔ 乱数を使わない(決定的)。
    返すのは `[(題, 実測(重なり, 枠外, 潜り, 小字), 期待)]`。

    ⚠ `raw` = **直す前**の文書。⭐ 「推定幅を 0.95 倍する」束はこれが要る —
    ⛔ 直した後の図を 0.95 で組み直しても、`clamp` は内へしか押さないので鳴らない。
    """
    tab = cls_tab or css_classes()
    out = []
    m = _RE_SVG.search(doc)
    if m is None:
        return [("⛔ 図版が1面も無い — **この検査は回っていない**", (-1, -1, -1, -1, -1, -1),
                 ("0", "0", "0", "0", "0", "0"))]
    W, H, body = float(m.group(2)), float(m.group(3)), m.group(4)
    ts = parse(body, tab)
    if len(ts) < 2:
        return [("⛔ 1面目の字面が2つ未満 — **試験を差し込めない**", (-1, -1, -1, -1, -1, -1),
                 ("0", "0", "0", "0", "0", "0"))]
    a, b = ts[0], ts[1]

    def _mut(nb):
        dc = doc[:m.start()] + m.group(1) + nb + m.group(5) + doc[m.end():]
        return counts(check(dc, tab))

    def _repl(span, s):
        return body[:span[0]] + s + body[span[1]:]

    # ① 1つ目の字面を2つ目の**真上へ重ねる** ⇒ 重なりが鳴る
    out.append(("① ⭐ 1つ目の字面を2つ目の**真上へ重ねる** — ⚠ **重なりが鳴る**",
                _mut(_repl(a.span, '<text class="%s" x="%.1f" y="%.1f" style="%s">%s</text>'
                           % (b.cls, b.x, b.y, "text-anchor:%s" % b.an,
                              _html.escape(b.s, quote=False)))),
                ("≥1", "0", "0", "0", "—", "0")))
    # ② 1つ目の字面を**枠の外へ出す** ⇒ 枠外が鳴る
    out.append(("② ⭐ 1つ目の字面を**枠の外へ出す** — ⚠ **枠外が鳴る**",
                _mut(_repl(a.span, '<text class="%s" x="%.1f" y="%.1f" style="%s">%s</text>'
                           % (a.cls, W + 40.0, a.y, "text-anchor:start",
                              _html.escape(a.s, quote=False)))),
                ("0", "≥1", "0", "0", "—", "0")))
    # ③ ⭐⭐ 1つ目の銘の上へ**不透明な塗りを後から被せる** ⇒ 潜りが鳴る
    ab = a.box_of(a.s, a.y)
    out.append(("③ ⭐⭐ 1つ目の銘の上へ**不透明な塗りを後から被せる**"
                "(=2026-09-08 まで 10 件あった消え方)— ⚠ **潜りが鳴る**",
                _mut(body + '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                            'fill="var(--paper)" opacity="1.00"/>'
                            % (ab[0] - 1, ab[1] - 1, (ab[2] - ab[0]) + 2, (ab[3] - ab[1]) + 2)),
                ("0", "0", "≥1", "0", "—", "0")))
    # ④ ⭐⭐ 1つ目の銘を**下限より小さく**する ⇒ 小字が鳴る
    out.append(("④ ⭐⭐ 1つ目の銘を**字送りの下限より小さく**する — ⚠ **小字が鳴る**",
                _mut(_repl(a.span, '<text class="%s" x="%.1f" y="%.1f" style="font-size:%.1fpx">'
                           '%s</text>' % (a.cls, a.x, a.y, MIN_EFF * W / VIEW_W * 0.5,
                                          _html.escape("室名の見本", quote=False)))),
                ("0", "0", "0", "≥1", "—", "0")))
    # ⑤ ⭐⭐ **推定幅を 0.95 倍して組み直す** ⇒ 枠外が鳴る
    #    ⛔⛔ この巡に実際に残った régime(幅を 5% 見誤る)を鳴らす束が一つも無かった。
    if raw is not None:
        _WS[0] = 0.95
        try:
            d95, _ = relayout(raw, tab)
        finally:
            _WS[0] = 1.0
        out.append(("⑤ ⭐⭐ **推定幅を 0.95 倍して組み直す**"
                    "(=一般約物を 0.5em と見誤っていた régime)— ⚠ **枠外が鳴る**",
                    counts(check(d95, tab)), ("—", "≥1", "0", "0", "—", "0")))
    # ⑥〜⑨ ⭐⭐⭐ **検図方が実証した「潜りの抜け道」**(2026-09-08 中1)。
    #   ⛔⛔ 従前の `paints` は「`fill` 属性を持つ非 `line` 要素」だけを見ており、
    #   ⚠ **6通りのうち4通りは画素で 0.00(=銘が完全に消える)のに 0 件**だった。
    #   ⚠⚠ そのうち **2通りは当図に現に在る形**(太い線 95本・曲線を含む塗り 1本)。
    #   ⇒ ここで**その4通りを毎回差す**。⛔ 鳴らなくなったら口が閉じている。
    R = (ab[0] - 1, ab[1] - 1, (ab[2] - ab[0]) + 2, (ab[3] - ab[1]) + 2)
    out.append(("⑥ ⭐⭐ **太い線で銘を塗りつぶす**(検図方の変異 (a)・当図に 95 本ある形)"
                "— ⚠ **潜りが鳴る**",
                _mut(body + '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--paper)"'
                            ' stroke-width="%.1f"/>'
                            % (R[0], (ab[1] + ab[3]) / 2.0, R[0] + R[2],
                               (ab[1] + ab[3]) / 2.0, R[3] + 2)),
                ("0", "0", "≥1", "0", "—", "0")))
    out.append(("⑦ ⭐⭐ **`style=\"fill:…\"` の矩形で覆う**(変異 (c))— ⚠ **潜りが鳴る**",
                _mut(body + '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                            'style="fill:#FBFAF6"/>' % R),
                ("0", "0", "≥1", "0", "—", "0")))
    out.append(("⑧ ⭐⭐ **曲線(`C`)を含む `path` の塗りで覆う**(変異 (d)・当図に 1 本ある形)"
                "— ⚠ **潜りが鳴る**",
                _mut(body + '<path d="M%.1f,%.1f H%.1f C%.1f,%.1f %.1f,%.1f %.1f,%.1f Z" '
                            'fill="var(--paper)"/>'
                            % (R[0], R[1], R[0] + R[2], R[0] + R[2], R[1] + R[3],
                               R[0], R[1] + R[3], R[0], R[1])),
                ("0", "0", "≥1", "0", "—", "0")))
    out.append(("⑨ ⭐⭐ **`<use>` で矩形を貼る**(変異 (f))— ⚠ **潜りが鳴る**",
                _mut(body + '<defs><rect id="pz9" x="0" y="0" width="%.1f" height="%.1f" '
                            'fill="var(--paper)"/></defs><use href="#pz9" x="%.1f" y="%.1f"/>'
                            % (R[2], R[3], R[0], R[1])),
                ("0", "0", "≥1", "0", "—", "0")))
    # ⑩ ⭐⭐ **地色に沈んだ銘** ⇒ コントラストが鳴る
    out.append(("⑩ ⭐⭐ 1つ目の銘を**地色とほぼ同じ色**にする(⛔ フチ無し)"
                "— ⚠ **コントラストが鳴る**",
                counts(check(_strip_halo(doc[:m.start()] + m.group(1) + body + m.group(5)
                                         + doc[m.end():]).replace(
                    body[a.span[0]:a.span[1]],
                    '<text class="%s" x="%.1f" y="%.1f" style="fill:#F2F0E8">%s</text>'
                    % (a.cls, a.x, a.y, _html.escape(a.s, quote=False)), 1), tab)),
                ("—", "—", "—", "—", "≥1", "0")))
    # ⑪⑫ ⛔⛔ **この物差しが鳴らないと分かっている形**(= 限界の明示。検図方の変異 (b)(e))。
    #   ⛔ 「0 件」を合格と読ませないために、**鳴らないことを期待値として刷る**。
    out.append(("⑪ ⛔⛔ **半透明(0.45)を3枚重ねて覆う**(変異 (b)・画素では 0.43 まで薄まる)"
                "— ⛔ **この物差しでは鳴らない(既知の穴)**",
                _mut(body + ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                             'fill="var(--paper)" opacity="0.45"/>' % R) * 3),
                ("0", "0", "0", "0", "—", "0")))
    out.append(("⑫ ⛔⛔ **字の中央 55% だけを帯で覆う**(変異 (e)・画素では 0.41)"
                "— ⛔ **この物差しでは鳴らない(既知の穴・`COVER_FR` 未満)**",
                _mut(body + '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                            'fill="var(--paper)"/>'
                            % (R[0], ab[1] + (ab[3] - ab[1]) * 0.225, R[2],
                               (ab[3] - ab[1]) * 0.55)),
                ("0", "0", "0", "0", "—", "0")))
    # ⑬⑭ ⭐⭐⭐ **文書の記法が図へ漏れる**(2026-09-08 検図方 中1)。
    #   ⛔⛔ **この一対が無いと、⑹「記法 0 件」は `plain()` が剥がすからそう出る数**に
    #   すぎない(= 恒真)。⇒ ⭕ **⑬は `plain()` を通さない生の `<text>`** を差して
    #   **口が開いていること**を、⭕ **⑭は同じ字を `plain()` に通して**
    #   **変換が生きていること**を、毎回別々に鳴らす。
    #   ⚠ 差した銘は場所も色も選んでいないので、**記法の欄以外は不問(「—」)**。
    _MKS = ["凡例=<b>江戸期の復元地盤</b>", "&lt;b&gt; と &#98;",
            "**太い字**", "点線の円=`at` の半径の帯", "[題](http://x)"]

    def _inject(ss):
        return body + "".join(
            '<text class="%s" x="%.1f" y="%.1f" style="text-anchor:start">%s</text>'
            % (a.cls, PAD, PAD + 12.0 * (k + 1), _html.escape(q, quote=False))
            for k, q in enumerate(ss))

    def _inject_raw(ss):
        """⛔ **escape せずに差す** — ⚠ 実体参照の腕は「生の口がそのまま出した形」でしか
        試せない(`escape` を通すと `&` が `&amp;` になって別の形になってしまう)。"""
        return body + "".join(
            '<text class="%s" x="%.1f" y="%.1f" style="text-anchor:start">%s</text>'
            % (a.cls, PAD, PAD + 12.0 * (k + 1), q) for k, q in enumerate(ss))
    out.append(("⑬ ⭐⭐⭐ **記法(タグ/実体参照/太字/引用符/リンク)の5通りを "
                "`plain()` を通さずに紙へ刷る** — ⚠ **記法が5件鳴る**",
                _mut(_inject(_MKS)), ("—", "—", "—", "—", "—", "≥5")))
    out.append(("⑭ ⭐⭐⭐ **同じ5通りを `plain()` に通して刷る** — "
                "⛔ **鳴らない(鳴ったら変換のほうが壊れている)**",
                _mut(_inject([plain(q) for q in _MKS])),
                ("—", "—", "—", "—", "—", "0")))
    # ⑮⑯ ⭐⭐⭐ **「実体参照」の腕は、限界の明示が「ほんとうに働く」と言った場所では
    #   働かない**(2026-09-08 第7巡・検図方 低1)。⛔⛔ `parse()` は字面を `unescape()` して
    #   から測るので、⚠ **生の口が正しく出した実体参照は解決され、腕に当たらない**。
    #   ⚠⚠ 第7巡に `&lt;b&gt;` が鳴ったのは**タグの腕**であって、この腕ではなかった
    #   = **1腕ぶん過大に申告していた。**⇒ ⭕ **この一対で口を名指す** —
    #   この腕がほんとうに捕まえるのは**二重にエスケープされた**実体参照だけである。
    out.append(("⑮ ⛔⛔ **正しい実体参照 `&nbsp;` を生のまま紙へ刷る** — "
                "⛔ **鳴らない(既知の穴)**。⚠ `parse()` の `unescape()` が解いてしまう",
                _mut(_inject_raw(["余白&nbsp;100 m"])), ("—", "—", "—", "—", "—", "0")))
    out.append(("⑯ ⭐⭐ **二重にエスケープした `&amp;nbsp;` を生のまま紙へ刷る** — "
                "⚠ **鳴る**(⇒ ⭕ この腕が捕まえるのは**この形だけ**である)",
                _mut(_inject_raw(["余白&amp;nbsp;100 m"])), ("—", "—", "—", "—", "—", "≥1")))
    # ⑰ 触らない ⇒ 鳴らない
    out.append(("⑰ いまの図(基準)— ⛔ **鳴らない**", counts(check(doc, tab)),
                ("0", "0", "0", "0", "0", "0")))
    return out


def probe_ok(rows):
    """`probes` / `doc_markup_probes` の各行が期待どおりか(⚠ 列の数には依らない)。
    ⛔ 期待は「≥N」「0」「—」(不問)の語で持つ。

    ⚠ **「—」は逃げ道ではない** — その束が**その筋では鳴ると言い切れない**ときだけ使う
    (例: 幅を 0.95 倍して組み直すと、枠外だけでなく重なりも副次的に出る)。
    ⭐ **「≥N」は N 件以上**(⛔ 「≥1」で済ませない — 5通りの記法を差す束は
    **5通りとも鳴ることまで**言い切る。1件だけ鳴って通ると、⚠ 残る4つの口が閉じていても
    合格に見える)。
    """
    out = []
    for title, got, want in rows:
        ok = all(True if w == "—" else
                 (g >= int(w[1:]) if w.startswith("≥") else g == int(w))
                 for g, w in zip(got, want))
        out.append((title, got, want, ok))
    return out


if __name__ == "__main__":
    import sys
    doc = open(sys.argv[1], encoding="utf-8").read()
    r0 = check(doc)
    print("直す前: 重なり %d 組 / 枠外 %d 件 / 潜り %d 件 / 小字 %d 件 / 低コントラスト %d 件"
          " / 記法 %d 件" % counts(r0))
    doc2, rep = relayout(doc)
    r1 = check(doc2)
    print("直した後: 重なり %d 組 / 枠外 %d 件 / 潜り %d 件 / 小字 %d 件 / 低コントラスト %d 件"
          " / 記法 %d 件 ・ %s" % (counts(r1) + (rep,)))
    for x in sorted(r1.get("lowcr", []))[:15]:
        print("  CR  f%02d %.2f  %s  (字 #%02X%02X%02X / 地 #%02X%02X%02X)"
              % ((x[0], x[1], x[2][:30]) + tuple(x[3]) + tuple(x[4])))
    for x in sorted(r1["overlap"], key=lambda z: -z[1])[:15]:
        print("  OV f%02d %8.1f  %s || %s" % (x[0], x[1], x[2][:30], x[3][:30]))
    for x in sorted(r1["outframe"], key=lambda z: -z[1])[:15]:
        print("  OUT f%02d %8.1f  %s" % (x[0], x[1], x[2][:40]))
    for x in r1["covered"][:15]:
        print("  COV f%02d %d/%d  %s" % (x[0], x[2], x[3], x[1][:40]))
    for x in sorted(r1["tiny"])[:20]:
        print("  TNY f%02d %.2fpx  %s" % (x[0], x[1], x[2][:40]))
    for x in r1["markup"][:20]:
        print("  MRK f%02d %-8s %s" % (x[0], x[1], x[2][:50]))
    doc3, _ = relayout(doc2)
    print("冪等: %s" % ("⭕" if doc3 == doc2 else "⛔ 2度目で変わった"))
    # ⚠ ここでは `raw` に**直した後の図**しか渡せない(この入口は完成した html を読むため)
    #   ⇒ **束⑤は必ず落ちる**。⭕ 生成器の中では直す前の文書が渡るので通る。
    for t, g, w, ok in probe_ok(probes(doc2, doc)):
        print("  %s %s 実測%s 期待%s%s"
              % ("⭕" if ok else "⛔", t[:44], g, w,
                 "  ⚠ この入口では束⑤だけは落ちて正しい" if (not ok and t.startswith("⑤")) else ""))
