# Memory Index — edo-toryo(棟梁)

実装中に踏んだ非自明な罠だけ。手順はスキル、不変則は CLAUDE.md、指図は docs/Sashizu が正典。

## Unity MCP の罠

- [書き戻しは必ずタイムアウトする](pitfall-writeback-mcp-timeout.md) — 大きい邸のプレハブ。⛔再送せず mtime で判定
- [domain reload 後に bridge が消える](pitfall-bridge-drops-after-domain-reload.md) — 約2分。status ファイルと Logs/Editor.log で見る

- [古い port 登録で「instances なし」が一回おき](pitfall-bridge-drops-after-domain-reload.md) — 6400→6401 退避 + 別プロジェクトの残骸。待たずに再送
- [start --unity が通っても claim が付いていないことがある](pitfall-unity-claim-not-verified.md) — status で「資源: unity」を見るまで MCP を叩かない

## 部材の据え方

- [測って置く。事後に寄せる関数を持たない](measure-dont-nudge.md) — 帯の頂点では門柱が消えて偽の穴。閉じは三角形で測る
- [番所はピボットが奥行の芯・部材は片手](bansho-pivot-and-protrude.md) — protrude は躯体の外面の越える量。対に振らないと袖塀へ 0.22 めり込む

- [帯割り屋根は床へ据える](banded-roof-sits-at-floor.md) — FBX が軒高を焼き込み済み。寄せ直すと 0.71m 浮く。⚠ 渡廊下と当たる
- [園路の敷きはメッシュ。スプラット不可](gravel-band-mesh-not-splat.md) — alphamap 4.0 m/px。巻きは上から見て時計回り

- [透塀の隅は kadoFrom で引き、run の群に入れない](pitfall-sanno-sukibei-kado.md) — kind は null。群に混ぜると偽の 0.29m 芯ずれ 8 本

- [山王の社叢は「数え方」が入れ物を決める](sanno-shaso-counting-and-bake-gap.md) — 低木はGameObject・名指しは群の外・旧Keidairinは群ごと退避。焼き出し7点は `{size}` のまま

## 測り方・関門

- [当たりは棟の外形線の上で測らない](notch-seat-has-80mm-plate-under.md) — 線上は内と外を拾い分ける。廊下の側へ張り出す三角形だけに絞る
- [実メッシュの当たりは紙より 0.08m 低い](mesh-atari-is-lower-than-paper.md) — 葺き厚と垂れ。5点の中央値で測る
- [C#の検図関門が kansei を見ていなかった](csharp-review-gate-ignored-kansei.md) — python が⭕でも止まる。直した

## 検査の読み方

- [CheckScene は矩形の芯で測る](checkscene-center-vs-seat.md) — `seat` で据えた部材は永久に鳴る。⛔芯へ動かして0件にしない
