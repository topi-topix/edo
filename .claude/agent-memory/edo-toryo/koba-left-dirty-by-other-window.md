---
name: koba-left-dirty-by-other-window
description: 作業場が前の窓の邸で dirty のまま残り Open が止まる・旧い退避は「前の案の造成前」で差分の基準にならない
metadata:
  type: project
---
症状: claim を受けた時、作業場(Koba)は前の窓の邸(岡部)を載せて dirty。EdoKoba.Open は dirty で ⛔。地形も IsDirty=true。
対処: `EdoYashikiPrefab.UnwrittenIn(scene)` が空なのを見てから SaveScene → OpenFor(邸)。地形は先に全面を scratchpad へ .bin で採り、開いた後に同じか突き合わせる(2026-10-03 一致)。造成後は `AssetDatabase.SaveAssetIfDirty(td)` で地形を資産へ。
罠2: 邸ビルダーの Stage0 の退避が「無いときだけ書く」だと、案を替えた建て直しでは**前の案の造成前**が残っていて今の地形の差分の基準にならない(土井 TerrainBackups/doi_20260906_pre_grade)。案ごとに退避の名を替える(土井は UserData/Backups/Doi/heightmap_pre_anA.bin)。
