"""DMA dialect canonicalization traits and patterns.

功能说明:
- 提供 dma.fill dead-fill、dma.view identity-view 与 dma.reshape identity/composition 的 canonicalization trait。
- pattern 内只按当前公开 dma op 语义做同 block 局部改写。

API 列表:
- `class DmaFillCanonicalizationTrait(HasCanonicalizationPatternsTrait)`
- `class DmaViewCanonicalizationTrait(HasCanonicalizationPatternsTrait)`
- `class DmaReshapeCanonicalizationTrait(HasCanonicalizationPatternsTrait)`

使用示例:
- `traits = traits_def(DmaFillCanonicalizationTrait())`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/canonicalization.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import ArrayAttr
from xdsl.ir import Attribute, Operation, OpResult, SSAValue
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.traits import EffectInstance, HasCanonicalizationPatternsTrait, MemoryEffectKind, get_effects

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from .common import (
    dim_expr_text,
    operand_int_value,
    symbol_int_expr_text,
    verify_memory_type,
)

class DmaFillCanonicalizationTrait(HasCanonicalizationPatternsTrait):
    """`dma.fill` 的 canonicalization pattern trait。"""

    @classmethod
    def get_canonicalization_patterns(cls) -> tuple[RewritePattern, ...]:
        """返回 `dma.fill` canonicalization pattern。

        功能说明:
        - 暴露 xDSL `CanonicalizePass` 可调用的 `dma.fill` dead-fill pattern。

        使用示例:
        - patterns = DmaFillCanonicalizationTrait.get_canonicalization_patterns()
        """

        return (DmaDeadFillCanonicalizationPattern(),)


class DmaViewCanonicalizationTrait(HasCanonicalizationPatternsTrait):
    """`dma.view` 的 canonicalization pattern trait。"""

    @classmethod
    def get_canonicalization_patterns(cls) -> tuple[RewritePattern, ...]:
        """返回 `dma.view` canonicalization pattern。

        功能说明:
        - 暴露 xDSL `CanonicalizePass` 可调用的 identity-view pattern。

        使用示例:
        - patterns = DmaViewCanonicalizationTrait.get_canonicalization_patterns()
        """

        return (DmaIdentityViewCanonicalizationPattern(),)


class DmaReshapeCanonicalizationTrait(HasCanonicalizationPatternsTrait):
    """`dma.reshape` 的 canonicalization pattern trait。"""

    @classmethod
    def get_canonicalization_patterns(cls) -> tuple[RewritePattern, ...]:
        """返回 `dma.reshape` canonicalization pattern。

        功能说明:
        - 暴露 xDSL `CanonicalizePass` 可调用的 identity-reshape 与一跳 reshape composition pattern。

        使用示例:
        - patterns = DmaReshapeCanonicalizationTrait.get_canonicalization_patterns()
        """

        return (DmaIdentityReshapeCanonicalizationPattern(), DmaComposeReshapeCanonicalizationPattern())


def _is_direct_target_alias(value: SSAValue, target: SSAValue) -> bool:
    """判断 value 是否为 target 的一跳 DMA alias。

    功能说明:
    - 只识别当前合同允许的 `dma.view`、`dma.subview`、`dma.reshape` 一跳 alias。
    - 不做跨 block、跨 region 或多级 alias 推理。

    使用示例:
    - is_alias = _is_direct_target_alias(source, target)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    owner = value.owner
    if not isinstance(owner, Operation):
        return False
    if owner.name == "dma.view":
        return owner.source is target
    if owner.name == "dma.subview":
        return len(owner.source) == 1 and owner.source[0] is target
    if owner.name == "dma.reshape":
        return owner.source is target
    return False


def _is_target_or_direct_alias(value: SSAValue, target: SSAValue) -> bool:
    """判断 value 是否为 target 或 target 的一跳 DMA alias。

    功能说明:
    - 为 `dma.fill` dead-fill pattern 判定 target 是否在覆盖前被读回。

    使用示例:
    - if _is_target_or_direct_alias(value, target): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return value is target or _is_direct_target_alias(value, target)


def _is_direct_alias_definition(op: Operation, target: SSAValue) -> bool:
    """判断 op 是否仅定义 target 的一跳 alias。

    功能说明:
    - `dma.view`、`dma.subview`、`dma.reshape` 是无副作用 alias op，本身不读取数据。
    - alias 的后续 use 会在对应 consumer 上重新判定，alias 定义本身不阻断扫描。

    使用示例:
    - if _is_direct_alias_definition(op, target): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if op.name == "dma.view":
        return op.source is target
    if op.name == "dma.subview":
        return len(op.source) == 1 and op.source[0] is target
    if op.name == "dma.reshape":
        return op.source is target
    return False


