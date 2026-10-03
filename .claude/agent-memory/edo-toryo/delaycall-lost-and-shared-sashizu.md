---
name: delaycall-lost-and-shared-sashizu
description: execute_code の delayCall で長い Stage を流すと、別窓の .cs 保存で起きる domain reload に黙って消される。同じ邸の指図を別の手が同時に書くと、Doc と Impl が別版になって範囲外の土留めが建つ
metadata:
  type: project
---

2026-09-25 EDO-0430 で二度踏んだ。
① delayCall で Stage2/3/9 を流すと、別セッションが EdoAssets.cs を保存した reload で予約が消え、出力ファイルが
「started」のまま止まる(CPU は静か)。Stage は 1 本ずつ 30 秒未満なら直に呼ぶ方が確実(山王 S2 4s / S3 6s / S9 15s)。
② 作業中に普請奉行が同じ指図へ本殿の西の欄を書き足してコミットした。キャッシュの差し替えで Doc(古)と Impl(新)が
食い違い、野面の土留めを城の石垣で建ててしまった ── 地形を実行前の .bin から戻して流し直した。

**Why:** 指図の claim は同じセッション ID の親も握るので門番は止めない。
**How to apply:** 流す直前に `shasum` と impl の src を突き合わせ、git log で HEAD の動きを確かめる。
積みが城の石垣でない土留め(`masonry` 欄)は Stage3 が退ける(2026-09-25 追加)。[[castlewall-face-is-local-minus-x]]

③ 2026-10-03 EDO-0535: 渡された直後に別窓(EDO-0554)が `kansei --reopen`(図から起こし直す)で phase を design へ戻していた。
関門の無い Stage1c は流れ(植栽 15 本を据え直し)、Stage6 で初めて ⛔ 検図関門が赤。**着手前に `review_gate.py <邸>` と
kansei の history の末尾を見る** ── 関門を持たない Stage(1c・地形だけの段)から流すと半端に建つ。
