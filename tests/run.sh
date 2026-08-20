#!/usr/bin/env bash
# 一键跑全部测试。零依赖:只要 python3 和 bash。
#   bash tests/run.sh
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
FAIL=0
for t in tests/test_geo_client.py tests/test_skills_meta.py; do
  echo "── $t"
  python3 "$t" 2>&1 | tail -3 || FAIL=1
  python3 "$t" >/dev/null 2>&1 || FAIL=1
done
echo "── tests/test_install.sh"
bash tests/test_install.sh | tail -3 || FAIL=1
echo
[ "$FAIL" -eq 0 ] && echo "✅ 全部通过" || echo "❌ 有失败"
exit "$FAIL"
