---
name: return-lost-when-sashizu-text-format-changes
description: 指図の文の欄を正規表現で読む所は、欄の書式が変わると「読めない」で Stage ごと黙って退く ── 岡部の腰石垣の返しが returnEnd の書き換え(土羽→見切り石)で丸ごと消えた
metadata:
  type: project
---
2026-10-06 EDO-0502 第32巡。

1. TW_Minami_Koshi の返し(#ret0/#ret1)が第30巡から消え、石垣の先が縦の土の崖になっていた。原因は NozuraEndRule ではなく、
   同じ巡の指図の上書き 8a332b02 で returnEnd が「土羽で止める・法 1:1.5」→「見切り石で止める」に変わり、SodeBenches の
   `rx(enT, "法 1:x")` が NaN ⇒ miss ⇒ 返しの割りをまるごと飛ばした。ログには `★ … 返し: 指図から読めない(returnEnd の土羽の法)` の1行だけ。
   **2書式を受ける**(見切り石なら法は要らない)で直した。
2. 主の線を妻の線まで延ばす量 0.31m を節点として足すと、その区間が < 0.5 で駒を据えず主と返しの間が切れる ⇒ 一直線の延長は端の節点を動かす。
3. 重ねて埋める run(RunsByCrestGap)の noAbut を両端に立てると、返しの終わり(見切り石を立てる端)まで納めから外れる ⇒ 上手の端だけ。
   上の run の端が下の run の走りの中に入る端は納めない(見切り石が返しの中ほどに立った)。

**How to apply:** 欄の上書きの直後の巡は、Stage のログの `★ … 指図から読めない` を必ず grep する。消えた物は「型が消した」より先に「欄が読めなかった」を疑う。
関連: [[nozura-end-rule-blocked-by-back-soil]] [[short-return-tie-and-sode-extent]] [[impl-fingerprint-after-yat-overwrite]]
