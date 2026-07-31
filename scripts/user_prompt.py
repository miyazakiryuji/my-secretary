#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my-secretary / user_prompt.py（UserPromptSubmit フック本体）

ユーザーが何か話しかけるたびに呼ばれる。執務室で、かつ「いま伝える価値がある」
ことがあるときだけ、秘書への気づきメモを1〜2行そっと注入する。
これにより、セッションを開いたまま時間が経っても、秘書のほうから
「そろそろ14時の打ち合わせです」と声をかけられる（自発的な声かけ）。

設計上の約束:
- 執務室でなければ**何も出力しない**（他のプロジェクトを一切汚さない）
- **1セッションで同じ話題は1回だけ**（状態は一時ファイルに置き、執務室は汚さない）
- **先回り度（控えめ/ふつう/しっかり）に従う**
- ユーザーの用件が最優先。気づきは「添える」だけ
- 毎回呼ばれるので速く、どんなエラーでも黙って exit 0
"""
import datetime
import glob
import json
import os
import re
import sys
import tempfile

MARKER = "my-secretary:workspace"
APPT_RE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})")
DEADLINE_RE = re.compile(r"（締切:\s*(\d{4}-\d{2}-\d{2})）")
WAITING_RE = re.compile(r"（返事待ち:.*?/\s*(\d{4}-\d{2}-\d{2})から")

# 先回り度ごとに出してよい気づきの種類
LEVELS = {
    "控えめ": {"appt"},
    "ふつう": {"appt", "evening", "due_today"},
    "しっかり": {"appt", "evening", "due_today", "waiting", "after_appt"},
}


def read(path, limit=None):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read() if limit is None else f.read(limit)


def find_workspace(start):
    d = os.path.abspath(start)
    for _ in range(6):
        p = os.path.join(d, "CLAUDE.md")
        if os.path.isfile(p):
            try:
                head = read(p, 4000)
            except Exception:
                head = ""
            if MARKER in head:
                return d, head
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None, ""


def state_path(session_id):
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(session_id))[:64] or "nosession"
    return os.path.join(tempfile.gettempdir(), "my-secretary-nudge-%s.json" % safe)


def load_state(session_id):
    try:
        with open(state_path(session_id), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(session_id, state):
    try:
        with open(state_path(session_id), "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


def sweep_old_states(days=7):
    """古い状態ファイルを掃除する（溜め込まない）。"""
    try:
        limit = datetime.datetime.now().timestamp() - days * 86400
        for p in glob.glob(os.path.join(tempfile.gettempdir(),
                                        "my-secretary-nudge-*.json")):
            try:
                if os.path.getmtime(p) < limit:
                    os.remove(p)
            except Exception:
                pass
    except Exception:
        pass


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    cwd = data.get("cwd") or os.getcwd()
    ws, head = find_workspace(cwd)
    if not ws:
        return  # 執務室ではない → 完全に沈黙

    session_id = data.get("session_id", "")
    state = load_state(session_id)

    # 開いた直後は SessionStart が状況を伝えているので、最初の1回は黙る
    turns = state.get("turns", 0) + 1
    state["turns"] = turns
    if turns <= 1:
        save_state(session_id, state)
        sweep_old_states()  # 最初の1回だけ、古い状態ファイルを掃除
        return

    # 先回り度（CLAUDE.md から。無ければ「ふつう」）
    m = re.search(r"^- 先回り度:\s*(\S+?)(?:\s|—|$)", head, re.M)
    level = m.group(1).strip() if m else "ふつう"
    allowed = LEVELS.get(level, LEVELS["ふつう"])

    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    fired = set(state.get("fired", []))
    nudges = []

    # ── 1. 予定リマインド（開始45分前〜開始時刻）＋ 終わったころの記録の促し
    appt_path = os.path.join(ws, "予定.md")
    if os.path.isfile(appt_path) and ({"appt", "after_appt"} & allowed):
        in_past = False
        try:
            lines = read(appt_path).splitlines()
        except Exception:
            lines = []
        for line in lines:
            s = line.strip()
            if s.startswith("##"):
                in_past = "済" in s
                continue
            if in_past:
                continue
            m = APPT_RE.match(s)
            if not m or m.group(1) != today:
                continue
            try:
                start = now.replace(hour=int(m.group(2)), minute=int(m.group(3)),
                                    second=0, microsecond=0)
            except ValueError:
                continue
            title = re.sub(r"^-\s*\S+\s+\S+\s*", "", s).strip() or "予定"
            mins = int((start - now).total_seconds() // 60)
            key_before = "appt:%s:%s" % (m.group(2), m.group(3))
            if "appt" in allowed and 0 <= mins <= 45 and key_before not in fired:
                nudges.append("まもなく %s:%s から「%s」です（あと約%d分）。"
                              % (m.group(2), m.group(3), title, mins))
                fired.add(key_before)
            key_after = "after:" + key_before
            if ("after_appt" in allowed and -150 <= mins <= -75
                    and key_after not in fired):
                nudges.append("「%s」は終わったころでしょうか。決まったこと・宿題があれば"
                              "記録に残せます。" % title)
                fired.add(key_after)

    # ── 2. 夕方なのに日報がまだ
    if "evening" in allowed and "evening" not in fired and now.hour >= 17:
        if not os.path.isfile(os.path.join(ws, "日報", today + ".md")):
            if os.path.isfile(os.path.join(ws, "タスク", today + ".md")):
                nudges.append("今日の日報がまだです。区切りがついたら夕会にしましょう。")
                fired.add("evening")

    # ── 3. 今日が締切のタスクが、午後になっても未完
    if "due_today" in allowed and "due_today" not in fired and now.hour >= 15:
        for p in glob.glob(os.path.join(ws, "タスク", "*.md")):
            hit = False
            try:
                for line in read(p).splitlines():
                    s = line.strip()
                    m = DEADLINE_RE.search(s)
                    if m and s.startswith("- [ ]") and m.group(1) == today:
                        hit = True
                        break
            except Exception:
                pass
            if hit:
                nudges.append("今日が締切のタスクが残っています。進み具合はいかがですか。")
                fired.add("due_today")
                break

    # ── 4. 返事待ちが3日以上（しっかりのみ）
    if "waiting" in allowed and "waiting" not in fired:
        old = 0
        for p in glob.glob(os.path.join(ws, "タスク", "*.md")):
            try:
                for line in read(p).splitlines():
                    s = line.strip()
                    m = WAITING_RE.search(s)
                    if m and s.startswith("- [ ]"):
                        try:
                            d = datetime.date(*map(int, m.group(1).split("-")))
                            if (now.date() - d).days >= 3:
                                old += 1
                        except Exception:
                            pass
            except Exception:
                pass
        if old:
            nudges.append("返事待ちが%d件、3日以上たっています。確認しておきますか。" % old)
            fired.add("waiting")

    state["fired"] = sorted(fired)
    save_state(session_id, state)

    if not nudges:
        return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                "【秘書の気づき】いま伝える価値がありそうなことです（自動検出）:\n"
                + "\n".join("- " + n for n in nudges[:2])
                + "\n\nご本人の用件が最優先。まず用件に応じたうえで、"
                  "この気づきを秘書の口調で**1行だけ**そっと添えること"
                  "（用件と無関係なら無理に混ぜず、応答の最後に短く）。"
                  "断られたら二度と持ち出さない（同じ話題はこのセッションで再通知されません）。"
            ),
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # 何があっても入力を邪魔しない
    sys.exit(0)
