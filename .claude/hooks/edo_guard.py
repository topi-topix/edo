#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""門番のフック — Claude Code のツール呼び出しを見て、他セッションとの衝突だけを止める。

stdin に PreToolUse の JSON が来る(session_id / tool_name / tool_input)。
止めるときは **終了コード2 + stderr**(stderr がそのまま Claude に返る)。
素通りは終了コード0。⚠ **フックが落ちても作業は止めない** — 例外は握りつぶして 0 を返す。

【文脈計】(2026-09-13・計画 A-2 / 2026-09-21 に再武装を足した・EDO-0259)transcript の末尾から
最後の assistant の文脈(トークン)を読み、天井を超えていたら止めて「手仕舞い→ /compact」を返す。
⛔ **一つの発話につき高々一度**しか止めない — モデルは自分で `/compact` できないので、
止め続ければ一歩も進めない。⭕ 逆に「段ごとに一度」だけだと**一度素通りした後は永久に黙る**:
2026-09-21 の実測では 306K で一度止めた後、7 件の宿題を片付けて 414K に達するまで一度も鳴らなかった。
そこで再武装する — ①新しい段(300K/450K/600K)を超えた ②**人が話した**(止めを受け取る相手が
今そこにいて `/compact` を打てる)③前の止めから 100K 伸びた。

【丸読みの関門】(2026-09-21・EDO-0259 後半)手引きの丸読みを止める。`sources.md` は 356KB
(≈90K トークン)で、一度 Read しただけで天井の 3 割を使う。64KB を超える文書を offset/limit 無しで
読もうとしたら、**見出しの索引を返して**止める。⚠ これは速度制限であって禁止ではない —
`limit` を明に付けて読み直せば通る(丸読みを「うっかり」から「決めてやること」へ変えるのが狙い)。

あわせて最後の**人間の発話**の時刻を `.git/edo-session/<sid>.json` に刻む — `review_gate.py` の
三巡則(同じ役で fail 3 回)はこの時刻より後の記録だけを数える。
実測(2026-09-13): 主セッションの読みの 44% が文脈 300K 超だった。散文の天井は守られなかった。

    python3 .claude/hooks/edo_guard.py --selftest   # 止める/通すの型を検める
