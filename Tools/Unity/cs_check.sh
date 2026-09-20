#!/bin/zsh
# Unity を起こさずに Editor アセンブリの C# を検める(構文と型)。
#   使い方: zsh Tools/Unity/cs_check.sh    — 何も出なければ通る。error 行が出たら直す。
#
# ⭐ **Unity の claim が要らない。**他のセッションが Unity を握っている間でも C# を直せる。
#    赤坂を開いた Unity の再コンパイルは 53 秒・作業場でも 9.8 秒(.claude/rules/unity.md)。
#    ここは 3〜5 秒で、しかも他人の Unity を巻き込まない。
# ⚠ これは**コンパイルの検め**であって、建つ姿の検めではない。据わりや取り合いは Unity で測る。
# ⚠ 参照は Unity 6000.5.2f1 の Managed/UnityEngine/*.dll(モジュール側)と Library/ScriptAssemblies。
#    ⛔ 一枚物の UnityEngine.dll / UnityEditor.dll を足さない — 同じ型が二重に見えて CS0433 が噴く。
set -e
P=${EDO_ROOT:-$(cd "$(dirname $0)/../.." && pwd)}
U=${UNITY_APP:-/Applications/Unity/Hub/Editor/6000.5.2f1/Unity.app/Contents}
DN=$U/Resources/Scripting/DotNetSdk/dotnet
CSC=$(ls $U/Resources/Scripting/DotNetSdk/sdk/*/Roslyn/bincore/csc.dll | head -1)
OUT=${TMPDIR:-/tmp}/edo_editor_check.dll
cd $P
refs=()
for d in $U/Resources/Scripting/NetStandard/ref/2.1.0/*.dll $U/Resources/Scripting/NetStandard/Extensions/2.0.0/*.dll(N); do refs+=("-r:$d"); done
for d in $U/Resources/Scripting/Managed/UnityEngine/*.dll; do refs+=("-r:$d"); done
for d in $P/Library/ScriptAssemblies/*.dll; do
  case "$(basename $d)" in Assembly-CSharp-Editor.dll) continue;; esac
  refs+=("-r:$d")
done
srcs=($(find Assets -path '*/Editor/*' -name '*.cs'))
$DN exec $CSC -nologo -target:library -nostdlib+ -langversion:9.0 -define:UNITY_EDITOR -out:$OUT "${refs[@]}" "${srcs[@]}" 2>&1 | grep -v "warning CS" || true
