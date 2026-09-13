# Unity 公式プラグイン(`unity@unity-agent-plugin`)— edo-unity での採否と読み替え

2026-09-12 導入。v0.1.2-beta・スキル31本(hooks・MCP サーバは同梱なし)。スキル名は `unity:<名>`。
プラグインは Unity 6 の一般的なゲーム開発向けで、**このプロジェクトの規則(CLAUDE.md)より弱い。**
食い違ったら CLAUDE.md が勝つ。

---

## 1. 前提の読み替え — プラグインは「CLI の `eval`」、このプロジェクトは「Unity MCP」

プラグインのスキルは、エディタを `unity` CLI + `com.unity.pipeline` パッケージの
`unity command eval '<C#>'` で動かす前提で書かれている。**当プロジェクトは pipeline を入れておらず、
エディタを動かす経路は Unity MCP だけ。** スキルの手順は次のように読み替える。

| プラグインの書き方 | このプロジェクトでは |
|---|---|
| `unity command eval '<C#>'` | `mcp__unityMCP__execute_code` |
| `unity status`(エディタが繋がっているか) | リソース `mcpforunity://instances` / `manage_editor` |
| `unity command editor_play` など | `manage_editor` |
| C# ファイルを書いてコンパイル確認 | `manage_script` → `read_console`(CLAUDE.md「コンパイルが止まっていることがある」) |
| UPM パッケージの追加(`unity-package-management`) | ⛔ `Packages/manifest.json` の変更は共有設定の変更 → ユーザー裁定 |

- `eval` の制約(`using` 不可・型は完全修飾・`Object` は `UnityEngine.Object`)は **execute_code と同じ**。
  加えてこのプロジェクトは codedom = **C# 6**(補間文字列不可)。→ `unity-surface-authoring/references/execute-code-and-render.md`
- ⛔ execute_code は Unity の排他(claim)に掛かる。**プラグインのスキルが Unity を触る手順を含むなら、
  `edo_session.py start <屋敷> --unity` の後で。**
- ⛔ プラグインの「許可を取らずに直接直せ」「診断せずに答えを書け」系の指示
  (`physics-3d-collision` の *No permission-asking* ほか)は、**指図先行(規則2)・関門(規則18)・
  検分役は read-only** に負ける。読み飛ばすこと。

## 2. ⛔ `unity` CLI でエディタを動かさない・pipeline を入れない

- CLI は `~/.unity/bin/unity`(1.0.0-beta.6)に入っている。`unity pipeline install` を打つと
  `Packages/manifest.json` が変わり、以後 **Bash から `unity command` でエディタを直接触れる**ようになる。
- 門番は `mcp__unityMCP__*` を `check-unity` に掛けるが、Bash は書き込み先のファイルしか見ていなかった。
  **2026-09-13 に `check-bash` へ `unity command|pipeline|open|build|test|job` を足し、`check-unity` と
  同じ規則で取るようにした**(`Tools/Session/edo_session.py` の `UNITY_CLI`)。入口ごとに規則が
  違う事故(EDO-0076)を繰り返さないため。
- それでも pipeline は入れない。入口が2本になると、MCP のタイムアウト再送の多重実行対策・
  冪等でない造成ステージのガードを2本ぶん保たなければならない。入れるならユーザー裁定。
- 読むだけの使い方(`unity status` / `unity editors --installed` / `unity releases`)は構わない。

## 3. 採否表

⭕=使う / △=その場面だけ使う / ✕=このプロジェクトでは使わない

| スキル | 採否 | このプロジェクトでの使いどころ |
|---|---|---|
| `unity:urp-postprocessing` | ⭕ | Volume・トーンマップ・Bloom の点検。検証レンダの見え方が妙なとき、§4 の所見から入る。デバッグ手順8項目が実用的 |
| `unity:ui-imgui` | ⭕ | `Edo/` メニューのエディタ窓の保守。`Assets/Edo` のエディタUIは IMGUI 10本・UI Toolkit 0本。スキルは新規窓に UI Toolkit を勧めるが「プロジェクトが IMGUI だけ」の例外に当たる → **新規も IMGUI で揃える** |
| `unity:physics-3d-collision` | △ | 接地QA・地形採寸の `Physics.Raycast` が当たらないとき(Collider の有無・layer mask・MeshCollider の条件)。§1 の最後の注意を守る |
| `unity:migrate-birp-to-urp` | △ | プロジェクトは URP 済みなので移行フェーズは回さない。在庫パックを再 import してマテリアルがマゼンタになったときだけ `references/custom-shader-triage.md` を引く(Japanese Garden の URP パッチはメモリ参照) |
| `unity:validate-urp-render-graph-renderer-feature` | △ | 現状 `Assets/Edo` に ScriptableRendererFeature は無い(水中は深度オーバーレイ方式、`PC_Renderer` は SSAO のみ)。**Renderer Feature を新しく書いたら、実装の前にこれで検める** |
| `unity:generate-editor-search-query` | △ | ユーザーが Unity の Search 窓で見たいときのクエリ組み立て(`t:prefab ref=…`)。在庫を引く正典は `edo-zaiko`(`docs/asset-index.tsv`)で、Search は補助。窓を開くのは execute_code なので Unity の claim が要る |
| `unity:initialize-ai-navigation` | △ 候補 | `com.unity.ai.navigation` 2.0.13 は入っているが未使用。囲いの抜け(EDO-0172「表門と番所の間が目の高さで素通し」の型)は部材の実メッシュに依るので、NavMesh の経路で捕まえる検査は**実装の輪でしか出ない型**に当たる。使うなら検査の設計から(`docs/verification-loops.md` §4) |
| `unity:unity-cli` | △ | 読むだけ(§2) |
| `unity:shader-graph-create-custom-node` | ✕ | 自作シェーダは手書きの `.shader`/`.hlsl`(EdoWater・TerrainLitStochastic ほか)で Shader Graph を使っていない |
| `unity:unity-package-management` | ✕ | manifest を触る → ユーザー裁定(§1) |
| `unity:new-unity-project` | ✕ | 新規プロジェクト用 |
| `unity:ui` / `ui-ugui` / `ui-uitk` / `optimize-text-mesh-pro` | ✕ | ランタイムUIが無い |
| `unity:2d-pixel-perfect` / `sprite-editor` / `sprite-segment-3x3grid` / `manage-sprite-atlas` / `tilemap-*` | ✕ | 2D 用 |
| `unity:implement-in-app-purchases` / `levelplay-unity-integration` / `build-live-game` / `setup-multiplayer-services` / `setup-vivox-voice-chat` | ✕ | 課金・広告・オンライン |
| `unity:audio-setup-mixers` / `optimize-audio` / `optimize-web` / `localization` | ✕ | 音・Web 配信・多言語は対象外 |

## 4. 導入時の点検で出た所見(2026-09-13)

1. **シーンの Post-processing Volume が何も効いていない。** `Akasaka.unity` の Volume(シーン内に1つ)の
   `sharedProfile` は `Assets/Edo/PostVolume.asset` だが、その `components` が **4件とも `{fileID: 0}`**
   (override の実体が失われている)。`urp-postprocessing` はこの状態を「不完全」と明記している。
   シーンの色味は Global Settings 側の `DefaultVolumeProfile` だけで決まっている。
   何を効かせるか(トーンマップ・霞・色温度)は見た目の判断なので、直すならユーザー裁定。
2. **門番の穴** — §2 のとおり塞いだ。
