---
name: front-axis-differs-per-part
description: 「正面がローカルのどの軸か」は同じ邸の中でも部材ごとに違う(山王 社殿5棟=+X / 堂宇10棟=+Z)。yaw 0 で揃えると後から足した部材だけ 90° ずれる
metadata:
  type: project
---

**症状**: 山王社の `Stage6_Shaden` は「部材のローカル **+X = 東 = 正面**」を前提に、`munes` の矩形の中心へ
**yaw 0 のまま**据えていた(5棟はそれで正しい)。2026-09-22 に焼けた堂宇10棟(`Sanno_Do_*` / `SannoInari` /
`Shoro` / `Koro` / `SannoUmaya` / `SannoKura` / 末社の小鳥居)は部材方の申告が**全点 +Z が正面**なので、
同じ yaw 0 で置くと**その10棟だけ 90° 北を向く**。

**根**: 「正面はローカルのどの軸か」は**部材の性質**で、邸の性質ではない。実装が「この邸は +X」と
決め打ちできる場面は一度も無い。⛔ 既存が +X で揃っているのは偶然(同じ生成器で焼いた5棟だから)。

**対処**(2026-09-22・EDO-0261 ③): 向きは**二つの宣言の引き算**にした。
① 図が決める `munes[].front` / `torii[].front` / `gates[].front`(方位の語)と
② 部材が決める `axis.front`(`+X` / `+Z` …)。yaw = ①の方位 − ②のローカル方位 =
`EdoBuild.FaceYaw`(`Assets/Edo/Scripts/Editor/EdoBuildMuki.cs`。`DirDeg` / `LocalAxisDeg` / `DirVec` も同じ本)。
⛔ どちらかが欠けたら yaw を出さない(`false`)— 呼び側は **yaw 0 のまま据えて「向きが未宣言」と刷る**
(= 宣言が無い間はこれまでと同じ姿。0 を合格と読ませない)。同じ引き算が門の側にもある
(`Tools/Sashizu/bake_impl.py::gate_yaw`)ので、**式は二つ持たない**。

**⚠ 門にも同じ穴が二つあった**(2026-09-22・EDO-0398・勝手口の木戸を足した巡):
① `Stage5_MonTorii` が `if (front != "+X")` で**部材の正面を決め打ちして弾いて**いた(既存3門が全部 +X だったから
気付かない)。木戸は `+Z` なので**据えずに差し戻す**側へ落ちる。⇒ `EdoBuild.FaceYaw` で焼いた yaw を**検算**して据える
(郭の辺の傾きを載せた門 = `gates[].frame` を持つ楼門だけ差を許す)。
② 突き合わせ `EdoSannoSashizuCheck.GATE_NAME` が**ビルダーと別の名簿**で、新しい門の行が無く
「名簿にも載っていない」= **未測定**が1件立つ(社殿・鳥居で先に踏んだのと同じ)。⇒ `EdoSannoShaRebuild.GateNameOf`
を public にして `Lookup(名簿, 名) ?? GateNameOf(名)` に寄せた。**部材を1点足す巡は、ビルダーと検査の両方の物差しを見る。**

**⚠ 宣言先がすぐに見つからないことがある**: 門は `bom[<gates[].bom>].axis.front` で引けるが、山王の堂宇の
`bom` の行は「鐘楼・鼓楼・附属堂(其一・其五・其八ほか)・観音堂・薬師堂・庚申堂」と**束ねて**立っていて
棟の名で引けない。⇒ `FrontAxisOf` は ①行自身の `axis.front` → ②`bom[].axis.front` の順に見る。
束ねた行しか無い部材は**行ごとの `axis.front`** を指図方へ頼むこと。
