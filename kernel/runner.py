"""Kernel demo runner.

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 为 `kernel/` 下的本地 demo 脚本提供统一的 `dsl_run -> npu-demo-lowering -> execute` 运行入口。
- 保留 `mlir_gen -> npu-demo-lowering -> gen_kernel` 的只生成入口，便于定位 IR/source。
- 统一设置 `kernel/dump/<case_name>/` 作为 dump 目录；pass IR 与最终源码都由公共 dump 链路写入。
- `dsl_run` 会额外按函数名创建子目录；runner 会把最终源码同步镜像到 `kernel/dump/<case_name>/source.cpp`，避免旧 dump 残留误导。
- 只使用 `kernel_gen` 已公开 API，不承载具体算子逻辑。

API 列表:
- `KERNEL_DUMP_ROOT: Path`
- `KernelTorchDemoResult(case_name: str, dsl_result: DslRunResult, max_abs_diff: float, atol: float, rtol: float)`
- `run_torch_demo(case_name: str, kernel_fn: Callable[..., object], real_args: tuple[object, ...] | list[object], output: object, expected: object, *, atol: float = 1e-4, rtol: float = 1e-4) -> KernelTorchDemoResult`
- `run_lowering_demo(case_name: str, kernel_fn: Callable[..., object], *runtime_args: object) -> tuple[ModuleOp, str]`

使用示例:
- `result = run_torch_demo("matmul/static_shape", matmul_kernel, (out, lhs, rhs), out, lhs @ rhs)`
- `module, source = run_lowering_demo("matmul/static_shape", matmul_kernel, lhs, rhs, out)`

关联文件:
- spec: `spec/kernel/README.md`
- 功能实现: `kernel/runner.py`
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import re

from xdsl.dialects.builtin import ModuleOp

from kernel_gen.core.config import restore_config, set_dump_dir, set_target, snapshot_config
from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
from kernel_gen.dsl.mlir_gen import mlir_gen
from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline
from kernel_gen.tools.dsl_run import DslRunResult, dsl_run

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


def _runtime_module_name(value: object) -> str:
    """提取运行时对象模块名。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 用于轻量识别 torch tensor 与 numpy ndarray。
    - 避免 runner 导入阶段强制加载 torch/numpy。

    使用示例:
    - `_runtime_module_name(tensor)`
    """

    return getattr(value.__class__, "__module__", "") or ""


def _is_torch_tensor(value: object) -> bool:
    """判断对象是否为 torch tensor。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 按公开运行时对象模块名前缀判断。
    - 只服务 `run_torch_demo(...)` 的结果校验。

    使用示例:
    - `_is_torch_tensor(torch.empty(1))`
    """

    return _runtime_module_name(value).startswith("torch")


def _is_numpy_array(value: object) -> bool:
    """判断对象是否为 numpy ndarray。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 按公开运行时对象模块名前缀判断。
    - 只服务 `run_torch_demo(...)` 的结果校验。

    使用示例:
    - `_is_numpy_array(np.empty(1))`
    """

    return _runtime_module_name(value).startswith("numpy")


def _assert_outputs_close(
    case_name: str,
    output: object,
    expected: object,
    *,
    atol: float,
    rtol: float,
) -> float:
    """校验真实执行结果与 PyTorch/NumPy 参考结果一致。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 支持 torch tensor 与 numpy ndarray 两类 `dsl_run` 运行时输出。
    - 返回最大绝对误差，便于 demo 输出摘要。
    - 校验失败时抛出带 case 名与误差的 `AssertionError`。

    使用示例:
    - `max_diff = _assert_outputs_close("matmul", out, expected, atol=1e-4, rtol=1e-4)`
    """

    if _is_torch_tensor(output):
        import torch

        if not _is_torch_tensor(expected):
            raise TypeError("expected must be torch.Tensor when output is torch.Tensor")
        diff = torch.max(torch.abs(output.detach().cpu() - expected.detach().cpu()))
        max_abs_diff = float(diff.item())
        if not torch.allclose(output, expected, atol=atol, rtol=rtol):
            raise AssertionError(
                f"{case_name}: dsl_run output does not match torch reference "
                f"(max_abs_diff={max_abs_diff}, atol={atol}, rtol={rtol})"
            )
        return max_abs_diff

    if _is_numpy_array(output):
        import numpy as np

        if not _is_numpy_array(expected):
            raise TypeError("expected must be numpy.ndarray when output is numpy.ndarray")
        max_abs_diff = float(np.max(np.abs(output - expected)))
        if not np.allclose(output, expected, atol=atol, rtol=rtol):
            raise AssertionError(
                f"{case_name}: dsl_run output does not match numpy reference "
                f"(max_abs_diff={max_abs_diff}, atol={atol}, rtol={rtol})"
            )
        return max_abs_diff

    raise TypeError("output must be torch.Tensor or numpy.ndarray")


def _write_current_source_dump(path: Path, source: str) -> None:
    """写入当前 demo 的最终源码 dump 镜像。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - `dsl_run` 的公开 dump 会写入函数名子目录；这里额外维护 case 根目录下的 `source.cpp`。
    - 覆盖旧源码，避免同一 case 改写后根目录残留 stale `source.cpp`。
    - 始终保证文件以换行结尾。

    使用示例:
    - `_write_current_source_dump(Path("kernel/dump/case/source.cpp"), source)`
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_source = source if source.endswith("\n") else f"{source}\n"
    path.write_text(normalized_source, encoding="utf-8")


