#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
CODEX="$HOME/.codex"

echo "安装 Codex 分层调度协议"
echo "项目目录: $ROOT"

mkdir -p "$CODEX"

# 1. 全局入口：把模板里的占位符替换成实际路径
sed "s|{{PROJECT_ROOT}}|$ROOT|g" "$ROOT/examples/AGENTS.global.md" > "$CODEX/AGENTS.md"
echo "  ✅ 全局入口 → ~/.codex/AGENTS.md"

# 2. 项目内 AGENTS.md（Codex 仓库级指令入口）
ln -sf agent.md "$ROOT/AGENTS.md"
echo "  ✅ 项目内 AGENTS.md → agent.md"

# 3. 状态配置
if [ ! -f "$ROOT/.route-state.json" ]; then
  cp "$ROOT/examples/route-state.example.json" "$ROOT/.route-state.json"
  echo "  ✅ 生成 .route-state.json"
else
  echo "  ⏭  .route-state.json 已存在，跳过"
fi

# 4. Codex 模型配置
if [ ! -f "$CODEX/config.toml" ]; then
  cp "$ROOT/examples/codex-config.toml" "$CODEX/config.toml"
  chmod 600 "$CODEX/config.toml"
  echo "  ⚠️  已生成 ~/.codex/config.toml —— 请编辑填入你的模型端点和密钥"
else
  echo "  ⏭  ~/.codex/config.toml 已存在，跳过"
fi

cat <<'MSG'

安装完成。下一步：

  1. 编辑 ~/.codex/config.toml，填入你的模型和密钥
  2. 重启 Codex（桌面端需 Cmd+Q 完全退出再打开）
  3. 新开对话，它会先问三个配置问题

文档见 README.md
MSG
