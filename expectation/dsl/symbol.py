from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.dsl.mlir_gen import build_func_op

s = SymbolDim("s")

def only_symbol(s:int):
    s_ = s+1
    return s_


func_op = build_func_op(only_symbol,1)
