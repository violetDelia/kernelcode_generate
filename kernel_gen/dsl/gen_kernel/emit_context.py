"""`gen_kernel.emit` 公开上下文定义。

创建者: 小李飞刀
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 定义 `EmitCContext` 稳定公开入口。
- 供 `emit` / `emit_c` / `gen_kernel` 共享同一份上下文；失败统一抛出 `KernelCodeError(module="gen_kernel")`。
- 目标行为配置只从 `kernel_gen.core.config` 读取，当前上下文只承载单次 EmitC 发射状态。

API 列表:
- `EmitCContext()`
- `EmitCContext.create_or_get_name(value: SSAValue) -> str`
- `EmitCContext.allocate_name(prefix: str) -> str`
- `EmitCContext.lookup_cached_name(scope: str, key: object) -> str | None`
- `EmitCContext.bind_cached_name(scope: str, key: object, name: str) -> str`
- `EmitCContext.is_target(name: str) -> bool`
- `EmitCContext.target_entry(table: Mapping[str, T], default: T | None = None) -> T | None`
- `EmitCContext.emit_error(subject: str, reason: str) -> KernelCodeError`
- `EmitCContext.dispatch(obj: Any) -> str | None`
- `EmitCContext.dispatch_op(op: Operation) -> str | None`
- `EmitCContext.dispatch_value(value: SSAValue) -> str | None`
- `EmitCContext.dispatch_type(attr: Any) -> str`
- `EmitCContext.dispatch_attr(attr: Any) -> str | None`
- `EmitCContext.dispatch_include() -> str`

helper 清单:
- `EmitCContext.current_indent -> str`
- `EmitCContext.push_indent() -> None`
- `EmitCContext.pop_indent() -> None`
- `EmitCContext.bind_name(value: SSAValue, name: str) -> str`
- `EmitCContext.lookup_name(value: SSAValue) -> str | None`

使用示例:
- from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
- from kernel_gen.core.config import set_target
- set_target("npu_demo")
- ctx = EmitCContext()

关联文件:
- spec: [spec/dsl/gen_kernel/emit_context.md](../../../spec/dsl/gen_kernel/emit_context.md)
- spec: [spec/dsl/gen_kernel/emit.md](../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_context.py](../../../kernel_gen/dsl/gen_kernel/emit_context.py)
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

import re
from collections.abc import Mapping
from typing import Any, TypeVar

from xdsl.ir import SSAValue
from xdsl.ir import Operation

from kernel_gen.core.config import get_target


T = TypeVar("T")


class EmitCContext:
    """单次片段生成上下文。"""

    _names: dict[int, str]
    _next_id: int
    _indent_level: int
    _target: str

    def __init__(self) -> None:
        """初始化公开 `EmitCContext`。

        创建者: 朽木露琪亚
        最后一次更改: 守护最好的爱莉希雅

        功能说明:
        - 从 `kernel_gen.core.config.get_target()` 读取当前公开 target 配置。
        - 拒绝未设置或非空字符串以外的 target。
        - 仅初始化单次 EmitC 发射状态，不接受任意公开 config 字典。

        使用示例:
        - set_target("npu_demo")
        - EmitCContext()

        关联文件:
        - spec: spec/dsl/gen_kernel/emit_context.md
        - test: test/dsl/gen_kernel/emit/test_emit.py
        - 功能实现: kernel_gen/dsl/gen_kernel/emit_context.py
        """

        target_value = get_target()
        if not isinstance(target_value, str) or not target_value:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.GEN_KERNEL, "EmitCContext: target must be non-empty str")
        self._target = target_value
        self._indent = "    "
        self._state: dict[str, object] = {}
        self._names = {}
        self._next_id = 0
        self._indent_level = 0

    def is_target(self, name: str) -> bool:
        """判断当前上下文是否使用指定 target。

        创建者: 守护最好的爱莉希雅
        最后一次更改: 守护最好的爱莉希雅

        功能说明:
        - 供 emit 内部按 target 分支，不对外暴露原始 target 字符串属性。

        使用示例:
        - if ctx.is_target("cpu"):
        -     ...
        """

        return self._target == name

    def target_entry(self, table: Mapping[str, T], default: T | None = None) -> T | None:
        """按当前 target 从表中选择条目。

        创建者: 守护最好的爱莉希雅
        最后一次更改: 守护最好的爱莉希雅

        功能说明:
        - 供 target registry 查表使用，避免跨文件直接读取 target 字符串属性。

        使用示例:
        - handler = ctx.target_entry(registry)
        """

        return table.get(self._target, default)

    def emit_error(self, subject: str, reason: str) -> KernelCodeError:
        """构造带 target 前缀的 gen_kernel 合同错误。

        创建者: 守护最好的爱莉希雅
        最后一次更改: 守护最好的爱莉希雅

        功能说明:
        - 统一当前 emit context 的错误拼接逻辑。
        - `reason` 为空字符串时，`subject` 作为完整错误文本使用。

        使用示例:
        - raise ctx.emit_error("dma.copy", "dma ops are cpu-only")
        """

        if reason:
            message = f"target={self._target}: {subject}: {reason}"
        else:
            message = f"target={self._target}: {subject}"
        return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.GEN_KERNEL, message)

    @property
    def current_indent(self) -> str:
        return self._indent * self._indent_level

    def allocate_name(self, prefix: str) -> str:
        """按前缀分配当前上下文内递增名称。

        创建者: 守护最好的爱莉希雅
        最后一次更改: 守护最好的爱莉希雅

        功能说明:
        - 替代对内部状态字典的直接访问。
        - 同一 prefix 在单个 context 内按 `prefix0`、`prefix1` 递增。

        使用示例:
        - temp_name = ctx.allocate_name("dma")
        """

        counters = self._state.setdefault("name_counters", {})
        if not isinstance(counters, dict):
            raise self.emit_error("state name_counters", "unsupported state")
        current = int(counters.get(prefix, 0))
        counters[prefix] = current + 1
        return f"{prefix}{current}"

    def lookup_cached_name(self, scope: str, key: object) -> str | None:
        """读取当前上下文内按 scope/key 缓存的名称。

        创建者: 守护最好的爱莉希雅
        最后一次更改: 守护最好的爱莉希雅

        功能说明:
        - 只返回名称字符串，不暴露可变状态字典。

        使用示例:
        - name = ctx.lookup_cached_name("symbol_const", 7)
        """

        value = self._state.setdefault(scope, {})
        if not isinstance(value, dict):
            raise self.emit_error(f"state {scope}", "unsupported state")
        cached = value.get(key)
        if cached is None:
            return None
        if not isinstance(cached, str):
            raise self.emit_error(f"state {scope}", "cached name must be str")
        return cached

    def bind_cached_name(self, scope: str, key: object, name: str) -> str:
        """写入当前上下文内按 scope/key 缓存的名称。

        创建者: 守护最好的爱莉希雅
        最后一次更改: 守护最好的爱莉希雅

        功能说明:
        - 替代直接修改内部状态字典。

        使用示例:
        - ctx.bind_cached_name("symbol_const", 7, "c_7")
        """

        if not isinstance(name, str) or not name:
            raise self.emit_error(f"state {scope}", "cached name must be non-empty str")
        value = self._state.setdefault(scope, {})
        if not isinstance(value, dict):
            raise self.emit_error(f"state {scope}", "unsupported state")
        value[key] = name
        return name

    def push_indent(self) -> None:
        self._indent_level += 1

    def pop_indent(self) -> None:
        if self._indent_level == 0:
            return
        self._indent_level -= 1

    def bind_name(self, value: SSAValue, name: str) -> str:
        self._names[id(value)] = name
        return name

    def lookup_name(self, value: SSAValue) -> str | None:
        return self._names.get(id(value))

    def _dedupe_name(self, name: str) -> str:
        """生成当前上下文内不冲突的变量名。

        创建者: OpenAI Codex
        最后一次更改: OpenAI Codex

        功能说明:
        - 若候选名未被占用则原样返回。
        - 若候选名已带 `_数字` 后缀，则递增该后缀，避免生成 `name_1_1` 这类不稳定名字。

        使用示例:
        - unique_name = ctx._dedupe_name("src_1")
        """

        used_names = set(self._names.values())
        if name not in used_names:
            return name
        suffix_match = re.match(r"^(.*)_([0-9]+)$", name)
        if suffix_match is None:
            base_name = name
            suffix = 1
        else:
            base_name = suffix_match.group(1)
            suffix = int(suffix_match.group(2)) + 1
        while f"{base_name}_{suffix}" in used_names:
            suffix += 1
        return f"{base_name}_{suffix}"

    def _allocate_name(self, value: SSAValue) -> str:
        """分配兜底 SSA 名称。

        创建者: OpenAI Codex
        最后一次更改: OpenAI Codex

        功能说明:
        - 生成 `vN` 递增临时名。
        - 不读取公开 config；命名策略属于单次发射内部状态，不作为跨文件公开配置。

        使用示例:
        - name = ctx._allocate_name(value)
        """

        name = f"v{self._next_id}"
        self._next_id += 1
        return name

    def create_or_get_name(self, value: SSAValue) -> str:
        existing = self.lookup_name(value)
        if existing is not None:
            return existing

        from .emit.register import dispatch_name

        name = dispatch_name(value, self)
        if name is None:
            name = self._allocate_name(value)
        return self.bind_name(value, self._dedupe_name(name))

    def dispatch(self, obj: Any) -> str | None:
        if isinstance(obj, SSAValue):
            return self.dispatch_value(obj)
        if isinstance(obj, Operation):
            return self.dispatch_op(obj)
        return self.dispatch_attr(obj)

    def dispatch_op(self, op: Operation) -> str | None:
        from .emit.register import dispatch_op

        return dispatch_op(op, self)

    def dispatch_value(self, value: SSAValue) -> str | None:
        from .emit.register import dispatch_value

        return dispatch_value(value, self)

    def dispatch_type(self, attr: Any) -> str:
        """把 xDSL / 仓库类型 attr 发射为 C/C++ 类型文本。

        创建者: OpenAI Codex
        最后一次更改: 守护最好的爱莉希雅

        功能说明:
        - 只通过 target type registry 发射类型文本。
        - 不接收公开 type_converter 配置；类型转换策略必须由 target 注册表承载。

        使用示例:
        - c_type = ctx.dispatch_type(i32)
        """

        from .emit.register import dispatch_type

        try:
            dispatched = dispatch_type(attr, self)
        except ValueError as exc:
            raise self.emit_error("dispatch_type", str(exc)) from exc
        if dispatched is not None:
            return dispatched
        raise self.emit_error(f"type {attr}", "unsupported type")

    def dispatch_attr(self, attr: Any) -> str | None:
        from .emit.register import dispatch_attr

        try:
            return dispatch_attr(attr, self)
        except ValueError as exc:
            raise self.emit_error("dispatch_attr", str(exc)) from exc

    def dispatch_include(self) -> str:
        from .emit.register import dispatch_include

        return dispatch_include(self)

__all__ = ["EmitCContext"]