def _operation_operands_reference_target(op: Operation, target: SSAValue) -> bool:
    """检查 op operand 是否直接引用 target 或其一跳 alias。

    功能说明:
    - 用于识别无 effect trait 的未知 consumer 或 target-derived alias consumer。

    使用示例:
    - if _operation_operands_reference_target(op, target): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return any(_is_target_or_direct_alias(operand, target) for operand in op.operands)


def _effect_references_target(effect: EffectInstance, target: SSAValue) -> bool:
    """检查 MemoryEffect 是否作用于 target 或其一跳 alias。

    功能说明:
    - 对无具体 SSA value 的 effect 保守视为可能命中 target。

    使用示例:
    - if _effect_references_target(effect, target): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    value = effect.value
    if value is None:
        return True
    if isinstance(value, SSAValue):
        return _is_target_or_direct_alias(value, target)
    return True


def _full_overwrites_fill_target(op: Operation, target: SSAValue) -> bool:
    """判断 op 是否完整覆盖 `dma.fill` 的 target。

    功能说明:
    - 仅承认后续 `dma.fill`、安全 `dma.copy`、标量 `dma.broadcast` 三类 full-overwrite。
    - `dma.copy` 的 source 不得是 target 或 target 的一跳 view/subview/reshape alias。
    - `dma.broadcast` 只有非 memory 标量 source 可覆盖 target。

    使用示例:
    - if _full_overwrites_fill_target(candidate, fill.target): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if op.name == "dma.fill":
        return op.target is target
    if op.name == "dma.copy":
        return op.target is target and not _is_target_or_direct_alias(op.source, target)
    if op.name == "dma.broadcast":
        return op.target is target and not isinstance(op.source.type, NnMemoryType)
    return False


def _blocks_dead_fill_scan(op: Operation, target: SSAValue) -> bool:
    """判断 op 是否阻断 `dma.fill` dead-fill 扫描。

    功能说明:
    - region op、未知 side effect、target read/free/partial write、target alias consumer 均阻断。
    - target 的一跳 alias 定义本身无副作用，不阻断；alias 的 consumer 会阻断。

    使用示例:
    - if _blocks_dead_fill_scan(candidate, fill.target): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if len(op.regions) != 0:
        return True
    if _is_direct_alias_definition(op, target):
        return False
    if _operation_operands_reference_target(op, target):
        return True

    effects = get_effects(op)
    if effects is None:
        return True
    return any(_effect_references_target(effect, target) for effect in effects)


def _has_later_full_overwrite(op: Operation) -> bool:
    """查找同 block 后续完整覆盖 writer。

    功能说明:
    - 从当前 `dma.fill` 的 next sibling 开始线性扫描。
    - 遇到安全 full-overwrite writer 时返回 True；遇到阻断 op 或 block 结束返回 False。

    使用示例:
    - if _has_later_full_overwrite(fill): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    target = op.target
    candidate = op.next_op
    while candidate is not None:
        if _full_overwrites_fill_target(candidate, target):
            return True
        if _blocks_dead_fill_scan(candidate, target):
            return False
        candidate = candidate.next_op
    return False


def _symbol_operands_match_layout(values: Sequence[SSAValue], layout: ArrayAttr[Attribute]) -> bool:
    """判断 symbol operand 列表是否与 layout 逐维一致。

    功能说明:
    - 只做公开表达文本的机械一致性判断，不做代数化简。
    - 任一 operand 不是 `!symbol.int` 时返回 False。

    使用示例:
    - if _symbol_operands_match_layout(op.shape, result_type.shape): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if len(values) != len(layout.data):
        return False
    for value, dim in zip(values, layout.data, strict=True):
        if not isinstance(value.type, SymbolValueType):
            return False
        if symbol_int_expr_text(value, "layout") != dim_expr_text(dim):
            return False
    return True


def _all_symbol_operands_static_value(values: Sequence[SSAValue], expected: int) -> bool:
    """判断所有 symbol operand 是否为同一静态整数。

    功能说明:
    - 用于 identity view 的 offset=0 与 stride=1 机械条件。

    使用示例:
    - if _all_symbol_operands_static_value(op.offsets, 0): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return all(operand_int_value(value) == expected for value in values)


def _identity_alias_replacement_keeps_consumer_inputs_distinct(result: SSAValue, source: SSAValue) -> bool:
    """判断 identity alias 替换是否会合并同一 consumer 的输入。

    功能说明:
    - `dma.view` / `dma.reshape` result 若被某个 op 使用，且该 op 同时直接使用原 source，
      替换 result 会把 target-derived alias read 变成同一 SSA value 的自读写形态。
    - 这类形态需要保留 alias op，供 dead-fill canonicalization 与后续 pass 继续观察原始读关系。

    使用示例:
    - if _identity_alias_replacement_keeps_consumer_inputs_distinct(op.result, op.source): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    for use in tuple(result.uses):
        if any(operand is source for operand in use.operation.operands):
            return False
    return True


