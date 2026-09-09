# -*- coding: utf-8 -*-
"""**切石(叩き仕上げ)の材のテクスチャを1枚焼く。**

    python3 Tools/Blender/make_kirishi_texture.py [--v <明度 0..255>] [--sat <彩度倍率>]

━━━ なぜ新造するか(⚠ 「新規マテリアルを作らない」規約の 2 例目の明示的な例外)━━━
庭方19巡目 指3 / 考証20巡目 高3 が **独立に同じ判定**を出した:
社殿の**石造亀腹・基壇が暗すぎて切石に読めない**(実測 V21.6% ＝ 木部 43.1% の**ちょうど半分**)。
在庫方が 2026-09-09 に洗った結果、**「淡灰の花崗岩系・平滑」の貼れる材は在庫に無い**:
  ・`M_FJG_Rock_001`(いま使っている)= 暗い苔むした写真計測岩。アルベド中央 V13.3% ⛔
  ・`M_Sakaiishi.mat` = 数値は要求どおりだが **テクスチャ無しの単色** ⇒ 近景で無地の板になる ⛔
  ・`Foundation_A_01` = 玉石の乱積み(既に 2026-09-09 に落とした)⛔
  ・`Japanese Castle` の `Steps` / `Wall Exterior Defence` = **アトラス**で、専用 UV を
    切らない限り隣の絵柄が混ざる ⛔
⇒ **銅瓦(`Doukawara`)と同じやり方**で1枚起こす: **在庫の石の肌(grain)と法線を流用し、
  色と粗さだけ差し替える**。素は `Assets/Edo/Materials/japanese_stone_wall/`(⭕ `Assets/Edo` 配下・
  git 追跡済み・**どの .mat からも参照されていない孤児アセット**)。

━━━ 確度 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔⛔ 【U 設計値 — 庭方 2026-09-09 十九巡目 指3。**史料は石種・色・目地・段数を言わない**【?】】
  ⛔ この材と色に【A】【S】を名乗らせない。指図の側にも同じ確度で書くこと。
【受入値(庭方)】H 25〜50°(暖灰)/ S ≤ 8% / V 52〜60% ≒ RGB (133,130,124)。
  肌は**叩き仕上げ・面の凹凸 ≤ 3mm**。⛔ 割肌・欠けた稜にしない。
⚠ **ここで焼くのはアルベドで、レンダの V ではない。**Blender の view transform(AgX)は
  明部を圧縮し彩度を落とすので、⭐ **アルベドの数をそのまま「基壇の明度」と読まない**
  (銅瓦で踏んだのと同じ罠 — あちらは色相が 13° ずれた)。**測るのは `check_color.py`。**

━━━ 素の選び方 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`jsw_diffuse.jpg`(2048²)は**石垣の壁**なので**目地が焼き込んである**。⛔ そのまま貼ると
本物の目地(石と石の隙)と喧嘩して二重の目地が出る。⇒ **目地に掛からない矩形**を
暗部の割合で機械的に探した ⇒ `SRC_RECT`(128²・実測 中央 RGB(122,118,109) H41.5 S10.7 V47.8)。
⭕ 低周波のムラを**ぼかしで割って落とし**(= 石ごとの色差を消す)、
  残った**高周波の粒だけ**を目標色に掛ける ⇒ 叩き肌の stipple になる。
⭕ 端は**半分ずらして重ねる**ことで継ぎ目を消す(タイル貼りにする)。
"""
import sys, os
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(REPO, "Assets", "Edo", "Materials", "japanese_stone_wall")
OUT = os.path.join(REPO, "Assets", "Edo", "Materials", "Sanno")

SRC_RECT = (1504, 928, 1632, 1056)   # jsw_diffuse.jpg(2048²)の**目地に掛からない**矩形
TILE_M = 0.44                        # このテクスチャが受け持つ実寸[m]。⛔ 段の丈 0.30 と
                                     #   **同じにしない** — 繰り返しが目地と揃って縞に見える
