#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my-secretary / init_workspace.py

「自分専用の秘書」の執務室（作業フォルダ一式）を、実行ディレクトリ
（または引数で指定したディレクトリ）に作成する。既存のフォルダ・ファイルは
上書きしない（何度実行しても安全）。

使い方:
    python3 init_workspace.py                        # カレントディレクトリに作成
    python3 init_workspace.py <対象パス>              # 指定ディレクトリに作成
    python3 init_workspace.py --extra "議事録,日記"   # 標準フォルダに追加で作成
    python3 init_workspace.py <対象パス> --extra "議事録"
    python3 init_workspace.py --plugin-root <プラグインのパス>
        # プラグインの workspace-skills/ から、この執務室専用のスキル
        # （締切ウォッチ・思い出し・申し送り）を .claude/skills/ へ複製する

注意: 秘書の人格ファイル（CLAUDE.md）とプロフィール.md は面談内容で変わるため、
このスクリプトでは作らない（/my-secretary:setup の中で Claude が書く）。

標準ライブラリのみで動作する。
"""
import os
import shutil
import sys

# ------------------------------------------------------------------
# 標準で作成するフォルダ（この6つは常に作る）
# ------------------------------------------------------------------
STANDARD_DIRS = [
    "受信箱",        # 何でも書き捨てるメモ置き場（あとで秘書が整理）
    "タスク",        # 1日1ファイルのタスクリスト（YYYY-MM-DD.md）
    "アイデア",      # 1アイデア1ファイル
    "ノート",        # 調べたこと・ナレッジ
    "日報",          # 夕会で秘書が書く日報（YYYY-MM-DD.md）
    "週次レビュー",  # 週次のふりかえり（YYYY-Www.md）
]

# ------------------------------------------------------------------
# 生成するテンプレート類（既存なら書き換えない）
# ------------------------------------------------------------------
FILES = {}

FILES["はじめにお読みください.md"] = """# 自分専用の秘書（my-secretary）の執務室

このフォルダは `/my-secretary:setup` で作られた、あなたの秘書の執務室です。
次回からは **このフォルダで Claude Code を開くだけ** で、秘書が出迎えてくれます。

そしてこの秘書は、**使えば使うほど・記録が溜まるほど、あなた専用に育ちます**。
好みや言い方を伝える（「覚えておいて」「もっと短く」）と `秘書の記憶.md` が育ち、
メモや日報が溜まるほど「あれどこだっけ？」に強くなります。

## 1日のリズム

| いつ | やること |
|---|---|
| 朝 | 「**おはよう**」と言うだけで朝会 … 昨日の持ち越しを拾って、今日の段取りを一緒に決める（`/my-secretary:morning` でも同じ） |
| 日中 | 思いついたら話しかけるだけ（下の「話しかけ方」参照） |
| 夜 | 「**おつかれさま**」と言うだけで夕会 … 今日の成果を聞かれて、日報が自動でできる（`/my-secretary:evening` でも同じ） |
| 週末 | `/my-secretary:weekly` … 1週間分をまとめた週次レビューができる |

## 話しかけ方（コマンド不要。普通に話すだけ）

| 言い方の例 | 秘書がすること |
|---|---|
| 「おはよう」 | 挨拶と一緒に朝会が始まる |
| 「おつかれさま」 | 夕方以降なら夕会が始まって、日報ができる |
| 「タスク追加 ◯◯」 | 今日のタスクに追加 |
| 「◯◯終わったよ」 | タスクを完了にする |
| 「今日のタスクは？」 | 今日のタスクを表示 |
| 「メモ ◯◯」 | 受信箱に書き留める |
| 「アイデア ◯◯」 | アイデアを1ファイルにして保存 |
| 「8/15までに◯◯」 | 締切つきで記録。朝会や開いたときに教えてくれる |
| 「今週の締切は？」 | 締切の一覧（期限切れ・今日・近日） |
| 「明日14時に打ち合わせ」 | 予定として記録。当日の朝会・出迎えで最初に知らせる |
| 「今日の予定は？」「今週の予定」 | 予定を時系列で表示 |
| 「あれどこだっけ？」 | 書き溜めた記録から探して思い出す |
| 「今日はここまで」「前回どこまで？」 | 申し送りを書く／前回の続きから再開 |
| 「覚えておいて」「今後は◯◯して」 | 秘書の記憶に残して、以後の応対に反映 |
| 「私のこと何覚えてる？」 | 育った記憶を一覧で見せる |
| 「田中さんの件メモ」「どんな人だっけ」 | 人物ごとのメモに記録・要約 |
| 「明日の打ち合わせの準備して」 | 前回の話・宿題・論点を1枚にまとめる |
| 「お礼メール書いて」「断りの文案」 | 下書きを作る（送信はしません） |
| 「◯◯さんに送った、返事待ち」 | 相手のボールとして管理し、3日過ぎたら教えてくれる |
| 「受信箱整理して」 | 受信箱のメモを各フォルダへ仕分け（承認してから移動） |
| 「ダッシュボード」 | 全体のようすをまとめて表示 |

