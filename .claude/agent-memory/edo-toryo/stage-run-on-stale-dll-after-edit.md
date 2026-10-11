---
name: stage-run-on-stale-dll-after-edit
description: .cs を保存した直後に execute_code で Stage を流すと古い DLL で走る(岡部 第109巡 s3b3 が 25 分の 3b を直す前の皮で焼いた)・再起動後は皮のプレハブが消えた資産を指す
metadata:
  type: project
---

2026-10-11 EDO-0502 第109巡(岡部)。

1. **症状**: OutsideBase(区画の外の皮の地盤)を直して 1 分後に Stage3b_Hifu を execute_code で流した(s3b3・25 分)が、道の上の土の棚
   (辺41 s45〜62・線の外で地形 +1.8)が全く変わらなかった。次の compile_wait が「DLL 1 件」を焼き直した ⇒ 3b は直す前のアセンブリで走っていた。
   **原因**: Unity は保存を見ても外から頼まれるまでコンパイルしない(.claude/rules/unity.md)。execute_code の中の Reload() は指図を読み直すだけ。
   **対処**: .cs を触ったら Stage の前に必ず compile_wait.py。長い Stage の前は特に(25 分を空振る)。
2. **症状**: 施主が Unity を立ち上げ直すと、作業場の EdgeSkin のメッシュが null(皮が無く穴だけ開いた姿)。
   **原因**: 書き戻し(17:22)の後に 3b を流すと新しい皮の資産を焼いて古い資産を消すが、プレハブは書き戻していない ⇒ プレハブが消えた資産を指す。
   **対処**: 3b の後は計測より先に書き戻す([[writeback-before-measuring]])。調べるだけなら最新の EdgeSkin_<邸>_*.asset を差す([[unity-kill-leaves-holes-without-skin]])。
