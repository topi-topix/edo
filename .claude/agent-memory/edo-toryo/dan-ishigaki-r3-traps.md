---
name: dan-ishigaki-r3-traps
description: 岡部の段の土留め(EDO-0502 2026-10-03)で踏んだ3つ ── BedTopAt の光線は 8m まで・指図の文言の上書きで正規表現が黙って 0・語だけの指図の直しでも指紋で RunAll が止まる
metadata:
  type: project
---

1. **BedTopAt(p, beds, yTop) の光線は 8m まで。** 天端の垣を Place(y=0) した直後の駒の頭(≈1.5)から打つと天端(16〜21m)に届かず全部 NaN → 地表で据えて 1〜2m 埋まった(報告の「高低差 2.18m」)。⇒ yTop = 描かれた地表 + 6。
2. **指図の文言を普請奉行が上書きすると、文から数を読む正規表現が黙って 0 を返す。** R_UraZaka の toeFix.soft が「芯を X m 内へ」→「芯を内へ寄せる ── 上限 1.5m」になり shiftMax=0 で坂が均されなかった(★ 法尻 1.45)。⇒ 両方の書き方を読むよう GradeRamps を直した。流したら ★ の坂の行を必ず読む。
3. **語だけの指図の直し(ce7d8859)でも指紋が変わり RunAll が IMPL で例外。** `bake_impl.py okabe --write` は「0 件を上書き」で指紋だけ刷り直す ── 安全。

**Why:** どれも黙って別の物が建つ(埋まった垣・均されない坂)か、何も建たない。
**How to apply:** 光線で当たりを測る関数は射程を先に見る。文から数を読む欄は ★ の行で検める。関連 [[measure-dont-nudge]] [[bake-impl-carried-src]]
