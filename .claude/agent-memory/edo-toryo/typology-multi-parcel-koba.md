---
name: typology-multi-parcel-koba
description: 類型の区画を何軒もまとめて建て直すときの作業場の載せ方と、「触った分だけ」が wrote=0 になる理由
metadata:
  type: project
---

2026-09-28 EDO-0472(十坊10区画)。

1. `EdoKoba.Open(<1軒>)` の隣は 20m 以内の足あとだけ — 十坊は 3〜7 しか載らず 0,1,2,8,9 が来ない。
   **対処**: 開いた後、残りを `PrefabUtility.InstantiatePrefab` で素の名前で置き、同じ区画の「(隣)」は消す。
   BuildParcel(force) は同名ルートを消して起こし直すので、置いた実体は害なく差し替わる。
2. `EdoTypologyBuilder.BuildParcel` は最後に自分で 1軒1プレハブへ切り出す(Externalize)。その後の
   `書き戻す(触った分だけ)` は `wrote=0 (台帳外=N)` と出るが正常。確かめるのはルートが inst=True・ovr 0/0 か。
3. 1区画 1.5〜11 秒。3〜6区画ずつ区画ごとの印のファイルで割れば30秒の再送に掛からない。

関連: [[koba-writeback-ledger-empty]] [[long-run-guard-and-soft-only-converge]]

追記 2026-09-29 EDO-0475(生垣の作り直し・10区画 57秒): 作業場が dirty のときは `EditorSceneManager.OpenScene(Koba, Single)` を
直に打てばダイアログ無しで捨てて開ける(その後 `EdoKoba.Open`)。生垣の区域の越えを外接箱の角で測ると 0.3〜1.07m の
偽の越えが出る(回した株の AABB)。葉の頂点で測れば 20 株・最大 0.38m。株の芯は全部区画の内。
