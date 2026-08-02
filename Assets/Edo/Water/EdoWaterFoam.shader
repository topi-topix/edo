Shader "Edo/WaterFoam"
{
    // 滝壺の churn 泡（水平パッチ）。手続き的な白い泡が湧いて流れる。外部テクスチャ不要。
    // UV: xを幅, yを滝からの距離(0=滝直下 ->1=下流) として使うと自然。
    Properties
    {
        _FoamColor ("Foam Color", Color) = (1,1,1,0.9)
        _Speed     ("Churn Speed", Float) = 1.3
        _Scale     ("Foam Scale", Float) = 7
        _Coverage  ("Coverage", Range(0,1)) = 0.55
        _Softness  ("Edge Softness", Range(0.01,0.5)) = 0.18
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent+11" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "ForwardFoam"
            Tags { "LightMode"="UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings   { float4 positionHCS : SV_POSITION; float2 uv : TEXCOORD0; };

            CBUFFER_START(UnityPerMaterial)
                float4 _FoamColor; float _Speed; float _Scale; float _Coverage; float _Softness;
            CBUFFER_END

            float hash2(float2 p){ return frac(sin(dot(p,float2(41.3,289.1)))*43758.5453); }
            float vnoise(float2 p){
                float2 i=floor(p), f=frac(p); f=f*f*(3.0-2.0*f);
                float a=hash2(i), b=hash2(i+float2(1,0)), c=hash2(i+float2(0,1)), d=hash2(i+float2(1,1));
                return lerp(lerp(a,b,f.x), lerp(c,d,f.x), f.y);
            }
            float fbm(float2 p){ float s=0,a=0.5; [unroll] for(int i=0;i<4;i++){ s+=a*vnoise(p); p*=2.03; a*=0.5; } return s; }

            Varyings vert(Attributes IN){ Varyings o; o.positionHCS=TransformObjectToHClip(IN.positionOS.xyz); o.uv=IN.uv; return o; }

            half4 frag(Varyings IN):SV_Target
            {
                float2 uv=IN.uv; float t=_Time.y*_Speed;
                // 滝直下(y小)ほど泡が濃い。下流(y大)へ流れて薄れる。
                float2 p=float2(uv.x*_Scale, uv.y*_Scale - t);       // 下流方向へスクロール
                float n=fbm(p) * 0.6 + fbm(p*2.1 + t*0.5)*0.4;
                float nearFall = smoothstep(1.0, 0.0, uv.y);          // 直下で強い
                float th = _Coverage * (0.5 + 0.9*nearFall);
                float foam = smoothstep(th-_Softness, th+_Softness, n);
                half4 col=_FoamColor;
                col.a *= foam * smoothstep(0.0,0.06,uv.x)*smoothstep(1.0,0.94,uv.x) * smoothstep(1.0,0.6,uv.y);
                return col;
            }
            ENDHLSL
        }
    }
}
