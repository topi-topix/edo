---
name: inner-ditch-and-foot-fill-r125
description: 岡部 第125巡 ── 塀の内の溝の外の縁は地際の板まで(型A ±0.67・段落ち型H ±1.0)・FillUnderFoot の足を 0.15 の升で読むと隅の入隅の留め(下端 1.73)を足と読み土の柱・台の裏の縁の下の節点を触らないと足の内の縁が浮く・指図のコミットで S1 が指紋で止まる
metadata:
  type: project
---
2026-10-13 EDO-0502 第125巡(EdoBuild.DitchCoreOff・FillUnderFoot の FOOT_R と capUnderFoot・PlaceMinamiHei)。

1. **溝の駒の外の縁は MizoPieceOf の |x|(地際の板を含む)** ── 型A_Ago ±0.67・段落ち DoiDanOchi ±1.00・桝 G0 ±0.52。芯を「内面 +0.40」で引くと
   板が足の内の縁に 0.27〜0.96 掛かった。innerDitch(足の内の縁 +0.05【硬】)で main・west 内面 +1.05・yuka +0.72(床が 0.65 / 0.32 狭まる)。
   尻の型H(tail)の終わりの床の溝の頭も本線の離れで引く(+0.72 で引くと tail の板が 0.26 掛かった)。
2. **土の柱(北の段の継ぎ目・隅の近く 線から 1.7・+2.2)の正体は FillUnderFoot の足の読み違い**: 足 = 半径 0.15 の升の最下点 + 0.05 ⇒ 一枚物の隅の入隅の留め
   (hashira2・hei の下端 1.73)だけの升を足と読み、その下の節点を座 +1.8〜2.2 へ上げた。半径 0.45(壁厚 0.41 より広い)+ 勾配の許し 0.13×0.45 で 52 節点 → 4(最大 +0.09)。
3. 足の内の縁(1.46)の 0.2〜0.48 の浮き(Kado_P7・P10・S_Hei_08・NW_Hei_1_3・P35)は、台の石垣の裏の縁の下の節点を「石が足を支える」で触らず、一升の双一次が落ちた物
   ⇒ capUnderFoot(石の天端 −0.02 まで上げる・天端の前の縁 c +0.05 より前は触らない)。
4. 指図をコミットすると S1 が指紋で止まる(VerifyImplFingerprint)⇒ bake_impl okabe --write・impl_okabe --graded-bin・流しの頭で EdoOkabeYashikiBuilder.Reload()。
5. 流しは 107 分かかった(2b が 95 分)。read_console は 30 秒で戻るので待ちに使える。
**How to apply:** 塀の内に溝を沿わせる時は駒の半幅を MizoPieceOf で測って DitchCoreOff に渡す。土の柱を見たら RawTop より 0.05 高い土の節点を刷る(r125/chain_d.cs の末尾)。
関連 [[neribei-nk-koshi-choice-r124]] [[mizo-apron-terrain-rules]]
