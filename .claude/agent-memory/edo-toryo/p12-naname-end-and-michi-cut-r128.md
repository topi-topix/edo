---
name: p12-naname-end-and-michi-cut-r128
description: 岡部 第128巡 ── P12 の塀の端を長屋の正面の線(実測)で斜めに切る駒・外の道の瘤の削り(michiP12)が自分の床 16.20 を割る・道側 2〜5m の台の見えの読みが削った道を拾い N12_0 を倍率 1.0 にする・線際の例外が隣の区画を下げる・札に文字列を入れると export が落ちる
metadata:
  type: project
---
2026-10-13 EDO-0502 第128巡(const.heiLine.cornerP12・grading.michiP12・施主裁定 案A)。

1. **指図の一様な坂は P12 で床を割る**: x −482 と −464 の横断を割合でつなぐと北の線は P12(x −470)で 16.08 ── limits「P12 の線上 16.20 以上【硬】」と 0.12 食い違う
   (指図の「P12 で 1.19」は 16.08 の方)。床を割ると S_Hei_08 の台の見え(線から 1.0 外で読む)が 3.19 ⇒ 倍率 0.75→1.0 で塀の一続き全部の c が変わる。
   ⇒ sashizu_lib.michi_p12_y が岡部の線から MICHI_P12_FLOOR_BAND 1.75(読みの 1.0 + 0.5 格子の 1.5 升)の内だけ床で止める。⚠ 報告に「線際だけ一様でない」。
2. **道に面する辺の台の見えは線から道側 2〜5m の最小**(roadRef)── 削った道の横断の低い側を拾い N12_0 を 3.38 と読んで倍率 1.0。⇒ impl_okabe.bake_base は
   michiP12 の中の点を線上(OUT 1.0)で読む。焼いた後に base の s を前の impl と diff する(N12_0・S_Hei_08 とも 0.75・見え 2.90 で止まった)。
3. MichiNarashiAt の「線の外 1 升なら帯の面で取る」例外は、岡部の線と隣の線の角(P12 = 樹下の線の端)で隣の区画の中の節点を下げる ⇒ EdoParcels.All の他の区画の中は NaN。
4. 道の面の欄が二つになった ⇒ C# の MichiNarashi は michiNarashi と michiP12 を同じ 0.5 格子へ重ねる(低い方)。Stage1 のログの「下げた升」は二つの合計。
5. **斜めの端の駒** EdoBuild.NeribeiNanameEnd: 長屋の正面は FaceStraight(足元 0.05〜1.0 の帯)で測り、外面の線との交点へ「足の外の縁の切り口の角」を据える。
   名は r.name + "_Naname"(⛔ "Kiri_" の頭は石垣の床へ組ごと据え直す群に入る・天端の線の駒の頭なら据えた所のまま)。P12: 交点 s 3.811・直角の端 2.956・前へ 0.000・足の入り 0.270。
6. build_neribei.py の --naname: V.export_fbx の札(spec)の入れ子に文字列を入れると round で TypeError(手は数で faceLonger 0/1)。cap() の lateral は単位でなくてよい(内積 / |lateral|²)。
7. ⛔ 試しの S1+S2 を流した後に本番の流しの頭で hm_pre.bin を採ると、道の削りが「前」に入って差が 0 に化けた ⇒ 区画の外の比べは前の巡の hm_pre(外は前の巡の後と同じ)で。
**How to apply:** 外の道を削る欄が来たら、まず台の見えの読み(線から何 m)の点が削る面のどこに落ちるかを刷り、倍率が変わらないことを impl の base の diff で見てから流す。
関連 [[face-front-columns-and-corner-slit-r126]] [[michi-narashi-outside-parcel]] [[graded-bin-stale-after-sashizu-commit]]

追記(同巡・EDO-0574): 類型の囲いの端が隣の区画の持つ辺に出会う所で、角の延ばし(CornerReach)と芯置きの壁体が隣へ入った(樹下 dobei_4_2・dobei_15_0 0.5、十坊9 kui_6_0 0.137)。
類型ビルダーの囲いの輪で、建てて EdoBuild.BodyOverLine(壁体・軒は数えない)で越えを測り、越えた分 / cos だけ端を引いて建て直す(最大 4 回)⇒ 0。
作業場の「(隣)」の類型を建て直すときは素の名で InstantiatePrefab してから EdoBuildQueue.Enqueue ── BuildParcel が「(隣)」も片付けた。
樹下の土塀の足の浮きを Body の底 − 地表で測ると布石の上の壁を「浮き」と読む(偽)── 布石の底で測る。
