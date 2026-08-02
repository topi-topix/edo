Shader "Edo/Waterfall"
{
    // 手続き的な滝（流れ落ちる水）。外部テクスチャ不要。
    // UV: x=幅方向(0..1) / y=0(天端側) -> 1(滝壺)。時間でストリークを下方向へスクロール。
    Properties
    {
        _TopColor   ("Water Color",  Color) = (0.62,0.78,0.86,0.40)
        _DeepColor  ("Deep Tint",    Color) = (0.28,0.46,0.58,0.70)
        _FoamColor  ("Foam Color",   Color) = (1,1,1,1)
        _FlowSpeed  ("Flow Speed",   Float) = 3.0
        _StreakScale("Streak Density", Float) = 22
        _StreakSharp("Streak Sharpness", Range(1,12)) = 4
        _Wobble     ("Streak Wobble", Range(0,0.3)) = 0.006
        _Alpha      ("Max Alpha", Range(0,1)) = 0.9
        _CrestFoam  ("Foam At Crest", Range(0,1)) = 0.10
        _PlungeFoam ("Foam At Plunge", Range(0,1)) = 0.42
        _Aerate     ("Aeration (白濁)", Range(0,1)) = 0.55
        _RimPower   ("Rim / 厚み感", Range(0.5,6)) = 2.2
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent+10" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "ForwardWaterfall"
            Tags { "LightMode"="UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings   { float4 positionHCS : SV_POSITION; float2 uv : TEXCOORD0; float3 nWS : TEXCOORD1; float3 vWS : TEXCOORD2; };

            CBUFFER_START(UnityPerMaterial)
                float4 _TopColor;
                float4 _DeepColor;
                float4 _FoamColor;
                float  _FlowSpeed;
                float  _StreakScale;
                float  _StreakSharp;
                float  _Wobble;
                float  _Alpha;
                float  _CrestFoam;
                float  _PlungeFoam;
                float  _Aerate;
                float  _RimPower;
            CBUFFER_END

            float hash(float n){ return frac(sin(n)*43758.5453); }

            // 縦ストリーク層: 落下につれ加速して伸びる
            float streakLayer(float2 uv, float density, float t, float sharp, float seed)
            {
                float s = 0.0;
                [unroll] for(int i=0;i<3;i++)
                {
                    float off = hash(i*7.3 + seed);
                    // 滝は「まっすぐ落ちる」: 横ゆらぎはごく僅か、かつ落ち口付近だけに限定
                    float wob = _Wobble * sin(uv.y*4.0 + t*1.2 + off*13.0) * (1.0 - saturate(uv.y*1.6));
                    float col = frac((uv.x+wob)*density + off*7.0);
                    // 落下で加速: 縦に引き伸ばす(筋が長くなる)
                    float acc = pow(saturate(uv.y), 1.6);
                    float speed = 1.4 + off*1.6;
                    float band = frac(uv.y*1.4 + acc*3.4 - t*speed + off*11.0);
                    float lane = pow(saturate(1.0 - abs(col-0.5)*2.0), sharp);
                    // 縦筋は下ほど途切れず伸びる
                    float wave = lerp(0.5 + 0.5*sin(band*6.28318), 0.85, saturate(uv.y*0.8));
                    s = max(s, lane*wave);
                }
                return s;
            }

            Varyings vert(Attributes IN)
            {
                Varyings o;
                float3 pWS = TransformObjectToWorld(IN.positionOS.xyz);
                o.positionHCS = TransformWorldToHClip(pWS);
                o.uv = IN.uv;
                o.nWS = TransformObjectToWorldNormal(IN.normalOS);
                o.vWS = GetWorldSpaceViewDir(pWS);
                return o;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float2 uv = IN.uv;
                float t = _Time.y * _FlowSpeed;

                // 3オクターブ: 粗い束 / 中 / 細い糸
                float c1 = streakLayer(uv, _StreakScale*0.35, t*0.85, _StreakSharp*0.7, 1.7);
                float c2 = streakLayer(uv, _StreakScale*0.9,  t*1.15, _StreakSharp,      5.1);
                float c3 = streakLayer(uv, _StreakScale*2.2,  t*1.5,  _StreakSharp*1.4,  9.3);
                float streaks = saturate(c1*0.55 + c2*0.45 + c3*0.35);

                float fall   = saturate(uv.y);
                float crest  = smoothstep(_CrestFoam, 0.0, uv.y);        // 天端の白波
                float plunge = smoothstep(1.0-_PlungeFoam, 1.0, uv.y);   // 滝壺の砕け
                // 落下するほど空気を巻き込み白濁
                float aer = _Aerate * pow(fall, 1.3);
                float foam = saturate(streaks*(0.35+0.55*fall) + crest*0.8 + plunge*1.25 + aer*0.5);

                // 厚み感: 視線に対して立っている面ほど濃く(リム)
                float3 N = normalize(IN.nWS);
                float3 V = normalize(IN.vWS);
                float rim = pow(1.0 - saturate(abs(dot(N,V))), _RimPower);

                half4 waterCol = lerp(_DeepColor, _TopColor, streaks);
                half4 col = lerp(waterCol, _FoamColor, foam);

                // アルファ: 天端は薄く、落下で濃く、泡は濃い。リムで厚みを出す。
                float a = _Alpha * (0.18 + 0.55*fall + foam*0.55 + rim*0.35);
                // 筋の隙間は透ける
                a *= lerp(0.55, 1.0, saturate(streaks*1.4 + plunge));
                col.a = saturate(a);
                // 幅の端: 石垣に食い込ませているので細く
                col.a *= smoothstep(0.0,0.012,uv.x) * smoothstep(1.0,0.988,uv.x);
                // uv.y=0.94 が水面。そこまでは消さず、水中に入る最後だけ溶かす
                float dissolve = 1.0 - smoothstep(0.94, 1.0, uv.y);
                float br = 0.5 + 0.5*sin(uv.x*47.0 + _Time.y*1.7) * sin(uv.x*19.0 - _Time.y*1.1);
                col.a *= saturate(dissolve + br*0.45*smoothstep(1.0,0.93,uv.y));
                return col;
            }
            ENDHLSL
        }
    }
}
