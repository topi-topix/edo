#!/usr/bin/env python3
"""建てる役が引く C# の目録を注釈から刷る(EDO-0456・2026-09-26)。三枚:

  docs/edobuild-mokuroku.md  据え方の関数(EdoBuild*.cs・EdoGeom.cs)と区画(EdoParcels.cs)
  docs/builder-mokuroku.md   邸ビルダー(Edo*Builder*.cs・Edo*Rebuild*.cs)のメニュー → Stage と中の関数(非公開も)
  docs/edoassets-mokuroku.md 部材の名(EdoAssets.cs の入れ子の分類ごと)と使っている所

  python3 Tools/Unity/edobuild_mokuroku.py            # 三枚を刷り直す
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
OUT_B = "docs/builder-mokuroku.md"
OUT_A = "docs/edoassets-mokuroku.md"
CMD = "python3 Tools/Unity/edobuild_mokuroku.py"
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


SIG = re.compile(r"^\s*(?P<mods>(?:(?:public|private|internal|protected|static|readonly|const|override|unsafe|new)\s+)+)"
                 r"(?P<ret>[\w<>\[\],.? ]+?)\s+(?P<name>\w+)\s*(?P<rest>[(=;{].*)$")
TYPE = re.compile(r"^\s*(?:(?:public|private|internal|static|partial|sealed|abstract)\s+)*(?P<kind>class|struct|enum)\s+(?P<name>\w+)")
MENU_RX = re.compile(r'\[MenuItem\(\s*(?:(?P<const>\w+)\s*\+\s*)?"(?P<label>[^"]*)"')


def header_of(lines):
    out = []
    lines = [l for l in lines if not l.startswith("using ")]
    for l in lines:
        if l.startswith("///"):
            break
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


def strip_code(l):
    """括弧を数えるために、注釈・文字列・文字('{')を消す。"""
    l = re.sub(r"'(?:\\.|[^'\\])'", "", l)
    l = re.sub(r'@"(?:""|[^"])*"', "", l)
    l = re.sub(r'"(?:\\.|[^"\\])*"', "", l)
    return re.sub(r"//.*$", "", l)


def parse_file(src, path, cls, nested=False, private=False):
    """cls の直下(nested なら入れ子の static class の中も)の宣言を拾う。
    private=True なら公開でない static 関数も拾う(邸ビルダー)。返り値 (冒頭, 当たる先, 項目, 定数)。"""
    text = src.read(path)
    lines = text.split("\n")
    head, ataru = header_of(lines)
    consts = dict(re.findall(r'const\s+string\s+(\w+)\s*=\s*"([^"]*)"', text))
    items, doc, cmt, attrs, section, depth = [], [], [], [], "", 0
    stack = []  # (名, 中の深さ)
    pend = None
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
        if st.startswith("//") and not re.match(r"//\s*[=-]{4,}", st):
            cmt.append(st[2:].strip())  # /// が無い関数は直前の // の注釈を採る
            i += 1
            continue
        if st.startswith("[") and not SIG.match(l):  # 属性は注釈と宣言の間に挟まってよい(複数行も)
            a = st
            while strip_code(a).count("[") > strip_code(a).count("]") and i + 1 < len(lines):
                i += 1
                a += " " + lines[i].strip()
            attrs.append(a)
            i += 1
            continue
        tm = TYPE.match(l)
        sm = None if tm else SIG.match(l)
        top = stack[-1] if stack else None
        here = top and depth == top[1]
        ok_scope = here and stack[0][0] == cls and (len(stack) == 1 or (nested and all(n != "" for n, _ in stack)))
        if ok_scope and (tm or sm):
            summ, ret, full = doc_parts(doc)
            if not doc and cmt:
                summ = full = " ".join(cmt)
            has_doc = bool(doc or cmt)
            obs = any("Obsolete" in a for a in attrs)
            menu = None
            for a in attrs:
                mm = MENU_RX.search(a)
                if mm:
                    menu = consts.get(mm.group("const"), "") + mm.group("label") if mm.group("const") else mm.group("label")
            owner = ".".join(n for n, _ in stack[1:])
            if tm:
                if tm.group("name") != cls:
                    items.append(dict(kind=tm.group("kind"), name=tm.group("name"), owner=owner, sig="", ret="",
                                      first=first_sentence(summ) if has_doc else "", full=clean(full),
                                      section=section, obs=obs, pub="public" in l))
            else:
                mods = sm.group("mods")
                pub = "public" in mods
                is_static = "static" in mods or "const" in mods
                if is_static and (pub or private):
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
                    kind = "const" if "const" in mods else ("method" if sm.group("rest").startswith("(") else "field")
                    val = ""
                    vm = re.search(r'=\s*"([^"]*)"', l)
                    if vm:
                        val = vm.group(1)
                    body = ""
                    if kind == "method":  # 本体の頭(メニュー → Stage の対応を採る)
                        body = " ".join(x.strip() for x in lines[i:i + 12])
                    items.append(dict(kind=kind, name=sm.group("name"), owner=owner, ret=sm.group("ret").strip(),
                                      sig=params, first=first_sentence(summ) if has_doc else "",
                                      rets=clean(ret) or rets_in(summ), full=clean(full), section=section,
                                      obs=obs, pub=pub, menu=menu, val=val, body=body))
        if st and not st.startswith("//"):
            doc, cmt, attrs = [], [], []
        elif not st:
            cmt = []
        if tm:
            pend = tm.group("name") if (tm.group("name") == cls or (stack and nested and stack[0][0] == cls)) else ""
        code = strip_code(l)
        for ch in code:
            if ch == "{":
                depth += 1
                if pend is not None:
                    stack.append((pend, depth))
                    pend = None
            elif ch == "}":
                if stack and stack[-1][1] == depth:
                    stack.pop()
                depth -= 1
        i += 1
    return head, ataru, items, consts


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


def callers(src, own, pat):
    """own の外の C# で pat(group1=キー)に当たる所 → {キー: {ファイルの短い名: {囲む関数}}}。"""
    hit = defaultdict(lambda: defaultdict(set))
    for rel in src.ls(SCAN_DIR):
        fn = os.path.basename(rel)
        if not fn.endswith(".cs") or fn in own:
            continue
        t = src.read(rel)
        who = short_name(fn)
        meth = [(m.start(), m.group(1)) for m in DEF.finditer(t)]
        for m in pat.finditer(t):
            enc = ""
            for pos, nm in meth:
                if pos > m.start():
                    break
                enc = nm
            hit[m.group(1)][who].add(enc)
    return hit