GRAIN = 0.55                         # 粒のコントラスト(1.0 = 素のまま)。⛔ 上げると割肌に寄る
# ⭐ 目標のアルベド(sRGB 0..255)。⚠ **レンダの V ではない**(AgX が圧縮する)。
#   ⇒ `check_color.py --preset shaden` で測って、この数を動かして合わせ込む。
TARGET = (134, 128, 119)


def _blur(a, r):
    """箱ぼかし(numpy だけで済ませる。scipy を持ち込まない)。"""
    k = 2 * r + 1
    p = np.pad(a, r, mode="reflect")
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    return (c[k:k + h, k:k + w] - c[0:h, k:k + w]
            - c[k:k + h, 0:w] + c[0:h, 0:w]) / float(k * k)


def _seamless(a):
    """半分ずらして重ね、継ぎ目を線形に溶かす(⇒ タイル貼りで継ぎ目が出ない)。"""
    h, w = a.shape[:2]
    b = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    fy = np.minimum(np.arange(h), h - 1 - np.arange(h)) / (h / 2.0)
    fx = np.minimum(np.arange(w), w - 1 - np.arange(w)) / (w / 2.0)
    f = np.clip(np.minimum(fy[:, None], fx[None, :]), 0.0, 1.0)
    if a.ndim == 3:
        f = f[:, :, None]
    return a * f + b * (1.0 - f)


