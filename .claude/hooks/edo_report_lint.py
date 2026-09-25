#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop フック — ユーザーへ返す最後の一通を、施主向けの作法(docs/reporting-protocol.md 規則0)で検める。

【なぜ要るか】2026-09-13 の実測: 土井は【裁定/報告】の見出し率 13%・記号 8.3 個/通で
「まとまりがなさすぎてよくわからない」、山王は「全然意味わかりません」。機構語(検査名・感度試験・
母集団・指紋)を含む通が 31〜45%。散文の規則 16 は守られなかったので、**硬い違反だけ**機械で止める。

【止める条件】(どれか 1 つ。1 回だけ — `stop_hook_active` が立っていれば通す)
  ⭐ 2026-09-19 施主裁定3=A: 見るのは**裁定・質問を含む通**と **2,000 字超**だけ。事実の返事は止めない。
  ・裸の符牒(U12 / EDO-0064 / 其十四)に同じ行の説明が無い          … 規則9
  ・問い(裁定・質問・「どちらに」「よいですか」)を含むのに【裁定】【質問】の見出しが無い … 規則1・7
  ・2,000 字超                                                       … 規則0
  ・⭕⛔⭐⚠ が 6 個超                                                … 規則0
  ・機構語(検査名 *_check / 感度試験 / 破壊試験 / 母集団 / 指紋 / 結線)が 3 個超 … 規則0
短い返事(400 字未満)と、コード塊だけの返事は見ない。
問いは文末の形(〜か。/？/ご裁定ください)で決め、語だけでは拾わない(EDO-0440)。
    python3 .claude/hooks/edo_report_lint.py --selftest   # 問い/叙述の判定の型を検める
