---
name: impl-fingerprint-after-yat-overwrite
description: 指図の欄を上書きした直後は Stage1 が算出物の指紋違いで例外を投げる・食い違い 0 なら bake_impl --write で通る(岡部 2026-10-03 EDO-0502)
metadata:
  type: project
---

普請奉行が指図の欄(岡部 E11/E17/E23 の yAt)を上書きしてコミットした直後に RunAll を流すと、Stage1 の `get_IMPL` が
「算出物がいまの指図から焼かれていない」で例外を投げ、何も建たない。

**Why:** 指紋は指図全体の sha。焼いた欄が変わらない上書きでも指紋はずれる。
**How to apply:** 流す前に `python3 Tools/Sashizu/bake_impl.py <邸>`(書かない)で「食い違い 0 件」を見てから `--write`。
食い違いが出たら焼き手の無い欄か確かめて差し戻す。関連 [[bake-impl-carried-src]] [[delaycall-lost-and-shared-sashizu]]

長い RunAll を役から待つ手: 門番は sleep/until を止める。印のファイル(run_*.mark)で再送を止め、結果は scratchpad の txt へ書き、
待つ間に別の仕事(memory・コード読み)をしてから `ls` で見る。
