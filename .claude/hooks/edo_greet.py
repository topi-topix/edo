#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart — このセッションが始まった時点で、他のセッションが何を押さえているかを出す。
stdout がそのままコンテキストに入る。"""
import json, os, subprocess, sys
ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _main_root(start):
    """worktree から起動されても、常に main の(最新の)Tools/Session/ を使う。
    edo_guard.py と同じ根拠(EDO-0076)— sparse worktree の Tools/ は
    sashizu/<邸> ブランチへ main をマージするまで古いまま。"""
    try:
        r = subprocess.run(["git", "-C", start, "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True, timeout=5)
        d = r.stdout.strip()
        if d:
            return os.path.dirname(d)
    except Exception:
        pass
    return start


MAIN_ROOT = _main_root(ROOT)
CLI = os.path.join(MAIN_ROOT, "Tools", "Session", "edo_session.py")
try:
    ev = json.load(sys.stdin)
except Exception:
    ev = {}
if os.path.exists(CLI):
    env = dict(os.environ)
    env["EDO_SESSION_ID"] = (ev.get("session_id") or "unknown")[:12]
    env["CLAUDE_PROJECT_DIR"] = ROOT
    r = subprocess.run([sys.executable, CLI, "status"], capture_output=True, text=True, env=env)
    out = r.stdout.strip()
    if out and "生きている claim は無し" not in out:
        print("⚠ このリポジトリでは**他の Claude Code セッションが同時に動いている**。"
              "他人が押さえているファイルと Unity には触らないこと。\n" + out)
        # ⛔ Unity の握りっぱなし(2026-08-30 ユーザー指摘)。心拍では終了を判定できないので、
        #   起動のたびに「終わったら返す」を通達する。
        if "unity" in out:
            print("⛔ **Unity 作業が終わったら即 "
                  "`python3 Tools/Session/edo_session.py release --resources unity`。**"
                  " 心拍は別作業でも更新されるので、放っておくと他邸が永久に触れない。"
                  " 使いたいのに埋まっていたら `edo_session.py wait --resources unity` で"
                  "**待ち行列に並ぶ**(空けば先頭に15分の予約が出る)。"
                  "⛔ **返した側は次の人へ SendMessage で連絡する義務がある。**")
        print("作業を始めるには **`python3 Tools/Session/edo_session.py start <屋敷>`**。"
              "指図だけなら worktree を探して(無ければ作って)そこへ回す。"
              "Unity を使うなら `start <屋敷> --unity` でメインに留まり Unity を確保する。")
    # 文脈計(計画 E-2): このセッションの文脈を 1 行。300K を超えたら /compact(docs/fushin-bugyo.md)。
    tp = ev.get("transcript_path") or ""
    tr = os.path.join(MAIN_ROOT, "Tools", "Session", "token_report.py")
    if tp and os.path.exists(tp) and os.path.exists(tr):
        t = subprocess.run([sys.executable, tr, "--self"], capture_output=True, text=True,
                           env=dict(env, EDO_TRANSCRIPT=tp))
        if t.stdout.strip():
            print("文脈計: %s(天井 300K。超えたら手仕舞いして /compact — 門番が段ごとに一度止める)" % t.stdout.strip())
    # 掲示板の digest(裁定待ち・ブロッカー・open)。CLI は**メインの checkout の物**を使う
    # (worktree のブランチには main を取り込むまで無いことがある)
    bcli = os.path.join(MAIN_ROOT, "Tools", "Session", "edo_board.py")
    if os.path.exists(bcli):
        b = subprocess.run([sys.executable, bcli, "digest"], capture_output=True, text=True, env=env)
        if b.stdout.strip():
            print(b.stdout.strip())
            print("起票の作法は docs/session-board.md(節目・ブロッカー・裁定要請だけ post。自己検図は3巡まで)。")
        # 普請場の一枚(2026-09-19 施主裁定A) — ⛔ **焼いた ≠ 施主に届いた。**
        #   9/2 に焼いた一枚が 17 日そのままで、施主が掲示板を見失った。掲示板が動いたのに
        #   公開の判が古ければ 1 行だけ鳴らす(揃っていれば無言)。
        try:
            import glob as _glob
            bd = os.path.join(MAIN_ROOT, ".git", "edo-board")
            if not os.path.isdir(bd):
                bd = None
            if bd:
                items = _glob.glob(os.path.join(bd, "EDO-*.json"))
                newest = max((os.path.getmtime(f) for f in items), default=0)
                pub = os.path.join(bd, "_pm", "published.json")
                at = json.load(open(pub, encoding="utf-8")).get("at", 0) if os.path.exists(pub) else 0
                days = (newest - at) / 86400.0
                if items and days > 3:
                    how = ("**まだ一度も公開していない**" if not at
                           else "**%.0f 日ぶん古い**" % days)
                    print("⛔ 普請場の一枚が %s(掲示板は動いたのに公開していない)。"
                          "`python3 Tools/Session/build_board_html.py` で焼き直し、Artifact を"
                          "更新したら `--published <URL>` で判を押す。"
                          "⛔ 焼いただけでは施主に届かない。" % how)
        except Exception:
            pass
        # 日誌(2026-09-19) — 夜の自動タスクが起票した「日誌(<日付>)」の task が未処置なら 1 行。0 なら無言。
        #   digest の 15 行予算の外。処置は /nikki(docs/teire.md「日誌」)。
        try:
            j = subprocess.run([sys.executable, bcli, "list", "--estate", "infra", "--type", "task", "--json"],
                               capture_output=True, text=True, env=env, timeout=8)
            items = json.loads(j.stdout or "[]")
            n = sum(1 for i in items if str(i.get("title", "")).startswith("日誌(")
                    and i.get("status") in ("open", "awaiting-user", "in-progress"))
            if n:
                print("日誌: 未処置が %d 日ぶん — 朝の普請奉行は `/nikki` で処置する(docs/teire.md「日誌」)。" % n)
        except Exception:
            pass
    # 検図関門 — この指図を誰が検めたか。⛔ 2026-09-01、松江松平の庭が**庭方に一度も
    #   検められないまま実装され**、ユーザーに差し戻された。ルーティング表に庭方は載って
    #   いたのに、通さなくても何も起きなかった。散文の規則は破れるので機械で見張る。
    rcli = os.path.join(MAIN_ROOT, "Tools", "Sashizu", "review_gate.py")
    if os.path.exists(rcli):
        r = subprocess.run([sys.executable, rcli, "--quiet"], capture_output=True, text=True, env=env)
        if r.stdout.strip():
            print(r.stdout.strip())
            print("  ⚠ 移行期間(2026-09-01 裁定B): 検分を通すまで作業は続けてよいが、"
                  "**ユーザーへ見せる前には必ず通す**。遡って pass を書かない。"
                  "結果は呼んだ側が `review_gate.py --record <屋敷> <役> <pass|fail>`(CLAUDE.md 規則18)")
    # 完成条件の表(2026-09-19 施主裁定3=A) — 実装の車線にいる敷地の 5 項目の残。
    #   検図関門は実装前まで、実装後はこの表が関門(CLAUDE.md 規則18)。
    kcli = os.path.join(MAIN_ROOT, "Tools", "Sashizu", "kansei_gate.py")
    if os.path.exists(kcli):
        k = subprocess.run([sys.executable, kcli, "--quiet"], capture_output=True, text=True, env=env)
        if k.stdout.strip():
            print(k.stdout.strip())
    # 類型表の関門(2026-09-19) — 類型の区画には指図も検分の輪も無い(docs/typology-builder.md §2)ので、
    #   「区画が増えたのに表に載っていない」「欄が抜けた」を捕まえる目がここにしか無い。
    tcli = os.path.join(MAIN_ROOT, "Tools", "Sashizu", "typology_check.py")
    if os.path.exists(tcli):
        t = subprocess.run([sys.executable, tcli, "--quiet"], capture_output=True, text=True, env=env)
        if t.stdout.strip():
            print(t.stdout.strip())
    # 結線関門(絶対規則19) — **書いたのに誰の目にも入らない産物**を鳴らす。
    #   ⛔ 規則19 は CLAUDE.md に入ったが、**機構としては誰にも鳴っていなかった**。
    #   これは規則18(検図関門)を作った動機そのもの ——「ルーティング表に載っていたが
    #   通さなくても何も起きなかった」—— の再来で、2026-09-02 にここへ結線した(EDO-0113)。
    #   ⚠ **`--quiet` は使わない。** 結線関門は 0 件でも全生成器を1行ずつ刷る作りで、
    #   そのまま入れると挨拶が7行増える。作り手のセッションが claim 中で本体に
    #   `--quiet` を足せないため、**exit コードで黙らせ、⛔ の行だけを拾う**
    #   (不備が無ければ exit 0 で、ここは一言も出さない)。
    wcli = os.path.join(MAIN_ROOT, "Tools", "Sashizu", "wiring_gate.py")
    if os.path.exists(wcli):
        w = subprocess.run([sys.executable, wcli], capture_output=True, text=True, env=env)
        if w.returncode:
            # 生成器の行と個々の不備(孤立/黙り)だけ拾う。道具の末尾の注意書き
            # (「0件は合格ではない」ほか)は下で一言にまとめるので落とす。
            bad = [ln for ln in w.stdout.split("\n")
                   if "⛔" in ln and ("build_" in ln or "孤立" in ln or "黙り" in ln)]
            if bad:
                print("結線関門 — **書いたのに誰の目にも入らない産物がある**"
                      "(`python3 Tools/Sashizu/wiring_gate.py <邸名>`)")
                for ln in bad[:8]:
                    print("  " + ln.strip())
                print("  ⛔ 輪に入っていない値は「未検査」であって「合格」ではない(規則19)。"
                      "孤立=一度も走らない / 黙り=件数が要約に届かない。正典: `docs/verification-loops.md`")
    # 道具改め(2026-09-13) — 設定そのもの(役→スキル・CLAUDE.md の表・フック・索引・義務の正典)の破れ。
    #   ⛔ だけを最大 6 行(無傷なら無言)+「前回の手入れから N 日」の 1 行。0.4 秒・transcript も git も読まない。
    #   正典: docs/teire.md。週次の表は /teire。
    dcli = os.path.join(MAIN_ROOT, "Tools", "Session", "config_doctor.py")
    if os.path.exists(dcli):
        try:
            d = subprocess.run([sys.executable, dcli, "--quick"], capture_output=True, text=True, env=env, timeout=8)
            if d.stdout.strip():
                print(d.stdout.strip())
        except Exception:
            pass
# ⛔ worktree の CLAUDE.md は main へマージするまで古いまま(EDO-0077)。
#   このセッションが読んでいる不変則が最新かどうかを、起動時に一度だけ確かめる。
if os.path.abspath(ROOT) != os.path.abspath(MAIN_ROOT):
    a = os.path.join(ROOT, "CLAUDE.md")
    b = os.path.join(MAIN_ROOT, "CLAUDE.md")
    try:
        if os.path.exists(a) and os.path.exists(b) and open(a, encoding="utf-8").read() != \
                open(b, encoding="utf-8").read():
            print("⚠ **この worktree の CLAUDE.md は main と食い違っている。**"
                  "sparse worktree は sashizu/<邸> ブランチへ main を取り込むまで更新されない"
                  "(2026-08-31、外堀セッションが基準年次の記述違いで実際に踏んだ)。"
                  "不変則(基準年次・絶対規則の番号など)を当てにする前に "
                  "`diff %s %s` で差分を確認すること。"
                  " Tools/Session/ のコマンドはフックが自動で main の最新版を使うのでこの限りではない。"
                  % (a, b))
    except Exception:
        pass
