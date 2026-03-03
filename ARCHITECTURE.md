# 目录结构说明

- 路径: `/`
- 作用: `kernelcode_generate` 项目根目录，包含示例脚本、核心源码包与测试目录
- 根目录: `/home/lfr/kernelcode_generate`
- 参考: 对齐 `/home/lfr/cpp_gen` 的组织方式（根目录下放置同名源码包与 tests）
- 范围: 仅列出当前目录的直接子项（更深层结构见下方“核心包内部结构建议”）

## 子目录（建议）

- `kernelcode_generate/`
  - 作用: 核心 DSL 包，包含前端语法、IR、Pass 与后端代码生成
- `tests/`
  - 作用: 测试目录，覆盖 DSL 行为、IR 正确性和多后端代码生成

## 文件（建议）

- `ARCHITECTURE.md`
  - 作用: 架构与目录结构说明（当前文件）
- `README.md`
  - 作用: 项目说明与快速上手
- `main.py`
  - 作用: 端到端 DSL 示例入口（类似 `cpp_gen/main.py`）
- `axpy.py`
  - 作用: 单算子示例脚本（可选）
- `matmul.py`
  - 作用: 矩阵乘示例脚本（可选）
- `pyproject.toml`
  - 作用: 现代 Python 打包与 CLI 入口配置
- `requirements.txt`
  - 作用: 依赖声明（可保持为空或最小依赖）
- `setup.py`
  - 作用: 兼容性打包入口（可选，占位即可）
- `.gitignore`
  - 作用: Git 忽略规则

## 核心包内部结构建议

```text
kernelcode_generate/
├── __init__.py
├── dsl.py
├── ir.py
├── compiler.py
├── kernel/
│   ├── __init__.py
│   └── launch_config.py
├── pass_manager/
│   ├── __init__.py
│   ├── canonicalize.py
│   └── const_fold.py
├── operation/
│   ├── __init__.py
│   ├── nn/
│   ├── control_flow/
│   └── utils/
├── target/
│   ├── __init__.py
│   ├── c/
│   └── cuda/
└── utils/
    ├── __init__.py
    └── diagnostics.py
```

## 测试结构建议

```text
tests/
├── test_dsl.py
├── test_ir.py
├── test_codegen_c.py
├── test_codegen_cuda.py
└── utils/
```
