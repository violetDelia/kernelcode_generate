"""DSL AST visitor.


功能说明:
- 定义 `DslAstVisitor`，把 Python `ast` 树转换为项目 DSL AST。
- helper call 先解析到实际 operation 对象，再通过 `kernel_gen.dsl.ast.plugin.lookup_builtin(...)` 注册表识别。
- 赋值名称绑定只消费右侧 `ValueAST.binding_value()` / `bind_target(...)`，不在 visitor 中维护节点级结果推导。
- `for` 循环变量的解析期 symbol 语义标记为 `?`，避免后续 shape/size 推导把迭代 SSA 名称拼入公开表达。

API 列表:
- `DslAstVisitor(fn: DslCallable, runtime_args: tuple[DslRuntimeArg, ...] = ())`
- `DslAstVisitor.runtime_arg_key(value: DslVisitValue) -> RuntimeArgKey`
- `DslAstVisitor.parse_python_callee(callee: DslCallable, args: tuple[DSLNode, ...], location: SourceLocation | None) -> FunctionAST`
- `DslAstVisitor.build_python_callee_call(callee: DslCallable, args: list[DSLNode], kwargs: dict[str, DSLNode], location: SourceLocation | None) -> CallAST`
- `DslAstVisitor.visit(node: ast.AST) -> DSLNode | None`
- `DslAstVisitor.visit_Module(node: ast.Module) -> ModuleAST`
- `DslAstVisitor.visit_FunctionDef(node: ast.FunctionDef) -> FunctionAST`
- `DslAstVisitor.visit_Import(node: ast.Import) -> None`
- `DslAstVisitor.visit_ImportFrom(node: ast.ImportFrom) -> None`
- `DslAstVisitor.visit_Assign(node: ast.Assign) -> DSLNode | None`
- `DslAstVisitor.visit_AugAssign(node: ast.AugAssign) -> DSLNode | None`
- `DslAstVisitor.visit_For(node: ast.For) -> ForAST | None`
- `DslAstVisitor.visit_If(node: ast.If) -> IfAST`
- `DslAstVisitor.visit_Return(node: ast.Return) -> ReturnAST | StatementAST`
- `DslAstVisitor.visit_Expr(node: ast.Expr) -> DSLNode | None`
- `DslAstVisitor.visit_BinOp(node: ast.BinOp) -> ValueAST`
- `DslAstVisitor.visit_Compare(node: ast.Compare) -> ValueAST`
- `DslAstVisitor.visit_Call(node: ast.Call) -> DSLNode`
- `DslAstVisitor.visit_List(node: ast.List) -> SymbolListAST | TupleAST`
- `DslAstVisitor.visit_Tuple(node: ast.Tuple) -> TupleAST`
- `DslAstVisitor.visit_keyword(node: ast.keyword) -> TupleAST`
- `DslAstVisitor.visit_Name(node: ast.Name) -> DSLNode`
- `DslAstVisitor.visit_Constant(node: ast.Constant) -> ConstValueAST | BoolValueAST`
- `DslAstVisitor.visit_Subscript(node: ast.Subscript) -> DSLNode`
- `DslAstVisitor.visit_UnaryOp(node: ast.UnaryOp) -> ConstValueAST`
- `DslAstVisitor.visit_Attribute(node: ast.Attribute) -> DSLNode`

使用示例:
- visitor = DslAstVisitor(kernel, (lhs, rhs))
- module_ast = visitor.visit(parsed_python_ast)

关联文件:
- spec: spec/dsl/ast/dsl_ast.md
- test: test/dsl/ast/test_parser.py
- 功能实现: kernel_gen/dsl/ast/dsl_ast.py
"""

from __future__ import annotations

import ast as py_ast
import inspect
import textwrap
from collections.abc import Callable
from typing import TypeAlias

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dsl.ast.nodes import (
    BlockAST,
    BoolValueAST,
    BoundExprAST,
    CallAST,
    ConstValueAST,
    Diagnostic,
    DSLNode,
    DmaLoadAST,
    ForAST,
    FunctionAST,
    IfAST,
    MemoryAST,
    MemorySpaceAttrAST,
    ModuleAST,
    NnAddAST,
    NnEqAST,
    NnFloorDivAST,
    NnGeAST,
    NnGtAST,
    NnLeAST,
    NnLtAST,
    NnMulAST,
    NnNeAST,
    NnSubAST,
    NnTrueDivAST,
    PythonObjectAttrAST,
    ReturnAST,
    SourceLocation,
    StatementAST,
    SymbolAddAST,
    SymbolDimAST,
    SymbolEqAST,
    SymbolFloorDivAST,
    SymbolGeAST,
    SymbolGtAST,
    SymbolLeAST,
    SymbolListAST,
    SymbolLtAST,
    SymbolMaxAST,
    SymbolMinAST,
    SymbolMulAST,
    SymbolNeAST,
    SymbolSubAST,
    SymbolToFloatAST,
    SymbolTrueDivAST,
    TensorAxisAccessAST,
    TupleAST,
    ValueAST,
)
from kernel_gen.dsl.ast.plugin import BuiltinCall, lookup_builtin
from kernel_gen.operation import arch as _operation_arch
from kernel_gen.operation import dma as _operation_dma
from kernel_gen.operation import kernel as _operation_kernel
from kernel_gen.operation import nn as _operation_nn
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility
from kernel_gen.operation.kernel import KernelBinaryElewiseKind
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

DslRuntimeArg: TypeAlias = "Memory | SymbolDim | int | float | bool | str"
DslCallable: TypeAlias = "Callable[..., DslVisitValue | None]"
DslVisitValue: TypeAlias = (
    "DSLNode | Memory | MemorySpace | NumericType | BarrierVisibility | BarrierScope | "
    "DslCallable | DslRuntimeArg | list[DslVisitValue] | tuple[DslVisitValue, ...] | None"
)
RuntimeArgKey: TypeAlias = "tuple[str, str | tuple[str, ...]]"

