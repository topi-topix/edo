#!/usr/bin/env python3
"""C# を直した後の「コンパイルして待つ」を一手で済ませる(EDO-0457)。

  使い方: python3 Tools/Unity/compile_wait.py [--no-check] [--timeout 180] [--json]

  ① `Tools/Unity/cs_check.sh`(Unity 不要・3〜5 秒)で `error CS` を先に拾う。あれば Unity に触らず止める
  ② Unity の橋(MCP for Unity の 6401 番)へ直に refresh を頼む
  ③ 待つ目印は `Logs/Editor.log` の行(バイト位置で区間を切る)— 固定の sleep は使わない
       再読み込みの完了 `Domain Reload Profiling` / 失敗 `Tundra build failed`・`error CS` /
       作り直し無し(コンパイルが要らなかった・DLL が 0 件更新)
  ④ 橋の上で本物のコマンド(read_console)が返るまで待つ = MCP が戻った。ping は橋の IO スレッドが
     即答するので目印にならない
  ⑤ 所要秒・結果を1行で返す

  試験(Unity 不要): python3 Tools/Unity/compile_wait.py --replay — 過去の Editor.log で読み分けを検める

  終了コード: 0 = 再読み込み済み / 作り直し無し ・ 1 = コンパイルの誤り ・ 2 = 時間切れ・橋に繋がらない

⭐ **C# を直したらこれだけを使う。**手書きの `sleep`・`until`・DLL の日付の見張り・`refresh_unity` の
   重ね打ちは禁じる(`.claude/rules/unity.md`)。Unity の claim が要る(門番が check-bash で見る)。
⚠ Unity は**本体の作業ツリー**を見ている。worktree で直した .cs は Unity に届かない — 本体へ当ててから叩く。
"""
import argparse, glob, json, os, re, socket, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(os.path.dirname(HERE))


def main_root():
    """Unity が開いているのは本体。worktree から叩かれても本体の Logs/Library を見る。"""
    try:
        common = subprocess.run(["git", "-C", TREE, "rev-parse", "--git-common-dir"],
                                capture_output=True, text=True, timeout=5).stdout.strip()
        if common:
            return os.path.dirname(os.path.abspath(os.path.join(TREE, common)))
    except Exception:
        pass
    return TREE


ROOT = main_root()
LOG = os.path.join(ROOT, "Logs", "Editor.log")
STAMP = os.path.join(ROOT, "Temp", "edo_compile_wait.json")   # edo_precheck_assembly.sh が読む
DLL = os.path.join(ROOT, "Library", "ScriptAssemblies", "Assembly-CSharp-Editor.dll")

RE_RELOAD = re.compile(r"Domain Reload Profiling: (\d+)ms")
RE_TUNDRA_OK = re.compile(r"\*\*\* Tundra build success \(([\d.]+) seconds\), (\d+) items updated")
RE_TUNDRA_NG = re.compile(r"\*\*\* Tundra build failed")
RE_CS_ERR = re.compile(r"(Assets/\S+\.cs\(\d+,\d+\)): error (CS\d+): (.*)")
RE_COMPILE_REQ = re.compile(r"\[ScriptCompilation\] Requested script compilation")
RE_REFRESH_DONE = re.compile(r"Asset Pipeline Refresh \(id=\w+\): Total: ([\d.]+) seconds")


def judge(text):
    """refresh を頼んだ後の log の区間から、いまの状態を決める(純粋な関数 — 過去の log で試せる)。

    state: "wait"(まだ)/ "reload"(再読み込み済み)/ "error"(コンパイル失敗)/ "no_rebuild"(DLL 0 件更新)
    ⚠ 失敗は `Tundra build failed` の行で決める。`error CS` の行は失敗の行より先に出るので、そこで切ると
      誤りの一覧が途中で欠ける。"""
    st = {"state": "wait", "compile_req": bool(RE_COMPILE_REQ.search(text)),
          "refresh_done": bool(RE_REFRESH_DONE.search(text)), "tundra": None, "reload_ms": None, "errors": []}
    m = RE_TUNDRA_OK.search(text)
    if m:
        st["tundra"] = (float(m.group(1)), int(m.group(2)))
    if RE_TUNDRA_NG.search(text):
        st["state"] = "error"
        st["errors"] = sorted({"%s: %s %s" % e for e in RE_CS_ERR.findall(text)})[:20]
        return st
    m = RE_RELOAD.search(text)
    if m:
        st["state"], st["reload_ms"] = "reload", int(m.group(1))
        return st
    if st["tundra"] and st["tundra"][1] == 0:
        st["state"] = "no_rebuild"                 # 0 件更新 = DLL は変わらない = 再読み込みは来ない
    return st


