---
name: steep-grade-piece-only-low-h
description: 勾配の駒を焼いた見付の帯と、据える駒の見付が食い違うと最も近い勾配へ黙って落ちる(岡部 袖の 049f は H4800 で G−660 が無く G−450)・折れ 60° 以上の鈍い隅は Kado90 決め打ちだった
metadata:
  type: project
---

2026-10-09 EDO-0502 第66巡(岡部 TW_Kado_Sode)。

1. 指図は「049f を G−660 の駒1つで 21.0→19.80 へ」。部材方は G−495/−660 を **H1800〜2400 だけ**焼いたが、049f は前の地表が
   約 15.5 なので needH が **H4800** を選ぶ ⇒ SannoNozura の最も近い勾配は H4800 の −0.45 になり、天端の端が 0.24 外れる(⚠ だけで建つ)。
   048f も踊り場を 19.80 へ上げたら H4800 になった。
   **How to apply:** 勾配の駒を頼む/取り込むときは、据える駒の**見付**を先に測り(Stage2b のログの駒名 `_H####_G`)、その見付で焼いてあるかを見る。
2. EdoBuildNozura の隅は `turn < 60°` だけが折れの駒(kadoDeg)、それ以上は Kado90 決め打ちだった ⇒ 90° から 5° を超えて外れる隅は、焼いた駒が
   在れば kadoDeg を据えるようにした(Kado103 が kado11 に据わった)。焼いていない Kado100・Kado79 は ⚠ を刷って Kado90 のまま。

関連: [[kado-short-arm-and-foot-groove]] [[nozura-dan-piece-fixed-height]]
