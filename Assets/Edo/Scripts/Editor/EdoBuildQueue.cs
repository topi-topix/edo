// EdoBuildQueue.cs — 長い建て直しを MCP の 1 回の呼び出しの中で回さず、エディタの中で順に予約して即座に返す(EDO-0503)。
//
// ⛔ 2026-10-03 の事故: execute_code の中で BuildParcel を 21 区画まわし(約 9 分)、MCP が応答の時間切れを見て
//    **同じ命令を自動で送り直し**、建て直しが 3 巡くり返して CPU 100% のまま止まらなくなった(施主が Unity を再起動)。
//    1 区画でも 30 秒を超えると同じことが起きる(樹下の建て直しで 2 回走った)。
// ⭐ 作法: execute_code では `EdoBuildQueue.Enqueue(<log の置き場>, "id1", "id2", ...)` を呼ぶだけ。呼び出しは即座に返り、
//    建て直しはエディタの update で 1 区画ずつ流れる。各区画の log は <置き場>/<id>.txt、様子は <置き場>/_state.json、
//    終わると <置き場>/_done。待つのは `python3 Tools/Unity/build_queue_wait.py <置き場>` の一手(Unity へ問い合わせを重ねない)。
//    見張り: .claude/hooks/edo_mcp_long_guard.py が BuildParcel の直呼びを止める。
//
// ⛔ 2026-10-03 の二つ目の事故(EDO-0517): 初版は EditorApplication.delayCall で次の手を積んでいた。
//    ① delayCall は全員で一本の使い捨ての列。コンパイル直後の起動では MCP の橋ほか約 35 件の初期化と一緒に
//      15 分以上流れず、Enqueue から 7 分 Remaining=1 のまま(update は回っていた)。列の手前の誰かが例外を投げても
//      後ろの手は捨てられる。
//    ② 予約は static の変数だけに在ったので、途中で再読み込み(部材の再取り込み・他の窓の C# の保存)が走ると消え、
//      _done が永久に出ない。
// ⭐ 恒久策(Unity の定石・MCP for Unity が #1229 で採った形と同じ):
//    - 次の手は **EditorApplication.update の拍**で打つ。[InitializeOnLoad] が再読み込みのたびに拍を付け直す。
//    - 予約は **SessionState** に置く(再読み込みを越え、エディタを閉じると消える = 落ちた後に勝手に蘇らない)。
//    - 1 区画を建てる間は **LockReloadAssemblies** で再読み込みを待たせる(区画と区画の間では再読み込みを通す)。
//      建てている最中に落ちた区画は再読み込みの後にもう一度だけ建て直す(BuildParcel は造成前の地盤から起こすので冪等)。
//    - コンパイル中・取り込み中・再生中は打たない。背面で拍が粗くなるので QueuePlayerLoopUpdate で一度ずつ起こす。
//    - 予約の流れだけを検めるときは区画の代わりに "~dry:<秒>" を積む(何も建てずに眠るだけ)。
//    - 進み具合は Unity の Background Tasks(右下)にも出し、そこから止められる。止めるのは `EdoBuildQueue.Cancel()` でも同じ。

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class EdoBuildQueue
{
    const string Key = "EdoBuildQueue.State";
    const int MaxAttempts = 2;      // 建てている最中に落ちた区画を建て直す回数の上限(初回を含む)
    const double BeatSec = 5.0;     // 待っている間に _state.json を書き直す間隔

    [Serializable]
    class State
    {
        public string dir;
        public List<string> ids = new List<string>();     // まだ建てていない区画
        public List<string> done = new List<string>();    // 済んだ区画(id: 結果の頭)
        public string current = "";                        // 建てている区画(空なら無し)
        public int attempts;
        public int total;
        public int failed;
        public bool cancel;
        public int progressId = -1;   // Background Tasks の項目(-1 なら無し)
        public string queuedAt;
    }

    [Serializable]
    class Beat
    {
        public string phase, current, beat, queuedAt;
        public int remaining, total, failed;
        public List<string> done;
    }

    static State _s;
    static bool _busy;
    static bool _reloading;     // 再読み込みに入った ── この間に来る取り消しは Unity が項目を畳む手であって施主の手ではない
    static double _lastBeat;

    static EdoBuildQueue()
    {
        // ⭐ 再読み込みのたびにここを通る ── 拍を付け直し、SessionState から予約を拾い直す
        EditorApplication.update -= Tick;
        EditorApplication.update += Tick;
        AssemblyReloadEvents.beforeAssemblyReload += () => _reloading = true;
        _s = Load();
        if (_s != null) { AttachProgress(); Nudge(); }
    }

    /// <summary>区画の建て直しを予約する。既に流れている予約があれば断る(二重に流さない)。</summary>
    public static string Enqueue(string logDir, params string[] ids)
    {
        if (_s != null) return "⛔ 前の予約が流れている(残り " + Remaining + ")── 終わってから";
        if (ids == null || ids.Length == 0) return "⛔ 区画が無い";
        Directory.CreateDirectory(logDir);
        var done = Path.Combine(logDir, "_done"); if (File.Exists(done)) File.Delete(done);
        _s = new State { dir = logDir, ids = new List<string>(ids), total = ids.Length, queuedAt = Now() };
        File.WriteAllText(Path.Combine(logDir, "_queued"), _s.queuedAt + " " + string.Join(" ", ids));
        AttachProgress();
        Save("queued");
        Nudge();
        return "queued " + ids.Length;
    }

    /// <summary>流れている予約の残り(建てている区画を含む・0 なら空き)。</summary>
    public static int Remaining { get { return _s == null ? 0 : _s.ids.Count + (string.IsNullOrEmpty(_s.current) ? 0 : 1); } }

    /// <summary>流れている予約を止める。建てている区画は建て終えてから止まる。</summary>
    public static string Cancel()
    {
        if (_s == null) return "— 予約は無い";
        _s.cancel = true; Save("canceling"); Nudge();
        return "canceling(残り " + Remaining + ")";
    }

    /// <summary>今の様子を一行で。</summary>
    public static string Status()
    {
        if (_s == null) return "— 予約は無い";
        return (string.IsNullOrEmpty(_s.current) ? "待ち" : "建てている " + _s.current) +
               " / 済 " + _s.done.Count + " / 残り " + _s.ids.Count + " / 失敗 " + _s.failed + (_s.cancel ? " / 止め中" : "");
    }

    [MenuItem("Edo/普請/建て直しの予約: 様子", false, 320)]
    static void MenuStatus() { Debug.Log("[EdoBuildQueue] " + Status()); }

    [MenuItem("Edo/普請/建て直しの予約: 止める", false, 321)]
    static void MenuCancel() { Debug.Log("[EdoBuildQueue] " + Cancel()); }

    static void Tick()
    {
        if (_s == null || _busy) return;
        try
        {
            if (EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode)
            { Heartbeat("waiting-editor"); return; }

            if (_s.cancel) { Finish("canceled"); return; }

            if (!string.IsNullOrEmpty(_s.current))
            {
                // 建てている最中に再読み込み・例外で抜けた区画。上限までは建て直す
                if (_s.attempts >= MaxAttempts)
                {
                    WriteLog(_s.current, "⛔ 建てている最中に " + _s.attempts + " 回落ちた ── 飛ばす", 0);
                    _s.done.Add(_s.current + ": interrupted"); _s.failed++; _s.current = ""; _s.attempts = 0;
                    Save("running"); return;
                }
            }
            else
            {
                if (_s.ids.Count == 0) { Finish("ok"); return; }
                _s.current = _s.ids[0]; _s.ids.RemoveAt(0); _s.attempts = 0;
            }
            _s.attempts++;
            Save("building");   // ⭐ 建てる前に書く ── 途中で落ちても何を建てていたかが残る
            RunOne(_s.current);
        }
        catch (Exception ex) { Debug.LogException(ex); }
    }

    static void RunOne(string id)
    {
        string r; var sw = System.Diagnostics.Stopwatch.StartNew();
        _busy = true;
        EditorApplication.LockReloadAssemblies();
        try { r = id.StartsWith(DryPrefix) ? Dry(id) : EdoTypologyBuilder.BuildParcel(id, true); }
        catch (Exception ex) { r = "EXC " + ex; }
        finally { EditorApplication.UnlockReloadAssemblies(); _busy = false; }
        if (_s == null) return;
        bool bad = r == null || r.StartsWith("EXC") || r.StartsWith("⛔");
        WriteLog(id, (r ?? "null") + (_s.attempts > 1 ? "\n(建て直し " + _s.attempts + " 回目)" : ""), sw.Elapsed.TotalSeconds);
        _s.done.Add(id + ": " + (bad ? "fail" : "ok")); if (bad) _s.failed++;
        _s.current = ""; _s.attempts = 0;
        Save("running");
        Nudge();
    }

    static void Finish(string how)
    {
        var s = _s; _s = null;
        SessionState.EraseString(Key);
        var body = Now() + " " + how + " ok=" + (s.done.Count - s.failed) + " fail=" + s.failed + " skipped=" + s.ids.Count +
                   (string.IsNullOrEmpty(s.current) ? "" : " (止めた時に途中: " + s.current + ")");
        WriteBeat(s, how);
        File.WriteAllText(Path.Combine(s.dir, "_done"), body);
        if (s.progressId >= 0 && Progress.Exists(s.progressId))
            Progress.Finish(s.progressId, how == "ok" && s.failed == 0 ? Progress.Status.Succeeded
                                        : how == "canceled" ? Progress.Status.Canceled : Progress.Status.Failed);
        Debug.Log("[EdoBuildQueue] " + body);
    }

    // ── 記録 ──

    static State Load()
    {
        var j = SessionState.GetString(Key, "");
        if (string.IsNullOrEmpty(j)) return null;
        try { return JsonUtility.FromJson<State>(j); } catch { SessionState.EraseString(Key); return null; }
    }

    static void Save(string phase)
    {
        SessionState.SetString(Key, JsonUtility.ToJson(_s));
        WriteBeat(_s, phase);
        if (_s.progressId >= 0 && Progress.Exists(_s.progressId))
            Progress.Report(_s.progressId, _s.done.Count, Math.Max(1, _s.total),
                string.IsNullOrEmpty(_s.current) ? phase : _s.current);
    }

    static void Heartbeat(string phase)
    {
        if (EditorApplication.timeSinceStartup - _lastBeat < BeatSec) return;
        WriteBeat(_s, phase);
    }

    static void WriteBeat(State s, string phase)
    {
        _lastBeat = EditorApplication.timeSinceStartup;
        try
        {
            var b = new Beat { phase = phase, current = s.current, beat = Now(), queuedAt = s.queuedAt,
                               remaining = s.ids.Count, total = s.total, failed = s.failed, done = s.done };
            File.WriteAllText(Path.Combine(s.dir, "_state.json"), JsonUtility.ToJson(b, true));
        }
        catch (Exception ex) { Debug.LogWarning("[EdoBuildQueue] _state.json を書けない: " + ex.Message); }
    }

    static void WriteLog(string id, string body, double sec)
    {
        File.WriteAllText(Path.Combine(_s.dir, id + ".txt"), body + "\nsec=" + sec.ToString("F1"));
    }

    static void AttachProgress()
    {
        if (_s.progressId < 0 || !Progress.Exists(_s.progressId))
            _s.progressId = Progress.Start("区画の建て直し", _s.total + " 区画(EdoBuildQueue)", Progress.Options.Unmanaged);
        // ⚠ 取り消しの手は再読み込みで消えるので毎回付け直す。
        // ⛔ 再読み込みの時に Unity が項目を取り消しに来る(2026-10-03 実測: 既定の項目では予約が丸ごと canceled になった)。
        //    項目は Unmanaged にし、再読み込み中の取り消しは断る。
        Progress.RegisterCancelCallback(_s.progressId, () => { if (_reloading) return false; Cancel(); return true; });
    }

    // 空打ち: "~dry:<秒>" は何も建てずに秒だけ眠る ── 予約の流れそのもの(背面・再読み込み越し)を検める用
    const string DryPrefix = "~dry:";
    static string Dry(string id)
    {
        float sec; float.TryParse(id.Substring(DryPrefix.Length), out sec);
        System.Threading.Thread.Sleep((int)(Mathf.Clamp(sec, 0f, 60f) * 1000));
        return "dry " + sec + "s";
    }

    static void Nudge() { try { EditorApplication.QueuePlayerLoopUpdate(); } catch { } }

    static string Now() { return DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"); }
}