"""
import json
import os
import subprocess
import sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _main_root(start):
    """git の common-dir から、全 worktree が共有する main のルートを解く。
    ⚠ **worktree で動くセッションは CLAUDE_PROJECT_DIR がその worktree を指す。**
    sparse worktree には Tools/ も入るが、main を更新しても sashizu/<邸> ブランチへ
    マージするまでは古いまま — フックが worktree 内の CLI を呼ぶと、9677eea の
    wait/unwait も 81a5250 の身元判定の是正も届かず、「入口ごとに判定が違う」現象になる
    (2026-08-31、松平・外堀の両セッションが実例で発見・EDO-0076)。
    git-common-dir はどの worktree から見ても main の .git を指すので、
    その親を「常に最新のツールが置かれている場所」として使う。"""
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


def run(args, sess):
    env = dict(os.environ)
    env["EDO_SESSION_ID"] = sess
    # ⚠ CLAUDE_PROJECT_DIR は呼び出し元の実際の作業場所(worktree ならその cwd)のまま渡す —
    #   CLI のコード自体は MAIN_ROOT の最新版を使うが、sid() の cwd 判定や rel() の
    #   パス相対化は「このセッションが今どこにいるか」を見るべきなので変えない。
    env["CLAUDE_PROJECT_DIR"] = ROOT
    r = subprocess.run([sys.executable, CLI] + args, capture_output=True, text=True, env=env)
    if r.returncode == 2:
        sys.stderr.write(r.stderr)
        sys.exit(2)
    sys.exit(0)


CTX_STAGES = (300000, 450000, 600000)
CTX_REARM = 100000          # 同じ発話の中でも、前の止めからこれだけ伸びたらもう一度止める
SESS_DIR = os.path.join(MAIN_ROOT, ".git", "edo-session")   # claim(.git/edo-locks)・板(.git/edo-board)と同じ前例


def ctx_verdict(st, ctx, last_user):
    """止めるか・なぜか。**状態と数だけで決める純関数**(--selftest が検める)。

    ⛔ 一つの発話につき高々一度(モデルは自分で /compact できない)。
    ⭕ 再武装は ①段 ②発話 ③伸び の三つ。返すのは (止めるか, 段, 理由)。"""
    stage = sum(1 for t in CTX_STAGES if ctx > t)
    if stage == 0:
        return False, 0, ""
    if stage > int(st.get("ctx_stage") or 0):
        return True, stage, "天井 %dK を超えた" % (CTX_STAGES[stage - 1] // 1000)
    if last_user and last_user != st.get("ctx_stop_user"):
        return True, stage, "まだ天井の上にいる(前の止めの後にあなたが話した)"
    if ctx - int(st.get("ctx_stop_ctx") or 0) >= CTX_REARM:
        return True, stage, "前に止めてから %dK 伸びた" % ((ctx - int(st.get("ctx_stop_ctx") or 0)) // 1000)
    return False, stage, ""


def holding(sess):
    """このセッションが握っている物を1行に。手仕舞いの手順を具体にするため(空なら "")。"""
    try:
        d = json.load(open(os.path.join(MAIN_ROOT, ".git", "edo-locks", sess + ".json"), encoding="utf-8"))
    except Exception:
        return ""
    got = list(d.get("resources") or [])
    n = len(d.get("paths") or [])
    if n:
        got.append("%d 件のファイル" % n)
    return "・".join(got)


def context_meter(ev, sess):
    """文脈の天井(計画 A-2)。天井の上では発話ごとに一度 exit 2。人間の発話の時刻も刻む。"""
    tp = ev.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        return
    sys.path.insert(0, os.path.join(MAIN_ROOT, "Tools", "Session"))
    try:
        from token_report import last_context, last_user_ts
    except Exception:
        return
    ctx = last_context(tp)
    if ctx is None:
        return
    os.makedirs(SESS_DIR, exist_ok=True)
    fp = os.path.join(SESS_DIR, sess + ".json")
    try:
        st = json.load(open(fp, encoding="utf-8"))
    except Exception:
        st = {}
    ts = last_user_ts(tp)
    if ts:
        st["last_user"] = ts
    st["ctx"] = ctx
    st["transcript"] = tp
    # ⭕ 止めた回数は**0 でも刻む** — 欄が無いのと「一度も止めなかった」は別物で、
    #   後者こそ天井が守られなかった証拠(token_report の `止` 欄・規則19)。
    st.setdefault("ctx_stops", 0)
    stop, stage, why = ctx_verdict(st, ctx, ts)
    if stop:
        st["ctx_stage"] = stage
        st["ctx_stop_user"] = ts
        st["ctx_stop_ctx"] = ctx
        st["ctx_stops"] = int(st.get("ctx_stops") or 0) + 1      # 何回止めたか(token_report が読む・規則19)
    tmp = fp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    os.replace(tmp, fp)
    if stop:
        got = holding(sess)
        sys.stderr.write(
            "⛔ 文脈計: この会話の文脈が %dK トークンで、天井 300K の上にいる — %s"
            "(docs/fushin-bugyo.md「文脈の作法」)。\n"
            "   費用は「文脈の大きさ × 往復の数」。ここから先の往復は毎回 %dK を読み直す。\n"
            "   ① 手仕舞い — 畳めなかった残タスクを board へ task で起票し、claim を返す%s\n"
            "   ② ユーザーに **`/compact`(定型: 裁定・_pending・claim・次の一手だけ残す)か新セッション**を求める\n"
            "   この止めは**一つの発話につき一度**。次の呼び出しは通るので、まず①を済ませてから②を頼む。\n"
            % (ctx // 1000, why, ctx // 1000,
               ("(いま握っているのは %s)" % got) if got else "(いま握っている物は無い)"))
        sys.exit(2)


BIG_READ = 64 * 1024        # これを超える文書の丸読みは止めて索引を返す(≈16K トークン)
READ_EXT = (".md", ".txt", ".tsv", ".csv", ".log")


def big_read(ti):
    """手引き・考証の丸読みを止め、**見出しの索引**を返す(EDO-0259)。

    ⛔ 止めるのは offset も limit も付いていない読みだけ。⚠ 禁止ではない —
    limit を明に付ければ通る。狙いは「うっかり 90K トークン」を「決めてやること」へ変えること。"""
    fp = ti.get("file_path") or ""
    if not fp or ti.get("offset") or ti.get("limit"):
        return
    if not fp.lower().endswith(READ_EXT):
        return                                   # 画像・コード・JSON は対象外(JSON は python で読む物)
    try:
        sz = os.path.getsize(fp)
    except OSError:
        return
    if sz < BIG_READ:
        return
    idx = []
    try:
        with open(fp, encoding="utf-8", errors="replace") as fh:
            for n, ln in enumerate(fh, 1):
                if ln.startswith("#"):
                    idx.append("%6d  %s" % (n, ln.rstrip()[:78]))
                if len(idx) >= 60:
                    idx.append("       … 見出しはまだ続く(`grep -n '^#' <file>`)")
                    break
    except OSError:
        pass
    sys.stderr.write(
        "⛔ 丸読みの関門: %s は %dKB(≈%dK トークン・天井 300K の %d%%)。\n"
        "   要る節だけ読む: `Read(offset=…, limit=…)` か `grep -n` で当たりを付ける。\n"
        "   ⚠ どうしても全部要るなら **limit を明に付けて**読み直せば通る(丸読みは決めてやること)。\n"
        "%s"
        % (os.path.relpath(fp, MAIN_ROOT) if fp.startswith(MAIN_ROOT) else fp,
           sz // 1024, sz // 4096, min(99, (sz // 4096) * 100 // 300),
           ("   見出しの索引:\n" + "\n".join(idx) + "\n") if idx else ""))
    sys.exit(2)


def _my_estate(sess):
    """このセッションの claim の `sashizu:<邸>` から邸名を引く。無ければ None。"""
    try:
        r = subprocess.run([sys.executable, CLI, "status"], capture_output=True, text=True,
                           env=dict(os.environ, EDO_SESSION_ID=sess, CLAUDE_PROJECT_DIR=ROOT), timeout=10)
        block, hit = r.stdout.split("\n"), None
        for i, ln in enumerate(block):
            if ln.strip().startswith("▶"):
                for ln2 in block[i + 1:i + 12]:
                    if ln2.strip().startswith(("▶", "・")) and not ln2.strip().startswith("▶ " + sess[:8]):
                        break
                    if "sashizu:" in ln2:
                        hit = ln2.strip().split("sashizu:", 1)[1].split()[0]
                        break
                break
        return hit if hit and hit not in ("infra", "cross") else None
    except Exception:
        return None


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    sess = (ev.get("session_id") or "unknown")[:12]
    try:
        context_meter(ev, sess)
    except SystemExit:
        raise
    except Exception:
        pass
    if not os.path.exists(CLI):
        sys.exit(0)
    tool = ev.get("tool_name") or ""
    ti = ev.get("tool_input") or {}
    if tool == "Read":
        big_read(ti)
        sys.exit(0)
    if tool == "Agent":
        # 三巡則(計画 B-1)— 検分役を呼ぶ前に、同じ役の fail がユーザー入力なしに 3 回続いていないか。
        st = (ti.get("subagent_type") or "")
        if st in ("edo-kenzu", "edo-kosho", "edo-niwashi"):
            est = _my_estate(sess)
            gate = os.path.join(MAIN_ROOT, "Tools", "Sashizu", "review_gate.py")
            if est and os.path.exists(gate):
                r = subprocess.run([sys.executable, gate, "--rounds", est], capture_output=True, text=True)
                if r.returncode == 2:
                    sys.stderr.write("⛔ 門番(三巡則): %s の検分を止めた。\n%s" % (est, r.stdout))
                    sys.exit(2)
        sys.exit(0)
    if tool in ("Write", "Edit", "NotebookEdit"):
        fp = ti.get("file_path") or ti.get("notebook_path")
        if fp:
            run(["check-write", fp], sess)
    elif tool in ("Bash", "BashOutput"):
        cmd = ti.get("command")
        if cmd:
            run(["check-bash", cmd], sess)
    elif tool.startswith("mcp__unityMCP__"):
        # 読むだけのものは通す(状態を変えない)
        if tool.split("__")[-1] in ("read_console", "get_sha", "find_in_file", "unity_docs",
                                    "unity_reflect", "debug_request_context", "find_gameobjects",
                                    "manage_script_capabilities", "get_test_job"):
            sys.exit(0)
        run(["check-unity"], sess)
    sys.exit(0)


def selftest():
    """止める/通すの型を検める。⛔ 0 件は合格ではない — 型を足したらここへ1行足す(規則19)。"""
    U1, U2 = "2026-09-21T06:00:00Z", "2026-09-21T07:00:00Z"
    cases = [
        # (状態, 文脈, 最後の発話, 止まるか, 何を守る型か)
        ({}, 250000, U1, False, "天井の下では鳴らない"),
        ({}, 306000, U1, True, "300K を初めて超えたら止める"),
        ({"ctx_stage": 1, "ctx_stop_user": U1, "ctx_stop_ctx": 306000}, 320000, U1,
         False, "同じ発話の中では二度止めない(⛔ 自分で /compact できないので進めなくなる)"),
        ({"ctx_stage": 1, "ctx_stop_user": U1, "ctx_stop_ctx": 306000}, 320000, U2,
         True, "⭐ 人が話したら再武装(2026-09-21 に 7 件素通りした穴)"),
        ({"ctx_stage": 1, "ctx_stop_user": U1, "ctx_stop_ctx": 306000}, 414000, U1,
         True, "⭐ 同じ発話でも 100K 伸びたら再武装(自走の巡)"),
        ({"ctx_stage": 1, "ctx_stop_user": U1, "ctx_stop_ctx": 306000}, 460000, U1,
         True, "次の段(450K)は発話に関わらず止める"),
        ({"ctx_stage": 1, "ctx_stop_user": U1, "ctx_stop_ctx": 306000}, 320000, None,
         False, "発話の時刻が読めない時は、伸びと段だけで決める"),
    ]
    bad = 0
    for st, ctx, usr, want, name in cases:
        got = ctx_verdict(dict(st), ctx, usr)[0]
        if got != want:
            bad += 1
            print("  ⛔ %s — %dK で %s のはずが %s" % (name, ctx // 1000, "止" if want else "通", "止" if got else "通"))
    reads = [
        ({"file_path": os.path.join(MAIN_ROOT, "CLAUDE.md")}, False, "小さい文書は通す"),
        ({"file_path": os.path.join(MAIN_ROOT, "Tools/Skills/unity-buke-yashiki/references/sources.md")},
         True, "356KB の手引きの丸読みは止める"),
        ({"file_path": os.path.join(MAIN_ROOT, "Tools/Skills/unity-buke-yashiki/references/sources.md"),
          "limit": 200}, False, "⚠ limit を明に付けたら通す(禁止ではない)"),
        ({"file_path": os.path.join(MAIN_ROOT, "docs/Sashizu/base_dem.json")}, False,
         "JSON は対象外(python で読む物)"),
    ]
    for ti, want, name in reads:
        if not os.path.exists(ti["file_path"]):
            print("  ⚠ %s — 検体が無い(%s)" % (name, ti["file_path"])); continue
        # ⭕ フックそのものを stdin 付きで呼ぶ(判定だけでなく**入口の配線**まで検める)
        r = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True,
                           input=json.dumps({"session_id": "selftest000", "tool_name": "Read", "tool_input": ti}))
        got = r.returncode == 2
        if got != want:
            bad += 1
            print("  ⛔ %s — %s のはずが %s" % (name, "止" if want else "通", "止" if got else "通"))
    # ⭐ 配線まで通しで検める — 判定が正しくても、transcript から文脈を読めなければ一度も鳴らない
    #   (2026-09-21 の穴はまさに「鳴っていないことが誰にも見えない」種類だった)。
    import tempfile
    e2e = 0
    sid = "selftest000"
    tp = os.path.join(tempfile.gettempdir(), "edo_guard_selftest.jsonl")
    state = os.path.join(SESS_DIR, sid + ".json")

    def transcript(usr):
        # ⚠ **詰めた JSON で書く** — `last_user_ts` は速さのため `"type":"user"` の素の文字列で
        #   前ふるいをする。空白を入れると本物の transcript と違う形になり、検体だけ素通りする。
        j = lambda d: json.dumps(d, separators=(",", ":"))
        with open(tp, "w", encoding="utf-8") as f:
            f.write(j({"type": "user", "timestamp": usr,
                       "message": {"content": "次のタスクお願いします"}}) + "\n")
            f.write(j({"type": "assistant", "timestamp": usr,
                       "message": {"usage": {"input_tokens": 6000,
                                             "cache_read_input_tokens": 300000}}}) + "\n")

    def fire():
        r = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True,
                           input=json.dumps({"session_id": sid, "transcript_path": tp,
                                             "tool_name": "Bash", "tool_input": {"command": "true"}}))
        return r.returncode == 2
    try:
        for usr, want, name in ((U1, True, "通しで: 306K の transcript で鳴る"),
                                (U1, False, "通しで: 同じ発話では二度目は通る"),
                                (U2, True, "通しで: 次の発話でまた鳴る")):
            transcript(usr)
            if fire() != want:
                e2e += 1
                print("  ⛔ %s — %s のはずが逆" % (name, "止" if want else "通"))
        n = json.load(open(state, encoding="utf-8")).get("ctx_stops")
        if n != 2:
            e2e += 1
            print("  ⛔ 通しで: 止めた回数が %s(2 のはず・token_report の `止` 欄が読む)" % n)
    except Exception as ex:
        e2e += 1
        print("  ⛔ 通しの検め自体が落ちた: %s" % ex)
    finally:
        for f in (tp, state):
            try:
                os.remove(f)
            except OSError:
                pass
    bad += e2e
    print(("⛔ 門番の型 — 破れ %d 件" % bad) if bad else
          "⭕ 門番 — %d 型(文脈の再武装 %d・丸読みの関門 %d・通しの配線 4)"
          % (len(cases) + len(reads) + 4, len(cases), len(reads)))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)          # フックの不調で作業を止めない