def bake(target, sat=1.0):
    os.makedirs(OUT, exist_ok=True)
    x0, y0, x1, y1 = SRC_RECT
    src = np.asarray(Image.open(os.path.join(SRC, "jsw_diffuse.jpg")).convert("RGB")
                     .crop((x0, y0, x1, y1))).astype(np.float32)
    lum = src.mean(2)
    # ⭕ 低周波(石ごとの色差・陰)を割って落とし、高周波の粒だけを残す
    # ⚠ 半径 12 では**縦の筋**(素の石垣の縦のムラ)が残り、0.30m 刻みで貼ると
    #   基壇が**コーデュロイ**になった(2026-09-09 の検証レンダで実見)。⇒ 半径を詰める
    g = lum / np.maximum(_blur(lum, 5), 1e-3)
    # ⛔⛔ **等方な粒にする。**素は石垣なので **縦の筋**(石の割れ・雨だれ)が残り、
    #   0.30〜0.44m 刻みで貼ると基壇が**コーデュロイ**に見えた(2026-09-09 実見)。
    #   ⇒ 列の平均・行の平均でそれぞれ割り、**1次元の縞を構造として消す**。
    g = g / np.maximum(g.mean(0)[None, :], 1e-3)
    g = g / np.maximum(g.mean(1)[:, None], 1e-3)
    g = 1.0 + (g - 1.0) * GRAIN
    g = _seamless(g)
    tgt = np.array(target, dtype=np.float32)
    grey = tgt.mean()
    tgt = grey + (tgt - grey) * sat
    alb = np.clip(g[:, :, None] * tgt[None, None, :], 0, 255).astype(np.uint8)
    Image.fromarray(alb).resize((256, 256), Image.LANCZOS) \
        .save(os.path.join(OUT, "T_Kirishi_Albedo.png"))

    nrm = Image.open(os.path.join(SRC, "jsw_normal.png")).convert("RGB")
    W, H = nrm.size
    s = W / 2048.0                                   # 法線は解像度が違うことがある
    nc = np.asarray(nrm.crop((int(x0 * s), int(y0 * s), int(x1 * s), int(y1 * s)))
                    ).astype(np.float32)
    nc = _seamless(nc)
    Image.fromarray(np.clip(nc, 0, 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS) \
        .save(os.path.join(OUT, "T_Kirishi_Normal.png"))

    import colorsys
    m = np.median(alb.reshape(-1, 3), 0)
    h, s2, v = colorsys.rgb_to_hsv(*(m / 255.0))
    print("[kirishi] アルベド中央 RGB(%3.0f,%3.0f,%3.0f)  H%.1f° S%.1f%% V%.1f%%  "
          "粒の振れ ±%.1f%%  タイル %.2f m"
          % (m[0], m[1], m[2], h * 360, s2 * 100, v * 100,
             100.0 * float(np.std(g)), TILE_M))
    print("[kirishi] 書き出し " + os.path.join(OUT, "T_Kirishi_Albedo.png"))
    print("[kirishi] 書き出し " + os.path.join(OUT, "T_Kirishi_Normal.png"))
    print("⚠ **これはアルベド。**レンダの V は `check_color.py --preset shaden` で測ること。")


# ==========================================================================
# Unity 側の器(.mat と .meta)— ⭕ 焼くたびに**同じ GUID** で作り直せるようにする
# ==========================================================================
# ⚠ `Edo/山王社/新造部材のマテリアルをremap` の donorDirs に `Edo/Materials/Sanno` が
#   既に入っている(`build_sanno_shaden` の冒頭に実測の記録あり)⇒ **足す行は無い**。
#   FBX は材質**名**しか運ばないので、ここに `Kirishi.mat` が在れば名前一致で当たる。
MAT_NAME = "Kirishi"
URP_LIT_GUID = "933532a4fcc9baf4fa0491de14d08ed7"     # Doukawara.mat と同じ URP/Lit
BUMP_SCALE = 0.30       # ⭐ 叩き仕上げ = 面の凹凸 ≤ 3mm。⛔ 1.0 だと割肌の陰が出る
SMOOTHNESS = 0.10       # 艶消し(在庫の `M_Sakaiishi.mat` の 0.08 に倣う)


def _guid(name):
    """⭕ 名前から決め打ちで作る(焼き直しても GUID が変わらない ⇒ 参照が切れない)。"""
    import hashlib
    return hashlib.md5(("edo-unity/sanno/" + name).encode("utf-8")).hexdigest()


TEX_META = """fileFormatVersion: 2
guid: %(guid)s
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {}
  serializedVersion: 13
  mipmaps:
    mipMapMode: 0
    enableMipMap: 1
    sRGBTexture: %(srgb)d
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
    flipGreenChannel: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  vTOnly: 0
  ignoreMipmapLimit: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 1
    aniso: 1
    mipBias: 0
    wrapU: 0
    wrapV: 0
    wrapW: 0
  nPOTScale: 1
  lightmap: 0
  compressionQuality: 50
  spriteMode: 0
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {x: 0.5, y: 0.5}
  spritePixelsToUnits: 100
  spriteBorder: {x: 0, y: 0, z: 0, w: 0}
  spriteGenerateFallbackPhysicsShape: 1
  alphaUsage: 1
  alphaIsTransparency: 0
  spriteTessellationDetail: -1
  textureType: %(ttype)d
  textureShape: 1
  singleChannelComponent: 0
  flipbookRows: 1
  flipbookColumns: 1
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureFormatSet: 0
  ignorePngGamma: 0
  applyGammaDecoding: 0
  swizzle: 50462976
  cookieLightType: 0
  platformSettings:
  - serializedVersion: 4
    buildTarget: DefaultTexturePlatform
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 1
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    customData: 
    physicsShape: []
    bones: []
    spriteID: 
    internalID: 0
    vertices: []
    indices: 
    edges: []
    weights: []
    secondaryTextures: []
    spriteCustomMetadata:
      entries: []
    nameFileIdTable: {}
  mipmapLimitGroupName: 
  pSDRemoveMatte: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

MAT_YAML = """%%YAML 1.1
%%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_Name: %(name)s
  m_Shader: {fileID: 4800000, guid: %(shader)s, type: 3}
  m_Parent: {fileID: 0}
  m_ModifiedSerializedProperties: 0
  m_ValidKeywords:
  - _NORMALMAP
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 0
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: -1
  stringTagMap:
    RenderType: Opaque
  disabledShaderPasses:
  - MOTIONVECTORS
  m_LockedProperties: 
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _BaseMap:
        m_Texture: {fileID: 2800000, guid: %(alb)s, type: 3}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _BumpMap:
        m_Texture: {fileID: 2800000, guid: %(nrm)s, type: 3}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _MainTex:
        m_Texture: {fileID: 2800000, guid: %(alb)s, type: 3}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _DetailAlbedoMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _DetailMask:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _DetailNormalMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _EmissionMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _MetallicGlossMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _OcclusionMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _ParallaxMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _SpecGlossMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    m_Ints: []
    m_Floats:
    - _AddPrecomputedVelocity: 0
    - _AlphaClip: 0
    - _AlphaToMask: 0
    - _Blend: 0
    - _BlendModePreserveSpecular: 1
    - _BumpScale: %(bump)s
    - _ClearCoatMask: 0
    - _ClearCoatSmoothness: 0
    - _Cull: 2
    - _Cutoff: 0.5
    - _DetailAlbedoMapScale: 1
    - _DetailNormalMapScale: 1
    - _DstBlend: 0
    - _DstBlendAlpha: 0
    - _EmissionScaleUI: 0
    - _EnvironmentReflections: 1
    - _GlossMapScale: 1
    - _Glossiness: 0
    - _GlossyReflections: 1
    - _Metallic: 0
    - _Mode: 0
    - _OcclusionStrength: 1
    - _Parallax: 0.02
    - _QueueOffset: 0
    - _ReceiveShadows: 1
    - _Smoothness: %(smooth)s
    - _SmoothnessTextureChannel: 0
    - _SpecularHighlights: 1
    - _SrcBlend: 1
    - _SrcBlendAlpha: 1
    - _Surface: 0
    - _UVSec: 0
    - _WorkflowMode: 1
    - _ZWrite: 1
    m_Colors:
    - _BaseColor: {r: 1, g: 1, b: 1, a: 1}
    - _Color: {r: 1, g: 1, b: 1, a: 1}
    - _EmissionColor: {r: 0, g: 0, b: 0, a: 0}
    - _EmissionColorUI: {r: 1, g: 1, b: 1, a: 1}
    - _SpecColor: {r: 0.2, g: 0.2, b: 0.2, a: 1}
  m_BuildTextureStacks: []
  m_AllowLocking: 1
"""

MAT_META = """fileFormatVersion: 2
guid: %(guid)s
NativeFormatImporter:
  externalObjects: {}
  mainObjectFileID: 2100000
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""


def write_unity():
    """⛔ 上書きで壊さない — .mat/.meta は毎回同じ内容を書くだけ(GUID は名前から決まる)。"""
    ga = _guid("T_Kirishi_Albedo.png")
    gn = _guid("T_Kirishi_Normal.png")
    gm = _guid("Kirishi.mat")
    for fn, guid, srgb, ttype in (("T_Kirishi_Albedo.png", ga, 1, 0),
                                  ("T_Kirishi_Normal.png", gn, 0, 1)):
        with open(os.path.join(OUT, fn + ".meta"), "w") as f:
            f.write(TEX_META % dict(guid=guid, srgb=srgb, ttype=ttype))
    with open(os.path.join(OUT, MAT_NAME + ".mat"), "w") as f:
        f.write(MAT_YAML % dict(name=MAT_NAME, shader=URP_LIT_GUID, alb=ga, nrm=gn,
                                bump=("%g" % BUMP_SCALE), smooth=("%g" % SMOOTHNESS)))
    with open(os.path.join(OUT, MAT_NAME + ".mat.meta"), "w") as f:
        f.write(MAT_META % dict(guid=gm))
    print("[kirishi] Unity 器 %s.mat(_BumpScale %.2f / _Smoothness %.2f)"
          % (MAT_NAME, BUMP_SCALE, SMOOTHNESS))


def main():
    a = sys.argv[1:]
    tgt = list(TARGET)
    sat = 1.0
    if "--v" in a:
        v = float(a[a.index("--v") + 1])
        k = v / max(TARGET)
        tgt = [q * k for q in TARGET]
    if "--sat" in a:
        sat = float(a[a.index("--sat") + 1])
    bake(tgt, sat)
    write_unity()


if __name__ == "__main__":
    main()