# ─────────────────────────────── 橋(MCP for Unity の stdio bridge)
def bridge_port():
    for f in sorted(glob.glob(os.path.expanduser("~/.unity-mcp/unity-mcp-status-*.json"))):
        try:
            d = json.load(open(f))
            if os.path.normpath(d.get("project_path", "")).startswith(os.path.join(ROOT, "Assets")):
                return int(d["unity_port"]), d
        except Exception:
            continue
    return 6401, {}


def _recv_exact(s, n):
    buf = b""
    while len(buf) < n:
        c = s.recv(n - len(buf))
        if not c:
            raise ConnectionError("橋が閉じた")
        buf += c
    return buf


def bridge_call(cmd, params, timeout=10.0):
    """1 コマンドを投げて result を返す。繋がらない・閉じた・時間切れは例外。"""
    port, _ = bridge_port()
    s = socket.create_connection(("127.0.0.1", port), 1.0)
    try:
        s.settimeout(2.0)
        hello = s.recv(256)
        if b"FRAMING=1" not in hello:
            raise ConnectionError("橋の挨拶が違う: %r" % hello[:60])
        payload = json.dumps({"type": cmd, "params": params}).encode()
        s.sendall(struct.pack(">Q", len(payload)) + payload)
        s.settimeout(timeout)
        n = struct.unpack(">Q", _recv_exact(s, 8))[0]
        resp = json.loads(_recv_exact(s, n).decode("utf-8", "replace"))
    finally:
        s.close()
    if resp.get("status") == "error":
        raise RuntimeError(resp.get("error") or resp.get("message") or "Unity error")
    return resp.get("result", {})


def console_errors():
    """主スレッドで走るコマンド — これが返れば MCP は戻っている。"""
    r = bridge_call("read_console", {"action": "get", "types": ["error"], "count": 20,
                                     "filterText": "error CS", "format": "plain"}, timeout=8.0)
    data = r.get("data") if isinstance(r, dict) else r
    if isinstance(data, dict):
        data = data.get("items") or data.get("lines") or []
    return [str(x) for x in (data or []) if "error CS" in str(x)]


# ─────────────────────────────── Editor.log
def log_size():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def read_from(off):
    """off からの新しい行。Unity の再起動で log が短くなったら頭から。"""
    n = log_size()
    if n < off:
        off = 0
    with open(LOG, "rb") as f:
        f.seek(off)
        raw = f.read()
    return raw.decode("utf-8", "replace"), off + len(raw)


def newest_cs():
    t, path = 0.0, None
    for dp, dn, fn in os.walk(os.path.join(ROOT, "Assets")):
        for n in fn:
            if n.endswith(".cs"):
                p = os.path.join(dp, n)
                m = os.path.getmtime(p)
                if m > t:
                    t, path = m, p
    return t, path


def cs_check():
    sh = os.path.join(HERE, "cs_check.sh")
    r = subprocess.run(["zsh", sh], capture_output=True, text=True, cwd=ROOT,
                       env=dict(os.environ, EDO_ROOT=ROOT))
    return [l for l in (r.stdout + r.stderr).splitlines() if "error CS" in l]


def write_stamp(res, src_t):
    try:
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        json.dump({"src_mtime": src_t, "at": time.time(), "result": res["result"],
                   "seconds": res["seconds"]}, open(STAMP, "w"))
    except Exception:
        pass


