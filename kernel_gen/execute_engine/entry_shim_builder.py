"""Entry shim builder for ExecutionEngine (P0/S2).

创建者: 朽木露琪亚
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 提供 entry shim 生成与检测逻辑，用于 S2 编译路径的可复现拼装。
- 在可解析函数签名时，生成可运行的 `ordered_args -> function` 绑定代码；
  无法解析时退回占位 shim，保持历史兼容。

使用示例:
- from kernel_gen.execute_engine.entry_shim_builder import build_entry_shim_source, needs_entry_shim
- src = build_entry_shim_source(function="cpu::add", entry_point="kg_execute_entry", source="void foo(){}")
- assert needs_entry_shim("int main(){}", "kg_execute_entry") is True

关联文件:
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_compile.py
- 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class _ParamSpec:
    """函数形参的最小描述。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 描述 entry shim 绑定所需的参数类别与类型信息。
    - 仅在本模块内部使用，不对外暴露。

    使用示例:
    - spec = _ParamSpec(kind="memory", ctype="int32_t", memory_space="GM")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    kind: str
    ctype: str
    memory_space: str | None = None


_INT_TYPE_PATTERN = re.compile(
    r"^(?:const\s+)?(?P<type>"
    r"int|short|long|long\s+long|"
    r"unsigned\s+int|unsigned\s+long|unsigned\s+long\s+long|"
    r"int32_t|int64_t|uint32_t|uint64_t|size_t"
    r")(?:\s*&)?\s+\w+$"
)
_FLOAT_TYPE_PATTERN = re.compile(
    r"^(?:const\s+)?(?P<type>float|double)(?:\s*&)?\s+\w+$"
)
_MEMORY_TYPE_PATTERN = re.compile(
    r"^(?:const\s+)?Memory<\s*(?P<space>[^,\s>]+)\s*,\s*(?P<dtype>[^>\s]+)\s*>\s*&\s+\w+$"
)


def _split_params(params_text: str) -> tuple[str, ...]:
    """按顶层逗号切分函数形参。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 对带模板参数的函数形参进行稳定切分。
    - 忽略 `<...>`、`(...)`、`[...]` 内部逗号，避免误拆。

    使用示例:
    - _split_params("Memory<GM, int32_t>& out, const Memory<GM, int32_t>& lhs")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    if not params_text.strip():
        return ()
    parts: list[str] = []
    current: list[str] = []
    angle_depth = 0
    paren_depth = 0
    bracket_depth = 0
    for ch in params_text:
        if ch == "<":
            angle_depth += 1
        elif ch == ">":
            angle_depth = max(0, angle_depth - 1)
        elif ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth = max(0, paren_depth - 1)
        elif ch == "[":
            bracket_depth += 1
        elif ch == "]":
            bracket_depth = max(0, bracket_depth - 1)
        if ch == "," and angle_depth == 0 and paren_depth == 0 and bracket_depth == 0:
            item = "".join(current).strip()
            if item:
                parts.append(item)
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return tuple(parts)


def _parse_param_spec(param_text: str) -> _ParamSpec | None:
    """把单个形参文本解析为最小参数规格。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 支持 `Memory<Space, T>&`、整型标量、浮点标量三类参数。
    - 不支持的参数形态返回 `None`，由上层回退占位 shim。

    使用示例:
    - _parse_param_spec("const Memory<GM, int32_t>& lhs")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    normalized = " ".join(param_text.strip().split())
    memory_match = _MEMORY_TYPE_PATTERN.match(normalized)
    if memory_match is not None:
        return _ParamSpec(
            kind="memory",
            ctype=memory_match.group("dtype"),
            memory_space=memory_match.group("space"),
        )
    int_match = _INT_TYPE_PATTERN.match(normalized)
    if int_match is not None:
        return _ParamSpec(kind="int", ctype=int_match.group("type"))
    float_match = _FLOAT_TYPE_PATTERN.match(normalized)
    if float_match is not None:
        return _ParamSpec(kind="float", ctype=float_match.group("type"))
    return None


