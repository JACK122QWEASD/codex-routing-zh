# weak-channel.md — W 档弱模型调用通道（派发时才读）

> 从 `agent.md` 分离出来，避免每轮会话都背着这段代码。
> 已用真实火山方舟 API 实测通过。

```bash
# ── 配置：从 .route-state.json 读取，不要硬编码厂商 ──────────────
# 这样换任何一家（火山 / DeepSeek / 智谱 / 百炼）都不用改脚本
ROOT="${ROOT:-$PWD}"                             # 默认当前目录，也可显式指定
STATE="$ROOT/.route-state.json"

WEAK_BASE_URL=$(grep -m1 '"cheap_endpoint"' "$STATE" | sed 's/.*: *"//; s/".*//')
WEAK_MODEL=$(grep -m1 '"cheap_model"'       "$STATE" | sed 's/.*: *"//; s/".*//')
WEAK_PROVIDER=$(grep -m1 '"cheap_provider"' "$STATE" | sed 's/.*: *"//; s/".*//')
export WEAK_BASE_URL WEAK_MODEL

# 关思考：推理模型必须关（实测省 88%），非推理模型置空即可
export WEAK_NO_THINK=1

# 密钥：优先环境变量；桌面端从 Dock 启动读不到 shell 变量时，
# 回退到 ~/.codex/config.toml 里对应 provider 的 bearer_token。
# ⚠️ 用纯 shell 提取，不用 python tomllib——很多系统的 python3 是 3.9，没有 tomllib（实测踩过）
if [ -z "$WEAK_API_KEY" ]; then
  WEAK_API_KEY=$(grep -A5 "model_providers.$WEAK_PROVIDER" "$HOME/.codex/config.toml" \
    | grep 'experimental_bearer_token' | sed 's/.*= *"//; s/"$//')
fi

run_weak() {
  local prompt="$1"
  local payload
  # prompt 必须走环境变量传给 python，直接拼进 -d 会被引号/换行搞坏
  payload=$(PROMPT="$prompt" WEAK_MODEL="$WEAK_MODEL" WEAK_NO_THINK="$WEAK_NO_THINK" python3 -c "
import json, os
p = {'model': os.environ['WEAK_MODEL'], 'temperature': 0,
     'messages': [{'role': 'user', 'content': os.environ['PROMPT']}]}
if os.environ.get('WEAK_NO_THINK'):
    p['thinking'] = {'type': 'disabled'}       # 关掉思考，省掉推理 token
print(json.dumps(p))
") || return 1
  curl -sS --max-time 60 "$WEAK_BASE_URL/chat/completions" \
    -H "Authorization: Bearer $WEAK_API_KEY" \
    -H "Content-Type: application/json" -d "$payload" \
  | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin)['choices'][0]['message']['content'])
except Exception as e:
    sys.exit('WEAK_CALL_FAILED: ' + str(e))    # 失败必须显式报错，不许静默返回空
"
}
```

## 🚀 批量派发脚本（性能关键，优先用这个）

> 一次脚本跑完**所有** W 档子任务，强档只做"写脚本 + 看校验结果"两次决策。
> 逐个派发 = N 轮强档推理（实测 v4-pro 一轮 6s），批量派发 = 2 轮。

> ⚠️ **本脚本是自包含的**（密钥回退 + run_weak 全部写在里面），复制即可运行。
> 之前版本写"run_weak 此处省略"，结果模型真的漏带了，脚本跑不起来——别再省略。

