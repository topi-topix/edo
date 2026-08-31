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
            print("報告・裁定要請の作法は **docs/session-board.md**(節目・ブロッカー・裁定要請だけ"
                  " post。自己検図・自己考証は**ユーザー入力なしに3巡まで**)。")
    # ⛔ 書き方の作法(規則16)。メッセージは揮発するので、起動のたびにここで通達する。
    #   2026-08-30 ユーザー指摘「どの質問や裁定にどう回答して良いか非常に困る」。
    print("⛔ **ユーザーへ書く前に `docs/reporting-protocol.md`(規則16・一件一葉)。**"
          " 冒頭1行で件数を宣言 → **【裁定】【質問】** → `---` → **【報告】【共有】**。"
          "**全項目に番号と題**(報告・共有にも。無題の段落を置かない)。選択肢は **A/B/C**。"
          "裁定は一通に最大3件・各件6点セット(どこ/背景2文/選択肢/推奨/影響/裁定図)。"
          "⛔ 地の文の末尾に問いを埋めない。⭐ 狙いは「1=A、2=B」「報告3だけ違う」で返せる形。")

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
