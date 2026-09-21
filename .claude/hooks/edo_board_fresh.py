#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop フック — 手仕舞いのときに普請場の一枚を焼き直し、公開していなければ一度だけ止める。

【なぜ要るか】2026-09-21 施主指摘「掲示板が更新されても、アーティファクト自体は1日1回しか
更新されないので、私自身が確認できるのもかなり時間が遅れる」。それまで焼く担い手は毎朝の日誌だけで、
板が動いてから施主の目に入るまで**最大 24 時間**空いていた。裁定 EDO-0298=A+B:
  A(この フック) 板が動いた日は、**手を止めるセッションが**焼いて同じ URL へ上書きする → 遅れは数分〜1時間
  B(常時の窓)    机の前では `Tools/Session/board_window.py` が 5 分以内に焼き直す(launchd)

【止める条件】(`stop_hook_active` が立っていれば通す = 一度だけ)
  ・掲示板の件が公開の判より新しい … 焼くのはこのフックがやる。**公開だけは手が要る**(Artifact は人の道具)
  ・このセッションが立てた裁定要請が awaiting-user のまま、最後の一通に【裁定】の見出しが無い
    … 「裁定と詰まりの二種は即時で施主に出す」(EDO-0298 の裁定文)を機械で守る

⛔ 焼いた ≠ 届いた。判は `build_board_html.py --published <URL>` で押す。
正典: docs/session-board.md「普請場の一枚」
"""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # .claude/
ROOT = os.path.dirname(ROOT)                       # リポジトリ(worktree のこともある)
DEFAULT_URL = "https://claude.ai/artifact/3wTRqrXgJBp8LJUwWFZ4KY"


def main_root():
    """worktree から呼ばれても、板と道具はメインの checkout の物を見る。"""
    try:
        out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             cwd=ROOT, capture_output=True, text=True, timeout=5).stdout.strip()
        if out.endswith(".git"):
            return os.path.dirname(out)
    except Exception:
        pass
    return ROOT


def stage_for_artifact(board, cwd):
    """Artifact へ渡せる **写す先と絶対パス** (写す先, index.html, dashboard.html) を返す。
    写すのは `build_board_html.py --stage <写す先>`(焼いた直後に一手で写る)。

    ⚠ 相対の `.git/edo-board/_pm/...` を渡してはいけない。**worktree では `.git` が
    ディレクトリでなくファイル**なので `ENOTDIR` で開けない(2026-09-22 実測)。実体は
    `git rev-parse --git-common-dir` の先=メインの checkout に在り、そこは worktree の
    作業ディレクトリの**外**なので、絶対パスに直しても Artifact は受け取らない。

    そこで**どの根から呼ばれても同じ**に、作業ツリーの `Temp/edo-board/` へ写してその絶対パスを渡す
    (`.gitignore` の `[Tt]emp/` で無視される・`git status` は汚れない)。⛔ メインの checkout だけ
    実体をそのまま渡す枝を作らない — `.git/` 配下を渡す形は Artifact で通した実績が無く、
    普段は worktree から呼ばれるので**壊れても誰も踏まずに残る**。
    """
    dst = os.path.join(os.path.realpath(cwd), "Temp", "edo-board")
    return dst, os.path.join(dst, "index.html"), os.path.join(dst, "dashboard.html")


def board_version(root):
    """今の掲示板の版。正典は `build_board_html.board_version` — ここでは計算しない
    (同じ式を二つ持つと、片方を直したときに静かに食い違う)。呼べなければ None。"""
    gen = os.path.join(root, "Tools", "Session", "build_board_html.py")
    if not os.path.exists(gen):
        return None
    try:
        r = subprocess.run([sys.executable, gen, "--version"], cwd=root,
                           capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    v = (r.stdout or "").strip().splitlines()[-1:] or [""]
    return v[0] if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{16}", v[0]) else None


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if ev.get("stop_hook_active"):
        sys.exit(0)
    root = main_root()
    board = os.path.join(root, ".git", "edo-board")
    if not os.path.isdir(board):
        sys.exit(0)
    items = [os.path.join(board, f) for f in os.listdir(board) if re.match(r"EDO-\d+\.json$", f)]
    if not items:
        sys.exit(0)
    newest = max(os.path.getmtime(f) for f in items)
    pub = os.path.join(board, "_pm", "published.json")
    stamp = {}
    if os.path.exists(pub):
        try:
            stamp = json.load(open(pub, encoding="utf-8"))
        except Exception:
            stamp = {}
    at = stamp.get("at", 0)
    url = stamp.get("url") or DEFAULT_URL
    ver, pub_ver = board_version(root), stamp.get("version")
    reasons = []

    # ── ① 板が公開より新しい → 焼いてから、公開を頼む
    # ⭐ **版で測る(2026-09-22 施主指示)。**版が同じなら、誰が上げた一枚でも今の板を写している。
    #   ⛔ 壁時計の `at` で測らない — 先に焼いて後から上げた相手の判は、時刻だけ新しくて中身が古い。
    #   版を採れない/判が版を持たないときだけ、旧来の時刻の比べ方へ後退する。
    if (ver != pub_ver) if (ver and pub_ver) else (newest - at > 60):
        gen = os.path.join(root, "Tools", "Session", "build_board_html.py")
        stage_dir_idx = stage_for_artifact(board, ev.get("cwd") or ROOT)
        stage_dir = stage_dir_idx[0]
        baked = os.path.join(board, "_pm", "dashboard.html")
        ok = False
        if os.path.exists(gen):
            try:
                r = subprocess.run([sys.executable, gen, "--stage", stage_dir], cwd=root,
                                   capture_output=True, text=True, timeout=120)
                ok = r.returncode == 0
            except Exception:
                ok = False
        late = (newest - at) / 3600.0
        idx_p, dash_p = stage_dir_idx[1], stage_dir_idx[2]
        how = ('Artifact(file_path="%s", url="%s", '
               'files={"board.html": "%s"}, '
               'overwrite_unread=["board.html"])' % (idx_p, url, dash_p))
        reasons.append(
            "掲示板が %s動いたのに、施主が見る一枚は古いまま。%s"
            "**中身だけ**を差し替えて上げ("
            "⛔ 板の本体 board.html を読み込まないこと — 大きくて文脈が飛ぶ・"
            "⛔ url を渡さないと別の図が生える):\n    %s\n  "
            "⚠ **上げる直前に `python3 Tools/Session/build_board_html.py --check-fresh`。**"
            "「掲示板が動いた」と出たら、焼いた一枚は古い — 下の焼き直しをしてから上げること。\n  "
            "上げるのを断られたら(枠の頁を見ていない/別のセッションが先に上げた):\n"
            "    ① `Artifact(action=\"read\", url=\"%s\")` を1回"
            "(読まれるのは板を表示する枠の頁だけで、板の本体は読まれない)\n"
            "    ② `python3 Tools/Session/build_board_html.py --stage %s` で**焼き直して写す**\n"
            "    ③ もう一度上げる\n  "
            "⛔ **上げずに終えない。**焼き直した一枚には自分の分も相手の分も入る"
            "(板は件の json から毎回作り直すので、取り合いにならない)。\n  "
            "上げられたら `python3 Tools/Session/build_board_html.py --published %s` で判を押してから終えること。"
            % (("%.0f 時間ぶん" % late) if at else "",
               "**焼き直しは済ませた**ので、" if ok
               else "⛔ 焼き直しに失敗したので `python3 Tools/Session/build_board_html.py` を手で回してから、",
               how, url, stage_dir, url))

    # ── ② 自分が立てた裁定要請を、施主へ出さずに手を止めようとしている
    me = (ev.get("session_id") or "")[:12]
    if me:
        msg = ev.get("last_assistant_message") or ""
        if not re.search(r"【裁定", msg):
            for f in items:
                try:
                    c = json.load(open(f, encoding="utf-8"))
                except Exception:
                    continue
                if c.get("type") != "decision" or c.get("status") != "awaiting-user":
                    continue
                if time.time() - (c.get("created") or 0) > 12 * 3600:
                    continue
                if any((e.get("by") or "")[:12] == me for e in c.get("log", [])):
                    reasons.append(
                        "この巡で裁定要請を立てたのに、最後の一通に【裁定】の見出しが無い。"
                        "裁定と詰まりは板に置くだけでは届かない — 6 点セット(どこ・現況・A/B/C・数値の差・推奨・影響)で"
                        "施主へ出してから終えること: 「%s」" % c.get("title", "")[:60])
                    break

    if not reasons:
        sys.exit(0)
    print(json.dumps({"decision": "block",
                      "reason": "⛔ 手仕舞いの前に片付けること(掲示板の作法・docs/session-board.md):\n- "
                                + "\n- ".join(reasons)}))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
