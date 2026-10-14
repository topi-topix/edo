---
name: r132-ramp-foot-pits-and-step-band
description: 岡部 第132巡 ── 切坂の足の窪みは SinkGroundUnderParts が両脇の石垣の埋まった法を掘った物(前の地表の歩きが全部駒の中で止めが無かった)・坂の水の検めは外形の中を外して窪みを見逃していた・造成QA の段の一升・欄の上書きの後は get_IMPL が例外
metadata:
  type: project
---
2026-10-14 EDO-0502 第132巡。

1. **症状**: R_KiriZaka の足(両脇の野面の石垣の足元)に深さ 1.4〜1.9 の窪み(写真 r131_08)。
   **原因**: Stage3d の SinkGroundUnderParts。節点の真上の光線が両脇・隅の駒の**埋まった法の根入れ**(地表より下)に当たり「面 −0.05」へ掘る。
   止めの「見え面の前の地表」は法線の向きへ 4m 歩いて駒の外の最初の節点を探すが、石垣が向き合う坂の足と隅の駒では 4m 全部が駒の外形の中で見つからず、止めが無かった。
   **対処**: EdoBuild.SinkGroundUnderParts で、見つからなければ歩いた節点の今の高さの最低を前の地表に。さらに**上を向いた面**(法線の水平 < 0.25 ── 根入れの石の上の面 12.75〜13.10)は
   従前は止めを掛けずに掘っていた ⇒ まわり 3 升の駒の外の節点の最低より下げない・それも無く天端より 0.5 以上低い面ならまわりの今の高さの最低より下げない。
   試しは足の周りだけを前の巡の hmc_S3.bin から戻し、坂の路盤の下限(RampProfileAt を reflection)付きで SinkGroundUnderParts を呼んで RampWaterQA で見る(S3d を流さず 1 分)。
   ⚠ 坂の水の検め(RampWaterQA)は駒の外形の中を全部外していたので、この窪みを「窪みなし ⭕」と刷っていた ⇒ 駒の上向きの面が地表より上の点だけ外す(PartTops.RawTop)。
2. 造成QA の P22 の一升 +0.60 は辺22 s0.90 の帯の段(0.635)の脇。帯の記録の yAt を一点で引くと上の座の節点を下の座と比べる ⇒ FootBandReachRange(前後 0.25 の最小〜最大)で数える。
3. 指図の欄を上書きした直後は Reload でなく **DesignY / get_IMPL が「算出物が焼かれていない」例外**。食い違い0なら bake_impl --write([[impl-fingerprint-after-yat-overwrite]])。
4. 背の帯 N40_1 の「+0.049 ⛔(259 点)」の 259 は測った点の数(超えた点の数でない)。流し終えた地形では −0.001・上り 0 だった。
5. 段の欄の書式「擦り付けは 1/20」は「1/n で…擦り付け」の正規表現に掛からず、隣の棟の値を借りて ⚠ を出していた。
6. 欄の上書きの後は okabe_graded.bin も古い ⇒ 1本目の S1 が 1m で造成した(ログ 3 行目の ⚠ を流し始めてから気付いた・1時間の空振り)。**流す前に impl_okabe.py --graded-bin**([[graded-bin-stale-after-sashizu-commit]])。
**How to apply:** 法のある石垣が 4m 以内で向き合う所・隅の法尻に窪みが出たら、まず駒の下の下げを疑う。検めは「外形の中」でなく「面が地表より上」で外す。
関連 [[r131-ground-nan-crash-and-camera-inside-nagaya]] [[wall-foot-ridge-from-nodes-under-hull]]
