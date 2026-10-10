---
name: nagayamon-bansho-beside-gate
description: 番所が口に接する門長屋は --bansho-mon(口の両脇の窓へ出格子)・向きで gc が割れるので mon<gc> と mon<len−gc> の両方の _kutai を焼く(2026-10-10 岡部 表門 B EDO-0502)
metadata:
  type: project
---
- `--bansho 2` は両端の間に付く。割りが「部屋・番所・門口・番所」なら `--bansho-mon` を足す(口に掛からない窓のうち口の両側で一番近い窓)。8間 14.544 では窓の芯が口の脇の 1.5間の帯に入った。
- PlaceOmoteNagaya は欄の版(mon10)を KutaiOf で先に引き、据えた向き sSign で gc = len/2 − sSign·(s − sMid) を出して引き直す ⇒ mon10_2f_kutai と mon4.54_2f_kutai の両方+素の mon10_2f を焼いた。
- zsh では `$B` に入れたコマンドが割れず黙って何もしない ⇒ 複数焼きは bash の .sh に書く([[machiya-small-shops-hira-and-zsh-quoting]])。

**How to apply:** 門長屋の新造は口の芯を両端から数えた2版を焼く。口の向きは札の passage の x の符号で確かめる。関連 [[nagayamon-bansho-side-and-gate-post]] [[nagaya-body-length-and-goten-root-offset]]
