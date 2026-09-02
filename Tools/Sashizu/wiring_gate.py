#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""結線関門 — 「書いたのに誰の目にも入らない」産物を機械で鳴らす(全邸共通)。

⭐ **狙い。**指図の欠陥は「値が間違っている」より先に「**値がどの目にも入っていない**」形で
潜む。検査を書いたのに呼んでいない・図を書いたのに描いていない・測ったのに図へ出していない。
⛔ どれも**目視では見つからない**(松江松平は同じ型を3度見逃し、4度目で機械化した)。
⭕ 実測: 岡部の `walls_table()`(段の土留めの一覧表)は**書かれて一度も描かれていない**。

⚠ **`build_matsudaira_dewa_sashizu.py` の `check_wiring_check` を各邸へ写さないこと。**
あれは当邸の `plane_check` の束と `main()` の `WARN` という**固有の報告経路**に結ばれており、
移植には読み替えが要る(移植の写しは 2026-08-25 に土井が偽の不一致28件を出した型)。
⭕ 本ツールは**外から生成器のソースを読むだけ**で、邸ごとの構造を仮定しない。

    python3 Tools/Sashizu/wiring_gate.py                     # 全邸の生成器
    python3 Tools/Sashizu/wiring_gate.py Tools/Sashizu/build_okabe_sashizu.py
    python3 Tools/Sashizu/wiring_gate.py --json

⭐ **第3型(測ったのに図に出していない)は静的には見えない。**別モードで、生成器の
実行ログと成果物の HTML を突き合わせる:

    python3 Tools/Sashizu/build_<邸>_sashizu.py 2>&1 | tee /tmp/run.log
    python3 Tools/Sashizu/wiring_gate.py --surfaced /tmp/run.log docs/Sashizu/<邸>_sashizu.html

⛔ **限界 — 0件は「合格」ではなく「この型では捕まらなかった」。**名前で辿る静的解析なので:
  ・恒真の検査(走って報告されるが何を壊しても0件)→ **破壊試験でしか出ない**
    (岡部の `kekkai_check` は「結界を全部消す」でも0件だった・2026-09-02 検図)
  ・検査そのものが無い領域 → **検査の型の欠落**は EDO-0106 の持ち場
  ・部材の実メッシュの見え方・駒どうしの隙間 → **建てて見る輪でしか出ない**(規則5・EDO-0096)
