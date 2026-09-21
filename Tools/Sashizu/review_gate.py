#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""検図関門 — 指図が「誰に検められたか」を機械で見張る。

【なぜ要るか】2026-09-01、松江松平邸の庭が**庭方(edo-niwashi)に一度も検められないまま
Stage7 まで実装され**、ユーザーから「この指図でよいとは全く思っていない」と差し戻された。
検図(kenzu)と考証(kosho)は通していたが、**庭の良し悪しを見る目は通していなかった**。
CLAUDE.md のルーティング表に edo-niwashi は載っていたのに、**通さなくても何も起きなかった**
のが原因。⛔ 散文の規則は破れる。関門は機械にする。

さらに同じ日、庭の**再設計**を指図方(edo-sashizukata)へ回しかけてユーザーに止められた。
指図方は「意匠上の判断はしない・書き起こすだけ」の役で、庭を設計する能力はない。
⭕ 正しい順は **庭方が設計 → 指図方が数値へ書き起こす → 検図・考証・庭方が検める**。

【仕組み】各 `docs/Sashizu/<屋敷>_sashizu.json` の直下に `reviews` を置く:

    "reviews": {
      "kenzu":   {"at": "2026-08-23", "verdict": "pass", "hash": "<16桁>", "note": "..."},
      "kosho":   {"at": "2026-08-31", "verdict": "pass", "hash": "<16桁>"},
      "niwashi": {"at": "2026-09-01", "verdict": "fail", "hash": "<16桁>", "note": "..."}
    }

・**誰が要るか**は指図の中身から決まる(庭があれば庭方が要る)。名簿を人が書き足す必要はない
・`hash` は**その検分が見た範囲の中身**の指紋。指図を書き換えると hash がずれ、
  検分は自動で **stale(検め直しが要る)** になる。⛔ 通ったことにして先へ進めない
・検分役は read-only なので自分で書けない。**呼んだ側(普請奉行)が結果を書き戻す**義務がある

【使い方】
    python3 Tools/Sashizu/review_gate.py              # 全邸の関門を見る(赤があれば exit 1)
    python3 Tools/Sashizu/review_gate.py matsudaira_dewa
    python3 Tools/Sashizu/review_gate.py --record matsudaira_dewa niwashi fail "庭の主景と園路が無い"
    python3 Tools/Sashizu/review_gate.py --quiet     # 赤の要約だけ(セッション開始の挨拶用)
    python3 Tools/Sashizu/review_gate.py --changed doi   # 前回の記録以降に変わった章(検分役へ渡す)
    python3 Tools/Sashizu/review_gate.py --rounds doi    # 三巡則の見張り(門番が呼ぶ・exit 2 で止める)
    python3 Tools/Sashizu/review_gate.py --ack doi "裁定1=A"   # ユーザーの発話で巡を reset
    python3 Tools/Sashizu/review_gate.py --checks        # 邸ごとの機械検査の本数(乖離の見える化)

⭐ **効くのは実装前まで(2026-09-19 施主裁定2=A)。** 実装の車線に入った敷地(`kansei_gate.py --init` で
`<邸>_kansei.json` が在る)ではこの関門は鳴らず、完成条件の表が関門になる。指摘は建つ姿を変える物だけ。

⛔ **関門が赤の指図を実装しない。赤のシーンをユーザーに見せない。**

⚠ **【移行期間】2026-09-01 ユーザー裁定(案B)。** この関門は 2026-09-01 の新設で、
全6邸が赤で立ち上がった(赤17件)。⛔ 全員を即時停止させない — 赤の大半は
「関門が新しくて記録が無い」だけで、土井は検図14巡・岡部は検図12巡を実際に通している。
  ⭕ 検分を通すまで、従来どおり作業を続けてよい(実装・指図の改訂とも)
  ⛔ ただし**新たにユーザーへ見せる前には必ず通す**(裁定を仰ぐ・レンダを出す・
     指図の Artifact を案内する、のすべて)。ここが移行中も動かない一線
  ⛔ 「記録が無い」は「通していない」ではない。⛔ それでも遡って pass を書かない
     (過去の検分はいまの指図を見ていない)
正典: CLAUDE.md 絶対規則18 / 展開は EDO-0099。

【2026-09-13 追加(計画 B-1/B-2)】
・**章の指紋** — `reviews.<役>.chapters` に top-level key ごとの指紋を残す。
  `--changed <屋敷>` が「前回の記録以降に変わった章」を役ごとに刷る。検分役にはこれを渡し、
  変わった章と前巡の指摘の解消だけを人の目で検めさせる(機械検査は生成器が全件走らせる)。
・**三巡則を機械で** — `reviews.<役>.rounds` に record の履歴。ユーザーの最後の発話
  (`.git/edo-session/<sid>.json` の last_user、門番が刻む)より後に同じ役の fail が 3 回続いたら、
  `--rounds` が exit 2 を返し(門番が検分役の呼び出しを止める)、4 回目の `--record … fail` も拒む。
  reset はユーザーの発話か `--ack <屋敷> "<発話の引用>"`。
  実測(2026-09-13): 山王 8 巡・土井 6 巡・松江松平 4 巡がユーザー入力なしに連なっていた。