"""
import json
import re
import sys

MECH = re.compile(r"[A-Za-z_]+_check\b|感度試験|破壊試験|母集団|指紋|結線|関門の自己検査")
MARKS = "⭕⛔⭐⚠"
BARE = re.compile(r"(?<![0-9A-Za-z])(U\d{1,3}|EDO-\d{3,4}|其[一二三四五六七八九十廿卅]+)(?![0-9A-Za-z])")
# ⚠ 問いは**文の終わりの形**で決める(EDO-0440 2026-09-25)。語だけで拾うと叙述を問いと誤る —
#   『どちらの向きにそろえても同じ』『先のご裁定のとおり』『ご判断は要らない』で報告が突き返され、
#   突き返された通も画面に残るので施主には同じ返信が二度見えた(2026-09-21 の「いずれも」も同じ型)。
#   ⛔ 語の網へ戻さない。引用(「」『』)の中は施主や史料の言葉なので見ない。
ASK_END = re.compile(r"(でしょうか|ですか|ますか|ませんか|でしょう[?？]|[?？])$")
ASK_REQ = re.compile(r"(ご裁定|ご判断|お決め|お選び|ご指示|ご返事|お知らせ)[^。]{0,12}"
                     r"(ください|下さい|願います|願いします|願いいたします|仰ぎます|頂けます|いただけます|待ちます)$")
QUOTE = re.compile(r"「[^「」]*」|『[^『』]*』|`[^`\n]*`")
SENT = re.compile(r"[^。!！\n]+[。!！]?")
TRAIL = re.compile(r"[\s。!！*_)）\]」』>]+$")


def ask_sentences(body):
    """問いの形で終わる文を返す(引用・インラインコードは除いて見る)。"""
    out = []
    for sent in SENT.findall(QUOTE.sub("", body)):
        t = TRAIL.sub("", sent.strip())
        t = re.sub(r"^[\s\-*#>|0-9.、]+", "", t)
        if t and (ASK_END.search(t) or ASK_REQ.search(t)):
            out.append(t)
    return out


def strip_code(t):
    return re.sub(r"```.*?```", "", t, flags=re.S)


def lint(msg):
    body = strip_code(msg or "")
    if len(body) < 400:
        return []
    # 2026-09-19 施主裁定3=A: 止めるのは**裁定・質問を含む通**と **2,000 字超**だけ。
    #   事実を答えるだけの通は止めない(それまで一日 14 回止めて、そのたびに書き直していた)。
    #   書式の規則(規則0・一件一葉)そのものは変わらない — 検める範囲を絞っただけ。
    asks = bool(ask_sentences(body)) or bool(re.search(r"【(裁定|質問)", body))
    if not asks and len(body) <= 2000:
        return []
    bad = []
    if len(body) > 2000:
        bad.append("2,000 字を超えている(%d 字)。報告は 1 通 800 字が目安。裁定は 6 点セットだけ" % len(body))
    n = sum(body.count(k) for k in MARKS)
    if n > 6:
        bad.append("記号 ⭕⛔⭐⚠ が %d 個。1 項目 1 個まで" % n)
    m = MECH.findall(body)
    if len(m) > 3:
        bad.append("検査機構の語が %d 個(%s…)。施主には『何が決まった/変わった/待っているか』だけを書く"
                   % (len(m), "・".join(sorted(set(m))[:3])))
    for line in body.split("\n"):
        toks = BARE.findall(line)
        if toks:
            rest = re.sub(r"[\s\-—:：/()（）\[\]、。,.*#]", "", BARE.sub("", line))
            if len(rest) < 8:
                bad.append("符牒 %s が裸(同じ行に一行の中身と行き先を添える)" % "・".join(sorted(set(toks))))
                break
    q = ask_sentences(body)
    if q and not re.search(r"【(裁定|質問)", body):
        bad.append("問い(『%s』)を含むのに【裁定n】【質問n】の見出しが無い(冒頭 1 行で件数を宣言し、選択肢は A/B/C)"
                   % q[0][-30:])
    return bad


PAD = "\n" + "施主へ返す報告の地の文。" * 40   # 400 字の下限を越えるための詰め物


def selftest():
    """問いの判定の型を検める。偽陽性(叙述を問いと誤る)の例文は票が出るたびここへ足す。"""
    asks = ["どちらにしますか?", "A と B のどちらがよいでしょうか。", "この向きでよろしいですか",
            "東西どちらに寄せるかご裁定ください。", "案 B でよろしいでしょうか", "進めてもよいですか？"]
    plain = ["どちらの向きにそろえても同じ。",                      # EDO-0440
             "先のご裁定のとおり、西の端は石垣の小口へ突き付けた。",  # EDO-0440
             "ご判断は要らない。直しは済んだ。",
             "いずれも同じ高さに揃った。", "どちらも 0 件。",        # 2026-09-21
             "施主「なぜ、同じ返信が2回出てくるの？」への答え: 突き返された通が残るため。",
             "いずれかの端が浮けば退ける(硬い条件)。",
             "`--reopen` を使うかは施主の発話で決まる。"]
    ng = [a for a in asks if not ask_sentences(a)] + [p for p in plain if ask_sentences(p)]
    ok_block = lint("【報告1】" + PAD + "\nどちらにしますか。")
    ok_pass = lint("【報告1】" + PAD + "\n" + "\n".join(plain))
    if not any("見出し" in b for b in ok_block):
        ng.append("<見出し無しの問いが止まらない>")
    if ok_pass:
        ng.append("<叙述だけの報告が止まる: %s>" % ok_pass)
    for x in ng:
        print("✗", x)
    print("selftest:", "ok" if not ng else "%d 件 NG" % len(ng))
    return 1 if ng else 0


def main():
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if ev.get("stop_hook_active"):
        sys.exit(0)
    bad = lint(ev.get("last_assistant_message") or "")
    if not bad:
        sys.exit(0)
    print(json.dumps({"decision": "block",
                      "reason": "⛔ 報告の作法(docs/reporting-protocol.md 規則0・一件一葉)に反する点があるので、"
                                "同じ内容を書き直してから返すこと:\n- " + "\n- ".join(bad) +
                                "\n読み手は施主。役名・検査名・巡次・ファイル名を落とし、"
                                "冒頭 1 行で件数、【種別n】の見出し、選択肢は A/B/C。"}))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
