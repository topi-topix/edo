---
name: bench-end-slope-spills-and-3b-opposite-wall
description: 皮の「箱形の土の盛り」は部材でなく小段の裏込めの端の法が隣の袖の前へ回り込んだ物・一間の溝の尾根は graded の 1m 格子・皮の縁の点は 2m 地形に留められる
metadata:
  type: project
---

2026-10-05 EDO-0502 第25巡(岡部 門の内・腰石垣の溝)。

1. 門の内の袖の前の「箱」: 皮 17.50 の平らな台が地盤 16.50 の上に 1m。真上に駒は無い(RaycastAll で確かめた)。
   設計の地盤に足す BackBenchAt を点で引くと TW_Kado_Sode_0 の小段の端の法(1:bf・盛り上限で頭打ち)が 2.5m 先の
   別の袖の前まで回り込んでいた。⇒ BackBench.keepOut + EdoBuild.InFrontOfFace(他の run の見え面の前 3m へ盛らない)。
2. 溝の尾根: graded(1m 格子)が返しの見え面の前 1〜1.5m で溝の底 19.20 から 20.5〜20.9 へ一次で上がる。
   ⇒ FlatFaces に一間の溝(stripDrain)の面を足す。EndDecisions → SkinGround → FlatFaces が再入するので旗で止める。
3. 返しの末端の背の角の隙 0.35: 皮の縁の行(z 948.07)は同じ xz の頂点が二つ(縁の点は 2m 地形に留める PIN)。
   小段の盛りは 2m 格子の地形に描けない(地形 19.88・式 20.32)。穴の升を小段の盛りまで広げる話(未着手)。

4. 直した後も残る土の台・尾根(門の内 17.0〜17.1・西の返しの前 19.8〜20.5)は**地形の残り**: BackBenchWrite は盛るだけで
   前の巡の盛りを下げない。皮の穴の外の升は地形(2m)が描く ⇒ 描かれた地表 = 地形の値。造成の流し直しか、盛りを設計面から書き直す型が要る。

**How to apply:** 皮に説明のつかない土の台・尾根が出たら、駒を疑う前に (a) 真上の駒を RaycastAll で数え (b) SodeBenches の各 BackBenchAt と
DesignY をその点で刷る。岡部 2b+3b は約 8 分。
関連: [[castle-batter-no-up-tris-skips-3b]] [[wall-toe-mound-is-grid-not-grading]] [[overlap-run-abuts-to-zero]]
