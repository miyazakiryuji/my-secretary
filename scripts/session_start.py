#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my-secretary / session_start.py（SessionStart フック本体）

Claude Code のセッション開始時に呼ばれる。カレントフォルダ（またはその親）が
my-secretary の執務室なら、秘書モードで出迎えるための状態スナップショットを
additionalContext としてコンテキストに注入する。これにより、ユーザーの最初の
ひとことが何であっても、秘書として出迎えられる。

設計上の約束:
- 執務室でなければ**何も出力しない**（他のプロジェクトを一切汚さない）
- どんなエラーが起きても黙って exit 0（セッション開始を邪魔しない）
- 標準ライブラリのみ・読み取りのみ
"""
import datetime
import glob
import json
import os
import re
import sys

MARKER = "my-secretary:workspace"
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
DEADLINE_RE = re.compile(r"（締切:\s*(\d{4}-\d{2}-\d{2})）")


def scan_deadlines(ws, today):
    """全タスクファイルから締切つき未完タスクを集計 → (期限切れ件数, 今日締切件数)。
    同じ内容がどこかで完了([x])していれば完了扱い。"""
    undone, done = {}, set()
    for p in glob.glob(os.path.join(ws, "タスク", "*.md")):
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    m = DEADLINE_RE.search(s)
                    if not m or not s.startswith("- ["):
                        continue
                    key = re.sub(r"\s*（締切:.*", "", s[5:]).strip()
                    if s.startswith("- [x]"):
                        done.add(key)
                    elif s.startswith("- [ ]"):
                        undone[key] = m.group(1)
        except Exception:
            pass
    overdue = sum(1 for k, d in undone.items() if k not in done and d < today)
    due_today = sum(1 for k, d in undone.items() if k not in done and d == today)
    return overdue, due_today


def find_workspace(start):
    """start から親方向に最大6階層、マーカー付き CLAUDE.md を探す。"""
    d = os.path.abspath(start)
    for _ in range(6):
        p = os.path.join(d, "CLAUDE.md")
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    head = f.read(4000)
            except Exception:
                head = ""
            if MARKER in head:
                return d, head
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None, ""


DATA_DIRS = ["受信箱", "タスク", "アイデア", "ノート", "日報", "週次レビュー"]


def count_records(ws):
    """データフォルダの .md ファイル総数（蓄積の見える化用）。"""
    n = 0
    for d in DATA_DIRS:
        n += len(glob.glob(os.path.join(ws, d, "*.md")))
    return n


def days_together(ws, today):
    """日付ファイル名の最古から数えた「一緒に働いて◯日目」。記録がなければ1日目。"""
    dates = []
    for d in ["タスク", "日報", "受信箱"]:
        for p in glob.glob(os.path.join(ws, d, "*.md")):
            b = os.path.basename(p)[:10]
            if re.match(r"^\d{4}-\d{2}-\d{2}$", b):
                dates.append(b)
    if not dates:
        return 1
    try:
        d0 = datetime.date(*map(int, min(dates).split("-")))
        d1 = datetime.date(*map(int, today.split("-")))
        return max((d1 - d0).days + 1, 1)
    except Exception:
        return 1


def read_memory(ws):
    """秘書の記憶.md → (学びの件数, 冒頭の抜粋)。なければ (0, "")。"""
    p = os.path.join(ws, "秘書の記憶.md")
    if not os.path.isfile(p):
        return 0, ""
    try:
        with open(p, encoding="utf-8") as f:
            text = f.read(4000)
    except Exception:
        return 0, ""
    n = sum(1 for l in text.splitlines() if l.strip().startswith("- "))
    return n, text[:600].strip()


def count_inbox(ws):
    """受信箱の未整理項目数（`- [済` で始まらない箇条書き）。"""
    n = 0
    for p in glob.glob(os.path.join(ws, "受信箱", "*.md")):
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s.startswith("- ") and not s.startswith("- [済"):
                        n += 1
        except Exception:
            pass
    return n


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    # 新規セッションと /clear のときだけ動く（resume 等では沈黙）
    if data.get("source", "startup") not in ("startup", "clear"):
        return

    cwd = data.get("cwd") or os.getcwd()
    ws, head = find_workspace(cwd)
    if not ws:
        return  # 執務室ではない → 何も出力しない

    # 秘書名・呼び名・仕える相手を CLAUDE.md からゆるく拾う（失敗しても続行）
    m = re.search(r"^- 名前:\s*(.+)$", head, re.M)
    sec_name = m.group(1).strip() if m else "秘書"
    m = re.search(r"^- 呼び名:\s*([^（\n]+)", head, re.M)
    sec_call = m.group(1).strip() if m else ""
    if sec_call and sec_call != sec_name:
        sec_name = "%s（呼び名: %s）" % (sec_name, sec_call)
    m = re.search(r"^- 仕える相手:\s*([^（\n]+)", head, re.M)
    owner = m.group(1).strip() if m else ""

    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    weekday = WEEKDAYS[now.weekday()]

    task_path = os.path.join(ws, "タスク", today + ".md")
    if os.path.isfile(task_path):
        try:
            with open(task_path, encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception:
            lines = []
        undone = sum(1 for l in lines if l.strip().startswith("- [ ]"))
        done = sum(1 for l in lines if l.strip().startswith("- [x]"))
        task_state = "あり（未完 %d / 全 %d）" % (undone, undone + done)
    else:
        task_state = "まだない"

    report_state = "あり" if os.path.isfile(os.path.join(ws, "日報", today + ".md")) else "まだない"
    inbox = count_inbox(ws)
    overdue, due_today = scan_deadlines(ws, today)
    records = count_records(ws)
    days = days_together(ws, today)
    mem_count, mem_excerpt = read_memory(ws)

    handover = ""
    hp = os.path.join(ws, "申し送り.md")
    if os.path.isfile(hp):
        try:
            with open(hp, encoding="utf-8") as f:
                handover = f.read(600).strip()
        except Exception:
            handover = ""

    owner_part = ("仕える相手は %s。" % owner) if owner else ""
    handover_part = (
        "\n申し送り（前回からの引き継ぎ）:\n---\n%s\n---\n" % handover
    ) if handover else ""
    memory_part = (
        "\n秘書の記憶（抜粋。応対はこれに沿わせる）:\n---\n%s\n---\n" % mem_excerpt
    ) if mem_excerpt else ""
    milestone_part = (
        "今日で一緒に働いて %d日目の節目。出迎えでひとことだけお祝いしてよい。\n" % days
    ) if days in (10, 30, 50, 100, 200, 365) else ""
    context = (
        "【my-secretary】ここはあなたが秘書を務める執務室です（SessionStart フックが自動検出）。\n"
        "秘書名: %s。%s人格・口調・ふるまいは執務室の CLAUDE.md に従うこと。\n"
        "\n"
        "現在: %s（%s）%s ／ 一緒に働いて %d日目・記録の蓄積 %d件・秘書の記憶 %d件\n"
        "- 今日のタスクファイル（タスク/%s.md）: %s\n"
        "- 今日の日報: %s\n"
        "- 受信箱の未整理: %d件\n"
        "- 締切のあるタスク: 期限切れ %d件 ／ 今日が締切 %d件\n"
        "%s%s"
        "\n"
        "最初の応答では、内容が何であれ、まず秘書として 1〜2 行で出迎えること。\n"
        "%s"
        "期限切れ・今日締切があれば、出迎えのひとことで最優先に伝える。\n"
        "申し送りがあれば「前回は◯◯の途中でした」と軽く触れる。\n"
        "用件があればそれを最優先で処理する。挨拶や雑談だけなら、上の状態と時間帯から\n"
        "次の一手を1つだけ添える（例: 午前でタスクファイルがまだ → そのまま朝会を始めてよい ／\n"
        "17時以降で日報がまだ → 夕会を提案）。提案は1回に1つ。断られたら同じセッションでは繰り返さない。"
        % (sec_name, owner_part, today, weekday, now.strftime("%H:%M"),
           days, records, mem_count,
           today, task_state, report_state, inbox, overdue, due_today,
           memory_part, handover_part, milestone_part)
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # 何があってもセッション開始を邪魔しない
    sys.exit(0)