def short_name(fn):
    return re.sub(r"^Edo|(?:Builder|Rebuild|Stage)?\.cs$", "", fn)


def fmt_callers(c, n=5):
    def one(k, v):
        v = sorted(x for x in v if x)
        return k + ("(" + "・".join(v[:3]) + ("…" if len(v) > 3 else "") + ")" if v else "")
    who = ", ".join(one(k, v) for k, v in sorted(c.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:n])
    if len(c) > n:
        who += f" ほか{len(c) - n}"
    return who or "—"


def tags_of(full):
    hard = "・".join(t for t, ws in TAGS if any(w in full for w in ws))
    aite = "・".join(t for t, ws in AITE if any(w in full for w in ws))
    return hard, aite


def build(src):
    names = [os.path.basename(p) for p in src.ls(SRC_DIR) if os.path.dirname(p) == SRC_DIR]
    files = sorted(f"{SRC_DIR}/{f}" for f in names if re.match(r"EdoBuild\w*\.cs$", f) and f != "EdoBuild.cs")
    files = [f"{SRC_DIR}/EdoBuild.cs"] + files + [f"{SRC_DIR}/EdoGeom.cs", f"{SRC_DIR}/EdoParcels.cs"]
    own = {os.path.basename(f) for f in files}
    call = callers(src, own, re.compile(r"\b((?:EdoBuild|EdoGeom|EdoParcels)\.\w+)\s*[(<]"))
    parsed = []
    for f in files:
        cls = os.path.basename(f)[:-3]
        cls = "EdoBuild" if cls.startswith("EdoBuild") else cls
        parsed.append((f, cls) + parse_file(src, f, cls)[:3])
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
                if not it["pub"]:
                    continue
                rows.append(f"| `{it['name']}`({it['kind']}) | — | | {it['first'] or '(注釈なし)'} | |")
                continue
            hard, aite = tags_of(it["full"])
            tag = " ".join(x for x in (hard, aite) if x)
            who = fmt_callers(call.get(f"{cls}.{it['name']}", {}))
            what = it["first"] or "⚠ 注釈なし"
            if it.get("rets"):
                what += f" ⟶ 返す: {first_sentence(it['rets'])}"
            name = f"`{cls}.{it['name']}({short_sig(it['sig'])})`" if it["kind"] == "method" else f"`{cls}.{it['name']}`"
            rows.append(f"| {name} | `{it['ret']}` | {tag} | {what} | {who} |")
        flush()
    fp = hashlib.sha1("\n".join(body).encode()).hexdigest()[:12]
    head = [
        "# EdoBuild の据え方の関数の目録(生成物・手で直さない)",
        "",
        f"<!-- 生成: {CMD} · 指紋 {fp} -->",
        "",
        "**据え方の関数を探すときは C# を grep で読み歩かず、まずここを引く。**置き方の手順と相手ごとの道具の選び方は",
        "`docs/oki-kata.md`(正典)。ここは「どの関数が在り、何を返し、どこで使われているか」の索引だけ。",
        "",
        f"- 公開関数 {n_fn} 本(注釈なし {n_nodoc})。`{SRC_DIR}/EdoBuild*.cs`・`EdoGeom.cs`・`EdoParcels.cs`(区画)の `///` 注釈から刷る。",
        f"- 同じ道具が刷る目録: 邸ビルダーのメニュー → Stage と中の関数 `{OUT_B}` / 部材の名 `{OUT_A}`。",
        "- 札: **硬** = 注釈に「硬い/許容0」・**柔** = 「柔らかい/狙い」がある(判定ではなく注釈の語)。"
        "相手の札(地面・駒どうし・天端・床・断面・面・隅・区域)も注釈の語を拾っただけ。",
        "- 呼んでいる所 = 定義のファイルの外で `EdoBuild.<名>(` と書いている C# ファイル(`Edo` と `Builder/Rebuild` を落とした名)と、その中の呼んでいる関数(Stage)。"
        "同じ名の多重定義はまとめて数える。`EdoBuild` の中どうしの呼び出しは載せない。",
        "- 関数へ跳ぶ: `grep -n \"static .* <名>(\" Assets/Edo/Scripts/Editor/<ファイル>` → その行から読む。",
        f"- ⛔ 手で直さない。関数を足した・注釈を直したら `{CMD}` で刷り直し、C# と同じコミットに入れる。",
        "",
    ]
    return "\n".join(head + body) + "\n"


