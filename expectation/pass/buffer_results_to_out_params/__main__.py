"""`buffer_results_to_out_params` 目录级 expectation 入口。

创建者: 守护最好的爱莉希雅
最后一次更改: 小李飞刀

功能说明:
- 作为 `buffer_results_to_out_params` expectation 的目录级入口，顺序运行 single /
  mixed / multi / reject 四组合同。
- 目录位置固定在 `expectation/pass/` 下，不再挂在 `expectation/pass/lowing/`。

使用示例:
- `PYTHONPATH=. python -m expectation.pass.buffer_results_to_out_params`

关联文件:
- spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../expectation/pass/buffer_results_to_out_params/__main__.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/single_output.py`](../../../expectation/pass/buffer_results_to_out_params/single_output.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/mixed_output.py`](../../../expectation/pass/buffer_results_to_out_params/mixed_output.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/multi_output.py`](../../../expectation/pass/buffer_results_to_out_params/multi_output.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/reject_cases.py`](../../../expectation/pass/buffer_results_to_out_params/reject_cases.py)
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Callable

_CANONICAL_CASE_MODULES = {
    "mixed_output": "expectation.pass.buffer_results_to_out_params.mixed_output",
    "multi_output": "expectation.pass.buffer_results_to_out_params.multi_output",
    "reject_cases": "expectation.pass.buffer_results_to_out_params.reject_cases",
    "single_output": "expectation.pass.buffer_results_to_out_params.single_output",
}


def _install_lowering_buffer_results_compat_alias() -> None:
    """为 immutable `reject_cases.py` 安装局部 lowering shim alias。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - `reject_cases.py` 仍通过旧模块名 `kernel_gen.passes.lowering.buffer_results_to_out_params`
      导入 pass；该文件是 `[immutable-file]`，不能直接改。
    - 当前 helper 仅在目录级 expectation 入口内，向 `sys.modules` 注入一个指向 canonical
      `kernel_gen.passes.buffer_results_to_out_params` 的局部 alias。
    - 该 alias 不改变仓库公开 pytest 对旧 lowering shim 的失败边界，只服务于本目录入口的
      contract runner。

    使用示例:
    - `_install_lowering_buffer_results_compat_alias()`

    关联文件:
    - spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
    - test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
    - 功能实现: [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../expectation/pass/buffer_results_to_out_params/__main__.py)
    - 功能实现: [`kernel_gen/passes/buffer_results_to_out_params.py`](../../../kernel_gen/passes/buffer_results_to_out_params.py)
    """

    legacy_name = "kernel_gen.passes.lowering.buffer_results_to_out_params"
    if legacy_name in sys.modules:
        return
    canonical = importlib.import_module("kernel_gen.passes.buffer_results_to_out_params")
    alias = ModuleType(legacy_name)
    alias.BufferResultsToOutParamsPass = canonical.BufferResultsToOutParamsPass
    alias.BufferResultsToOutParamsError = canonical.BufferResultsToOutParamsError
    sys.modules[legacy_name] = alias


_install_lowering_buffer_results_compat_alias()


def _load_case_main(case_module: str) -> Callable[[], None]:
    """加载单个 buffer-results-to-out-params case 的入口函数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 包上下文存在时，优先使用相对导入加载当前目录下的 case 模块。
    - 只有当前入口没有包上下文，或目标 case 模块本身缺失时，才退回 canonical package import。
    - 保持 `reject_cases.py` 依赖的 lowering shim alias 已提前安装，不在这里额外改导入路径。

    使用示例:
    - `single_output_main = _load_case_main("single_output")`

    关联文件:
    - spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
    - test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
    - 功能实现: [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../expectation/pass/buffer_results_to_out_params/__main__.py)
    """

    canonical_module_name = _CANONICAL_CASE_MODULES[case_module]
    if not __package__:
        return importlib.import_module(canonical_module_name).main

    try:
        module = importlib.import_module(f".{case_module}", __package__)
    except ModuleNotFoundError as exc:
        if exc.name not in {case_module, canonical_module_name}:
            raise
        module = importlib.import_module(canonical_module_name)

    return module.main


mixed_output_main = _load_case_main("mixed_output")
multi_output_main = _load_case_main("multi_output")
reject_cases_main = _load_case_main("reject_cases")
single_output_main = _load_case_main("single_output")


def main() -> None:
    """运行 buffer_results_to_out_params 目录级 expectation。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 小李飞刀

    功能说明:
    - 依次执行 single、mixed、multi、reject 四组 case。
    - 当前入口优先使用包内相对导入，不再依赖当前目录写入 `sys.path`。
    - 局部 lowering shim alias 只服务于 immutable `reject_cases.py` 的旧导入口径。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
    - test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
    - 功能实现: [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../expectation/pass/buffer_results_to_out_params/__main__.py)
    """

    print("[SUITE] buffer_results_to_out_params")
    single_output_main()
    mixed_output_main()
    multi_output_main()
    reject_cases_main()


if __name__ == "__main__":
    main()
