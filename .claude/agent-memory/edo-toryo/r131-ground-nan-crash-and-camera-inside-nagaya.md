---
name: r131-ground-nan-crash-and-camera-inside-nagaya
description: 岡部 第131巡 ── Ground に NaN で Unity が落ちる・黒い L 字はカメラが長屋の中・hei2 の浮きは小口の頂点と隣の段・皮の退役で nozuraCrestCover が地形へ効いていなかった・造成QA は書いた高さの記録で測る・隙間は建てた後は無い
metadata:
  type: project
---
2026-10-14 EDO-0502 第131巡。

1. **症状**: 測りの execute_code で Unity が native crash(Heightmap::GetInterpolatedHeight ← Terrain.SampleHeight ← EdoBuild.Ground)。
   **原因**: FootLinesOn の辺 8 は nPts 0 で dIn = −3.4e38(float.MinValue)── その線の点を Ground へ渡した。SampleHeight は巨大・NaN の座標で落ちる。
   **対処**: EdoBuild.Ground と GroundProbe.At に NaN・無限の門を足した(NaN を返す)。測る側も FootLine は nPts > 0 を見てから使う。落ちたら open -a で起こし直し、compile_wait を一度。
2. 普請検査の写真の「長屋 N39_1 の前に浮く黒い細い L 字 7 本」は**カメラが N39_1 の躯体の中**(前の面の 2.5m 後ろ)で、外向きの片面が裏から抜けて窓の格子だけが見えていた。
   N39_1 を消すと消え、外から撮ると窓は正しい。⇒ 欠陥でない。写真の謎の物は、まずカメラの位置が駒の外形の中かを測る(光線で最初に当たる駒と距離)。
3. hei2(塀の足の頂点の真下の石)の浮き: 0.909/0.648 は隣の段の塀の躯体が閉じる点(EdoBuild.HeiFootOnStoneReport で別に数える)・0.202 N_Hei_26_1_4 は**小口の面の頂点**(升の最低だが隣の升に 0.31 低い足)── 3×3 升の最低より 0.05 高い頂点は足でない。
4. 坂の水の検め(RampWaterQA)は、坂の足の前・脇の石垣の駒の下の下げた地面を拾うと偽の窪み 1.23・横断 0.66 が出る ⇒ 近くの Dan/Ishigaki/Kakoi の躯体の外形の中は測らない。
5. **皮をやめた(第110巡)後、const.nozuraCrestCover(野面の天端の裏石の帯の土)と「背の側で駒の底より低い節点を底 +0.05 へ」は Stage3b の皮の設計にだけ残り地形へ効いていなかった**
   ⇒ TW_Higashi_Se の背で裏石の尻が東の平場の上 0.46 に浮いて見えた(GroundQA の C「小口」45 件の正体)。EdoBuild.CrestCoverToTerrain で地形へ写した。
   ⚠ ①(帯を天端 +0.03)をそのまま地形へ効かせると隅・端の駒の背の帯が低い庭・路地へ回り込み 4.68m 盛る ⇒ ② だけ・駒の外形の中だけ(bandToo=false)。① は皮の PIN・範囲の篩を写すまで止める。
6. GradeQA が小段・溝の帯を「式の引き直し」で枠にすると、静的な一覧(_sideEndBenches)が reload で消え・頭打ちの盛りや 0.30 の帯を読めない ⇒ **書いた節点の高さを記録(BandRecPath bench/s3d)して記録で測る**。
7. 指図の「塀と棟の妻の隙間 0.6〜0.9」は造成の面(graded.bin)の読み。建てた後は N12_0 の躯体の足と S_Hei_08 の足の内の縁が辺11 の 3m で接し(離れ 0〜0.04)、隙間は P11 の端の 0.14 だけ。
   帯(塀の内の足元の帯)が地面を 19.0〜19.1 に上げるので、普請方の見込み(18.6〜18.85)より 0.3〜0.5 高い ── 普請方の数は帯の後の地表で測り直してもらう。
**How to apply:** Ground を自作の線で引く測りは NaN の門を信じて良いが、FootLine.dIn の float.MinValue は自分で弾く。写真の謎はカメラ位置から。
関連 [[r130-grade-qa-frames-g0-hei-feet]] [[qa-misreads-stack-and-single-mesh-gate]]
