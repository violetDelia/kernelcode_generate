"""Conv2d symbolic memory gen_kernel tests.


功能说明:
- 覆盖 `kernel/conv2d/inputs_dynamic_tile_dynamic.py` 的符号 memory 编译形态。
- 覆盖两条 static conv2d demo 将 per-run random 选值具体化到 static IR 的编译形态。
- 验证 `run_lowering_demo(...)` 通过公开 `mlir_gen -> lowering -> gen_kernel` 链路生成动态 memory IR/source。
- 验证 C/K reduce 维和 matmul 一样使用本地 accumulator，不允许通过反复读写 out 累计 partial。

API 列表:
- 无（pytest 文件，不承载公开 API）

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
- 功能实现: `kernel/conv2d/inputs_static_tile_dynamic.py`
- 功能实现: `kernel/conv2d/inputs_static_tile_static.py`
- 公共运行器: `kernel/runner.py`
- 测试文件: `test/kernel/test_conv2d_symbolic_memory_genkernel.py`
"""

from __future__ import annotations

import inspect
import os
from ast import literal_eval
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TypeAlias

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.conv2d.inputs_dynamic_tile_dynamic import conv2d_inputs_dynamic_tile_dynamic_kernel
from kernel.conv2d.inputs_static_tile_dynamic import conv2d_inputs_static_tile_dynamic_kernel
from kernel.conv2d.inputs_static_tile_static import conv2d_inputs_static_tile_static_kernel
from kernel.runner import run_lowering_demo
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

