Shader "Edo/WorldGrid"
{
    // ワールドXZ平面に実寸グリッドを描くURP Unlitシェーダ。
    // 江戸の寸法体系: 既定で 1間=1.818m を細線、10間=18.18m を太線で表示。
    Properties
    {
        _BaseColor  ("Ground Color", Color) = (0.16, 0.18, 0.14, 1)
        _LineColor  ("Minor Line (1 ken)", Color) = (0.32, 0.38, 0.28, 1)
        _MajorColor ("Major Line (10 ken)", Color) = (0.62, 0.78, 0.52, 1)
        _Minor      ("Minor Spacing m (1 ken)", Float) = 1.818
        _Major      ("Major Spacing m (10 ken)", Float) = 18.18
        _LineWidth  ("Minor Line Width m", Float) = 0.03
        _MajorWidth ("Major Line Width m", Float) = 0.08
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionHCS : SV_POSITION; float3 positionWS : TEXCOORD0; };

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseColor;
                float4 _LineColor;
                float4 _MajorColor;
                float _Minor;
                float _Major;
                float _LineWidth;
                float _MajorWidth;
            CBUFFER_END

            Varyings vert (Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs p = GetVertexPositionInputs(IN.positionOS.xyz);
                OUT.positionHCS = p.positionCS;
                OUT.positionWS  = p.positionWS;
                return OUT;
            }

            // 最寄りの格子線までの距離(m)からアンチエイリアスした線を返す
            float gridLine (float2 coord, float spacing, float width)
            {
                float2 g  = abs(frac(coord / spacing - 0.5) - 0.5) * spacing;
                float2 fw = fwidth(coord);
                float2 ln = 1.0 - smoothstep(float2(0,0), fw + width, g);
                return max(ln.x, ln.y);
            }

            half4 frag (Varyings IN) : SV_Target
            {
                float2 xz    = IN.positionWS.xz;
                float minor  = gridLine(xz, _Minor, _LineWidth);
                float major  = gridLine(xz, _Major, _MajorWidth);
                float3 col   = _BaseColor.rgb;
                col = lerp(col, _LineColor.rgb,  minor);
                col = lerp(col, _MajorColor.rgb, major);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
}
