#!/usr/bin/env python3
"""merge.py — 把 .scratch 里的弱模型输出按 manifest 合并到目标文件。

强档只负责写 manifest 和看退出码，合并过程完全脚本化（agent.md §5.4）。

用法:
    python3 tools/merge.py manifest.json [--dry-run]

manifest.json 格式（数组，每项一条）:
    {
      "src":    ".scratch/task-1.out",   # 弱模型输出
      "dst":    "string.js",             # 目标文件
      "mode":   "replace" | "append" | "insert_after",
      "anchor": "// MARKER"              # 仅 insert_after 需要
    }

退出码:
    0 = 全部成功   1 = 有失败项（会打印具体原因，便于只重跑那一条）
"""

import json
import os
import sys


def apply(item: dict, dry_run: bool = False) -> tuple:
    """执行一条合并规则，返回 (是否成功, 说明)。"""
    src = item.get("src")
    dst = item.get("dst")
    mode = item.get("mode", "replace")

    if not src or not dst:
        return False, "缺 src 或 dst 字段"
    if not os.path.isfile(src):
        return False, f"源文件不存在: {src}"
    if os.path.getsize(src) == 0:
        return False, f"源文件为空（弱模型静默失败？）: {src}"

    with open(src, encoding="utf-8") as f:
        content = f.read().rstrip("\n")

    if mode == "replace":
        if not os.path.isfile(dst):
            # 目标不存在时按新建处理，但仍提示，避免误建文件
            note = "目标文件不存在，将新建"
        else:
            note = "整体替换"
        if dry_run:
            return True, f"[dry-run] {dst}: {note}（{len(content)} 字符）"
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content + "\n")
        return True, f"{dst}: {note}"

    if mode == "append":
        if not os.path.isfile(dst):
            return False, f"append 模式要求目标文件已存在: {dst}"
        if dry_run:
            return True, f"[dry-run] {dst}: 追加 {len(content)} 字符"
        with open(dst, "a", encoding="utf-8") as f:
            f.write("\n" + content + "\n")
        return True, f"{dst}: 追加"

    if mode == "insert_after":
        anchor = item.get("anchor")
        if not anchor:
            return False, "insert_after 需要 anchor 字段"
        if not os.path.isfile(dst):
            return False, f"目标文件不存在: {dst}"
        with open(dst, encoding="utf-8") as f:
            lines = f.read().split("\n")
        try:
            idx = next(i for i, l in enumerate(lines) if anchor in l)
        except StopIteration:
            return False, f"在 {dst} 里找不到锚点: {anchor!r}"
        if dry_run:
            return True, f"[dry-run] {dst}: 插入到第 {idx + 1} 行后"
        lines.insert(idx + 1, content)
        with open(dst, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True, f"{dst}: 插入到锚点后"

    return False, f"未知 mode: {mode}"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    if not args:
        print(__doc__)
        return 1

    try:
        with open(args[0], encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"manifest 读取失败: {e}")
        return 1

    ok, fail = 0, []
    for i, item in enumerate(manifest, 1):
        good, msg = apply(item, dry_run)
        if good:
            ok += 1
            print(f"  ✅ #{i} {msg}")
        else:
            fail.append((i, msg))
            print(f"  ❌ #{i} {msg}")

    print(f"\n合并结果: 成功 {ok} / 共 {len(manifest)}")
    if fail:
        print("失败项（只重跑这些，不要整批重来）:")
        for i, msg in fail:
            print(f"  #{i}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
