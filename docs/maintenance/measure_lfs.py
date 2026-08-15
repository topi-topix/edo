#!/usr/bin/env python3
"""main の履歴が抱える LFS 実体をパス別に集計する。

    python3 docs/maintenance/measure_lfs.py [ref]

LFS はバージョンごとにファイルを丸ごと保存する(差分を取らない)ので、
「そのパスを何回コミットしたか」がそのまま保存量になる。
掃除(docs/maintenance/lfs-history-rewrite.md)の前後で走らせて比べる。
"""
import collections
import re
import subprocess
import sys

REF = sys.argv[1] if len(sys.argv) > 1 else "main"
LFS_RE = re.compile(
    r"\.(fbx|png|jpg|jpeg|tga|psd|exr|hdr|obj|blend|dll|bundle|mp4|wav|ogg|mp3|glb|gltf|tif|tiff|bmp)$",
    re.I,
)


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def is_lfs_path(p):
    return (
        bool(LFS_RE.search(p))
        or p.endswith("Akasaka.unity")
        or ("Edo/Terrain" in p and p.endswith(".asset"))
    )


def main():
    paths = sorted({p for p in sh("git", "log", "--format=", "--name-only", REF).split("\n") if p.strip()})
    tot, cnt, seen = collections.Counter(), collections.Counter(), set()
    for p in filter(is_lfs_path, paths):
        for rev in sh("git", "rev-list", REF, "--", p).split():
            blob = sh("git", "rev-parse", f"{rev}:{p}").strip()
            if not blob or blob in seen:
                continue
            m = re.search(r"^size (\d+)$", sh("git", "cat-file", "-p", blob)[:400], re.M)
            if not m:            # LFS ポインタでない = 通常の git オブジェクト
                continue
            seen.add(blob)
            key = "Akasaka.unity(シーン)" if p.endswith("Akasaka.unity") else "/".join(p.split("/")[:3])
            tot[key] += int(m.group(1))
            cnt[key] += 1

    print(f"=== {REF} の履歴が抱える LFS 実体 ===")
    for k, v in tot.most_common():
        print(f"{v / 1073741824:7.2f} GB  {cnt[k]:4d}本  {k}")
    print(f"\n総計 {sum(tot.values()) / 1073741824:.2f} GB / {sum(cnt.values())}本  (GitHub無料枠 1 GiB)")


if __name__ == "__main__":
    main()
