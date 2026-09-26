#!/usr/bin/env python3
"""EdoBuild の据え方の関数の目録を C# の注釈から刷る(EDO-0456・2026-09-26)。

  python3 Tools/Unity/edobuild_mokuroku.py            # docs/edobuild-mokuroku.md を刷り直す
  python3 Tools/Unity/edobuild_mokuroku.py --check    # 古ければ 1 を返す(刷り直しの命令を出す)

⭐ 狙い: 建てる役が「据え方の関数を探すための既存 C# の grep の読み歩き」をせずに、目録を一度引けば
   関数名・返す物・硬い/柔らかい・どの邸の何が使っているかが分かること(EDO-0437 の実測で考える時間の約25%)。
⭐ 目録は**手で書かない**。C# の `///` 注釈(summary / returns)とファイル冒頭の注釈から機械で刷る。
   関数を足した・注釈を直したら、C# と一緒に刷り直してコミットする(`cs_check.sh` が古さを知らせる)。
⛔ 置き方の手順は目録に書き写さない — 正典は docs/oki-kata.md。目録は「どの関数が在るか」の索引だけ。
⚠ 行番号は載せない(C# を1行直すたびに目録が古くなる)。関数へは
   `grep -n "static .* <名>(" Assets/Edo/Scripts/Editor/<ファイル>` で跳ぶ。
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys
from collections import defaultdict

SRC_DIR = "Assets/Edo/Scripts/Editor"
SCAN_DIR = "Assets/Edo/Scripts"
OUT = "docs/edobuild-mokuroku.md"
FIRST_MAX = 110

# 注釈の語 → 目録の札。どれも**注釈に書いてある語を拾うだけ**で、判定を足さない。
TAGS = [
    ("硬", ("硬い", "許容0")),
    ("柔", ("柔らかい", "狙い")),
]
AITE = [  # 何を測る/何に効くか(注釈に出る語)
    ("地面", ("地表", "地面", "地形", "SampleHeight")),
    ("駒どうし", ("駒どうし", "部材どうし", "相手の駒", "相手の面", "突き付け")),
    ("天端", ("天端",)),
    ("床", ("床", "礎石", "受け")),
    ("断面", ("断面",)),
    ("面", ("見え面", "実面", "前面", "背面", "面を測")),
    ("隅", ("出隅", "入隅", "隅の駒", "留め継ぎ")),
    ("区域", ("区画", "区域", "PIP")),
]


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


class Src:
    """読む元。作業の木(Assets が在る木)ならその木のファイル、疎な worktree(Assets を持たない)なら
    その worktree の HEAD のコミットから読む。⚠ 本体の作業の木は読まない — 他のセッションがまだ
    コミットしていない C# が目録に混ざるため(2026-09-26)。"""

    def __init__(self, top, ref=None):
        self.top, self.ref = top, ref
        if ref is None and not os.path.isdir(os.path.join(top, SRC_DIR)):
            self.ref = "HEAD"

    def ls(self, d):
        if self.ref is None:
            out = []
            for dp, _, fs in os.walk(os.path.join(self.top, d)):
                out += [os.path.relpath(os.path.join(dp, f), self.top) for f in fs]
            return sorted(out)
        return sorted(git(self.top, "ls-tree", "-r", "--name-only", self.ref, "--", d).splitlines())

    def read(self, rel):
        if self.ref is None:
            with open(os.path.join(self.top, rel), encoding="utf-8", errors="replace") as f:
                return f.read()
        return subprocess.run(["git", "-C", self.top, "show", f"{self.ref}:{rel}"],
                              capture_output=True, text=True).stdout


def toplevel():
    here = os.path.dirname(os.path.abspath(__file__))
    return git(here, "rev-parse", "--show-toplevel") or os.path.abspath(os.path.join(here, "..", ".."))


