using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;
using Unity.Cinemachine;

/// <summary>
/// 主人公の視点を「背後(三人称)」と「目線(一人称)」で切り替える。V キーで切替。
/// Starter Assets の ThirdPersonController + CinemachineThirdPersonFollow が前提
/// (カメラの向きは ThirdPersonController が CinemachineCameraTarget を回して決める)。
/// 目線では体を影だけにし、カメラの的を目の高さへ上げ、腕の長さを 0 にする。
/// 背後ではカメラが塀や建物にめり込まないよう、的からカメラまでを球で掃いて手前に寄せる(Cinemachine 側)。
/// </summary>
public class EdoViewSwitch : MonoBehaviour
{
    public enum View { Behind, Eyes }

    [Header("参照(空なら自動で探す)")]
    public CinemachineThirdPersonFollow follow;
    public Transform cameraTarget;          // PlayerCameraRoot
    public Renderer[] body;                 // 目線のとき影だけにする

    [Header("背後")]
    public float behindDistance = 3.5f;
    public Vector3 behindShoulder = new Vector3(0.5f, 0f, 0f);
    public float behindTargetHeight = 1.45f;

    [Header("目線(1.8m の人型で目の高さ)")]
    public float eyeHeight = 1.62f;

    public View view = View.Behind;

    void Awake()
    {
        if (follow == null) follow = FindAnyObjectByType<CinemachineThirdPersonFollow>();
        if (cameraTarget == null)
        {
            var t = transform.Find("PlayerCameraRoot");
            if (t != null) cameraTarget = t;
        }
        if (body == null || body.Length == 0) body = GetComponentsInChildren<SkinnedMeshRenderer>(true);
        Apply();
    }

    void Update()
    {
        if (EdoAppFlow.BlocksGameplay) return;   // 一時停止・開始画面のあいだは切り替えない
        var kb = Keyboard.current;
        if (kb != null && kb.vKey.wasPressedThisFrame)
        {
            view = view == View.Behind ? View.Eyes : View.Behind;
            Apply();
        }
    }

    public void Apply()
    {
        bool eyes = view == View.Eyes;
        if (follow != null)
        {
            follow.CameraDistance = eyes ? 0f : behindDistance;
            follow.ShoulderOffset = eyes ? Vector3.zero : behindShoulder;
            follow.VerticalArmLength = 0f;
            follow.Damping = eyes ? Vector3.zero : new Vector3(0.1f, 0.5f, 0.3f);
        }
        if (cameraTarget != null)
            cameraTarget.localPosition = eyes ? new Vector3(0f, eyeHeight, 0f)
                                              : new Vector3(0f, behindTargetHeight, 0f);
        if (body != null)
            foreach (var r in body)
                if (r != null) r.shadowCastingMode = eyes ? ShadowCastingMode.ShadowsOnly : ShadowCastingMode.On;
    }
}
