# execute_code の罠と、レンダで確かめる方法

すべての作業の土台。**見えない表面は作れない** — 変更したら必ず撮って見る。

## 1. Running C# through `execute_code` — the gotchas that bite every time

Almost all surfacing work is done by sending C# to `mcp__unityMCP__execute_code` with
`action:"execute"`. The snippet runs **inside a method body**, which causes recurring traps:

- **No `using` directives, no top-level type declarations.** They fail with
  `Unexpected symbol 'UnityEngine', expecting '('`. Use fully-qualified names:
  `UnityEditor.AssetDatabase`, `System.Text.StringBuilder`, `System.Collections.Generic.List<>`.
  `UnityEngine.*` and `Mathf`/`Debug`/`GameObject` are already in scope.
- **`Object` is ambiguous** (`object` vs `UnityEngine.Object`). Write
  `UnityEngine.Object.DestroyImmediate(x)`.
- **`AssetDatabase.DeleteAsset` is a BLOCKED pattern** (MCP safety check). Don't call it.
  `AssetDatabase.CreateAsset(obj, path)` overwrites an existing asset at that path anyway.
- **`return` a string** to get output back; also `Debug.Log` for the console.
- **⚠️ Check `EditorApplication.isPlaying` before ANY scene-object edit.** If the user pressed Play,
  GameObject changes you make through `execute_code` can silently revert (Unity restores the scene
  snapshot taken when Play began) — I lost a roof swap this way and only caught it because a later
  read-back showed the *old* prefab name. Crucially the loss is **partial and confusing**: `terrainData`
  is an ASSET, so heightmap edits, splat paints and `SetTreeInstances` all survive Play, while the
  transform/prefab changes next to them do not. `EditorSceneManager.MarkSceneDirty` also throws
  `InvalidOperationException: This cannot be used during play mode` — treat that error as "everything
  scene-side in this call is now untrustworthy", re-read the state, and re-apply after stopping Play
  (`manage_editor action:"stop"`). Verify by reading back a *name or material*, not just a count.
- **A tool timeout does NOT mean the code didn't run.** `Timeout receiving Unity response` usually means
  Unity was busy, not that the edit failed. Never blindly re-run a mutating snippet after a timeout —
  read the state back first, or you get duplicated objects.
- **Domain reload drops the connection.** After `SaveAssets()`, `refresh_unity`, or creating/editing
  scripts, the next call often fails with `Connection closed before reading expected bytes` or
  `No Unity Editor instances found`. This is normal: wait ~6–7s (a `sleep` Bash call), then retry and
  check `read_console` (types:["error"]) before relying on new types/assets.
- **Reading pixels from a project texture** may fail if the texture isn't marked readable. Bypass the
  import flag entirely: read the PNG bytes from disk and `LoadImage` into a fresh Texture2D —
  `var t=new Texture2D(2,2); t.LoadImage(System.IO.File.ReadAllBytes(path));` then `GetPixels32()`.
- **Measuring a prefab/mesh's real-world size:** don't trust the asset filename (`"...4x12.fbx"` can be
  wrong or refer to a different variant than what's actually placed). Query the selected instance
  directly: `UnityEditor.Selection.activeGameObject`, then both
  `MeshFilter.sharedMesh.bounds.size` (the raw mesh extent, unaffected by the instance's rotation —
  this is "the stone's real size") **and** the accumulated `Renderer.bounds` across
  `GetComponentsInChildren<Renderer>()` (the rotated/scaled world-space footprint as it actually sits
  in the scene — these two numbers legitimately differ when the object is rotated, e.g. a corner-filler
  piece placed at a diagonal). Report both; don't collapse to one. The from-UI equivalent (no code) is
  **Add Component → Box Collider** (auto-fits to the renderer bounds and shows a numeric `Size` field)
  — but Unity's Inspector Debug mode does *not* show this, since `Renderer.bounds` is a computed
  property, not a serialized field, so it never appears there no matter how far you scroll.

## 2. Verify by rendering an off-screen screenshot

The reliable way to see a change without the user relaying it. Spawn a temp Camera → RenderTexture →
ReadPixels → EncodeToPNG under `Screenshots/` (that folder is gitignored — free scratch),
then open it with the Read tool. Take an **eye-level** shot and, for layout/coverage, a **top-down
orthographic** shot. Full helper in `references/recipes.md` → "Screenshot helper".

Key params that matter: `nearClipPlane` small (0.03–0.1) for ground close-ups; `clearFlags=Skybox`;
for top-down use `orthographic=true` + `eulerAngles=(90,0,0)` and set `orthographicSize` to half the
world span you want to frame.

## 2b. Test a terrain-editing tool on a throwaway Terrain, never the user's

Terrain edits are destructive and the user's heightmap is usually hand-tuned, so **never** "just try
it" on `Terrain.activeTerrain` — and don't test via the tool's own snapshot/restore either, because
saving clobbers whatever state the user had parked in it. Instead build a scratch terrain in
`execute_code`: `new TerrainData{heightmapResolution=129, size=(256,100,256)}`, `SetHeights` to a flat
known value, `Terrain.CreateTerrainGameObject(td)`; `ScriptableObject.CreateInstance<TheWindow>()`
(an EditorWindow instantiates fine without being shown, and its `OnEnable` runs); poke the private
`terr`/`td`/parameter fields with reflection (`BindingFlags.NonPublic|Instance`), `Invoke` the apply
method, then read results back with `terr.SampleHeight()` and `DestroyImmediate` the GO, the window,
and the TerrainData. Flat-fill makes every expected number hand-checkable (a 10 % grade over 150 m
must read 27.50 m at the midpoint), and a falloff is best verified at 4 radii: centre, band edge,
mid-feather, outside. `codedom` is the compiler in this project (no Roslyn) → C# 6 only: no
interpolated strings, no lambda-typed local funcs, and write `UnityEngine.Object.DestroyImmediate`
(bare `Object` is ambiguous with `object`).

**Graphs inside an EditorWindow:** `Handles.DrawAAPolyLine`/`Handles.color` work directly in
`OnGUI` — with no `Camera.current` they fall back to GUI space (y-down, pixels), so a distance×
elevation profile is just `EditorGUI.DrawRect` for the grid plus poly-lines for the curves. Guard the
drawing with `if (Event.current.type == EventType.Repaint)`, take the graph `Rect` from
`GUILayoutUtility.GetRect`, and drive point-dragging with your own `GUIUtility.hotControl` id so the
drag survives the cursor leaving the rect.

---

## Addendum (2026-08-12): 検証レンダの霞はフォグ
- 上空400mからのtop-downが全体に霞む場合、ModernMap/OldMapオーバーレイを疑う前に **RenderSettings.fog** を確認。
  一時的に `RenderSettings.fog=false` にして撮り、必ず元値へ戻す。
- EdoModernMap.ToggleOverlay は `GameObject.Find`(非アクティブを見つけられない)のため、OFF状態で呼ぶと
  **重複オーバーレイを生成**する。掃除は FindObjectsByType<Transform>(FindObjectsInactive.Include,...) で名前一致を全部SetActive(false)。
