Shader "Edo/TriplanarLit"
{
    // World-space triplanar mapped URP Lit surface.
    // Keeps texel scale constant in meters no matter the object's box dimensions,
    // so stone-wall (石垣) blocks read at a real ~1m stone size on every face,
    // including battered (sloped) faces. Tiling is in "meters per texture tile".
    Properties
    {
        _BaseMap        ("Albedo", 2D) = "white" {}
        _BaseColor      ("Tint", Color) = (1,1,1,1)
        _TileSize       ("World tiles-per-meter", Float) = 0.06
        _BlendSharpness ("Blend sharpness", Range(1,16)) = 6
        _Smoothness     ("Smoothness", Range(0,1)) = 0.15
        _Metallic       ("Metallic", Range(0,1)) = 0.0
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        LOD 200

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                float4 _BaseColor;
                float  _TileSize;
                float  _BlendSharpness;
                float  _Smoothness;
                float  _Metallic;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float3 positionWS  : TEXCOORD0;
                float3 normalWS    : TEXCOORD1;
                float  fogFactor   : TEXCOORD2;
            };

            Varyings vert (Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs pos = GetVertexPositionInputs(IN.positionOS.xyz);
                VertexNormalInputs   nrm = GetVertexNormalInputs(IN.normalOS);
                OUT.positionHCS = pos.positionCS;
                OUT.positionWS  = pos.positionWS;
                OUT.normalWS    = nrm.normalWS;
                OUT.fogFactor   = ComputeFogFactor(pos.positionCS.z);
                return OUT;
            }

            half4 SampleTriplanar(float3 worldPos, float3 normal)
            {
                float scale = _TileSize;
                float2 uvX = worldPos.zy * scale;
                float2 uvY = worldPos.xz * scale;
                float2 uvZ = worldPos.xy * scale;

                half4 cX = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uvX);
                half4 cY = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uvY);
                half4 cZ = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uvZ);

                float3 w = pow(abs(normal), _BlendSharpness);
                w /= (w.x + w.y + w.z + 1e-5);
                return cX * w.x + cY * w.y + cZ * w.z;
            }

            half4 frag (Varyings IN) : SV_Target
            {
                float3 N = normalize(IN.normalWS);
                half4 albedo = SampleTriplanar(IN.positionWS, N) * _BaseColor;

                InputData inputData = (InputData)0;
                inputData.positionWS = IN.positionWS;
                inputData.normalWS = N;
                inputData.viewDirectionWS = GetWorldSpaceNormalizeViewDir(IN.positionWS);
                inputData.shadowCoord = TransformWorldToShadowCoord(IN.positionWS);
                inputData.fogCoord = IN.fogFactor;
                inputData.bakedGI = SampleSH(N);   // ambient so shadowed faces aren't pure black

                SurfaceData surfaceData = (SurfaceData)0;
                surfaceData.albedo = albedo.rgb;
                surfaceData.metallic = _Metallic;
                surfaceData.smoothness = _Smoothness;
                surfaceData.occlusion = 1.0;
                surfaceData.alpha = 1.0;

                half4 color = UniversalFragmentPBR(inputData, surfaceData);
                color.rgb = MixFog(color.rgb, IN.fogFactor);
                return color;
            }
            ENDHLSL
        }

        // Shadow caster so the walls cast/receive shadows.
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ZWrite On ZTest LEqual ColorMask 0

            HLSLPROGRAM
            #pragma vertex shadowVert
            #pragma fragment shadowFrag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

            float3 _LightDirection;

            struct SAttributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct SVaryings { float4 positionHCS : SV_POSITION; };

            SVaryings shadowVert (SAttributes IN)
            {
                SVaryings OUT;
                float3 posWS = TransformObjectToWorld(IN.positionOS.xyz);
                float3 nrmWS = TransformObjectToWorldNormal(IN.normalOS);
                float4 positionCS = TransformWorldToHClip(ApplyShadowBias(posWS, nrmWS, _LightDirection));
                #if UNITY_REVERSED_Z
                    positionCS.z = min(positionCS.z, positionCS.w * UNITY_NEAR_CLIP_VALUE);
                #else
                    positionCS.z = max(positionCS.z, positionCS.w * UNITY_NEAR_CLIP_VALUE);
                #endif
                OUT.positionHCS = positionCS;
                return OUT;
            }

            half4 shadowFrag (SVaryings IN) : SV_Target { return 0; }
            ENDHLSL
        }
    }
    FallBack "Universal Render Pipeline/Lit"
}