@dataclass(frozen=True)
class KernelTorchDemoResult:
    """`run_torch_demo(...)` 的执行与校验结果。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 保存 `dsl_run(...)` 的完整结果对象。
    - 保存输出相对 PyTorch/NumPy 参考结果的最大绝对误差与校验容差。

    使用示例:
    - `result = run_torch_demo("matmul", kernel, (out, lhs, rhs), out, lhs @ rhs)`
    """

    case_name: str
    dsl_result: DslRunResult
    max_abs_diff: float
    atol: float
    rtol: float


def run_torch_demo(
    case_name: str,
    kernel_fn: Callable[..., object],
    real_args: tuple[object, ...] | list[object],
    output: object,
    expected: object,
    *,
    atol: float = 1e-4,
    rtol: float = 1e-4,
) -> KernelTorchDemoResult:
    """通过 `dsl_run` 执行 kernel demo，并和参考结果对齐。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 设置公开 core config target 为 `npu_demo`。
    - 设置 dump 根目录为 `kernel/dump/<case_name>`，由 `dsl_run` 按函数名写出 IR/source。
    - 调用 `dsl_run(kernel_fn, real_args, "npu-demo-lowering")` 完成编译和执行。
    - 校验 `output` 与调用方给出的 PyTorch/NumPy 参考结果一致。
    - 函数结束后恢复调用前 core config，避免 demo 脚本污染后续测试或交互状态。

    使用示例:
    - `run_torch_demo("matmul/static", matmul_kernel, (out, lhs, rhs), out, lhs @ rhs)`
    """

    dump_dir = KERNEL_DUMP_ROOT / _sanitize_case_name(case_name)
    snapshot = snapshot_config()
    try:
        set_target("npu_demo")
        set_dump_dir(dump_dir)
        dsl_result = dsl_run(kernel_fn, real_args, "npu-demo-lowering")
        _write_current_source_dump(dump_dir / "source.cpp", dsl_result.source)
        if not dsl_result.execute_result.ok:
            raise RuntimeError(f"{case_name}: dsl_run execute failed: {dsl_result.execute_result.failure_phrase}")
        max_abs_diff = _assert_outputs_close(case_name, output, expected, atol=atol, rtol=rtol)
        return KernelTorchDemoResult(
            case_name=case_name,
            dsl_result=dsl_result,
            max_abs_diff=max_abs_diff,
            atol=atol,
            rtol=rtol,
        )
    finally:
        restore_config(snapshot)


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
