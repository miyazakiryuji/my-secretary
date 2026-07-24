#!/usr/bin/env bash
# ------------------------------------------------------------------
# 配布用 zip（my-secretary.zip）を作る。
# この zip は「claude --plugin-dir <zip>」には zip のまま渡せる。
# 「/plugin marketplace add」で恒久導入する場合は、zip を解凍した
# フォルダのパスを指定する（marketplace add は zip 非対応）。
#
# 使い方: bash make_dist.sh [出力先.zip]
#   省略時は カレントディレクトリに my-secretary.zip を作成。
# ------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # .../my-secretary
NAME="$(basename "${ROOT}")"               # my-secretary
OUT="${1:-$PWD/${NAME}.zip}"
# 相対パス指定でも壊れないよう絶対パス化（後段で cd するため）
case "${OUT}" in /*) ;; *) OUT="${PWD}/${OUT}" ;; esac

if ! command -v zip >/dev/null 2>&1; then
  echo "エラー: zip コマンドが見つかりません。" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp -R "${ROOT}" "${TMP}/${NAME}"
# 不要物を除去（.git / キャッシュ / OS ゴミ / 既存 dist）
find "${TMP}/${NAME}" \
  \( -name '.git' -o -name '__pycache__' -o -name 'node_modules' -o -name 'dist' \) \
  -prune -exec rm -rf {} + 2>/dev/null || true
find "${TMP}/${NAME}" \( -name '*.pyc' -o -name '.DS_Store' -o -name '*.zip' \) -delete 2>/dev/null || true

rm -f "${OUT}"
( cd "${TMP}" && zip -r -X "${OUT}" "${NAME}" >/dev/null )
echo "created: ${OUT}"
echo "配布時は、この zip と『はじめに_参加者向け.md』を渡してください。"
