#!/usr/bin/env bash
# PostToolUse hook (matcher: mcp__unityMCP__.*)
#
# edo-unity で Unity を触ったセッションの終わりに、得た知見を「正しい置き場所」へ
# 書き戻すことを促す。セッション1回だけ発火する(マーカーファイルでスロットル)。
#
# 設計意図:
#  - 旧版は unity-surface-authoring だけを名指しし、かつ「SKILL.md に追記せよ」と言っていた。
#    その結果 SKILL.md が時系列の追記で1100行に膨らみ、矛盾した記述が両論併記で残った。
#  - そこでこの版は (1) スキルを名指しせず用途で振り分け (2) 追記先を references/ に誘導
#    (3) メモリとの棲み分けを明示 (4) 矛盾チェックを義務づける。

sid="$(jq -r '.session_id // "nosess"' 2>/dev/null)"
marker="/tmp/claude_edo_capture_${sid}"
[ -f "$marker" ] && exit 0
touch "$marker" 2>/dev/null

read -r -d '' msg <<'EOF'
[edo-unity] このセッションで Unity を触りました。終わる前に、新しく分かったことを置き場所に書き戻してください。
判断できない/新しい知見が無いならスキップして構いません。

■ どこに書くか(同じ事実を両方に書かない — 二重管理はドリフトします)
  「別のシーンで作っても同じか?」で振り分ける。
  YES = 再利用できるやり方 → スキル。NO = このシーン固有の状態や決定 → メモリ。

■ スキル側(~/.claude/skills/ — 実体は Tools/Skills/ で版管理。symlink 越しに編集してよい)
  - 屋敷・街区の敷地の中身 → unity-buke-yashiki
  - 石垣・城壁・護岸のモジュール配置 → unity-modular-stonewall
  - 地表テクスチャ・植栽・スクショ等の plumbing → unity-surface-authoring
  追記は原則 references/ 配下の該当ファイルへ。SKILL.md 本体(原則と索引)に足すのは、
  ユーザーが明示的に是正した設計原則だけにしてください(本体は500行以内を保つ)。
  ★ 追記の前に SKILL.md の原則章と矛盾しないか必ず確認する。矛盾する古い記述は
    消すか撤回表へ移す — 両論併記のまま残さない(過去にこれで手戻りが出ています)。
  ★ 新しい主張には典拠を付ける。unity-buke-yashiki なら references/sources.md に
    書誌を足して本文から [ID] で参照し、文献でないもの(実測値・ユーザー指示)は
    確度 P / U と明示する。

■ メモリ側(projects/-Users-toshio-project-edo-unity/memory/)
  区画の正体・坪数・実装状態・未再現リスト・ユーザーの決定・環境の状態。
  1ファイル1事実、MEMORY.md に1行の索引を足す。手順そのものは書かない(スキルへ)。

■ 役の memory(棟梁 edo-toryo・部材方 edo-buzai は memory: project を持つ)
  実装中に踏んだ罠は役自身の memory へ 3 行。共有すべき物だけ完了報告に「pitfalls 候補」1 行(役の本文が正典)。
EOF

jq -n --arg m "$msg" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$m}}'
exit 0
