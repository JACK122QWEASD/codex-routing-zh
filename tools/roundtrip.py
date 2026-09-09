#!/usr/bin/env python3
"""roundtrip.py — 回译校验：把弱模型的输出反向转换，看能否回到原值。

专治"形状对、内容错"：格式校验（非空、能编译）挡不住改错内容，
回译校验能挡住——而且**零 token 成本**，纯脚本跑。

用法:
    python3 tools/roundtrip.py pairs.json

pairs.json:
    [
      {"orig": "get_user_id",  "out": "getUserId",  "kind": "snake_to_camel"},
      {"orig": "toCamelCase",  "out": "to_camel_case", "kind": "camel_to_snake"}
    ]

kind 支持:
    snake_to_camel   原值 snake，弱档输出 camel → 反向转回 snake 比对
    camel_to_snake   原值 camel，弱档输出 snake → 反向转回 camel 比对
    lower / upper    大小写转换（反向即反向大小写）

退出码: 0 = 全部通过   1 = 有不一致（会打印具体是哪些，便于只重跑那些）
"""

import json
import re
import sys


def to_snake(s: str) -> str:
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", s)
    return s.lower()


def to_camel(s: str) -> str:
    parts = s.replace("-", "_").split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


REVERSE = {
    "snake_to_camel": to_snake,   # 输出是 camel → 转回 snake
    "camel_to_snake": to_camel,   # 输出是 snake → 转回 camel
    "lower": str.upper,
    "upper": str.lower,
}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1

    try:
        with open(args[0], encoding="utf-8") as f:
            pairs = json.load(f)
    except Exception as e:
        print(f"pairs 读取失败: {e}")
        return 1

    ok, bad = 0, []
    for i, p in enumerate(pairs, 1):
        orig, out, kind = p.get("orig"), p.get("out"), p.get("kind")
        if not orig or not out:
            bad.append((i, orig, out, "缺 orig 或 out"))
            continue
        fn = REVERSE.get(kind or "")
        if not fn:
            bad.append((i, orig, out, f"不支持的 kind: {kind}"))
            continue
        back = fn(out)
        if back == orig:
            ok += 1
            print(f"  ✅ #{i} {orig} → {out} → {back}  一致")
        else:
            bad.append((i, orig, out, f"反向得到 {back}"))
            print(f"  ❌ #{i} {orig} → {out} → {back}  **不一致**")

    print(f"\n回译校验: 通过 {ok} / 共 {len(pairs)}")
    if bad:
        print("不一致项（这些必须重跑或升档，不能放行）:")
        for i, orig, out, why in bad:
            print(f"  #{i}: {orig} → {out}（{why}）")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
