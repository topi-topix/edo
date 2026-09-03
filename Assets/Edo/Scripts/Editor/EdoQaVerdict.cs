// 検査の**判定そのもの**だけを置く。⛔ ここに Unity の型を持ち込まない。
//
// 【なぜ切り出すか】検査の合否を決める2行(指紋が一致するか / 報告が失敗を含むか)は、
// 屋敷でも場面でも地形でもなく**純粋な関数**である。Unity の型から切り離しておくと、
//   ・Unity を握らずに **破壊試験が走らせられる**(同梱の Roslyn で単体コンパイルできる)
//   ・「検査を書いたのに、その検査が本当に鳴るのか」を機械で確かめられる
// ⚠ 2026-09-04 の破壊試験で分かったこと: 失敗の判定が `report.StartsWith("★")` だったため、
//   **★ が2行目以降に出る報告(算出物の検め)を一つも捕まえられなかった**。
//   検査を書いても、その検査の**失敗が伝わらない**なら書いていないのと同じ
//   (CLAUDE.md 規則19「輪に入っていない値は『未検査』であって『合格』ではない」)。
using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

public static class EdoQaVerdict
{
    /// <summary>ファイルの SHA-256(小文字hex)。算出物が**いまの指図から焼かれたか**の照合に使う。
    /// ⚠ 古い焼きで建てると、指図では直したはずの物が黙って復活する
    ///   (2026-09-01 に松江松平の Stage7 で実際に起きた型)。</summary>
    public static string Sha256Hex(string path)
    {
        using (var sha = SHA256.Create())
        using (var fs = File.OpenRead(path))
        {
            var h = sha.ComputeHash(fs);
            var sb = new StringBuilder(h.Length * 2);
            for (int i = 0; i < h.Length; i++) sb.Append(h[i].ToString("x2"));
            return sb.ToString();
        }
    }

    /// <summary>指紋が一致するか。⛔ 大文字小文字と前後の空白だけは吸うが、**それ以上は緩めない**。</summary>
    public static bool FingerprintMatches(string declared, string actual)
    {
        if (string.IsNullOrEmpty(declared) || string.IsNullOrEmpty(actual)) return false;
        return declared.Trim().ToLowerInvariant() == actual.Trim().ToLowerInvariant();
    }

    /// <summary>検査の報告が**失敗を含むか**。当プロジェクトの検査は失敗の行に ★ か ✗ を付ける。
    /// ⛔ `StartsWith` で見ない — 失敗が2行目以降に出る報告(複数項目を並べる検め)を
    ///   まるごと取り逃がす。⛔ 「0 件」の語で判定しない(報告の書式に依存して脆い)。</summary>
    public static bool Failed(string report)
    {
        if (string.IsNullOrEmpty(report)) return false;
        return report.IndexOf('★') >= 0 || report.IndexOf('✗') >= 0;
    }
}
