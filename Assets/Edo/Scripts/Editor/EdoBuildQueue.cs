// EdoBuildQueue.cs — 長い建て直しを MCP の 1 回の呼び出しの中で回さず、エディタの中で順に予約して即座に返す(EDO-0503)。
//
// ⛔ 2026-10-03 の事故: execute_code の中で BuildParcel を 21 区画まわし(約 9 分)、MCP が応答の時間切れを見て
//    **同じ命令を自動で送り直し**、建て直しが 3 巡くり返して CPU 100% のまま止まらなくなった(施主が Unity を再起動)。
//    1 区画でも 30 秒を超えると同じことが起きる(樹下の建て直しで 2 回走った)。
// ⭐ 作法: execute_code では `EdoBuildQueue.Enqueue(<log の置き場>, "id1", "id2", ...)` を呼ぶだけ。呼び出しは即座に返り、
//    建て直しは EditorApplication.delayCall で 1 区画ずつ流れる。各区画の log は <置き場>/<id>.txt、終わると <置き場>/_done。
//    待つのは Bash の until ループで _done を見る(Unity へ問い合わせを重ねない)。
//    見張り: .claude/hooks/edo_mcp_long_guard.py が BuildParcel の直呼びを止める。

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;

public static class EdoBuildQueue
{
    static Queue<string> _q;
    static string _dir;

    /// <summary>区画の建て直しを予約する。既に流れている予約があれば断る(二重に流さない)。</summary>
    public static string Enqueue(string logDir, params string[] ids)
    {
        if (_q != null && _q.Count > 0) return "⛔ 前の予約が流れている(残り " + _q.Count + ")── 終わってから";
        Directory.CreateDirectory(logDir);
        var done = Path.Combine(logDir, "_done"); if (File.Exists(done)) File.Delete(done);
        _q = new Queue<string>(ids); _dir = logDir;
        File.WriteAllText(Path.Combine(logDir, "_queued"), DateTime.Now.ToString("HH:mm:ss") + " " + string.Join(" ", ids));
        EditorApplication.delayCall += Step;
        return "queued " + ids.Length;
    }

    /// <summary>流れている予約の残り(0 なら空き)。</summary>
    public static int Remaining { get { return _q == null ? 0 : _q.Count; } }

    static void Step()
    {
        if (_q == null) return;
        if (_q.Count == 0) { File.WriteAllText(Path.Combine(_dir, "_done"), DateTime.Now.ToString("HH:mm:ss")); _q = null; return; }
        var id = _q.Dequeue(); string r; var sw = System.Diagnostics.Stopwatch.StartNew();
        try { r = EdoTypologyBuilder.BuildParcel(id, true); } catch (Exception ex) { r = "EXC " + ex; }
        File.WriteAllText(Path.Combine(_dir, id + ".txt"), (r ?? "null") + "\nsec=" + sw.Elapsed.TotalSeconds.ToString("F1"));
        EditorApplication.delayCall += Step;
    }
}
