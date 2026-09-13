# 道具改め — 所見と処置の案(2026-09-13・0 件・承認済 6 件は畳んだ)

処置の列を直してから `python3 Tools/Session/config_doctor.py --apply <このファイル>`。語彙は同スクリプトの docstring。⛔ は keep で黙らせられない。

| 鍵 | 重さ | 場所 | 所見 | 処置 |
|---|---|---|---|---|

内訳: 

## 関門の自己検査

⭕ Tools/Sashizu/decision_gate.py
⚠ Tools/Sashizu/review_gate.py に --selftest が無い
⭕ Tools/Sashizu/wiring_gate.py
⭕ Tools/Session/config_doctor.py

## 挨拶の予算

⭕ 挨拶 7.3 秒 / 19 行(目安 8 秒 / 25 行)

## 月次の手作業(道具では測れない物)

- メモリ: `Skill(anthropic-skills:consolidate-memory)` で重複・古い事実・索引を整理する
- スキル: `Skill(anthropic-skills:skill-creator)` で edo 各スキルの description の発火精度と SKILL.md の長さを見直す
- 利用実績(第2期・未実装): 30 日呼ばれない役・スキル、60 日読まれない参照を transcript から挙げる
