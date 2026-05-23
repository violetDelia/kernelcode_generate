"""DMA dialect MemoryEffect traits.

功能说明:
- 承载 dma op 使用的 xDSL MemoryEffect trait。
- 这些 trait 只供 dma package 内 op 定义导入，不从 package root re-export。

API 列表:
- `memory_effect(kind: MemoryEffectKind, value: SSAValue) -> EffectInstance`
- `class DmaAllocMemoryEffect(MemoryEffect)`
- `class DmaTargetWriteEffect(MemoryEffect)`
- `class DmaFreeMemoryEffect(MemoryEffect)`
- `class DmaTargetSourceEffect(MemoryEffect)`
- `class DmaBroadcastMemoryEffect(MemoryEffect)`

使用示例:
- `traits = traits_def(DmaTargetSourceEffect())`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/effect.py
"""

from __future__ import annotations

from xdsl.ir import Operation, SSAValue
from xdsl.traits import EffectInstance, MemoryEffect, MemoryEffectKind

from kernel_gen.dialect.nn import NnMemoryType

def memory_effect(kind: MemoryEffectKind, value: SSAValue) -> EffectInstance:
    """构造作用到具体 SSA memory value 的 MemoryEffect。


    功能说明:
    - 将 dma 方言内的 alloc/free/read/write 语义统一绑定到具体 SSA value。
    - 仅供当前文件私有 trait 类复用，不作为跨文件公开 API。

    使用示例:
    - memory_effect(MemoryEffectKind.WRITE, target)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return EffectInstance(kind, SSAValue.get(value))


class DmaAllocMemoryEffect(MemoryEffect):
    """`dma.alloc` 的 alloc effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回 `dma.alloc` 对 result 的 ALLOC effect。


        功能说明:
        - 将新建 memory result 作为 alloc lifecycle 的 effect value。

        使用示例:
        - effects = DmaAllocMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        return {memory_effect(MemoryEffectKind.ALLOC, op.results[0])}


class DmaTargetWriteEffect(MemoryEffect):
    """只写 target memory 的 DMA effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回 target WRITE effect。


        功能说明:
        - 用于 `dma.fill` 这类只写目标 memory、不读取目标旧值的 op。

        使用示例:
        - effects = DmaTargetWriteEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        return {memory_effect(MemoryEffectKind.WRITE, op.operands[0])}


class DmaFreeMemoryEffect(MemoryEffect):
    """`dma.free` 的 free effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回 source FREE effect。


        功能说明:
        - 将被释放 memory operand 作为生命周期释放点。

        使用示例:
        - effects = DmaFreeMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        return {memory_effect(MemoryEffectKind.FREE, op.operands[0])}


class DmaTargetSourceEffect(MemoryEffect):
    """读 source 并写 target 的 DMA effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回 target WRITE 与 source READ effect。


        功能说明:
        - 用于 `dma.copy/load/store/slice/deslice/transpose/cast` 等目标式搬运或转换 op。

        使用示例:
        - effects = DmaTargetSourceEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        return {
            memory_effect(MemoryEffectKind.WRITE, op.operands[0]),
            memory_effect(MemoryEffectKind.READ, op.operands[1]),
        }


class DmaBroadcastMemoryEffect(MemoryEffect):
    """`dma.broadcast` 的目标写与可选 source 读 effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回 broadcast 的 MemoryEffect 集合。


        功能说明:
        - 永远写 target memory。
        - 当 source 是 memory 时额外读 source；scalar source 不产生 memory read effect。

        使用示例:
        - effects = DmaBroadcastMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        effects = {memory_effect(MemoryEffectKind.WRITE, op.operands[0])}
        if isinstance(op.operands[1].type, NnMemoryType):
            effects.add(memory_effect(MemoryEffectKind.READ, op.operands[1]))
        return effects



__all__ = [
    "memory_effect",
    "DmaAllocMemoryEffect",
    "DmaTargetWriteEffect",
    "DmaFreeMemoryEffect",
    "DmaTargetSourceEffect",
    "DmaBroadcastMemoryEffect",
]
