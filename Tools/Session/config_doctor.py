#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""道具改め — Claude Code の設定そのもの(CLAUDE.md・.claude/・スキル・メモリ・教訓)の破れを機械で鳴らす。

【なぜ要るか】2026-09-13 の点検: 設定は 27 日で 48 コミット動いたが全部が事故の後追いで、
設定を検める道具も定期の担い手も無かった(EDO-0138)。同日、`qa-and-pitfalls.md` を分割した
1 時間後に 5 つの役が「154KB の丸読み禁止」と古い数字を語り、棟梁の書き戻し先が description・
本文・CLAUDE.md で三様になっていた。参照が切れた役・スキル・フックは**黙って古い規則で動く**
(EDO-0076 型)ので、散文の作法ではなく機械で見張る。

【作法】検出は機械、処置の決定は人、実行は機械的な物だけ(`docs/verification-loops.md`「書き戻しを自動化しない」)。
挨拶(--quick)は ⛔ だけを最大 6 行、無傷なら無言。表(--table)を人が直して --apply。

【使い方】
    python3 Tools/Session/config_doctor.py --quick                 # 挨拶用。exit 1 iff ⛔
    python3 Tools/Session/config_doctor.py --table > docs/teire-latest.md
    python3 Tools/Session/config_doctor.py --apply docs/teire-latest.md
    python3 Tools/Session/config_doctor.py --deep                  # 月次: 表 + 各関門の自己検査 + 挨拶の計時
    python3 Tools/Session/config_doctor.py --selftest              # ⛔ 落ちたらこの道具の検出が死んでいる

処置の語彙(表の「処置」列。編集してよい):
  機械的(--apply が実行する):
    rm <path>                 ゴミを消す(K1)
    remeasure                 計測キー付きの数字を今の値に書き直す(Q2)
    index-add / index-rm      MEMORY.md の索引行を足す / 消す(R7 のみ。⛔ 典拠台帳の索引=R8 は手で入れる
                              — その項をどの確度の行へ載せるかは考証の判断)
    sync-rm                   worktree の作業ツリーから main に無いファイルを消す(W1・コミットしない)
    lesson-tag →不要 | lesson-tag →保留:YYYY-MM-DD   教訓の行に処置タグを付ける(L1)
    task:<邸> "<文>"          掲示板へ宿題として起票する(意味的な件の逃がし先)(⚠ 門番の都合で EDO_SESSION_ID を付けて叩く)
    keep "<理由>"             承認済として黙らせる(対象行が変わるまで。⛔ には効かない)
  意味的(--apply は実行しない。セッションが手で直す):
    drop | rewrite | merge:<a>,<b> | promote:→規則|→スキル|→メモリ | expire | sync-add <path> | manual