```bash
#!/bin/bash
# 批量派发：把所有 W 档子任务一次性并行跑完
set -u
# 不 cd：脚本位置不固定，统一以运行目录（或 $ROOT）为准

# —— 1. 配置（自包含，不要省略）——
# 同样从 .route-state.json 读，别硬编码厂商
STATE="${STATE:-${ROOT:-$PWD}/.route-state.json}"
WEAK_BASE_URL=$(grep -m1 '"cheap_endpoint"' "$STATE" | sed 's/.*: *"//; s/".*//')
WEAK_MODEL=$(grep -m1 '"cheap_model"'       "$STATE" | sed 's/.*: *"//; s/".*//')
WEAK_PROVIDER=$(grep -m1 '"cheap_provider"' "$STATE" | sed 's/.*: *"//; s/".*//')
export WEAK_BASE_URL WEAK_MODEL
export WEAK_NO_THINK=1                      # 关思考，省 88% token
if [ -z "${WEAK_API_KEY:-}" ]; then         # 桌面端读不到 shell 变量时回退
  WEAK_API_KEY=$(grep -A5 "model_providers.$WEAK_PROVIDER" "$HOME/.codex/config.toml" \
    | grep 'experimental_bearer_token' | sed 's/.*= *"//; s/"$//')
fi

run_weak() {
  local prompt="$1" payload
  payload=$(PROMPT="$prompt" WEAK_MODEL="$WEAK_MODEL" WEAK_NO_THINK="$WEAK_NO_THINK" python3 -c "
import json, os
p = {'model': os.environ['WEAK_MODEL'], 'temperature': 0,
     'messages': [{'role': 'user', 'content': os.environ['PROMPT']}]}
if os.environ.get('WEAK_NO_THINK'):
    p['thinking'] = {'type': 'disabled'}
print(json.dumps(p))
") || return 1
  curl -sS --max-time 60 "$WEAK_BASE_URL/chat/completions" \
    -H "Authorization: Bearer $WEAK_API_KEY" \
    -H "Content-Type: application/json" -d "$payload" \
  | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin)['choices'][0]['message']['content'])
except Exception as e:
    sys.exit('WEAK_CALL_FAILED: ' + str(e))
"
}

# —— 2. canary 预热探测：先确认通道通，别浪费整批 ——
run_weak "回复两个字：OK" > /dev/null 2>&1 || {
  echo "CANARY_FAIL：弱档通道不通 → 本批直接升档给强档"
  exit 1
}

mkdir -p .scratch

# —— 2. 所有子任务的 prompt，输入必须贴全 ——
P1="把 get_user_id 改成驼峰命名，只输出改后的标识符，不要解释"
P2="把 parse_json_data 改成驼峰命名，只输出改后的标识符，不要解释"
P3="把 read_file_path 改成驼峰命名，只输出改后的标识符，不要解释"

# —— 3. 一次性全部派发，并行跑 ——
i=0
for p in "$P1" "$P2" "$P3"; do
  i=$((i+1))
  run_weak "$p" > ".scratch/task-$i.out" 2> ".scratch/task-$i.err" &
done
wait                                   # 等全部结束

# —— 4. 脚本化校验（不让模型用眼睛看内容，省一轮推理且更可靠）——
fail=0
for f in .scratch/task-*.out; do
  [ -s "$f" ] || { echo "FAIL 空输出: $f"; fail=1; }          # 非空
  grep -qE '^[A-Za-z]' "$f" || { echo "FAIL 格式: $f"; fail=1; }  # 内容形状（按产物换正则）
done
echo "批量派发完成，失败标记=$fail"
exit $fail
```

**校验命令速查**（按产物类型选，全部是确定性命令）：

| 产物 | 校验命令 | 通过条件 |
|---|---|---|
| 任意输出 | `[ -s .scratch/task-N.out ]` | 文件非空 |
| JS 代码 | `node --check file.js` | 退出码 0 |
| Python | `python3 -m py_compile f.py` | 退出码 0 |
| JSON | `python3 -c "import json;json.load(open('f.json'))"` | 退出码 0 |
| 单测 | `node --test` / `pytest -q` | 0 失败 |
| 改名是否彻底 | `grep -c '旧名' *.js` | 全为 0 |
| 注释覆盖 | `grep -c '/\*\*' f.js` | 等于函数数 |
| 任务超时/报错 | `[ -s .scratch/task-N.err ]` | .err 为空 |

**要点**：
- 子任务之间**无依赖**才可批量；有依赖的留到下一批。
- 并行度上限 5，超了分批。
- 单个失败**只重跑那一个**（改脚本里的对应 prompt 再跑），别整批重来。
- 校验失败 → 按 agent.md §6 走兜底（重试 → 串行 → 升档），别让强档逐个肉眼看。

## 实测数据（3 个 L1 改名任务）

| 配置 | 串行 | 并行 | 加速 | token | 推理占比 |
|---|---|---|---|---|---|
| 强档 v4-pro | 7.09s | 2.95s | 2.40× | 550 | 42% |
| 弱档 GLM 关思考 | 8.27s | 2.65s | 3.13× | **85** | 0% |
| 弱档 GLM 开思考 | 17.05s | 7.86s | 2.17× | 796 | 87% |

弱档省 85% token；单次延迟略高但并行后反超 → L1 批量任务必须并行。
