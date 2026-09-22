#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""常時の窓 — 掲示板が動いたら普請場の一枚を焼き直し、この Mac の中で出し続ける。

【なぜ要るか】2026-09-21 施主指摘「掲示板が更新されても、アーティファクト自体は1日1回しか
更新されない」。裁定 EDO-0298=A+B の B。外からは Artifact(手仕舞いごとに上書き・
`.claude/hooks/edo_board_fresh.py`)、机の前ではこの窓(5 分以内)の二本立て。

    http://127.0.0.1:8787/        … 普請場の一枚(最新)
    http://127.0.0.1:8787/summary.json

⛔ 公開の判(`--published`)はここでは押さない。判は「施主の目に入る Artifact が新しい」ことの
   印なので、ローカルの焼き直しで押すと外向きの遅れが見えなくなる。

常駐は launchd(`Tools/Session/board_window.plist` を ~/Library/LaunchAgents/ へ):
    launchctl bootstrap gui/$UID ~/Library/LaunchAgents/jp.edo.board-window.plist
    launchctl bootout   gui/$UID/jp.edo.board-window        # 止めるとき
手で試すなら `python3 Tools/Session/board_window.py --once`(焼くだけ)。
"""
import argparse, functools, json, os, subprocess, sys, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edo_session import _common_git_dir

GITDIR = _common_git_dir()
ROOT = os.path.dirname(GITDIR) if GITDIR.endswith(".git") else GITDIR
BOARD = os.path.join(GITDIR, "edo-board")
OUT = os.path.join(BOARD, "_pm")
GEN = os.path.join(ROOT, "Tools", "Session", "build_board_html.py")
POLL = 20          # 秒。板を見に行く間隔
FLOOR = 60         # 秒。どんなに板が動いても、この間隔より密には焼かない
CEIL = 600         # 秒。板が静かでも、これだけ経ったら焼く(claim と git log が古びるので)
SHOW_S = 60.0      # 秒。board_now と同じ — 手を止めてからこれを超えたら「施主の指示待ち」の黄になる


def newest():
    """焼き直しの要否を決める入力の最終更新(板・指図・コミット・claim)。"""
    t = 0.0
    for d, pat in ((BOARD, ".json"), (os.path.join(ROOT, "docs", "Sashizu"), ".json"),
                   (os.path.join(GITDIR, "edo-locks"), ".json")):
        try:
            for f in os.listdir(d):
                if f.endswith(pat):
                    t = max(t, os.path.getmtime(os.path.join(d, f)))
        except Exception:
            pass
    for f in (os.path.join(GITDIR, "HEAD"), os.path.join(GITDIR, "refs")):
        try:
            t = max(t, os.path.getmtime(f))
        except Exception:
            pass
    return t


def bake():
    r = subprocess.run([sys.executable, GEN], cwd=ROOT, capture_output=True, text=True, timeout=180)
    ok = r.returncode == 0
    print("%s 焼いた: %s" % (time.strftime("%m-%d %H:%M:%S"), "⭕" if ok else "⛔ " + r.stderr.strip()[:200]),
          flush=True)
    return ok


def due_after(now):
    """焼いた結果に「手を止めた」(まだ SHOW_S 未満)の窓があれば、**黄へ変わる頃**に焼き直す時刻を返す。
    ⭐ 板は Stop の直後に焼かれる(`edo_board_fresh.py`)ので、手を止めた窓はいつも 0 分で写る。
       静かな時間はそれきり CEIL(10分)まで焼かれず、施主を待つ窓が黄にならなかった。
       黄が出るのは「手を止めて 60 秒」— その時刻をこちらから指しておく。無ければ 0。"""
    try:
        ws = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8")).get("windows") or []
    except Exception:
        return 0.0
    left = [SHOW_S - (w.get("min") or 0) * 60 for w in ws if w.get("state") == "paused"]
    return (now + max(min(left), 5) + 5) if left else 0.0


def watch():
    last_src, last_bake, due = 0.0, 0.0, 0.0
    while True:
        try:
            src = newest()
            now = time.time()
            if (src > last_src and now - last_bake > FLOOR) or (now - last_bake > CEIL) or (due and now >= due):
                if bake():
                    last_src, last_bake, due = src, now, due_after(now)
        except Exception as e:
            print("watch: %r" % e, flush=True)
        time.sleep(POLL)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/dashboard.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")   # 焼き直しが即ひらく
        return SimpleHTTPRequestHandler.end_headers(self)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--once", action="store_true", help="1 回焼いて終わる(常駐しない)")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.once:
        return 0 if bake() else 1
    bake()
    threading.Thread(target=watch, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port),
                              functools.partial(Handler, directory=OUT))
    print("常時の窓: http://127.0.0.1:%d/ (%s を出す)" % (a.port, OUT), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    sys.exit(main() or 0)
