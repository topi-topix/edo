---
name: neribei-nk-koshi-choice-r124
description: 岡部 第124巡 ── 練塀の腰なしの駒(_NK)への入れ替え。外面の線は元から下見板の表で寄せていた(腰は 0.137 外へ出ていた)・腰の出 0.14 の決め打ちが Stage3d に 3 箇所・KadoGauge の faceDepth は 0.296→0.212
metadata:
  type: project
---
2026-10-13 EDO-0502 第124巡(const.heiLine.koshi・EdoBuild.StoneBaseUnder・EdoAssets.Own.Nk)。

1. **NeribeiLineRun の外面は元から下見板の表(NeribeiWallParts に腰の群 "ishigaki" は入っていない)** ⇒ 腰ありの駒は腰が線より 0.137 外へ出ていた。
   腰なしへ替えても外面の線 d は動かない(実測 shitami −1.050 のまま)。札の foot ±0.337→±0.206 で動くのは足の外の縁だけ。
2. 腰の出 0.14 は Stage3d の犬走りの面(PlaneBand の q1・qMax)と LowerSoilOnCrest の上限に決め打ちで入っていた ⇒ HeiFootOut(e)(据えた駒の足の帯の FaceOut − 線)へ。
   練塀の無い辺(長屋・門)は前の 0.14 を返す(天端の土の下げを長屋の下へ広げない)。
3. 腰なしの駒の群: ishigaki が無く、koguchi は ±0.212 で y0 から・底の板 soko(±0.206)。足の測り・棟止めの奥行は ishigaki → soko(FootEnds・SeatHeiLineKado に soko を足した)。
   棟止めの実寸(TomeGauge)も腰あり/なしで別に測る。
4. KadoGauge の faceDepth は腰あり 0.296・腰なし 0.212 ⇒ KadoArms の腕の選びが変わり得る(第124巡は全 25 基とも焼いた版が在った)。
5. Stage2 の内面の帯の始まりが 1.552 → 1.462(内の足の縁が 0.09 外へ)── 内の帯の地面も動く。
6. **腰の有無を足の真下の石で決めると外れる**: Stage2 の時は台の天端に土が載っていて(3d が下げる)「石 > 地表」で N_Hei_32_0 を見落とし、細い台(S_Hei_02 倍率 0.25)は
   塀の外面の 0.4〜0.6 前で止まり足は台の裏の土 ⇒ 区画の線から塀の内面までの帯で「石の天端が座 ±0.15」を数える(地表と比べない)。
7. **長い execute_code の最中に compile_wait.py を打つと refresh が積まれ、流し終わった直後に domain reload が走る** ⇒ _heiLineD・run.lineS が消え、
   同じ巡の計測ができず 90 分の流しをやり直した。流しの間は read_console だけで待ち、計測は流しと同じ execute_code の末尾に入れる(try で包む)。
**How to apply:** 腰の有無は StoneBaseUnder(区画の線〜塀の内面の帯に石の天端が座 ±0.15)で区間・隅ごとに決まる。台を退けた区間は自動で腰ありへ戻る。
関連 [[kidan-crest-slope-r122]] [[heiline-tenba-spec-r121]]
