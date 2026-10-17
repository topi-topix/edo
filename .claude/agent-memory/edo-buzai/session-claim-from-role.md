---
name: session-claim-from-role
description: 役から edo_session.py claim を打つと窓の claim と note を書き換える・blender という資源は無い(2026-10-08)
metadata:
  type: feedback
---
Blender に排他の資源は無い(資源は unity/terrain/git-index/assets/main だけ)。スクリプトの道だけ claim すれば足りる。
**Why:** 役の身元は呼んだ窓そのもの。`claim --note` は窓の note([実装] EDO-xxxx)を上書きし、`release` は門番が止める。
**How to apply:** claim するなら道だけ・note は付けない(付けたら元の文言で打ち直す)。返すのは呼んだ窓に任せる。
