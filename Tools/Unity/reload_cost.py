#!/usr/bin/env python3
"""ドメインリロードに何秒使ったかを、そのとき開いていたシーン別に出す(EDO-0282①)。

なぜ: C# を1行直すたびに Unity はドメインを作り直し、**開いているシーンを丸ごと退避して
復元する**。赤坂(83ルート・290万オブジェクト)を開いたままだと1回 30〜36 秒、作業場
(地形+対象邸+隣)なら 7 秒。どちらで回していたかは Editor.log にしか残らないので、
ここで数えて手仕舞いのときに突きつける。

  使い方: python3 Tools/Unity/reload_cost.py [--log <path>] [--from-offset N] [--json]

⚠ Editor.log に時刻は入らない。区間を切りたいときは `--from-offset`(前回のバイト位置)。
  出力の末尾に今回のバイト位置を出すので、呼ぶ側はそれを控えて次に渡す。
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LOG = os.path.join(ROOT, "Logs", "Editor.log")

RE_OPEN = re.compile(r"(?:Opening|Loaded) scene '([^']+)'")   # 起動直後は Loaded しか出ない
RE_RELOAD = re.compile(r"Domain Reload Profiling: (\d+)ms")
RE_AWAKE = re.compile(r"AwakeInstancesAfterBackupRestoration \((\d+)ms\)")


def scan(path, offset=0):
    """(rows, end_offset) — rows は {scene, ms, awake_ms} の並び。

    ⚠ `offset` は**報告する範囲**を切るだけで、読むのは常に頭から。途中から読むと
    「そのとき開いていたシーン」を見失い、全部が (シーン前) に落ちる(2026-09-21 に踏んだ)。"""
    rows, scene = [], None
    if not os.path.exists(path):
        return rows, 0
    with open(path, "rb") as fb:
        raw = fb.read()
    pos = 0
    for bline in raw.splitlines(keepends=True):
        here, pos = pos, pos + len(bline)
        line = bline.decode("utf-8", "replace")
        m = RE_OPEN.search(line)
        if m:
            scene = os.path.splitext(os.path.basename(m.group(1)))[0]
            continue
        if here < offset:                       # 範囲の手前 — シーンの追跡だけ続ける
            continue
        m = RE_RELOAD.search(line)
        if m:
            rows.append({"scene": scene, "ms": int(m.group(1)), "awake_ms": 0})
            continue
        m = RE_AWAKE.search(line)
        if m and rows and rows[-1]["awake_ms"] == 0:
            rows[-1]["awake_ms"] = int(m.group(1))
    return rows, len(raw)


def summarize(rows):
    """シーン別に畳む。⚠ シーンの行より前のリロード(起動の最初の1回)は scene=None。"""
    agg = {}
    for r in rows:
        k = r["scene"] or "(シーン前)"
        a = agg.setdefault(k, {"n": 0, "ms": 0, "awake_ms": 0, "each": []})
        a["n"] += 1
        a["ms"] += r["ms"]
        a["awake_ms"] += r["awake_ms"]
        a["each"].append(r["ms"])
    for a in agg.values():
        e = sorted(a["each"])
        a["median_ms"] = e[len(e) // 2] if e else 0
    return agg


def lines(agg, heavy=("Akasaka",)):
    """報告の行。作業場との差を「取り戻せた秒数」として出す。"""
    if not agg:
        return ["ドメインリロードの記録なし"]
    koba = agg.get("Koba")
    koba_med = koba["median_ms"] if koba else 6900      # 実測 2026-09-21: 作業場 6.9 秒
    out, waste, total = [], 0, 0
    for k in sorted(agg, key=lambda k: -agg[k]["ms"]):
        a = agg[k]
        total += a["ms"]
        mark = "⚠ " if k in heavy else "  "
        out.append("%s%-14s %2d回 %6.1fs(中央値 %4.1fs・うち復元 %5.1fs)"
                   % (mark, k, a["n"], a["ms"] / 1000.0, a["median_ms"] / 1000.0, a["awake_ms"] / 1000.0))
        if k in heavy:
            waste += max(0, a["ms"] - a["n"] * koba_med)
    out.append("  合計 %.0f 秒。うち**作業場で回していれば要らなかった分 %.0f 秒**"
               "(作業場の中央値 %.1fs で置き換えた場合)" % (total / 1000.0, waste / 1000.0, koba_med / 1000.0))
    if waste > 60000:
        out.append("  ⛔ 建て直しは作業場で回すこと — Edo/普請/作業場を開く(対象邸+隣+地形)。→ CLAUDE.md『触ると壊れるもの』")
    return out


def report(log=DEFAULT_LOG, offset=0):
    rows, end = scan(log, offset)
    return lines(summarize(rows)), end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--from-offset", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows, end = scan(a.log, a.from_offset)
    if a.json:
        print(json.dumps({"rows": rows, "by_scene": summarize(rows), "end_offset": end},
                         ensure_ascii=False, indent=1))
        return 0
    for l in lines(summarize(rows)):
        print(l)
    print("  (次はここから: --from-offset %d)" % end)
    return 0


if __name__ == "__main__":
    sys.exit(main())
