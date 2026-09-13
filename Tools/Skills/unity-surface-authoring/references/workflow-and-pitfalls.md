# 作業方法とハマりどころ

## 8. Working method

- Change → screenshot → read → iterate. Never assume a paint worked; look.
- For expensive full-terrain operations, prototype the rule on a coarse grid or preview image first.
- Performance: replacing per-texel heavy work (e.g. inverse map projection over 1M texels) with a
  coarse-grid (e.g. 65×65) bilinear interpolation is accurate to sub-metre and far faster.
- Persist reusable editor tools as project `Editor/*.cs` scripts; persist non-obvious project facts to
  memory. Keep menu items unique (watch for duplicate `[MenuItem]` shortcuts).
- **A new/edited `Editor/*.cs` often does NOT rebuild, and nothing says so.** Symptoms:
  `execute_menu_item` fails with "might be invalid, disabled, or context-dependent", or reflection runs
  the old method body. Checks and cures, in order:
  1. **A compile error anywhere blocks the whole `Assembly-CSharp-Editor`** — including files you never
     touched (a half-finished builder from a previous session). `read_console` returns *cached* entries
     and can look clean; the truth is `grep "error CS" <project>/Logs/Editor.log`. Fix that first.
  2. `AssetDatabase.ImportAsset(..., ForceUpdate)` + `CompilationPipeline.RequestScriptCompilation()`
     can silently no-op — `Library/ScriptAssemblies/Assembly-CSharp-Editor.dll` keeps its old mtime.
     What actually rebuilt it: `AssetDatabase.Refresh(ForceSynchronousImport | ForceUpdate)` then
     **`EditorUtility.RequestScriptReload()`**. Expect 60–90 s and several
     "Unity is reloading; please retry" / MCP timeouts before it settles.
  3. **Verify the new code is live, not just that the type exists.** Reflect on a method and check a
     value only the new version can produce. A stale dll can carry the same type name and a
     coincidentally-fresh mtime; "the type resolves" proves nothing.
- **Before any `EditorSceneManager.SaveScene` / `AssetDatabase.SaveAssets` you initiate, copy the
  `.unity` file (and any `TerrainData.asset` you might flush) to scratch first.** `Scene.isDirty` is
  *not* a reliable "memory == disk" signal: right after a domain reload it can read `false` while the
  in-memory scene still differs from the file. Your save then also commits the user's pending edits —
  benign, but you must detect and report it. Verify afterwards by diffing the **set of
  `^--- !u!NNN &ID` lines** between backup and saved file (added/removed objects show up cleanly), and
  cross-check the count against a live `PrefabUtility.IsAnyPrefabInstanceRoot` walk. Do **not** try to
  read prefab-instance names/positions out of the YAML with regex — a `!u!1001` block contains
  overrides for nested children too, so the first `m_Name` / `m_LocalPosition.x` match is often the
  wrong object and you will "discover" deletions that never happened.
- **Re-datuming an axis is only "done" when the Inspector shows the new numbers.** The Transform
  Inspector displays `localPosition`, so moving group roots by the offset changes nothing the user can
  see — children still read their old values and the point of the change is lost. Bake the offset
  **down** into the objects that actually carry positions and return the group roots to 0: recurse only
  through pass-through groups (`localPosition.y == 0`, has children, **not** a prefab instance root)
  and apply the offset where you stop. Never descend into a prefab instance — that spams overrides.
  Verify by snapshotting every `transform.position` before and comparing after; only the emptied
  container pivots may differ. Parts *inside* a model (beam/ceiling/roof) keep model-local values —
  that is correct, not a miss.
- **Rigid-transforming a whole scene** (e.g. re-datuming Y to sea level): move root transforms, but
  first hunt for *data that stores world coordinates outside transforms* — it cannot ride along.
  In edo-unity that was `WaterBody.waterY`/`outline[].y` (its parent must stay put; fix the fields and
  re-run `WaterBaker.RebuildSurface`), heights baked into shared mesh assets (`OldMapQuad.asset`),
  absolute-Y constants in generator scripts, and world coords in JSON side-files
  (bookmarks, sketches). `TerrainData` is safe — its heights are normalized.

---

## 7. Scene-view navigation: zoom punching through the ground

On a huge terrain the Scene-view **pivot** easily ends up hundreds of metres underground; scroll-zoom
dollies toward the pivot, so you punch through the surface and can't zoom onto the ground. Fix by
snapping `SceneView.lastActiveSceneView.pivot` onto the terrain surface (raycast the collider through
the viewport centre, or `Terrain.SampleHeight` at the pivot XZ) and shrinking `size`. The project ships
`Edo/View/Drop Pivot To Ground (Cmd+Shift+G)` for this (`EdoSceneNav.cs`). Also suggest enabling
Preferences → search "zoom" → "Zoom towards mouse pointer" (a user-level setting).

