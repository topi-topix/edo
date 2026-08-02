Shader "Edo/Underwater"
{
    // カメラ手前に置くフルスクリーンのクワッドに貼る「水中」オーバーレイ。
    // シーン深度から波長別の色吸収(赤から先に消える)を計算し、遠方ほど水中色に沈める。
    // さらに屈折の揺らぎ・コースティック光・水面から差す光芒・周辺減光を重ねて水中感を出す。
    // 前提: URP の Depth Texture と Opaque Texture が ON。
    Properties
    {
        _WaterColor  ("Deep Water Color", Color) = (0.03,0.16,0.19,1)
        _ShallowTint ("Light Streak Tint", Color) = (0.18,0.44,0.47,1)
        _Density     ("Murk Density (1/m)", Float) = 0.67
        _MaxMurk     ("Max Murk", Range(0,1)) = 0.94
        _NearTint    ("Near Tint", Range(0,0.6)) = 0.28
        _CausticStrength ("Caustic Strength", Range(0,1)) = 0.75
        _CausticScale ("Caustic Scale", Float) = 7
        _CausticSpeed ("Caustic Speed", Float) = 0.8
        _SurfaceGlow ("Surface Glow (overhead)", Range(0,2)) = 0.8
        _Vignette    ("Vignette", Range(0,2)) = 0.75
        _Submersion  ("Submersion (0..1)", Range(0,1)) = 1
        _Wobble      ("Refraction Wobble", Range(0,0.03)) = 0.010
        _WobbleSpeed ("Wobble Speed", Float) = 1.1
        _RefrMix     ("Refraction Mix", Range(0,1)) = 0.45
        _GodRay      ("God Rays", Range(0,1)) = 0.35
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent+400" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "UnderwaterOverlay"
            Tags { "LightMode"="UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            ZTest Always
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareOpaqueTexture.hlsl"

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float4 screenPos   : TEXCOORD0;
                float3 viewDirWS   : TEXCOORD1;
            };

            CBUFFER_START(UnityPerMaterial)
                float4 _WaterColor;
                float4 _ShallowTint;
                float  _Density;
                float  _MaxMurk;
                float  _NearTint;
                float  _CausticStrength;
                float  _CausticScale;
                float  _CausticSpeed;
                float  _SurfaceGlow;
                float  _Vignette;
                float  _Submersion;
                float  _Wobble;
                float  _WobbleSpeed;
                float  _RefrMix;
                float  _GodRay;
            CBUFFER_END

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs p = GetVertexPositionInputs(IN.positionOS.xyz);
                OUT.positionHCS = p.positionCS;
                OUT.screenPos   = ComputeScreenPos(p.positionCS);
                OUT.viewDirWS   = p.positionWS - _WorldSpaceCameraPos;
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float2 uv = IN.screenPos.xy / IN.screenPos.w;
                float t = _Time.y;

                // --- 屈折の揺らぎ(水越しに見るユラユラ) ---
                float2 wob;
                wob.x = sin(uv.y * 21.0 + t * _WobbleSpeed * 1.7) * 0.6
                      + sin(uv.y * 7.3  - t * _WobbleSpeed * 1.1) * 0.4;
                wob.y = sin(uv.x * 17.0 - t * _WobbleSpeed * 1.3) * 0.6
                      + sin(uv.x * 5.9  + t * _WobbleSpeed * 0.9) * 0.4;
                float2 uvR = uv + wob * _Wobble;

                // --- シーン深度 → 波長別の吸収(赤が先に消える) ---
                float rawD = SampleSceneDepth(uv);
                float dist = LinearEyeDepth(rawD, _ZBufferParams);
                float dn = max(0.0001, _Density);
                float3 ext = float3(dn * 1.9, dn * 1.0, dn * 0.75);   // R>G>B の順に強く吸収
                float3 fog3 = 1.0 - exp(-dist * ext);
                fog3 = _NearTint + fog3 * (1.0 - _NearTint);
                float fog = fog3.g;

                // --- 見上げた先の水面グロー / 光芒 ---
                float3 ray = normalize(IN.viewDirWS);
                float up   = saturate(ray.y);
                float glow = pow(up, 3.0) * _SurfaceGlow;
                float rays = pow(up, 1.6) * _GodRay
                           * (0.5 + 0.5 * sin(uv.x * 34.0 + t * 0.9) * sin(uv.x * 13.0 - t * 0.6));

                // --- コースティック(揺らぐ光の筋) ---
                float ct = t * _CausticSpeed;
                float2 cp = uvR * _CausticScale;
                float caustic = sin(cp.x * 3.1 + ct) * sin(cp.y * 2.7 - ct * 1.3)
                              + sin((cp.x + cp.y) * 2.0 + ct * 0.7);
                caustic = saturate(caustic * 0.3 + 0.45);

                // 水中色: 深い水色ベース、光の筋で明るい水色へ、上方向はグロー
                float3 col = _WaterColor.rgb;
                col = lerp(col, _ShallowTint.rgb, caustic * _CausticStrength);
                float shimmer = 0.7 + 0.5 * caustic;
                col += glow * float3(0.35, 0.78, 1.0) * shimmer;
                col += rays * float3(0.30, 0.62, 0.75);

                // --- 揺らいだシーン色を混ぜて「水越し」感を出す ---
                float3 scene = SampleSceneColor(uvR);
                // 吸収で色を失わせてから混ぜる
                float3 sceneAbs = scene * saturate(1.0 - fog3);
                col = lerp(col, col * 0.35 + sceneAbs * 1.15, _RefrMix * saturate(1.0 - fog * 0.55));

                // --- 周辺減光 ---
                float2 d2 = uv - 0.5;
                float r2 = dot(d2, d2);
                float vig = saturate(1.0 - r2 * _Vignette * 4.0);
                col *= lerp(0.5, 1.0, vig);

                float a = saturate(fog + (1.0 - vig) * 0.18);
                a = a * _MaxMurk * _Submersion;

                return half4(col, a);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
