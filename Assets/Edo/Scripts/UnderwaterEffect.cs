using UnityEngine;

/// <summary>
/// カメラが水面下(WaterBody の水位より下＋その水域の内側)に入ると、
/// シーン深度を使ったフルスクリーンの「水中」オーバーレイ(濁り＝色吸収・コースティック光・
/// 見上げた先の水面グロー・周辺減光)＋漂う浮遊物で、実際に水の中にいる感じを出す。
/// 水面から出れば元に戻る。PlayerCamera に付ける。実行時に動作。
///
/// URPの組み込みフォグに依存せず、Edo/Underwater シェーダーで自前に水中色を合成するため
/// 確実に効く。前提: URP アセットの Depth Texture が ON。
/// </summary>
[RequireComponent(typeof(Camera))]
public class UnderwaterEffect : MonoBehaviour
{
    [Header("水中の色 / 濁り")]
    [Tooltip("深い方向・遠方の水中色")] public Color deepColor = new Color(0.03f, 0.16f, 0.19f);
    [Tooltip("コースティック光の筋の明るい水色")] public Color lightTint = new Color(0.18f, 0.44f, 0.47f);
    [Tooltip("視界がほぼ消える距離(m)。小さいほど濁る")] public float visibility = 7f;
    [Range(0f, 1f)] public float maxMurk = 0.92f;
    [Tooltip("目の前(距離0)でも乗る水中色の下限")] [Range(0f, 0.6f)] public float nearTint = 0.18f;

    [Header("光 / 演出")]
    [Range(0f, 1f)] public float causticStrength = 0.5f;
    public float causticScale = 6f;
    public float causticSpeed = 0.6f;
    [Tooltip("見上げた先(水面方向)の明るさ")] [Range(0f, 2f)] public float surfaceGlow = 0.6f;
    [Range(0f, 2f)] public float vignette = 0.6f;

    [Header("浮遊物")]
    public bool motes = true;
    [Tooltip("浮遊物の密度(1秒あたりの発生数)")] public float moteRate = 26f;

    [Header("切替")]
    [Tooltip("水面を出入りする時のフェード時間(秒)")] public float fadeTime = 0.25f;

    Camera _cam;
    Material _mat;
    GameObject _overlay;
    MeshRenderer _overlayMR;
    ParticleSystem _motes;
    float _submT;     // 0..1 に平滑化した水中度
    bool _built;

    void OnDisable()
    {
        if (_overlay) _overlay.SetActive(false);
        if (_motes) { var em = _motes.emission; em.enabled = false; }
        _submT = 0f;
    }

    void LateUpdate()
    {
        if (_cam == null) _cam = GetComponent<Camera>();
        float depth = SubmergeDepth(transform.position);
        bool under = depth > 0f;

        _submT = Mathf.MoveTowards(_submT, under ? 1f : 0f,
                                   Time.deltaTime / Mathf.Max(0.01f, fadeTime));
        bool active = _submT > 0.001f;

        EnsureBuilt();
        if (_overlay.activeSelf != active) _overlay.SetActive(active);
        if (_motes)
        {
            var em = _motes.emission;
            bool wantMotes = active && motes;
            if (em.enabled != wantMotes) em.enabled = wantMotes;
            em.rateOverTime = moteRate;
        }
        if (!active) return;

        UpdateOverlayTransform();

        float s = Mathf.SmoothStep(0f, 1f, _submT);
        // 視界距離 → 密度: 1-exp(-vis*density)=0.95 になるよう density=3/vis
        float density = 3f / Mathf.Max(0.5f, visibility);
        _mat.SetColor("_WaterColor", deepColor);
        _mat.SetColor("_ShallowTint", lightTint);
        _mat.SetFloat("_Density", density);
        _mat.SetFloat("_MaxMurk", maxMurk);
        _mat.SetFloat("_NearTint", nearTint);
        _mat.SetFloat("_CausticStrength", causticStrength);
        _mat.SetFloat("_CausticScale", causticScale);
        _mat.SetFloat("_CausticSpeed", causticSpeed);
        _mat.SetFloat("_SurfaceGlow", surfaceGlow);
        _mat.SetFloat("_Vignette", vignette);
        _mat.SetFloat("_Submersion", s);
    }

    // ---- 水中判定: どれかの WaterBody の水位より下 かつ 輪郭の内側なら、その潜り深さ(>0) ----
    static float SubmergeDepth(Vector3 p)
    {
#if UNITY_2023_1_OR_NEWER
        var bodies = Object.FindObjectsByType<WaterBody>(FindObjectsSortMode.None);
#else
        var bodies = Object.FindObjectsOfType<WaterBody>();
#endif
        float best = 0f;
        foreach (var wb in bodies)
            if (p.y < wb.waterY && InOutline(wb, p))
                best = Mathf.Max(best, wb.waterY - p.y);
        return best;
    }

    static bool InOutline(WaterBody wb, Vector3 p)
    {
        if (wb.outline == null || wb.outline.Count < 3) return false;
        bool inside = false; int n = wb.outline.Count;
        for (int i = 0, j = n - 1; i < n; j = i++)
        {
            Vector3 a = wb.outline[i], b = wb.outline[j];
            if (((a.z > p.z) != (b.z > p.z)) &&
                (p.x < (b.x - a.x) * (p.z - a.z) / (b.z - a.z) + a.x))
                inside = !inside;
        }
        return inside;
    }