_DEFAULT_DSL_HELPERS: dict[str, DslCallable] = {
    "alloc": _operation_dma.alloc,
    "copy": _operation_dma.copy,
    "cast": _operation_dma.cast,
    "view": _operation_dma.view,
    "reshape": _operation_dma.reshape,
    "flatten": _operation_dma.flatten,
    "free": _operation_dma.free,
    "fill": _operation_dma.fill,
    "load": _operation_dma.load,
    "slice": _operation_dma.slice,
    "store": _operation_dma.store,
    "deslice": _operation_dma.deslice,
    "add": _operation_nn.add,
    "sub": _operation_nn.sub,
    "mul": _operation_nn.mul,
    "truediv": _operation_nn.truediv,
    "floordiv": _operation_nn.floordiv,
    "eq": _operation_nn.eq,
    "ne": _operation_nn.ne,
    "lt": _operation_nn.lt,
    "le": _operation_nn.le,
    "gt": _operation_nn.gt,
    "ge": _operation_nn.ge,
    "relu": _operation_nn.relu,
    "leaky_relu": _operation_nn.leaky_relu,
    "sigmoid": _operation_nn.sigmoid,
    "tanh": _operation_nn.tanh,
    "hard_sigmoid": _operation_nn.hard_sigmoid,
    "exp": _operation_nn.exp,
    "reduce_sum": _operation_nn.reduce_sum,
    "reduce_min": _operation_nn.reduce_min,
    "reduce_max": _operation_nn.reduce_max,
    "softmax": _operation_nn.softmax,
    "broadcast": _operation_nn.broadcast,
    "broadcast_to": _operation_nn.broadcast_to,
    "transpose": _operation_nn.transpose,
    "matmul": _operation_nn.matmul,
    "fc": _operation_nn.fc,
    "conv": _operation_nn.conv,
    "img2col1d": _operation_nn.img2col1d,
    "img2col2d": _operation_nn.img2col2d,
    "get_dynamic_memory": _operation_arch.get_dynamic_memory,
    "barrier": _operation_arch.barrier,
    "launch_kernel": _operation_arch.launch_kernel,
    "get_block_id": _operation_arch.get_block_id,
    "get_block_num": _operation_arch.get_block_num,
    "get_subthread_id": _operation_arch.get_subthread_id,
    "get_subthread_num": _operation_arch.get_subthread_num,
    "get_thread_id": _operation_arch.get_thread_id,
    "get_thread_num": _operation_arch.get_thread_num,
}

_IMPORTABLE_DSL_HELPER_MODULES: dict[str, dict[str, DslCallable]] = {
    "kernel_gen.operation.dma": {
        name: value
        for name, value in _DEFAULT_DSL_HELPERS.items()
        if value in {
            _operation_dma.alloc,
            _operation_dma.copy,
            _operation_dma.cast,
            _operation_dma.view,
            _operation_dma.reshape,
            _operation_dma.flatten,
            _operation_dma.free,
            _operation_dma.fill,
            _operation_dma.load,
            _operation_dma.slice,
            _operation_dma.store,
            _operation_dma.deslice,
        }
    },
    "kernel_gen.operation.nn": {
        name: value
        for name, value in _DEFAULT_DSL_HELPERS.items()
        if value in {
            _operation_nn.add,
            _operation_nn.sub,
            _operation_nn.mul,
            _operation_nn.truediv,
            _operation_nn.floordiv,
            _operation_nn.eq,
            _operation_nn.ne,
            _operation_nn.lt,
            _operation_nn.le,
            _operation_nn.gt,
            _operation_nn.ge,
            _operation_nn.relu,
            _operation_nn.leaky_relu,
            _operation_nn.sigmoid,
            _operation_nn.tanh,
            _operation_nn.hard_sigmoid,
            _operation_nn.exp,
            _operation_nn.reduce_sum,
            _operation_nn.reduce_min,
            _operation_nn.reduce_max,
            _operation_nn.softmax,
            _operation_nn.broadcast,
            _operation_nn.broadcast_to,
            _operation_nn.transpose,
            _operation_nn.matmul,
            _operation_nn.fc,
            _operation_nn.conv,
            _operation_nn.img2col1d,
            _operation_nn.img2col2d,
        }
    },
    "kernel_gen.operation.kernel": {
        name: value
        for name, value in {
            "binary_elewise": _operation_kernel.binary_elewise,
            "add": _operation_kernel.add,
            "sub": _operation_kernel.sub,
            "mul": _operation_kernel.mul,
            "div": _operation_kernel.div,
            "truediv": _operation_kernel.truediv,
            "eq": _operation_kernel.eq,
            "ne": _operation_kernel.ne,
            "lt": _operation_kernel.lt,
            "le": _operation_kernel.le,
            "gt": _operation_kernel.gt,
            "ge": _operation_kernel.ge,
            "matmul": _operation_kernel.matmul,
            "img2col1d": _operation_kernel.img2col1d,
            "img2col2d": _operation_kernel.img2col2d,
        }.items()
    },
    "kernel_gen.operation.arch": {
        name: value
        for name, value in _DEFAULT_DSL_HELPERS.items()
        if value in {
            _operation_arch.get_dynamic_memory,
            _operation_arch.barrier,
            _operation_arch.launch_kernel,
            _operation_arch.get_block_id,
            _operation_arch.get_block_num,
            _operation_arch.get_subthread_id,
            _operation_arch.get_subthread_num,
            _operation_arch.get_thread_id,
            _operation_arch.get_thread_num,
        }
    },
}


