---
name: writeback-before-measuring
description: Stage を流したら計測・レンダの前に書き戻す。途中で他所の .cs 保存で domain reload が走り、待つ間に Unity の claim が他の窓へ移って書き戻せなくなった
metadata:
  type: project
---

症状: 山王 EDO-0415(2026-09-23)。Stage2 → 計測 → レンダの途中で、呼び出し元の窓が EdoSannoShaRebuild.cs を保存して domain reload(bridge 断)。
reload を待つ間に Unity は EDO-0401 の窓の手へ渡り、門番が execute_code を止めた。Stage2 の結果は作業場シーンに載ったまま、書き戻しも保存もされていない。
対処: 流したら**すぐ**「触った分だけ」で書き戻す(計測とレンダは書き戻した後でも取れる)。reload は2分待てば戻るが、claim は待ってくれない。

関連: [[pitfall-bridge-drops-after-domain-reload]] [[cs-edit-is-not-claim-free]]