    // ---- オーバーレイのクワッドを毎フレーム near plane にフィットさせる ----
    void UpdateOverlayTransform()
    {
        float d = _cam.nearClipPlane * 1.5f + 0.01f;
        float halfH = d * Mathf.Tan(_cam.fieldOfView * 0.5f * Mathf.Deg2Rad) * 1.25f;
        float halfW = halfH * _cam.aspect;
        _overlay.transform.localPosition = new Vector3(0f, 0f, d);
        _overlay.transform.localRotation = Quaternion.identity;
        _overlay.transform.localScale = new Vector3(halfW * 2f, halfH * 2f, 1f);
    }

    void EnsureBuilt()
    {
        if (_built && _overlay != null) return;

        var sh = Shader.Find("Edo/Underwater");
        _mat = new Material(sh) { hideFlags = HideFlags.HideAndDontSave };

        _overlay = new GameObject("UnderwaterOverlay") { hideFlags = HideFlags.HideAndDontSave };
        _overlay.transform.SetParent(transform, false);
        var mf = _overlay.AddComponent<MeshFilter>();
        mf.sharedMesh = BuildQuad();
        _overlayMR = _overlay.AddComponent<MeshRenderer>();
        _overlayMR.sharedMaterial = _mat;
        _overlayMR.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        _overlayMR.receiveShadows = false;
        _overlayMR.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off;
        _overlay.SetActive(false);

        BuildMotes();
        _built = true;
    }

    static Mesh BuildQuad()
    {
        var m = new Mesh { name = "UnderwaterQuad", hideFlags = HideFlags.HideAndDontSave };
        m.vertices = new[] {
            new Vector3(-0.5f,-0.5f,0f), new Vector3(-0.5f,0.5f,0f),
            new Vector3( 0.5f, 0.5f,0f), new Vector3( 0.5f,-0.5f,0f)
        };
        m.uv = new[] { new Vector2(0,0), new Vector2(0,1), new Vector2(1,1), new Vector2(1,0) };
        m.triangles = new[] { 0, 1, 2, 0, 2, 3 };
        m.bounds = new Bounds(Vector3.zero, Vector3.one * 10f);
        return m;
    }

    void BuildMotes()
    {
        var go = new GameObject("UnderwaterMotes") { hideFlags = HideFlags.HideAndDontSave };
        go.transform.SetParent(transform, false);
        go.transform.localPosition = Vector3.zero;
        _motes = go.AddComponent<ParticleSystem>();

        var main = _motes.main;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.startLifetime = 9f;
        main.startSpeed = 0.05f;
        main.startSize = new ParticleSystem.MinMaxCurve(0.015f, 0.05f);
        main.startColor = new Color(0.8f, 0.9f, 0.9f, 0.16f);
        main.maxParticles = 260;
        main.gravityModifier = -0.01f; // ごくゆっくり上昇

        var em = _motes.emission; em.rateOverTime = moteRate; em.enabled = false;

        var shape = _motes.shape;
        shape.shapeType = ParticleSystemShapeType.Box;
        shape.scale = new Vector3(12f, 7f, 12f);

        var vel = _motes.velocityOverLifetime;
        vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
        vel.x = new ParticleSystem.MinMaxCurve(-0.03f, 0.03f);
        vel.y = new ParticleSystem.MinMaxCurve(-0.02f, 0.02f);
        vel.z = new ParticleSystem.MinMaxCurve(-0.03f, 0.03f);

        var col = _motes.colorOverLifetime; // 端でフェードして自然に
        col.enabled = true;
        var grad = new Gradient();
        grad.SetKeys(
            new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
            new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.2f),
                    new GradientAlphaKey(1f, 0.8f), new GradientAlphaKey(0f, 1f) });
        col.color = grad;

        var r = go.GetComponent<ParticleSystemRenderer>();
        r.renderMode = ParticleSystemRenderMode.Billboard;
        // 専用のソフト半透明シェーダー(丸いスプライト×頂点カラー)。四角い不透明粒を防ぐ。
        r.material = new Material(Shader.Find("Edo/Mote")) { hideFlags = HideFlags.HideAndDontSave };
        r.material.mainTexture = MoteSprite();
        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        r.receiveShadows = false;
        r.sortingFudge = -5f;
    }

    static Texture2D _sprite;
    static Texture2D MoteSprite()
    {
        if (_sprite != null) return _sprite;
        const int S = 16;
        _sprite = new Texture2D(S, S, TextureFormat.RGBA32, false)
        { hideFlags = HideFlags.HideAndDontSave, wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
        for (int y = 0; y < S; y++)
            for (int x = 0; x < S; x++)
            {
                float dx = (x + 0.5f) / S - 0.5f, dy = (y + 0.5f) / S - 0.5f;
                float d = Mathf.Sqrt(dx * dx + dy * dy) * 2f;   // 0=中心, 1=縁
                float a = Mathf.SmoothStep(1f, 0f, d);          // なめらかな円形フェード
                _sprite.SetPixel(x, y, new Color(1f, 1f, 1f, a));
            }
        _sprite.Apply();
        return _sprite;
    }
}
