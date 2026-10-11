using System.Collections;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;
using UnityEngine.TextCore.Text;
using UnityEngine.UIElements;

/// <summary>
/// アプリの流れ — 開始画面 → (操作の説明)→ 読み込み → 歩く ⇄ 一時停止(EDO-0450)。
///
/// ・アプリの最初の一枚(Boot)に置き、以後はシーンをまたいで生き残る(一つだけ)。画面は UI Toolkit の一枚
///   (<c>Assets/Edo/UI/EdoApp.uxml</c>)を重ね、四つの画面を出し入れする。
/// ・**赤坂は開始画面を出した瞬間から裏で読む**(<see cref="AsyncOperation.allowSceneActivation"/> = false で 90% まで)。
///   「はじめる」で残りの組み立てだけ待つ。読み込みの棒は Unity の進み(大きな一枚だと長く 0 に張り付く)と、
///   前回かかった秒数(PlayerPrefs)の大きい方で進める。
/// ・Esc で一時停止: 時間を止め、主人公の入力を切り、マウスの矢印を戻す。
/// ・字は OS の日本語書体(Mac=ヒラギノ / Windows=游ゴシック・メイリオ)から起こす — 書体ファイルを抱えない。
/// ⚠ エディタで赤坂を直に ▶ した時はこの流れが居ないので、今まで通り(一時停止なし)。
/// </summary>
[RequireComponent(typeof(UIDocument))]
public class EdoAppFlow : MonoBehaviour
{
    [Tooltip("歩く本番のシーン名(書き出し一覧に入っていること)")]
    public string sceneName = "Akasaka";
    [Tooltip("開始画面の背景(Edo/書き出し/開始画面の絵を撮る)。無ければ無地")]
    public Texture2D titleImage;

    public static EdoAppFlow Instance { get; private set; }
    /// <summary>一時停止・説明・開始画面のあいだ true — 主人公の側のキー(V など)はこれを見て黙る。</summary>
    public static bool BlocksGameplay => Instance != null && Instance.state != State.Playing;

    enum State { Title, Help, Loading, Playing, Paused }
    State state = State.Title, helpReturn = State.Title;

    const string LastLoadKey = "EdoApp.lastLoadSeconds";
    const int BootSceneIndex = 0;

    VisualElement titleScreen, helpScreen, loadingScreen, pauseScreen, loadingFill;
    Label preloadLabel, loadingState, loadingTime;

    AsyncOperation load;
    float loadStart, lastLoadSeconds;
    bool activating;

    // ── 生まれと UI の結線 ────────────────────────────────────────────

    void Awake()
    {
        // 開始画面へ戻ると Boot がもう一つ生む — 先に居る方が続けるので、新しい方は UI を結ぶ前に消える
        if (Instance != null && Instance != this) { gameObject.SetActive(false); Destroy(gameObject); return; }
        Instance = this;
        DontDestroyOnLoad(gameObject);
        lastLoadSeconds = PlayerPrefs.GetFloat(LastLoadKey, 0f);
    }

    void OnDestroy() { if (Instance == this) Instance = null; }

    void OnEnable()
    {
        var root = GetComponent<UIDocument>().rootVisualElement;
        titleScreen   = root.Q("title-screen");
        helpScreen    = root.Q("help-screen");
        loadingScreen = root.Q("loading-screen");
        pauseScreen   = root.Q("pause-screen");
        loadingFill   = root.Q("loading-fill");
        preloadLabel  = root.Q<Label>("title-preload");
        loadingState  = root.Q<Label>("loading-state");
        loadingTime   = root.Q<Label>("loading-time");

        root.Q<Button>("title-start").clicked  += StartGame;
        root.Q<Button>("title-help").clicked   += OpenHelp;
        root.Q<Button>("title-quit").clicked   += Quit;
        root.Q<Button>("help-back").clicked    += CloseHelp;
        root.Q<Button>("pause-resume").clicked += Resume;
        root.Q<Button>("pause-help").clicked   += OpenHelp;
        root.Q<Button>("pause-title").clicked  += BackToTitle;
        root.Q<Button>("pause-quit").clicked   += Quit;

        var font = JapaneseFont();
        if (font != null) root.style.unityFontDefinition = new StyleFontDefinition(FontDefinition.FromSDFFont(font));
        if (titleImage != null)
        {
            var bg = new StyleBackground(titleImage);
            root.Q("title-bg").style.backgroundImage = bg;
            root.Q("loading-bg").style.backgroundImage = bg;
        }
    }

    void Start()
    {
        if (Instance != this) return;
        ShowTitle();
        StartPreload();
    }

    // ── 状態の出し入れ ─────────────────────────────────────────────

    void Show(VisualElement screen, Button focus = null)
    {
        foreach (var s in new[] { titleScreen, helpScreen, loadingScreen, pauseScreen })
            s.EnableInClassList("screen--shown", s == screen);
        focus?.schedule.Execute(() => focus.Focus());
    }

    void ShowTitle()
    {
        state = State.Title;
        SetCursorFree(true);
        Show(titleScreen, titleScreen.Q<Button>("title-start"));
    }

    void OpenHelp()
    {
        helpReturn = state;
        state = State.Help;
        Show(helpScreen, helpScreen.Q<Button>("help-back"));
    }

    void CloseHelp()
    {
        if (helpReturn == State.Paused) { state = State.Paused; Show(pauseScreen, pauseScreen.Q<Button>("pause-resume")); }
        else ShowTitle();
    }

    void StartGame()
    {
        if (state != State.Title) return;
        state = State.Loading;
        Show(loadingScreen);
        if (load == null) StartPreload();
        StartCoroutine(FinishLoading());
    }

