#!/usr/bin/env bash
# TurboWarp の実行エンジン一式(scaffolding)を npm から取得し vendor/ へコピーする。
set -euo pipefail
cd "$(dirname "$0")/.."
npm install --no-save @turbowarp/scaffolding
rm -rf vendor/scaffolding
mkdir -p vendor/scaffolding
cp -r node_modules/@turbowarp/scaffolding/dist/* vendor/scaffolding/
echo "--- vendor/scaffolding ---"
ls -la vendor/scaffolding
if [ ! -f vendor/scaffolding/scaffolding-full.js ]; then
  echo "WARNING: scaffolding-full.js が見つかりません。上の一覧を確認し README の『トラブルシュート』を参照してください。" >&2
fi
