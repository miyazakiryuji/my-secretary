---
description: 環境チェック。執務室と環境の状態を点検する（読み取りのみ・何も変更しない）
argument-hint: "[チェックする秘書フォルダ（省略時は現在のフォルダ）]"
---

# 環境チェック（doctor）

あなたは `my-secretary` プラグインの点検担当です。以下を順番に、日本語で実行してください。
**何も変更しない**（読み取りとチェックのみ）。

## 1. スクリプトによるチェック

Bash ツールで次を実行し、出力をそのままユーザーに見せる:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" [$ARGUMENTS があればそのフォルダ]
```

- `python3` がなければ `python` で再試行する。
- どちらもない場合は「⚠️ Python が見つかりません」と伝えたうえで、同じ項目
  （CLAUDE.md のマーカー・プロフィール.md・標準6フォルダ・今日のファイル）を
  自分で Read / ls して確認し、✅／⚠️ 形式で報告する。

## 2. プラグイン本体のチェック

以下のファイルが存在するか確認する（Read で先頭数行を読めればOK）:

- `${CLAUDE_PLUGIN_ROOT}/skills/secretary-mode/SKILL.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/secretary-mode/references/templates.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/secretary-mode/references/claude-md-template.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/secretary-mode/references/persona-presets.md`
- `${CLAUDE_PLUGIN_ROOT}/hooks/hooks.json`（フォルダを開くだけで秘書モードになる仕掛け）
- `${CLAUDE_PLUGIN_ROOT}/scripts/session_start.py`

フック2ファイルに問題がなければ「✅ 自動出迎え（SessionStartフック）— OK」。
「執務室で開いたのに出迎えがない」という相談の場合は、プラグインのインストール・有効化後に
**Claude Code を再起動したか**を確認する（フックは再起動後に有効になる）。

読めれば「✅ プラグイン本体 — OK」。読めなければ「⚠️ プラグインの再インストールを
お試しください（/plugin から）」。

## 3. まとめ

最後に3行以内でまとめる:

1. 総合判定（例: 「準備OKです！」／「⚠️が1件ありますが、すぐ直せます」）
2. ⚠️ があれば、直し方を1行ずつ
3. 次の一歩（未セットアップなら `/my-secretary:setup`、セットアップ済みなら
   `/my-secretary:morning` か、そのまま「タスク追加 ◯◯」と話しかける）
