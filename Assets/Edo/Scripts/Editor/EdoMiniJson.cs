// 小さな JSON リーダ。docs/Sashizu/*.json をエディタ側から読むためだけの物。
//   object → Dictionary<string,object> / array → List<object> / 数値 → double /
//   文字列 → string / true,false → bool / null → null
// JsonUtility は Vector2 を {"x":..,"y":..} に展開してしまい、python 側と共有する
// 設計値ファイルの形が崩れるので使わない。
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

public static class EdoMiniJson
{
    public static object Parse(string s)
    {
        int i = 0;
        var v = ParseValue(s, ref i);
        return v;
    }

    static void Ws(string s, ref int i)
    {
        while (i < s.Length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) i++;
    }

    static object ParseValue(string s, ref int i)
    {
        Ws(s, ref i);
        if (i >= s.Length) return null;
        char c = s[i];
        if (c == '{') return ParseObject(s, ref i);
        if (c == '[') return ParseArray(s, ref i);
        if (c == '"') return ParseString(s, ref i);
        if (c == 't' && s.Length >= i + 4 && s.Substring(i, 4) == "true") { i += 4; return true; }
        if (c == 'f' && s.Length >= i + 5 && s.Substring(i, 5) == "false") { i += 5; return false; }
        if (c == 'n' && s.Length >= i + 4 && s.Substring(i, 4) == "null") { i += 4; return null; }
        return ParseNumber(s, ref i);
    }

    static Dictionary<string, object> ParseObject(string s, ref int i)
    {
        var d = new Dictionary<string, object>();
        i++; // {
        while (true)
        {
            Ws(s, ref i);
            if (i >= s.Length) break;
            if (s[i] == '}') { i++; break; }
            if (s[i] == ',') { i++; continue; }
            string k = ParseString(s, ref i);
            Ws(s, ref i);
            if (i < s.Length && s[i] == ':') i++;
            d[k] = ParseValue(s, ref i);
        }
        return d;
    }

    static List<object> ParseArray(string s, ref int i)
    {
        var l = new List<object>();
        i++; // [
        while (true)
        {
            Ws(s, ref i);
            if (i >= s.Length) break;
            if (s[i] == ']') { i++; break; }
            if (s[i] == ',') { i++; continue; }
            l.Add(ParseValue(s, ref i));
        }
        return l;
    }

    static string ParseString(string s, ref int i)
    {
        var sb = new StringBuilder();
        if (i < s.Length && s[i] == '"') i++;
        while (i < s.Length)
        {
            char c = s[i++];
            if (c == '"') break;
            if (c != '\\') { sb.Append(c); continue; }
            if (i >= s.Length) break;
            char e = s[i++];
            switch (e)
            {
                case '"': sb.Append('"'); break;
                case '\\': sb.Append('\\'); break;
                case '/': sb.Append('/'); break;
                case 'b': sb.Append('\b'); break;
                case 'f': sb.Append('\f'); break;
                case 'n': sb.Append('\n'); break;
                case 'r': sb.Append('\r'); break;
                case 't': sb.Append('\t'); break;
                case 'u':
                    if (i + 4 <= s.Length)
                    {
                        sb.Append((char)Convert.ToInt32(s.Substring(i, 4), 16));
                        i += 4;
                    }
                    break;
                default: sb.Append(e); break;
            }
        }
        return sb.ToString();
    }

    static object ParseNumber(string s, ref int i)
    {
        int st = i;
        while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
        double d;
        if (double.TryParse(s.Substring(st, i - st), NumberStyles.Float, CultureInfo.InvariantCulture, out d)) return d;
        return 0.0;
    }
}