def run(a):
    t0 = time.monotonic()
    res = {"result": None, "seconds": 0.0, "errors": [], "notes": [], "reload_ms": None}

    def done(result, code):
        res["result"] = result
        res["seconds"] = round(time.monotonic() - t0, 1)
        return res, code

    if os.path.realpath(TREE) != os.path.realpath(ROOT):
        res["notes"].append("worktree から叩いた — Unity が見るのは本体(%s)。worktree の .cs は届かない" % ROOT)

    # ① Unity を起こさずに誤りを拾う
    if not a.no_check:
        errs = cs_check()
        res["cs_check_s"] = round(time.monotonic() - t0, 1)
        if errs:
            res["errors"] = errs[:20]
            return done("コンパイルの誤り(cs_check・Unity に触らず止めた)", 1)

    src_t, src_p = newest_cs()
    off = log_size()
    _, st = bridge_port()

    # ② refresh を頼む。再読み込み中(橋が落ちている)なら頼まずに待つ — 重ね打ちで一周増やさない
    asked = False
    if st.get("reloading"):
        res["notes"].append("既に再読み込み中 — refresh は投げずに待った")
    else:
        try:
            bridge_call("refresh_unity", {"mode": "if_dirty", "scope": "all", "compile": "request",
                                          "wait_for_ready": False}, timeout=a.timeout)
            asked = True
        except (ConnectionError, socket.timeout, OSError) as e:
            # 橋が落ちた = 頼んだ refresh が再読み込みを起こした(想定どおり)か、既に起きていた
            res["notes"].append("refresh の返事の前に橋が落ちた(%s)— 再読み込みとみて待つ" % type(e).__name__)
            asked = True
        except RuntimeError as e:
            return done("refresh を断られた: %s" % e, 2)

    lap = res.setdefault("lap", {})               # 段ごとの経過秒(どこで待ったかを刷る)
    lap["依頼"] = round(time.monotonic() - t0, 1)

    # ③ Editor.log の目印を待つ
    deadline = time.monotonic() + a.timeout
    text, tundra, reload_ms, quiet_since = "", None, None, None
    while time.monotonic() < deadline:
        chunk, off = read_from(off)
        text += chunk
        st = judge(text)
        tundra = st.get("tundra")
        if tundra and "コンパイル" not in lap:
            lap["コンパイル"] = round(time.monotonic() - t0, 1)
        if st["state"] == "error":
            # 誤りの後も Unity は古い DLL で動いている — 橋が応えるのを確かめてから返す
            res["errors"] = st["errors"]
            break
        if st["state"] == "reload":
            reload_ms = st["reload_ms"]
            break
        if st["state"] == "no_rebuild":
            break
        # 作り直し無し: コンパイルの要求が出ず refresh が済んだ(log からは「来ない」を言えないので静けさで)
        if st["refresh_done"] and not st["compile_req"] and asked:
            quiet_since = quiet_since or time.monotonic()
            if time.monotonic() - quiet_since > 1.5:
                break
        time.sleep(0.2)                            # log を読む間隔(待ちの長さは log が決める)
    else:
        res["log_tail"] = text[-600:]
        return done("時間切れ(%d 秒)— log に完了の目印が出ない" % a.timeout, 2)

    lap["log の完了"] = round(time.monotonic() - t0, 1)

    # ④ MCP が戻るまで(主スレッドのコマンドが返るまで)
    ready = False
    while time.monotonic() < deadline:
        try:
            ce = console_errors()
            ready = True
            if res["errors"] or (ce and not reload_ms):
                res["errors"] = res["errors"] or ce[:20]
            break
        except Exception:
            time.sleep(0.25)
    if not ready:
        return done("再読み込みは済んだが MCP が戻らない(%d 秒)" % a.timeout, 2)

    lap["MCP"] = round(time.monotonic() - t0, 1)
    res["reload_ms"] = reload_ms
    res["tundra"] = tundra
    if res["errors"]:
        return done("コンパイルの誤り(Unity)", 1)
    if reload_ms is not None:
        write_stamp(dict(res, result="reloaded", seconds=round(time.monotonic() - t0, 1)), src_t)
        return done("再読み込み済み", 0)
    # 作り直し無し — DLL が .cs より古くても、Unity が「要らない」と判じた事を印に残す(precheck が読む)
    dll_t = os.path.getmtime(DLL) if os.path.exists(DLL) else 0
    if src_t > dll_t + 2:
        res["notes"].append("DLL は .cs より古いまま(%s)— Unity は作り直し不要と判じた"
                            % os.path.relpath(src_p, ROOT))
    write_stamp(dict(res, result="no_rebuild", seconds=round(time.monotonic() - t0, 1)), src_t)
    return done("作り直し無し", 0)


