#!/usr/bin/env python3
"""岡部筑前守上屋敷の指図を組む。

    python3 Tools/Sashizu/build_okabe_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/okabe_sashizu.json … 設計値の正典（人が書く）
    docs/Sashizu/okabe_kosho.md     … 文章の部（人が書く・現況形）

の二つだけで、それを一枚の HTML に組む。実装から指図を作ると
CLAUDE.md 絶対規則2「指図を先に起こす」の関門が消える（ユーザー指摘 2026-08-20）。

【流れ】
    1. 設計   docs/Sashizu/*.json / *.md を直す
    2. 組む   このスクリプト
    3. 検図   edo-kosho（史実）と edo-kenzu（図の成立）→ ユーザーのレビュー
    4. 実装   ビルダーの表を指図に合わせる
    5. 突合   Unity の「Edo ▸ 岡部筑前守上屋敷 ▸ 指図と実装を突き合わせる」で 0 件を確認
              建ててみて指図が誤りと分かったら **指図を直してから** 合わせ直す
    6. 経緯   コミットメッセージと git log。**指図には残さない**

数値は json にしか無い（この文書にも markdown にも写さない）ので、二重管理が起きない。
"""
import json, os, re, subprocess, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "okabe_sashizu.json")
MD = os.path.join(DOC, "okabe_kosho.md")
OUT = os.path.join(DOC, "okabe_sashizu.html")
TSUBO = 3.305785


# ---------------------------------------------------------------- markdown
def md2html(text):
    """指図の文章に要る分だけの最小変換（見出し・表・箇条書き・強調・コード）。"""
    out, i, lines = [], 0, text.split("\n")
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in ln.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")]); i += 1
            out.append('<div class="tw"><table><thead><tr>'
                       + "".join("<th>%s</th>" % inline(h) for h in head)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join('<td class="note">%s</td>' % inline(c) for c in r) + "</tr>" for r in rows)
                       + "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lv = len(m.group(1))
            tag = {1: "h1", 2: "h2", 3: "h3", 4: "h4"}[lv]
            out.append("<%s>%s</%s>" % (tag, inline(m.group(2)), tag)); i += 1; continue
        if ln.startswith("- "):
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("  ")):
                if lines[i].startswith("- "):
                    items.append(inline(lines[i][2:]))
                elif items:
                    items[-1] += " " + inline(lines[i].strip())
                i += 1
            out.append("<ul>" + "".join("<li>%s</li>" % t for t in items) + "</ul>"); continue
        if ln.strip() == "---":
            out.append('<hr class="rule">'); i += 1; continue
        if ln.strip() == "":
            i += 1; continue
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "-", "|")) and lines[i].strip() != "---":
            buf.append(lines[i].strip()); i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"【([^】]*確度 ?[SABPU?][^】]*)】", r'<span class="cert">【\1】</span>', s)
    return s


# ---------------------------------------------------------------- 図
def plan_svg(d):
    """敷地の平面。区画・段・外周の種別・隅・門を一枚に。"""
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    x0, x1, z0, z1 = min(xs) - 12, max(xs) + 12, min(zs) - 12, max(zs) + 12
    W, H = 900.0, 900.0 * (z1 - z0) / (x1 - x0)
    def X(v): return (v - x0) / (x1 - x0) * W
    def Y(v): return H - (v - z0) / (z1 - z0) * H     # z は北が上

    g = ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="岡部筑前守上屋敷 敷地全体">' % (W, H)]
    # 段
    col = {25.5: "var(--dan1)", 19.5: "var(--dan2)", 13.5: "var(--dan3)", 11.5: "var(--dan4)"}
    for t in d["terraces"]:
        g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.65"/>'
                 % (X(t["x0"]), Y(t["z1"]), X(t["x1"]) - X(t["x0"]), Y(t["z0"]) - Y(t["z1"]),
                    col.get(t["y"], "var(--dan4)")))
        g.append('<text class="sl" x="%.1f" y="%.1f" text-anchor="middle">%s %.1f</text>'
                 % ((X(t["x0"]) + X(t["x1"])) / 2, (Y(t["z0"]) + Y(t["z1"])) / 2, t["name"], t["y"]))
    # 区画線
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (X(p[0]), Y(p[1])) for p in P))
    for i, p in enumerate(P):
        g.append('<circle cx="%.1f" cy="%.1f" r="2.4" fill="var(--ink)"/>' % (X(p[0]), Y(p[1])))
        g.append('<text class="jo" x="%.1f" y="%.1f">P%d</text>' % (X(p[0]) + 5, Y(p[1]) - 5, i))
    # 外周の run（種別で色分け）
    kc = {"Tsuiji": "var(--hei)", "Nagaya": "var(--nagaya)", "Takegaki": "var(--take)", "None": "var(--dim)"}
    for r in d["runs"]:
        a, b = r["a"], r["b"]
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="5" stroke-linecap="round"/>'
                 % (X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), kc.get(r["kind"], "var(--dim)")))
    # 郭の土留め
    for w in d["terraceWalls"]:
        a, b = w["a"], w["b"]
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--ishi)" stroke-width="3" stroke-dasharray="7 4"/>'
                 % (X(a[0]), Y(a[1]), X(b[0]), Y(b[1])))
    # 隅・門・櫓
    for c in d["corners"]:
        if c["part"] != "Ishigaki":
            continue
        g.append('<circle cx="%.1f" cy="%.1f" r="7" fill="none" stroke="var(--shu)" stroke-width="2"/>'
                 % (X(c["v"][0]), Y(c["v"][1])))
    for y in d["yagura"]:
        g.append('<rect x="%.1f" y="%.1f" width="9" height="9" fill="var(--shu)"/>'
                 % (X(y["pos"][0]) - 4.5, Y(y["pos"][1]) - 4.5))
    gp = d["gate"]["pos"]
    g.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>' % (X(gp[0]), Y(gp[1])))
    g.append('<text class="sr" x="%.1f" y="%.1f">表門</text>' % (X(gp[0]) + 9, Y(gp[1]) + 4))
    g.append("</svg>")
    return "\n".join(g)


