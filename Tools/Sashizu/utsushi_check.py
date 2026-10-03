#!/usr/bin/env python3
"""指図の写しの関門 — 章立てと読み込み先を検める(2026-10-03 施主裁定 EDO-0558)。

正典は docs/Sashizu/README.md 決めごと2c。写し(`<邸>_sashizu.html`)は指図(json)の忠実な再現で、
載せる章と見た目は全邸で揃える。⛔ 裁定図・経緯の図・履歴・建った姿の実測は写しに載せない。

  python3 Tools/Sashizu/utsushi_check.py              # 全邸の写しの章立て(速い・html を読むだけ)
  python3 Tools/Sashizu/utsushi_check.py --quiet      # 破れだけ刷る(挨拶フック用)。無傷なら無言
  python3 Tools/Sashizu/utsushi_check.py --inputs     # 生成器を試し焼きし、開いたファイルが許す範囲か(遅い)
  python3 Tools/Sashizu/utsushi_check.py --inputs doi # 一邸だけ

生成器は焼いた直後に `check_html()` を呼んで、自分の写しの章立てを ⭕/⛔ で刷る(規則19 の結線)。

⚠ 章立ての検めは**章の名と並び**しか見ない。章の中身が json から来ているかは --inputs が
「生成器が何を読んだか」で間接に押さえる(json・地盤・算出物・在庫の目録の外を読んだら ⛔)。
⛔ 0 件は「描いた物がすべて json にある」の証明ではない — 生成器の中に文章を直書きした所は
読み込み先に現れない(丹羽・外堀の生成器にはまだ多い。notes へ移すのは prose_split の持ち場)。
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "docs", "Sashizu")

# ---------------------------------------------------------------- 章立て(決めごと2c)
YASHIKI_REQ = ["配置図", "現況図", "切盛図", "断面", "動線図", "外周と役割"]
YASHIKI_OPT = ["棟の接地", "庭", "隣家との取り合い", "建蔽率", "部材", "実装の順序", "未解決"]
YASHIKI_TAIL = ["検査", "考証と決めごと"]
APPENDIX = ["文書の記法"]        # 末尾に置いてよい読み方の凡例(どの型でも任意)
DOBOKU = [("位置と水系", 1), ("現況調査", 1), ("現況図", 1), ("掘削平面図", 1), ("縦断面", 1),
          ("横断面", "+"), ("工区と摺り付け", 1), ("施工の段階", 1), ("検査", 1),
          ("考証と決めごと", 1), ("未解決", 1)]
# ⛔ 写しに出てはならない章の語(裁定図・経緯の図・履歴・建った姿の実測)
FORBID = ["裁定図", "履歴", "改訂", "取り合い 詳細", "詳細平面", "実測 vs", "比べ", "施工の記録"]

KIND = {"sotobori": "doboku"}          # 無ければ屋敷(寺社を含む)

# 生成器と、その邸の写し
GEN = {"niwa_sakyo": ["build_niwa_sakyo_sashizu.py"],
       "sotobori": ["build_sotobori_sashizu.py"]}
COMMON = ["build_sashizu.py"]         # 他の邸は共通の生成器に邸名を渡す


def estates():
    return sorted(f[:-len("_sashizu.json")] for f in os.listdir(DOC) if f.endswith("_sashizu.json"))


def chapters(html):
    """章の名(図版番号「其X　」を外したもの)を並びのまま返す。章=図版の枠(phead)の見出し。"""
    out = []
    for m in re.finditer(r'<div class="phead"><h2>(.*?)</h2>', html):
        t = re.sub(r"<[^>]+>", "", m.group(1))
        t = re.sub(r"^其[一二三四五六七八九十]+\s*", "", t.replace("&#x27;", "'")).strip()
        out.append(t)
    return out


def _is(t, name):
    return t == name or t.startswith(name + " ") or t.startswith(name + "—") or t.startswith(name + " —")


def check_chapters(est, chs, title):
    """破れの list を返す(空なら ⭕)。"""
    bad = []
    if "指図の写し" not in title:
        bad.append("題が「指図の写し」になっていない(%s)" % (title or "題なし"))
    for t in chs:
        for w in FORBID:
            if w in t:
                bad.append("写しに載せない章がある:「%s」(語「%s」→ 裁定図・経緯の図へ)" % (t, w))
    while chs and chs[-1] in APPENDIX:
        chs = chs[:-1]
    if KIND.get(est) == "doboku":
        i = 0
        for name, cnt in DOBOKU:
            n = 0
            while i < len(chs) and _is(chs[i], name):
                i += 1
                n += 1
            if n == 0:
                bad.append("章が無いか並びが違う:「%s」(%d 章目の辺り)" % (name, i + 1))
            elif cnt == 1 and n > 1:
                bad.append("章「%s」が %d 回出る" % (name, n))
        if i < len(chs):
            bad.append("決めごとに無い章:「%s」ほか %d 章" % (chs[i], len(chs) - i))
        return bad
    seq = YASHIKI_REQ + YASHIKI_OPT + YASHIKI_TAIL
    req = set(YASHIKI_REQ + YASHIKI_TAIL)
    pos = []
    for t in chs:
        k = next((j for j, nm in enumerate(seq) if _is(t, nm)), None)
        if k is None:
            bad.append("決めごとに無い章:「%s」" % t)
            continue
        pos.append((k, t))
    for (k0, t0), (k1, t1) in zip(pos, pos[1:]):
        if k1 <= k0:
            bad.append("並びが違う:「%s」が「%s」の後にある" % (t1, t0))
    have = set(seq[k] for k, _ in pos)
    for nm in seq:
        if nm in req and nm not in have:
            bad.append("必ず載せる章が無い:「%s」" % nm)
    return bad


def check_html(est, path):
    """焼いた写しの章立てを検めて刷る。生成器の末尾から呼ぶ。⛔ の件数を返す。"""
    h = open(path, encoding="utf-8").read()
    m = re.search(r"<title>(.*?)</title>", h)
    bad = check_chapters(est, chapters(h), m.group(1) if m else "")
    if bad:
        print("  ⛔ 写しの章立て(決めごと2c)の破れ %d 件" % len(bad))
        for b in bad:
            print("    ⛔ %s" % b)
    else:
        print("  ⭕ 写しの章立て(決めごと2c)の破れ 0 件 ／ 章 %d" % len(chapters(h)))
    return len(bad)


# ---------------------------------------------------------------- 読み込み先
# ⭕ 写しが読んでよいもの: 指図・考証・notes・地盤・算出物(いずれも docs/Sashizu)、様式、在庫の目録。
ALLOW = [r"^docs/Sashizu/", r"^Tools/Sashizu/sashizu\.css$", r"^docs/asset-index\.tsv$"]

_PROBE = r'''
import os, runpy, sys
ROOT = sys.argv[1]; script = sys.argv[2]; sys.argv = sys.argv[2:]
seen = set()
def hook(ev, args):
    if ev == "open" and args and isinstance(args[0], (str, bytes)):
        p = args[0] if isinstance(args[0], str) else args[0].decode()
        p = os.path.abspath(p)
        mode = str(args[1]) if len(args) > 1 and args[1] is not None else "r"
        if p.startswith(ROOT + os.sep) and "__pycache__" not in p and not p.endswith(".py") \
                and "w" not in mode and "a" not in mode:
            seen.add(os.path.relpath(p, ROOT))
sys.addaudithook(hook)
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as e:
    if e.code is not None and not isinstance(e.code, int):
        sys.stderr.write(str(e.code) + "\n")
sys.stderr.write("@@READ@@" + "\n".join(sorted(seen)) + "\n")
'''


def reads(est, tmp):
    gen = GEN.get(est, COMMON)
    cmd = [sys.executable, "-c", _PROBE, ROOT, os.path.join(HERE, gen[0])]
    if gen is COMMON:
        cmd.append(est)
    cmd += ["--out", os.path.join(tmp, est + "_sashizu.html")]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if "@@READ@@" not in r.stderr:
        return None, r.stderr[-400:]
    if not os.path.exists(os.path.join(tmp, est + "_sashizu.html")):
        # ⛔ 途中で止まった生成器は、止まるまでに読んだ物しか見えない ── ⭕ と刷らない
        msg = [x for x in (r.stdout + r.stderr.split("@@READ@@")[0]).split("\n") if "⛔" in x]
        return None, "写しを焼く前に止まった: " + (msg[-1].strip() if msg else "(理由の行なし)")
    return [x for x in r.stderr.split("@@READ@@", 1)[1].split("\n") if x], None


def main(argv):
    quiet = "--quiet" in argv
    names = [a for a in argv if not a.startswith("--")]
    ests = names or estates()
    nbad = 0
    if "--inputs" in argv:
        with tempfile.TemporaryDirectory() as tmp:
            for e in ests:
                got, err = reads(e, tmp)
                if got is None:
                    print("⛔ %-16s 試し焼きが走らない: %s" % (e, err.strip().split("\n")[-1]))
                    nbad += 1
                    continue
                out = [p for p in got if not any(re.match(a, p) for a in ALLOW)]
                nbad += len(out)
                print("%s %-16s 読んだ %d ／ 許す範囲の外 %d" % ("⛔" if out else "⭕", e, len(got), len(out)))
                for p in out:
                    print("    ⛔ %s" % p)
        return 1 if nbad else 0
    rows = []
    for e in ests:
        p = os.path.join(DOC, e + "_sashizu.html")
        if not os.path.exists(p):
            rows.append((e, ["写しが無い(%s)" % os.path.relpath(p, ROOT)]))
            continue
        h = open(p, encoding="utf-8").read()
        m = re.search(r"<title>(.*?)</title>", h)
        rows.append((e, check_chapters(e, chapters(h), m.group(1) if m else "")))
    nbad = sum(1 for _, b in rows if b)
    if quiet and not nbad:
        return 0
    print("指図の写しの関門 — %s(`python3 Tools/Sashizu/utsushi_check.py`・決めごと2c)"
          % ("**章立てが決めごとから外れた写しが %d 邸**" % nbad if nbad else "全 %d 邸 ⭕" % len(rows)))
    for e, b in rows:
        if b or not quiet:
            print("  %s %-16s %s" % ("⛔" if b else "⭕", e, ("%d 件 — %s" % (len(b), b[0])) if b else "破れ 0 件"))
    if nbad:
        print("  ⚠ 建った敷地の写しは完成まで刷り直さない(規則4)ので、古い型のまま残る邸がある — "
              "刷るときに生成器が揃える。⛔ 写しを揃えるためだけに図を開かない。")
    return 1 if nbad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
