#!/usr/bin/env bash
# PreToolUse hook (matcher: mcp__unityMCP__execute_code)
#
# 「直したのに反映されない」を止める。
#
# Unity のコンパイルは黙って止まっていることがある。古い Assembly-CSharp-Editor.dll のまま
# execute_code を投げると、直したはずのコードが走らず「まだ直っていない」と誤診して
# 同じ修正を繰り返す(2026-08-14 に2回踏んだ)。
# dll の mtime が Assets/Edo/Scripts 配下の最新 .cs より古ければ、実行前に知らせる。
#
# 誤検知を避けるため: 猶予 2 秒。Library が無い(Unity 未起動)なら黙って通す。

input="$(cat)"
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
[ -z "$cwd" ] && cwd="$PWD"

# edo-unity のツリー(worktree 含む)でなければ何もしない
root="$cwd"
while [ "$root" != "/" ] && [ ! -d "$root/Assets/Edo" ]; do root="$(dirname "$root")"; done
[ "$root" = "/" ] && exit 0

dll="$root/Library/ScriptAssemblies/Assembly-CSharp-Editor.dll"
[ -f "$dll" ] || exit 0   # Unity 未起動 / 未ビルド

dll_t=$(stat -f %m "$dll" 2>/dev/null) || exit 0
src_t=$(find "$root/Assets/Edo" -name '*.cs' -type f -exec stat -f %m {} + 2>/dev/null | sort -rn | head -1)
[ -z "$src_t" ] && exit 0

# 猶予 2 秒
[ "$((src_t - dll_t))" -le 2 ] && exit 0

newest=$(find "$root/Assets/Edo" -name '*.cs' -type f -newer "$dll" 2>/dev/null | sed "s|^$root/||" | head -5)
lag=$(( (src_t - dll_t) / 60 ))

read -r -d '' msg <<EOF
[edo-unity] ⚠ アセンブリが古い — このまま execute_code を走らせると「直したのに反映されない」と誤診します。

  Assembly-CSharp-Editor.dll  : $(date -r "$dll_t" '+%Y-%m-%d %H:%M:%S')
  Assets/Edo の最新 .cs       : $(date -r "$src_t" '+%Y-%m-%d %H:%M:%S')  (${lag} 分ぶん古い)

  dll より新しいソース:
$(printf '%s\n' "$newest" | sed 's/^/    /')

やること:
  1. mcp__unityMCP__refresh_unity を投げる(失敗しても実際には再コンパイルされることが多い)
  2. dll の mtime が更新されるまで待つ。ドメインリロードの完了は Unity プロセスの %CPU が
     <20% を数回続けるまで待つ (ps -Ao %cpu,comm | grep "MacOS/Unity$")
  3. mcp__unityMCP__read_console でコンパイルエラーを確認する
  4. それでも更新されないなら Editor の再起動をユーザーに頼む(こちらからフォーカスは当てられない)

古い結果を根拠に同じ修正を繰り返さないこと。
EOF

jq -n --arg m "$msg" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "ask",
    permissionDecisionReason: "Unity のアセンブリがソースより古い(コンパイル未完/停止)。このまま実行すると誤診します。",
    additionalContext: $m
  }
}'
exit 0
