#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart — 窓を開いた時に、掲示板の齢(古び14日・時効30日)を黙って検める。**何も刷らない。**

【なぜ刷らないか】2026-10-10 施主指示(EDO-0580)「挨拶は要らない。再開もこちらから番号を指定して
指示する。文脈は掲示板に書いてある」。挨拶は窓が指示を読む前に出るので、どの邸の仕事かを知らないまま
全邸の関門の赤・他の窓の claim の一覧・規則の文を全窓に刷っていた(4〜5千字)。受け取った窓は
範囲外の赤に手を出せず(規則16)、Unity と他の窓のファイルは門番が止め、文脈の天井も門番が止める。
刷っていた物の行き先:
  ・その邸の関門の赤(検図・完成条件・算出物・結線)… `edo_session.py start <邸>`(`_gates`)
  ・全邸の関門の赤と設定の破れ(道具改め)… `edo_session.py start infra`
  ・worktree の CLAUDE.md の食い違い … worktree へ回す `start`(`_claude_md_drift`)
  ・掲示板のその邸の件 … `start`(`_board_open`・2026-09-21 裁定 EDO-0297 の「自邸全件」)

【残すもの】齢の処理(2026-09-21 施主裁定 EDO-0297=A)だけ。決まった時刻に回す担い手が他に無いので、
窓を開くたびに回す(約 1 秒・出力は捨てる)。
"""
import json, os, subprocess, sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _main_root(start):
    """worktree から起動されても、常に main の(最新の)Tools/Session/ を使う(EDO-0076)。"""
    try:
        r = subprocess.run(["git", "-C", start, "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True, timeout=5)
        d = r.stdout.strip()
        if d:
            return os.path.dirname(d)
    except Exception:
        pass
    return start


try:
    ev = json.load(sys.stdin)
except Exception:
    ev = {}
bcli = os.path.join(_main_root(ROOT), "Tools", "Session", "edo_board.py")
if os.path.exists(bcli):
    env = dict(os.environ)
    env["EDO_SESSION_ID"] = (ev.get("session_id") or "unknown")[:12]
    try:
        subprocess.run([sys.executable, bcli, "age", "--apply", "--quiet"],
                       capture_output=True, text=True, env=env, timeout=20)
    except Exception:
        pass
