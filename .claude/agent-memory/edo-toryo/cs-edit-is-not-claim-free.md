---
name: cs-edit-is-not-claim-free
description: .cs を1行保存するだけで他人の Unity が再コンパイル+ドメイン再読み込みに入る。claim が取れない巡は「コードだけ先に書く」も禁。用意は scratchpad へ
metadata:
  type: feedback
---

**Unity の claim が取れない巡は、`Assets/**/*.cs` を保存してもいけない。** 用意した編集は
scratchpad の指示書に置き、claim が空いてから当てる。

**Why:** `cs_check.sh` は claim が要らない(`.claude/rules/unity.md` に明記)ので、
「コンパイルの検めだけなら他人を巻き込まない」と読みがちだが、**検めるより手前の
「ファイルを保存する」が既に共有資源を消費する**。走っている Unity は保存を自分で拾って
再取り込み→再コンパイル→ドメイン再読み込みに入り、相手の MCP bridge が約2分落ちる
([[pitfall-bridge-drops-after-domain-reload]])。赤坂を開いた相手なら1行で 34 秒、
実行中の `execute_code`(検証レンダなど)はその場で落ちる。つまり claim の排他は
「MCP を叩くか」ではなく「Unity が見ているファイルを書くか」で決まる。
2026-09-22・EDO-0323 の庭の直し4件で踏んだ(別セッションが検証レンダ中だった)。

**How to apply:**
- `EDO_SESSION_ID=<短縮ID> python3 Tools/Session/edo_session.py check-unity` が ⛔ を返したら、
  **Unity を叩かないだけでなく `Assets/` 配下を1文字も書かない。** `docs/` や scratchpad は可。
- 代わりに **OLD/NEW を対で並べた指示書**を scratchpad へ書いて返す。次の巡は
  「当てる→`cs_check.sh`→建てる」だけになり、ファイルを読み直す費用が消える。
- ⛔ 待ち行列に並んだまま黙って待たない。1番目に並べた事を報告に書いて呼び出し元へ返す
  (予約は 15 分で切れるので、使う側が居ないと無駄に塞ぐ)。
- 関連: [[pitfall-unity-claim-not-verified]](claim が付いたかの確かめ方)