def clean(s):
    s = re.sub(r'<see cref="([^"]+)"\s*/>', lambda m: m.group(1).split("(")[0], s)
    s = re.sub(r'<(?:paramref|typeparamref) name="([^"]+)"\s*/>', r"\1", s)
    s = re.sub(r"</?(?:c|para|b|i|code|list|item|description|term)>", "", s)
    s = s.replace("**", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace("|", "／")


def first_sentence(s):
    s = clean(s)
    ends = [m.end() for m in re.finditer(r"。", s)]
    cut = next((e for e in ends if e >= 20), None)  # 「突き付け。」のような見出しだけの一文は次の文まで採る
    if cut and cut <= FIRST_MAX + 40:
        s = s[:cut]
    if len(s) > FIRST_MAX:
        s = s[:FIRST_MAX].rstrip() + "…"
    return s


def rets_in(summ):
    m = re.search(r"(?:返り値|戻り値|返す)\s*[=は:]\s*(.+?)(?:。|$)", clean(summ))
    return m.group(1) if m else ""


def doc_parts(lines):
    txt = "\n".join(re.sub(r"^\s*///\s?", "", l) for l in lines)
    summ = re.search(r"<summary>(.*?)</summary>", txt, re.S)
    ret = re.search(r"<returns>(.*?)</returns>", txt, re.S)
    return (summ.group(1) if summ else txt), (ret.group(1) if ret else ""), txt


SIG = re.compile(r"^\s*public\s+(?:static\s+)?(?:readonly\s+)?(?:const\s+)?(?P<ret>[\w<>\[\],.? ]+?)\s+(?P<name>\w+)\s*(?P<rest>[(=;{].*)$")
TYPE = re.compile(r"^\s*public\s+(?:static\s+)?(?:partial\s+)?(?P<kind>class|struct|enum)\s+(?P<name>\w+)")


def header_of(lines):
    out = []
    lines = [l for l in lines if not l.startswith("using ")]
    for l in lines:
        if l.startswith("//"):
            out.append(l[2:].strip())
        elif l.strip() == "":
            if out:
                break
        else:
            break
    head = clean(out[0]) if out else ""
    ataru = ""
    for i, l in enumerate(out):
        if "当たる先" in l:
            buf = [l]
            for m in out[i + 1:]:
                if not m or re.match(r"^[⭐⛔⚠⭕]|^[・]", m):
                    break
                buf.append(m)
            ataru = first_sentence(" ".join(buf).split("当たる先", 1)[1].lstrip(":: "))
            break
    return head, ataru


def parse_file(src, path, cls):
    lines = src.read(path).split("\n")
    head, ataru = header_of(lines)
    items, doc, cmt, section, depth = [], [], [], "", 0
    i = 0
    while i < len(lines):
        l = lines[i]
        m = re.match(r"^\s*//\s*={8,}\s*(.+)$", l)
        if m:
            section = clean(m.group(1))
        st = l.strip()
        if st.startswith("///"):
            doc.append(l)
            i += 1
            continue
        if st.startswith("//") and not st.startswith("///") and not re.match(r"//\s*[=-]{4,}", st):
            cmt.append(st[2:].strip())  # /// が無い関数は直前の // の注釈を採る
            i += 1
            continue
        if st.startswith("[") and doc:  # 属性は注釈と宣言の間に挟まってよい
            i += 1
            continue
        tm = TYPE.match(l)
        sm = SIG.match(l) if "public" in l and not tm else None
        # 入れ子の型の中の public(型の欄)は拾わない — 深さ 1(= partial class の直下)だけ
        if depth == 1 and (tm or sm):
            summ, ret, full = doc_parts(doc)
            if not doc and cmt:
                summ = full = " ".join(cmt)
            doc = doc or cmt
            if tm and tm.group("name") != cls:
                items.append(dict(kind=tm.group("kind"), name=tm.group("name"), sig="", ret="",
                                  first=first_sentence(summ) if doc else "", full=clean(full), section=section))
            elif sm and "static" in l or (sm and " const " in l):
                sig = l.strip()
                j = i
                while "(" in sig and sig.count("(") > sig.count(")") and j + 1 < len(lines):
                    j += 1
                    sig += " " + lines[j].strip()
                params = ""
                pm = re.search(r"\((.*)\)", sig)
                if pm and sm.group("rest").startswith("("):
                    params = re.sub(r"\s+", " ", pm.group(1))
                    params = re.sub(r"\)\s*(?:where .*|=>.*|\{.*)?$", "", params)
                kind = "const" if " const " in l else ("method" if sm.group("rest").startswith("(") else "field")
                items.append(dict(kind=kind, name=sm.group("name"), ret=sm.group("ret").strip(),
                                  sig=params, first=first_sentence(summ) if doc else "",
                                  rets=clean(ret) or rets_in(summ), full=clean(full), section=section))
        if st and not st.startswith("//"):
            doc, cmt = [], []
        elif not st:
            cmt = []
        code = re.sub(r'"(?:\\.|[^"\\])*"', "", re.sub(r"//.*$", "", l))
        depth += code.count("{") - code.count("}")
        i += 1
    return head, ataru, items


def short_sig(p):
    if not p:
        return ""
    out, parts_, depth, cur = [], [], 0, ""
    for ch in p:
        depth += ch in "<([" and 1 or (ch in ">)]" and -1 or 0)
        if ch == "," and depth == 0:
            parts_.append(cur); cur = ""
        else:
            cur += ch
    parts_.append(cur)
    for a in parts_:
        a = a.strip()
        a = re.sub(r"\s*=\s*[^,]+$", "=…", a)
        parts = a.split()
        out.append(parts[-1] if parts else a)
    return ", ".join(out)


DEF = re.compile(r"^[ \t]*(?:public|internal|private|static)[\w<>\[\], \t]*?\s(\w+)\s*\([^;{]*?\)\s*(?:\{|$)", re.M)


def callers(src, files):
    own = {os.path.basename(f) for f in files}
    hit = defaultdict(lambda: defaultdict(set))
    pat = re.compile(r"\b(EdoBuild|EdoGeom)\.(\w+)\s*[(<]")
    for rel in src.ls(SCAN_DIR):
        fn = os.path.basename(rel)
        if True:
            if not fn.endswith(".cs") or fn in own:
                continue
            t = src.read(rel)
            who = re.sub(r"^Edo|(?:Builder|Rebuild|Stage)?\.cs$", "", fn)
            meth = [(m.start(), m.group(1)) for m in DEF.finditer(t)]
            for m in pat.finditer(t):
                enc = ""
                for pos, nm in meth:
                    if pos > m.start():
                        break
                    enc = nm
                hit[(m.group(1), m.group(2))][who].add(enc)
    return hit


def tags_of(full):
    hard = "・".join(t for t, ws in TAGS if any(w in full for w in ws))
    aite = "・".join(t for t, ws in AITE if any(w in full for w in ws))
    return hard, aite


def build(src):
    names = [os.path.basename(p) for p in src.ls(SRC_DIR) if os.path.dirname(p) == SRC_DIR]
    files = sorted(f"{SRC_DIR}/{f}" for f in names if re.match(r"EdoBuild\w*\.cs$", f) and f != "EdoBuild.cs")
    files = [f"{SRC_DIR}/EdoBuild.cs"] + files + [f"{SRC_DIR}/EdoGeom.cs"]
    call = callers(src, files)
    parsed = []
    for f in files:
        cls = "EdoGeom" if f.endswith("EdoGeom.cs") else "EdoBuild"
        parsed.append((f, cls) + parse_file(src, f, cls))
    n_fn = sum(1 for p in parsed for it in p[4] if it["kind"] == "method")
    n_nodoc = sum(1 for p in parsed for it in p[4] if it["kind"] == "method" and not it["first"])
    body = []
    body.append("## ファイルの索引\n")
    body.append("| ファイル | 何の道具か(ファイル冒頭の注釈) | 当たる先 | 関数 |")
    body.append("|---|---|---|---|")
    for f, cls, head, ataru, items in parsed:
        fn = os.path.basename(f)
        k = sum(1 for it in items if it["kind"] == "method")
        body.append(f"| [{fn}](#{fn.lower().replace('.', '')}) | {head or '—'} | {ataru or '—'} | {k} |")
    body.append("")
    for f, cls, head, ataru, items in parsed:
        fn = os.path.basename(f)
        body.append(f"## {fn}\n")
        if head:
            body.append(f"{head}\n")
        sec = None
        rows = []
        def flush():
            if rows:
                body.append("| 関数 | 返す | 札 | 何をするか(注釈の一文目) | 呼んでいる所 |")
                body.append("|---|---|---|---|---|")
                body.extend(rows)
                body.append("")
                rows.clear()
        for it in items:
            if it["section"] != sec:
                flush()
                sec = it["section"]
                if sec:
                    body.append(f"### {sec}\n")
            if it["kind"] in ("class", "struct", "enum"):
                rows.append(f"| `{it['name']}`({it['kind']}) | — | | {it['first'] or '(注釈なし)'} | |")
                continue
            hard, aite = tags_of(it["full"])
            tag = " ".join(x for x in (hard, aite) if x)
            c = call.get((cls, it["name"]), {})
            def fmt(k, v):
                v = sorted(x for x in v if x)
                return k + ("(" + "・".join(v[:3]) + ("…" if len(v) > 3 else "") + ")" if v else "")
            who = ", ".join(fmt(k, v) for k, v in sorted(c.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:5])
            if len(c) > 5:
                who += f" ほか{len(c) - 5}"
            what = it["first"] or "⚠ 注釈なし"
            if it.get("rets"):
                what += f" ⟶ 返す: {first_sentence(it['rets'])}"
            name = f"`{cls}.{it['name']}({short_sig(it['sig'])})`" if it["kind"] == "method" else f"`{cls}.{it['name']}`"
            rows.append(f"| {name} | `{it['ret']}` | {tag} | {what} | {who or '—'} |")
        flush()
    fp = hashlib.sha1("\n".join(body).encode()).hexdigest()[:12]
    head = [
        "# EdoBuild の据え方の関数の目録(生成物・手で直さない)",
        "",
        f"<!-- 生成: python3 Tools/Unity/edobuild_mokuroku.py · 指紋 {fp} -->",
        "",
        "**据え方の関数を探すときは C# を grep で読み歩かず、まずここを引く。**置き方の手順と相手ごとの道具の選び方は",
        "`docs/oki-kata.md`(正典)。ここは「どの関数が在り、何を返し、どこで使われているか」の索引だけ。",
        "",
        f"- 公開関数 {n_fn} 本(注釈なし {n_nodoc})。`{SRC_DIR}/EdoBuild*.cs` と `EdoGeom.cs` の `///` 注釈から刷る。",
        "- 札: **硬** = 注釈に「硬い/許容0」・**柔** = 「柔らかい/狙い」がある(判定ではなく注釈の語)。"
        "相手の札(地面・駒どうし・天端・床・断面・面・隅・区域)も注釈の語を拾っただけ。",
        "- 呼んでいる所 = `EdoBuild*.cs` の外で `EdoBuild.<名>(` と書いている C# ファイル(`Edo` と `Builder/Rebuild` を落とした名)と、その中の呼んでいる関数(Stage)。"
        "同じ名の多重定義はまとめて数える。`EdoBuild` の中どうしの呼び出しは載せない。",
        "- 関数へ跳ぶ: `grep -n \"static .* <名>(\" Assets/Edo/Scripts/Editor/<ファイル>` → その行から読む。",
        "- ⛔ 手で直さない。関数を足した・注釈を直したら `python3 Tools/Unity/edobuild_mokuroku.py` で刷り直し、C# と同じコミットに入れる。",
        "",
    ]
    return "\n".join(head + body) + "\n", fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="古ければ 1 を返す")
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--ref", help="この版の C# から刷る(既定: Assets の在る木は作業の木・疎な worktree は HEAD)")
    a = ap.parse_args()
    top = toplevel()
    text, fp = build(Src(top, a.ref))
    out = os.path.join(top, OUT)
    if a.stdout:
        sys.stdout.write(text)
        return 0
    old = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
    if a.check:
        if old != text:
            print(f"⚠ 据え方の関数の目録が古い({OUT})→ python3 Tools/Unity/edobuild_mokuroku.py で刷り直し、C# と同じコミットに入れる")
            return 1
        return 0
    if old != text:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"刷った: {OUT}(指紋 {fp})")
    else:
        print(f"変わりなし: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
