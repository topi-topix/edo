---
name: stepjoint-and-kado-return-traps
description: 袖の stepJoint は駒の勾配の上限で解けない・②の隅の返しの腕は延ばす向きの塞ぐ物で測ると全部③・否定文の「見切り石」を Contains で拾う・邸の Stage は EdoBuildQueue の ~call で流す
metadata:
  type: project
---
2026-10-07 EDO-0502(岡部 施主指摘 2026-10-06 夕 A〜D)。

1. **TW_Kado_Sode の stepJoint は在庫の勾配では解けない。** 袖の run は 0.08〜1.63m(0.5 刻みの段)で、背の法が 1:2.8 前後 ⇒
   要る勾配 0.31〜0.45 > 焼いた最大 ±0.275。2 間 ±0.12 も 1 間 ±0.275 も 7 継ぎ目すべて「高い側の長さ < 走り」で取れない。
   型は EdoBuild.FlowStepJoints(取れない継ぎ目は unresolved で返す)。解くのは部材(急な勾配の駒)か指図。
2. **②の隅の返しの腕を endRule.Block(延ばす向きの塞ぐ物 = 長屋の躯体から一間の全周)で測ると、妻の脇で終わる返し(TW_Minami_Koshi)が全部③。**
   指図は「長屋の背の一間」だけ ⇒ 腕は endRule.armBlock(長手の脇だけ一間・妻の先は実面 0.3)で測る。
3. 欄の文が「⛔ 見切り石を使わない」に変わっても `Contains("見切り石")` は真のまま(returnEnd の retMikiri)。否定の文で書式の分岐を拾わない。
4. 邸ビルダーの Stage は `EdoBuildQueue.Enqueue(dir, "~call:EdoOkabeYashikiBuilder.Stage2b_Dan", ...)` で予約し build_queue_wait.py で待つ(log は `~call_<型>.<関数>.txt`)。
   Stage2b は約40秒、3b が最も長い。

関連: [[nozura-end-rule-blocked-by-back-soil]] [[return-lost-when-sashizu-text-format-changes]] [[long-run-guard-and-soft-only-converge]]
