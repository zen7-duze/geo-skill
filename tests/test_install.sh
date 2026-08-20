#!/usr/bin/env bash
# install.sh 的行为测试 —— 不联网(用本地仓库当源),不碰真实 HOME。
#
# 测的是三件出过事或会出事的:装到哪、选装、以及**别把源码仓库当安装目标**。
#
#   bash tests/test_install.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL="$ROOT/vigilath-geo/install.sh"
PASS=0; FAIL=0
ok()   { printf '  \033[32m✔\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }

command -v bash >/dev/null || { echo "需要 bash"; exit 1; }
bash -n "$INSTALL" && ok "install.sh 语法正确" || bad "install.sh 语法错误"

run_install() {  # run_install <fake_home> <额外参数...>
  local home="$1"; shift
  HOME="$home" bash "$INSTALL" --token dummy-token --base https://example.invalid "$@" 2>&1
}

# ① 装进探测到的目录:建好 .openclaw/skills 就该装那儿
H=$(mktemp -d); mkdir -p "$H/.openclaw/skills"
out=$(cd "$H" && run_install "$H")
if [ -f "$H/.openclaw/skills/vigilath-site-audit/SKILL.md" ] &&
   [ -f "$H/.openclaw/skills/vigilath-site-audit/scripts/geo_client.py" ]; then
  ok "装进 ~/.openclaw/skills,且每个技能自带客户端副本"
else
  bad "没装进 ~/.openclaw/skills"; echo "$out" | tail -3
fi

# ② 默认装八个窄技能,且**不含**兜底全能包(同装会让宿主选不准)
n=$(ls "$H/.openclaw/skills" | grep -c '^vigilath-')
if [ "$n" -ge 8 ] && [ ! -d "$H/.openclaw/skills/vigilath-geo" ]; then
  ok "默认装 $n 个窄技能,不含全能包"
else
  bad "默认安装集不对:$n 个,vigilath-geo 存在=$([ -d "$H/.openclaw/skills/vigilath-geo" ] && echo yes || echo no)"
fi

# ③ --skills 选装
H2=$(mktemp -d); mkdir -p "$H2/.claude/skills"
run_install "$H2" --skills site-audit,seo-audit >/dev/null
got=$(ls "$H2/.claude/skills" | tr '\n' ' ')
if [ "$(ls "$H2/.claude/skills" | wc -l)" = "2" ] && [ -d "$H2/.claude/skills/vigilath-site-audit" ]; then
  ok "--skills 只装指定的两个($got)"
else
  bad "--skills 选装不对:$got"
fi

# ④ 技能名写错时跳过、不中断整次安装
H3=$(mktemp -d); mkdir -p "$H3/.claude/skills"
out=$(run_install "$H3" --skills site-audit,nosuchskill)
if echo "$out" | grep -q "跳过" && [ -d "$H3/.claude/skills/vigilath-site-audit" ]; then
  ok "错误技能名被跳过,其余照装"
else
  bad "错误技能名处理不对"
fi

# ⑤ **在 skill 源码仓库根跑,不能把安装产物写回源码目录**(2026-08-19 真踩过)
H4=$(mktemp -d); mkdir -p "$H4/.openclaw/skills"
before=$(find "$ROOT" -path '*/scripts/geo_client.py' | wc -l)
(cd "$ROOT/.." && HOME="$H4" bash "$INSTALL" --token t --base https://example.invalid >/dev/null 2>&1)
after=$(find "$ROOT" -path '*/scripts/geo_client.py' | wc -l)
if [ "$before" = "$after" ]; then
  ok "在源码仓库里跑不会污染源码目录(客户端副本仍只有 $after 份)"
else
  bad "污染了源码仓库:客户端副本从 $before 变成 $after"
fi

# ⑥ 凭证写入权限必须是 600
if [ "$(stat -c '%a' "$H/.vigilath/config" 2>/dev/null)" = "600" ]; then
  ok "~/.vigilath/config 权限 600"
else
  bad "凭证文件权限不是 600"
fi

echo
printf '通过 %d,失败 %d\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