def build_builders(src):
    names = [os.path.basename(p) for p in src.ls(SRC_DIR) if os.path.dirname(p) == SRC_DIR]
    files = sorted(f"{SRC_DIR}/{f}" for f in names if re.match(r"Edo\w+(?:Builder|Rebuild)(?:\.\w+)?\.cs$", f))
    body, n_fn, n_menu = [], 0, 0
    idx = ["## ファイルの索引\n", "| ファイル | 何の道具か(ファイル冒頭の注釈) | メニュー | 関数 |", "|---|---|---|---|"]
    for f in files:
        fn = os.path.basename(f)
        cls = fn[:-3].split(".")[0]
        head, ataru, items, consts = parse_file(src, f, cls, private=True)
        meths = [it for it in items if it["kind"] == "method"]
        own = {it["name"] for it in meths}
        menus = [it for it in meths if it.get("menu")]
        n_fn += len(meths)
        n_menu += len(menus)
        idx.append(f"| [{fn}](#{fn.lower().replace('.', '')}) | {head or '—'} | {len(menus)} | {len(meths)} |")
        body.append(f"## {fn}\n")
        if head:
            body.append(f"{head}\n")
        if menus:
            body.append("| メニュー | 関数 | 呼ぶ関数(Stage) |")
            body.append("|---|---|---|")
            for it in menus:
                called = []
                for c in re.findall(r"\b(\w+)\s*\(", it["body"].split("{", 1)[-1]):
                    if c in own and c != it["name"] and c not in called:
                        called.append(c)
                body.append(f"| `{it['menu']}` | `{it['name']}` | {', '.join('`' + c + '`' for c in called[:4]) or '—'} |")
            body.append("")
        rows = [it for it in meths if not it.get("menu")]
        if rows:
            body.append("| 関数 | 返す | 公開 | 何をするか(注釈の一文目) |")
            body.append("|---|---|---|---|")
            for it in rows:
                what = it["first"] or "—"
                if it.get("rets"):
                    what += f" ⟶ 返す: {first_sentence(it['rets'])}"
                body.append(f"| `{it['name']}({short_sig(it['sig'])})` | `{it['ret']}` | {'公' if it['pub'] else ''} | {what} |")
            body.append("")
    idx.append("")
    head = [
        "# 邸ビルダーの目録(生成物・手で直さない)",
        "",
        "<!-- 生成: " + CMD + " -->",
        "",
        "**メニューの名・Stage の関数・ビルダーの中の関数を探すときは、C# を grep で読み歩かずまずここを引く。**",
        "Stage の本体(何をどの順に据えるか)は目録に無い — 名を決めてから、その関数の行だけ読む。",
        "",
        f"- `{SRC_DIR}/Edo*Builder*.cs`・`Edo*Rebuild*.cs` {len(files)} 本・メニュー {n_menu}・関数 {n_fn}(非公開も)。",
        "- メニューは Unity の `execute_menu_item` にそのまま渡せる全名。呼ぶ関数 = メニューの関数の頭で呼んでいる同じファイルの関数。",
        "- 関数へ跳ぶ: `grep -n \"static .* <名>(\" Assets/Edo/Scripts/Editor/<ファイル>`。",
        f"- 据え方の関数は `{OUT}`、部材の名は `{OUT_A}`。⛔ 手で直さない(`{CMD}`)。",
        "",
    ]
    return "\n".join(head + idx + body) + "\n"


