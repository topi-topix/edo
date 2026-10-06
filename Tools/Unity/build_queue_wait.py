#!/usr/bin/env python3
"""EdoBuildQueue に予約した区画の建て直しを待つ一手(EDO-0517)。

  使い方: python3 Tools/Unity/build_queue_wait.py <置き場> [--timeout 3600] [--stall 900] [--json]

  <置き場> は execute_code で `EdoBuildQueue.Enqueue("<置き場>", "id1", ...)` に渡したのと同じ所。
  Unity へは問い合わせない(ファイルを読むだけ)── MCP の時間切れ・再送を起こさない。

  読むもの(書くのは Assets/Edo/Scripts/Editor/EdoBuildQueue.cs):
    _queued      予約の時刻と区画
    _state.json  様子(phase=queued/building/running/waiting-editor/ok/canceled・beat=最後に書いた時刻)
    <id>.txt     区画ごとの結果(1 行目が BuildParcel の返り)と sec=
    _done        済(ok=/fail=/skipped=)

  終了コード: 0 = 全部済んで失敗 0 ・ 1 = 済んだが失敗・取り消しあり ・ 2 = 時間切れ・止まっている

  止まっていると判じる所(固定の sleep で待たず、印の古さで判じる):
    - _state.json が出ない(予約から 90 秒)= 新しい EdoBuildQueue がまだコンパイルされていない、
      または Unity が拍を打っていない
    - phase=building のまま beat が --stall 秒より古い = 1 区画が終わらない(落ちた・固まった)
    - それ以外の phase で beat が 180 秒より古い = Unity が落ちた/再起動した(SessionState は再起動で消える)

⭐ 区画の建て直しを待つのはこれだけ。手書きの until/sleep の見張りは書かない(.claude/rules/unity.md)。
"""
import argparse, json, os, re, sys, time
from datetime import datetime

POLL = 2.0
NO_STATE_SEC = 90
IDLE_STALE_SEC = 180


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def age(beat):
    try:
        return (datetime.now() - datetime.fromisoformat(beat)).total_seconds()
    except Exception:
        return None


def summary(d, ids):
    rows = []
    for i in ids:
        t = read(os.path.join(d, i.replace(":", "_") + ".txt"))  # ~call:<型>.<関数> は : を _ にした名
        if t is None:
            rows.append((i, "—", "(未着手)"))
            continue
        lines = t.strip().splitlines()
        sec = next((l[4:] for l in reversed(lines) if l.startswith("sec=")), "?")
        rows.append((i, sec, lines[0][:140] if lines else ""))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--timeout", type=float, default=3600)
    ap.add_argument("--stall", type=float, default=900, help="1 区画を建てている間の無音の上限(秒)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = os.path.abspath(a.dir)

    q = read(os.path.join(d, "_queued"))
    if q is None:
        print(f"⛔ 予約が無い: {d}/_queued が無い ── execute_code で EdoBuildQueue.Enqueue を呼んだか")
        return 2
    ids = q.split()[1:]
    t0 = time.time()
    seen = -1
    code, why = 2, ""
    while True:
        done = read(os.path.join(d, "_done"))
        if done is not None:
            parts = done.split()
            ok = len(parts) > 1 and parts[1] == "ok" and re.search(r"\bfail=0\b", done) is not None
            code, why = (0 if ok else 1), done.strip()
            break
        st_raw = read(os.path.join(d, "_state.json"))
        st = None
        if st_raw:
            try:
                st = json.loads(st_raw)
            except ValueError:
                st = None  # 書きかけ。次の拍で読む
        el = time.time() - t0
        if st is None:
            qmt = os.path.getmtime(os.path.join(d, "_queued"))
            if not st_raw and time.time() - qmt > NO_STATE_SEC:
                why = ("⛔ _state.json が出ない ── 新しい EdoBuildQueue がコンパイルされていないか(compile_wait.py)、"
                       "Unity が拍を打っていない")
                break
        else:
            n = len(st.get("done") or [])
            if n != seen:
                seen = n
                print(f"  {int(el):>5}s  済 {n}/{st.get('total')}  失敗 {st.get('failed')}  "
                      f"{st.get('phase')} {st.get('current') or ''}", flush=True)
            ag = age(st.get("beat", ""))
            if ag is not None:
                if st.get("phase") == "building" and ag > a.stall:
                    why = f"⛔ {st.get('current')} を建て始めて {int(ag)} 秒 音が無い(--stall {int(a.stall)})── 落ちたか固まった"
                    break
                if st.get("phase") != "building" and ag > IDLE_STALE_SEC:
                    why = (f"⛔ 様子が {int(ag)} 秒更新されない(phase={st.get('phase')})── Unity が落ちた・再起動した"
                           "(予約は再起動で消える。残りは Enqueue し直す)")
                    break
        if el > a.timeout:
            why = f"⛔ 時間切れ {int(a.timeout)} 秒"
            break
        time.sleep(POLL)

    rows = summary(d, ids)
    if a.json:
        print(json.dumps({"code": code, "why": why, "sec": round(time.time() - t0, 1),
                          "parcels": [{"id": i, "sec": s, "result": r} for i, s, r in rows]}, ensure_ascii=False))
    else:
        print(why)
        for i, s, r in rows:
            print(f"  {i:<28} {s:>6}s  {r}")
    return code


if __name__ == "__main__":
    sys.exit(main())