    void Pause()
    {
        state = State.Paused;
        Time.timeScale = 0f;
        AudioListener.pause = true;
        SetGameplayInput(false);
        Show(pauseScreen, pauseScreen.Q<Button>("pause-resume"));
    }

    void Resume()
    {
        state = State.Playing;
        Time.timeScale = 1f;
        AudioListener.pause = false;
        Show(null);
        SetGameplayInput(true);
    }

    void BackToTitle()
    {
        Time.timeScale = 1f;
        AudioListener.pause = false;
        ShowTitle();
        StartCoroutine(ReloadTitle());
    }

    void Quit()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.ExitPlaymode();
#else
        Application.Quit();
#endif
    }

    void Update()
    {
        var kb = Keyboard.current;
        if (kb != null && kb.escapeKey.wasPressedThisFrame)
        {
            if (state == State.Playing) Pause();
            else if (state == State.Paused) Resume();
            else if (state == State.Help) CloseHelp();
        }

        if (state == State.Title) UpdatePreloadLabel();
        else if (state == State.Loading) UpdateLoadingScreen();
    }

    // ── 読み込み ──────────────────────────────────────────────────

    void StartPreload()
    {
        loadStart = Time.realtimeSinceStartup;
        activating = false;
        load = SceneManager.LoadSceneAsync(sceneName, LoadSceneMode.Single);
        load.allowSceneActivation = false;
    }

    IEnumerator FinishLoading()
    {
        while (load.progress < 0.9f) yield return null;
        activating = true;
        UpdateLoadingScreen();
        yield return null;                         // 「組み立てています」を一度描いてから固まる
        load.allowSceneActivation = true;
        while (!load.isDone) yield return null;
        lastLoadSeconds = Time.realtimeSinceStartup - loadStart;
        PlayerPrefs.SetFloat(LastLoadKey, lastLoadSeconds);
        PlayerPrefs.Save();
        load = null;
        yield return null;                         // 赤坂の最初の絵が出てから幕を上げる
        state = State.Playing;
        Show(null);
        SetGameplayInput(true);
    }

    IEnumerator ReloadTitle()
    {
        load = null;
        var op = SceneManager.LoadSceneAsync(BootSceneIndex, LoadSceneMode.Single);
        while (!op.isDone) yield return null;
        yield return Resources.UnloadUnusedAssets();   // 赤坂の分のメモリを返してから読み直す(8GB の機械)
        System.GC.Collect();
        StartPreload();
    }

    float Fraction()
    {
        float real = load == null ? 1f : Mathf.Clamp01(load.progress / 0.9f);
        if (lastLoadSeconds <= 0f) return real;
        float byTime = (Time.realtimeSinceStartup - loadStart) / lastLoadSeconds;
        return Mathf.Max(real, Mathf.Min(0.97f, byTime));
    }

    void UpdatePreloadLabel()
    {
        if (load == null) { preloadLabel.text = ""; return; }
        preloadLabel.text = load.progress >= 0.9f ? "町の用意ができました" : $"町を読み込んでいます  {Mathf.FloorToInt(Fraction() * 100)}%";
    }

    void UpdateLoadingScreen()
    {
        float f = Fraction();
        loadingFill.style.width = Length.Percent(f * 100f);
        loadingState.text = activating ? "町を組み立てています" : $"読み込み中  {Mathf.FloorToInt(f * 100)}%";
        float elapsed = Time.realtimeSinceStartup - loadStart;
        loadingTime.text = lastLoadSeconds > 0f
            ? (elapsed < lastLoadSeconds ? $"残り 約 {Clock(lastLoadSeconds - elapsed)}" : $"経過 {Clock(elapsed)}(前回は {Clock(lastLoadSeconds)})")
            : $"経過 {Clock(elapsed)}(初回は数分かかります)";
    }

    static string Clock(float sec)
    {
        int s = Mathf.Max(0, Mathf.RoundToInt(sec));
        return $"{s / 60}:{s % 60:00}";
    }

    // ── 主人公の入力とマウス ───────────────────────────────────────────

    /// <summary>主人公の入力を入れる/切る。切るときは押しっぱなしの値を消し、マウスの矢印を戻す。</summary>
    static void SetGameplayInput(bool on)
    {
        foreach (var pi in FindObjectsByType<PlayerInput>(FindObjectsSortMode.None)) pi.enabled = on;
        foreach (var inp in FindObjectsByType<StarterAssets.StarterAssetsInputs>(FindObjectsSortMode.None))
        {
            inp.cursorLocked = on;
            if (!on) { inp.move = Vector2.zero; inp.look = Vector2.zero; inp.jump = false; inp.sprint = false; }
        }
        SetCursorFree(!on);
    }

    static void SetCursorFree(bool free)
    {
        UnityEngine.Cursor.lockState = free ? CursorLockMode.None : CursorLockMode.Locked;
        UnityEngine.Cursor.visible = free;
    }

    // ── 字 ──────────────────────────────────────────────────────

    static readonly (string family, string style)[] JapaneseFaces =
    {
        ("Hiragino Sans", "W3"), ("Hiragino Kaku Gothic ProN", "W3"),   // Mac
        ("Yu Gothic UI", "Regular"), ("Meiryo", "Regular"),             // Windows
    };

    static FontAsset JapaneseFont()
    {
        foreach (var (family, style) in JapaneseFaces)
        {
            var fa = FontAsset.CreateFontAsset(family, style);
            if (fa != null) return fa;
        }
        Debug.LogWarning("[開始画面] 日本語の書体が OS に見つからない — 既定の書体で出す");
        return null;
    }
}
