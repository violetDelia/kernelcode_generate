"""Kernel demo runner.

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 为 `kernel/` 下的本地 demo 脚本提供统一的 `mlir_gen -> npu-demo-lowering -> gen_kernel` 运行入口。
- 统一设置 `kernel/dump/<case_name>/` 作为 dump 目录；pass IR 与最终源码都由公共 dump 链路写入。
- 只使用 `kernel_gen` 已公开 API，不承载具体算子逻辑。

API 列表:
- `KERNEL_DUMP_ROOT: Path`
- `run_lowering_demo(case_name: str, kernel_fn: Callable[..., object], *runtime_args: object) -> tuple[ModuleOp, str]`

使用示例:
- `module, source = run_lowering_demo("matmul/static_shape", matmul_kernel, lhs, rhs, out)`

关联文件:
- spec: `spec/kernel/README.md`
- 功能实现: `kernel/runner.py`
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import re

from xdsl.dialects.builtin import ModuleOp

from kernel_gen.core.config import restore_config, set_dump_dir, set_target, snapshot_config
from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
from kernel_gen.dsl.mlir_gen import mlir_gen
from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline

KERNEL_DUMP_ROOT = Path(__file__).resolve().parent / "dump"


def _sanitize_case_name(case_name: str) -> Path:
    """规整 demo case 名称为相对 dump 路径。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 允许调用方传入 `operator/case` 形式的相对路径。
    - 每段只保留字母、数字、点、下划线和短横线，其余字符替换为 `_`。
    - 拒绝空名称，避免 dump 直接写到根目录。

    使用示例:
    - `_sanitize_case_name("matmul/static_shape")`
    """

    if not isinstance(case_name, str) or not case_name.strip():
        raise ValueError("case_name must be non-empty str")
    parts = [
        re.sub(r"[^A-Za-z0-9_.-]+", "_", item.strip())
        for item in case_name.split("/")
        if item.strip()
    ]
    if not parts:
        raise ValueError("case_name must contain at least one path segment")
    return Path(*parts)


def run_lowering_demo(
    case_name: str,
    kernel_fn: Callable[..., object],
    *runtime_args: object,
) -> tuple[ModuleOp, str]:
    """运行一个 kernel demo 并写出 IR/source dump。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 使用 `mlir_gen(...)` 生成初始 module。
    - 使用 `build_npu_demo_lowering_pipeline().run(...)` 执行 lowering。
    - 通过 `set_dump_dir(kernel/dump/<case_name>)` 让 pass manager 写入 `01-first-ir.mlir` 和逐 pass IR。
    - 使用 `gen_kernel(module, EmitCContext())` 生成 npu_demo 源码；`gen_kernel` 根据同一 dump 配置写入 `source.cpp`。
    - 函数结束后恢复调用前 core config，避免 demo 脚本污染后续测试或交互状态。

    使用示例:
    - `module, source = run_lowering_demo("matmul/dynamic_shape", matmul_kernel, lhs, rhs, out, tile_m, tile_n)`
    """

    dump_dir = KERNEL_DUMP_ROOT / _sanitize_case_name(case_name)
    snapshot = snapshot_config()
    try:
        set_target("npu_demo")
        set_dump_dir(dump_dir)
        module = mlir_gen(kernel_fn, *runtime_args)
        lowered_module = build_npu_demo_lowering_pipeline().run(module)
        if not isinstance(lowered_module, ModuleOp):
            raise TypeError("npu-demo lowering pipeline must return ModuleOp")
        source = gen_kernel(lowered_module, EmitCContext())
        return lowered_module, source
    finally:
        restore_config(snapshot)