def build_assets(src):
    f = f"{SRC_DIR}/EdoAssets.cs"
    head, ataru, items, consts = parse_file(src, f, "EdoAssets", nested=True)
    call = callers(src, {"EdoAssets.cs"}, re.compile(r"\bEdoAssets\.((?:[A-Z]\w*\.)*\w+)"))
    body, sec, n = [], None, 0
    for it in items:
        if it["kind"] in ("class", "struct", "enum"):
            continue
        grp = it["owner"] or "(直下)"
        if grp != sec:
            seen_grp = [g for g in body if g.startswith("## " + grp + "\n") or g.startswith("## " + grp + "(続き)")]
            if body:
                body.append("")
            sec = grp
            body.append(f"## {grp}" + ("(続き)" if seen_grp else "") + "\n")
            body.append("| 名 | 種 | 中身・注釈の一文目 | 使っている所 |")
            body.append("|---|---|---|---|")
        n += 1
        key = (it["owner"] + "." if it["owner"] else "") + it["name"]
        what = it["first"] or ""
        if it["val"]:
            what = f"`{os.path.basename(it['val'])}`" + (" — " + what if what else "")
        if it["obs"]:
            what = "⛔ 使用禁止(Obsolete)。" + what
        kind = "関数" if it["kind"] == "method" else it["ret"]
        nm = f"`{key}({short_sig(it['sig'])})`" if it["kind"] == "method" else f"`{key}`"
        body.append(f"| {nm} | {kind} | {what or '—'} | {fmt_callers(call.get(key, {}), 4)} |")
    head_ = [
        "# 部材の名の目録 — EdoAssets(生成物・手で直さない)",
        "",
        "<!-- 生成: " + CMD + " -->",
        "",
        "**部材のパスの名を探すときは `EdoAssets.cs` を grep で読み歩かずまずここを引く。**在庫に何が在るか"
        "(実寸・ピボット)は `docs/asset-catalog.md` → `docs/asset-index.tsv`。ここは C# から呼べる名の索引だけ。",
        "",
        f"- `{f}` の公開の名 {n}(入れ子の分類ごと)。中身 = 定数ならパスの末尾、関数なら注釈の一文目。",
        "- 使っている所 = `EdoAssets.<分類>.<名>` と書いている C# ファイルとその中の関数。",
        f"- ⛔ 手で直さない(`{CMD}`)。",
        "",
    ]
    return "\n".join(head_ + body) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="古ければ 1 を返す")
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--ref", help="この版の C# から刷る(既定: Assets の在る木は作業の木・疎な worktree は HEAD)")
    a = ap.parse_args()
    top = toplevel()
    src = Src(top, a.ref)
    outs = [(OUT, build(src)), (OUT_B, build_builders(src)), (OUT_A, build_assets(src))]
    if a.stdout:
        for _, t in outs:
            sys.stdout.write(t)
        return 0
    stale = []
    for rel, text in outs:
        path = os.path.join(top, rel)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if old == text:
            continue
        stale.append(rel)
        if not a.check:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"刷った: {rel}")
    if a.check:
        if stale:
            print(f"⚠ C# の目録が古い({'・'.join(stale)})→ {CMD} で刷り直し、C# と同じコミットに入れる")
            return 1
        return 0
    if not stale:
        print("変わりなし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
