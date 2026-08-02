Shader "Edo/Water"
{
    Properties
    {
        _DeepColor   ("Deep Color",    Color) = (0.04,0.13,0.15,1)
        _ShallowColor("Shallow Color", Color) = (0.16,0.34,0.36,1)
        _Smoothness  ("Smoothness",  Range(0,1)) = 0.92
        _WaveSpeed   ("Wave Speed",  Float) = 0.35
        _WaveScale   ("Wave Scale (unused)",  Float) = 0.12
        _WaveStrength("Wave Strength", Range(0,0.6)) = 0.06
        _NormalStrength("Ripple Strength", Range(0,3)) = 1.0
        _NormalScale ("Ripple Scale", Float) = 0.35
        _FresnelPower("Fresnel Power", Range(0.5,8)) = 4.0
        _ReflectionStrength("Reflection", Range(0,2)) = 1.0
        _RefractionStrength("Refraction", Range(0,0.08)) = 0.025
        _SunSpecPower("Sun Glint Sharpness", Range(16,4000)) = 800
        _SunSpecIntensity("Sun Glint", Range(0,8)) = 3.5
        _Alpha       ("Max Alpha",   Range(0,1)) = 0.95
        _DepthFade   ("Color Depth Fade (m)", Float) = 4
        _ShoreWidth  ("Shore Width (m)", Float) = 1.5
        _FoamAmount  ("Foam Amount", Range(0,1)) = 0.4
        _MaskTex     ("Shape Mask (R)", 2D) = "white" {}
        // ---- 滝壺の擾乱: 着水線(A→B)からの距離で指数減衰する荒れ ----
        _AgitA       ("Plunge Line A (xz)", Vector) = (0,0,0,0)
        _AgitB       ("Plunge Line B (xz)", Vector) = (0,0,0,0)
        _AgitRange   ("Agitation Decay Length (m)", Float) = 12
        _AgitStrength("Agitation Strength", Range(0,6)) = 0
        _AgitFoam    ("Agitation Foam", Range(0,1)) = 0.55
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "ForwardWater"
            Tags { "LightMode"="UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareOpaqueTexture.hlsl"

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings   { float4 positionHCS : SV_POSITION; float3 positionWS : TEXCOORD0; float2 uv : TEXCOORD1; };

            TEXTURE2D(_MaskTex); SAMPLER(sampler_MaskTex);

            CBUFFER_START(UnityPerMaterial)
                float4 _DeepColor;
                float4 _ShallowColor;
                float  _Smoothness;
                float  _WaveSpeed;
                float  _WaveScale;
                float  _WaveStrength;
                float  _NormalStrength;
                float  _NormalScale;
                float  _FresnelPower;
                float  _ReflectionStrength;
                float  _RefractionStrength;
                float  _SunSpecPower;
                float  _SunSpecIntensity;
                float  _Alpha;
                float  _DepthFade;
                float  _ShoreWidth;
                float  _FoamAmount;
                float4 _AgitA;
                float4 _AgitB;
                float  _AgitRange;
                float  _AgitStrength;
                float  _AgitFoam;
                float4 _MaskTex_ST;
            CBUFFER_END

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs p = GetVertexPositionInputs(IN.positionOS.xyz);
                OUT.positionHCS = p.positionCS;
                OUT.positionWS  = p.positionWS;
                OUT.uv = IN.uv;
                return OUT;
            }

            // 着水線(線分A-B)からの距離で指数減衰する擾乱量 0..1
            float Agitation(float3 posWS)
            {
                if (_AgitStrength <= 0.0001) return 0.0;
                float2 a = _AgitA.xz, b = _AgitB.xz, p = posWS.xz;
                float2 ab = b - a;
                float t = saturate(dot(p - a, ab) / max(1e-5, dot(ab, ab)));
                float d = distance(p, a + ab * t);      // 着水線までの最短距離
                return exp(-d / max(0.5, _AgitRange));  // 乱れの下流減衰
            }

            // 着水線からの放射波＋側壁反射による定在波の勾配（滝壺の荒れ）
            float2 PlungeGradient(float3 posWS, out float agit, out float boil)
            {
                agit = 0.0; boil = 0.0;
                if (_AgitStrength <= 0.0001) return float2(0,0);
                float2 a = _AgitA.xz, bb = _AgitB.xz, p = posWS.xz;
                float2 ab = bb - a; float len2 = max(1e-5, dot(ab, ab));
                float tt = saturate(dot(p - a, ab) / len2);
                float2 closest = a + ab * tt;
                float d = distance(p, closest);
                agit = exp(-d / max(0.5, _AgitRange));
                float t = _Time.y;

                // 放射波: 着水線から外向きに伝播(波長≈3m)
                float kr = 2.1;
                float radial = sin(d * kr - t * 3.4) + 0.5 * sin(d * kr * 1.9 - t * 4.6);
                float2 dirOut = (d > 0.01) ? (p - closest) / d : float2(0,1);

                // 側壁反射の定在波: 壁際(tt=0,1)が腹になる
                float wallness = saturate(1.0 - 4.0 * tt * (1.0 - tt));
                float lateral = sin(tt * 3.14159 * 9.0) * cos(t * 2.4)
                              + 0.6 * sin(tt * 3.14159 * 15.0 + t * 1.7);
                float2 dirAlong = ab / sqrt(len2);

                // 直下の湧き上がり(ボイル): 着水直近で最も激しい
                boil = exp(-d / max(0.5, _AgitRange * 0.35));

                float2 gAdd = dirOut  * radial  * 0.55 * (0.5 + boil)
                            + dirAlong * lateral * 0.40 * (0.25 + wallness);
                return gAdd * agit * _AgitStrength;
            }

            // 4オクターブの正弦波勾配から水面法線を合成（細かいさざ波）
            float3 WaveNormal(float2 p, float agit)
            {
                // 荒れている所ほど波は速く・細かく
                float t = _Time.y * _WaveSpeed * (1.0 + agit * 2.2);
                float2 d1 = normalize(float2( 1.0, 0.30)); float k1 = _NormalScale;
                float2 d2 = normalize(float2(-0.40, 1.0)); float k2 = _NormalScale * 2.1;
                float2 d3 = normalize(float2( 0.70,-0.70)); float k3 = _NormalScale * 3.7;
                float2 d4 = normalize(float2(-0.90,-0.20)); float k4 = _NormalScale * 5.3;
                float a1 = dot(p, d1) * k1 + t * 1.0;
                float a2 = dot(p, d2) * k2 + t * 1.4;
                float a3 = dot(p, d3) * k3 + t * 1.9;
                float a4 = dot(p, d4) * k4 + t * 2.6;
                float2 g = cos(a1) * k1 * d1 * 1.00
                         + cos(a2) * k2 * d2 * 0.60
                         + cos(a3) * k3 * d3 * 0.35
                         + cos(a4) * k4 * d4 * 0.20;
                // 着水付近ほど振幅を増す(乱れのエネルギーが下流へ減衰)
                g *= _NormalStrength * _WaveStrength * 6.0 * (1.0 + agit * _AgitStrength);
                return normalize(float3(-g.x, 1.0, -g.y));
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float mask = SAMPLE_TEXTURE2D(_MaskTex, sampler_MaskTex, IN.uv).r;
                clip(mask - 0.28);

                float2 screenUV = IN.positionHCS.xy / _ScreenParams.xy;

                // 背後シーン(川底/地形)の深度 → 水の厚み
                float rawD = SampleSceneDepth(screenUV);
                float sceneEye = LinearEyeDepth(rawD, _ZBufferParams);
                float surfEye  = LinearEyeDepth(IN.positionHCS.z, _ZBufferParams);
                float waterDepth = max(0.0, sceneEye - surfEye);

                float agit, boil;
                float2 gPlunge = PlungeGradient(IN.positionWS, agit, boil);
                float3 N = WaveNormal(IN.positionWS.xz * _NormalScale, agit);
                // 滝壺の放射波・反射波を法線へ加算
                N = normalize(float3(N.x - gPlunge.x, N.y, N.z - gPlunge.y));
                float3 V = normalize(GetCameraPositionWS() - IN.positionWS);
                float  ndv = saturate(dot(N, V));
                float  fres = pow(1.0 - ndv, _FresnelPower);

                // ---- 屈折: 波の法線で背後シーンをずらしてサンプル ----
                float2 refr = N.xz * _RefractionStrength * saturate(waterDepth * 0.5);
                float2 refrUV = screenUV + refr;
                // ずらした先が水面より手前(=水の上の物体)なら屈折を打ち消す（滲み防止）
                float sceneEyeR = LinearEyeDepth(SampleSceneDepth(refrUV), _ZBufferParams);
                if (sceneEyeR < surfEye) { refrUV = screenUV; sceneEyeR = sceneEye; }
                float refrDepth = max(0.0, sceneEyeR - surfEye);
                half3 sceneCol = SampleSceneColor(refrUV);

                // ---- 深度吸収: 浅いほど背後が透け、深いほど水色へ ----
                float dFade = saturate(refrDepth / max(0.01, _DepthFade));
                half3 shallowTint = lerp(half3(1,1,1), _ShallowColor.rgb * 1.6, 0.35);
                half3 underwater = lerp(sceneCol * shallowTint, _DeepColor.rgb, dFade);

                // ---- 反射(空/環境) ----
                float3 R = reflect(-V, N);
                half3 refl = GlossyEnvironmentReflection(R, IN.positionWS, 1.0 - _Smoothness, 1.0) * _ReflectionStrength;

                // フレネルで水面色↔反射をブレンド
                half3 col = lerp(underwater, refl, saturate(fres));

                // ---- 太陽のギラつき（鋭いスペキュラ）----
                Light ml = GetMainLight();
                float3 H = normalize(ml.direction + V);
                float glint = pow(saturate(dot(N, H)), _SunSpecPower) * _SunSpecIntensity;
                col += glint * ml.color;

                // ---- 岸際の泡 ----
                float shoreT = saturate(waterDepth / max(0.01, _ShoreWidth));
                float foam = (1.0 - shoreT) * _FoamAmount;
                // 滝壺付近は白泡が多く、下流へ向かって減衰(まだらに)
                float ap = IN.positionWS.x * 0.9 + IN.positionWS.z * 0.7;
                float churn = 0.5 + 0.5 * sin(ap * 1.7 + _Time.y * 2.3) * sin(ap * 0.8 - _Time.y * 1.4);
                float churn2 = 0.5 + 0.5 * sin(ap * 4.3 - _Time.y * 3.1) * sin(ap * 2.6 + _Time.y * 2.0);
                // 直下のボイル(湧き上がり)は最も白い
                foam = saturate(foam + agit * _AgitFoam * churn + boil * _AgitFoam * 1.15 * churn2);
                col = lerp(col, half3(0.92, 0.95, 0.97), foam);

                // 深い所はほぼ不透明(背後は自前で合成済み)、岸際はやわらかく透過
                float a = saturate(lerp(0.55, 1.0, shoreT) + fres * 0.15) * _Alpha;
                return half4(col, a);
            }
            ENDHLSL
        }
    }
    FallBack "Universal Render Pipeline/Unlit"
}
