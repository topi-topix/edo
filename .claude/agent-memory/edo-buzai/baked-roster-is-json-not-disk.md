---
name: baked-roster-is-json-not-disk
description: 指図の「焼けているか」検査は json の baked 名簿だけを読む。FBX を焼いても ⛔ は消えず、名簿を足すと sha が変わって --export-impl の焼き直しが要る
metadata:
  type: project
---

`Tools/Sashizu/build_sanno_sashizu.py` の検査「透塀のスパン部材が焼けているか」
(`sukibei_span_check`)は `bom[…].baked` の**名簿だけ**を突き合わせる。
`Assets/Edo/Models/` を走査しない。

**Why:** 名簿は指図(人が書く正典)の一部で、部材方はそれを触れない(指図方の役)。
だから部材方が 25 点焼き切っても、生成器を回した限りでは ⛔ は 1 件のまま残る。
「焼いたのに ⛔ が消えない」を実装の失敗と読み違えない。

**How to apply:**
- 焼いたら**名簿へ加えるべき名前の一覧**を報告に入れて、指図方へ渡す。自分で json を書かない。
- ⛔ が 0 になるかを自分で確かめたいときは、json を scratchpad へ**複製**して名簿を足し、
  `build_sanno_sashizu` を import して `B.JSON` / `B.OUT` を複製側へ差し替えて `B.main()` を回す
  (docs/ の本物を書き換えない)。⚠ 複製で回すと「実装が読む算出物の鮮度」が sha 不一致で ⛔ 1 件出る
  — これは複製の副作用で、本物の json では鳴らない。
- ⭐ 指図方が名簿を足すと json のバイト列が変わるので、**そのあと `--export-impl` を回し直さないと**
  同じ鮮度検査が本物でも ⛔ になる。引き継ぎに必ず書く。
- ⚠ 検査が生の json をそのまま食うとは限らない。`sukibei_span_check(d, None)` を素の
  `json.load` の `d` で呼ぶと、`main()` が前処理で入れる派生値が無いため**別の割り付けが出る**
  (2026-09-18 に 2568/2651 が 2623 に化けて混乱した)。割り付けは必ず生成器の通し実行の
  〔記録〕から読む。
