using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 編集できる水域。輪郭の点(outline)を保持し、水面メッシュ＋地形の掘り込みを生成する。
/// 実際の生成/掘り直しはエディタの WaterBaker が行う（点のドラッグや『掘り直す』ボタン）。
/// snap は掘り込みを元に戻す(縮小時)ための地形スナップショット。
/// </summary>
[RequireComponent(typeof(MeshFilter))]
[RequireComponent(typeof(MeshRenderer))]
public class WaterBody : MonoBehaviour
{
    public List<Vector3> outline = new List<Vector3>();

    [Tooltip("頂点ごとの角スタイル: true=直角(角を残す) / false=スムーズ(丸める)。outline と同じ長さ。空/短い場合は該当点はスムーズ扱い")]
    public List<bool> sharp = new List<bool>();

    public float depth = 2.2f;
    public float waterY = 0f;

    [Tooltip("true=壁を垂直に掘る(断面が直角・カクッと)。false=なだらかに掘る(従来・壁が斜めに丸まる)")]
    public bool verticalWalls = false;

    [Tooltip("true=底を『深さ』の高さでならす(深すぎる所は埋め戻す)。false=掘るだけ(従来。旧掘り込みが残ると底に段差ができ、上から見て水の色が変わる)")]
    public bool levelFloor = false;

    [Tooltip("水域の外側の低い地面を水位まで盛り上げて土手を作り、水が浮かない/漏れないようにする")]
    public bool raiseBanks = true;
    [Tooltip("土手の幅(m)")]
    public float bankWidth = 10f;

    // 掘り込み復元用スナップショット（初回の掘り込み前に固定領域を保存）
    [HideInInspector] public int sX, sZ, sW, sH;
    [HideInInspector] public bool hasSnap;

    // ---- スナップショットの実体は外部のバイナリファイルに置く -------------------
    // 2026-08-15 まではこの配列がシーンに直接埋まっており、池5個で **9.4 MB**
    // (シーンファイルの9%)を占めていた。float 1個が YAML では約13バイトの文字列に
    // なるため。バイナリ(4バイト/個)の .bytes へ移して 2.5 MB に落とした。
    // 書き出しは Editor 側の WaterSnapStore が行う。**snap を書き換えたら必ず
    // WaterSnapStore.Save(wb) を呼ぶこと** — 呼ばないとドメインリロードで消える。
    [HideInInspector] public TextAsset snapFile;

    // 旧データの受け皿。移行後は空。FormerlySerializedAs でシーン内の既存 "snap" を拾う
    [HideInInspector, UnityEngine.Serialization.FormerlySerializedAs("snap")]
    public float[] snapLegacy;

    [System.NonSerialized] float[] _cache;
    [System.NonSerialized] bool _loaded;

    /// <summary>掘る前の地形高。外部ファイル→旧フィールドの順に解決する。</summary>
    public float[] snap
    {
        get
        {
            if (!_loaded)
            {
                _loaded = true;
                if (snapFile != null && snapFile.bytes != null && snapFile.bytes.Length >= 4)
                {
                    var b = snapFile.bytes;
                    _cache = new float[b.Length / 4];
                    System.Buffer.BlockCopy(b, 0, _cache, 0, _cache.Length * 4);
                }
                else _cache = (snapLegacy != null && snapLegacy.Length > 0) ? snapLegacy : null;
            }
            return _cache;
        }
        set { _cache = value; _loaded = true; }
    }
}
