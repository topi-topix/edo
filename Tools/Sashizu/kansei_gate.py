#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完成条件の表 — 敷地が「完成した」と言える条件を機械で見張る(2026-09-19 施主裁定 3件=A)。

【なぜ要るか】7 週間で完成 0/88。松江松平は建ってから 10 日、直しているのは細部で、指図は凍結後も
第32→54次まで上がり続けた。**完成の定義が無い**ので三役の残が尽きず、普請検査の指摘が指図へ戻って
版が上がり、版が上がると検分が再実行される — 輪が閉じない。
⭕ 完成は**合否つきの項目表**で定める。全部 pass で完成。以後の指摘は掲示板へ積み、指図は開かない。

【仕組み】`docs/Sashizu/<敷地>_kansei.json` に 5 項目を持つ:

    隙 0 ／ 境界侵犯 0 ／ 埋没・浮き 0 ／ 突き合わせ 0 ／ レンダの施主承認

・表が在る = その敷地は**建った**(`phase: built`)。以後 `review_gate.py`(検図関門)は効かず、この表が関門になる。
  ⛔ **建った敷地の直しは欄の上書き**(2026-09-19 施主指示) — 屋根の型・門の型・棟の増減も json の値を直して
  建て直すだけで、図(html)の組み直しも検分も回さない。`--reopen` は施主が「図から起こし直せ」と言ったときだけ
・値を埋めるのは普請検査(edo-fushin-qa)の実測。⛔ 施主承認(render)だけは役が書けない —
  **施主の発話の引用**が要る(`--quote`)。呼んだ側(普請奉行)が書き戻す
・実装の車線は**同時に一敷地**。表が全部 pass になるまで次の敷地を実装の車線に入れない

【使い方】
    python3 Tools/Sashizu/kansei_gate.py                          # 全敷地の表を見る
    python3 Tools/Sashizu/kansei_gate.py --init matsudaira_dewa   # 実装の車線へ入れる(表を起こす)
      ⛔ **図の機械検査(C01〜C23)が赤なら入れない**(2026-09-21・EDO-0291・規則3)。記録は生成器が
         書く(`build_sashizu.py <邸>` → `<邸>_checks.json`)。記録が無い・古い指図の物でも止まる。
         施主が承知なら `--init <邸> --quote "<施主の発話>"`(表の history に引用が残る)
    python3 Tools/Sashizu/kansei_gate.py --record matsudaira_dewa gap pass --value "隙 0 / めり込み 0 (JointQA 214 組)"
    python3 Tools/Sashizu/kansei_gate.py --record matsudaira_dewa render pass --quote "この見た目でよい(2026-09-20)"
    python3 Tools/Sashizu/kansei_gate.py --reopen matsudaira_dewa "図から起こし直す" --quote "<施主の発話>"   # ⛔ 施主の発話が要る
    python3 Tools/Sashizu/kansei_gate.py --quiet                  # 挨拶用(実装の車線にいる敷地だけ 1 行)
    python3 Tools/Sashizu/kansei_gate.py --selftest