def _is_identity_view(op: Operation) -> bool:
    """判断 `dma.view` 是否为机械 identity view。

    功能说明:
    - 只在 source/result type 完全一致、offset 全 0、shape 完全一致、stride 全 1 时返回 True。
    - byte-pool typed view、shape/stride 改变或动态不可证明场景均返回 False。

    使用示例:
    - if _is_identity_view(view): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    source_type = verify_memory_type(op.source.type, "source")
    result_type = verify_memory_type(op.result.type, "result")
    if source_type != result_type:
        return False
    return (
        _all_symbol_operands_static_value(op.offsets, 0)
        and _symbol_operands_match_layout(op.shape, result_type.shape)
        and _all_symbol_operands_static_value(op.stride, 1)
        and _identity_alias_replacement_keeps_consumer_inputs_distinct(op.result, op.source)
    )


def _is_identity_reshape(op: Operation) -> bool:
    """判断 `dma.reshape` 是否为机械 identity reshape。

    功能说明:
    - 只在 source/result type 完全一致且 shape operand 完全等于 source/result shape 时返回 True。
    - rank 改变、same-rank shape 改变或动态不可证明场景均返回 False。

    使用示例:
    - if _is_identity_reshape(reshape): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    source_type = verify_memory_type(op.source.type, "source")
    result_type = verify_memory_type(op.result.type, "result")
    return (
        source_type == result_type
        and _symbol_operands_match_layout(op.shape, result_type.shape)
        and _identity_alias_replacement_keeps_consumer_inputs_distinct(op.result, op.source)
    )


def _one_hop_source_reshape(op: Operation) -> Operation | None:
    """返回可与当前 reshape 合并的一跳 source reshape。

    功能说明:
    - 只识别 `current.source` 直接来自另一个 `dma.reshape` result 的一跳结构。
    - 前序 reshape result 必须只有当前 reshape 这一个 use，避免删除仍被其它 consumer 使用的 view。

    使用示例:
    - previous = _one_hop_source_reshape(current)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if not isinstance(op.source, OpResult):
        return None
    previous_op = op.source.op
    if previous_op.name != "dma.reshape":
        return None
    uses = tuple(previous_op.result.uses)
    if len(uses) != 1 or uses[0].operation is not op:
        return None
    return previous_op


class DmaDeadFillCanonicalizationPattern(RewritePattern):
    """删除被后续完整覆盖的 `dma.fill`。"""

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter, /) -> None:
        """匹配并删除 dead fill。

        功能说明:
        - 仅当同 block 后续 sibling 对同一 target 做安全完整覆盖时删除当前 `dma.fill`。

        使用示例:
        - _DmaDeadFillCanonicalizationPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if op.name != "dma.fill":
            return
        if _has_later_full_overwrite(op):
            rewriter.erase_op(op)


class DmaIdentityViewCanonicalizationPattern(RewritePattern):
    """删除 identity `dma.view`。"""

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter, /) -> None:
        """匹配并删除 identity view。

        功能说明:
        - 将 identity `dma.view` 的 result uses 替换为 source。

        使用示例:
        - _DmaIdentityViewCanonicalizationPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if op.name != "dma.view":
            return
        if _is_identity_view(op):
            rewriter.replace_matched_op([], [op.source])


class DmaIdentityReshapeCanonicalizationPattern(RewritePattern):
    """删除 identity `dma.reshape`。"""

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter, /) -> None:
        """匹配并删除 identity reshape。

        功能说明:
        - 将 identity `dma.reshape` 的 result uses 替换为 source。

        使用示例:
        - _DmaIdentityReshapeCanonicalizationPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if op.name != "dma.reshape":
            return
        if _is_identity_reshape(op):
            rewriter.replace_matched_op([], [op.source])


class DmaComposeReshapeCanonicalizationPattern(RewritePattern):
    """把一跳连续 `dma.reshape` 合并为一个 `dma.reshape`。"""

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter, /) -> None:
        """匹配并合并一跳连续 reshape。

        功能说明:
        - 将 `reshape(reshape(source))` 改写为从原始 source 到最终 result type 的单个 `dma.reshape`。
        - 仅当前序 reshape result 只有当前 reshape 一个 use 时改写。

        使用示例:
        - _DmaComposeReshapeCanonicalizationPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if op.name != "dma.reshape":
            return
        previous = _one_hop_source_reshape(op)
        if previous is None:
            return
        from .operation.alias import DmaReshapeOp
        merged = DmaReshapeOp(previous.source, list(op.shape), op.result.type)
        rewriter.replace_matched_op(merged)
        rewriter.erase_op(previous)



__all__ = [
    "DmaFillCanonicalizationTrait",
    "DmaViewCanonicalizationTrait",
    "DmaReshapeCanonicalizationTrait",
]