def _extract_param_specs(source: str, function: str) -> tuple[_ParamSpec, ...] | None:
    """从源码中提取 function 定义对应的参数规格。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 在源码中查找目标函数定义并解析参数。
    - 同时尝试完整名称与短名（去命名空间）匹配。

    使用示例:
    - _extract_param_specs("void add_kernel(...)", "add_kernel")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    candidates = [function]
    short_name = function.split("::")[-1]
    if short_name not in candidates:
        candidates.append(short_name)

    for function_name in candidates:
        pattern = re.compile(
            rf"\b{re.escape(function_name)}\s*\((?P<params>.*?)\)\s*\{{",
            re.DOTALL,
        )
        for match in pattern.finditer(source):
            params = _split_params(match.group("params"))
            specs: list[_ParamSpec] = []
            for param in params:
                spec = _parse_param_spec(param)
                if spec is None:
                    specs = []
                    break
                specs.append(spec)
            if specs or not params:
                return tuple(specs)
    return None


def _build_runtime_entry_shim_source(
    *,
    function: str,
    entry_point: str,
    params: tuple[_ParamSpec, ...],
) -> str:
    """根据参数规格生成可运行 entry shim。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 生成稳定的 C ABI 入口：`extern "C" int <entry_point>(...)`。
    - 把 `ordered_args` 映射为函数形参并执行真实调用。

    使用示例:
    - _build_runtime_entry_shim_source(function="add_kernel", entry_point="kg_execute_entry", params=(...))

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    lines: list[str] = [
        f"// runtime entry shim for {function} as {entry_point}",
        "enum KgArgKind : int {",
        "  KG_ARG_MEMORY = 1,",
        "  KG_ARG_INT = 2,",
        "  KG_ARG_FLOAT = 3,",
        "};",
        "struct KgArgSlot {",
        "  int kind;",
        "  void* data;",
        "  const long long* shape;",
        "  const long long* stride;",
        "  unsigned long long rank;",
        "  long long int_value;",
        "  double float_value;",
        "};",
        f'extern "C" int {entry_point}(const KgArgSlot* ordered_args, unsigned long long arg_count) {{',
        "  if (ordered_args == nullptr) {",
        "    return -1;",
        "  }",
        f"  if (arg_count != {len(params)}ULL) {{",
        "    return -1;",
        "  }",
    ]
    for idx, spec in enumerate(params):
        if spec.kind == "memory":
            lines.extend(
                [
                    f"  if (ordered_args[{idx}].kind != KG_ARG_MEMORY) {{",
                    "    return -1;",
                    "  }",
                    f"  if (ordered_args[{idx}].data == nullptr || ordered_args[{idx}].shape == nullptr || ordered_args[{idx}].stride == nullptr) {{",
                    "    return -1;",
                    "  }",
                    f"  Memory<{spec.memory_space}, {spec.ctype}> arg{idx}(",
                    f"      reinterpret_cast<{spec.ctype}*>(ordered_args[{idx}].data),",
                    f"      ordered_args[{idx}].shape,",
                    f"      ordered_args[{idx}].stride,",
                    f"      ordered_args[{idx}].rank);",
                ]
            )
            continue
        if spec.kind == "int":
            lines.extend(
                [
                    f"  if (ordered_args[{idx}].kind != KG_ARG_INT) {{",
                    "    return -1;",
                    "  }",
                    f"  {spec.ctype} arg{idx} = static_cast<{spec.ctype}>(ordered_args[{idx}].int_value);",
                ]
            )
            continue
        lines.extend(
            [
                f"  if (ordered_args[{idx}].kind != KG_ARG_FLOAT) {{",
                "    return -1;",
                "  }",
                f"  {spec.ctype} arg{idx} = static_cast<{spec.ctype}>(ordered_args[{idx}].float_value);",
            ]
        )
    call_args = ", ".join(f"arg{idx}" for idx in range(len(params)))
    lines.extend(
        [
            f"  {function}({call_args});",
            "  return 0;",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def needs_entry_shim(source: str, entry_point: str) -> bool:
    """判断是否需要生成 entry shim。

    创建者: jcc你莫辜负
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 当源码未显式提供 `extern "C"` 且同名入口时，返回 True。
    - 用于避免重复生成已存在的稳定入口。

    使用示例:
    - assert needs_entry_shim('extern "C" int kg_execute_entry(...) { return 0; }', "kg_execute_entry") is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    if not isinstance(source, str) or not isinstance(entry_point, str):
        return True
    pattern = rf'extern\s+"C"\s+[^;{{]*\b{re.escape(entry_point)}\b'
    return re.search(pattern, source) is None


def build_entry_shim_source(*, function: str, entry_point: str, source: str | None = None) -> str:
    """构造 entry shim 源码片段。

    创建者: 朽木露琪亚
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 可解析参数时生成真实参数绑定 shim，用于 `ExecutionEngine.execute` 的真实调用。
    - 参数不可解析时回退最小占位 shim，保持历史编译路径兼容。

    使用示例:
    - src = build_entry_shim_source(function="cpu::add", entry_point="kg_execute_entry", source="void add(){}")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    if isinstance(source, str) and source.strip():
        params = _extract_param_specs(source, function)
        if params is not None:
            return _build_runtime_entry_shim_source(
                function=function,
                entry_point=entry_point,
                params=params,
            )
    return (
        f"// entry shim placeholder for {function} as {entry_point}\n"
        "struct KgArgSlot;\n"
        f'extern "C" int {entry_point}(const KgArgSlot* ordered_args, unsigned long long arg_count) {{\n'
        "  (void)ordered_args;\n"
        "  (void)arg_count;\n"
        "  return 0;\n"
        "}\n"
    )


__all__ = ["build_entry_shim_source", "needs_entry_shim"]
