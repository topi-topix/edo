---
name: akasaka-open-resent-six-times
description: 応答の待ち(約30秒)を超える execute_code は MCP サーバが5回再送して6回走る。赤坂・作業場を開く・重い計測で踏んだ
metadata:
  type: project
---

症状: 2026-09-23 作業場から `EditorSceneManager.OpenScene(Akasaka)` を execute_code で投げたらタイムアウト。
Logs/Editor.log に `Opening scene 'Akasaka.unity'` が6回、1回 90〜205 秒(M1・8GB で Integration が重い)。
原因: mcpforunityserver の send_command は既定で max(max_retries,5) 回まで再送する。1回の開きが応答の待ちを超えるので毎回再送される。
対処: 開く呼び出しは1回きり。タイムアウトしたら何も投げずに Editor.log の "Opening scene" の回数を数え、6回目の
"Total Operation Time" と CPU <20% を待つ。⚠ 2026-09-23 EDO-0409: `Edo/普請/赤坂へ戻す` の execute_menu_item **も**タイムアウトして再送され、同じく6回開いた
(1回目 404 秒・2〜6回目は各 40 秒前後・計約9分)。menu でも逃げられない。開く手は1回投げたら Logs/Editor.log の
"Opening scene" と "Loaded scene" の数が揃い、CPU が数%に落ちるまで何も投げない。

追記(2026-09-23 EDO-0415 仕上げ): 赤坂に限らない。**応答の待ち(約30秒)を超える execute_code はどれも6回走る** —
作業場を開く `EdoKoba.Open`(1回目 33秒・残り5回は各6秒)と、3cm 格子の平面の抜けの総当たり(結果の行が 6 回追記された)で踏んだ。
冪等な呼び出しなら害は時間だけ。重い計測は区間に割るか外接矩形で先に弾いて 30 秒以内に収め、結果はファイルへ書く(再送を数えられる)。

追記 2026-09-23 EDO-0409(植え直し2回目): `EdoKoba.BackToAkasaka` は今回1回しか開かなかった(開いている間に資産の読み込み 33 秒+
domain reload が挟まり、bridge が切れて再送が届かなかった)。回数は決め打ちせず、"Opening scene" と "Loaded scene" の数が揃い
CPU が落ちるのを待つ。直後の1回目は「instances なし」が出るが、待たずに再送すれば通る。作業場を開く方は今回も6回。

追記 2026-09-26 EDO-0437: 駒どうしのめり込みを総当たり(頂点ごとに全三角形へ3本の光線+最近点)で 11 対まとめて測る execute_code が
30 秒を超え、6 回走って Unity が 25 分以上ふさがった(compile_wait の refresh も断られ続ける)。**野面の駒(三角形 9,000 前後)の対は
1 回に 1〜2 対まで**。重なりの外接箱の外の三角形を先に捨ててから光線を打つ。
