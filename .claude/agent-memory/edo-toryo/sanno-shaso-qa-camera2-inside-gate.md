---
name: sanno-shaso-qa-camera2-inside-gate
description: 山王社叢 QA のカメラ②(地盤 -448,721・目の高さ)は赤坂では宝蔵院の表門の中に入る。作業場では隣が載らないので写る
metadata:
  type: project
---

症状: 赤坂で UserData/QA_Sanno_Shaso の ② を撮ると真っ暗な門の内側が写る(作業場で撮った前回とは別物)。
原因: 地点 (-448, 11.32, 721) が Edo_SannoBo_Hozoin/Omotemon と Edo_Typo_sannojubo_parcels_2/Kakoi の中。
対処: 撮るあいだだけ、その地点を含む renderer と Hozoin/Omotemon の renderer(計53)を enabled=false にし、撮ったら戻す。
カメラは動かさない。2026-09-23 EDO-0401 の before/after はこれで揃えた。

**How to apply:** ② を撮り直すときは同じ隠し方をする。カメラを動かすなら前後とも撮り直す。

追記 2026-09-23 EDO-0409: 十坊の敷地の板塀が建て直され、目の点が `Edo_Typo_sannojubo_parcels_2/Kakoi/ita+ikegaki_3_4f`・`_4b`
(笠木・垂木)の外接箱の**すぐ下 0.05m**に来た。bounds.Contains では拾えず、塀の屋根と柱が手前に写る。
この2駒を名指しで足して隠す(門 26 + 箱が点を含む物 + 板塀 20 = 計 52)。写り込みの正体は近平面 0.1m より先の当たりで光線を当てて引く。
