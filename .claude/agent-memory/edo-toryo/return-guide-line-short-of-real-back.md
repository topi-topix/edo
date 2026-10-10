---
name: return-guide-line-short-of-real-back
description: 指図の輪郭の返しの線は長屋の奥行の目安で引くので、実の背(浅い)から一間の帯の手前で線が止まり、ReturnAlongBack が「返し要らない」と黙って退いた ── 線の終わりを帯の縁まで延ばす枝を足した
metadata:
  type: project
---
2026-10-10 EDO-0502 第103巡(岡部 TW_Kado_Hokuto × N39_1)。

- 症状: 普請方が輪郭(Kadonouchi.poly)を「区画の線から inubashiri+nagayaD+一間 = 6.47」で引き直した巡から、算出物の線の終わりが v=6.46 で止まり、
  実の背 3.65 + 一間 = 5.47 の帯へ入らない ⇒ `ReturnAlongBack` が null(「線が背から 1.82m の帯へ入らない ── 返し要らない」)。返しも溝も建たず、N39_1 の背に 2.5m の土の崖(急な土 153)。
- 対処: `EdoBuild.ReturnAlongBack` に枝 ── 帯と交わらず、最後の区間が背へ向かい(向き·yard < −0.3)、延ばしが一間以内・背の端の内なら、線の終わりを帯の縁まで延ばして返す。
  食い違いの量(1.01m)を note に名乗る。平らは FlatFaces に「KaeshiSe_<棟>」(返しの線から庭へ一間+1 を hi の面の高さ)を足し、輪郭の目安との間を埋める。急な土 153 → 41。
- 読み方: ログの「返し要らない」は**線の側の欠陥**のことがある。指図の輪郭が目安【柔】なら実メッシュの側へ寄せる(指図の数字は書き換えない)。

How to apply: 輪郭・線が「長屋の背から」の目安で引かれた欄は、棟の実の奥行(FaceOut)と目安の差を先に刷る。関連: [[gate-host-vs-koshi-host-split]] [[ramp-side-walls-unresolved-by-bake]]
