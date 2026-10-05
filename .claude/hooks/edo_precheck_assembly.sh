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
# 止め方は deny(2026-10-06 施主): ask だと毎回「一度だけ許可」の確認になり常時許可にできない。
# deny なら理由が Claude へ返り、compile_wait.py で作り直してから自分でやり直す。
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

# compile_wait.py が「Unity は作り直し不要と判じた」印を残していれば通す(EDO-0457)。
#   .cs の日付だけ新しく DLL が書き換わらない(中身が同じ・0 件更新)ときに、毎回ここで止まる。
stamp="$root/Temp/edo_compile_wait.json"
if [ -f "$stamp" ]; then
  st_src=$(jq -r '.src_mtime // 0 | floor' "$stamp" 2>/dev/null)
  [ -n "$st_src" ] && [ "$st_src" -ge "$src_t" ] && exit 0
fi

newest=$(find "$root/Assets/Edo" -name '*.cs' -type f -newer "$dll" 2>/dev/null | sed "s|^$root/||" | head -5)
lag=$(( (src_t - dll_t) / 60 ))

read -r -d '' msg <<EOF
[edo-unity] ⚠ アセンブリが古い — このまま execute_code を走らせると「直したのに反映されない」と誤診します。

  Assembly-CSharp-Editor.dll  : $(date -r "$dll_t" '+%Y-%m-%d %H:%M:%S')
  Assets/Edo の最新 .cs       : $(date -r "$src_t" '+%Y-%m-%d %H:%M:%S')  (${lag} 分ぶん古い)

  dll より新しいソース:
$(printf '%s\n' "$newest" | sed 's/^/    /')

やること:
  python3 Tools/Unity/compile_wait.py   — 一手で cs_check → refresh → 完了まで待つ → 誤りと所要秒を返す
  ⛔ 手書きの sleep・until・DLL の日付の見張り・refresh_unity の重ね打ちはしない(EDO-0457)
  ⚠ 時間切れ(⚠ で返る)なら Editor の再起動をユーザーに頼む(こちらからフォーカスは当てられない)

古い結果を根拠に同じ修正を繰り返さないこと。
EOF

jq -n --arg m "$msg" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("止めた(ユーザーに許可は求めない)。compile_wait.py で作り直してから同じ execute_code をやり直す。\n\n" + $m)
  }
}'
exit 0