※どれも言い方は自由です。「おはよー」「今日終わり！」「これメモっといて」など、
意味が伝われば秘書がくみ取ります。

## フォルダの中身

| 場所 | 役割 |
|---|---|
| CLAUDE.md | 秘書の人格・ルール（このフォルダで開くと自動で読み込まれます） |
| プロフィール.md | あなたの基本情報と目標 |
| 秘書の記憶.md | 秘書があなたについて学んだこと（使うほど育ちます） |
| 申し送り.md | 「前回の続き」の引き継ぎメモ（秘書が管理します） |
| 予定.md | 日時のある約束（アポ）。必要になったとき秘書が作ります |
| 人物/・下書き/ | 人物メモと代筆した文章（必要になったとき秘書が作ります） |
| 受信箱/ | 何でも書き捨てるメモ置き場 |
| タスク/ | 1日1ファイルのタスクリスト |
| アイデア/ | 1アイデア1ファイル |
| ノート/ | 調べたこと・ナレッジ |
| 日報/ | 夕会で秘書が書く日報 |
| 週次レビュー/ | 週ごとのふりかえり |

（隠しフォルダ `.claude/skills/` には、この執務室**専用**の秘書スキル7点
〔予定・締切/返事待ち・思い出し・申し送り・学習・人物/打ち合わせ準備・代筆〕が
入っています。触らなくて大丈夫ですが、中身を開いて自分好みに育てるのも自由です）

## 秘書が新しくなったとき

プラグインが更新されたら、この執務室で `/my-secretary:update` を実行してください。
**あなたの記録・秘書の人格・キャラ設定はそのまま**に、新しい機能だけが足されます。

## 2つだけ注意

- 会社の機密情報や、他人の個人情報は、このフォルダに書かないでください。
- ファイルはぜんぶただの Markdown（テキスト）です。手で直しても大丈夫。
  むしろどんどん自分で開いて眺めてください（それが資産になります）。
"""

def parse_args(argv):
    """引数から (対象パス, 追加フォルダのリスト, プラグインルート) を取り出す。"""
    target = os.getcwd()
    extras = []
    plugin_root = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--extra":
            if i + 1 >= len(argv):
                print("エラー: --extra の後にフォルダ名（カンマ区切り）を指定してください。")
                sys.exit(1)
            extras += [x.strip() for x in argv[i + 1].split(",") if x.strip()]
            i += 2
        elif a.startswith("--extra="):
            extras += [x.strip() for x in a.split("=", 1)[1].split(",") if x.strip()]
            i += 1
        elif a == "--plugin-root":
            if i + 1 >= len(argv):
                print("エラー: --plugin-root の後にパスを指定してください。")
                sys.exit(1)
            plugin_root = argv[i + 1]
            i += 2
        elif a.startswith("--plugin-root="):
            plugin_root = a.split("=", 1)[1]
            i += 1
        else:
            target = a
            i += 1
    return target, extras, plugin_root


def main():
    target, extras, plugin_root = parse_args(sys.argv[1:])
    target = os.path.abspath(os.path.expanduser(target))
    os.makedirs(target, exist_ok=True)

    created, skipped = [], []

    # フォルダ作成（重複は除いて順序維持）
    dirs = list(dict.fromkeys(STANDARD_DIRS + extras))
    for d in dirs:
        path = os.path.join(target, d)
        if os.path.isdir(path):
            skipped.append(d + "/")
        else:
            os.makedirs(path, exist_ok=True)
            created.append(d + "/")

    # テンプレートファイル作成（既存は触らない）
    for name, body in FILES.items():
        path = os.path.join(target, name)
        if os.path.exists(path):
            skipped.append(name)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            created.append(name)

    # 執務室限定スキルの複製（プラグインの workspace-skills/ → .claude/skills/）
    if plugin_root:
        src_root = os.path.join(os.path.abspath(os.path.expanduser(plugin_root)), "workspace-skills")
        if os.path.isdir(src_root):
            for name in sorted(os.listdir(src_root)):
                src = os.path.join(src_root, name, "SKILL.md")
                if not os.path.isfile(src):
                    continue
                rel = os.path.join(".claude", "skills", name, "SKILL.md")
                dst = os.path.join(target, rel)
                if os.path.exists(dst):
                    skipped.append(rel)
                else:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)
                    created.append(rel)
        else:
            print("注意: workspace-skills が見つかりません: " + src_root)

    print("対象フォルダ: " + target)
    print("")
    if created:
        print("✅ 作成:")
        for c in created:
            print("   " + c)
    if skipped:
        print("⏭  スキップ（既にあるため触っていません）:")
        for s in skipped:
            print("   " + s)
    if not created:
        print("")
        print("すべて作成済みでした（何も変更していません）。")


if __name__ == "__main__":
    main()