"""
import json
import os
import sys
import hashlib
import collections
import datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(REPO, "docs", "Sashizu")


def _doc_path(name):
    """その邸の指図の**いま生きている実体**を返す。

    ⛔ **main だけを見てはいけない。** 各邸は `.claude/worktrees/<邸>/` で作業しており、
    検分の結果(`reviews`)はそこへ書かれる。main へマージするまで反映されないので、
    main だけ見ると「通したのに赤のまま」になり、関門が形骸化する
    (2026-09-01 実測: 山王は worktree で庭方=pass・考証/検図=fail を記録済みなのに、
    関門は3件とも「記録が無い」と表示していた)。
    ⚠ フックは main の絶対パスでこの道具を呼ぶので、cwd では判断できない。

    ⭕ **新しい方を採る。** worktree と main の両方にあれば、`reviews` の `at`(検分の日)が
    新しい側を正とする。同じなら worktree(作業中の実体)を採る。
    """
    main_fp = os.path.join(DOC, name + "_sashizu.json")
    wt_fp = os.path.join(REPO, ".claude", "worktrees", name,
                         "docs", "Sashizu", name + "_sashizu.json")
    if not os.path.exists(wt_fp):
        return main_fp
    if not os.path.exists(main_fp):
        return wt_fp

    def _newest(fp):
        try:
            rv = (json.load(open(fp)).get("reviews") or {})
        except Exception:
            return ""
        return max([v.get("at", "") for v in rv.values()] or [""])

    return wt_fp if _newest(wt_fp) >= _newest(main_fp) else main_fp


def estate_names():
    """main と worktree の両方から邸の名を集める(worktree だけにある邸も拾う)。"""
    names = set()
    for f in os.listdir(DOC):
        if f.endswith("_sashizu.json"):
            names.add(f[: -len("_sashizu.json")])
    wt_root = os.path.join(REPO, ".claude", "worktrees")
    if os.path.isdir(wt_root):
        for d in os.listdir(wt_root):
            if os.path.exists(os.path.join(wt_root, d, "docs", "Sashizu",
                                           d + "_sashizu.json")):
                names.add(d)
    return sorted(names)

# 検分役 → (日本語名, その役が見る範囲のキー, いつ要るか)
#   keys=None は「指図全体」。required は指図の中身を受け取って True/False を返す
REVIEWERS = collections.OrderedDict([
    ("kenzu", dict(
        label="検図(edo-kenzu)",
        keys=None,
        # ⭐ **生成器と文章も指紋に混ぜる**(2026-09-02・松江松平 検図 低7)。
        #   ⛔ json だけを見ていると、**壊れているのが `.py` の配線や `kosho.md` の文**の
        #   ときに関門をそのまま通る(実際に3度起きた — 図が `main()` から呼ばれていない/
        #   検査が報告経路を持たない/撤回済みの主張が md に残って公開されている)。
        files=("py", "md"),
        why="図として成立しているか(重なり・断面・造成・柱割り・建蔽率)",
        required=lambda d: True)),
    ("kosho", dict(
        label="考証(edo-kosho)",
        keys=None,
        files=("py", "md"),
        why="史実・典拠・確度",
        required=lambda d: True)),
    ("niwashi", dict(
        label="庭方(edo-niwashi)",
        # ⚠ **庭方が見る範囲は「植栽と園路」だけではない。**2026-09-01 に松江松平で、
        #   池・水の系・築山・庭の断面・主視点・中仕切の規則が指紋のキーに入っておらず、
        #   ⛔ **いま壊れている物がちょうどこの穴に落ちた**(指図を書き換えても検分が
        #   「検め直し」にならなかった)。⭕ 庭の意匠が載るキーはすべて入れる。
        keys=["gardens", "planting", "plantRule", "tenkei",
              "slopeArea", "slopePlanting", "routes",
              "sensui", "mizu", "tsukiyama", "gardenSections",
              "viewpoints", "nakajikiriRule"],
        # ⚠ 庭方は**範囲キー**を持つので按分する — `kosho.md` は庭方の範囲外(考証の文章)、
        #   `.py` は庭の検査と図版そのものなので入れる。
        files=("py",),
        why="庭が庭として成立しているか(主景・見所・園路・作庭の作法・植栽の時代考証)",
        required=lambda d: _needs_niwashi(d))),
])


# ⚠ **キーの有無だけで判定しない**(2026-09-01 松平セッションの指摘)。
#   「庭・植栽・点景のどれかがあれば」だけだと、**庭の実体はあるのに点景しか書いていない
#   段階の指図**で要求が立たない — 一番検分が要る時期に関門がすり抜ける。
#   ⭕ 「この敷地に庭があるか」を、書きかけでも拾える手がかりから判断する。
_NIWA_HINTS = ("gardens", "planting", "plantRule", "tenkei", "slopePlanting", "slopeArea")
# 棟・郭・区域の**名前**に現れる、庭の存在を示す語(書きかけでも拾える)
#   ⛔ 「池」は入れない — 外堀の題「溜**池**堰下流」のような**地名**を拾ってしまう。
#      庭の池は「泉水」「主庭」など別の語で必ず現れるので、取りこぼしにはならない。
_NIWA_WORDS = ("庭", "泉水", "築山", "露地", "茶室", "稲荷", "園路", "枯山水")


def _walk_names(o):
    """指図の中の**名前らしい値**だけを辿る。題・説明文・典拠の引用は見ない
    (⚠ 本文まで見ると『溜池』のような地名や、史料の引用文で誤検出する)。"""
    if isinstance(o, dict):
        for k, v in o.items():
            if k.startswith("_"):
                continue
            if k in ("name", "ja", "label", "title") and isinstance(v, str):
                yield v
            else:
                for x in _walk_names(v):
                    yield x
    elif isinstance(o, list):
        for v in o:
            for x in _walk_names(v):
                yield x


def _needs_niwashi(d):
    """庭方が要るか。⚠ **キーの有無だけで決めない**(2026-09-01 松平セッションの指摘)—
    「庭の実体はあるのに点景しか書いていない段階」で要求が立たず、
    一番検分が要る時期に関門がすり抜ける。"""
    # ① 庭まわりのキーが1つでも埋まっていれば要る
    if any(d.get(k) for k in _NIWA_HINTS):
        return True
    # ② キーが空でも、棟・郭・区域の**名前**に庭を示す語があれば要る
    #    ⛔ title は除く(「溜池堰下流 外堀 掘り直し指図」で誤検出するため)
    for nm in _walk_names({k: v for k, v in d.items() if k != "title"}):
        if any(w in nm for w in _NIWA_WORDS):
            return True
    return False

VERDICTS = ("pass", "fail", "advisory")


def _side_digest(name, path, files):
    """指図と一緒に検分される**外の実体**の指紋(生成器の `.py` と文章の `kosho.md`)。

    ⛔ **json だけを指紋にすると、壊れているのが `.py` や `.md` のときに関門を素通りする**
      (2026-09-02・松江松平 検図 低7)。実例が3つある — ①図が `main()` から呼ばれず
      artifact に出ない ②検査が報告経路を持たず素の設計を一度も報告しない
      ③撤回済みの主張が `kosho.md` に残ったまま html に公開される。どれも json は正しかった。

    ⚠ 根は**指図の実体と同じ側**を採る(worktree で作業していれば worktree の `.py` / `.md`)。
    ⚠ 無い実体は `-` として混ぜる(有→無の変化も指紋を動かす)。"""
    sep = os.sep + "docs" + os.sep
    root = path.split(sep)[0] if sep in path else REPO
    out = []
    for kind in files or ():
        fp = (os.path.join(root, "Tools", "Sashizu", "build_%s_sashizu.py" % name)
              if kind == "py" else
              os.path.join(root, "docs", "Sashizu", "%s_kosho.md" % name))
        if kind == "py" and not os.path.exists(fp):        # 2026-09-20 以降は共通の生成器
            fp = os.path.join(root, "Tools", "Sashizu", "build_sashizu.py")
        if os.path.exists(fp):
            with open(fp, "rb") as f:
                out.append(kind + ":" + hashlib.sha256(f.read()).hexdigest()[:16])
        else:
            out.append(kind + ":-")
    return out


def _drop_notes(v):
    """`_` で始まるキーを**入れ子まで**落とす。

    ⚠ **2026-09-21 まで top-level しか落としていなかった**(EDO-0330)。docstring は当初から
    「文章を直しただけで検め直しを要求すると関門が形骸化する」と述べていたのに、実装は
    章の中の `_` を指紋に入れていた — 意図と実装のずれ。指図の文章を `<邸>_notes/` へ
    切り出す普請(2026-09-21 施主指示)で表に出た。
    ⭕ 入れ子まで落とせば、**文章をどこへ置き換えても検分は動かない**(土井・岡部・外堀で実証)。
    ⛔ 値は一つも落とさない — 落ちるのは `_` で始まるキーだけ。"""
    if isinstance(v, dict):
        return {k: _drop_notes(x) for k, x in v.items() if not str(k).startswith("_")}
    if isinstance(v, list):
        return [_drop_notes(x) for x in v]
    return v


def fingerprint(doc, keys, name=None, path=None, files=(), legacy=False):
    """検分が見た範囲の指紋。⚠ `_` で始まる注記のキーは**入れ子まで除く** —
    文章を直しただけで検め直しを要求すると、関門がすぐ形骸化する。
    `legacy=True` は 2026-09-21 以前の式(top-level の `_` しか除かない)。
    記録済みの hash を突き合わせるためだけに残す — 新たに書く指紋は常に新しい式。
    ⛔ **`reviews` 自身も除く。** 除かないと自己矛盾になる — record() が reviews を
    書き込むたびに指紋が動き、書いた直後から「検め直しが要る」に戻ってしまう
    (2026-09-01、丹羽セッションが実測: 検図→考証と2件記録したら両方とも無効化され、
    3役を同時に緑にすることが原理的に不可能だった。EDO-0101)。
    検分は指図の中身を見るもので、検分の記録簿そのものを見るものではない。"""
    if keys is None:
        src = {k: v for k, v in doc.items() if not k.startswith("_") and k != "reviews"}
    else:
        src = {}
        for k in keys:
            if k in doc:
                src[k] = doc[k]
        if not src:
            # ⛔ **空の指紋は全邸で同じ定数になる。** 庭方が要ると判定されたのに庭のキーが
            #   まだ1つも無い段階(棟や郭の名前だけで庭が現れている段階)で pass を記録すると、
            #   以後どれだけ庭が育っても指紋が動かず「通っている」ままになる。
            #   ⭕ 見る範囲が空なら指図全体で採る(=何か変われば検め直しになる)。
            #   2026-09-01 の点検で見つけた、EDO-0101 と同じ「関門が形骸化する」型の穴。
            return fingerprint(doc, None, name, path, files, legacy)
    if not legacy:
        src = _drop_notes(src)
    blob = json.dumps(src, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if name and path:
        blob += "|" + "|".join(_side_digest(name, path, files))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def still_valid(recorded, want, doc, spec, name, path):
    """記録された指紋が、いまの指図をまだ覆っているか。

    ⭐ **旧い式(2026-09-21 以前)で一致するなら、その記録はまだ有効**(EDO-0330)。
    旧い式は「値 + 入れ子の文章」を見ていた。それが一致するということは**値も文章も
    当時のまま**ということなので、新しい式(値だけ)も必ず一致する。
    ⇒ 式を変えた日に全邸を赤へ落とさずに済む(松江松平は完成・山王は緑だった)。
    ⛔ **逆は成り立たない。**新しい式だけが合う記録(=文章だけが動いた)は
    上の `recorded == want` が先に拾うので、ここへは来ない。
    記録は次に検分を通したとき新しい式で上書きされる(遅延移行)。"""
    if recorded == want:
        return True
    return recorded == fingerprint(doc, spec["keys"], name, path,
                                   spec.get("files", ()), legacy=True)


def chapter_prints(doc, keys, name=None, path=None, files=()):
    """章(top-level key)ごとの指紋。`_` 注記(**入れ子まで**)と reviews は除く。
    生成器・文章は "py"/"md" の擬似章。⚠ 入れ子まで除くのは 2026-09-21 から(EDO-0330) —
    文章だけを直した章が「変わった章」に挙がると、検分が毎回そこを読み直す。"""
    out = collections.OrderedDict()
    src = [k for k in doc if not k.startswith("_") and k != "reviews"]
    if keys is not None:
        src = [k for k in keys if k in doc] or src
    for k in src:
        blob = json.dumps(_drop_notes(doc[k]), ensure_ascii=False,
                          sort_keys=True, separators=(",", ":"))
        out[k] = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
    if name and path:
        for item in _side_digest(name, path, files):
            kind, h = item.split(":", 1)
            out[kind] = h
    return out


SESS_DIR = os.path.join(REPO, ".git", "edo-session")


def _last_user_ts():
    """ユーザーの最後の発話(ISO)。自分のセッションの刻印を優先し、無ければ全刻印の最新。"""
    best = ""
    mine = None
    try:
        sys.path.insert(0, os.path.join(REPO, "Tools", "Session"))
        from edo_session import sid
        mine = sid(strict=False)
    except Exception:
        pass
    if not os.path.isdir(SESS_DIR):
        return ""
    for fn in os.listdir(SESS_DIR):
        if not fn.endswith(".json"):
            continue
        try:
            ts = json.load(open(os.path.join(SESS_DIR, fn), encoding="utf-8")).get("last_user") or ""
        except Exception:
            continue
        if mine and fn[:-5] == mine:
            return ts
        best = max(best, ts)
    return best


def _reset_ts(doc):
    ack = (doc.get("_rounds_ack") or {}).get("at", "")
    return max(_last_user_ts(), ack)


def consecutive_fails(doc, key):
    """reset 以降に同じ役の fail が何回続いているか。"""
    since = _reset_ts(doc)
    hist = ((doc.get("reviews") or {}).get(key) or {}).get("rounds") or []
    n = 0
    for h in reversed(hist):
        if h.get("at", "") <= since:
            break
        if h.get("verdict") == "fail":
            n += 1
        else:
            break
    return n


ROUND_MAX = 3


def cmd_rounds(name):
    """門番用。同じ役の fail が ROUND_MAX 回続いていれば exit 2。"""
    path = _doc_path(name)
    doc = json.load(open(path))
    bad = []
    for key, spec in REVIEWERS.items():
        n = consecutive_fails(doc, key)
        print("  %-22s ユーザー入力なしの fail %d 回" % (spec["label"], n))
        if n >= ROUND_MAX:
            bad.append(spec["label"])
    if bad:
        print("⛔ 三巡則: %s が %d 巡続けて不合格。4 巡目に入らない — `decision` か `blocker` を post して"
              "手を止め、ユーザーの返事の後に再開する(reset は発話か `--ack`)。" % ("・".join(bad), ROUND_MAX))
        return 2
    return 0


def cmd_checks():
    """邸ごとの機械検査の本数(計画 B-7 の「刷り」)。検査は各生成器の関数として個別に生えており、
    中央の表が無い(2026-09-13 実測: 松江松平 109 / 土井 72 / 岡部 57 / 山王 56 / 京極 1)。
    本数の乖離をここで見える化する。横展開の禁止則(verification-loops.md)は変えない。"""
    import re as _re
    rows = []
    for est in estate_names():
        fp = os.path.join(REPO, "Tools", "Sashizu", "build_%s_sashizu.py" % est)
        if not os.path.exists(fp):
            fp = os.path.join(REPO, "Tools", "Sashizu", "build_sashizu.py")   # 共通の生成器(2026-09-20)
        if not os.path.exists(fp):
            continue
        src = open(fp, encoding="utf-8", errors="replace").read()
        n = len(_re.findall(r"^def \w+_check\(", src, _re.M)) or len(_re.findall(r"^    def c\d\d\(self\)", src, _re.M))
        rows.append((est, n, src.count("\n")))
    print("機械検査の本数(def *_check)  邸 | 本数 | 生成器の行数")
    for est, n, ln in sorted(rows, key=lambda r: -r[1]):
        print("  %-18s %4d | %6d" % (est, n, ln))
    if rows:
        ns = [r[1] for r in rows]
        print("  ⇒ 最多/最少 = %d 倍。検査が多い邸ほど 1 巡の指摘が増え、巡が伸びる。" % (max(ns) // max(1, min(ns))))
    return 0


def cmd_ack(name, quote):
    path = _doc_path(name)
    doc = json.load(open(path), object_pairs_hook=collections.OrderedDict)
    doc["_rounds_ack"] = collections.OrderedDict([
        ("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
        ("quote", quote[:200])])
    with open(path, "w") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("ack: %s の巡カウンタを reset(引用: %s)" % (name, quote[:60]))
    return 0


def cmd_changed(name, as_json=False):
    """前回の記録以降に変わった章を役ごとに刷る(検分役へ渡す)。"""
    path = _doc_path(name)
    doc = json.load(open(path))
    rev = doc.get("reviews") or {}
    out = collections.OrderedDict()
    for key, spec in REVIEWERS.items():
        if not spec["required"](doc):
            continue
        now = chapter_prints(doc, spec["keys"], name, path, spec.get("files", ()))
        old = (rev.get(key) or {}).get("chapters")
        if not old:
            out[key] = dict(all=True, changed=list(now), note="章の記録が無い(初回は全章)")
            continue
        ch = [k for k, v in now.items() if old.get(k) != v] + [k for k in old if k not in now]
        out[key] = dict(all=False, changed=ch, unchanged=len([k for k in now if k not in ch]))
    if as_json:
        print(json.dumps(out, ensure_ascii=False))
        return 0
    print("変わった章 — %s(前回の記録以降)" % name)
    for key, o in out.items():
        lab = REVIEWERS[key]["label"]
        if o.get("all"):
            print("  %-22s 全章(%s)" % (lab, o["note"]))
        elif o["changed"]:
            print("  %-22s %s ／ 変わっていない章 %d" % (lab, ", ".join(o["changed"]), o["unchanged"]))
        else:
            print("  %-22s 変更なし(検め直し不要)" % lab)
    print("  ⭐ 検分役には「変わった章」と前巡の指摘(review_ledger.py)の解消だけを人の目で検めさせる。"
          "機械検査(*_check)は生成器が全件走らせる。")
    return 0


def _kansei_sides(name, sashizu_path):
    """完成条件の表の在りかの候補 — 指図と同じ側・main・その邸の worktree。実在する物だけ返す。"""
    cand = [os.path.join(os.path.dirname(sashizu_path), "%s_kansei.json" % name),
            os.path.join(DOC, "%s_kansei.json" % name),
            os.path.join(REPO, ".claude", "worktrees", name, "docs", "Sashizu",
                         "%s_kansei.json" % name)]
    seen, out = set(), []
    for p in cand:
        rp = os.path.realpath(p)
        if rp in seen or not os.path.exists(p):
            continue
        seen.add(rp)
        out.append(p)
    return out


def _kansei_phase(name, sashizu_path):
    """完成条件の表の phase。表が無ければ design(= この関門が効く)。

    ⛔ **指図と同じ側だけを見てはいけない。**表(`--init`)は main へ書かれるのに、指図は
    worktree の方が新しければそちらが採られる(`_doc_path`)。同じ側しか見ないと、
    **実装へ入った邸に紙の巡を要求し続ける**(2026-09-21 実測: 山王は 2026-09-19 の
    施主裁定Aで実装へ入り main に phase=built の表が在るのに、指図は worktree 側が採られ、
    関門は3役の検め直しを要求し続けていた。掲示板 EDO-0307)。

    ⭕ **新しい方を採る**(`_doc_path` と同じ作法)。`history` の最後の `at` が新しい側を正とする。
    これで `--reopen`(phase=design へ戻す)も効く — 戻した側の history が最も新しくなるから。
    """
    newest, phase = "", "design"
    for p in _kansei_sides(name, sashizu_path):
        try:
            with open(p) as fp:
                doc = json.load(fp)
        except Exception:
            continue
        hist = doc.get("history") or []
        at = (hist[-1].get("at") if hist else None) or doc.get("since") or ""
        if at >= newest:
            newest, phase = at, doc.get("phase") or "built"
    return phase


def estates():
    """互換のための薄い殻。実体は estate_names()(worktree も見る)。"""
    return estate_names()


def gate(name):
    """1邸の関門。返すのは (赤の件数, 行の列)。
    ⚠ 指図は main とは限らない — worktree の方が新しければそちらを見る(_doc_path)。"""
    path = _doc_path(name)
    with open(path) as fp:
        doc = json.load(fp)
    # 2026-09-19 施主裁定2=A: 検分は**実装前に 1 巡**。実装の車線に入った敷地(<邸>_kansei.json が在り
    #   phase=built/done)では、この関門は効かない — 関門は完成条件の表(kansei_gate.py)へ移る。
    #   指図へ戻る(--reopen で phase=design)と再び効く(変わった章だけ)。
    ph = _kansei_phase(name, path)
    if ph in ("built", "done"):
        return 0, [("・", "kansei", "完成条件の表",
                    "実装後(phase=%s) — 検図関門は効かない。関門は `kansei_gate.py`" % ph, "")]
    rev = doc.get("reviews") or {}
    rows, red = [], 0
    for key, spec in REVIEWERS.items():
        if not spec["required"](doc):
            continue
        want = fingerprint(doc, spec["keys"], name, path, spec.get("files", ()))
        got = rev.get(key)
        if not got:
            # ⚠ **「通していない」と書かない。** この関門は 2026-09-01 に新設したので、
            #   それ以前の検分は記録されていないだけで、実際には通している邸がある
            #   (土井=検図14巡・考証13巡 / 岡部=検図12巡)。事実と食い違う非難を機械が
            #   出すと、正しく回してきた邸ほど関門を信用しなくなる。
            #   ⭕ ただし「改めて通す必要がある」という結論は変わらない — 過去の検分は
            #      いまの指図を見ていないので、記録を遡って書いてはならない。
            rows.append(("⛔", key, spec["label"], "**記録が無い**(関門は 2026-09-01 新設)",
                         spec["why"] + " ／ 過去に通していても、いまの指図を見た検分が要る"))
            red += 1
            continue
        verdict = got.get("verdict")
        at = got.get("at", "?")
        if verdict == "fail":
            rows.append(("⛔", key, spec["label"], "不合格(%s)" % at, got.get("note", "")))
            red += 1
        elif not still_valid(got.get("hash"), want, doc, spec, name, path):
            rows.append(("⚠", key, spec["label"],
                         "検め直しが要る — %s に通ったあと指図が変わった" % at,
                         "記録 %s / いま %s" % (got.get("hash", "—"), want)))
            red += 1
        elif verdict == "advisory":
            rows.append(("・", key, spec["label"], "助言のみ(%s)" % at, got.get("note", "")))
        elif verdict == "pass":
            rows.append(("⭕", key, spec["label"], "通っている(%s)" % at,
                         "" if got.get("hash") == want
                         else "指紋の式が 2026-09-21 に変わったが記録は有効(EDO-0330)"))
        else:
            rows.append(("⛔", key, spec["label"], "verdict が読めない: %r" % verdict, ""))
            red += 1
    return red, rows


def selftest():
    """⭐ **既知の形を仕込んで、関門が必ずその判定を出すことを確かめる。**

    ⛔ 他の関門(`wiring_gate` / `decision_gate` / `config_doctor`)には自己検査が
    あるのに、検図関門にだけ無かった(2026-09-13 の道具改め G1・EDO-0219)。
    ⚠ **関門は「赤が出ない」のが正常**なので、判定が死んでも誰も気づかない —
    静かに全邸が通り、赤のまま実装へ進む。だから自分で自分を鳴らす。
    ⛔ 本物の指図は一切読まない(捨て場に仕込んだ json だけを見る)。"""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="review-gate-selftest-")
    base = {"_": "自己検査の作り物", "mune": [{"name": "表御殿"}]}   # 庭を持たない = 庭方は不要

    def doc_with(reviews, extra=None):
        d = dict(base)
        if extra:
            d.update(extra)
        d["reviews"] = reviews
        return d

    def place(d, phase=None):
        """作り物を捨て場へ置き、_doc_path / _kansei_phase をそこへ向ける。"""
        p = os.path.join(tmp, "selftest_sashizu.json")
        with open(p, "w") as fp:
            json.dump(d, fp, ensure_ascii=False)
        if phase:
            with open(os.path.join(tmp, "selftest_kansei.json"), "w") as fp:
                json.dump({"phase": phase}, fp)
        elif os.path.exists(os.path.join(tmp, "selftest_kansei.json")):
            os.remove(os.path.join(tmp, "selftest_kansei.json"))
        return p

    def good_hash(d, p):
        return fingerprint(d, REVIEWERS["kenzu"]["keys"], "selftest", p,
                           REVIEWERS["kenzu"].get("files", ()))

    orig_doc_path = globals()["_doc_path"]
    globals()["_doc_path"] = lambda n: os.path.join(tmp, "selftest_sashizu.json")
    ng, ran = [], []
    try:
        # (題, 仕込む reviews.kenzu, phase, 期待する印, 期待が赤か)
        d0 = doc_with({})
        p0 = place(d0)
        h = good_hash(d0, p0)
        # ⛔ **印と赤の件数だけを見てはいけない。**2026-09-21 の破壊試験で判った —
        #   「不合格」の判定を殺しても、`verdict` が pass/advisory のどれでもないので
        #   最後の「読めない」へ落ち、印も ⛔・赤も 1 件のまま**同じに見える**。
        #   ⭕ **なぜ赤なのかの文言まで突き合わせる**(検査の文言と実装の集合を合わせる)。
        cases = [
            ("記録が無い",          None,                                        None,    "⛔", True,  "記録が無い"),
            ("不合格",              {"verdict": "fail", "at": "2026-01-01", "hash": h}, None, "⛔", True,  "不合格"),
            ("指図が変わった",      {"verdict": "pass", "at": "2026-01-01", "hash": "ちがう"}, None, "⚠", True,  "検め直しが要る"),
            ("通っている",          {"verdict": "pass", "at": "2026-01-01", "hash": h}, None, "⭕", False, "通っている"),
            ("助言のみ",            {"verdict": "advisory", "at": "2026-01-01", "hash": h}, None, "・", False, "助言のみ"),
            ("verdict が読めない",  {"verdict": "まる", "at": "2026-01-01", "hash": h}, None, "⛔", True,  "読めない"),
            ("実装後は効かない",    None,                                        "built", "・", False, "実装後"),
        ]
        for title, kenzu, phase, want_mark, want_red, want_why in cases:
            # ⚠ 指紋は指図の中身から出るので、**記録を入れ終えた形**で採る。
            #   ⭕ `reviews` 自身は指紋の対象外(でなければ循環する)。
            d = doc_with({"kenzu": dict(kenzu)} if kenzu else {})
            d["reviews"]["kosho"] = {"verdict": "pass", "at": "2026-01-01"}
            p = place(d, phase)
            for role in ("kenzu", "kosho"):
                rec = d["reviews"].get(role)
                if rec and rec.get("hash") != "ちがう":
                    rec["hash"] = fingerprint(d, REVIEWERS[role]["keys"], "selftest", p,
                                              REVIEWERS[role].get("files", ()))
            p = place(d, phase)
            red, rows = gate("selftest")
            row = next((r for r in rows if r[1] in ("kenzu", "kansei")), None)
            mark = row[0] if row else "(行が無い)"
            why = row[3] if row else ""
            ok = (mark == want_mark) and (bool(red) == want_red) and (want_why in why)
            ran.append(title)
            print("%s %-20s → %s「%s」(期待 %s「%s」)/ 赤 %d 件"
                  % ("⭕" if ok else "⛔", title, mark, why[:22], want_mark, want_why, red))
            if not ok:
                ng.append(title)

        # ⭐ **表が指図と別の側に在っても効く**(EDO-0307)。`--init` は main へ書くのに、指図は
        #   worktree の方が新しければそちらが採られる。同じ側しか見ない実装だと、実装へ入った
        #   邸に紙の巡を要求し続ける。ここでは tmp=worktree 側・tmp2=main 側に見立てる。
        tmp2 = tempfile.mkdtemp(prefix="review-gate-selftest-main-")
        orig_doc_dir = globals()["DOC"]
        try:
            d = doc_with({})
            place(d)                                  # 指図だけ(表は置かない)
            with open(os.path.join(tmp2, "selftest_kansei.json"), "w") as fp:
                json.dump({"phase": "built", "since": "2026-09-20",
                           "history": [{"at": "2026-09-20T12:00:00+09:00", "event": "init"}]}, fp)
            globals()["DOC"] = tmp2
            red, rows = gate("selftest")
            row = next((r for r in rows if r[1] in ("kenzu", "kansei")), None)
            mark, why = (row[0], row[3]) if row else ("(行が無い)", "")
            ok = (mark == "・") and (red == 0) and ("実装後" in why)
            ran.append("表が別の側に在る")
            print("%s %-20s → %s「%s」(期待 ・「実装後」)/ 赤 %d 件"
                  % ("⭕" if ok else "⛔", "表が別の側に在る", mark, why[:22], red))
            if not ok:
                ng.append("表が別の側に在る")
        finally:
            globals()["DOC"] = orig_doc_dir
            shutil.rmtree(tmp2, ignore_errors=True)
    finally:
        globals()["_doc_path"] = orig_doc_path
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if ng:
        print("⛔ 自己検査 不通 %d 件 — **関門の判定が死んでいる。**%s" % (len(ng), " / ".join(ng)))
        return 1
    print("⭕ 自己検査 全通 — %d つの形とも生きている。" % len(ran))
    return 0


def record(name, key, verdict, note):
    # ⚠ 書き戻し先も _doc_path — main に書くと、worktree で作業している邸の
    #   指図には反映されず、次の巡回でまた「記録が無い」に戻る。
    if key not in REVIEWERS:
        sys.exit("検分役が違う。使えるのは: " + " / ".join(REVIEWERS))
    if verdict not in VERDICTS:
        sys.exit("verdict は " + " / ".join(VERDICTS))
    path = _doc_path(name)
    with open(path) as fp:
        doc = json.load(fp, object_pairs_hook=collections.OrderedDict)
    doc.setdefault("_reviews", (
        "**検図関門。**この指図を誰が検めたか。⛔ 呼んだ側(普請奉行)が結果を書き戻す — "
        "検分役は read-only で自分では書けない。`hash` はその検分が見た範囲の指紋で、"
        "指図を書き換えるとずれ、検分は自動で『検め直しが要る』になる。"
        "見張りは `python3 Tools/Sashizu/review_gate.py`。"
        "⛔ 関門が赤の指図を実装しない・赤のシーンをユーザーに見せない。"))
    rv = doc.setdefault("reviews", collections.OrderedDict())
    prev = rv.get(key) or {}
    hist = list(prev.get("rounds") or [])
    if verdict == "fail" and consecutive_fails(doc, key) >= ROUND_MAX:
        sys.exit("⛔ 三巡則: %s はユーザー入力なしに fail が %d 回続いている。4 巡目の記録は受けない。\n"
                 "   `decision` か `blocker` を post して手を止め、ユーザーの返事の後に再開する"
                 "(reset は発話か `--ack %s \"<発話の引用>\"`)。" % (REVIEWERS[key]["label"], ROUND_MAX, name))
    hist.append(collections.OrderedDict([
        ("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
        ("verdict", verdict)]))
    rv[key] = collections.OrderedDict([
        ("at", datetime.date.today().isoformat()),
        ("verdict", verdict),
        ("hash", fingerprint(doc, REVIEWERS[key]["keys"], name, path,
                             REVIEWERS[key].get("files", ()))),
        ("note", (note or "")[:1500]),
        ("chapters", chapter_prints(doc, REVIEWERS[key]["keys"], name, path,
                                    REVIEWERS[key].get("files", ()))),
        ("rounds", hist[-12:]),
    ])
    with open(path, "w") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    # ⚠ **どこへ書いたかを必ず出す。** main と worktree のどちらに入ったかが見えないと、
    #   「記録したのに関門が赤のまま」を追えない。
    where = "worktree" if ".claude/worktrees/" in path else "main"
    print("記録: %s / %s = %s  → %s (%s)"
          % (name, REVIEWERS[key]["label"], verdict, os.path.relpath(path, REPO), where))
    n = consecutive_fails(doc, key)
    if verdict == "fail" and n >= 2:
        print("  ⚠ 三巡則: この役はユーザー入力なしに fail %d 回目。%d 回で止まる。" % (n, ROUND_MAX))
    if where == "worktree":
        print("  ⚠ worktree の指図に書いた。**main へマージするまで main 側には映らない** — "
              "関門は新しい方を見るので赤は消えるが、マージを忘れないこと。")


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--selftest":
        return sys.exit(selftest())
    if argv and argv[0] == "--record":
        if len(argv) < 4:
            sys.exit("使い方: --record <屋敷> <検分役> <pass|fail|advisory> [一言]\n"
                     "        --record <屋敷> <検分役> <判定> --note-file <パス|->")
        # ⭐ **一言をファイル(か標準入力)から渡せる**(2026-09-21 EDO-0179)。
        #   ⛔ コマンドラインに二重引用符で書くと、検分役の文中の `鍵の名` を
        #   **シェルがコマンドとして実行して消す**。2026-09-09 に山王で 4 件が消え、
        #   それでも本ツールは exit 0 で「記録: … = fail」と成功を刷った。
        #   ⚠ 消えるのは「どの鍵を直せばよいか」なので、次の巡が読んで**何を直すか分からない**。
        #   ⛔ 関門の側では気づけない — シェルが先に食うので、ここには届かないため。
        rest = argv[4:]
        if "--note-file" in rest:
            i = rest.index("--note-file")
            if i + 1 >= len(rest):
                sys.exit("--note-file にパスが無い(標準入力から読むなら `-`)")
            src = rest[i + 1]
            note = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
            note = note.strip()
        else:
            note = " ".join(rest)
        record(argv[1], argv[2], argv[3], note)
        return
    if argv and argv[0] == "--changed":
        if len(argv) < 2:
            sys.exit("使い方: --changed <屋敷> [--json]")
        return sys.exit(cmd_changed(argv[1], "--json" in argv))
    if argv and argv[0] == "--rounds":
        if len(argv) < 2:
            sys.exit("使い方: --rounds <屋敷>")
        return sys.exit(cmd_rounds(argv[1]))
    if argv and argv[0] == "--checks":
        return sys.exit(cmd_checks())
    if argv and argv[0] == "--ack":
        if len(argv) < 3:
            sys.exit("使い方: --ack <屋敷> \"<ユーザーの発話の引用>\"")
        return sys.exit(cmd_ack(argv[1], " ".join(argv[2:])))
    quiet = "--quiet" in argv
    names = [a for a in argv if not a.startswith("--")] or estates()
    total = 0
    lines = []
    for n in names:
        red, rows = gate(n)
        total += red
        if quiet:
            if red:
                miss = ", ".join(r[2] for r in rows if r[0] in ("⛔", "⚠"))
                lines.append("  ⛔ %-18s 検図関門 %d 件 — %s" % (n, red, miss))
            continue
        lines.append("%s  %s" % ("⛔" if red else "⭕", n))
        for mark, key, label, state, why in rows:
            lines.append("    %s %-22s %s" % (mark, label, state))
            if why:
                lines.append("        %s" % why)
    if quiet and total:
        lines.insert(0, "検図関門 — **検分の記録が無い/検め直しが要る指図がある**"
                        "(`python3 Tools/Sashizu/review_gate.py`)")
    print("\n".join(lines))
    if not quiet and total:
        print("\n⛔ 赤 %d 件。**関門が赤の指図を実装しない・赤のシーンをユーザーに見せない。**"
              "\n   検分に出す → 結果を `--record <屋敷> <役> <pass|fail>` で書き戻す。"
              "\n"
              "\n⚠ **【移行期間】2026-09-01 ユーザー裁定(案B)。**関門は新設で全邸が赤で"
              "立ち上がったので、\n   ⭕ **検分を通すまで従来どおり作業を続けてよい**"
              "(実装・指図の改訂とも)。\n"
              "   ⛔ **ただし新たにユーザーへ見せる前には必ず通す** — 見せる=裁定を仰ぐ・"
              "レンダを出す・\n      指図の Artifact を案内する、のすべて。ここが移行中も"
              "動かない一線。\n"
              "   ⛔ 「記録が無い」は「通していない」ではない。⛔ それでも遡って pass は"
              "書かない。" % total)
    sys.exit(1 if total else 0)


# ⚠ **`main()` を裸で呼ばない。** import しただけで全邸の検査が走り、`sys.exit` まで
#   到達する(2026-09-01、判定の単体確認をしようとして踏んだ)。他所からこの道具の
#   関数(`_needs_niwashi` / `gate` / `fingerprint`)を使えるようにしておく。
if __name__ == "__main__":
    main()
