#!/usr/bin/env bash
# PostToolUse hook (matcher: Bash)
#
# 「Unity に入れたら全部真っ白」を止める。
#
# Blender で FBX を出しただけでは終わっていない。Unity 側でマテリアルを remap しないと
# 材質が結合されず真っ白になり、EdoAssets.cs に登録しないとパスが散る。
#
# 判定はコマンド文字列でなく**挙動**で行う: Assets/Edo/Models 配下に新しい .fbx が
# 出現したかを見る。文字列照合(blender --background を含むか)は、ヒアドキュメント本文・
# echo・grep の引用に反応して誤発火するため採らない(2026-08-18 に2度踏んだ)。
#
# 同じ書き出しで何度も鳴らないよう、直近に観測した最新 mtime をマーカーに残して差分で発火する。

input="$(cat)"
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
[ -z "$cwd" ] && cwd="$PWD"

# ⛔ 2026-09-06: 他セッション(部材方)が出した FBX に、Blender を回していないセッションの
#   Bash 毎に鳴っていた(1セッションで3回)。「このセッションが blender を打ったことがある」を
#   セッション単位のマーカーで記録し、それが無ければ黙る。文字列照合は**有効化にだけ**使い、
#   発火の判定は従来どおり .fbx の出現(挙動)で行う。
sid="$(printf '%s' "$input" | jq -r '.session_id // "nosess"' 2>/dev/null)"
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)"
used="/tmp/claude_edo_blender_used_${sid}"
case "$cmd" in *"blender --background"*|*"blender -b "*|*"/blender "*|*"blender.app"*) touch "$used" 2>/dev/null ;; esac
[ -f "$used" ] || exit 0

root="$cwd"
while [ "$root" != "/" ] && [ ! -d "$root/Assets/Edo" ]; do root="$(dirname "$root")"; done
[ "$root" = "/" ] && exit 0

models="$root/Assets/Edo/Models"
[ -d "$models" ] || exit 0

# 最新 .fbx の mtime と、それが直近120秒以内か
newest_t=$(find "$models" -name '*.fbx' -type f -exec stat -f %m {} + 2>/dev/null | sort -rn | head -1)
[ -z "$newest_t" ] && exit 0
now=$(date +%s)
[ "$((now - newest_t))" -gt 120 ] && exit 0   # 直前の書き出しでなければ黙る

marker="/tmp/claude_edo_fbx_${sid}_$(printf '%s' "$root" | md5 -q 2>/dev/null || echo default)"
[ -f "$marker" ] && [ "$(cat "$marker" 2>/dev/null)" = "$newest_t" ] && exit 0
printf '%s' "$newest_t" > "$marker" 2>/dev/null

fresh=$(find "$models" -name '*.fbx' -type f -newermt "-120 seconds" 2>/dev/null | sed "s|^$root/||")
[ -z "$fresh" ] && fresh="  (mtime $(date -r "$newest_t" '+%H:%M:%S'))"

read -r -d '' msg <<EOF
[edo-unity] 新しい FBX が出ました。部材はまだ「出しただけ」です。

$(printf '%s\n' "$fresh" | sed 's/^/    /')

残りの完了条件:
  1. **検証レンダを自分で見る** — --render で Screenshots/*.png を出し、Read で開く。
     形・UV・厚み・端部(小口が透けていないか)を確認する。見ずに完了と言わない。
  2. **実寸を測って報告する** — Unity 座標で W(X) × H(Y) × D(Z)。
     Blender は Z-up なので「厚み = Blender Y / 高さ = Blender Z」。
     取り違えて 2.57m の壁が 1.60m に潰れた実例がある。
  3. **Unity でマテリアルを remap する** — Edo/御殿/…マテリアルをremap(隅・坂は別メニュー)。
     やらないと全部真っ白。FBX は材質「名」しか運ばないので Search & Remap が既存 .mat を再結合する。
  4. **EdoAssets.cs に登録する** — 寸法パラメタ化パスは関数で(Own.Kado(part,deg) の書式)。
     関数のコメントに対応する Blender コマンドを1行で書く。パスの literal を他所に書かない。

いずれかを飛ばすなら、その理由を明示してください。
EOF

jq -n --arg m "$msg" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$m}}'
exit 0