Conv2dCompileArg: TypeAlias = "Memory | SymbolDim"
_CONV_STATIC_STATIC_SHAPE_RNG = random.Random(2026052701)
_CONV_SS_B = _CONV_STATIC_STATIC_SHAPE_RNG.randint(4, 6)
_CONV_SS_CIN = _CONV_STATIC_STATIC_SHAPE_RNG.randint(48, 64)
_CONV_SS_H = _CONV_STATIC_STATIC_SHAPE_RNG.randint(241, 289)
_CONV_SS_W = _CONV_STATIC_STATIC_SHAPE_RNG.randint(225, 273)
_CONV_SS_F = _CONV_STATIC_STATIC_SHAPE_RNG.randint(18, 24)
_CONV_SS_KH = _CONV_STATIC_STATIC_SHAPE_RNG.choice((3, 5))
_CONV_SS_KW = _CONV_STATIC_STATIC_SHAPE_RNG.choice((3, 5))
_CONV_SS_PADDING = tuple(_CONV_STATIC_STATIC_SHAPE_RNG.choice((0, 1, 2, 3, 4)) for _ in range(4))
_CONV_SS_HO = ((_CONV_SS_H + _CONV_SS_PADDING[0] + _CONV_SS_PADDING[1] - _CONV_SS_KH) // 8) + 1
_CONV_SS_WO = ((_CONV_SS_W + _CONV_SS_PADDING[2] + _CONV_SS_PADDING[3] - _CONV_SS_KW) // 8) + 1
_CONV_SS_TILE = random.Random(2026051721).choice(((8, 16, 4, 8, 9), (7, 18, 3, 9, 8), (6, 20, 2, 10, 7)))
_CONV_STATIC_DYNAMIC_SHAPE_RNG = random.Random(2026052702)
_CONV_SD_B = _CONV_STATIC_DYNAMIC_SHAPE_RNG.randint(4, 6)
_CONV_SD_CIN = _CONV_STATIC_DYNAMIC_SHAPE_RNG.randint(48, 64)
_CONV_SD_H = _CONV_STATIC_DYNAMIC_SHAPE_RNG.randint(241, 289)
_CONV_SD_W = _CONV_STATIC_DYNAMIC_SHAPE_RNG.randint(225, 273)
_CONV_SD_F = _CONV_STATIC_DYNAMIC_SHAPE_RNG.randint(18, 24)
_CONV_SD_KH = _CONV_STATIC_DYNAMIC_SHAPE_RNG.choice((3, 5))
_CONV_SD_KW = _CONV_STATIC_DYNAMIC_SHAPE_RNG.choice((3, 5))
_CONV_SD_PADDING = tuple(_CONV_STATIC_DYNAMIC_SHAPE_RNG.choice((0, 1, 2, 3, 4)) for _ in range(4))
_CONV_SD_HO = ((_CONV_SD_H + _CONV_SD_PADDING[0] + _CONV_SD_PADDING[1] - _CONV_SD_KH) // 8) + 1
_CONV_SD_WO = ((_CONV_SD_W + _CONV_SD_PADDING[2] + _CONV_SD_PADDING[3] - _CONV_SD_KW) // 8) + 1
_CONV_SD_TILE = random.Random(2026051724).choice(((8, 16, 4, 8, 9), (7, 18, 3, 9, 8), (6, 20, 2, 10, 7)))
_CONV_DYNAMIC_SHAPE_RNG = random.Random(2026052703)
_CONV_DD_B = _CONV_DYNAMIC_SHAPE_RNG.randint(4, 6)
_CONV_DD_CIN = _CONV_DYNAMIC_SHAPE_RNG.randint(48, 64)
_CONV_DD_H = _CONV_DYNAMIC_SHAPE_RNG.randint(241, 289)
_CONV_DD_W = _CONV_DYNAMIC_SHAPE_RNG.randint(225, 273)
_CONV_DD_F = _CONV_DYNAMIC_SHAPE_RNG.randint(18, 24)
_CONV_DD_KH = _CONV_DYNAMIC_SHAPE_RNG.choice((3, 5))
_CONV_DD_KW = _CONV_DYNAMIC_SHAPE_RNG.choice((3, 5))
_CONV_DD_PADDING = tuple(_CONV_DYNAMIC_SHAPE_RNG.choice((0, 1, 2, 3, 4)) for _ in range(4))
_CONV_DD_HO = ((_CONV_DD_H + _CONV_DD_PADDING[0] + _CONV_DD_PADDING[1] - _CONV_DD_KH) // 8) + 1
_CONV_DD_WO = ((_CONV_DD_W + _CONV_DD_PADDING[2] + _CONV_DD_PADDING[3] - _CONV_DD_KW) // 8) + 1
_CONV_DD_TILE = random.Random(2026051726).choice(((8, 16, 4, 8, 9), (7, 18, 3, 9, 8), (6, 20, 2, 10, 7)))
STATIC_STATIC_OUTPUT_MEMORY = (
    f"!nn.memory<[#symbol.expr<{_CONV_SS_B}>, #symbol.expr<{_CONV_SS_F}>, "
    f"#symbol.expr<{_CONV_SS_HO}>, #symbol.expr<{_CONV_SS_WO}>]"
)
STATIC_STATIC_INPUT_MEMORY = (
    f"!nn.memory<[#symbol.expr<{_CONV_SS_B}>, #symbol.expr<{_CONV_SS_CIN}>, "
    f"#symbol.expr<{_CONV_SS_H}>, #symbol.expr<{_CONV_SS_W}>]"
)
STATIC_STATIC_WEIGHT_MEMORY = (
    f"!nn.memory<[#symbol.expr<{_CONV_SS_F}>, #symbol.expr<{_CONV_SS_CIN}>, "
    f"#symbol.expr<{_CONV_SS_KH}>, #symbol.expr<{_CONV_SS_KW}>]"
)
STATIC_STATIC_BIAS_MEMORY = f"!nn.memory<[#symbol.expr<{_CONV_SS_F}>]"
STATIC_DYNAMIC_OUTPUT_MEMORY = (
    f"!nn.memory<[#symbol.expr<{_CONV_SD_B}>, #symbol.expr<{_CONV_SD_F}>, "
    f"#symbol.expr<{_CONV_SD_HO}>, #symbol.expr<{_CONV_SD_WO}>]"
)
STATIC_DYNAMIC_INPUT_MEMORY = (
    f"!nn.memory<[#symbol.expr<{_CONV_SD_B}>, #symbol.expr<{_CONV_SD_CIN}>, "
    f"#symbol.expr<{_CONV_SD_H}>, #symbol.expr<{_CONV_SD_W}>]"
)
STATIC_DYNAMIC_WEIGHT_MEMORY = (
    f"!nn.memory<[#symbol.expr<{_CONV_SD_F}>, #symbol.expr<{_CONV_SD_CIN}>, "
    f"#symbol.expr<{_CONV_SD_KH}>, #symbol.expr<{_CONV_SD_KW}>]"
)
STATIC_DYNAMIC_BIAS_MEMORY = f"!nn.memory<[#symbol.expr<{_CONV_SD_F}>]"
SEMANTIC_OUTPUT_MEMORY = (
    "!nn.memory<[#symbol.expr<B>, #symbol.expr<C>, #symbol.expr<-KH + XH + 1>, #symbol.expr<-KW + XW + 1>]"
)
SEMANTIC_OUTPUT_PREFIX = "!nn.memory<[#symbol.expr<B>, #symbol.expr<C>,"
SEMANTIC_INPUT_MEMORY = "!nn.memory<[#symbol.expr<B>, #symbol.expr<N>, #symbol.expr<XH>, #symbol.expr<XW>]"
SEMANTIC_WEIGHT_MEMORY = "!nn.memory<[#symbol.expr<C>, #symbol.expr<N>, #symbol.expr<KH>, #symbol.expr<KW>]"
SEMANTIC_BIAS_MEMORY = "!nn.memory<[#symbol.expr<C>]"
SEMANTIC_RUNTIME_SYMBOLS = ("SH", "SW", "DH", "DW", "PT", "PB", "PL", "PR", "TF", "TC", "TN", "THO", "TWO")


def _assert_conv2d_source_uses_kernel_out_first(fn) -> None:
    """校验 conv2d demo Python 源码使用 kernel out-first helper。


    功能说明:
    - 当前测试文件内 helper，只读取公开 demo 函数源码。
    - 防止 demo 主计算入口回退到 `nn.img2col2d/nn.matmul/nn.add`。

    使用示例:
    - `_assert_conv2d_source_uses_kernel_out_first(conv2d_inputs_dynamic_tile_dynamic_kernel)`
    """

    function_source = inspect.getsource(fn)
    assert "kernel.img2col2d(" in function_source
    assert "kernel.matmul(" in function_source
    assert "kernel.add(" in function_source
    assert "for c0 in loop(0, c_size, tile_c)" in function_source
    assert "for ni in loop(0, cur_n, 1)" in function_source
    assert "batch_tile = min(n_size, 1)" in function_source
    assert "k_tile = cur_c * kh_size * kw_size" in function_source
    assert "col = alloc([batch_tile, cur_c, kh_size, kw_size, cur_ho, cur_wo]" in function_source
    assert "col2 = reshape(col, [k_tile, out_tile])" in function_source
    assert "acc = alloc([batch_tile, tile_f, tile_ho, tile_wo]" in function_source
    assert "bias_tile = alloc([tile_f]" in function_source
    assert "bias_nchw = reshape(bias_tile, [1, tile_f, 1, 1])" in function_source
    assert "partial = transpose(out_fnhw, [1, 0, 2, 3])" in function_source
    assert "partial_full = alloc([batch_tile, tile_f, tile_ho, tile_wo]" in function_source
    assert "deslice(partial_full, partial, [0, 0, 0, 0], [batch_tile, cur_f, cur_ho, cur_wo]" in function_source
    assert "kernel.add(acc, acc, partial_full)" in function_source
    assert "if bias is not None:" in function_source
    assert "bias_current = view(bias_tile, [0], [cur_f], [1])" in function_source
    assert "broadcast(bias_full, bias_nchw)" in function_source
    assert "acc_current = view(acc, [0, 0, 0, 0], [batch_tile, cur_f, cur_ho, cur_wo]" in function_source
    assert "[batch_index, f0, ho0, wo0]" in function_source
    assert "partial_tile = alloc" not in function_source
    assert "out_tile_mem = slice(out" not in function_source
    assert "col = img2col2d(" not in function_source
    assert "out2 = matmul(" not in function_source
    assert "acc = alloc([batch_tile, cur_f, cur_ho, cur_wo]" not in function_source
    assert "bias_tile = alloc([cur_f]" not in function_source
    assert "kernel.add(acc, acc, partial)" not in function_source


def _read_first_ir(case_name: str) -> str:
    """读取公开 dump 目录中的生成侧 first-ir。

    功能说明:
    - 只读取 `run_lowering_demo(...)` 公开写出的 `kernel/dump/<case>/01-first-ir.mlir`。
    - 用于验证 DSL/kernel 生成侧已产生 fixed upper-bound scratch，而不是依赖后续 pass 掩盖。

    使用示例:
    - `_read_first_ir("test_conv2d/inputs_dynamic_tile_dynamic_symbolic_memory")`
    """

    return (_REPO_ROOT / "kernel" / "dump" / Path(case_name) / "01-first-ir.mlir").read_text(encoding="utf-8")


def _run_kernel_script(script: str) -> subprocess.CompletedProcess[str]:
    """运行 conv2d demo 脚本并返回完成对象。

    功能说明:
    - 运行前清理对应公开 dump 目录，防止读取旧 source/IR。
    - 只通过公开 Python 脚本入口验证 demo，可捕获编译或执行失败。

    使用示例:
    - `_run_kernel_script("kernel/conv2d/inputs_static_tile_dynamic.py")`
    """

    dump_cases = {
        "kernel/conv2d/inputs_static_tile_static.py": (
            "conv2d/inputs_static_tile_static_absent_bias",
            "conv2d/inputs_static_tile_static_present_bias",
        ),
        "kernel/conv2d/inputs_static_tile_dynamic.py": ("conv2d/inputs_static_tile_dynamic",),
        "kernel/conv2d/inputs_dynamic_tile_dynamic.py": ("conv2d/inputs_dynamic_tile_dynamic",),
    }
    for case_name in dump_cases[script]:
        shutil.rmtree(_REPO_ROOT / "kernel" / "dump" / Path(case_name), ignore_errors=True)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(_REPO_ROOT)
    return subprocess.run(
        [sys.executable, script],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
        timeout=600,
    )


def _assert_source_dump_contains(case_name: str, markers: tuple[str, ...]) -> None:
    """校验公开 source.cpp dump 来自本次脚本运行。

    功能说明:
    - 读取 `kernel/dump/<case_name>/source.cpp` 并核对关键源码 marker。
    - 只验证公开 dump 文件，不读取测试临时目录。

    使用示例:
    - `_assert_source_dump_contains("conv2d/inputs_static_tile_dynamic", ("npu_demo::launch",))`
    """

    source_path = _REPO_ROOT / "kernel" / "dump" / Path(case_name) / "source.cpp"
    assert source_path.exists()
    source_dump = source_path.read_text(encoding="utf-8")
    missing_markers = tuple(marker for marker in markers if marker not in source_dump)
    assert source_dump.strip()
    assert not missing_markers


def _assert_first_ir_dump_contains(
    case_name: str,
    markers: tuple[str, ...],
    forbidden_markers: tuple[str, ...] = (),
) -> None:
    """校验公开 first-ir dump 的入口与 loop marker。

    功能说明:
    - 读取公开脚本写出的 `kernel/dump/<case_name>/01-first-ir.mlir`。
    - 核对入口 memory/tile/conv attr 与 `symbol.for` step 正反 marker。
    - 防止测试只验证 stdout 或 test-only dump。

    使用示例:
    - `_assert_first_ir_dump_contains("conv2d/inputs_static_tile_dynamic", ("func.func",))`
    """

    first_ir_path = _REPO_ROOT / "kernel" / "dump" / Path(case_name) / "01-first-ir.mlir"
    assert first_ir_path.exists()
    first_ir = first_ir_path.read_text(encoding="utf-8")
    missing_markers = tuple(marker for marker in markers if marker not in first_ir)
    unexpected_markers = tuple(marker for marker in forbidden_markers if marker in first_ir)
    assert first_ir.strip()
    assert not missing_markers
    assert not unexpected_markers


def _conv2d_script_first_ir_markers(
    script: str,
    stdout: str,
) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
    """构造 conv2d 脚本本次随机 profile 对应的 first-ir marker。

    功能说明:
    - static 脚本必须在 first-ir 中出现本次随机 output/input/weight shape。
    - dynamic 脚本必须保留语义符号，且不得把本次随机 shape 静态化。

    使用示例:
    - `_conv2d_script_first_ir_markers("kernel/conv2d/inputs_static_tile_dynamic.py", stdout)`
    """

    shape_seed_match = re.search(r"shape_seed=(\d+)", stdout)
    tile_seed_match = re.search(r"tile_seed=(\d+)", stdout)
    output_match = re.search(r"output=(\([^)]*\))", stdout)
    input_match = re.search(r"input=(\([^)]*\))", stdout)
    weight_match = re.search(r"weight=(\([^)]*\))", stdout)
    stride_match = re.search(r"stride=(\([^)]*\))", stdout)
    dilation_match = re.search(r"dilation=(\([^)]*\))", stdout)
    padding_match = re.search(r"padding=(\([^)]*\))", stdout)
    candidates_match = re.search(r"tile_candidates=([^\n]*?) selected_tile=", stdout)
    tile_match = re.search(r"selected_tile=(\([^)]*\))", stdout)
    assert shape_seed_match is not None
    assert tile_seed_match is not None
    assert output_match is not None
    assert input_match is not None
    assert weight_match is not None
    assert stride_match is not None
    assert dilation_match is not None
    assert padding_match is not None
    assert candidates_match is not None
    assert tile_match is not None
    shape_seed = int(shape_seed_match.group(1))
    tile_seed = int(tile_seed_match.group(1))
    shape_rng = random.Random(shape_seed)
    batch = shape_rng.randint(4, 6)
    in_channels = shape_rng.randint(48, 64)
    input_h = shape_rng.randint(241, 289)
    input_w = shape_rng.randint(225, 273)
    out_channels = shape_rng.randint(18, 24)
    kernel_h = shape_rng.choice((3, 5))
    kernel_w = shape_rng.choice((3, 5))
    padding = tuple(shape_rng.choice((0, 1, 2, 3, 4)) for _ in range(4))
    stride = (8, 8)
    dilation = (1, 1)
    output_h = ((input_h + padding[0] + padding[1] - dilation[0] * (kernel_h - 1) - 1) // stride[0]) + 1
    output_w = ((input_w + padding[2] + padding[3] - dilation[1] * (kernel_w - 1) - 1) // stride[1]) + 1
    expected_candidates = ((8, 16, 4, 8, 9), (7, 18, 3, 9, 8), (6, 20, 2, 10, 7))
    assert tuple(literal_eval(candidates_match.group(1))) == expected_candidates
    tile = random.Random(tile_seed).choice(expected_candidates)
    output_shape = (batch, out_channels, output_h, output_w)
    input_shape = (batch, in_channels, input_h, input_w)
    weight_shape = (out_channels, in_channels, kernel_h, kernel_w)
    assert literal_eval(output_match.group(1)) == output_shape
    assert literal_eval(input_match.group(1)) == input_shape
    assert literal_eval(weight_match.group(1)) == weight_shape
    assert literal_eval(stride_match.group(1)) == stride
    assert literal_eval(dilation_match.group(1)) == dilation
    assert literal_eval(padding_match.group(1)) == padding
    assert literal_eval(tile_match.group(1)) == tile
    assert batch * out_channels * output_h * output_w * in_channels * kernel_h * kernel_w <= 300_000_000
    batch, out_channels, output_h, output_w = output_shape
    _input_batch, in_channels, input_h, input_w = input_shape
    _weight_out, _weight_in, kernel_h, kernel_w = weight_shape
    tile_f, tile_c, tile_n, tile_ho, tile_wo = tile
    assert out_channels > tile_f
    assert in_channels > tile_c
    assert batch > tile_n
    assert output_h > tile_ho
    assert output_w > tile_wo
    assert out_channels % tile_f != 0
    assert in_channels % tile_c != 0
    assert batch % tile_n != 0
    assert output_h % tile_ho != 0
    assert output_w % tile_wo != 0
    if script == "kernel/conv2d/inputs_static_tile_static.py":
        markers = (
            "func.func @conv2d_inputs_static_tile_static_kernel",
            f"!nn.memory<[#C{batch}, #C{out_channels}, #C{output_h}, #C{output_w}]",
            f"!nn.memory<[#C{batch}, #C{in_channels}, #C{input_h}, #C{input_w}]",
            f"!nn.memory<[#C{out_channels}, #C{in_channels}, #C{kernel_h}, #C{kernel_w}]",
            f"!nn.memory<[#C{out_channels}]",
            f"#It1 = #symbol.iter<start = #C0, end = #C{out_channels}, step = #C{tile_f}>",
            f"#It2 = #symbol.iter<start = #C0, end = #C{batch}, step = #C{tile_n}>",
            f"#It3 = #symbol.iter<start = #C0, end = #C{output_h}, step = #C{tile_ho}>",
            f"#It4 = #symbol.iter<start = #C0, end = #C{output_w}, step = #C{tile_wo}>",
            f"#It6 = #symbol.iter<start = #C0, end = #C{in_channels}, step = #C{tile_c}>",
        )
        return (
            (
                "conv2d/inputs_static_tile_static_absent_bias/conv2d_inputs_static_tile_static_kernel",
                markers,
                ("#S_TF", "#S_TC", "#S_TN", "#S_THO", "#S_TWO"),
            ),
            (
                "conv2d/inputs_static_tile_static_present_bias/conv2d_inputs_static_tile_static_kernel",
                markers,
                ("#S_TF", "#S_TC", "#S_TN", "#S_THO", "#S_TWO"),
            ),
        )
    if script == "kernel/conv2d/inputs_static_tile_dynamic.py":
        return (
            (
                "conv2d/inputs_static_tile_dynamic",
                (
                    "func.func @conv2d_inputs_static_tile_dynamic_kernel",
                    f"!nn.memory<[#C{batch}, #C{out_channels}, #C{output_h}, #C{output_w}]",
                    f"!nn.memory<[#C{batch}, #C{in_channels}, #C{input_h}, #C{input_w}]",
                    f"!nn.memory<[#C{out_channels}, #C{in_channels}, #C{kernel_h}, #C{kernel_w}]",
                    f"!nn.memory<[#C{out_channels}]",
                    "!symbol.int<#S_TF>",
                    "!symbol.int<#S_TC>",
                    "!symbol.int<#S_TN>",
                    "!symbol.int<#S_THO>",
                    "!symbol.int<#S_TWO>",
                    f"#It1 = #symbol.iter<start = #C0, end = #C{out_channels}, step = #S_TF>",
                    f"#It2 = #symbol.iter<start = #C0, end = #C{batch}, step = #S_TN>",
                    f"#It3 = #symbol.iter<start = #C0, end = #C{output_h}, step = #S_THO>",
                    f"#It4 = #symbol.iter<start = #C0, end = #C{output_w}, step = #S_TWO>",
                    f"#It6 = #symbol.iter<start = #C0, end = #C{in_channels}, step = #S_TC>",
                ),
                (
                    f"#It1 = #symbol.iter<start = #C0, end = #C{out_channels}, step = #C{tile_f}>",
                    f"#It2 = #symbol.iter<start = #C0, end = #C{batch}, step = #C{tile_n}>",
                    f"#It3 = #symbol.iter<start = #C0, end = #C{output_h}, step = #C{tile_ho}>",
                    f"#It4 = #symbol.iter<start = #C0, end = #C{output_w}, step = #C{tile_wo}>",
                    f"#It6 = #symbol.iter<start = #C0, end = #C{in_channels}, step = #C{tile_c}>",
                ),
            ),
        )
    return (
        (
            "conv2d/inputs_dynamic_tile_dynamic",
            (
                "func.func @conv2d_inputs_dynamic_tile_dynamic_kernel",
                "!nn.memory<[#S_B, #S_C,",
                "!nn.memory<[#S_B, #S_N, #S_XH, #S_XW]",
                "!nn.memory<[#S_C, #S_N, #S_KH, #S_KW]",
                "!nn.memory<[#S_C]",
                "!symbol.int<#S_SH>",
                "!symbol.int<#S_SW>",
                "!symbol.int<#S_DH>",
                "!symbol.int<#S_DW>",
                "!symbol.int<#S_PT>",
                "!symbol.int<#S_PB>",
                "!symbol.int<#S_PL>",
                "!symbol.int<#S_PR>",
                "!symbol.int<#S_TF>",
                "!symbol.int<#S_TC>",
                "!symbol.int<#S_TN>",
                "!symbol.int<#S_THO>",
                "!symbol.int<#S_TWO>",
                "step = #S_TF",
                "step = #S_TN",
                "step = #S_THO",
                "step = #S_TWO",
                "step = #S_TC",
            ),
            (
                f"!nn.memory<[#C{batch}, #C{out_channels}, #C{output_h}, #C{output_w}]",
                f"!nn.memory<[#C{batch}, #C{in_channels}, #C{input_h}, #C{input_w}]",
                f"!nn.memory<[#C{out_channels}, #C{in_channels}, #C{kernel_h}, #C{kernel_w}]",
                f"!nn.memory<[#C{out_channels}]",
            ),
        ),
    )


def _assert_conv2d_first_ir_uses_fixed_upper_bound_scratch(case_name: str) -> None:
    """校验 conv2d 生成侧 first-ir 中可改写 scratch 已用上界形态。

    功能说明:
    - 锁定 accumulator、bias tile、partial staging 三类 scratch 使用 tile 上界分配。
    - 同时锁定 current tile 通过 `dma.view/deslice` 表达，旧 iterator-derived accumulator/bias alloc 不得回归。

    使用示例:
    - `_assert_conv2d_first_ir_uses_fixed_upper_bound_scratch("test_conv2d/inputs_dynamic_tile_dynamic_symbolic_memory")`
    """

    first_ir_path = _REPO_ROOT / "kernel" / "dump" / Path(case_name) / "01-first-ir.mlir"
    assert first_ir_path.exists()
    first_ir = first_ir_path.read_text(encoding="utf-8")
    if "#S_TF" in first_ir:
        assert "#S_TF" in first_ir
        assert "#S_TC" in first_ir
        assert "#S_THO" in first_ir
        assert "#S_TWO" in first_ir
        assert '!nn.memory<[#S_TF], [#C1], f32, #nn.space<tsm>>' in first_ir
        assert '"dma.deslice"' in first_ir
        assert '"dma.view"' in first_ir
        assert '"kernel.matmul"' in first_ir
        return

    assert re.search(r'!nn\.memory<\[#C1, #C7, #C9, #C8\]', first_ir)
    assert '!nn.memory<[#C7], [#C1], f32, #nn.space<tsm>>' in first_ir
    assert re.search(r'!nn\.memory<\[#C1, #S\d+, #S\d+, #S\d+\], \[#C\d+, #C\d+, #C8, #C1\]', first_ir)
    assert '"dma.deslice"' in first_ir
    assert '"dma.view"' in first_ir


def _symbolic_conv2d_compile_args() -> tuple[Conv2dCompileArg, ...]:
    """构造测试用符号 memory 编译参数。


    功能说明:
    - 用 conv2d 语义化符号名表达 output/input/weight memory 的编译期动态形状。
    - output 空间维使用 stride/dilation/padding 的完整符号表达式。
    - 标量参数均使用 runtime `SymbolDim`，锁定公开 scalar real args 合同。

    使用示例:
    - `_symbolic_conv2d_compile_args()`
    """

    xh_dim = SymbolDim("XH")
    xw_dim = SymbolDim("XW")
    kh_dim = SymbolDim("KH")
    kw_dim = SymbolDim("KW")
    sh_dim = SymbolDim("SH")
    sw_dim = SymbolDim("SW")
    dh_dim = SymbolDim("DH")
    dw_dim = SymbolDim("DW")
    pt_dim = SymbolDim("PT")
    pb_dim = SymbolDim("PB")
    pl_dim = SymbolDim("PL")
    pr_dim = SymbolDim("PR")
    tf_dim = SymbolDim("TF")
    tc_dim = SymbolDim("TC")
    tn_dim = SymbolDim("TN")
    tho_dim = SymbolDim("THO")
    two_dim = SymbolDim("TWO")
    output_h_dim = ((xh_dim + pt_dim + pb_dim - dh_dim * (kh_dim - 1) - 1) // sh_dim) + 1
    output_w_dim = ((xw_dim + pl_dim + pr_dim - dw_dim * (kw_dim - 1) - 1) // sw_dim) + 1

    return (
        Memory(["B", "C", output_h_dim, output_w_dim], NumericType.Float32),
        Memory(["B", "N", "XH", "XW"], NumericType.Float32),
        Memory(["C", "N", "KH", "KW"], NumericType.Float32),
        Memory(["C"], NumericType.Float32),
        sh_dim,
        sw_dim,
        dh_dim,
        dw_dim,
        pt_dim,
        pb_dim,
        pl_dim,
        pr_dim,
        tf_dim,
        tc_dim,
        tn_dim,
        tho_dim,
        two_dim,
    )


def _seeded_static_dynamic_conv2d_compile_args() -> tuple[Conv2dCompileArg, ...]:
    """构造 static-dynamic 测试用 本次随机选中 编译参数。


    功能说明:
    - output/input/weight 均使用本计划 static-dynamic seed 随机选出的具体值。
    - static case 将这些 本次随机选中 值具体化到 IR memory type。
    - tile 使用 `TF/TC/TN/THO/TWO` 符号，锁定公开脚本 compile path。
    - 只服务本 pytest 文件，不新增产品公开 API。

    使用示例:
    - `_seeded_static_dynamic_conv2d_compile_args()`
    """

    return (
        Memory([_CONV_SD_B, _CONV_SD_F, _CONV_SD_HO, _CONV_SD_WO], NumericType.Float32),
        Memory([_CONV_SD_B, _CONV_SD_CIN, _CONV_SD_H, _CONV_SD_W], NumericType.Float32),
        Memory([_CONV_SD_F, _CONV_SD_CIN, _CONV_SD_KH, _CONV_SD_KW], NumericType.Float32),
        Memory([_CONV_SD_F], NumericType.Float32),
        SymbolDim("TF"),
        SymbolDim("TC"),
        SymbolDim("TN"),
        SymbolDim("THO"),
        SymbolDim("TWO"),
    )


def _seeded_static_static_conv2d_compile_args() -> tuple[Memory, Memory, Memory, Memory]:
    """构造 static-static 测试用 本次随机选中 static memory 编译参数。


    功能说明:
    - output/input/weight 均使用本计划 static-static seed 随机选出的具体值。
    - static case 将这些 本次随机选中 值具体化到 IR memory type。
    - tile 从 demo 文件内 per-run random 候选集合选择，不作为编译参数传入。

    使用示例:
    - `_seeded_static_static_conv2d_compile_args()`
    """

    return (
        Memory([_CONV_SS_B, _CONV_SS_F, _CONV_SS_HO, _CONV_SS_WO], NumericType.Float32),
        Memory([_CONV_SS_B, _CONV_SS_CIN, _CONV_SS_H, _CONV_SS_W], NumericType.Float32),
        Memory([_CONV_SS_F, _CONV_SS_CIN, _CONV_SS_KH, _CONV_SS_KW], NumericType.Float32),
        Memory([_CONV_SS_F], NumericType.Float32),
    )


# TC-KERNEL-CONV2D-SYMBOLIC-MEMORY-001
# 功能说明: 验证动态输入 demo 的 gen_kernel 编译参数使用语义化符号 Memory shape。
# 测试目的: 锁定 lowered IR/source 不回退为旧 s1/s2 匿名 shape 或 runtime 本次随机选中 具体 shape，确保 demo 名称中的 dynamic 真实体现在编译形态。
# 使用示例: pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -k symbolic_memory
# 对应功能实现文件路径: kernel/conv2d/inputs_dynamic_tile_dynamic.py
# 对应 spec 文件路径: spec/kernel/runner.md
# 对应测试文件路径: test/kernel/test_conv2d_symbolic_memory_genkernel.py
def test_inputs_dynamic_tile_dynamic_gen_kernel_keeps_symbolic_memory_shapes() -> None:
    module, source = run_lowering_demo(
        "test_conv2d/inputs_dynamic_tile_dynamic_symbolic_memory",
        conv2d_inputs_dynamic_tile_dynamic_kernel,
        *_symbolic_conv2d_compile_args(),
    )
    module_text = str(module)

    _assert_conv2d_source_uses_kernel_out_first(conv2d_inputs_dynamic_tile_dynamic_kernel)
    _assert_conv2d_first_ir_uses_fixed_upper_bound_scratch("test_conv2d/inputs_dynamic_tile_dynamic_symbolic_memory")
    assert SEMANTIC_OUTPUT_PREFIX in module_text
    assert SEMANTIC_INPUT_MEMORY in module_text
    assert SEMANTIC_WEIGHT_MEMORY in module_text
    assert SEMANTIC_BIAS_MEMORY in module_text
    for symbol_name in SEMANTIC_RUNTIME_SYMBOLS:
        assert symbol_name in module_text
    assert "arch.get_dynamic_memory" in module_text
    assert "dma.view" in module_text
    assert "dma.subview" not in module_text
    assert "dma.alloc" not in module_text
    assert "allalloc" not in module_text
    assert "memory.get_data" in module_text
    assert "symbol.ne" in module_text
    assert "!nn.memory<[#symbol.expr<s1>, #symbol.expr<s2>, #symbol.expr<s3>, #symbol.expr<s4>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>, #symbol.expr<s5>, #symbol.expr<s6>, #symbol.expr<s7>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s2>, #symbol.expr<s5>, #symbol.expr<3>, #symbol.expr<3>]" not in module_text
    assert "!nn.memory<[#symbol.expr<11>, #symbol.expr<4>, #symbol.expr<258>, #symbol.expr<262>]" not in module_text
    assert "!nn.memory<[#symbol.expr<11>, #symbol.expr<30>, #symbol.expr<260>, #symbol.expr<264>]" not in module_text
    assert "!nn.memory<[#symbol.expr<4>, #symbol.expr<30>, #symbol.expr<3>, #symbol.expr<3>]" not in module_text
    assert "arg1.get_shape(2)" in source
    assert "arg1.get_shape(3)" in source
    assert "npu_demo::get_dynamic_memory<TSM>()" in source
    assert ".template view<" in source
    assert "slice(" in source
    assert "alloc<TSM" not in source
    assert "S_INT c_6 = 258" not in source


# TC-KERNEL-CONV2D-SYMBOLIC-MEMORY-002
# 功能说明: 验证静态输入、动态 tile demo 的 lowered IR 保持 本次随机选中 static shape。
# 测试目的: 锁定 static demo 不回退为默认 12/32/256/256 形状，也不误变为 dynamic 符号 shape。
# 使用示例: pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -k static_tile_dynamic
# 对应功能实现文件路径: kernel/conv2d/inputs_static_tile_dynamic.py
# 对应 spec 文件路径: spec/kernel/runner.md
# 对应测试文件路径: test/kernel/test_conv2d_symbolic_memory_genkernel.py
def test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes() -> None:
    module, _source = run_lowering_demo(
        "test_conv2d/inputs_static_tile_dynamic_seeded_static_memory",
        conv2d_inputs_static_tile_dynamic_kernel,
        *_seeded_static_dynamic_conv2d_compile_args(),
    )
    module_text = str(module)

    _assert_conv2d_source_uses_kernel_out_first(conv2d_inputs_static_tile_dynamic_kernel)
    _assert_conv2d_first_ir_uses_fixed_upper_bound_scratch("test_conv2d/inputs_static_tile_dynamic_seeded_static_memory")
    assert STATIC_DYNAMIC_OUTPUT_MEMORY in module_text
    assert STATIC_DYNAMIC_INPUT_MEMORY in module_text
    assert STATIC_DYNAMIC_WEIGHT_MEMORY in module_text
    assert STATIC_DYNAMIC_BIAS_MEMORY in module_text
    assert "!symbol.int<#symbol.expr<TF>>" in module_text
    assert "!symbol.int<#symbol.expr<TC>>" in module_text
    assert "!symbol.int<#symbol.expr<TN>>" in module_text
    assert "!symbol.int<#symbol.expr<THO>>" in module_text
    assert "!symbol.int<#symbol.expr<TWO>>" in module_text
    assert "!nn.memory<[#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<254>, #symbol.expr<254>]" not in module_text
    assert "!nn.memory<[#symbol.expr<12>, #symbol.expr<32>, #symbol.expr<256>, #symbol.expr<256>]" not in module_text
    assert "!nn.memory<[#symbol.expr<4>, #symbol.expr<32>, #symbol.expr<3>, #symbol.expr<3>]" not in module_text
    assert SEMANTIC_OUTPUT_MEMORY not in module_text
    assert SEMANTIC_INPUT_MEMORY not in module_text
    assert SEMANTIC_WEIGHT_MEMORY not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    assert "memory.get_data" in module_text
    assert "symbol.ne" in module_text


def test_inputs_static_tile_static_uses_seeded_tile_constants() -> None:
    """static-static demo 应使用 seed 选择的静态 tile 常量。

    功能说明:
    - 读取公开 demo 函数源码，确认 tile 来自模块级 seed 选择常量。
    - 防止 static-static demo 回退到旧硬编码 tile 组合。

    使用示例:
    - `pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -k seeded_tile_constants`
    """

    function_source = inspect.getsource(conv2d_inputs_static_tile_static_kernel)
    assert "tile_f = _STATIC_TILE_F" in function_source
    assert "tile_c = _STATIC_TILE_C" in function_source
    assert "tile_n = _STATIC_TILE_N" in function_source
    assert "tile_ho = _STATIC_TILE_HO" in function_source
    assert "tile_wo = _STATIC_TILE_WO" in function_source
    assert "tile_f = 8" not in function_source
    assert "tile_c = 16" not in function_source


# TC-KERNEL-CONV2D-SYMBOLIC-MEMORY-003
# 功能说明: 验证静态输入、静态 tile demo 的 lowered IR 保持 本次随机选中 static shape。
# 测试目的: 锁定 static demo 不回退为默认 12/32/256/256 形状，也不误变为 dynamic 符号 shape。
# 使用示例: pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -k static_tile_static
# 对应功能实现文件路径: kernel/conv2d/inputs_static_tile_static.py
# 对应 spec 文件路径: spec/kernel/runner.md
# 对应测试文件路径: test/kernel/test_conv2d_symbolic_memory_genkernel.py
def test_inputs_static_tile_static_gen_kernel_keeps_seeded_static_shapes() -> None:
    module, source = run_lowering_demo(
        "test_conv2d/inputs_static_tile_static_seeded_static_memory",
        conv2d_inputs_static_tile_static_kernel,
        *_seeded_static_static_conv2d_compile_args(),
    )
    module_text = str(module)

    _assert_conv2d_source_uses_kernel_out_first(conv2d_inputs_static_tile_static_kernel)
    _assert_conv2d_first_ir_uses_fixed_upper_bound_scratch("test_conv2d/inputs_static_tile_static_seeded_static_memory")
    assert STATIC_STATIC_OUTPUT_MEMORY in module_text
    assert STATIC_STATIC_INPUT_MEMORY in module_text
    assert STATIC_STATIC_WEIGHT_MEMORY in module_text
    assert STATIC_STATIC_BIAS_MEMORY in module_text
    assert "!nn.memory<[#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<254>, #symbol.expr<254>]" not in module_text
    assert "!nn.memory<[#symbol.expr<12>, #symbol.expr<32>, #symbol.expr<256>, #symbol.expr<256>]" not in module_text
    assert "!nn.memory<[#symbol.expr<4>, #symbol.expr<32>, #symbol.expr<3>, #symbol.expr<3>]" not in module_text
    assert SEMANTIC_OUTPUT_MEMORY not in module_text
    assert SEMANTIC_INPUT_MEMORY not in module_text
    assert SEMANTIC_WEIGHT_MEMORY not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    assert "memory.get_data" in module_text
    assert "symbol.ne" in module_text
    assert "? -" not in module_text
    assert "? -" not in source


def test_conv2d_target_scripts_execute_and_report_random_profile() -> None:
    """三条 conv2d 脚本都应通过公开脚本入口并报告本次随机 profile。

    功能说明:
    - 通过公开脚本入口验证 static/dynamic demo，而不是直连私有 helper。
    - 独立重算 本次随机选中 shape、padding、tile，并核对 stdout 与 source dump marker。

    使用示例:
    - `pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -k target_scripts`
    """

    scripts = {
        "kernel/conv2d/inputs_static_tile_static.py": (
            "profile=per-run-random",
            "static_ir=random-concrete",
        ),
        "kernel/conv2d/inputs_static_tile_dynamic.py": (
            "profile=per-run-random",
            "static_memory=random-concrete",
            "dynamic_tile=symbolic-runtime",
        ),
        "kernel/conv2d/inputs_dynamic_tile_dynamic.py": (
            "profile=per-run-random",
            "dynamic_ir=symbolic",
            "runtime=random",
        ),
    }
    source_markers = {
        "kernel/conv2d/inputs_static_tile_static.py": (
            (
                "conv2d/inputs_static_tile_static_absent_bias",
                ("conv2d_inputs_static_tile_static_kernel", "npu_demo::launch", "img2col2d<", "matmul<"),
            ),
            (
                "conv2d/inputs_static_tile_static_present_bias",
                ("conv2d_inputs_static_tile_static_kernel", "npu_demo::launch", "img2col2d<", "matmul<"),
            ),
        ),
        "kernel/conv2d/inputs_static_tile_dynamic.py": (
            (
                "conv2d/inputs_static_tile_dynamic",
                ("conv2d_inputs_static_tile_dynamic_kernel", "npu_demo::launch"),
            ),
        ),
        "kernel/conv2d/inputs_dynamic_tile_dynamic.py": (
            (
                "conv2d/inputs_dynamic_tile_dynamic",
                ("conv2d_inputs_dynamic_tile_dynamic_kernel", "npu_demo::launch"),
            ),
        ),
    }
    for script, expected_markers in scripts.items():
        completed = _run_kernel_script(script)
        assert "[CHECK] conv2d/" in completed.stdout
        assert "absent_bias max_abs_diff=" in completed.stdout
        assert "present_bias max_abs_diff=" in completed.stdout
        assert "shape_seed=" in completed.stdout
        assert "tile_seed=" in completed.stdout
        assert "tile_candidates=" in completed.stdout
        assert "bias_case_order=" in completed.stdout
        for marker in expected_markers:
            assert marker in completed.stdout
        for case_name, markers in source_markers[script]:
            _assert_source_dump_contains(case_name, markers)
        for case_name, markers, forbidden_markers in _conv2d_script_first_ir_markers(script, completed.stdout):
            _assert_first_ir_dump_contains(case_name, markers, forbidden_markers)
