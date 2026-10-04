---
name: nagayamon-bansho-side-and-gate-post
description: 長屋門の片番所は既定で Unity −X(街路から見て右)に付く・--bansho-ux +1 で左へ・中心固定の口の縁の窓の欠片は門柱で隠す・潜戸の足元は z_base_ref(2026-10-04 土井 EDO-0533)
metadata:
  type: project
---
- build_nagaya_omote の片番所(cen[0])は回した後 Blender +X = **Unity 局所 −X = 街路から見て右**。旧注「向かって左 = ローカル +X」は Blender 局所の言い方で、土井の表門が逆に焼けていた。街路から見て左 = Unity +X(見る人は −Z を向く)。`--bansho-ux +1` を足した。確かめは FBX を (−x,z,−y) で読み、出格子(z 0.3〜0.6・y<3.5)の x の符号。
- 扉の中心が躯体の中心に固定だと口の縁が1階下段の窓に 0.12〜0.14 入って黒い筋が残る ⇒ `--gate-post 0.24`(門柱)で隠す。口を動かせないときの手。
- 潜戸も敷居(土台の底 − drop)まで下げる(段では通れない・施主側の指示)。札は passageKuguri。
関連 [[nagaya-mon-short-pier-window-sliver]] [[nagaya-body-length-and-goten-root-offset]]