def runs_table(d):
    rows = []
    for r in d["runs"]:
        w = r.get("wall") or "—"
        rows.append("<tr><td>%s</td><td>%s</td><td>%.1f</td><td>%.1f</td><td>%.1f</td><td class='note'>%s</td></tr>"
                    % (r["name"], {"Tsuiji": "築地塀", "Nagaya": "長屋塀", "Takegaki": "竹垣", "None": "囲い無し"}
                       .get(r["kind"], r["kind"]), r["len"], r["top"], r["seat"], w))
    return ("<div class='tw'><table><thead><tr><th>run</th><th>囲い</th><th>延長 m</th>"
            "<th>地盤 top</th><th>天端 seat</th><th class='note'>足元の石垣</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def walls_table(d):
    rows = ["<tr><td>%s</td><td>%.1f</td><td>%.1f</td><td>%.2f</td><td>%.1f</td><td>%.1f</td><td>%.1f</td></tr>"
            % (w["name"], w["len"], w["coping"], w["s"], 4 * w["s"], 1.4 * w["s"], 2.4 * w["s"])
            for w in d["terraceWalls"]]
    return ("<div class='tw'><table><thead><tr><th>石垣</th><th>延長 m</th><th>天端</th><th>s</th>"
            "<th>壁高</th><th>天端幅</th><th>底厚</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def corners_table(d):
    nm = {"Ishigaki": "石垣", "Dobei": "築地塀", "Nagaya": "長屋"}
    rows = ["<tr><td>%s</td><td class='note'>%s → %s</td><td>%.1f°</td></tr>"
            % (nm.get(c["part"], c["part"]), c["in"], c["out"], c["deg"]) for c in d["corners"]]
    rows += ["<tr><td>隅櫓</td><td class='note'>%s</td><td>底 %.2f</td></tr>" % (y["name"], y["base"])
             for y in d["yagura"]]
    return ("<div class='tw'><table><thead><tr><th>部材</th><th class='note'>場所</th><th>折れ角／高さ</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def munes_table(d):
    ken = d["const"]["ken"]
    rows = []
    for m in d["munes"]:
        area = m["kw"] * m["kd"] * ken * ken
        rows.append("<tr><td>%s</td><td>%d×%d</td><td>%d×%d</td><td>%.1f</td><td>%.0f</td></tr>"
                    % (m["name"], m["kw"], m["kd"], m["kw"] - 2, m["kd"] - 2, m["y"], area))
    return ("<div class='tw'><table><thead><tr><th>棟</th><th>外形(間)</th><th>身舎(間)</th>"
            "<th>床の高さ</th><th>外形 m²</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def history():
    """経緯は指図に書かない。git log への入口だけ置く。"""
    try:
        out = subprocess.check_output(
            ["git", "log", "-12", "--date=short", "--format=%h|%ad|%s", "--", "docs/Sashizu", "Assets/Edo/Scripts/Editor/EdoOkabeYashikiBuilder.cs"],
            cwd=ROOT, stderr=subprocess.DEVNULL).decode()
    except Exception:
        return "<p class='cap'>git log が読めなかった。</p>"
    rows = []
    for ln in out.strip().split("\n"):
        if not ln:
            continue
        h, dt, sub = ln.split("|", 2)
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td class='note'>%s</td></tr>"
                    % (h, dt, html.escape(sub)))
    return ("<div class='tw'><table><thead><tr><th>commit</th><th>日付</th><th class='note'>件名</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- 組み立て
def main():
    d = json.load(open(JSON, encoding="utf-8"))
    prose = md2html(open(MD, encoding="utf-8").read())
    xs = [p[0] for p in d["polygon"]]; zs = [p[1] for p in d["polygon"]]
    area = abs(sum(d["polygon"][i][0] * d["polygon"][(i + 1) % len(d["polygon"])][1]
                   - d["polygon"][(i + 1) % len(d["polygon"])][0] * d["polygon"][i][1]
                   for i in range(len(d["polygon"])))) / 2

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()
    h = ["<title>岡部筑前守上屋敷 指図</title>", "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">赤坂 山王社北 ／ 譜代雁間 五万三千石 上屋敷</p>')
    h.append("<h1>岡部筑前守上屋敷 指図</h1>")
    h.append('<p class="lede"><b>この文書は現況だけを載せる。</b>過去の案・撤回した説は書かない — '
             '経緯は <code>git log docs/Sashizu/</code> で追う。'
             '寸法の正典は <code>okabe_sashizu.json</code>、文章は <code>okabe_kosho.md</code> で、'
             'この HTML は <code>Tools/Sashizu/build_okabe_sashizu.py</code> が組む。'
             '<b>数値をこの文書に書き足さないこと</b>（写した瞬間に二重管理が始まる）。</p>')
    h.append('<div class="box"><h3>作る順序</h3><p>'
             '① 設計＝<code>json</code>／<code>md</code> を直す　→　② 組む　→　③ 検図（edo-kosho / edo-kenzu）'
             '→ ユーザーのレビュー　→　④ 実装　→　⑤ Unity の「指図と実装を突き合わせる」で 0 件を確認'
             '　→　⑥ 経緯はコミットへ。<br>'
             '建ててみて指図のほうが誤りと分かったときは、<b>指図を直してから</b>実装を合わせ直す。'
             '実装から指図を生成してはならない — 先に図を描く関門が消える。</p></div>')

    h.append('<div class="plate"><div class="phead"><h2>其一　敷地</h2>'
             '<span class="meta">%.0f m²（%.0f坪）／ 江戸間 1間 = %.3fm</span></div>'
             % (area, area / TSUBO, d["const"]["ken"]))
    h.append('<div class="fig">%s</div>' % plan_svg(d))
    h.append('<div class="legend"><span>■ 段（数字は地盤の標高）</span>'
             '<span style="color:var(--hei)">━ 築地塀</span>'
             '<span style="color:var(--nagaya)">━ 長屋塀</span>'
             '<span style="color:var(--take)">━ 竹垣</span>'
             '<span style="color:var(--ishi)">┄ 郭の土留め</span>'
             '<span style="color:var(--shu)">● 表門 ／ ○ 留め継ぎの隅 ／ ■ 隅櫓</span></div>')
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>其二　外周</h2>'
             '<span class="meta">天端は run ごとに一定。段は継ぎ目で落とす</span></div>')
    h.append(runs_table(d))
    h.append('<p class="cap"><b>地盤 top</b> はその run が面する郭の高さ、<b>天端 seat</b> は石垣の天端＝塀を据える高さ。'
             '犬走りは %.2fm。石垣は 壁高 = 4.0×s ／ 天端幅 = 1.4×s ／ 底厚 = 2.4×s。</p>'
             % d["const"]["inubashiri"])
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>其三　郭の土留め</h2></div>')
    h.append(walls_table(d))
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>其四　隅</h2>'
             '<span class="meta">折れ角は現地が決める。決め打ちしない</span></div>')
    h.append(corners_table(d))
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>其五　棟</h2>'
             '<span class="meta">外形＝身舎＋四方の入側一間</span></div>')
    h.append(munes_table(d))
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>其六　考証と決めごと</h2></div>')
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>改訂</h2>'
             '<span class="meta">経緯はここに書かず git で追う</span></div>')
    h.append(history())
    h.append("</div>")

    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>okabe_sashizu.json</code> ／ '
             '文章 <code>okabe_kosho.md</code>。Y は海抜 m（Unity の Y がそのまま標高）。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")
    open(OUT, "w", encoding="utf-8").write("\n".join(h))
    print("wrote %s (%.0f KB)" % (OUT, os.path.getsize(OUT) / 1024))
    print("  run: 検図 → ユーザーのレビュー → 実装 → 指図と実装を突き合わせる")


if __name__ == "__main__":
    main()
