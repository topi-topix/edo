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
    # 掲示板の digest(裁定待ち・ブロッカー・open)。CLI は**メインの checkout の物**を使う
    # (worktree のブランチには main を取り込むまで無いことがある)
    bcli = os.path.join(MAIN_ROOT, "Tools", "Session", "edo_board.py")
    if os.path.exists(bcli):
        b = subprocess.run([sys.executable, bcli, "digest"], capture_output=True, text=True, env=env)
        if b.stdout.strip():
            print(b.stdout.strip())
            print("起票の作法は docs/session-board.md(節目・ブロッカー・裁定要請だけ post。自己検図は3巡まで)。")
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
