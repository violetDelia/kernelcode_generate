"""Third-party generic backend expectation cases."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, Region

from kernel_gen.core.config import reset_config, set_dump_dir, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c, gen_kernel
from kernel_gen.execute_engine import ExecutionEngine
from kernel_gen.target.registry import TargetSpec, register_target


def register_dummy_target() -> None:
    """Register the dummy generic target for expectation cases."""

    try:
        register_target(TargetSpec("dummy_generic", None, set(), {}))
    except ValueError:
        pass


def module_with_func(func_name: str) -> ModuleOp:
    """Build a minimal module containing one empty function."""

    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp(func_name, ([], []), Region(block))
    return ModuleOp([func_op])


def case_module_auto_load_source_bundle() -> None:
    """Verify auto-load and SourceBundle output for ModuleOp emit."""

    reset_config()
    register_dummy_target()
    set_target("dummy_generic")

    source = emit_c(module_with_func("dummy_bundle"), EmitCContext())

    assert source.startswith("// __KG_BUNDLE_FILE__:kernel.cpp")
    assert "// __KG_BUNDLE_FILE__:include/kernel.h" in source
    assert "void dummy_bundle() {}" in source


def case_gen_kernel_dump_expands_source_bundle() -> None:
    """Verify gen_kernel writes aggregate source and artifacts."""

    reset_config()
    register_dummy_target()
    set_target("dummy_generic")
    with TemporaryDirectory() as tmp:
        dump_dir = Path(tmp)
        set_dump_dir(dump_dir)

        source = gen_kernel(module_with_func("dummy_bundle"), EmitCContext())

        assert (dump_dir / "source.cpp").read_text(encoding="utf-8") == source
        assert (dump_dir / "kernel.cpp").read_text(encoding="utf-8") == "void dummy_bundle() {}\n"
        assert (dump_dir / "include" / "kernel.h").read_text(encoding="utf-8") == "#pragma once\n"


def case_compile_only_execute_fails_stably() -> None:
    """Verify dummy compile strategy returns execution_unsupported on execute."""

    reset_config()
    register_dummy_target()
    set_target("dummy_generic")
    source = gen_kernel(module_with_func("dummy_single"), EmitCContext())

    kernel = ExecutionEngine(target="dummy_generic").compile(source=source, function="dummy_single")

    try:
        kernel.execute(args=())
    except KernelCodeError as exc:
        assert exc.failure_phrase == "execution_unsupported"
        return
    raise AssertionError("dummy_generic execute must fail with execution_unsupported")


def run() -> None:
    """Run all third-party generic backend expectation cases."""

    case_module_auto_load_source_bundle()
    case_gen_kernel_dump_expands_source_bundle()
    case_compile_only_execute_fails_stably()