RE_API = re.compile(r"Requested script compilation because: Requested through public api")
RE_OBSERVED = re.compile(r"Requested script compilation because: AssetDatabase observed changes")


def replay(paths):
    """過去の log で読み分けを検める(Unity 不要)。⛔ 0 件は合格ではない — 区間の数を必ず刷る。

    ① 道具と同じ要求(public api)ごとに、次の同じ要求までに judge が決着するか(しなければ道具の空振り)
    ② 変更を見つけただけの要求(observed)が自力で決着したか — 手順書から「refresh を投げずに待て」を
       外した根拠。2026-09-26 の実測で 123 回中 71 回は外からの要求が来るまで止まっていた。"""
    import collections
    api, obs = collections.Counter(), collections.Counter()
    for path in paths:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines(keepends=True)
        reqs = [i for i, l in enumerate(lines) if RE_COMPILE_REQ.search(l)]
        apis = [i for i in reqs if RE_API.search(lines[i])]
        for k, s in enumerate(apis):
            e = apis[k + 1] if k + 1 < len(apis) else len(lines)
            st = judge("".join(lines[s:e]))["state"]
            api["log の終わり" if st == "wait" and e == len(lines) else st] += 1
        for k, s in enumerate(reqs):
            if RE_OBSERVED.search(lines[s]):
                e = reqs[k + 1] if k + 1 < len(reqs) else len(lines)
                st = judge("".join(lines[s:e]))["state"]
                obs["自力で決着" if st != "wait" else "止まった" if e < len(lines) else "log の終わり"] += 1
    n = sum(v for k, v in api.items() if k != "log の終わり")
    print("道具と同じ要求 %d 回: %s" % (n, dict(api)))
    print("変更を見つけただけの要求 %d 回: %s" % (sum(obs.values()), dict(obs)))
    miss = api.get("wait", 0)
    print(("⛔ 決着しない区間 %d 件 — judge の読み分けに穴" % miss) if miss or not n else "⭕ 空振り 0 件")
    return 1 if miss or not n else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--replay":
        ps = sys.argv[2:] or [LOG, os.path.join(ROOT, "Logs", "Editor-prev.log")]
        return replay([p for p in ps if os.path.exists(p)])
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-check", action="store_true", help="cs_check を飛ばす(直前に通したとき)")
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res, code = run(a)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return code
    mark = {0: "⭕", 1: "⛔", 2: "⚠"}[code]
    extra = []
    if res.get("cs_check_s") is not None:
        extra.append("cs_check %.1fs" % res["cs_check_s"])
    if res.get("reload_ms"):
        extra.append("再読み込み %.1fs" % (res["reload_ms"] / 1000.0))
    if res.get("tundra"):
        extra.append("DLL %d 件" % res["tundra"][1])
    print("%s %s — %.1f 秒%s" % (mark, res["result"], res["seconds"],
                                 ("(" + "・".join(extra) + ")") if extra else ""))
    if res.get("lap"):
        print("   経過: " + " → ".join("%s %.1fs" % kv for kv in res["lap"].items()))
    for e in res["errors"]:
        print("   " + e)
    for n in res["notes"]:
        print("   ⚠ " + n)
    if res.get("log_tail"):
        print("   log の末尾:\n" + "\n".join("     " + l for l in res["log_tail"].splitlines()[-8:]))
    return code


if __name__ == "__main__":
    sys.exit(main())
