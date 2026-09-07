#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my-secretary / recurring.py

執務室の `繰り返し.md` を読み、指定した日に当たる予定・タスクを返す小さな部品。
session_start.py（出迎え）と user_prompt.py（声かけ）が共用する。標準ライブラリのみ・読み取りのみ。

行の書式（行頭の形はスキルと合わせてある）:
    - <頻度> <時刻|終日> <内容>
    頻度: 毎日 ／ 平日 ／ 毎週 <曜>（複数は 月・水）／ 毎月 <N>日 ／ 毎月 末日
    時刻: HH:MM または HH:MM-HH:MM。無ければ 終日
    行末が （休止） の行は飛ばす

節: 「## 予定」以下は kind="予定"、「## タスク」以下は kind="タスク"。
"""
import calendar
import datetime
import os
import re

WEEKDAYS = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}
LINE_RE = re.compile(
    r"^-\s*(?P<freq>毎日|平日|毎週\s*[月火水木金土日・]+|毎月\s*(?:\d{1,2}日|末日))"
    r"\s+(?:(?P<start>\d{1,2}:\d{2})(?:-(?P<end>\d{1,2}:\d{2}))?|終日)?\s*(?P<title>.+?)\s*$"
)


def _matches(freq, day):
    freq = freq.replace(" ", "").replace("　", "")
    if freq == "毎日":
        return True
    if freq == "平日":
        return day.weekday() < 5
    if freq.startswith("毎週"):
        wanted = [WEEKDAYS[c] for c in freq[2:] if c in WEEKDAYS]
        return day.weekday() in wanted
    if freq.startswith("毎月"):
        spec = freq[2:]
        last = calendar.monthrange(day.year, day.month)[1]
        if spec == "末日":
            return day.day == last
        try:
            n = int(spec.rstrip("日"))
        except ValueError:
            return False
        # 31日指定で30日までの月 → その月の末日に当てる
        return day.day == min(n, last)
    return False


def items_for(ws, day):
    """執務室 ws の 繰り返し.md から、day（datetime.date）に当たる項目を返す。
    戻り値: [{"kind": "予定"|"タスク", "start": "10:00"|None, "end": "10:30"|None, "title": str}, ...]
    ファイルが無い・壊れている場合は []。"""
    path = os.path.join(ws, "繰り返し.md")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception:
        return []
    kind = "予定"
    out = []
    for line in lines:
        s = line.strip()
        if s.startswith("##"):
            kind = "タスク" if "タスク" in s else "予定"
            continue
        if s.endswith("（休止）") or s.endswith("(休止)"):
            continue
        m = LINE_RE.match(s)
        if not m:
            continue
        if not _matches(m.group("freq"), day):
            continue
        out.append({
            "kind": kind,
            "start": m.group("start"),
            "end": m.group("end"),
            "title": m.group("title"),
        })
    # 時刻順（終日は先頭）
    out.sort(key=lambda x: (x["start"] or "00:00"))
    return out


if __name__ == "__main__":
    import sys
    ws = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    day = datetime.date.today()
    if len(sys.argv) > 2:
        day = datetime.date(*map(int, sys.argv[2].split("-")))
    for it in items_for(ws, day):
        print("%s\t%s\t%s" % (it["kind"], it["start"] or "終日", it["title"]))