class DslAstVisitor(py_ast.NodeVisitor):
    """Python AST 到 DSL AST 的公开 visitor。


    功能说明:
    - 保存待解析函数、运行时参数、可解析全局符号和当前词法作用域。
    - 通过 `visit_*` 方法把 Python AST 节点转换为 `ModuleAST`、`FunctionAST` 与表达式节点。

    使用示例:
    - module_ast = DslAstVisitor(kernel, (lhs, rhs)).visit(tree)

    关联文件:
    - spec: spec/dsl/ast/dsl_ast.md
    - test: test/dsl/ast/test_parser.py
    - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
    """

    def __init__(self, fn: DslCallable, runtime_args: tuple[DslRuntimeArg, ...] = ()) -> None:
        """初始化 DSL AST visitor。


        功能说明:
        - 捕获函数 globals、closure nonlocals 与 runtime args，供后续表达式解析使用。

        使用示例:
        - visitor = DslAstVisitor(kernel, (lhs,))

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        self.fn = fn
        self.runtime_args = tuple(runtime_args)
        self.callee_bound_values: tuple[DSLNode, ...] = ()
        self.globals_table: dict[str, DslVisitValue] = dict(fn.__globals__) if inspect.isfunction(fn) else {}
        if inspect.isfunction(fn):
            closure_vars = inspect.getclosurevars(fn)
            self.globals_table.update(closure_vars.globals)
            self.globals_table.update(closure_vars.nonlocals)
        self.runtime_table: dict[str, DslVisitValue] = {}
        if inspect.isfunction(fn):
            for parameter, value in zip(inspect.signature(fn).parameters.values(), self.runtime_args, strict=False):
                self.runtime_table[parameter.name] = value
        self.scope: dict[str, DSLNode] = {}
        self.import_states: dict[str, str] = {}
        self.tensor_metadata: dict[str, Memory] = {}
        self.diagnostics: list[Diagnostic] = []
        self.source = ""
        self.callee_function_map: dict[tuple[int, tuple[RuntimeArgKey, ...]], FunctionAST] = {}
        self.callee_function_order: list[tuple[int, tuple[RuntimeArgKey, ...]]] = []
        self.callee_signature_by_function: dict[int, tuple[RuntimeArgKey, ...]] = {}
        self.call_stack: list[DslCallable] = [fn] if inspect.isfunction(fn) else []
        self.statement_call_node: py_ast.Call | None = None

    def runtime_arg_key(self, value: DslVisitValue) -> RuntimeArgKey:
        """生成 runtime 或 DSL 参数的稳定签名 key。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 用于判断同一个 Python callee 是否被不同签名重复调用。
        - helper call 优先使用 DSLNode 字段生成签名，不再从 DSLNode 反推 runtime value。
        - key 只用于解析期去重，作为 Python callee 结构化解析的公开 visitor API。

        使用示例:
        - key = visitor.runtime_arg_key(memory)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_mlir_gen.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if isinstance(value, MemoryAST):
            memory = value.memory
            return (
                "MemoryAST",
                tuple(str(dim) for dim in memory.get_shape()),
                tuple(str(dim) for dim in memory.get_stride()),
                str(memory.get_type()),
                str(memory.get_space()),
            )
        if isinstance(value, SymbolDimAST):
            return ("SymbolDimAST", str(value.symbol.get_value()))
        if isinstance(value, BoolValueAST):
            return ("bool", repr(value.raw_value))
        if isinstance(value, ConstValueAST):
            return (type(value.raw_value).__name__, repr(value.raw_value))
        if isinstance(value, Memory):
            return (
                "Memory",
                tuple(str(dim) for dim in value.get_shape()),
                tuple(str(dim) for dim in value.get_stride()),
                str(value.get_type()),
                str(value.get_space()),
            )
        if isinstance(value, SymbolDim):
            return ("SymbolDim", str(value))
        if isinstance(value, (bool, int, float, str)):
            return (type(value).__name__, repr(value))
        if isinstance(value, NnMemoryType):
            return (
                "NnMemoryType",
                tuple(str(dim) for dim in value.shape.data),
                tuple(str(dim) for dim in value.stride.data),
                str(value.element_type),
                str(value.space),
            )
        return (type(value).__name__, repr(value))

    def parse_python_callee(
        self,
        callee: DslCallable,
        args: tuple[DSLNode, ...],
        location: SourceLocation | None,
    ) -> FunctionAST:
        """即时解析合法 Python callee。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - `CallAST` 构造前即完成 callee 源码读取、递归解析和签名去重。
        - callee 参数使用 caller 侧 DSLNode 绑定，不再还原为 runtime `Memory` / `SymbolDim`。
        - 发现递归、不同签名重复调用或不可读取源码时立即抛出稳定错误。

        使用示例:
        - helper_ast = visitor.parse_python_callee(helper, (memory_ast,), location)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_mlir_gen.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if callee in self.call_stack:
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Recursive Python callee is unsupported")
        signature = tuple(self.runtime_arg_key(value) for value in args)
        function_id = id(callee)
        previous_signature = self.callee_signature_by_function.get(function_id)
        if previous_signature is not None and previous_signature != signature:
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Python callee cannot use multiple signatures")
        key = (function_id, signature)
        if key in self.callee_function_map:
            return self.callee_function_map[key]

        self.callee_signature_by_function[function_id] = signature
        self.callee_function_order.append(key)
        self.call_stack.append(callee)
        try:
            try:
                source = textwrap.dedent(inspect.getsource(callee))
            except OSError as exc:
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Python callee source is unavailable") from exc
            tree = py_ast.parse(source)
            function_defs = [stmt for stmt in tree.body if isinstance(stmt, py_ast.FunctionDef)]
            if len(function_defs) != 1:
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Python callee source must contain one function")
            callee_visitor = DslAstVisitor(callee)
            callee_visitor.callee_bound_values = args
            callee_visitor.source = source
            callee_visitor.callee_function_map = self.callee_function_map
            callee_visitor.callee_function_order = self.callee_function_order
            callee_visitor.callee_signature_by_function = self.callee_signature_by_function
            callee_visitor.call_stack = self.call_stack
            function_ast = callee_visitor.visit_FunctionDef(function_defs[0])
            self.callee_function_map[key] = function_ast
            return function_ast
        except Exception:
            if key not in self.callee_function_map and key in self.callee_function_order:
                self.callee_function_order.remove(key)
            raise
        finally:
            self.call_stack.pop()

    def build_python_callee_call(
        self,
        callee: DslCallable,
        args: list[DSLNode],
        kwargs: dict[str, DSLNode],
        location: SourceLocation | None,
    ) -> CallAST:
        """构造已经完成合法性检查的 `CallAST`。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 直接使用实参 DSL 节点绑定 Python callee 形参，并立即解析 Python callee。
        - 不使用待解析队列；构造失败即表示该 callee 不属于当前支持范围。

        使用示例:
        - call_ast = visitor.build_python_callee_call(helper, args, {}, location)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_mlir_gen.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if kwargs:
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Python callee keyword arguments are unsupported")
        expected_arg_count = len(inspect.signature(callee).parameters)
        if len(args) != expected_arg_count:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "Python callee arity mismatch")
        value_args: list[ValueAST] = []
        for arg in args:
            if not isinstance(arg, ValueAST):
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Unsupported Python callee argument")
            value_args.append(arg)
        callee_ast = self.parse_python_callee(callee, tuple(value_args), location)
        return CallAST(callee_ast, value_args, location=location)

    def visit(self, node: py_ast.AST) -> DSLNode | None:
        """分发 Python AST 节点并校验 visitor 返回值。


        功能说明:
        - 所有 `visit_*` 非空返回值必须是 `DSLNode`。
        - import 与 docstring 等无 AST 产物的节点允许返回 `None`；无值 return 生成 `ReturnAST`。

        使用示例:
        - value = visitor.visit(expr_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        result = super().visit(node)
        if result is not None and not isinstance(result, DSLNode):
            raise KernelCodeError(
                ErrorKind.INTERNAL,
                ErrorModule.AST,
                f"{type(self).__name__}.{self.visit.__name__} must return DSLNode or None",
            )
        return result

    def visit_Module(self, node: py_ast.Module) -> ModuleAST:
        """解析 Python module 节点。


        功能说明:
        - 收集 module 中的 `FunctionDef` 并转换为 `ModuleAST`。

        使用示例:
        - module_ast = visitor.visit_Module(module_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        functions = [self.visit_FunctionDef(stmt) for stmt in node.body if isinstance(stmt, py_ast.FunctionDef)]
        functions.extend(self.callee_function_map[key] for key in self.callee_function_order if key in self.callee_function_map)
        return ModuleAST(functions=functions, runtime_args=self.runtime_args, source_fn=self.fn)

    def visit_FunctionDef(self, node: py_ast.FunctionDef) -> FunctionAST:
        """解析 Python 函数定义节点。


        功能说明:
        - 只根据 runtime args 生成函数输入 AST；Python annotation 不参与 DSL 语义。
        - 逐条解析函数体语句并保存到 `BlockAST`。

        使用示例:
        - func_ast = visitor.visit_FunctionDef(function_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        previous_scope = self.scope
        previous_import_states = self.import_states
        previous_tensor_metadata = self.tensor_metadata
        previous_runtime_table = self.runtime_table
        previous_callee_bound_values = self.callee_bound_values
        self.scope = {}
        self.import_states = {}
        self.tensor_metadata = {}
        self.runtime_table = {}
        inputs: list[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST] = []
        parameters = list(node.args.args)
        for index, arg in enumerate(parameters):
            location = SourceLocation.from_py_ast(arg)
            bound_value = self.callee_bound_values[index] if index < len(self.callee_bound_values) else None
            runtime_value = self.runtime_args[index] if index < len(self.runtime_args) else previous_runtime_table.get(arg.arg)
            if bound_value is not None:
                if not isinstance(bound_value, ValueAST):
                    diagnostic = Diagnostic("Unsupported Python callee argument", location)
                    raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, diagnostic.message)
                input_node = FunctionAST.input_from_bound_value(arg.arg, bound_value, location)
                self.scope[arg.arg] = input_node
                inputs.append(input_node)
                input_memory = input_node.result_memory()
                if isinstance(input_memory, Memory):
                    self.tensor_metadata[arg.arg] = input_memory
                continue
            input_node = FunctionAST.input_from_runtime_arg(arg.arg, runtime_value, location)
            inputs.append(input_node)
            self.scope[arg.arg] = input_node
            self.runtime_table[arg.arg] = runtime_value
            input_memory = input_node.result_memory()
            if isinstance(input_memory, Memory):
                self.tensor_metadata[arg.arg] = input_memory
            continue

        returns_none = False

        statements: list[DSLNode] = []
        has_explicit_return = False
        for stmt in node.body:
            if has_explicit_return:
                location = SourceLocation.from_py_ast(stmt)
                diagnostic = Diagnostic("Return statement must be last", location)
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            value = self.visit(stmt)
            if isinstance(stmt, py_ast.Return):
                has_explicit_return = True
                returns_none = stmt.value is None or (isinstance(value, StatementAST) and not isinstance(value, ReturnAST))
            if value is None:
                continue
            statements.append(value)
        outputs: list[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST] = []
        func_ast = FunctionAST(
            name=node.name,
            inputs=inputs,
            outputs=outputs,
            body=BlockAST(statements, location=SourceLocation.from_py_ast(node)),
            location=SourceLocation.from_py_ast(node),
            source=self.source,
            py_ast=node,
            diagnostics=list(self.diagnostics),
            has_explicit_return=has_explicit_return,
            returns_none=returns_none,
            runtime_args=self.runtime_args,
        )
        self.scope = previous_scope
        self.import_states = previous_import_states
        self.tensor_metadata = previous_tensor_metadata
        self.runtime_table = previous_runtime_table
        self.callee_bound_values = previous_callee_bound_values
        return func_ast

    def visit_Import(self, node: py_ast.Import) -> None:
        """解析 import 语句。


        功能说明:
        - 作为标准 `ast.NodeVisitor` 入口处理 `ast.Import`。
        - 当前只记录历史不支持的 operation module 形态，供 call 阶段生成稳定错误。

        使用示例:
        - visitor.visit_Import(import_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        for alias in node.names:
            if alias.name in {
                "kernel_gen.operation.dma",
                "kernel_gen.operation.nn",
                "kernel_gen.operation.arch",
            }:
                self.import_states[alias.asname or alias.name.split(".", 1)[0]] = "__unknown_import__"
        return None

    def visit_ImportFrom(self, node: py_ast.ImportFrom) -> None:
        """解析 from-import 语句。


        功能说明:
        - 作为标准 `ast.NodeVisitor` 入口处理 `ast.ImportFrom`。
        - 对 `from kernel_gen.operation import dma|nn|arch` 保持稳定 unsupported 语义。

        使用示例:
        - visitor.visit_ImportFrom(import_from_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if node.module == "kernel_gen.operation":
            for alias in node.names:
                if alias.name in {"dma", "nn", "arch"}:
                    self.import_states[alias.asname or alias.name] = "__unsupported_import__"
        return None

    def visit_Assign(self, node: py_ast.Assign) -> DSLNode | None:
        """解析赋值语句。


        功能说明:
        - 支持单变量赋值与 tuple/list unpack，并把变量绑定写入当前作用域。
        - 对会产生 IR 的表达式语句返回表达式节点；不创建赋值节点。

        使用示例:
        - value = visitor.visit_Assign(assign_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        value_node = node.value
        value = self.visit(value_node)
        target = node.targets[0] if node.targets else None
        emit_expression = isinstance(value_node, (py_ast.BinOp, py_ast.Call, py_ast.Compare, py_ast.Subscript, py_ast.UnaryOp))
        if (
            isinstance(value_node, py_ast.Call)
            and isinstance(value_node.func, py_ast.Attribute)
            and value_node.func.attr in {"get_shape", "get_stride"}
        ):
            emit_expression = False
        if isinstance(value_node, py_ast.Call) and isinstance(value_node.func, py_ast.Name) and value_node.func.id == "float":
            emit_expression = False
        if isinstance(target, py_ast.Name):
            bound_value = value.binding_value() if isinstance(value, ValueAST) else None
            if emit_expression:
                if not isinstance(value, ValueAST):
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "assignment expression must be ValueAST")
                target_node = value.bind_target(target.id, SourceLocation.from_py_ast(target))
                bound_expr = BoundExprAST(target.id, target_node, value, location=SourceLocation.from_py_ast(target))
                self.scope[target.id] = target_node
                if isinstance(bound_value, Memory):
                    self.tensor_metadata[target.id] = bound_value
                    self.runtime_table[target.id] = bound_value
                elif bound_value is not None:
                    self.runtime_table[target.id] = bound_value
                    self.tensor_metadata.pop(target.id, None)
                else:
                    self.runtime_table.pop(target.id, None)
                    self.tensor_metadata.pop(target.id, None)
                return bound_expr
            self.scope[target.id] = value
            if bound_value is not None:
                self.runtime_table[target.id] = bound_value
            else:
                self.runtime_table.pop(target.id, None)
            if isinstance(bound_value, Memory):
                self.tensor_metadata[target.id] = bound_value
            else:
                self.tensor_metadata.pop(target.id, None)
            return None
        elif isinstance(target, (py_ast.Tuple, py_ast.List)) and isinstance(value, (SymbolListAST, TupleAST)):
            for target_item, source_item in zip(target.elts, value.items, strict=False):
                if isinstance(target_item, py_ast.Name):
                    self.scope[target_item.id] = source_item
        return None

    def visit_AugAssign(self, node: py_ast.AugAssign) -> DSLNode | None:
        """解析增强赋值语句。


        功能说明:
        - 把 `x += y` 一类语句转换为对应二元表达式，并更新作用域绑定。

        使用示例:
        - expr = visitor.visit_AugAssign(augassign_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        lhs = self.visit(node.target)
        rhs = self.visit(node.value)
        op_map = {
            py_ast.Add: "add",
            py_ast.Sub: "sub",
            py_ast.Mult: "mul",
            py_ast.Div: "truediv",
            py_ast.FloorDiv: "floordiv",
        }
        op = op_map.get(type(node.op))
        if op is None:
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Unsupported augmented assignment")
        expr_map = {
            "add": SymbolAddAST,
            "sub": SymbolSubAST,
            "mul": SymbolMulAST,
            "truediv": SymbolTrueDivAST,
            "floordiv": SymbolFloorDivAST,
        }
        expr_cls = expr_map[op]
        expr = expr_cls(lhs, rhs, location=SourceLocation.from_py_ast(node))
        if isinstance(node.target, py_ast.Name):
            self.scope[node.target.id] = expr
        return expr

    def visit_For(self, node: py_ast.For) -> ForAST | None:
        """解析 for 循环语句。


        功能说明:
        - 支持 `range(...)` 与 DSL `loop(...)`，生成 `ForAST`。
        - 循环变量的解析期 symbol 语义标记为 `?`，避免后续 shape/size 推导把迭代 SSA 名称拼入公开表达。

        使用示例:
        - for_ast = visitor.visit_For(for_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if not isinstance(node.target, py_ast.Name):
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "for target must be a name")
        if not isinstance(node.iter, py_ast.Call):
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "for iterable must be range or loop")
        call_name = node.iter.func.id if isinstance(node.iter.func, py_ast.Name) else node.iter.func.attr if isinstance(node.iter.func, py_ast.Attribute) else ""
        if call_name not in {"range", "loop", "LoopRange"}:
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "for iterable must be range or loop")
        args = [self.visit(arg) for arg in node.iter.args]
        if len(args) == 1:
            start, end, step = ConstValueAST(0), args[0], ConstValueAST(1)
        elif len(args) == 2:
            start, end, step = args[0], args[1], ConstValueAST(1)
        elif len(args) == 3:
            start, end, step = args
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "for range arity must be 1, 2 or 3")
        if isinstance(step, ConstValueAST) and step.raw_value == 0:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "for range step must not be zero")
        previous_scope = dict(self.scope)
        loop_var = SymbolDimAST(
            node.target.id,
            location=SourceLocation.from_py_ast(node.target),
            runtime_symbol=SymbolDim("?"),
        )
        self.scope[node.target.id] = loop_var
        statements: list[DSLNode] = []
        for stmt in node.body:
            value = self.visit(stmt)
            if value is None:
                continue
            statements.append(value)
        self.scope = previous_scope
        return ForAST(loop_var, start, end, BlockAST(statements), step, location=SourceLocation.from_py_ast(node))

    def visit_If(self, node: py_ast.If) -> IfAST:
        """解析 if 语句。


        功能说明:
        - 将 Python `if` / `else` 语句转换为 `IfAST`。

        使用示例:
        - if_ast = visitor.visit_If(if_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        condition = self.visit(node.test)
        true_statements: list[DSLNode] = []
        false_statements: list[DSLNode] = []
        for stmt in node.body:
            value = self.visit(stmt)
            if value is not None:
                true_statements.append(value)
        for stmt in node.orelse:
            value = self.visit(stmt)
            if value is not None:
                false_statements.append(value)
        return IfAST(
            condition,
            BlockAST(true_statements),
            BlockAST(false_statements) if node.orelse else None,
            location=SourceLocation.from_py_ast(node),
        )

    def visit_Return(self, node: py_ast.Return) -> ReturnAST | StatementAST:
        """解析 return 语句。


        功能说明:
        - 返回 `ReturnAST`；无值 return 生成空返回。
        - `return kernel.add(...)` 这类无结果 statement helper 作为发射该 statement 后返回 `None` 处理。

        使用示例:
        - value = visitor.visit_Return(return_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if (
            isinstance(node.value, py_ast.Name)
            and node.value.id not in self.scope
            and node.value.id not in self.runtime_table
            and isinstance(self.globals_table.get(node.value.id), (int, float, bool, str, SymbolDim, Memory))
        ):
            location = SourceLocation.from_py_ast(node.value)
            diagnostic = Diagnostic("cannot use external value inside function body", location)
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
        if node.value is None:
            return ReturnAST((), location=SourceLocation.from_py_ast(node))
        value = self.visit(node.value)
        if isinstance(value, StatementAST) and not isinstance(value, ReturnAST):
            return value
        if isinstance(value, TupleAST):
            values: list[ValueAST] = []
            for item in value.items:
                if not isinstance(item, ValueAST):
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "return values must be ValueAST")
                values.append(item)
            return ReturnAST(values, location=SourceLocation.from_py_ast(node))
        if not isinstance(value, ValueAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "return values must be ValueAST")
        return ReturnAST(value, location=SourceLocation.from_py_ast(node))

    def visit_Expr(self, node: py_ast.Expr) -> DSLNode | None:
        """解析表达式语句。


        功能说明:
        - 表达式语句直接下沉为对应表达式 AST。

        使用示例:
        - expr = visitor.visit_Expr(expr_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if isinstance(node.value, py_ast.Constant) and isinstance(node.value.value, str):
            return None
        previous_statement_call_node = self.statement_call_node
        self.statement_call_node = node.value if isinstance(node.value, py_ast.Call) else None
        try:
            return self.visit(node.value)
        finally:
            self.statement_call_node = previous_statement_call_node

    def visit_BinOp(self, node: py_ast.BinOp) -> ValueAST:
        """解析二元表达式。


        功能说明:
        - 支持 `+`、`-`、`*`、`/`、`//`。

        使用示例:
        - expr = visitor.visit_BinOp(binop_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        op_map = {
            py_ast.Add: "add",
            py_ast.Sub: "sub",
            py_ast.Mult: "mul",
            py_ast.Div: "truediv",
            py_ast.FloorDiv: "floordiv",
        }
        op = op_map.get(type(node.op))
        if op is None:
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Unsupported binary operator")
        lhs = self.visit(node.left)
        rhs = self.visit(node.right)
        symbol_ops = {
            "add": SymbolAddAST,
            "sub": SymbolSubAST,
            "mul": SymbolMulAST,
            "truediv": SymbolTrueDivAST,
            "floordiv": SymbolFloorDivAST,
        }
        nn_ops = {
            "add": NnAddAST,
            "sub": NnSubAST,
            "mul": NnMulAST,
            "truediv": NnTrueDivAST,
            "floordiv": NnFloorDivAST,
        }
        if not isinstance(lhs, ValueAST) or not isinstance(rhs, ValueAST):
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, f"Unsupported binary op: {op}")
        lhs_is_symbol = lhs.result_symbol() is not None
        rhs_is_symbol = rhs.result_symbol() is not None
        lhs_is_float = isinstance(lhs.result_scalar(), float)
        rhs_is_float = isinstance(rhs.result_scalar(), float)
        if (lhs_is_symbol and rhs_is_float) or (rhs_is_symbol and lhs_is_float):
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, f"Unsupported binary op: {op}")
        if lhs_is_symbol and rhs_is_symbol:
            return symbol_ops[op](lhs, rhs, location=SourceLocation.from_py_ast(node))
        return nn_ops[op](lhs, rhs, location=SourceLocation.from_py_ast(node))

    def visit_Compare(self, node: py_ast.Compare) -> ValueAST:
        """解析比较表达式。


        功能说明:
        - 支持单个比较操作，并按输入类型生成具体 symbol / NN compare 节点。

        使用示例:
        - expr = visitor.visit_Compare(compare_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Only single compare is supported")
        op_map = {
            py_ast.Eq: "eq",
            py_ast.NotEq: "ne",
            py_ast.Lt: "lt",
            py_ast.LtE: "le",
            py_ast.Gt: "gt",
            py_ast.GtE: "ge",
        }
        op = op_map.get(type(node.ops[0]))
        if op is None:
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Unsupported compare operator")
        lhs = self.visit(node.left)
        rhs = self.visit(node.comparators[0])
        symbol_ops = {
            "eq": SymbolEqAST,
            "ne": SymbolNeAST,
            "lt": SymbolLtAST,
            "le": SymbolLeAST,
            "gt": SymbolGtAST,
            "ge": SymbolGeAST,
        }
        nn_ops = {
            "eq": NnEqAST,
            "ne": NnNeAST,
            "lt": NnLtAST,
            "le": NnLeAST,
            "gt": NnGtAST,
            "ge": NnGeAST,
        }
        if not isinstance(lhs, ValueAST) or not isinstance(rhs, ValueAST):
            if isinstance(lhs, PythonObjectAttrAST) and isinstance(rhs, PythonObjectAttrAST) and op in {"eq", "ne"}:
                is_equal = lhs.attr == rhs.attr
                return BoolValueAST(is_equal if op == "eq" else not is_equal, location=SourceLocation.from_py_ast(node))
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, f"Unsupported compare op: {op}")
        lhs_is_symbol = lhs.result_symbol() is not None
        rhs_is_symbol = rhs.result_symbol() is not None
        lhs_is_float = isinstance(lhs.result_scalar(), float)
        rhs_is_float = isinstance(rhs.result_scalar(), float)
        if (lhs_is_symbol and rhs_is_float) or (rhs_is_symbol and lhs_is_float):
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, f"Unsupported compare op: {op}")
        if lhs_is_symbol and rhs_is_symbol:
            return symbol_ops[op](lhs, rhs, location=SourceLocation.from_py_ast(node))
        return nn_ops[op](lhs, rhs, location=SourceLocation.from_py_ast(node))

    def visit_Call(self, node: py_ast.Call) -> DSLNode:
        """解析函数调用表达式。


        功能说明:
        - 通过 builtin registry 识别 DSL helper。
        - 未注册但可静态解析的 Python function 会立即解析为 `CallAST`。

        使用示例:
        - value = visitor.visit_Call(call_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if isinstance(node.func, py_ast.Attribute) and node.func.attr in {"get_shape", "get_stride"}:
            if node.args or node.keywords:
                diagnostic = Diagnostic(
                    f"Unsupported {node.func.attr} arity",
                    SourceLocation.from_py_ast(node),
                )
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            attribute = node.func.value
            if isinstance(attribute, py_ast.Name):
                tensor_name = attribute.id
            elif isinstance(attribute, py_ast.Attribute) and isinstance(attribute.value, py_ast.Name):
                tensor_name = attribute.value.id
            else:
                tensor_name = ""
            if tensor_name in self.tensor_metadata and tensor_name in self.scope:
                rank = len(self.tensor_metadata[tensor_name].get_shape())
                kind = "shape" if node.func.attr == "get_shape" else "stride"
                return TupleAST(tuple(
                    TensorAxisAccessAST(self.scope[tensor_name], kind, ConstValueAST(axis), location=SourceLocation.from_py_ast(node))
                    for axis in range(rank)
                ), location=SourceLocation.from_py_ast(node))
        launch_extents: list[DSLNode] | None = None
        callee_obj: DslVisitValue | None = None
        if isinstance(node.func, py_ast.Subscript):
            launch_base = node.func.value
            if isinstance(launch_base, py_ast.Name):
                call_name = launch_base.id
                if call_name in self.import_states:
                    callee_obj = self.import_states[call_name]
                elif call_name not in self.scope:
                    callee_obj = self.globals_table.get(call_name)
            elif isinstance(launch_base, py_ast.Attribute) and isinstance(launch_base.value, py_ast.Name):
                call_name = launch_base.attr
                base_name = launch_base.value.id
                if base_name in self.import_states:
                    callee_obj = self.import_states[base_name]
                else:
                    base = self.globals_table.get(base_name)
                    if base is _operation_arch and call_name in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.arch"]:
                        callee_obj = _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.arch"][call_name]
            else:
                call_name = ""
            if callee_obj == "__unsupported_import__":
                location = SourceLocation.from_py_ast(node)
                diagnostic = Diagnostic("Unsupported call expression", location)
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, diagnostic.message)
            if callee_obj == "__unknown_import__":
                location = SourceLocation.from_py_ast(node)
                diagnostic = Diagnostic("Unknown name", location)
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            if callee_obj is not _operation_arch.launch_kernel:
                location = SourceLocation.from_py_ast(node)
                diagnostic = Diagnostic("Unsupported call expression", location)
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, diagnostic.message)
            launch_slice = node.func.slice
            if isinstance(launch_slice, py_ast.Tuple):
                launch_extents = [self.visit(item) for item in launch_slice.elts]
            else:
                launch_extents = [self.visit(launch_slice)]
        elif isinstance(node.func, py_ast.Attribute) and not isinstance(node.func.value, py_ast.Name):
            location = SourceLocation.from_py_ast(node)
            diagnostic = Diagnostic("Unsupported call expression", location)
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, diagnostic.message)
        elif isinstance(node.func, py_ast.Attribute):
            if isinstance(node.func.value, py_ast.Name) and self.import_states.get(node.func.value.id) == "__unsupported_import__":
                location = SourceLocation.from_py_ast(node)
                diagnostic = Diagnostic("Unsupported call expression", location)
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, diagnostic.message)
            if isinstance(node.func.value, py_ast.Name) and self.import_states.get(node.func.value.id) == "__unknown_import__":
                location = SourceLocation.from_py_ast(node)
                diagnostic = Diagnostic("Unknown name", location)
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            if (
                isinstance(node.func.value, py_ast.Name)
                and node.func.value.id not in self.scope
                and node.func.value.id not in self.globals_table
                and node.func.value.id not in self.import_states
            ):
                location = SourceLocation.from_py_ast(node)
                diagnostic = Diagnostic("Unsupported call expression", location)
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, diagnostic.message)
            call_name = node.func.attr
            base = self.globals_table.get(node.func.value.id)
            if base is _operation_dma and call_name in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.dma"]:
                callee_obj = _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.dma"][call_name]
            elif base is _operation_nn and call_name in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.nn"]:
                callee_obj = _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.nn"][call_name]
            elif base is _operation_kernel and call_name in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.kernel"]:
                callee_obj = _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.kernel"][call_name]
            elif base is _operation_arch and call_name in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.arch"]:
                callee_obj = _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.arch"][call_name]
        else:
            call_name = node.func.id if isinstance(node.func, py_ast.Name) else node.func.attr if isinstance(node.func, py_ast.Attribute) else ""
            if isinstance(node.func, py_ast.Name):
                if node.func.id in self.import_states:
                    callee_obj = self.import_states[node.func.id]
                elif node.func.id not in self.scope:
                    callee_obj = self.globals_table.get(node.func.id)
                if callee_obj is None and node.func.id not in {"float", "min", "max"}:
                    location = SourceLocation.from_py_ast(node)
                    if node.func.id in _DEFAULT_DSL_HELPERS:
                        diagnostic = Diagnostic("Unsupported call expression", location)
                        raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, diagnostic.message)
                    diagnostic = Diagnostic("Unknown name", location)
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
        if callee_obj == "__unsupported_import__":
            location = SourceLocation.from_py_ast(node)
            diagnostic = Diagnostic("Unsupported call expression", location)
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, diagnostic.message)
        if callee_obj == "__unknown_import__":
            location = SourceLocation.from_py_ast(node)
            diagnostic = Diagnostic("Unknown name", location)
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
        entry = lookup_builtin(callee_obj) if callee_obj is not None else None
        if entry is not None:
            call_name = entry.dsl_name
        args: list[DSLNode] = []
        for index, arg in enumerate(node.args):
            if callee_obj is _operation_arch.launch_kernel and index == 0:
                if isinstance(arg, py_ast.Constant):
                    args.append(PythonObjectAttrAST(arg.value, SourceLocation.from_py_ast(arg)))
                    continue
                if isinstance(arg, py_ast.Attribute):
                    args.append(PythonObjectAttrAST(py_ast.unparse(arg), SourceLocation.from_py_ast(arg)))
                    continue
            arg_node = self.visit(arg)
            args.append(arg_node)
        kwargs: dict[str, DSLNode] = {}
        for keyword_node in node.keywords:
            keyword_pair = self.visit(keyword_node)
            if not isinstance(keyword_pair, TupleAST) or len(keyword_pair.items) != 2:
                diagnostic = Diagnostic("Unsupported keyword expression", SourceLocation.from_py_ast(keyword_node))
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            keyword_name_node, keyword_value = keyword_pair.items
            keyword_name = keyword_name_node.raw_value if isinstance(keyword_name_node, ConstValueAST) else None
            if keyword_name is None:
                continue
            kwargs[keyword_name] = keyword_value
        location = SourceLocation.from_py_ast(node)
        if call_name == "float":
            if len(args) != 1 or kwargs:
                diagnostic = Diagnostic("Unsupported float arity", location)
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            return SymbolToFloatAST(args[0], location=location)
        if call_name in {"min", "max"}:
            if len(args) != 2 or kwargs:
                diagnostic = Diagnostic(f"Unsupported {call_name} arity", location)
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            lhs, rhs = args
            if not isinstance(lhs, ValueAST) or not isinstance(rhs, ValueAST):
                diagnostic = Diagnostic(f"{call_name} arguments must be symbol values", location)
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            lhs_symbol = lhs.result_symbol()
            rhs_symbol = rhs.result_symbol()
            if lhs_symbol is None or rhs_symbol is None:
                diagnostic = Diagnostic(f"{call_name} arguments must be symbol values", location)
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
            if isinstance(lhs_symbol, int) and isinstance(rhs_symbol, int):
                value = min(lhs_symbol, rhs_symbol) if call_name == "min" else max(lhs_symbol, rhs_symbol)
                return ConstValueAST(value, location=location)
            return SymbolMinAST(lhs, rhs, location=location) if call_name == "min" else SymbolMaxAST(lhs, rhs, location=location)
        if entry is not None and entry.ast_node is not None:
            builtin_call = BuiltinCall(
                source=node,
                dsl_name=call_name,
                ast_node=entry.ast_node,
                args=args,
                kwargs=kwargs,
                location=location,
                launch_extents=launch_extents,
            )
            return entry.builder(builtin_call)
        if inspect.isfunction(callee_obj):
            if node is not self.statement_call_node:
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Python callee return value is unsupported")
            return self.build_python_callee_call(callee_obj, args, kwargs, location)
        raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, f"Unsupported call: {call_name}")

    def visit_List(self, node: py_ast.List) -> SymbolListAST | TupleAST:
        """解析 Python list AST 节点。


        功能说明:
        - 作为标准 `ast.NodeVisitor` 入口解析 `ast.List`。
        - 返回逐项解析后的 DSL AST 节点。

        使用示例:
        - values = visitor.visit_List(list_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        values = [self.visit(item) for item in node.elts]
        if all(isinstance(item, (ConstValueAST, SymbolDimAST)) for item in values):
            return SymbolListAST(values, location=SourceLocation.from_py_ast(node))
        return TupleAST(tuple(values), location=SourceLocation.from_py_ast(node))

    def visit_Tuple(self, node: py_ast.Tuple) -> TupleAST:
        """解析 Python tuple AST 节点。


        功能说明:
        - 作为标准 `ast.NodeVisitor` 入口解析 `ast.Tuple`。
        - 返回逐项解析后的 tuple。

        使用示例:
        - values = visitor.visit_Tuple(tuple_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        values = tuple(self.visit(item) for item in node.elts)
        return TupleAST(values, location=SourceLocation.from_py_ast(node))

    def visit_keyword(self, node: py_ast.keyword) -> TupleAST:
        """解析 Python keyword AST 节点。


        功能说明:
        - 作为标准 `ast.NodeVisitor` 入口解析 `ast.keyword`。
        - 返回 `TupleAST((ConstValueAST(keyword_name), value))`，其中 `keyword_name=None` 表示 `**kwargs` 展开。

        使用示例:
        - pair = visitor.visit_keyword(keyword_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        value = self.visit(node.value)
        return TupleAST((ConstValueAST(node.arg), value), location=SourceLocation.from_py_ast(node))

    def visit_Name(self, node: py_ast.Name) -> DSLNode:
        """解析名称引用。


        功能说明:
        - 优先返回作用域绑定，其次把 runtime/global 值包装为当前公开 DSL 节点。

        使用示例:
        - value = visitor.visit_Name(name_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if node.id in self.scope:
            return self.scope[node.id]
        if node.id in self.runtime_table:
            value = self.runtime_table[node.id]
            if isinstance(value, (int, float, bool, str, SymbolDim)):
                if isinstance(value, bool):
                    return BoolValueAST(value, location=SourceLocation.from_py_ast(node))
                if isinstance(value, SymbolDim):
                    return SymbolDimAST(value, location=SourceLocation.from_py_ast(node))
                return ConstValueAST(value, location=SourceLocation.from_py_ast(node))
            return PythonObjectAttrAST(value, location=SourceLocation.from_py_ast(node))
        if node.id in self.globals_table:
            value = self.globals_table[node.id]
            if isinstance(value, (int, float, bool, str, SymbolDim)):
                if isinstance(value, bool):
                    return BoolValueAST(value, location=SourceLocation.from_py_ast(node))
                if isinstance(value, SymbolDim):
                    return SymbolDimAST(value, location=SourceLocation.from_py_ast(node))
                return ConstValueAST(value, location=SourceLocation.from_py_ast(node))
            return PythonObjectAttrAST(value, location=SourceLocation.from_py_ast(node))
        location = SourceLocation.from_py_ast(node)
        diagnostic = Diagnostic("Unknown name", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)

    def visit_Constant(self, node: py_ast.Constant) -> ConstValueAST | BoolValueAST:
        """解析常量表达式。


        功能说明:
        - 将 Python literal 包装为 `ConstValueAST` 或 `BoolValueAST`。

        使用示例:
        - const = visitor.visit_Constant(const_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        if isinstance(node.value, bool):
            return BoolValueAST(node.value, location=SourceLocation.from_py_ast(node))
        return ConstValueAST(node.value, location=SourceLocation.from_py_ast(node))

    def visit_Subscript(self, node: py_ast.Subscript) -> DSLNode:
        """解析下标表达式。


        功能说明:
        - 支持 shape/stride 访问结果下标与 tensor load 语义。

        使用示例:
        - value = visitor.visit_Subscript(subscript_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        index_node = node.slice
        index = self.visit(index_node) if isinstance(index_node, py_ast.AST) else ConstValueAST(index_node)
        index_value = index.raw_value if isinstance(index, ConstValueAST) else None
        if isinstance(node.value, py_ast.Name) and node.value.id in self.tensor_metadata and node.value.id in self.scope:
            return DmaLoadAST(self.scope[node.value.id], index, ConstValueAST(1), ConstValueAST(1), location=SourceLocation.from_py_ast(node))
        value = self.visit(node.value)
        if isinstance(value, (SymbolListAST, TupleAST)) and isinstance(index_value, int):
            return value.items[index_value]
        raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Unsupported subscript")

    def visit_UnaryOp(self, node: py_ast.UnaryOp) -> ConstValueAST:
        """解析一元表达式。


        功能说明:
        - 支持字面量正负号。

        使用示例:
        - value = visitor.visit_UnaryOp(unary_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        operand = self.visit(node.operand)
        if isinstance(operand, ConstValueAST) and isinstance(operand.raw_value, (int, float)):
            if isinstance(node.op, py_ast.USub):
                return ConstValueAST(-operand.raw_value, location=SourceLocation.from_py_ast(node))
            if isinstance(node.op, py_ast.UAdd):
                return operand
        raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Unsupported unary operator")

    def visit_Attribute(self, node: py_ast.Attribute) -> DSLNode:
        """解析属性表达式。


        功能说明:
        - 支持 enum 属性、tensor/memory dtype 与显式 DSL helper 模块属性。
        - 不使用任意 Python 反射解析未知对象属性。

        使用示例:
        - value = visitor.visit_Attribute(attribute_node)

        关联文件:
        - spec: spec/dsl/ast/dsl_ast.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/dsl_ast.py
        """

        location = SourceLocation.from_py_ast(node)
        if isinstance(node.value, py_ast.Name):
            if node.value.id in self.import_states:
                if self.import_states[node.value.id] == "__unknown_import__":
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "Unknown name")
                raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Unsupported attribute")
            if node.value.id in self.tensor_metadata and node.attr == "dtype":
                return PythonObjectAttrAST(self.tensor_metadata[node.value.id].get_type(), location)
            if (
                node.value.id not in self.scope
                and node.value.id not in self.globals_table
                and node.value.id not in self.tensor_metadata
            ):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "Unknown name")
            base = self.scope[node.value.id] if node.value.id in self.scope else self.globals_table.get(node.value.id)
            if isinstance(base, PythonObjectAttrAST):
                base = base.attr
            if isinstance(base, Memory) and node.attr == "dtype":
                return PythonObjectAttrAST(base.dtype, location)
            if isinstance(base, dict) and node.attr in base:
                return PythonObjectAttrAST(base[node.attr], location)
            if base is _operation_dma and node.attr in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.dma"]:
                return PythonObjectAttrAST(_IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.dma"][node.attr], location)
            if base is _operation_nn and node.attr in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.nn"]:
                return PythonObjectAttrAST(_IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.nn"][node.attr], location)
            if base is _operation_kernel and node.attr in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.kernel"]:
                return PythonObjectAttrAST(_IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.kernel"][node.attr], location)
            if base is _operation_kernel and node.attr == "KernelBinaryElewiseKind":
                return PythonObjectAttrAST(KernelBinaryElewiseKind, location)
            if base is _operation_arch and node.attr in _IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.arch"]:
                return PythonObjectAttrAST(_IMPORTABLE_DSL_HELPER_MODULES["kernel_gen.operation.arch"][node.attr], location)
            if base is KernelBinaryElewiseKind and node.attr in KernelBinaryElewiseKind.__members__:
                return PythonObjectAttrAST(KernelBinaryElewiseKind[node.attr], location)
            if base is MemorySpace and node.attr in MemorySpace.__members__:
                return PythonObjectAttrAST(MemorySpace[node.attr], location)
            if base is NumericType and node.attr in NumericType.__members__:
                return PythonObjectAttrAST(NumericType[node.attr], location)
            if base is BarrierVisibility and node.attr in BarrierVisibility.__members__:
                return PythonObjectAttrAST(BarrierVisibility[node.attr], location)
            if base is BarrierScope and node.attr in BarrierScope.__members__:
                return PythonObjectAttrAST(BarrierScope[node.attr], location)
        if isinstance(node.value, py_ast.Attribute):
            base_node = self.visit_Attribute(node.value)
            if isinstance(base_node, PythonObjectAttrAST):
                base = base_node.attr
                if base is KernelBinaryElewiseKind and node.attr in KernelBinaryElewiseKind.__members__:
                    return PythonObjectAttrAST(KernelBinaryElewiseKind[node.attr], location)
        raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, f"Unsupported attribute: {node.attr}")
