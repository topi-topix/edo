#!/bin/sh
# 検査の**判定そのもの**の破壊試験。⛔ Unity を握らずに走る(同梱の Roslyn で単体コンパイル)。
#
#   sh Tools/Qa/run_verdict_destructive.sh [指図の json]
#
# ⚠ 「検査を書いた」だけでは記録にならない — その検査が**本当に鳴るか**を機械で確かめる
#   (CLAUDE.md 規則19)。2026-09-04 の初回でいきなり1件見つけた:
#   失敗の判定が `report.StartsWith("★")` だったため、★ が2行目以降に出る報告
#   (算出物の検め)を**一つも捕まえられなかった**。
# 終了コードは「期待外れの件数」。0 なら全件が期待どおり。
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
DOC=${1:-"$ROOT/docs/Sashizu/okabe_sashizu.json"}
ED=$(ls -d /Applications/Unity/Hub/Editor/*/Unity.app/Contents 2>/dev/null | tail -1)
[ -n "$ED" ] || { echo "Unity が見つからない"; exit 2; }
SDK=$(ls -d "$ED"/Resources/Scripting/DotNetSdk/sdk/* | tail -1)
NS="$ED/Resources/Scripting/NetStandard/ref/2.1.0"
OUT=$(mktemp -d)
RSP="$OUT/d.rsp"
{ echo "-nologo"; echo "-target:exe"; echo "-langversion:9.0"; echo "-noconfig"; echo "-nostdlib+";
  echo "-out:$OUT/destr.dll";
  for f in "$NS"/*.dll; do echo "-r:$f"; done
  echo "$ROOT/Assets/Edo/Scripts/Editor/EdoQaVerdict.cs"
  echo "$ROOT/Tools/Qa/EdoQaVerdictDestructive.cs"; } > "$RSP"
"$ED/Resources/Scripting/DotNetSdk/dotnet" "$SDK/Roslyn/bincore/csc.dll" "@$RSP" | grep -v "warning CS2023" || true
printf '{ "runtimeOptions": { "tfm": "net8.0", "framework": { "name": "Microsoft.NETCore.App", "version": "8.0.0" } } }' > "$OUT/destr.runtimeconfig.json"
"$ED/Resources/Scripting/DotNetSdk/dotnet" "$OUT/destr.dll" "$DOC"