【終了コード】0 = 実装の車線に敷地が無い、または全部 pass ／ 1 = 未 pass の項目が残る敷地がある。
"""
import collections
import datetime
import hashlib
import json
import os
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(REPO, "docs", "Sashizu")

# 項目は施主裁定 3(2026-09-19)の 5 つ。⛔ 増やさない — 増やすと「残が尽きない」に戻る。
ITEMS = collections.OrderedDict([
    ("gap", {"label": "隙 0",
             "what": "塀と塀・門と塀・長屋 run の駒どうしの隙・めり込み・裏表(許容 0)",
             "how": "edo-fushin-qa 項目 6(run の格子)・7(裏表)・8(門の取り合い)、JointQA / GateQA"}),
    ("boundary", {"label": "境界侵犯 0",
                  "what": "棟・塀・木・石が区画 / 庭の区域 / 建物 / 水面 / 道へ入らない",
                  "how": "edo-fushin-qa 項目 1(境界)と区域の点検(EdoGeom.PIP)"}),
    ("ground", {"label": "埋没・浮き 0",
                "what": "埋 ≤1.0 / 浮 ≤0.7 を超える駒が 0",
                "how": "edo-fushin-qa 項目 2(接地)と GroundQA"}),
    ("match", {"label": "突き合わせ 0",
               "what": "指図(意図)と実装の食い違いが 0 件",
               "how": "Unity メニュー Edo/<敷地>/指図と実装を突き合わせる"}),
    ("render", {"label": "レンダの施主承認",
                "what": "検証レンダ(真上・門の外・庭の目線)を施主が見て承認",
                "how": "施主の発話。⛔ 役は書けない — --quote に引用を入れる"}),
])
VERDICTS = ("pass", "fail")


def _path(name, base=None):
    return os.path.join(base or DOCS, "%s_kansei.json" % name)


def phase(name, base=None):
    """review_gate.py が呼ぶ。表が無ければ 'design'、在れば表の phase('built' / 'done')。"""
    p = _path(name, base)
    if not os.path.exists(p):
        return "design"
    try:
        with open(p) as fp:
            return json.load(fp).get("phase") or "built"
    except Exception:
        return "design"


def _load(name, base=None):
    p = _path(name, base)
    if not os.path.exists(p):
        sys.exit("⛔ %s に完成条件の表が無い。実装の車線へ入れるなら `--init %s`。" % (name, name))
    with open(p) as fp:
        return json.load(fp, object_pairs_hook=collections.OrderedDict), p


def _save(doc, p):
    with open(p, "w") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


def _blank_items():
    items = collections.OrderedDict()
    for k, spec in ITEMS.items():
        items[k] = collections.OrderedDict([
            ("label", spec["label"]), ("what", spec["what"]), ("how", spec["how"]),
            ("value", None), ("verdict", None), ("at", None), ("note", "")])
        if k == "render":
            items[k]["quote"] = None
    return items


def names(base=None):
    d = base or DOCS
    if not os.path.isdir(d):
        return []
    return sorted(f[:-len("_kansei.json")] for f in os.listdir(d) if f.endswith("_kansei.json"))


def zu_checks(name, base=None):
    """図の機械検査(C01〜C23)の記録を読む。返すのは (印, 一行, 赤の列)。

    ⛔ **これが無かったのが規則3 が効かなかった理由**(掲示板 EDO-0291)。2026-09-01、
    松江松平の図の検査は棟別 38.4% の赤を出していたのに、実装の車線へ入る所は**検分の記録**しか
    見ていなかった。紙の上で分かっていたのに誰も止まらず、建てて普請検査で出た。
    ⇒ 刷るだけでは関門にならない。⭕ 入口で読んで止める(規則19)。

    記録は生成器が毎回書く(`build_sashizu.py <邸>` → `<邸>_checks.json`)。
    ⚠ 指図の指紋を照らして、**いまの指図を見た記録か**まで見る — 古い緑で通さない。
    """
    d = base or DOCS
    p = os.path.join(d, "%s_checks.json" % name)
    if not os.path.exists(p):
        return "⛔", "図の機械検査の記録が無い — `python3 Tools/Sashizu/build_sashizu.py %s` で焼き直す" % name, []
    try:
        with open(p, encoding="utf-8") as fp:
            rec = json.load(fp)
    except Exception:
        return "⛔", "図の機械検査の記録が読めない(%s)" % os.path.relpath(p, REPO), []
    try:
        sha = hashlib.sha256(open(os.path.join(d, "%s_sashizu.json" % name), "rb").read()).hexdigest()[:16]
    except Exception:
        sha = ""
    if rec.get("sashizu_sha") and sha and rec["sashizu_sha"] != sha:
        return "⛔", ("図の機械検査の記録が**いまの指図の物ではない**(記録 %s / いま %s)— 焼き直す"
                      % (rec["sashizu_sha"], sha)), []
    red = [r for r in (rec.get("rows") or []) if r.get("status") == "ng"]
    na = [r for r in (rec.get("rows") or []) if r.get("status") == "na"]
    if red:
        return "⛔", "図の機械検査が赤 %d 件(未検査 %d 件)" % (len(red), len(na)), red
    return "⭕", "図の機械検査 赤 0 件(未検査 %d 件)" % len(na), []


def cmd_init(name, base=None, force=False, quote=None):
    p = _path(name, base)
    if os.path.exists(p) and not force:
        sys.exit("⛔ %s の表は既に在る(%s)。白紙に戻すのは --reopen。" % (name, os.path.relpath(p, REPO)))
    sashizu = os.path.join(base or DOCS, "%s_sashizu.json" % name)
    if not os.path.exists(sashizu):
        sys.exit("⛔ %s は指図(%s)が無い — 類型の区画なら表は要らない(docs/typology-builder.md)。" % (name, os.path.relpath(sashizu, REPO)))
    # 検図関門は「実装前に 1 巡」。赤のまま入れるのは移行期間の邸(既に建っている)だけなので、止めずに刷る。
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import review_gate  # noqa
        red, _rows = review_gate.gate(name)
        if red:
            print("⚠ 検図関門が赤 %d 件のまま実装の車線へ入れる(移行期間の邸だけ許される。CLAUDE.md 規則18)。" % red)
    except SystemExit:
        pass
    except Exception:
        pass
    # ⛔ **図の機械検査の赤は止める**(EDO-0291・規則3)。検分の記録の赤とは扱いが違う —
    #   あちらは移行期間の断りがあるが、こちらは「紙の上で既に分かっている欠陥」。
    #   ⭕ 抜けられるのは施主の発話の引用がある時だけ(完成条件の render と同じ作法)。
    mark, line, red = zu_checks(name, base)
    if mark == "⛔":
        print("⛔ %s — %s" % (name, line))
        for r in red[:8]:
            print("     %s %s: %s" % (r.get("id"), r.get("what"), str(r.get("res"))[:80]))
        if len(red) > 8:
            print("     … ほか %d 件" % (len(red) - 8))
        if not quote:
            sys.exit("⛔ 実装の車線へ入れない。直してから焼き直すか、施主が承知なら `--quote \"<施主の発話>\"`。"
                     "\n   ⚠ 直すのは棟でも土でもなく**面の引き方**のことが多い(規則3・スキル §B-1 の 2 へ戻る)。")
        print("⚠ 施主の発話の引用があるので、赤のまま実装の車線へ入れる: 「%s」" % quote[:120])
    else:
        print("⭕ %s — %s" % (name, line))
    doc = collections.OrderedDict([
        ("_", "完成条件の表(2026-09-19 施主裁定3=A)。全部 pass で完成。以後の指摘は掲示板へ積み、指図は開かない。"
              "値は普請検査の実測、render だけは施主の発話の引用。見張りは python3 Tools/Sashizu/kansei_gate.py"),
        ("estate", name),
        ("phase", "built"),
        ("since", datetime.date.today().isoformat()),
        ("items", _blank_items()),
        ("completed", None),
        ("history", [collections.OrderedDict(
            [("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
             ("event", "init")]
            + ([("zu_red", len(red)), ("quote", quote[:600])] if red and quote else []))]),
    ])
    _save(doc, p)
    print("起票: %s → %s(phase=built。以後 review_gate は効かず、この表が関門)" % (name, os.path.relpath(p, REPO)))
    return 0


def cmd_record(name, key, verdict, value=None, note=None, quote=None, base=None):
    if key not in ITEMS:
        sys.exit("項目が違う。使えるのは: " + " / ".join(ITEMS))
    if verdict not in VERDICTS:
        sys.exit("verdict は " + " / ".join(VERDICTS))
    doc, p = _load(name, base)
    if doc.get("phase") == "design":
        sys.exit("⛔ %s は指図を開いている(phase=design)。建て直してから `--built %s`。" % (name, name))
    if key == "render":
        if verdict == "pass" and not (quote or "").strip():
            sys.exit("⛔ 施主承認は役が書けない。`--quote \"<施主の発話の引用>\"` が要る。")
    elif not (value or "").strip():
        sys.exit("⛔ 実測値が無い(`--value \"<件数・最大値・対象数>\"`)。数値を出さずに合格と言わない。")
    it = doc["items"][key]
    it["value"] = value
    it["verdict"] = verdict
    it["at"] = datetime.date.today().isoformat()
    it["note"] = (note or "")[:600]
    if key == "render":
        it["quote"] = (quote or "")[:600] or None
    doc["history"].append(collections.OrderedDict([
        ("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
        ("event", "record"), ("item", key), ("verdict", verdict)]))
    done = all(v.get("verdict") == "pass" for v in doc["items"].values())
    if done and doc.get("phase") != "done":
        doc["phase"] = "done"
        doc["completed"] = datetime.date.today().isoformat()
    elif not done and doc.get("phase") == "done":
        doc["phase"] = "built"
        doc["completed"] = None
    _save(doc, p)
    print("記録: %s / %s = %s  → %s" % (name, ITEMS[key]["label"], verdict, os.path.relpath(p, REPO)))
    if done:
        print("⭕ **完成** — 5 項目すべて pass。以後の指摘は欄の上書きで直す。指図は開かない。" % ())
        # 2026-09-19 施主指示: 完成時に**一度だけ**図(html)を最終形へ刷り直す。値は json が常に正で、
        #   突き合わせ 0 が完成条件に入っているので「図と違う物が建つ」は完成にならない。刷り直しは記録の為。
        print("   → 最後に一度だけ図を刷り直す: `python3 Tools/Sashizu/build_sashizu.py %s`(検分は付けない・記録の為)" % name)
    return 0


def cmd_reopen(name, reason, base=None, quote=None):
    """⛔ 2026-09-19 施主指示: 建った敷地の直しは**欄の上書き**(json の値を直して建て直す)で、図は開かない。
    開けるのは施主が「図から起こし直せ」と言ったときだけ — その発話の引用が要る。表は白紙へ戻る。"""
    if not (reason or "").strip():
        sys.exit("⛔ 理由が要る — 何を起こし直すのか。")
    if not (quote or "").strip():
        sys.exit("⛔ 建った敷地の図は役の判断で開けない(CLAUDE.md 規則4)。屋根の型・棟の増減も**欄の上書き**で直す。\n"
                 "   施主が「図から起こし直せ」と言ったときだけ `--quote \"<施主の発話>\"` を添えて開く。")
    doc, p = _load(name, base)
    doc["phase"] = "design"
    doc["completed"] = None
    doc["items"] = _blank_items()
    doc["history"].append(collections.OrderedDict([
        ("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
        ("event", "reopen"), ("reason", reason[:600]), ("quote", quote[:600])]))
    _save(doc, p)
    print("指図を開いた: %s(phase=design)。変わった章だけ検分 1 巡 → 建て直し → `--built %s` で表を再開。" % (name, name))
    return 0


def cmd_built(name, base=None):
    doc, p = _load(name, base)
    doc["phase"] = "built"
    doc["history"].append(collections.OrderedDict([
        ("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
        ("event", "built")]))
    _save(doc, p)
    print("実装の車線へ戻した: %s(phase=built)。5 項目を測り直す。" % name)
    return 0


def rows(name, base=None):
    doc, _p = _load(name, base)
    out = []
    for k, it in doc["items"].items():
        v = it.get("verdict")
        mark = "⭕" if v == "pass" else ("⛔" if v == "fail" else "・")
        state = {"pass": "pass(%s)" % it.get("at"), "fail": "fail(%s)" % it.get("at")}.get(v, "未測")
        extra = it.get("quote") if k == "render" else it.get("value")
        out.append((mark, k, it["label"], state, extra or ""))
    return doc, out


def cmd_status(only=None, quiet=False, base=None):
    lst = [n for n in names(base) if not only or n in only]
    exit_code = 0
    lines = []
    for n in lst:
        doc, rr = rows(n, base)
        ph = doc.get("phase")
        npass = sum(1 for r in rr if r[0] == "⭕")
        nfail = sum(1 for r in rr if r[0] == "⛔")
        if ph == "design":
            lines.append("  ・ %-18s 指図を開いている(phase=design) — 検図関門が効く" % n)
            continue
        if ph == "done":
            lines.append("  ⭕ %-18s 完成(%s)" % (n, doc.get("completed")))
            continue
        exit_code = 1
        if quiet:
            lines.append("  ⛔ %-18s 完成条件 %d/5 pass(fail %d・未測 %d)" % (n, npass, nfail, 5 - npass - nfail))
            continue
        lines.append("⛔  %s  %d/5 pass" % (n, npass))
        for mark, _k, label, state, extra in rr:
            lines.append("    %s %-14s %s" % (mark, label, state))
            if extra:
                lines.append("        %s" % extra)
    if quiet and exit_code:
        lines.insert(0, "完成条件の表 — **実装の車線に未完成の敷地がある**(`python3 Tools/Sashizu/kansei_gate.py`)")
    if lines:
        print("\n".join(lines))
    elif not quiet:
        print("完成条件の表を持つ敷地は無い(実装の車線は空)。入れるなら `--init <敷地>`。")
    return exit_code


def selftest():
    """関門そのものの輪(docs/verification-loops.md)。壊したら鳴ることを確かめる。"""
    fails = []
    import contextlib, io as _io
    with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(_io.StringIO()):
        with open(os.path.join(td, "x_sashizu.json"), "w") as fp:
            fp.write("{}")

        def expect(cond, msg):
            if not cond:
                fails.append(msg)

        def zu(rows, sha=None):
            """図の機械検査の記録を仕込む。sha=None なら今の指図の指紋(= 新しい記録)。"""
            if sha is None:
                sha = hashlib.sha256(open(os.path.join(td, "x_sashizu.json"), "rb").read()).hexdigest()[:16]
            with open(os.path.join(td, "x_checks.json"), "w") as f2:
                json.dump({"estate": "x", "sashizu_sha": sha, "rows": rows}, f2)

        def blocked(**kw):
            """--init が止まるか。⛔ 止まらなければ規則3 の関門が死んでいる(EDO-0291)。"""
            try:
                cmd_init("x", base=td, force=True, **kw)
                return False
            except SystemExit:
                return True

        # ⛔ 図の機械検査の赤を読む関門(EDO-0291)— 紙で分かっている欠陥を実装へ通さない
        expect(blocked(), "図の検査の**記録が無い**のに実装の車線へ入れた")
        zu([{"id": "C04", "what": "面と地形", "res": "系統差 0.45m", "status": "ng"}])
        expect(blocked(), "図の検査が**赤**なのに実装の車線へ入れた")
        expect(not blocked(quote="Bで(施主 2026-09-20)"), "施主の引用があるのに通らない")
        zu([{"id": "C01", "what": "重なり", "res": "0 件", "status": "ok"}], sha="むかしの指図")
        expect(blocked(), "**古い指図を見た記録**で実装の車線へ入れた")
        zu([{"id": "C01", "what": "重なり", "res": "0 件", "status": "ok"}])
        cmd_init("x", base=td, force=True)
        expect(phase("x", td) == "built", "init 後の phase が built でない")
        expect(cmd_status(base=td) == 1, "未測が残るのに exit 0")
        try:
            cmd_record("x", "gap", "pass", base=td)
            expect(False, "実測値なしの pass を受けた")
        except SystemExit:
            pass
        try:
            cmd_record("x", "render", "pass", base=td)
            expect(False, "引用なしの施主承認を受けた")
        except SystemExit:
            pass
        for k in ("gap", "boundary", "ground", "match"):
            cmd_record("x", k, "pass", value="0 件", base=td)
        expect(phase("x", td) == "built", "render 未測なのに done になった")
        cmd_record("x", "render", "pass", quote="よい", base=td)
        expect(phase("x", td) == "done", "5 項目 pass で done にならない")
        expect(cmd_status(base=td) == 0, "完成しているのに exit 1")
        cmd_record("x", "gap", "fail", value="隙 0.4m ×3", base=td)
        expect(phase("x", td) == "built", "fail で done から built に戻らない")
        try:
            cmd_reopen("x", "門の型を変える", base=td)
            expect(False, "施主の引用なしの reopen を受けた")
        except SystemExit:
            pass
        cmd_reopen("x", "門の型を変える", base=td, quote="図から起こし直して")
        expect(phase("x", td) == "design", "reopen で design にならない")
        doc, _ = _load("x", td)
        expect(all(v["verdict"] is None for v in doc["items"].values()), "reopen で表が白紙に戻らない")
        try:
            cmd_record("x", "gap", "pass", value="0", base=td)
            expect(False, "design のまま記録を受けた")
        except SystemExit:
            pass
        cmd_built("x", base=td)
        expect(phase("x", td) == "built", "--built で built に戻らない")
        expect(phase("nothing", td) == "design", "表が無い敷地が design でない")
    if fails:
        print("⛔ kansei_gate selftest: %d 件\n  " % len(fails) + "\n  ".join(fails))
        return 1
    print("⭕ kansei_gate selftest: 全件通過")
    return 0


def _opt(argv, key):
    if key in argv:
        i = argv.index(key)
        if i + 1 < len(argv):
            v = argv[i + 1]
            del argv[i:i + 2]
            return v
    return None


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--selftest":
        return sys.exit(selftest())
    if argv and argv[0] == "--init":
        if len(argv) < 2:
            sys.exit("使い方: --init <敷地>")
        return sys.exit(cmd_init(argv[1], force="--force" in argv, quote=_opt(argv, "--quote")))
    if argv and argv[0] == "--record":
        value, note, quote = _opt(argv, "--value"), _opt(argv, "--note"), _opt(argv, "--quote")
        if len(argv) < 4:
            sys.exit("使い方: --record <敷地> <gap|boundary|ground|match|render> <pass|fail> [--value ..] [--note ..] [--quote ..]")
        return sys.exit(cmd_record(argv[1], argv[2], argv[3], value, note, quote))
    if argv and argv[0] == "--reopen":
        quote = _opt(argv, "--quote")
        if len(argv) < 3:
            sys.exit("使い方: --reopen <敷地> \"<何を起こし直すか>\" --quote \"<施主の発話>\"")
        return sys.exit(cmd_reopen(argv[1], " ".join(argv[2:]), quote=quote))
    if argv and argv[0] == "--built":
        if len(argv) < 2:
            sys.exit("使い方: --built <敷地>")
        return sys.exit(cmd_built(argv[1]))
    quiet = "--quiet" in argv
    only = [a for a in argv if not a.startswith("--")]
    sys.exit(cmd_status(only or None, quiet))


if __name__ == "__main__":
    main()
