#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my-secretary / doctor.py

秘書の執務室（作業フォルダ）とローカル環境の状態をチェックする。
読み取りのみで、何も変更しない。

使い方:
    python3 doctor.py            # カレントディレクトリをチェック
    python3 doctor.py <対象パス>  # 指定ディレクトリをチェック

標準ライブラリのみで動作する。
"""
import datetime
import os
import sys

MARKER = "my-secretary:workspace"
STANDARD_DIRS = ["受信箱", "タスク", "アイデア", "ノート", "日報", "週次レビュー"]

ok_count = 0
warn_count = 0


def ok(msg):
    global ok_count
    ok_count += 1
    print("✅ " + msg)


def warn(msg, hint=""):
    global warn_count
    warn_count += 1
    print("⚠️  " + msg)
    if hint:
        print("    → " + hint)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    target = os.path.abspath(os.path.expanduser(target))

    print("=== my-secretary 環境チェック ===")
    print("対象フォルダ: " + target)
    print("")

    # 1. Python（ここまで動いていれば使える）
    ok("Python %d.%d — 使えます" % (sys.version_info[0], sys.version_info[1]))

    # 2. フォルダ自体
    if not os.path.isdir(target):
        warn("対象フォルダが見つかりません", "パスを確認してください")
        summary()
        return
    if os.access(target, os.W_OK):
        ok("フォルダへの書き込み — OK")
    else:
        warn("フォルダに書き込みできません", "別のフォルダで /my-secretary:setup を実行してください")

    # 3. 秘書の人格ファイル（CLAUDE.md + マーカー）
    is_ws = False
    claude_md = os.path.join(target, "CLAUDE.md")
    if not os.path.exists(claude_md):
        warn("CLAUDE.md（秘書の人格ファイル）がありません",
             "まだの場合は /my-secretary:setup で秘書との面談から始めてください")
    else:
        try:
            with open(claude_md, encoding="utf-8", errors="replace") as f:
                head = f.read(2000)
        except Exception:
            head = ""
        if MARKER in head:
            ok("CLAUDE.md — 秘書の人格ファイルを確認")
            is_ws = True
        else:
            warn("CLAUDE.md はありますが my-secretary のものではないようです",
             "別プロジェクトのフォルダかもしれません。秘書専用のフォルダで setup するのがおすすめです")

    # 4. プロフィール.md / 秘書の記憶.md
    profile = os.path.join(target, "プロフィール.md")
    if os.path.exists(profile):
        ok("プロフィール.md — あり")
    else:
        warn("プロフィール.md がありません", "/my-secretary:setup の面談で作成されます")
    if is_ws:
        if os.path.exists(os.path.join(target, "秘書の記憶.md")):
            ok("秘書の記憶.md（学んだこと）— あり")
        else:
            warn("秘書の記憶.md がありません",
                 "秘書に何か「覚えておいて」と話すと作られます（使うほど育つファイルです）")

    # 5. 標準フォルダ
    missing = [d for d in STANDARD_DIRS if not os.path.isdir(os.path.join(target, d))]
    if not missing:
        ok("標準フォルダ（%s）— すべてあり" % "・".join(STANDARD_DIRS))
    else:
        warn("標準フォルダが不足: " + "・".join(missing),
             "/my-secretary:setup を再実行すると足りない分だけ作られます（既存は触りません）")

    # 6. 執務室限定スキル（セットアップ済みの場合のみ）
    if is_ws:
        expected = ["deadline-watch", "recall", "handover", "learning",
                    "appointments", "people", "drafting"]
        missing_sk = [s for s in expected
                      if not os.path.isfile(os.path.join(target, ".claude", "skills", s, "SKILL.md"))]
        if not missing_sk:
            ok("執務室スキル7点（予定・締切・思い出し・申し送り・学習・人物・代筆）— すべてあり")
        else:
            warn("執務室スキルが不足: " + "・".join(missing_sk),
                 "/my-secretary:update を実行すると足りない分だけ補充されます"
                 "（記録・人格はそのまま）")

    # 7. 今日のようす（情報表示のみ）
    today = datetime.date.today().strftime("%Y-%m-%d")
    task_file = os.path.join(target, "タスク", today + ".md")
    report_file = os.path.join(target, "日報", today + ".md")
    if os.path.exists(task_file):
        ok("今日のタスクファイル（タスク/%s.md）— あり" % today)
    else:
        print("ℹ️  今日のタスクファイルはまだありません（/my-secretary:morning で作られます）")
    if os.path.exists(report_file):
        ok("今日の日報（日報/%s.md）— あり" % today)

    summary()


def summary():
    print("")
    print("=== 結果: ✅ %d件 / ⚠️ %d件 ===" % (ok_count, warn_count))


if __name__ == "__main__":
    main()
