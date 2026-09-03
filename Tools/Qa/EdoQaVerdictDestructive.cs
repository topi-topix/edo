using System;
public static class Harness
{
    static int fail = 0;
    static void Want(string name, bool got, bool want)
    {
        bool ok = got == want;
        if (!ok) fail++;
        Console.WriteLine((ok ? "  ✔ " : "  ✗ ") + name + "  → " + got + "(期待 " + want + ")");
    }
    // ⛔ 旧実装。★ が2行目以降に出る報告を取り逃がすことを示すための比較対象
    static bool OldFailed(string r)
    { return !string.IsNullOrEmpty(r) && (r.Contains("✗") || r.StartsWith("★")); }

    public static int Main(string[] a)
    {
        string sashizu = a[0];
        string real = EdoQaVerdict.Sha256Hex(sashizu);
        Console.WriteLine("指図の SHA-256 = " + real);

        // ① 正しい指紋 → 一致する(通す)
        Want("① 正しい指紋は一致する", EdoQaVerdict.FingerprintMatches(real, real), true);

        // ② 1桁だけ変えた指紋 → 一致しない(=IMPL の getter が例外を投げて Stage が止まる)
        char c = real[7];
        char mut = c == '0' ? '1' : '0';
        string broken = real.Substring(0, 7) + mut + real.Substring(8);
        Console.WriteLine("  1桁変えた指紋 = " + broken.Substring(0, 16) + "…(7文字目 " + c + " → " + mut + ")");
        Want("② 1桁変えた指紋は一致しない", EdoQaVerdict.FingerprintMatches(broken, real), false);

        // ③ 大文字・空白は吸うが、それ以上は緩めない
        Want("③ 大文字と前後の空白は吸う", EdoQaVerdict.FingerprintMatches("  " + real.ToUpperInvariant() + " ", real), true);
        Want("③' 末尾を1文字落とした指紋は一致しない", EdoQaVerdict.FingerprintMatches(real.Substring(0, real.Length - 1), real), false);

        // ④ 指紋が合わないときに ImplQA が返す報告 → CheckScene が鳴る
        string report =
            "算出物の検め(場面・地形に触らない)\n" +
            "  ★ ⛔ 算出物が**いまの指図から焼かれていない**\n" +
            "   指図 " + real.Substring(0, 16) + "… / 算出物が名乗る元 " + broken.Substring(0, 16) + "…\n";
        Want("④ 失敗の報告で CheckScene が鳴る", EdoQaVerdict.Failed(report), true);
        Want("④' ⛔ 旧実装(StartsWith)は同じ報告を取り逃がす", OldFailed(report), false);

        // ⑤ 合格の報告では鳴らない(恒真でないことの確認)
        string pass =
            "算出物の検め(場面・地形に触らない)\n" +
            "  ✔ src.sha256 が指図と一致(" + real.Substring(0, 12) + "…)\n" +
            "  ✔ graded は区画内 8520 節点すべてに値がある(格子 1.00m)\n" +
            "→ 0 件 ✔ 算出物は指図と噛み合っている";
        Want("⑤ 合格の報告では鳴らない(検査が恒真でない)", EdoQaVerdict.Failed(pass), false);

        Console.WriteLine(fail == 0 ? "破壊試験: 全件 期待どおり ✔" : "破壊試験: ★ " + fail + " 件が期待外れ");
        return fail;
    }
}
