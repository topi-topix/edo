# edo

江戸(赤坂・溜池周辺)を Unity 上に再現するプロジェクト。

- **Unity バージョン**: 6000.5.2f1
- **レンダーパイプライン**: URP 17.5.0
- **メインシーン**: `Assets/Edo/Scenes/Akasaka.unity`
- **座標系**: X,Z の原点は江戸見坂。**Y=0 は海抜0m**(Unity の Y がそのまま標高)

## リポジトリに含まれるもの

自作の成果物のみを管理しています。

| パス | 内容 |
|---|---|
| `Assets/Edo/` | シーン、地形、石垣、道路、水系、シェーダ、マテリアル、古地図/現代地図オーバーレイ、エディタ拡張 |
| `Assets/Edo/Scripts/`, `Assets/Edo/Editor/` | 地形・植生・石垣・水面の生成/編集ツール(`Edo` メニュー) |
| `docs/` | アセット目録([用途別](docs/asset-catalog.md) / [全件TSV](docs/asset-index.tsv) / [フォルダ別](docs/asset-index-summary.md)) |
| `Packages/`, `ProjectSettings/` | パッケージ構成とプロジェクト設定 |

バイナリ(png/fbx/TerrainData 等)は **Git LFS** で管理しています。clone 前に `git lfs install` を実行してください。

## リポジトリに含まれないもの

### 1. サードパーティ製アセットパック

再配布が許諾されていないため除外しています(計約 6.9GB)。シーンを正しく開くには各自で入手し、
`Assets/` 直下に**同じフォルダ名**で import してください。パック同梱の `.meta` に GUID が入っているため、
同一バージョンを import すればプレハブやシーンからの参照は復元されます。

| フォルダ | パック | 入手元 | 用途 |
|---|---|---|---|
| `Assets/NatureManufacture Assets/` | Meadow Environment – Dynamic Nature (NatureManufacture) | Unity Asset Store (有償) | 草木・植生シェーダ・Wind |
| `Assets/Waldemarst/` | Japanese Garden 2 Free (Waldemarst) | Unity Asset Store (無料) | 松・桜・竹の SpeedTree、庭園の地面テクスチャ |
| `Assets/Japanese Castle/` | Japanese Castle Pack (Gabriel M. Guimarães) | Unity Asset Store (有償) | 城郭・石垣パーツ |
| `Assets/Japanese Village Kit/` | Japanese Village Kit (Gabriel M. Guimarães) | Unity Asset Store (有償) | 町家・村落パーツ |
| `Assets/edogoyomi/` | 江戸暦 Edo street series | 3Dモデル素材集(別途購入) | 門・土塀・長屋・辻番所・蔵などの江戸建築 |

import が終わったら Unity で **Edo ▸ アセット目録 ▸ 目録を再生成** を実行して `docs/` の目録を更新する。

#### import 後に必要なローカル改変

**Japanese Garden 2 Free (Waldemarst)** は素の状態では URP / Unity 6 で動きません。import のたびに以下を再適用します。

1. マテリアルの URP 化(114枚中82枚)
   - `Nature/SpeedTree8` → `Universal Render Pipeline/Nature/SpeedTree8_PBRLit`(shader 差し替えのみでプロパティ互換)
   - `Standard` → `URP/Lit`(`_MainTex`→`_BaseMap`, `_Color`→`_BaseColor` の再マップが必要)
   - 未変換だとピンク表示になります
2. `FreeJapaneseGarden/Scripts/BroccoTreeController_FJG_1_10_3.cs` の `_localRenderer.GetInstanceID()` 2箇所を
   `_localRenderer.GetHashCode()` に置換(Unity 6 で `GetInstanceID` が obsolete-as-error。未修正だとプロジェクト全体がコンパイル不能)
3. SpeedTree ビルボードが URP で白飛びするため、Terrain の `treeBillboardDistance = treeDistance` でビルボードを無効化
   (`Assets/Edo/Scripts` の EdoTrees 側で対応済み)

### 2. Unity 生成物

`Library/`, `Temp/`, `Logs/`, `UserSettings/`, `Screenshots/`(Assets の外に移動)は除外しています。

## セットアップ手順

```bash
git lfs install
git clone https://github.com/topi-topix/edo.git
```

1. 上記のサードパーティ製パックを `Assets/` 直下に import
2. Unity 6000.5.2f1 でプロジェクトを開く(初回は import に時間がかかります)
3. `Assets/Edo/Scenes/Akasaka.unity` を開く

## 過去に使っていて外したもの

- **PLATEAU SDK for Unity v4.3.0**(2026-08-14 撤去)。地形は国土地理院タイルから
  `GsiTerrainBuilder` で起こしており、PLATEAU 由来のオブジェクトはシーンに1つも無かった。
  SDK 本体(799MB の tarball)と `LocalPackages/`、`manifest.json` の
  `com.synesthesias.plateau-unity-sdk` を削除。Unity 6000.5 で毎回必要だった
  `EntityId` パッチ(`Library/` を消すと失われる)からも解放される。
  必要になったら v4.3.0 を再入手して `LocalPackages/` に戻し、manifest に1行足せば復帰できる。