**A repeatable straight-down view for tracing over map overlays.** Clicking the scene gizmo's Y cone
is NOT reproducible: (a) it keeps **perspective**, so anything off screen-centre leans outward by its
height — the map Quad, the terrain and buildings sit at different Y, so their apparent offsets change
whenever the pivot moves; (b) `pivot`/`size` carry over from the last navigation, so the scale differs
every time; (c) the rotation setter animates, so grabbing the mouse mid-lerp leaves it a fraction off
90°. Fix all three in one call: `sv.in2DMode = false;` then
`sv.LookAt(pivot, Quaternion.Euler(90,0,0), size, /*ortho*/true, /*instant*/true)` — `instant:true`
skips the interpolation so the rotation is exactly 90°, and ortho removes the parallax entirely. Then
`sv.isRotationLocked = true` so a stray Alt-drag can't tilt it back. For true frame-to-frame identity,
also quantise the framing: round `pivot.x/z` to 1 m and snap `size` to a 1-2-5 ladder
(`e=10^floor(log10 v)`, `m=v/e → 1/2/5/10`). Put `pivot.y` on the terrain surface — invisible under
ortho, but it keeps the near/far planes sane. Shipped as `Edo/視点/真上から見る（正射）` (Cmd+Shift+T)
in `Assets/Edo/Scripts/Editor/EdoTopView.cs`, with a rotation-lock toggle beside it.

**Capturing "exactly what the Scene view shows" (viewport-angle bookmark).** To snapshot the current
Scene view from a temp camera, DON'T render to a fixed 16:9 RT with a copied fov — the user's Scene
view window is almost never 16:9, so the framing (and thus the apparent "画角") won't match what they
see. Fix: `c2.CopyFrom(sv.camera)` (clones fov/ortho/orthoSize/clip/projection intent), copy the
transform, set `c2.aspect = sv.camera.pixelWidth/pixelHeight`, and size the RenderTexture to those
same pixel dims (scaled down preserving aspect if huge). This also picks up orthographic (2D) Scene
views for free. Store the aspect (and ortho/orthoSize) alongside pos/euler/fov so the shot can be
reproduced later. Shipped in `Assets/Edo/Scripts/Editor/EdoViewBookmark.cs` (Cmd+Shift+B bookmark
with screenshot + click-to-mark + comments — the user's channel for reporting visual issues by angle).

---

## 巨大なBloom白球の正体＝法線ゼロ→NaN（proven 2026-08-03, 汐見坂の石組下水溝）

**症状**: Scene/Game ビューで画面を覆う真っ白な光球。ライトも発光マテリアルも無い場所に出る。
ブックマークのキャプチャ（ポストプロセス無し）では**同じ場所が真っ黒な小さい破片**に見える。
「黒いのに光る」というこの食い違いが NaN の指紋。NaN ピクセルは HDR で Bloom に拾われて画面
いっぱいに滲み、ポストプロセスを通さないキャプチャでは黒にクランプされる。

**原因**: スクリプト生成メッシュを「同じ頂点を使い回して巻き順を反転した三角形を複製」して
両面化し、そのあと `RecalculateNormals()` を呼ぶと、表裏の面法線が頂点で足し合わされて
**完全に打ち消し、法線が (0,0,0) になる**。URP/Lit がそれを `normalize()` して NaN。

**診断**（シーン全体を1回で）:
```csharp
foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None)) {
    var m = mf.sharedMesh; if (m == null || !seen.Add(m) || !m.isReadable) continue;
    var N = m.normals; int z = 0;
    foreach (var n in N) if (float.IsNaN(n.x) || n.sqrMagnitude < 1e-8f) z++;
    // AssetDatabase.GetAssetPath(m) が空 = シーン生成メッシュ（自前バグ）／非空 = 資産側
}
```
**偽陽性に注意**: 市販アセット（Waldemarst 樹木など）が引っかかっても、まず
「その頂点はどの三角形からも参照されているか」を確かめる。`m.triangles` に現れない**孤立頂点**の
法線ゼロはラスタライズされないので完全に無害。37メッシュ582頂点が全部これだった。

**修正**（トポロジは保ったまま、三角形コーナーごとに頂点を分割してフラット法線を入れ直す）:
頂点位置・三角形・UV・頂点カラーはそのまま複製、法線は `Cross(b-a,c-a).normalized` を3コーナーに。
面積ゼロ三角形は `Vector3.up` にフォールバック（数を必ずログする）。最後に `RecalculateTangents()`
`RecalculateBounds()`、`MeshCollider` があれば `sharedMesh` を入れ直す。同じ Mesh オブジェクトに
書き戻せば MeshFilter の参照が切れない。切石はフラットシェーディングが正解なので見た目も向上する。
頂点数は約9倍になる（776→6912）が、この規模の構造物では問題にならない。
LOD メッシュなど頂点数を増やしたくない場合は、壊れた頂点の法線だけ差し替える最小修正にする。

**検証**: ポストプロセス込みで撮らないと再発を見逃す。
`SceneView.lastActiveSceneView.LookAt(pivot, rot, dist*Tan(fov/2))` で画角を合わせ、
`manage_camera(action:"screenshot", capture_source:"scene_view")` で撮る
（`view_position`/`view_rotation` の一時カメラ撮影はポストプロセスを通らない）。
合格判定は目視でなく数値で: 白飛びピクセル数0 かつ 最大輝度 < 765。

---

## Field note (2026-08-10, 虎御門)
- ユーザーの「下書き(色線)」はEdoSketchのストローク: `UserData/Sketches/<scene>.json` を読むと
  ワールド座標の折れ線が色番号付きで得られる(0赤1黄2水色3緑4桃5白)。設計座標はここから直接取る。
- Akasaka地形のsplat: layer 0=L_dirt 1=L_grass 2=L_bare 3=L_moat。道=bare 0.55-0.72+grass0.04、
  広場(枡形内)=bare 0.42-0.60+grass0.08 (EdoShinmachiBuilderの通り筋レシピ流用)。
