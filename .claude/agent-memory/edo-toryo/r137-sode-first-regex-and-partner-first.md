---
name: r137-sode-first-regex-and-partner-first
description: 岡部 第137巡 ── 石段の袖を先に据える欄の頭の語が「追記」から「(普請方 …・今のまま)」に変わり SodeFirstWall が黙って退いていた・離れて終わる交わり(端どうし 0.06〜1.5)は Links が継がず二つの隅の駒が同じ角に立つ・角の桝は版の差の和で選ぶ
metadata:
  type: project
---
2026-10-14 EDO-0502 第137巡。

1. **症状**: K_Kuruwa の袖が「上端の相手なし」・本線 TW_Kado_Hokuto_0_0/0_1 の口の端に自前の隅の駒(② の返し)。**原因**: SodeFirstWall が cuts の
   「追記 2026-10-10o」を探すが、欄の上書きで「(普請方 2026-10-10o・今のまま)」の書式になり一致せず、SodesBeforeNet が何も刷らずに退いた。
   **対処**: 日付の符号「2026-10-10o」だけで探す。⇒ [[return-lost-when-sashizu-text-format-changes]] と同じ型(三度目)。欄を読む正規表現は頭の語に頼らない。
2. **症状**: TW_Higashi_Se_3_0_kado6 と Side0_0_Kado0_kado1 が同じ角(0.05 離れ)に二つ。TW_Higashi_Hokuto_8_1 の端は TW_Kado_Hokuto_0_0 の線まで縮めた後 ③⛔。
   **原因**: PlaceNozuraNet の Links は端どうしが TOL 0.05 以内でないと継がない ⇒ 0.06 離れた入隅も、0.05 超の出隅も「相手の居ない端」として ② が各々に隅を立てた。
   **対処**: EdoBuild.NozuraEndRule.partnerFirst(指図 nozuraEndRule 追記 2026-10-14a の「端から x 以内」)── 継がれていない端どうしが x 以内なら二本の線の交点へ寄せて継ぐ
   (出隅 = 鎖の一つの隅・入隅 = 相手の線の上に在る側を可動側 NozuraSeg.concaveRole)。
3. 角の桝 D_Corner_Masu の腕 A(局所 −X)の向きは据える向きで決まる ⇒ 据える前に向きを解き、口ごとに要る敷居を出して焼いた版(EdoAssets.Own.DoiMasuKadoVersions)から差の和で選ぶ。
**How to apply:** 欄の上書きの後に「黙って」消えた納めは、まず読む側の正規表現の頭の語を疑う。網の端の ② が同じ角に二つ立ったら端どうしの離れを測る。