"""
import argparse
import ast
import datetime
import fnmatch
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import usage_ledger as UL  # noqa: E402  利用実績(U1/U2)

HOME = os.path.expanduser("~")

# ── 既知の名前(Claude Code の作法) ──────────────────────────────────────
HOOK_EVENTS = {"SessionStart", "SessionEnd", "PreToolUse", "PostToolUse", "Stop", "SubagentStop",
               "Notification", "UserPromptSubmit", "PreCompact", "PermissionRequest", "Elicitation",
               "ElicitationResult", "TeammateIdle", "TaskCompleted", "ConfigChange", "WorktreeCreate",
               "WorktreeRemove", "PostToolUseFailure", "InstructionsLoaded", "SubagentStart",
               "PermissionDenied", "CwdChanged", "FileChanged", "StopFailure"}
KNOWN_TOOLS = {"Read", "Grep", "Glob", "Edit", "Write", "Bash", "Skill", "ToolSearch", "WebSearch",
               "WebFetch", "Agent", "NotebookEdit", "Workflow", "MultiEdit", "TodoWrite", "LS",
               "BashOutput", "KillShell", "SendMessage", "Artifact", "AskUserQuestion", "Monitor",
               "TaskOutput", "TaskStop", "EnterPlanMode", "ExitPlanMode", "ListAgents", "Task"}
MODELS = {"opus", "sonnet", "haiku", "inherit"}
MEMORY_KINDS = {"project", "user", "local"}
EFFORTS = {"low", "medium", "high", "max"}
REVIEWERS = ("edo-kenzu", "edo-kosho", "edo-niwashi")
CONFIG_DIRS = (".claude/agents", ".claude/hooks", ".claude/commands", ".claude/rules", ".claude/workflows")
CONFIG_FILES = ("CLAUDE.md", ".claude/settings.json")
CRUFT_GLOBS = ("*.superseded", ".backup-*", "*.bak", "*.orig", "*.rej")
LESSON_TAG = re.compile(r"→(規則\d+|スキル:[\w-]+|メモリ:[\w.-]+|不要|保留:\d{4}-\d{2}-\d{2})\s*$")
LESSON_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \*\*(.+?)\*\*\((EDO-\d{4})")
MEASURED = re.compile(r"<!--\s*measured:\s*([\w:./-]+)\s*-->")
NUMBER = re.compile(r"(\d+(?:\.\d+)?)\s?(KB|MB)|(\d{1,3}(?:,\d{3})+|\d{4,})\s?(点)")
OBL_TAG = re.compile(r"<!--\s*obl:([\w-]+)(\s+canon)?\s*-->")
OBL_WORDS = re.compile(r"必ず|毎回|義務")
NEG_WORDS = re.compile(r"しない|禁止|⛔")

BUDGET = {"claude_lines": 160, "claude_kb": 14, "agent_lines": 200, "command_lines": 60, "rule_lines": 60,
          "skill_lines": 500, "skill_desc": 1024, "ref_lines": 600, "memory_total": 4000,
          "memory_file": 250, "memory_index": 120, "lessons_lines": 200, "agent_desc": 600}
REF_ALLOW = {"sources.md"}          # 典拠台帳は長くてよい(目次があること)
LESSON_DUE_DAYS, TRANSITION_DAYS, NUDGE_DAYS, UNCOMMITTED_DAYS = 14, 30, 7, 7
IDLE_ROLE_DAYS, IDLE_REF_DAYS, USAGE_MIN_COVER = 30, 60, 30   # U1(役・スキル)/ U2(参照)/ これ未満の記録では判定しない
QUICK_MAX = 6


# ── 環境 ─────────────────────────────────────────────────────────────────
def _git(root, *args, timeout=5):
    try:
        r = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _main_root(start):
    d = _git(start, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    return os.path.dirname(d) if d else start


class Env:
    def __init__(self, a):
        cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        self.cwd = os.path.abspath(a.root or cwd)
        self.root = os.path.abspath(a.root) if a.root else _main_root(cwd)
        self.is_git = bool(_git(self.root, "rev-parse", "--git-dir").strip())
        self.skills = os.path.abspath(a.skills_dir) if a.skills_dir else os.path.join(HOME, ".claude", "skills")
        proj = "-" + self.root.strip("/").replace("/", "-")
        self.memory = os.path.abspath(a.memory_dir) if a.memory_dir else \
            os.path.join(HOME, ".claude", "projects", proj, "memory")
        self.global_settings = os.path.abspath(a.global_settings) if a.global_settings else \
            os.path.join(HOME, ".claude", "settings.json")
        gd = _git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
        self.state = os.path.abspath(a.state_dir) if a.state_dir else os.path.join(gd or self.root, "edo-teire")
        self.worktrees_override = a.worktrees
        self.transcripts_override = a.transcripts_dir
        self.quick = False
        self.now = time.time()
        self._tracked = None

    def p(self, *rel):
        return os.path.join(self.root, *rel)

    def rel(self, path):
        for base, tag in ((self.root, ""), (self.skills, "<skills>/"), (self.memory, "<memory>/")):
            if path.startswith(base + os.sep):
                return tag + os.path.relpath(path, base)
        return path

    def tracked(self):
        if self._tracked is None:
            out = _git(self.root, "ls-files", timeout=20)
            if out:
                self._tracked = out.split("\n")
            else:                                   # git が無い(fixture)→ 作業ツリー
                self._tracked = [os.path.relpath(os.path.join(d, f), self.root)
                                 for d, _, fs in os.walk(self.root) for f in fs]
        return self._tracked

    def worktrees(self):
        """(path, branch) の一覧。main は含めない。1 日 cache(挨拶の予算のため git を毎回呼ばない)。"""
        if self.worktrees_override is not None:
            return [(os.path.abspath(w), "?") for w in self.worktrees_override if os.path.isdir(w)]
        if not self.is_git:
            return []
        cache = os.path.join(self.state, "worktrees.json")
        try:
            c = json.load(open(cache, encoding="utf-8"))
            if self.now - c.get("t", 0) < 86400:
                return [tuple(x) for x in c["wt"]]
        except Exception:
            pass
        out, cur = [], {}
        for ln in _git(self.root, "worktree", "list", "--porcelain").split("\n") + [""]:
            if ln.startswith("worktree "):
                cur = {"p": ln[9:]}
            elif ln.startswith("branch "):
                cur["b"] = ln[7:].replace("refs/heads/", "")
            elif ln == "" and cur:
                if os.path.realpath(cur["p"]) != os.path.realpath(self.root):
                    out.append((cur["p"], cur.get("b", "(detached)")))
                cur = {}
        try:
            os.makedirs(self.state, exist_ok=True)
            json.dump({"t": self.now, "wt": out}, open(cache, "w", encoding="utf-8"))
        except Exception:
            pass
        return out

    def added_at(self, path):
        """git に入った時刻(epoch)。git が無い・履歴が無いなら None(= 古い物として扱う)。"""
        if not self.is_git:
            return None
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(self.root))   # ⚠ スキルは symlink 越し
        if rel.startswith(".."):
            return None
        out = _git(self.root, "log", "--diff-filter=A", "--follow", "--format=%ct", "--", rel, timeout=10).split()
        return int(out[-1]) if out else None

    def edo_skills(self):
        """検める対象のスキル = 設定から Skill(x) で参照される物 ∪ Tools/Skills/ にある物。irweather 等は見ない。"""
        names = set()
        for fp in self.config_texts():
            for ln in read(fp).split("\n"):
                if "⛔" in ln or "読まない" in ln:
                    continue
                names |= set(re.findall(r"Skill\(([\w-]+)\)", ln))
                names |= set(re.findall(r"スキル `([\w-]+)`", ln))
        ts = self.p("Tools", "Skills")
        if os.path.isdir(ts):
            names |= {d for d in os.listdir(ts) if os.path.isfile(os.path.join(ts, d, "SKILL.md"))}
        return sorted(names)

    def skill_dir(self, name):
        for cand in (os.path.join(self.skills, name), self.p("Tools", "Skills", name)):
            if os.path.isfile(os.path.join(cand, "SKILL.md")):
                return cand
        return None

    def config_texts(self):
        out = []
        for d in (".claude/agents", ".claude/commands", ".claude/rules"):
            out += sorted(glob.glob(self.p(d, "*.md")))
        if os.path.isfile(self.p("CLAUDE.md")):
            out.append(self.p("CLAUDE.md"))
        return out

    def agents(self):
        return sorted(glob.glob(self.p(".claude", "agents", "*.md")))


def read(fp):
    try:
        return io.open(fp, encoding="utf-8").read()
    except Exception:
        return ""


def frontmatter(text):
    """PyYAML 無しで frontmatter を読む。先頭 `---` と**その次の** `---` の間だけ(本文の水平線と混同しない)。
    返り値: (dict, body)。入れ子(hooks:)は生の行の list、`>`/`>-`/`|` の続きは畳む、`- x` の list は list。"""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None, text
    fm, key, mode = {}, None, None
    for ln in lines[1:end]:
        if ln and not ln[0].isspace():
            k, _, v = ln.partition(":")
            key, v = k.strip(), v.strip()
            if v in (">", ">-", "|", "|-"):
                fm[key], mode = "", "fold"
            elif v == "":
                fm[key], mode = [], "list"
            else:
                fm[key], mode = v.strip('"').strip("'"), None
        elif key is not None and ln.strip():
            s = ln.strip()
            if mode == "fold":
                fm[key] = (fm[key] + " " + s).strip()
            elif mode == "list":
                fm[key].append(s[2:].strip().strip('"').strip("'") if s.startswith("- ") else ln.rstrip())
    return fm, "\n".join(lines[end + 1:])


def num(s):
    try:
        return float(s.replace(",", ""))
    except Exception:
        return None


# ── 所見 ─────────────────────────────────────────────────────────────────
class Findings:
    def __init__(self, env):
        self.env, self.items = env, []

    def add(self, cid, sev, where, text, fix="manual", quick=False):
        key = cid + "#" + hashlib.sha256((where + " " + text).encode("utf-8")).hexdigest()[:8]
        self.items.append({"id": cid, "sev": sev, "where": self.env.rel(where) if where else "", "text": text,
                           "fix": fix, "quick": quick and sev == "⛔", "key": key})

    def ids(self):
        return sorted({f["id"] for f in self.items})


# ── 検査 ─────────────────────────────────────────────────────────────────
def chk_R1_R2(env, F):
    """役・コマンド・CLAUDE.md が指すスキルと参照ファイル・節が実在するか。"""
    for fp in env.config_texts():
        txt = read(fp)
        for m in re.finditer(r"Skill\(([\w-]+)\)|スキル `([\w-]+)`", txt):
            name = m.group(1) or m.group(2)
            if env.skill_dir(name) is None:
                F.add("R1", "⛔", fp, "スキル `%s` が無い(%s)" % (name, "Skill(…)" if m.group(1) else "表"), quick=True)
        # references/<f>.md は直前の Skill(x) に束ねる。無ければ検める全スキルから探す
        for m in re.finditer(r"references/([\w./-]+?\.(?:md|py))", txt):
            ref = m.group(1)
            prev = [x for x in re.finditer(r"Skill\(([\w-]+)\)", txt[:m.start()])]
            cands = [prev[-1].group(1)] if prev else env.edo_skills()
            dirs = [env.skill_dir(c) for c in cands if env.skill_dir(c)]
            hit = [d for d in dirs if os.path.isfile(os.path.join(d, "references", ref))]
            if not hit:
                F.add("R2", "⛔", fp, "`references/%s` が%s に無い" % (ref, ("スキル `%s`" % cands[0]) if prev else "どのスキル"),
                      quick=True)
                continue
        # §N は直前(400 字以内)の references/<f>.md に束ねる。見出しは `## §5.` / `## 5.` / `## 0b.` を認める
        for m in re.finditer(r"§(\d+[a-z]?)", txt):
            sec = m.group(1)
            prev = list(re.finditer(r"references/([\w./-]+?\.md)", txt[max(0, m.start() - 400):m.start()]))
            if not prev:
                continue
            ref = prev[-1].group(1)
            sk = [x for x in re.finditer(r"Skill\(([\w-]+)\)", txt[:m.start()])]
            cands = [sk[-1].group(1)] if sk else env.edo_skills()
            hit = [env.skill_dir(c) for c in cands if env.skill_dir(c)
                   and os.path.isfile(os.path.join(env.skill_dir(c), "references", ref))]
            if not hit:
                continue
            body = read(os.path.join(hit[0], "references", ref))
            if not re.search(r"^#+\s*§?%s[\s.．]" % re.escape(sec), body, re.M):
                F.add("R2", "⚠", fp, "`references/%s` に見出し §%s が無い" % (ref, sec), fix="rewrite")


def chk_R3(env, F):
    """CLAUDE.md の表が指すパス・役名が実在するか。"""
    fp = env.p("CLAUDE.md")
    txt = read(fp)
    for m in re.finditer(r"`((?:docs|Tools|Assets|\.claude)/[\w./-]+)`", txt):
        rel = m.group(1)
        if any(c in rel for c in "*<>{"):
            continue
        if not os.path.exists(env.p(rel)):
            F.add("R3", "⛔", fp, "`%s` が無い" % rel, quick=True)
    for name in sorted(set(re.findall(r"`(edo-[a-z][\w-]*)`", txt))):
        if name == "edo-unity" or "/" in name:
            continue
        if not os.path.isfile(env.p(".claude", "agents", name + ".md")):
            F.add("R3", "⛔", fp, "役 `%s` の定義 `.claude/agents/%s.md` が無い" % (name, name), quick=True)


def chk_R4(env, F):
    """コマンド・役・CLAUDE.md・rules が指す Workflow と Tools/*.py が実在するか。"""
    for fp in env.config_texts():
        txt = read(fp)
        for wf in re.findall(r"Workflow\(\s*name:\s*[\"']([\w-]+)[\"']", txt):
            js = env.p(".claude", "workflows", wf + ".js")
            if not os.path.isfile(js):
                F.add("R4", "⛔", fp, "Workflow `%s` の `.claude/workflows/%s.js` が無い" % (wf, wf), quick=True)
        for py in sorted(set(re.findall(r"python3 ((?:Tools|\.claude)/[\w./-]+\.py)", txt))):
            if not os.path.isfile(env.p(py)):
                F.add("R4", "⛔", fp, "`%s` が無い" % py, quick=True)


def _hook_cmds(node, out, event=None):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "command" and isinstance(v, str):
                out.append((event, v, node.get("timeout")))
            else:
                _hook_cmds(v, out, event if k in ("hooks", "matcher", "type", "timeout", "command") else k)
    elif isinstance(node, list):
        for x in node:
            _hook_cmds(x, out, event)


def _script_of(cmd, env):
    cmd = cmd.replace('"$CLAUDE_PROJECT_DIR"', env.root).replace("$CLAUDE_PROJECT_DIR", env.root)
    toks = [t for t in cmd.split() if t.endswith((".py", ".sh"))]
    return toks[0] if toks else None


def chk_R5(env, F):
    """フック: settings.json(プロジェクト・グローバル)と役の hooks: が指すスクリプトの実在・構文・matcher。"""
    for fp, is_global in ((env.p(".claude", "settings.json"), False), (env.global_settings, True)):
        if not os.path.isfile(fp):
            continue
        try:
            doc = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            F.add("R5", "⛔", fp, "JSON として読めない: %s" % str(e)[:60], quick=True)
            continue
        hooks = doc.get("hooks") or {}
        for ev, entries in hooks.items():
            if ev not in HOOK_EVENTS:
                F.add("R5", "⚠", fp, "未知のフックイベント `%s`" % ev, fix="rewrite")
            for ent in entries if isinstance(entries, list) else []:
                mt = ent.get("matcher")
                if mt:
                    try:
                        re.compile(mt)
                    except re.error:
                        F.add("R5", "⛔", fp, "%s の matcher `%s` が正規表現として不正" % (ev, mt[:40]), quick=True)
                for h in ent.get("hooks") or []:
                    cmd = h.get("command") or ""
                    sp = _script_of(cmd, env)
                    if is_global and "edo_" in cmd:
                        F.add("R5", "⚠", fp, "edo 用フックがグローバル側にある(版管理・sync の外): `%s`"
                              % os.path.basename(sp or cmd), fix="manual")
                    if sp and not os.path.isabs(sp) and not os.path.exists(sp):
                        sp = env.p(sp)
                    _check_script(env, F, fp, ev, sp, cmd)
                    if "timeout" not in h:
                        F.add("R5", "⚠", fp, "%s のフック `%s` に timeout が無い" % (ev, os.path.basename(sp or cmd)),
                              fix="rewrite")
    for fp in env.agents():
        fm, _ = frontmatter(read(fp))
        for ln in (fm or {}).get("hooks") or []:
            if "command:" in ln:
                cmd = ln.split("command:", 1)[1].strip()
                _check_script(env, F, fp, "hooks", _script_of(cmd, env), cmd)


def _check_script(env, F, fp, ev, sp, cmd):
    if not sp:
        return
    if not os.path.exists(sp):
        F.add("R5", "⛔", fp, "%s のフックが指す `%s` が無い" % (ev, os.path.basename(sp)), quick=True)
        return
    if sp.endswith(".py"):
        try:
            compile(read(sp), sp, "exec")
        except SyntaxError as e:
            F.add("R5", "⛔", fp, "`%s` が構文エラー(行 %s)" % (os.path.basename(sp), e.lineno), quick=True)
    elif sp.endswith(".sh") and not cmd.lstrip().startswith(("bash ", "sh ")) and not os.access(sp, os.X_OK):
        F.add("R5", "⚠", fp, "`%s` に実行ビットが無い" % os.path.basename(sp), fix="manual")


def chk_R6_V3(env, F):
    """スキル: SKILL.md が挙げる参照の実在、辿れない参照ファイル、frontmatter。"""
    for name in env.edo_skills():
        d = env.skill_dir(name)
        if not d:
            continue
        sk = os.path.join(d, "SKILL.md")
        txt = read(sk)
        fm, body = frontmatter(txt)
        if fm is None:
            F.add("V3", "⚠", sk, "frontmatter が無い", fix="rewrite")
        else:
            if fm.get("name") != name:
                F.add("V3", "⚠", sk, "name `%s` がディレクトリ名 `%s` と違う" % (fm.get("name"), name), fix="rewrite")
            desc = fm.get("description") or ""
            if not desc.strip():
                F.add("V3", "⚠", sk, "description が空", fix="rewrite")
            elif len(desc) > BUDGET["skill_desc"]:
                F.add("V3", "⚠", sk, "description が %d 字(上限 %d)" % (len(desc), BUDGET["skill_desc"]), fix="rewrite")
        refdir = os.path.join(d, "references")
        mentioned = set(re.findall(r"references/([\w./-]+?\.(?:md|py))", txt))
        for ref in sorted(mentioned):
            if not os.path.isfile(os.path.join(refdir, ref)):
                F.add("R6", "⛔", sk, "SKILL.md が挙げる `references/%s` が無い" % ref, quick=True)
        if os.path.isdir(refdir):
            allmd = " ".join(read(os.path.join(dp, f)) for dp, _, fs in os.walk(refdir) for f in fs if f.endswith(".md"))
            for dp, _, fs in os.walk(refdir):
                for f in sorted(fs):
                    if not f.endswith((".md", ".py")):
                        continue
                    rel = os.path.relpath(os.path.join(dp, f), refdir)
                    stem = os.path.splitext(f)[0]
                    if rel in mentioned or ("references/" + rel) in allmd or ("/" + f) in allmd or f in txt \
                            or re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(stem), allmd + txt):
                        continue
                    F.add("R6", "⚠", os.path.join(dp, f), "SKILL.md からも他の参照からも辿れない参照ファイル",
                          fix="manual")


def chk_R7(env, F):
    """メモリ: MEMORY.md の索引 ↔ ファイル。"""
    idx = os.path.join(env.memory, "MEMORY.md")
    if not os.path.isfile(idx):
        return
    txt = read(idx)
    links = set(re.findall(r"\]\(([\w.-]+\.md)\)", txt))
    files = {f for f in os.listdir(env.memory) if f.endswith(".md") and f != "MEMORY.md"}
    for f in sorted(links - files):
        F.add("R7", "⛔", idx, "索引が指す `%s` が無い" % f, fix="index-rm", quick=True)
    for f in sorted(files - links):
        if f in txt:
            continue
        F.add("R7", "⚠", os.path.join(env.memory, f), "MEMORY.md に索引行が無い", fix="index-add")


def chk_R8(env, F):
    """典拠台帳: sources.md の索引 ↔ 項の見出し。

    ⚠ **索引に無い項は、grep する ID が分からないので実質的に見つからない。**考証方の手順は
    「索引で ID を見つけてから該当項だけ読む」(台帳は14万字超で丸読みしない)。索引から漏れると
    **次の巡で同じ史料を取り直す**ことになる — WebFetch のやり直しと外部への負荷。
    2026-09-06 にはその日の起票が1件残らず漏れていた(掲示板 EDO-0151)。

    ⛔ 逆(索引に在って見出しが無い)は見ない — §3 の書籍図版の表のように、
    `### [ID]` の見出しを持たないまま索引に載る項が在る(索引にその旨が書いてある)。
    """
    for name in env.edo_skills():
        d = env.skill_dir(name)
        if not d:
            continue
        fp = os.path.join(d, "references", "sources.md")
        if not os.path.isfile(fp):
            continue
        lines = read(fp).split("\n")
        i0 = next((i for i, l in enumerate(lines) if re.match(r"^#+ .*索引", l)), None)
        if i0 is None:
            continue        # 索引が無いことは chk_S1 が言う
        i1 = next((i for i in range(i0 + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        idx = "\n".join(lines[i0:i1])
        seen = set()
        for n, l in enumerate(lines, 1):
            m = re.match(r"^### \[([^\]]+)\]", l)
            if not m:
                continue
            i = re.sub(r"\(続き.*$", "", m.group(1)).strip()    # 「(続き — …)」は同じ ID
            if i in seen:
                continue
            seen.add(i)
            if "`%s`" % i not in idx:
                F.add("R8", "⚠", "%s:%d" % (fp, n),
                      "典拠 [%s] が索引に無い — 考証方が ID を引けず、次の巡で取り直しになる" % i,
                      fix="manual")


def _measure(env, key):
    kind, _, arg = key.partition(":")
    try:
        if key == "count:asset-index":
            return max(0, len(read(env.p("docs", "asset-index.tsv")).rstrip("\n").split("\n")) - 1)
        if key == "count:parcels":
            d = json.load(open(env.p("docs", "Sashizu", "parcels.json"), encoding="utf-8"))
            return len(d["parcels"] if isinstance(d, dict) and "parcels" in d else d)
        if key == "count:memory-files":
            return len([f for f in os.listdir(env.memory) if f.endswith(".md") and f != "MEMORY.md"])
        if kind == "kb":
            return round(os.path.getsize(env.p(arg)) / 1024)
        if kind == "lines":
            return len(read(env.p(arg)).split("\n"))
    except Exception:
        return None
    return None


def _prose_files(env):
    out = list(env.config_texts())
    for name in env.edo_skills():
        d = env.skill_dir(name)
        if d:
            out.append(os.path.join(d, "SKILL.md"))
    if os.path.isfile(os.path.join(env.memory, "MEMORY.md")):
        out.append(os.path.join(env.memory, "MEMORY.md"))
    return out


def chk_Q(env, F):
    """設定を語る数字: 計測キーが無い(Q1)/ 計測とずれている(Q2)/ 期限切れの移行期間(Q3)。"""
    for fp in _prose_files(env) + sorted(glob.glob(env.p(".claude", "hooks", "*.py"))):
        for i, ln in enumerate(read(fp).split("\n"), 1):
            if fp.endswith(".py") and not "移行期間" in ln:
                continue
            mk = MEASURED.search(ln)
            nums = [(a or c, b or d) for a, b, c, d in NUMBER.findall(ln)]
            if nums and not mk and not fp.endswith(".py"):
                # 予算(≤・以内・上限)は規則であって計測値ではない
                if re.search(r"[≤≦]\s*\d|以内|上限|まで", ln):
                    continue
                F.add("Q1", "⚠", fp, "行 %d: 設定を語る数字 `%s%s` に計測キーが無い" % (i, nums[0][0], nums[0][1]),
                      fix="drop")
            elif mk:
                val = _measure(env, mk.group(1))
                if val is None:
                    F.add("Q2", "⚠", fp, "行 %d: 計測キー `%s` を測れない" % (i, mk.group(1)), fix="rewrite")
                    continue
                for s, unit in nums:
                    v = num(s)
                    if v is None:
                        continue
                    off = abs(v - val) > (0.25 * max(val, 1) if unit in ("KB", "MB") else 0)
                    if off:
                        F.add("Q2", "⚠", fp, "行 %d: `%s%s` は今 %s(%s)" % (i, s, unit, val, mk.group(1)),
                              fix="remeasure")
            if "移行期間" in ln:
                for ds in re.findall(r"(20\d\d-\d\d-\d\d)", ln):
                    age = (env.now - time.mktime(time.strptime(ds, "%Y-%m-%d"))) / 86400
                    if age > TRANSITION_DAYS:
                        F.add("Q3", "⚠", fp, "行 %d: 移行期間(%s)が %d 日経っている" % (i, ds, age), fix="expire")


def chk_C(env, F):
    """義務の矛盾: 極性(C1)・obl タグの正典(C2)・description の衛生(C3)。"""
    claude = read(env.p("CLAUDE.md"))
    for fp in env.agents():
        name = os.path.basename(fp)[:-3]
        fm, body = frontmatter(read(fp))
        if fm is None:
            continue
        desc = fm.get("description") or ""
        # C3
        if len(desc) > BUDGET["agent_desc"] or re.search(r"→|\b\d\.\s", desc):
            why = "%d 字" % len(desc) if len(desc) > BUDGET["agent_desc"] else "手順語(→・番号)"
            F.add("C3", "⚠", fp, "description が起動判断用でない: %s(上限 %d 字・手順は本文へ)" % (why, BUDGET["agent_desc"]),
                  fix="rewrite")
        # C1: 同じ .md について description / 本文 / CLAUDE.md の極性
        sources = [("description", desc.split("。")), ("本文", body.split("\n")),
                   ("CLAUDE.md", [l for l in claude.split("\n") if name in l])]
        pol = {}
        for src, lines in sources:
            for ln in lines:
                for obj in set(re.findall(r"([\w-]+\.md)", ln)):
                    if NEG_WORDS.search(ln):
                        pol.setdefault(obj, {}).setdefault("NEG", []).append(src)
                    elif OBL_WORDS.search(ln):
                        pol.setdefault(obj, {}).setdefault("OBL", []).append(src)
        for obj, d in sorted(pol.items()):
            if "OBL" in d and "NEG" in d:
                F.add("C1", "⚠", fp, "`%s` について「必ず」(%s)と「しない」(%s)が並ぶ" %
                      (obj, "/".join(sorted(set(d["OBL"]))), "/".join(sorted(set(d["NEG"])))), fix="rewrite")
    # C2
    tags = {}
    for fp in env.config_texts() + sorted(glob.glob(env.p("docs", "*.md"))):
        txt = read(fp)
        fm, body = frontmatter(txt)
        fm_len = len(txt) - len(body) if fm is not None else 0
        for m in OBL_TAG.finditer(txt):
            line = txt[txt.rfind("\n", 0, m.start()) + 1: txt.find("\n", m.end()) if txt.find("\n", m.end()) > 0 else None]
            tags.setdefault(m.group(1), []).append((fp, bool(m.group(2)), m.start() < fm_len, line))
    agent_names = {os.path.basename(a)[4:-3] for a in env.agents()}   # edo-toryo → toryo
    for oid, uses in sorted(tags.items()):
        canons = [u for u in uses if u[1]]
        if len(canons) != 1:
            F.add("C2", "⛔", canons[0][0] if canons else uses[0][0],
                  "義務 `%s` の正典が %d 箇所(1 箇所であること)" % (oid, len(canons)), quick=True)
        for fp, is_canon, in_fm, line in uses:
            if not is_canon and "→" not in line:
                F.add("C2", "⚠", fp, "義務 `%s` の参照行にポインタ(→)が無い" % oid, fix="rewrite")
        owner = oid.split("-")[0]
        if owner in agent_names and len(canons) == 1:
            fp, _, in_fm, _ = canons[0]
            if os.path.basename(fp) != "edo-%s.md" % owner or in_fm:
                F.add("C2", "⚠", fp, "役の義務 `%s` の正典は `edo-%s.md` の本文に置く" % (oid, owner), fix="rewrite")


def chk_S1(env, F):
    """サイズ予算。"""
    def lines(fp):
        return len(read(fp).split("\n"))
    cm = env.p("CLAUDE.md")
    if os.path.isfile(cm):
        if lines(cm) > BUDGET["claude_lines"]:
            F.add("S1", "⚠", cm, "%d 行(予算 %d)" % (lines(cm), BUDGET["claude_lines"]), fix="rewrite")
        if os.path.getsize(cm) > BUDGET["claude_kb"] * 1024:
            F.add("S1", "⚠", cm, "%d KB(予算 %d)" % (os.path.getsize(cm) // 1024, BUDGET["claude_kb"]), fix="rewrite")
    for d, key in (("agents", "agent_lines"), ("commands", "command_lines"), ("rules", "rule_lines")):
        for fp in sorted(glob.glob(env.p(".claude", d, "*.md"))):
            if lines(fp) > BUDGET[key]:
                F.add("S1", "⚠", fp, "%d 行(予算 %d)" % (lines(fp), BUDGET[key]), fix="rewrite")
    for name in env.edo_skills():
        d = env.skill_dir(name)
        if not d:
            continue
        sk = os.path.join(d, "SKILL.md")
        if lines(sk) > BUDGET["skill_lines"]:
            F.add("S1", "⚠", sk, "%d 行(予算 %d)" % (lines(sk), BUDGET["skill_lines"]), fix="rewrite")
        for dp, _, fs in os.walk(os.path.join(d, "references")):
            for f in fs:
                fp = os.path.join(dp, f)
                if f.endswith(".md") and f not in REF_ALLOW and lines(fp) > BUDGET["ref_lines"]:
                    F.add("S1", "⚠", fp, "%d 行(予算 %d)— 分割か目次" % (lines(fp), BUDGET["ref_lines"]), fix="manual")
                if f in REF_ALLOW and not re.search(r"^#+ .*(目次|索引)", read(fp), re.M):
                    F.add("S1", "⚠", fp, "長い参照に目次が無い", fix="rewrite")
    if os.path.isdir(env.memory):
        tot = 0
        for f in sorted(os.listdir(env.memory)):
            if not f.endswith(".md"):
                continue
            fp = os.path.join(env.memory, f)
            n = lines(fp)
            tot += n
            lim = BUDGET["memory_index"] if f == "MEMORY.md" else BUDGET["memory_file"]
            if n > lim:
                F.add("S1", "⚠", fp, "%d 行(予算 %d)" % (n, lim), fix="rewrite")
        if tot > BUDGET["memory_total"]:
            F.add("S1", "⚠", env.memory, "メモリ合計 %d 行(予算 %d)— consolidate-memory" % (tot, BUDGET["memory_total"]),
                  fix="manual")
    ls = env.p("docs", "lessons.md")
    if os.path.isfile(ls) and lines(ls) > BUDGET["lessons_lines"]:
        F.add("S1", "⚠", ls, "%d 行(予算 %d)— 処置済の行を畳む" % (lines(ls), BUDGET["lessons_lines"]), fix="manual")


def chk_V1_V2(env, F):
    """frontmatter の妥当性: 役(V1)、コマンド・rules・workflow(V2)。"""
    for fp in env.agents():
        name = os.path.basename(fp)[:-3]
        txt = read(fp)
        fm, body = frontmatter(txt)
        if fm is None:
            F.add("V1", "⛔", fp, "frontmatter が読めない", quick=True)
            continue
        if fm.get("name") != name:
            F.add("V1", "⚠", fp, "name `%s` がファイル名と違う" % fm.get("name"), fix="rewrite")
        if not (fm.get("description") or "").strip():
            F.add("V1", "⚠", fp, "description が無い", fix="rewrite")
        model = fm.get("model")
        if model and model not in MODELS and not str(model).startswith("claude-"):
            F.add("V1", "⚠", fp, "model `%s` が未知" % model, fix="rewrite")
        tools = fm.get("tools")
        if isinstance(tools, str):
            for t in [t.strip() for t in tools.split(",") if t.strip()]:
                if t not in KNOWN_TOOLS and not t.startswith("mcp__") and t != "*":
                    F.add("V1", "⚠", fp, "tools に未知の `%s`" % t, fix="rewrite")
            ro = "read-only" in txt or "read only" in txt
            if ro and re.search(r"\b(Edit|Write)\b", tools):
                F.add("V1", "⚠", fp, "read-only と言いながら tools に Edit/Write", fix="rewrite")
        mt = fm.get("maxTurns")
        if mt is not None and not str(mt).isdigit():
            F.add("V1", "⚠", fp, "maxTurns `%s` が整数でない" % mt, fix="rewrite")
        if fm.get("memory") and fm["memory"] not in MEMORY_KINDS:
            F.add("V1", "⚠", fp, "memory `%s` が未知" % fm["memory"], fix="rewrite")
        if fm.get("effort") and fm["effort"] not in EFFORTS:
            F.add("V1", "⚠", fp, "effort `%s` が未知" % fm["effort"], fix="rewrite")
        if name in REVIEWERS and "edo_review_stop.py" not in " ".join(fm.get("hooks") or []):
            F.add("V1", "⚠", fp, "検分役なのに hooks.Stop → edo_review_stop.py が無い(返答の上限が効かない)", fix="rewrite")
    for fp in sorted(glob.glob(env.p(".claude", "commands", "*.md"))):
        fm, _ = frontmatter(read(fp))
        if not fm or not (fm.get("description") or "").strip():
            F.add("V2", "⚠", fp, "コマンドに description が無い", fix="rewrite")
    tracked = None
    for fp in sorted(glob.glob(env.p(".claude", "rules", "*.md"))):
        fm, _ = frontmatter(read(fp))
        for pat in (fm or {}).get("paths") or []:
            tracked = env.tracked() if tracked is None else tracked
            pre = pat.split("**")[0].rstrip("/") if "**" in pat else None
            ok = any(t.startswith(pre + "/") for t in tracked) if pre else any(fnmatch.fnmatch(t, pat) for t in tracked)
            if not ok:
                F.add("V2", "⚠", fp, "paths `%s` に当たる追跡ファイルが無い" % pat, fix="rewrite")
    for fp in sorted(glob.glob(env.p(".claude", "workflows", "*.js"))):
        want = os.path.basename(fp)[:-3]
        m = re.search(r"export const meta\s*=\s*\{[^}]*?name:\s*['\"]([\w-]+)['\"]", read(fp), re.S)
        if not m or m.group(1) != want:
            F.add("V2", "⚠", fp, "meta.name が `%s` でない(%s)" % (want, m.group(1) if m else "無い"), fix="rewrite")


def chk_G1(env, F):
    """関門には自己検査(docs/verification-loops.md)。"""
    for fp in sorted(glob.glob(env.p("Tools", "Sashizu", "*_gate.py"))) + [env.p("Tools", "Session", "config_doctor.py")]:
        if os.path.isfile(fp) and "--selftest" not in read(fp):
            F.add("G1", "⚠", fp, "関門に --selftest が無い(検出が死んでも気づけない)", fix="manual")


def chk_K1(env, F):
    """ゴミ。"""
    roots = [env.p(".claude"), env.p("Tools"), env.p("docs"), env.skills]
    seen = set()
    for base in roots:
        if not os.path.isdir(base):
            continue
        for dp, ds, fs in os.walk(base, followlinks=False):
            if "/.claude/worktrees" in dp or "/.git" in dp:
                ds[:] = []
                continue
            for n in ds + fs:
                if any(fnmatch.fnmatch(n, g) for g in CRUFT_GLOBS):
                    p = os.path.join(dp, n)
                    if p not in seen:
                        seen.add(p)
                        F.add("K1", "⚠", p, "ゴミ(%s)" % n, fix="rm %s" % env.rel(p))
    for t in env.tracked():
        if "__pycache__" in t:
            F.add("K1", "⚠", env.p(t), "追跡された __pycache__", fix="rm %s" % t)
    locks = env.p(".claude", "locks")
    if os.path.isdir(locks) and env.is_git and "edo-locks" in read(env.p("Tools", "Session", "edo_session.py")):
        F.add("K1", "⚠", locks, "旧い claim 置き場(今は .git/edo-locks)", fix="rm .claude/locks")
    for wp, br in env.worktrees():
        if br == "(detached)":
            F.add("K1", "⚠", wp, "detached HEAD の worktree(git worktree remove を検討)", fix="manual")


def chk_W(env, F):
    """worktree の設定が main と違う: main に無いファイル(W1)・内容の違い(W2)。"""
    def sha(b):
        return hashlib.sha256(b).hexdigest()

    def rb(fp):
        with open(fp, "rb") as fh:
            return fh.read()

    def files(base):
        out = {}
        for d in CONFIG_DIRS:
            for fp in glob.glob(os.path.join(base, d, "*")):
                if os.path.isfile(fp) and fp.endswith((".md", ".py", ".sh", ".js", ".json")):
                    out[os.path.relpath(fp, base)] = sha(rb(fp))
        for f in CONFIG_FILES:
            fp = os.path.join(base, f)
            if os.path.isfile(fp):
                out[f] = sha(rb(fp))
        return out

    def files_committed(root):
        """main ブランチの**最新コミット**の設定。⛔ main の作業ツリーの現物とは比べない —
        sync-tools が配るのはコミット済みの内容で(別セッションの編集中の版は配らない)、
        現物と比べると main に書きかけがあるあいだ「配れ」と鳴り続け、配っても消えない偽の警報になる。
        main ブランチが無ければ None(呼び手が作業ツリーへ戻る)。"""
        def cat(rp):
            r = subprocess.run(["git", "-C", root, "cat-file", "blob", "main:" + rp], capture_output=True)
            return r.stdout if r.returncode == 0 else None
        if not _git(root, "rev-parse", "--verify", "-q", "main"):
            return None
        out = {}
        for d in CONFIG_DIRS:
            r = subprocess.run(["git", "-C", root, "ls-tree", "-z", "main", d + "/"], capture_output=True)
            for ent in r.stdout.split(b"\0"):
                meta, _, path = ent.partition(b"\t")
                if len(meta.split()) >= 2 and meta.split()[1] == b"blob":
                    rp = path.decode("utf-8")
                    if rp.endswith((".md", ".py", ".sh", ".js", ".json")):
                        data = cat(rp)
                        if data is not None:
                            out[rp] = sha(data)
        for f in CONFIG_FILES:
            data = cat(f)
            if data is not None:
                out[f] = sha(data)
        return out
    main = files_committed(env.root)
    if main is None:
        main = files(env.root)
    stale = []
    for wp, br in env.worktrees():
        wf = files(wp)
        here = os.path.realpath(wp) == os.path.realpath(env.cwd)
        for rel in sorted(set(wf) - set(main)):
            F.add("W1", "⛔" if here else "⚠", os.path.join(wp, rel),
                  "worktree `%s` にだけある(main で廃止済)" % os.path.basename(wp), fix="sync-rm", quick=here)
        diff = sorted(r for r in set(wf) & set(main) if wf[r] != main[r])
        if diff:
            stale.append("%s %d" % (os.path.basename(wp), len(diff)))
    if stale:
        F.add("W2", "⚠", env.p(".claude", "worktrees"), "worktree の設定が main と違う(%s)— sync-tools で配る" % ", ".join(stale),
              fix="keep \"main を取り込むまで古い\"")


def _sync_paths(env):
    src = read(env.p("Tools", "Session", "edo_session.py"))
    m = re.search(r"^SYNC_PATHS\s*=\s*(\[.*?\])\s*$", src, re.S | re.M)
    if not m:
        return None, src
    try:
        return ast.literal_eval(re.sub(r"#.*", "", m.group(1))), src
    except Exception:
        return None, src


def chk_Y1(env, F):
    """sync-tools の網羅: 全 worktree へ配るべき設定が SYNC_PATHS に入っているか。"""
    paths, src = _sync_paths(env)
    if paths is None:
        return
    es = env.p("Tools", "Session", "edo_session.py")
    want = set()
    for t in env.tracked():
        if t.startswith(".claude/") and not t.startswith((".claude/worktrees", ".claude/locks", ".claude/settings.local")):
            parts = t.split("/")
            want.add("/".join(parts[:2]) if len(parts) > 2 else t)
        if t.startswith("Tools/Sashizu/") and t.endswith("_gate.py"):
            want.add(t)
    for x in ("CLAUDE.md", "Tools/Session", "docs/lessons.md"):
        if os.path.exists(env.p(x)):
            want.add(x)
    for d in re.findall(r"`(docs/[\w-]+\.md)`", read(env.p("CLAUDE.md"))):
        if os.path.isfile(env.p(d)):
            want.add(d)
    covered = lambda w: any(w == p or w.startswith(p.rstrip("/") + "/") for p in paths)
    for w in sorted(want):
        if not covered(w):
            F.add("Y1", "⚠", es, "SYNC_PATHS に `%s` が無い(worktree の写しが古いまま動く)" % w, fix="sync-add %s" % w)
    if any(p.startswith("Tools/Skills") for p in paths):
        F.add("Y1", "⚠", es, "SYNC_PATHS に Tools/Skills がある(スキルは symlink で 1 本。写しを作らない)", fix="rewrite")
    m = re.search(r"endswith\(\((.*?)\)\)", src)
    if m and (".js" not in m.group(1) or ".json" not in m.group(1)):
        F.add("Y1", "⚠", es, "sync-tools が写す拡張子に .js / .json が無い(workflows・settings が配られない)", fix="rewrite")


def chk_SK1(env, F):
    """スキル(Tools/Skills)の未コミットが放置されていないか。"""
    ts = env.p("Tools", "Skills")
    if not env.is_git or not os.path.isdir(ts):
        return
    out = _git(env.root, "status", "--porcelain", "--", "Tools/Skills", timeout=20)
    old = []
    for ln in out.split("\n"):
        if not ln.strip():
            continue
        fp = env.p(ln[3:].strip().split(" -> ")[-1])
        try:
            if env.now - os.path.getmtime(fp) > UNCOMMITTED_DAYS * 86400:
                old.append(os.path.relpath(fp, ts))
        except Exception:
            pass
    if old:
        F.add("SK1", "⚠", ts, "スキルの未コミットが %d 日超: %s" % (UNCOMMITTED_DAYS, ", ".join(old[:4])), fix="manual")


def chk_L(env, F):
    """教訓の処置: タグ無し(L1)・タグの先に痕跡が無い(L2)。"""
    fp = env.p("docs", "lessons.md")
    if not os.path.isfile(fp):
        return
    claude = read(env.p("CLAUDE.md"))
    for i, ln in enumerate(read(fp).split("\n"), 1):
        m = LESSON_LINE.match(ln)
        if not m:
            continue
        date, title, iid = m.groups()
        tag = LESSON_TAG.search(ln)
        age = (env.now - time.mktime(time.strptime(date, "%Y-%m-%d"))) / 86400
        if not tag:
            if age > LESSON_DUE_DAYS:
                F.add("L1", "⚠", fp, "行 %d: %s(%d 日)に処置タグ(→規則N/→スキル:x/→メモリ:f/→不要/→保留:日付)が無い"
                      % (i, iid, age), fix="lesson-tag →保留:%s" % time.strftime("%Y-%m-%d", time.localtime(env.now + 30 * 86400)))
            continue
        t = tag.group(1)
        key = title[:8]
        if t.startswith("規則"):
            n = t[2:]
            if not re.search(r"^%s\. " % n, claude, re.M):
                F.add("L2", "⚠", fp, "行 %d: →%s だが CLAUDE.md に規則 %s が無い" % (i, t, n), fix="rewrite")
        elif t.startswith("スキル:"):
            d = env.skill_dir(t[4:])
            blob = "" if not d else " ".join(read(os.path.join(dp, f)) for dp, _, fs in os.walk(d) for f in fs if f.endswith(".md"))
            if not d or (iid not in blob and key not in blob):
                F.add("L2", "⚠", fp, "行 %d: →%s の先に %s も「%s」も無い" % (i, t, iid, key), fix="rewrite")
        elif t.startswith("メモリ:"):
            mf = os.path.join(env.memory, t[4:])
            blob = read(mf)
            if not blob or (iid not in blob and key not in blob):
                F.add("L2", "⚠", fp, "行 %d: →%s の先に %s も「%s」も無い" % (i, t, iid, key), fix="rewrite")
        elif t.startswith("保留:"):
            due = time.mktime(time.strptime(t[3:], "%Y-%m-%d"))
            if env.now > due:
                F.add("L1", "⚠", fp, "行 %d: %s の保留期限 %s を過ぎた" % (i, iid, t[3:]), fix="lesson-tag →不要")


def _usage(env):
    """(台帳の要約, 記録の最古 epoch) — 台帳を差分更新してから読む。transcript が無ければ (None, None)。"""
    dirs = env.transcripts_override if env.transcripts_override is not None else UL.project_dirs(env.root)
    if not dirs:
        return None, None
    return UL.summarize(UL.scan(env.state, dirs))


def chk_U(env, F):
    """利用実績(EDO-0221)。U1 役・スキルが 30 日呼ばれていない / U2 参照が 60 日読まれていない。
    ⚠ 挨拶(--quick)では回さない(transcript を舐める)。⚠ 記録が 30 日に満たない間は判定しない —
    「一度も呼ばれていない」は記録が足りないだけかもしれない。⚠ 新しく入った物は窓の分だけ猶予する。"""
    if env.quick:
        return
    tot, first = _usage(env)
    if not first:
        return
    cover = int((env.now - first) / 86400)
    if cover < USAGE_MIN_COVER:
        return
    since = time.strftime("%Y-%m-%d", time.localtime(first))

    for fp in env.agents():
        name = os.path.basename(fp)[:-3]
        w = idle_from(env, tot.get("role:" + name, (0, 0)), IDLE_ROLE_DAYS, fp, cover, since)
        if w:
            F.add("U1", "⚠", fp, "役 %s は %s呼ばれていない(最後 %s)" % ((name,) + w), fix="")
    for name in env.edo_skills():
        d = env.skill_dir(name)
        if not d:
            continue
        w = idle_from(env, tot.get("skill:" + name, (0, 0)), IDLE_ROLE_DAYS, os.path.join(d, "SKILL.md"), cover, since)
        if w:
            F.add("U1", "⚠", os.path.join(d, "SKILL.md"), "スキル %s は %s呼ばれていない(最後 %s)" % ((name,) + w), fix="")
    refs = {}       # 台帳の鍵 → 実ファイル
    for name in env.edo_skills():
        d = env.skill_dir(name)
        for fp in sorted(glob.glob(os.path.join(d, "references", "**", "*.md"), recursive=True)) if d else []:
            refs["%s/%s" % (name, os.path.relpath(fp, d))] = fp
    base_count = {}
    for k in refs:
        b = k.split("/references/", 1)[-1]
        base_count[b] = base_count.get(b, 0) + 1
    for k, fp in refs.items():
        b = k.split("/references/", 1)[-1]
        alts = ["path:" + k] + (["base:" + b] if base_count[b] == 1 else [])
        best = max((tot.get(a, (0, 0)) for a in alts), key=lambda v: v[1])
        w = idle_from(env, best, IDLE_REF_DAYS, fp, cover, since)
        if w:
            F.add("U2", "⚠", fp, "参照 %s は %s読まれていない(最後 %s)" % ((k,) + w), fix="")
    for doc in sorted({m for f in env.config_texts() if f.endswith("CLAUDE.md")
                       for m in re.findall(r"docs/[\w./-]+\.md", read(f))}):
        fp = env.p(doc)
        if not os.path.isfile(fp):
            continue
        w = idle_from(env, tot.get("path:" + doc, (0, 0)), IDLE_REF_DAYS, fp, cover, since)
        if w:
            F.add("U2", "⚠", fp, "参照 %s は %s読まれていない(最後 %s)" % ((doc,) + w), fix="")


def idle_from(env, hit, thr, path, cover, since):
    """→ (窓の言い方, 最後の日付|"一度も無し")。窓の中で使われた・入ったばかりなら None。"""
    n, last = hit
    win = min(thr, cover) * 86400
    if last and env.now - last <= win:
        return None
    added = env.added_at(path)
    if added and env.now - added <= win:
        return None
    span = "%d 日" % thr if cover >= thr else "記録の範囲(%s〜)" % since
    return span, (time.strftime("%Y-%m-%d", time.localtime(last)) if last else "一度も無し")


def chk_N1(env, F):
    last = os.path.join(env.state, "last.json")
    try:
        t = json.load(open(last, encoding="utf-8")).get("t", 0)
    except Exception:
        t = 0
    days = int((env.now - t) / 86400) if t else None
    if days is None or days > NUDGE_DAYS:
        F.add("N1", "行", "", "手入れ: %s(週 1 の目安 — /teire)" % ("道具改めをまだ一度も回していない" if days is None
                                                                 else "前回の道具改めから %d 日" % days), fix="")


CHECKS = [chk_R1_R2, chk_R3, chk_R4, chk_R5, chk_R6_V3, chk_R7, chk_R8, chk_Q, chk_C, chk_S1, chk_V1_V2, chk_G1,
          chk_K1, chk_W, chk_Y1, chk_SK1, chk_L, chk_U]


def run_checks(env, quick=False):
    F = Findings(env)
    env.quick = quick
    for c in CHECKS:
        try:
            c(env, F)
        except Exception as e:      # ⚠ 検査が落ちても他の検査は続ける。落ちたことは所見にする
            F.add("XX", "⚠", "", "検査 %s が例外で落ちた: %s" % (c.__name__, str(e)[:80]), fix="manual")
    chk_N1(env, F)
    acks = _load(env, "ack.json")
    for f in F.items:
        if f["sev"] != "⛔" and f["key"] in acks:
            f["acked"] = acks[f["key"]]
    return F


def _load(env, name):
    try:
        return json.load(open(os.path.join(env.state, name), encoding="utf-8"))
    except Exception:
        return {}


def _save(env, name, obj):
    os.makedirs(env.state, exist_ok=True)
    tmp = os.path.join(env.state, name + ".tmp")
    json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(env.state, name))


# ── 出口 ─────────────────────────────────────────────────────────────────
def cmd_quick(env):
    F = run_checks(env, quick=True)
    bad = [f for f in F.items if f["sev"] == "⛔"]
    nudge = [f for f in F.items if f["id"] == "N1"]
    if bad:
        print("道具改め — **設定に破れがある**(`python3 Tools/Session/config_doctor.py --table`)")
        for f in bad[:QUICK_MAX]:
            print("  ⛔ %s %s — %s" % (f["id"], f["where"], f["text"]))
        if len(bad) > QUICK_MAX:
            print("  … 他 %d 件" % (len(bad) - QUICK_MAX))
        print("  ⛔ 参照が切れた役・スキル・フックは「黙って古い規則で動く」(EDO-0076 型)。正典: `docs/teire.md`")
    for f in nudge:
        print(f["text"])
    return 1 if bad else 0


def cmd_table(env, write_state=True):
    F = run_checks(env)
    rows = [f for f in F.items if f["id"] != "N1"]
    live = [f for f in rows if "acked" not in f]
    print("# 道具改め — 所見と処置の案(%s・%d 件・承認済 %d 件は畳んだ)\n" %
          (time.strftime("%Y-%m-%d"), len(live), len(rows) - len(live)))
    print("処置の列を直してから `python3 Tools/Session/config_doctor.py --apply <このファイル>`。語彙は同スクリプトの docstring。"
          "⛔ は keep で黙らせられない。\n")
    print("| 鍵 | 重さ | 場所 | 所見 | 処置 |\n|---|---|---|---|---|")
    agg = {}
    for f in sorted(live, key=lambda f: (f["sev"] != "⛔", f["id"], f["where"])):
        agg[f["sev"]] = agg.get(f["sev"], 0) + 1
        print("| %s | %s | %s | %s | `%s` |" % (f["key"], f["sev"], f["where"].replace("|", "｜"),
                                              f["text"].replace("|", "｜"), f["fix"] or "keep"))
    print("\n内訳: " + " / ".join("%s %d" % kv for kv in sorted(agg.items())))
    if write_state:
        by_id = {}
        for f in live:
            by_id[f["id"]] = by_id.get(f["id"], 0) + 1
        _save(env, "last.json", {"t": env.now, "mode": "table", "counts": agg, "by_id": by_id,
                                 "ids": sorted(by_id)})
    return 1 if agg.get("⛔") else 0


def _board(env, *args):
    r = subprocess.run([sys.executable, os.path.join(env.root, "Tools", "Session", "edo_board.py")] + list(args),
                       capture_output=True, text=True, cwd=env.root)
    return r.returncode, (r.stdout + r.stderr).strip().split("\n")[0]


def _abs(env, where):
    if where.startswith("<skills>/"):
        return os.path.join(env.skills, where[9:])
    if where.startswith("<memory>/"):
        return os.path.join(env.memory, where[9:])
    return where if os.path.isabs(where) else env.p(where)


def cmd_apply(env, fp):
    rows = re.findall(r"^\| ([A-Z0-9]+#[0-9a-f]{8}) \| (\S+) \| (.*?) \| (.*?) \| `([^`]*)` \|$", read(fp), re.M)
    F = run_checks(env)
    by = {f["key"]: f for f in F.items}
    acks = _load(env, "ack.json")
    n, log = 0, []
    for key, sev, where, text, act in rows:
        f = by.get(key)
        if f is None:
            print("? %s は今の走査に無い(直った/変わった)" % key)
            continue
        kind, _, arg = act.strip().partition(" ")
        kind, _, karg = kind.partition(":")
        target = _abs(env, f["where"])
        try:
            if kind == "keep":
                if f["sev"] == "⛔":
                    print("✗ %s ⛔ は keep できない" % key)
                    continue
                acks[key] = {"why": arg.strip('"'), "t": env.now}
            elif kind == "rm":
                p = _abs(env, arg or f["where"])
                if os.path.isdir(p) and not os.path.islink(p):
                    import shutil
                    shutil.rmtree(p)
                else:
                    os.remove(p)
                _git(env.root, "rm", "-q", "--cached", "-r", "--ignore-unmatch", "--", p)
            elif kind == "sync-rm":
                if f["id"] != "W1":
                    print("✗ %s sync-rm は W1 にだけ効く" % key)
                    continue
                os.remove(target)
            elif kind == "index-add":
                if f["id"] != "R7":
                    # ⛔ この処置は MEMORY.md にしか効かない。典拠台帳(R8)は確度の行を選ぶ判断が要る
                    print("✗ %s index-add は R7(MEMORY.md)にだけ効く — 手で索引へ入れる" % key)
                    continue
                name = os.path.basename(target)
                title = re.search(r"^name:\s*(.+)$", read(target), re.M)
                desc = re.search(r"^description:\s*(.+)$", read(target), re.M)
                with open(os.path.join(env.memory, "MEMORY.md"), "a", encoding="utf-8") as w:
                    w.write("- [%s](%s) — %s\n" % ((title.group(1) if title else name[:-3]).strip(), name,
                                                  (desc.group(1) if desc else "").strip()[:80]))
            elif kind == "index-rm":
                idx = os.path.join(env.memory, "MEMORY.md")
                miss = re.search(r"`([\w.-]+\.md)`", f["text"]).group(1)
                lines = [l for l in read(idx).split("\n") if "(%s)" % miss not in l]
                io.open(idx, "w", encoding="utf-8").write("\n".join(lines))
            elif kind == "remeasure":
                m = re.search(r"行 (\d+): `([\d,.]+)(KB|MB|点)` は今 (\S+)\(", f["text"])
                ln_no, old, unit, new = int(m.group(1)), m.group(2), m.group(3), m.group(4)
                lines = read(target).split("\n")
                newv = ("{:,}".format(int(float(new))) if "," in old else str(int(float(new))))
                lines[ln_no - 1] = lines[ln_no - 1].replace(old + unit, newv + unit, 1).replace(old + " " + unit, newv + " " + unit, 1)
                io.open(target, "w", encoding="utf-8").write("\n".join(lines))
            elif kind == "lesson-tag":
                m = re.search(r"行 (\d+):", f["text"])
                lines = read(target).split("\n")
                i = int(m.group(1)) - 1
                lines[i] = LESSON_TAG.sub("", lines[i]).rstrip() + " " + arg.strip()
                io.open(target, "w", encoding="utf-8").write("\n".join(lines))
            elif kind == "task":
                est = karg or "infra"
                title = arg.strip().strip('"') or ("%s %s — %s" % (f["id"], f["where"], f["text"]))[:90]
                rc, line = _board(env, "post", "--estate", est, "--type", "task", "--owner", est,
                                  "--title", title[:90], "--msg", "道具改め %s: %s %s" % (key, f["where"], f["text"]))
                print("   " + line)
                acks[key] = {"why": "task → 掲示板", "t": env.now}
            else:
                log.append("- %s `%s` は手で: %s %s — %s" % (key, act, f["id"], f["where"], f["text"]))
                continue
            n += 1
            print("%s ← %s" % (key, act))
        except Exception as e:
            print("✗ %s %s: %s" % (key, act, str(e)[:80]))
    _save(env, "ack.json", acks)
    last = _load(env, "last.json")
    last.update({"t": env.now, "mode": "apply", "applied": n})
    _save(env, "last.json", last)
    print("実行 %d 件" % n)
    if log:
        print("\n手で直す物(意味的な処置):\n" + "\n".join(log))
    return 0


def cmd_deep(env):
    rc = cmd_table(env)
    print("\n## 関門の自己検査\n")
    gates = [(g, "--selftest") for g in sorted(glob.glob(env.p("Tools", "Sashizu", "*_gate.py")))
             + [os.path.abspath(__file__), env.p("Tools", "Session", "usage_ledger.py")]]
    gates.append((env.p("Tools", "Session", "edo_session.py"), "selftest"))      # 設定コミットの関門(EDO-0221)
    for g, arg in gates:
        if not os.path.isfile(g) or arg.lstrip("-") not in read(g):
            print("⚠ %s に %s が無い" % (env.rel(g), arg))
            continue
        r = subprocess.run([sys.executable, g, arg], capture_output=True, text=True, cwd=env.root)
        print("%s %s" % ("⭕" if r.returncode == 0 else "⛔", env.rel(g)))
        if r.returncode:
            print("   " + (r.stdout + r.stderr).strip().replace("\n", "\n   ")[:1500])
            rc = 1
    print("\n## 挨拶の予算\n")
    g = env.p(".claude", "hooks", "edo_greet.py")
    if os.path.isfile(g):
        t0 = time.time()
        r = subprocess.run([sys.executable, g], input="{}", capture_output=True, text=True, cwd=env.root,
                           env=dict(os.environ, CLAUDE_PROJECT_DIR=env.root))
        dt, nl = time.time() - t0, len(r.stdout.strip().split("\n"))
        print("%s 挨拶 %.1f 秒 / %d 行(目安 8 秒 / 25 行)" % ("⭕" if dt <= 8 and nl <= 25 else "⚠", dt, nl))
    print("\n## 月次の手作業(道具では測れない物)\n")
    print("- メモリ: `Skill(anthropic-skills:consolidate-memory)` で重複・古い事実・索引を整理する")
    print("- スキル: `Skill(anthropic-skills:skill-creator)` で edo 各スキルの description の発火精度と SKILL.md の長さを見直す")
    print("- 利用実績: 表の U1(30 日呼ばれない役・スキル)/ U2(60 日読まれない参照)を見て、畳む・統合する・残す(keep + 理由)を決める。"
          "台帳は `python3 Tools/Session/usage_ledger.py`")
    return rc


# ── 自己検査 ─────────────────────────────────────────────────────────────
def _fixture(base):
    """無傷な最小の設定一式を base に作る。"""
    def w(rel, txt):
        fp = os.path.join(base, rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        io.open(fp, "w", encoding="utf-8").write(txt)
    today = time.strftime("%Y-%m-%d")
    w("CLAUDE.md", "# fx\n\n## 絶対規則\n\n1. 規則一。\n2. 規則二。\n\n| 話題 | 読む物 |\n|---|---|\n| a | スキル `sk` |\n"
                   "| b | `docs/teire.md` |\n| c | **`edo-alpha`** |\n")
    w(".claude/agents/edo-alpha.md", "---\nname: edo-alpha\ndescription: 役アルファ。read-only。\nmodel: opus\n"
                                     "tools: Read, Grep, Bash, Skill\nmaxTurns: 10\n---\n\n1. `Skill(sk)` — `references/a.md` §1 を読む。\n"
                                     "python3 Tools/Sashizu/x_gate.py を回す。\n<!-- obl:alpha-write canon --> 必ず memory へ書く。\n")
    w(".claude/commands/go.md", "---\ndescription: go\n---\n\n`Workflow(name: \"wf\")` を回す。\n")
    w(".claude/workflows/wf.js", "export const meta = {\n  name: 'wf',\n  description: 'x',\n}\n")
    w(".claude/rules/r.md", "---\npaths:\n  - \"docs/**\"\n---\nrule\n")
    w(".claude/hooks/h.py", "print('ok')\n")
    w(".claude/settings.json", json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/h.py", "timeout": 5}]}]}}))
    w("docs/teire.md", "# t\n")
    w("docs/lessons.md", "# l\n\n- %s **教訓一 その先**(EDO-0001・cross) →規則1\n" % today)
    w("Tools/Sashizu/x_gate.py", "import sys\nif '--selftest' in sys.argv: pass\n")
    w("Tools/Session/edo_session.py", "SYNC_PATHS = [\"Tools/Session\", \"CLAUDE.md\", \".claude/hooks\", \".claude/agents\",\n"
                                      "              \".claude/commands\", \".claude/rules\", \".claude/workflows\", \".claude/settings.json\",\n"
                                      "              \"docs/lessons.md\", \"docs/teire.md\", \"Tools/Sashizu/x_gate.py\"]\n"
                                      "X = fn.endswith((\".py\", \".md\", \".js\", \".json\"))\n")
    w("Tools/Session/config_doctor.py", "# --selftest\n")
    w("skills/sk/SKILL.md", "---\nname: sk\ndescription: skill sk\n---\n\n- `references/a.md`\n- `references/b.md`\n"
                            "- `references/sources.md`\n")
    w("skills/sk/references/a.md", "# a\n\n## §1 節\n")
    w("skills/sk/references/b.md", "# b\n")
    # 典拠台帳の型 — 索引と項の見出しが揃っている無傷な版(R8 の土台)
    w("skills/sk/references/sources.md",
      "# 典拠一覧\n\n## 索引 — 確度別の [ID] 一覧\n\n**B 一般類型** (1件)\n\n\u3000`甲`\n\n---\n\n"
      "### [甲] 確度B\n本文。\n")
    w("memory/MEMORY.md", "# idx\n\n- [one](one.md) — x\n")
    w("memory/one.md", "---\nname: one\ndescription: d\n---\nfact\n")
    os.makedirs(os.path.join(base, "wt", ".claude", "agents"))     # worktree は空の .claude(W の型だけが植える)
    w("gsettings.json", json.dumps({"hooks": {}}))
    _transcripts(base)


def _transcripts(base, role_days=2, skill_days=2, refs=("a", "b", "sources", "orphan"), doc=True, cover=70):
    """利用実績の fixture。既定は「全部が最近使われ、記録は 70 日前から」の無傷な版。
    role_days / skill_days=None なら一度も無し。cover は記録の最古(日前)。"""
    def ts(days):
        return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()

    def tu(name, inp, days):
        return json.dumps({"type": "assistant", "timestamp": ts(days), "message": {"content": [
            {"type": "tool_use", "id": "x", "name": name, "input": inp}]}}) + "\n"
    out = tu("Bash", {"command": "true"}, cover)
    if role_days is not None:
        out += tu("Agent", {"subagent_type": "edo-alpha"}, role_days)
    if skill_days is not None:
        out += tu("Skill", {"skill": "sk"}, skill_days)
    for r in refs:
        out += tu("Read", {"file_path": "/h/.claude/skills/sk/references/%s.md" % r}, 2)
    if doc:
        out += tu("Bash", {"command": "cat docs/teire.md"}, 2)
    _w(base, "tr/s1.jsonl", out)


def _run_fixture(base, extra=None):
    args = ["--root", os.path.join(base), "--skills-dir", os.path.join(base, "skills"),
            "--memory-dir", os.path.join(base, "memory"), "--global-settings", os.path.join(base, "gsettings.json"),
            "--state-dir", os.path.join(base, "state"), "--worktrees", os.path.join(base, "wt"),
            "--transcripts-dir", os.path.join(base, "tr")]
    env = Env(parse(args + (extra or [])))
    F = run_checks(env)
    return sorted({f["id"] for f in F.items if f["id"] != "N1"}), F


def selftest():
    """⛔ 落ちたら**この道具の検出が死んでいる**。設定でなく道具を疑うこと。"""
    import shutil
    ng = 0
    base = tempfile.mkdtemp(prefix="teire-")
    try:
        _fixture(base)
        ids, F = _run_fixture(base)
        if ids:
            print("⛔ 無傷な版で鳴った(誤検出): %s" % ", ".join("%s %s" % (f["id"], f["text"]) for f in F.items if f["id"] != "N1"))
            ng += 1
        else:
            print("⭕ 無傷な版では鳴らない")
        old = time.strftime("%Y-%m-%d", time.localtime(time.time() - 40 * 86400))
        CASES = [
            ("R1 役が無いスキルを指す", lambda: _app(base, ".claude/agents/edo-alpha.md", "\n`Skill(ghost)`\n"), "R1"),
            ("R2 役が無い参照を指す", lambda: _app(base, ".claude/agents/edo-alpha.md", "\n`Skill(sk)` の `references/nope.md`\n"), "R2"),
            ("R2 §が無い", lambda: _app(base, ".claude/agents/edo-alpha.md", "\n`Skill(sk)` の `references/a.md` §9z\n"), "R2"),
            ("R3 表が無い文書を指す", lambda: _app(base, "CLAUDE.md", "| d | `docs/gone.md` |\n"), "R3"),
            ("R3 表が無い役を指す", lambda: _app(base, "CLAUDE.md", "| e | `edo-ghost` |\n"), "R3"),
            ("R4 無い Workflow", lambda: _app(base, ".claude/commands/go.md", "\n`Workflow(name: \"nope\")`\n"), "R4"),
            ("R4 無い道具", lambda: _app(base, ".claude/commands/go.md", "\npython3 Tools/Session/gone.py\n"), "R4"),
            ("R5 フックが無いスクリプトを指す", lambda: _rep(base, ".claude/settings.json", "h.py", "gone.py"), "R5"),
            ("R5 matcher が不正", lambda: _set(base, ".claude/settings.json", {"hooks": {"PreToolUse": [{"matcher": "(",
                "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/h.py", "timeout": 5}]}]}}), "R5"),
            ("R5 構文エラー", lambda: _app(base, ".claude/hooks/h.py", "def (\n"), "R5"),
            ("R5 edo フックがグローバル側", lambda: _set(base, "gsettings.json", {"hooks": {"PostToolUse": [{"matcher": "Bash",
                "hooks": [{"type": "command", "command": "bash %s/.claude/hooks/edo_x.sh" % base, "timeout": 5}]}]}}), "R5"),
            ("R6 SKILL.md が無い参照を挙げる", lambda: _app(base, "skills/sk/SKILL.md", "- `references/zz.md`\n"), "R6"),
            ("R6 辿れない参照ファイル", lambda: _w(base, "skills/sk/references/orphan.md", "# o\n"), "R6"),
            ("R7 索引が無いファイルを指す", lambda: _app(base, "memory/MEMORY.md", "- [two](two.md) — y\n"), "R7"),
            ("R7 索引に無いファイル", lambda: _w(base, "memory/three.md", "fact\n"), "R7"),
            ("Q1 計測キー無しの数字", lambda: _app(base, ".claude/agents/edo-alpha.md", "\n索引は 154KB ある。\n"), "Q1"),
            ("Q2 計測とずれ", lambda: _app(base, "memory/MEMORY.md", "- 目録 2,681点 <!-- measured: count:memory-files -->\n"), "Q2"),
            ("Q3 期限切れの移行期間", lambda: _app(base, "CLAUDE.md", "移行期間(%s 裁定B)。\n" % old), "Q3"),
            ("C1 必ず/しない の矛盾", lambda: (_rep(base, ".claude/agents/edo-alpha.md", "description: 役アルファ。read-only。",
                "description: 役アルファ。read-only。x.md へ必ず追記する。"),
                _app(base, ".claude/agents/edo-alpha.md", "\n⛔ x.md へ毎回追記しない。\n")), "C1"),
            ("C2 正典が 2 つ", lambda: _app(base, "CLAUDE.md", "<!-- obl:alpha-write canon --> 書く。\n"), "C2"),
            ("C2 参照にポインタ無し", lambda: _app(base, "CLAUDE.md", "<!-- obl:alpha-write --> 書く。\n"), "C2"),
            ("C3 description が長い", lambda: _rep(base, ".claude/agents/edo-alpha.md", "description: 役アルファ。read-only。",
                "description: 役アルファ。read-only。" + "あ" * 700), "C3"),
            ("S1 役が長い", lambda: _app(base, ".claude/agents/edo-alpha.md", "x\n" * 210), "S1"),
            ("V1 model が未知", lambda: _rep(base, ".claude/agents/edo-alpha.md", "model: opus", "model: gpt"), "V1"),
            ("V1 read-only なのに Write", lambda: _rep(base, ".claude/agents/edo-alpha.md", "tools: Read, Grep, Bash, Skill",
                "tools: Read, Write, Skill"), "V1"),
            ("V2 rules の paths が空振り", lambda: _rep(base, ".claude/rules/r.md", "docs/**", "Nowhere/**"), "V2"),
            ("V2 meta.name 不一致", lambda: _rep(base, ".claude/workflows/wf.js", "name: 'wf'", "name: 'other'"), "V2"),
            ("V3 スキルの description が空", lambda: _rep(base, "skills/sk/SKILL.md", "description: skill sk", "description:"), "V3"),
            ("G1 関門に selftest 無し", lambda: _rep(base, "Tools/Sashizu/x_gate.py", "--selftest", "--x"), "G1"),
            ("R8 典拠が索引に無い", lambda: _app(base, "skills/sk/references/sources.md",
                "\n### [乙] 確度B\n本文。\n"), "R8"),
            ("K1 ゴミ", lambda: _w(base, ".claude/hooks/old.sh.superseded", "x\n"), "K1"),
            ("W1 worktree にだけある役", lambda: _w(base, "wt/.claude/agents/edo-ghost.md", "---\nname: edo-ghost\n---\n"), "W1"),
            ("W2 worktree の内容が違う", lambda: _w(base, "wt/CLAUDE.md", read(os.path.join(base, "CLAUDE.md")) + "old\n"), "W2"),
            ("Y1 SYNC_PATHS の漏れ", lambda: _rep(base, "Tools/Session/edo_session.py", "\".claude/rules\", ", ""), "Y1"),
            ("Y1 拡張子の漏れ", lambda: _rep(base, "Tools/Session/edo_session.py", ", \".js\", \".json\"", ""), "Y1"),
            ("L1 タグ無しの教訓", lambda: _app(base, "docs/lessons.md", "- %s **教訓二 その先**(EDO-0002・cross)\n" % old), "L1"),
            ("L2 →規則 が無い規則", lambda: _app(base, "docs/lessons.md", "- %s **教訓三 その先**(EDO-0003・cross) →規則9\n" % old), "L2"),
            ("L2 →スキル に痕跡が無い", lambda: _app(base, "docs/lessons.md", "- %s **教訓四 その先**(EDO-0004・cross) →スキル:sk\n" % old), "L2"),
            ("U1 役が 30 日呼ばれていない", lambda: _transcripts(base, role_days=40), "U1"),
            ("U1 役が一度も呼ばれていない", lambda: _transcripts(base, role_days=None), "U1"),
            ("U1 スキルが 30 日呼ばれていない", lambda: _transcripts(base, skill_days=40), "U1"),
            ("U2 参照が読まれていない", lambda: _transcripts(base, refs=("a", "sources", "orphan")), "U2"),
            ("U2 CLAUDE.md の表の文書が読まれていない", lambda: _transcripts(base, doc=False), "U2"),
        ]
        for title, plant, want in CASES:
            shutil.rmtree(base)
            os.makedirs(base)
            _fixture(base)
            plant()
            ids, F = _run_fixture(base)
            if ids == [want]:
                print("⭕ %s → %s を鳴らした" % (title, want))
            elif want in ids:
                print("⚠ %s → %s は鳴ったが他も鳴った(%s)" % (title, want, ", ".join(i for i in ids if i != want)))
                ng += 1
            else:
                print("⛔ %s → **鳴らなかった**(期待 %s / 実際 %s)" % (title, want, ", ".join(ids) or "0件"))
                ng += 1
        # 記録が 30 日に満たなければ「呼ばれていない」と言わない(言えば誤検出になる)
        shutil.rmtree(base)
        os.makedirs(base)
        _fixture(base)
        _transcripts(base, role_days=None, refs=(), doc=False, cover=10)
        ids, F = _run_fixture(base)
        if "U1" in ids or "U2" in ids:
            print("⛔ 記録が 10 日ぶんなのに U を鳴らした(判定してはいけない)")
            ng += 1
        else:
            print("⭕ 記録が短い間は U を鳴らさない")
        # 表 → apply の往復(keep と lesson-tag)
        shutil.rmtree(base)
        os.makedirs(base)
        _fixture(base)
        _app(base, "docs/lessons.md", "- %s **教訓五 その先**(EDO-0005・cross)\n" % old)
        _w(base, ".claude/hooks/old.sh.superseded", "x\n")
        ids, F = _run_fixture(base)
        env = Env(parse(["--root", base, "--skills-dir", os.path.join(base, "skills"), "--memory-dir",
                         os.path.join(base, "memory"), "--global-settings", os.path.join(base, "gsettings.json"),
                         "--state-dir", os.path.join(base, "state"), "--worktrees", os.path.join(base, "wt")]))
        tbl = os.path.join(base, "t.md")
        with open(tbl, "w", encoding="utf-8") as fh:
            for f in F.items:
                if f["id"] == "L1":
                    fh.write("| %s | %s | %s | %s | `lesson-tag →不要` |\n" % (f["key"], f["sev"], f["where"], f["text"]))
                elif f["id"] == "K1":
                    fh.write("| %s | %s | %s | %s | `%s` |\n" % (f["key"], f["sev"], f["where"], f["text"], f["fix"]))
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_apply(env, tbl)
        ids2, _ = _run_fixture(base)
        if ids2 == []:
            print("⭕ 表 → apply(lesson-tag・rm)で所見が消える")
        else:
            print("⛔ 表 → apply の後も残る: %s" % ", ".join(ids2))
            ng += 1
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print()
    if ng:
        print("⛔ 自己検査 %d 件失敗 — **この道具の検出が死んでいる。**設定が 0 件でも合格の意味を持たない。" % ng)
    else:
        print("⭕ 自己検査 全通 — %d 型とも生きている。" % len(CASES))
    return 1 if ng else 0


def _w(base, rel, txt):
    fp = os.path.join(base, rel)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    io.open(fp, "w", encoding="utf-8").write(txt)


def _app(base, rel, txt):
    with io.open(os.path.join(base, rel), "a", encoding="utf-8") as f:
        f.write(txt)


def _rep(base, rel, old, new):
    fp = os.path.join(base, rel)
    txt = read(fp)                      # ⚠ 先に読む(open("w") を先に評価すると空になる)
    assert old in txt, "fixture に %r が無い" % old
    io.open(fp, "w", encoding="utf-8").write(txt.replace(old, new))


def _set(base, rel, obj):
    io.open(os.path.join(base, rel), "w", encoding="utf-8").write(json.dumps(obj))


# ── 入口 ─────────────────────────────────────────────────────────────────
def parse(argv):
    ap = argparse.ArgumentParser(description="道具改め")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--quick", action="store_true")
    g.add_argument("--table", action="store_true")
    g.add_argument("--apply", metavar="MD")
    g.add_argument("--deep", action="store_true")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--root")
    ap.add_argument("--skills-dir")
    ap.add_argument("--memory-dir")
    ap.add_argument("--global-settings")
    ap.add_argument("--state-dir")
    ap.add_argument("--worktrees", nargs="*", default=None)
    ap.add_argument("--transcripts-dir", nargs="*", default=None, help="transcript の置き場(既定は main と worktree の全部)")
    return ap.parse_args(argv)


def main(argv=None):
    a = parse(sys.argv[1:] if argv is None else argv)
    if a.selftest:
        return selftest()
    env = Env(a)
    if a.quick:
        return cmd_quick(env)
    if a.apply:
        return cmd_apply(env, a.apply)
    if a.deep:
        return cmd_deep(env)
    return cmd_table(env)


if __name__ == "__main__":
    sys.exit(main())