→ 正典 `docs/verification-loops.md`。
"""

import argparse
import ast
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 産物を作る関数の名づけ。⚠ 各邸の慣習に合わせて足してよい — 「辿れる」なら鳴らないので、
# 網を広げても誤報は増えない。
KIND = [
    ("検査", re.compile(r"(^|_)(check|verify|audit|validate|qa)(_|$)", re.I)),
    ("図",   re.compile(r"(^|_)(svg|fig|figure|plate|plan|section|diagram|chart)(_|$)", re.I)),
    ("表",   re.compile(r"(^|_)(table|tbl|ledger|matrix)(_|$)", re.I)),
]


def _kind(name):
    for label, rx in KIND:
        if rx.search(name):
            return label
    return None


def _refs(node, universe):
    """`node` の中で名前として現れる関数。⭐ 呼び出しだけでなく**値としての参照**も数える
    (`[foo_check, bar_check]` のように束へ入れる書き方が各邸にある)。"""
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            out.add(sub.id)
        elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            out.add(sub.func.attr)
    return out & universe


def audit(path):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    funcs = {n.name: n for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    universe = set(funcs)
    if not universe:
        return None

    calls = {n: _refs(node, universe) for n, node in funcs.items()}

    # 根 = module 直下から参照されるもの + main
    roots = set()
    for n in tree.body:
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            roots |= _refs(n, universe)
    if "main" in funcs:
        roots.add("main")
    if not roots:                      # ライブラリ(入口が無い)は外から呼ばれる前提で見送る
        return {"path": path, "library": True, "orphan": [], "discarded": []}

    seen, stack = set(), list(roots)
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        stack.extend(calls.get(x, ()))

    # ── ⛔ 孤立: 産物を作るのに、どの入口からも辿れない
    orphan = [{"name": n, "kind": _kind(n), "line": funcs[n].lineno}
              for n in sorted(universe - seen)
              if _kind(n) and not n.startswith("_")]

    # ── ⛔ 捨て: 値を返す検査を**式文として**呼んでいる(戻り値を誰も受け取らない)
    #    ⭐ 判定は「その Call の親が ast.Expr か」— 代入・演算・引数・return なら使われている。
    returns_val = {n: any(isinstance(s, ast.Return) and s.value is not None
                          for s in ast.walk(node)) for n, node in funcs.items()}
    discarded = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            f = node.value.func
            nm = f.id if isinstance(f, ast.Name) else None
            if nm in funcs and _kind(nm) == "検査" and returns_val.get(nm):
                discarded.append({"name": nm, "line": node.lineno})

    # ── ⛔ 黙り: 走っているが、結果が print にも return にも届かない
    # ⭐ **変数経由で回す検査は免除**(2026-09-02 岡部の申し送り)—
    #   `for 題, fn9 in ((…, garden_alloc_check), …): print(…, len(fn9(d)))` の形は
    #   静的に追えない。⛔ **関数名が「呼び出しの func 以外」に値として現れたら免除**。
    #   ⚠ 保守的に倒す — 狼少年の関門は無視される。
    exempt = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            for a in list(node.args) + [k.value for k in node.keywords]:
                exempt |= _value_names(a)
        elif isinstance(node, (ast.Tuple, ast.List, ast.Set, ast.Dict)):
            exempt |= _value_names(node)
        elif isinstance(node, ast.Lambda):
            # ⭐ **ラムダの中の呼び出しは免除**(2026-09-02 岡部の実物)—
            #   `(題, lambda d, raw, ter: batter_check(d, ter))` の表にまとめて入れ、
            #   呼び出し側が回して件数を刷る形がある。⛔ 静的には追えないので保守的に倒す。
            exempt |= {n.func.id for n in ast.walk(node)
                       if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    exempt &= universe

    # ⭐ **合否はモジュール全体で** — どこか1つの関数で刷られていれば良い形。
    verdict = {}
    for n, node in funcs.items():
        if n not in seen:                   # 到達しない関数は「孤立」で既に鳴っている
            continue
        for nm, (v, seed, line) in _flows(node, exempt).items():
            prev = verdict.get(nm)
            rank = {"print": 3, "return": 3, "guarded": 2, None: 1}
            if prev is None or rank[v] > rank[prev[0]]:
                verdict[nm] = (v, seed, line)
    mute = [{"name": nm, "line": ln, "via": sd,
             "why": ("guarded" if v == "guarded" else "mute")}
            for nm, (v, sd, ln) in sorted(verdict.items())
            if v not in ("print", "return")]

    n_check = len([n for n in universe if _kind(n) == "検査"])
    return {"path": path, "library": False, "orphan": orphan, "discarded": discarded,
            "mute": mute,
            "n_func": len(universe), "n_reached": len(seen), "n_check": n_check}


# ────────────────────────────────────────────────────────────────────────────
# 第3型 — 測ったのに図に出していない(実行ログ × 成果物 HTML)
# ────────────────────────────────────────────────────────────────────────────
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_NUM = re.compile(r"-?\d+\.\d+|-?\d+")


def _plain(html):
    return _WS.sub(" ", _TAG.sub(" ", html))


def surfaced(log_path, html_path):
    """実行ログの ⚠ 行が成果物へ載っているかを突き合わせる。

    ⭐ 判定は**行に出てくる数値**で行う(文言は図の側で言い換えられるため)。
    行の数値がすべて成果物の地の文に現れれば「載っている」とみなす。
    ⚠ 粗い突き合わせ — 「載っていない」は要確認の合図であって断定ではない。"""
    log = open(log_path, encoding="utf-8", errors="replace").read().splitlines()
    body = _plain(open(html_path, encoding="utf-8", errors="replace").read())
    hits = set(_NUM.findall(body))
    miss = []
    warn_lines = [ln for ln in log if ("⚠" in ln or "WARN" in ln or "⛔" in ln)]
    for ln in warn_lines:
        nums = [x for x in _NUM.findall(ln) if len(x) > 1]
        if not nums:
            continue
        if not all(x in hits for x in nums):
            miss.append(ln.strip()[:160])
    return warn_lines, miss


# ────────────────────────────────────────────────────────────────────────────
# 第4型 — 走っているが「件数を刷る経路」に届かない(岡部 2026-09-02 の申し送り)
# ────────────────────────────────────────────────────────────────────────────
# ⭐ **孤立していないが要約に出ない検査は、孤立と実害が同じ。**
#   岡部の `batter_check`(法面)は呼ばれているのに、結果が **切盛図のキャプションの中にしか**
#   出ない。要約だけを見た指図方も普請奉行も「全項目0件」と報告し、**24件を1巡見落とした**。
#   ⛔ `--surfaced`(実行ログ × 成果物)では拾えない — 実行ログにそもそも1行も出ないため。
#
# ⭕ 良い形: `bad = f(d)` → `print("… %d 件" % len(bad))`(0件でも必ず刷る)
#          または `bad += f(d)` → `return bad`(呼び出し側が刷る責任を持つ)
# ⛔ 悪い形: `bb = f(d, ter)` → `h.append('<p class="cap">法面の検査: %s' % …)` だけ
#
# ⚠ **保守的に判定する** — 狼少年の関門は無視されるので、疑わしきは鳴らさない。
#   別名(`y = x` / `y += x` / `y.extend(x)` / `y.append(x)`)だけを追い、
#   ⛔ **書式文字列の中に埋め込まれた参照では taint を伝播させない**(そこが岡部の型)。

_ALIAS_METH = {"extend", "update", "append", "add"}
_STR_METH = {"format", "join"}


def _stringy(node):
    """文字列を組み立てている式か。⭐ **ここが岡部の型と当邸の感度試験を分ける一線。**
    ⛔ `h.append('<p>…%s' % (…, len(bb), …))` は**図の中へ埋める**ので、件数は誰にも刷られない。
    ⭕ `out.append((題, len(msg)))` は**数のまま運ぶ**ので、呼び出し側が刷れる。"""
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, ast.BinOp):
        return _stringy(node.left) or _stringy(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr in _STR_METH:
        return True
    return False


def _value_names(node):
    """`node` の中で**値として**現れる名前。⛔ 呼び出しの func 位置は数えない。

    ⚠ ここを緩めると全滅する(2026-09-02 に踏んだ)— `(…, batter_check(d, ter), …)` の
    ような**タプルの中の呼び出し**まで「値としての参照」に数えてしまい、
    ⛔ 岡部の全29検査が免除に落ちて黙り検出が丸ごと効かなくなった。"""
    out, stack = set(), [node]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.add(n.id)
        for f, v in ast.iter_fields(n):
            if isinstance(n, ast.Call) and f == "func":
                continue                      # ⛔ 呼び出しの func は「値としての参照」ではない
            if isinstance(v, ast.AST):
                stack.append(v)
            elif isinstance(v, list):
                stack += [x for x in v if isinstance(x, ast.AST)]
    return out


def _reaches(fn, seed, nodes):
    """`seed` が受けた値が print / return へ届くか。
    返り値: "print" / "return" / "guarded"(0件のとき沈黙する print)/ None"""
    taint = {seed}
    for _ in range(6):                           # 素直な別名の閉包(浅くてよい)
        before = len(taint)
        for node in nodes:
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                v = node.value
                names = {x.id for x in ast.walk(v)
                         if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)}
                if isinstance(v, (ast.Name, ast.BinOp)) and (names & taint):
                    tg = node.targets if isinstance(node, ast.Assign) else [node.target]
                    taint |= {t.id for t in tg if isinstance(t, ast.Name)}
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in _ALIAS_METH and len(node.args) == 1 \
                    and isinstance(node.func.value, ast.Name):
                arg = node.args[0]
                if any(isinstance(x, ast.Name) and x.id in taint for x in ast.walk(arg)) \
                        and not _stringy(arg):
                    taint.add(node.func.value.id)   # ⭕ 数のまま運ぶ / ⛔ 文字列へ埋めない
        if len(taint) == before:
            break

    # ⚠ 真偽で守られた print は「0件のとき沈黙する」= 件数が出ない。⛔ 黙りと実害が同じ。
    guarded = set()
    for node in nodes:
        if not isinstance(node, ast.If):
            continue
        t = node.test
        if not any(isinstance(x, ast.Name) and x.id in taint for x in ast.walk(t)):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                    and sub.func.id == "print":
                guarded.add(id(sub))

    hit = None
    for node in nodes:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "print":
            if any(isinstance(x, ast.Name) and x.id in taint for x in ast.walk(node)):
                if id(node) in guarded:
                    hit = hit or "guarded"
                else:
                    return "print"
        elif isinstance(node, ast.Return) and node.value is not None:
            if any(isinstance(x, ast.Name) and x.id in taint for x in ast.walk(node.value)):
                return "return"
    return hit


def _flows(fn, exempt):
    """この関数の中で、検査の結果が「件数を刷る経路」に届いているか。

    返り値: {検査名: ("print"|"return"|"guarded"|None, 受けた名前, 行)}
    ⭐ **合否はモジュール全体で決める**(`audit` 側)。⛔ 同じ検査を
    「要約で刷る関数」と「図へ埋める関数」の**別々の関数**から呼ぶのは正常な形なので、
    関数ごとに鳴らすと必ず誤検出になる(2026-09-02 岡部で5件出した)。"""
    seeds = {}
    for node in ast.walk(fn):
        if not isinstance(node, (ast.Assign, ast.AugAssign)):
            continue
        val = node.value
        if not (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)):
            continue
        nm = val.func.id
        if _kind(nm) != "検査" or nm in exempt:
            continue
        tgts = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in tgts:
            if isinstance(t, ast.Name):
                seeds.setdefault(nm, []).append((t.id, node.lineno))
    if not seeds:
        return {}

    nodes = list(ast.walk(fn))
    out = {}
    for nm, sites in seeds.items():
        best, seed0, line0 = None, sites[0][0], sites[0][1]
        for seed, line in sites:
            v = _reaches(fn, seed, nodes)
            if v in ("print", "return"):
                best = v
                break
            if v == "guarded" and best is None:
                best = "guarded"
        out[nm] = (best, seed0, line0)
    return out


def _live(main_fp):
    """その生成器の**いま生きている実体**。⭐ `review_gate._doc_path` と同じ考え方。

    ⛔ **worktree を無条件に優先してはいけない。**邸によっては main で作業している
    (松江松平は main・岡部は worktree)。⚠ 無条件に worktree を採ると、
    **古い版を検めて「検査が減った」と誤読する**(2026-09-02 に踏んだ: 検査 47 → 27)。
    ⭕ **mtime の新しい方を採る。**"""
    base = os.path.basename(main_fp)
    estate = base[6:].rsplit("_", 1)[0]
    wt = os.path.join(ROOT, ".claude", "worktrees", estate, "Tools", "Sashizu", base)
    if not os.path.exists(wt):
        return main_fp
    if not os.path.exists(main_fp):
        return wt
    return wt if os.path.getmtime(wt) > os.path.getmtime(main_fp) else main_fp


def targets(argv):
    """⭐ **邸名でも引ける**(2026-09-02 infra セッションの申し送り) —
    `review_gate.py okabe` / `review_ledger.py okabe` が邸名で引けるのに、
    ⛔ 本ツールだけ生パスを要求して `FileNotFoundError` を投げていた。"""
    if argv:
        out = []
        for a in argv:
            if os.path.exists(a):
                out.append(a)
                continue
            # ⭐ **worktree を先に見る**(2026-09-02 岡部の申し送り)— 各邸は
            #   `.claude/worktrees/<邸>/` で作業しており、main だけ見ると**旧版を検める**。
            #   ⛔ 実際、岡部の作業版は検査が 14 → 28 本に増えていた。`review_gate._doc_path`
            #   と同じ考え方。⭕ worktree にあればそちらを、無ければ main を採る。
            hits = [_live(x) for x in
                    sorted(glob.glob(os.path.join(ROOT, "Tools/Sashizu/build_%s_*.py" % a)))]
            if hits:
                out += hits
            else:
                sys.stderr.write(
                    "⛔ 邸名にもパスにも当たらない: %s\n"
                    "   邸名は %s\n" % (
                        a, ", ".join(sorted(set(
                            os.path.basename(x)[6:].rsplit("_", 1)[0]
                            for x in glob.glob(os.path.join(ROOT, "Tools/Sashizu/build_*_sashizu.py"))
                        )))))
                raise SystemExit(2)
        return out
    # ⭐ 無引数のときも**邸ごとに worktree を先に見る**(邸名で引いたときと揃える)。
    out, seen = [], set()
    for pat in ("Tools/Sashizu/build_*_sashizu.py", "Tools/Sashizu/build_*_saitei.py"):
        for fp in sorted(glob.glob(os.path.join(ROOT, pat))):
            fp = _live(fp)
            if fp not in seen:
                seen.add(fp)
                out.append(fp)
    return out


def main():
    ap = argparse.ArgumentParser(description="結線関門 — 誰にも届かない産物を鳴らす")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--surfaced", nargs=2, metavar=("RUN.LOG", "OUT.HTML"),
                    help="実行ログの ⚠ 行が成果物 HTML に載っているかを突き合わせる")
    a = ap.parse_args()

    if a.surfaced:
        warn_lines, miss = surfaced(*a.surfaced)
        print("実行ログの警告行 %d 件 / 成果物に見当たらない %d 件" % (len(warn_lines), len(miss)))
        for m in miss:
            print("    ⚠ %s" % m)
        if miss:
            print("\n⛔ **測ったのに図に出ていない疑い。**stdout にしか無い検査結果は、"
                  "読む人にとって存在しない(docs/verification-loops.md 第3型)。")
        return 1 if miss else 0

    reports, bad = [], 0
    for p in targets(a.paths):
        r = audit(p)
        if r is None:
            continue
        reports.append(r)
        bad += len(r["orphan"]) + len(r["discarded"]) \
            + len([o for o in r.get("mute", ()) if o.get("why") != "guarded"])

    if a.json:
        print(json.dumps(reports, ensure_ascii=False, indent=1))
        return 1 if bad else 0

    for r in reports:
        name = os.path.basename(r["path"])
        if r["library"]:
            print("・%-38s 入口が無い(ライブラリ)— 見送り" % name)
            continue
        hard = r["orphan"] or r["discarded"] or \
            [o for o in r.get("mute", ()) if o.get("why") != "guarded"]
        mark = "⛔" if hard else ("⚠" if r.get("mute") else "⭕")
        print("%s %-38s 関数 %d / 到達 %d / 検査 %d"
              % (mark, name, r["n_func"], r["n_reached"], r["n_check"]))
        for o in r["orphan"]:
            print("    ⛔ 孤立 L%-5d %s()  … %sを作るが、main からも module 直下からも"
                  "辿れない = 一度も走らない" % (o["line"], o["name"], o["kind"]))
        for o in r["discarded"]:
            print("    ⛔ 捨て L%-5d %s()  … 走るが戻り値を誰も受け取っていない"
                  % (o["line"], o["name"]))
        for o in r.get("mute", ()):
            if o.get("why") != "guarded":
                print("    ⛔ 黙り L%-5d %s()  … 走るが件数が print にも return にも届かない"
                      "(受け `%s` は図の中で消える)" % (o["line"], o["name"], o["via"]))
        # ⭐ 「0件のとき沈黙」は**規約の食い違い**であって個別の欠陥ではない。
        #   ⛔ 1本ずつ並べると狼少年になる(岡部で12行出た)ので**1行にまとめる**。
        g = [o for o in r.get("mute", ()) if o.get("why") == "guarded"]
        if g:
            print("    ⚠ 0件で沈黙 %d 本 — `if bad: print(…)` の形で、**0件のとき件数が出ない**。"
                  % len(g))
            print("       %s" % " / ".join(o["name"] for o in g[:8])
                  + (" ほか" if len(g) > 8 else ""))
            print("       ⭕ 当プロジェクトの作法は「**0件でも件数を出す**」"
                  "(0件と未実行が見分けられなくなるため)。⚠ 規約の食い違いなので、"
                  "邸の方針として `if` を外すかどうかを決めること。")

    print()
    if bad:
        print("⛔ 結線の不備 %d 件 — **書いたのに誰の目にも入らない産物がある。**" % bad)
    else:
        print("⭕ 孤立・捨て・黙り 0 件。")
    print("⛔ 0件は「合格」ではない — 恒真の検査・検査の欠落・建てないと見えない不良は"
          "本ツールでは見えない(docs/verification-loops.md)。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
