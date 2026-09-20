---
name: pitfall-sanno-sukibei-kado
description: 山王の透塀の隅は joints[].kind ではなく kadoFrom で引く。隅を run の群に入れると突き合わせが偽の 0.29m 芯ずれを 8 本出す
metadata:
  type: project
---

山王権現社の透塀の隅(8箇所)で二つ続けて踏んだ。どちらも**据え間違いではなく引き方・名づけ**の罠。

## 1. 隅は `joints[].kadoFrom` で名指される(`kind` は null)

9f0dc530 / K059(2026-09-16)で隅の凹凸が**折れ線からの従属値**になり、`joints[].kind` が
`null` になった。⇒ `kind.IndexOf('隅')` で拾う実装は **隅が 0 箇所**になる(黙って 0 になるので
気づかない)。`kadoFrom = {in: <run>, out: <run>, name: <呼び名>}` の `in`/`out` で run を引く。
⚠ `kadoFrom.name` は一意ではない(「北の段」が 2 箇所)。

## 2. 隅を run の群・run 名で据えると突き合わせが壊れる

`EdoSannoSashizuCheck` は `RunPrefixOf` = `<run名>_<数字>f|b` で駒を run へ束ね、
**`segs` の外接矩形の芯**と比べる。隅を `Sukibei_E_900f` と名づけると run の矩形に混ざり、
隅部材が節点の外へ 0.49m 出るぶん芯が走り方向へ寄って **8 本ぜんぶ 0.29m ずれている**と出る。
駒は一つも動いていない。

⇒ 隅は `Kakoi/Sukibei_Kado` 群・名 `Kado_<in>_<out>`(末尾が f/b でないので `RunPrefixOf` が
null を返し、孤児にも数えられない)。そのうえで**突き合わせに隅の節を足す**
(節点そのものと比べる。部材の外形が X/Z とも [−0.477,+0.493] なので芯は節点から 0.011m ずれる)。

**Why:** 偽の 8 件を「据え直し」で消そうとすると、正しく据わっている駒を動かしてしまう。
**How to apply:** 突き合わせが「run ごとに同じ量」ずれていると言ったら、まず**何を一束にして
測っているか**を読む。→ [[checkscene-center-vs-seat]]
