using UnityEngine;
using UnityEngine.InputSystem;

/// <summary>
/// 実寸(1 unit = 1 m)の一人称コントローラ。
/// 目線1.6m、歩行~1.4m/s(走り~3.3m/s)。新Input System(Keyboard/Mouse.current)を使用。
/// CharacterController + 子Camera(目線) が前提。WASD移動 / マウス視点 / LeftShiftで走る / Escでカーソル解放。
/// </summary>
[RequireComponent(typeof(CharacterController))]
public class FirstPersonController : MonoBehaviour
{
    [Header("移動 (m/s) ― 江戸の徒歩を基準に実寸")]
    public float walkSpeed = 1.4f;
    public float runSpeed = 3.3f;
    public float gravity = -9.81f;

    [Header("視点")]
    public Transform cam;                 // 目線となる子カメラ
    public float mouseSensitivity = 0.08f; // ~deg/pixel
    public float pitchClamp = 85f;

    CharacterController cc;
    float pitch;
    float vSpeed;

    void Awake()
    {
        cc = GetComponent<CharacterController>();
        if (cam == null)
        {
            var c = GetComponentInChildren<Camera>();
            if (c != null) cam = c.transform;
        }
    }

    void OnEnable()
    {
        Cursor.lockState = CursorLockMode.Locked;
        Cursor.visible = false;
    }

    void Update()
    {
        var kb = Keyboard.current;
        if (kb == null) return;
        var mouse = Mouse.current;

        // --- 視点(マウス) ---
        if (mouse != null && Cursor.lockState == CursorLockMode.Locked)
        {
            Vector2 d = mouse.delta.ReadValue() * mouseSensitivity;
            transform.Rotate(Vector3.up, d.x, Space.Self);
            pitch = Mathf.Clamp(pitch - d.y, -pitchClamp, pitchClamp);
            if (cam != null) cam.localRotation = Quaternion.Euler(pitch, 0f, 0f);
        }

        // --- 移動(WASD) ---
        float x = (kb.aKey.isPressed ? -1f : 0f) + (kb.dKey.isPressed ? 1f : 0f);
        float z = (kb.sKey.isPressed ? -1f : 0f) + (kb.wKey.isPressed ? 1f : 0f);
        Vector3 dir = transform.right * x + transform.forward * z;
        if (dir.sqrMagnitude > 1f) dir.Normalize();
        float speed = kb.leftShiftKey.isPressed ? runSpeed : walkSpeed;

        // --- 重力 / 接地 ---
        if (cc.isGrounded && vSpeed < 0f) vSpeed = -2f;
        vSpeed += gravity * Time.deltaTime;

        Vector3 vel = dir * speed + Vector3.up * vSpeed;
        cc.Move(vel * Time.deltaTime);

        // 確認用: Escでカーソルを解放 / クリックで再ロック
        if (kb.escapeKey.wasPressedThisFrame)
        {
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }
        if (mouse != null && mouse.leftButton.wasPressedThisFrame && Cursor.lockState != CursorLockMode.Locked)
        {
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
        }
    }
}
