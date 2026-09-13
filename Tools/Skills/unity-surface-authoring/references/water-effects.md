# 水中・スクリーンスペースの水表現(URP)

## 9. Underwater / screen-space water-volume effects (URP)

Making "you are submerged" feel real is a **screen-space** job, not a surface job — the water *surface*
shader (viewed from below) does almost nothing for it.

- **Do NOT rely on URP built-in fog** (`RenderSettings.fog`) for the underwater volume. In this project
  it was effectively a no-op (terrain barely tinted even at exp² density 0.06) and the old effect —
  solid-color camera background + built-in fog — produced a flat dead teal fill with zero depth cue.
- **Working recipe (self-contained, no Renderer Feature / no URP-asset edit):** a full-screen **quad
  parented to the camera** at `nearClip*1.5`, sized to the frustum (`halfH = d*tan(fov/2)*1.25`,
  `halfW = halfH*aspect`, rebuilt each frame), material = an unlit transparent shader with
  `ZTest Always`/`ZWrite Off`/`Cull Off`, queue `Transparent+400`. The shader reads `_CameraDepthTexture`
  (`SampleSceneDepth`→`LinearEyeDepth`) and does its **own** exponential absorption
  `a = 1-exp(-dist*density)`, alpha-blending the water colour over the scene = reliable depth fog you
  fully control. Layer on: caustic streaks (animated sin field over screen uv), an overhead **surface
  glow** tinted blue-green (`pow(saturate(rayDir.y),3)` — white glow looks grey/washed-out, so multiply
  by `float3(0.35,0.78,1.0)`), a vignette, and a camera-parented **particle motes** system (world sim
  space, ~26/s, soft radial sprite) — the motes are the single strongest "I'm underwater" cue.
  Requires URP **Depth Texture** ON. Files: `EdoUnderwater.shader` + `UnderwaterEffect.cs`.
- **Particle gotcha (square "bubbles"):** a runtime-created `Universal Render Pipeline/Particles/Unlit`
  material stays **Opaque** — setting the `_Surface`/`_Blend` *floats* does NOT switch blend state
  (that needs the material-editor's keyword/`_SrcBlend`/`_DstBlend` setup), so every particle draws as
  an opaque white **square** ignoring the sprite alpha. Fix: give the motes a tiny dedicated shader
  (`Blend SrcAlpha OneMinusSrcAlpha`, `ZWrite Off`, sample `_MainTex.a * vertexColor` — the particle
  system feeds tint/alpha via `COLOR`), plus a Clamp-wrapped `SmoothStep` radial sprite. See
  `Edo/Mote` (`EdoMote.shader`).
- **Off-screen verify without Play mode:** temp `Camera` at an underwater world pos, add
  `UniversalAdditionalCameraData` with `requiresDepthOption/requiresColorOption = On`, parent the same
  overlay quad+material with `_Submersion=1`, render to a RenderTexture, `EncodeToPNG`. Shoot horizontal
  **and** straight-up (the up view exposes a washed-out/grey glow fastest). Then confirm live: enter
  Play, disable the FirstPersonController+CharacterController, drop the player below `waterY`, and
  capture the real camera. Submersion test itself = point-in-polygon on `WaterBody.outline` &&
  `camY < waterY`.

---
