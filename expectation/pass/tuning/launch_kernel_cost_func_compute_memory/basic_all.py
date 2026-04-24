"""launch-kernel-cost-func compute/memory expectation。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 使用 `ircheck` 锁定 `launch-kernel-cost-func` 在 `compute / memory` 两种公开 kind 下的最小合同。
- 目录资产只覆盖当前计划的 canonical 两 kind，不再接线历史四 kind expectation。
- 验证生成的 cost function 名称与 `tuner.cost.cost_kind` 均与输入选项一致。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory.basic_all`

关联文件:
- spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [`test/pass/test_launch_kernel_cost_func.py`](test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)
- 功能实现: [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from __future__ import annotations

from importlib import import_module

_CANONICAL_SHARED_MODULE = "expectation.pass.tuning.launch_kernel_cost_func._shared"


def _load_runner_shared_module() -> object:
    """加载 compute/memory expectation 依赖的 `_shared` 模块。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 包上下文存在时，优先通过相对导入加载 `..launch_kernel_cost_func._shared`。
    - 只有当前模块没有包上下文，或目标 `_shared` 模块本身缺失时，才 fallback 到 canonical import。
    - 不吞掉 `_shared.py` 内部真实依赖错误，避免把实现问题误判成 runner 边界问题。

    使用示例:
    - `shared_module = _load_runner_shared_module()`

    关联文件:
    - spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](expectation/pass/tuning/launch_kernel_cost_func/_shared.py)
    """

    if not __package__:
        return import_module(_CANONICAL_SHARED_MODULE)

    try:
        return import_module("..launch_kernel_cost_func._shared", __package__)
    except ModuleNotFoundError as exc:
        missing_module_names = {
            "launch_kernel_cost_func",
            "expectation.pass.tuning.launch_kernel_cost_func",
            _CANONICAL_SHARED_MODULE,
        }
        if exc.name not in missing_module_names:
            raise
        return import_module(_CANONICAL_SHARED_MODULE)


_shared = _load_runner_shared_module()
raise_if_failures = _shared.raise_if_failures
run_case = _shared.run_case
run_ircheck_success = _shared.run_ircheck_success

MEM_TYPE = "!nn.memory<[4], [1], f32, #nn.space<global>>"
INPUT_IR = f"""
builtin.module {{
  func.func @wrapper(%0 : {MEM_TYPE}, %1 : {MEM_TYPE}, %2 : {MEM_TYPE}) {{
    %3 = symbol.const 1 : !symbol.int<"1">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 0 : !symbol.int<"0">
    arch.launch<%3, %4, %5, %6>(@_device_kernel, %0, %1, %2) : ({MEM_TYPE}, {MEM_TYPE}, {MEM_TYPE}) -> ()
    func.return
  }}
  func.func @_device_kernel(%0 : {MEM_TYPE}, %1 : {MEM_TYPE}, %2 : {MEM_TYPE}) {{
    "kernel.add"(%0, %1, %2) {{space = #nn.space<global>}} : ({MEM_TYPE}, {MEM_TYPE}, {MEM_TYPE}) -> ()
    func.return
  }}
}}
""".strip()

CASE_TEXT_COMPUTE = (
    """// COMPILE_ARGS: --pass "launch-kernel-cost-func={cost_kind=compute}"
// CHECK: func.func @_cost_compute__device_kernel(
// CHECK: = tuner.cost(%{{.*}}, %{{.*}}, %{{.*}}) {space = #nn.space<global>, cost_kind = "compute", op_name = "kernel.add"} : (!nn.memory<[4], [1], f32, #nn.space<global>>, !nn.memory<[4], [1], f32, #nn.space<global>>, !nn.memory<[4], [1], f32, #nn.space<global>>) -> !symbol.int<{{.*}}>
// CHECK: func.return %{{.*}} : !symbol.int<{{.*}}>
"""
    + INPUT_IR
)

CASE_TEXT_MEMORY = (
    """// COMPILE_ARGS: --pass "launch-kernel-cost-func={cost_kind=memory}"
// CHECK: func.func @_cost_memory__device_kernel(
// CHECK: = tuner.cost(%{{.*}}, %{{.*}}, %{{.*}}) {space = #nn.space<global>, cost_kind = "memory", op_name = "kernel.add"} : (!nn.memory<[4], [1], f32, #nn.space<global>>, !nn.memory<[4], [1], f32, #nn.space<global>>, !nn.memory<[4], [1], f32, #nn.space<global>>) -> !symbol.int<{{.*}}>
// CHECK: func.return %{{.*}} : !symbol.int<{{.*}}>
"""
    + INPUT_IR
)


def main() -> None:
    """运行 compute/memory 两条最小成功 expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 `cost_kind=compute` 会生成 `_cost_compute__device_kernel`。
    - 校验 `cost_kind=memory` 会生成 `_cost_memory__device_kernel`。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "CASE-1-COMPUTE",
        lambda: run_ircheck_success(
            CASE_TEXT_COMPUTE,
            source_path="expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py#compute",
        ),
    )
    run_case(
        failures,
        "CASE-2-MEMORY",
        lambda: run_ircheck_success(
            CASE_TEXT_MEMORY,
            source_path="expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py#memory",
        ),
    )
    raise_if_failures("launch-kernel-cost-func compute/memory expectation", failures)


if __name__ == "__main__":
    main()
