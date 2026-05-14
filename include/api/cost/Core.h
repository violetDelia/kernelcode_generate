/*
功能说明:
- 定义 include/api/cost/Core.h 的统一公共成本类型声明。
- 当前公开 `npu_demo::cost::CostKind::{DMA1, DMA2, DMA3, DMA4, MAC, VECTOR1, VECTOR2}`，并额外公开
  `npu_demo::{DMA1, DMA2, DMA3, DMA4, MAC, VECTOR1, VECTOR2}` 作为模板实参别名。
- 全部 cost helper 继续沿用 `S_INT` 作为返回类型来源。

API 列表:
- `namespace npu_demo::cost`
- `enum class npu_demo::cost::CostKind { DMA1, DMA2, DMA3, DMA4, MAC, VECTOR1, VECTOR2 }`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA1`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA2`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA3`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA4`
- `inline constexpr npu_demo::cost::CostKind npu_demo::MAC`
- `inline constexpr npu_demo::cost::CostKind npu_demo::VECTOR1`
- `inline constexpr npu_demo::cost::CostKind npu_demo::VECTOR2`

helper 清单:
- 无；当前文件只声明公开 cost 基础类型。

使用示例:
- #include "include/api/cost/Core.h"
- npu_demo::cost::CostKind kind = npu_demo::VECTOR1;
- S_INT cost = 0;


关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_COST_CORE_H_
#define KERNELCODE_GENERATE_INCLUDE_API_COST_CORE_H_

#include "include/api/Core.h"

namespace npu_demo {
namespace cost {

/*
功能说明:
- 定义当前公开的成本统计视角。
- `DMA` 兼容旧合同，当前透传为 `DMA1` 语义；`DMA1` 对应 GM -> TSM/TLM 方向；`DMA2` 对应 TSM/TLM -> GM 方向。
- `DMA3` 对应 TSM -> TLM、img2col 与 transpose；`DMA4` 对应 TSM -> TSM 与同类 transpose。
- `MAC` 对应 matmul；`VECTOR1` 对应当前非 matmul kernel op；`VECTOR2` 当前保留为 0。

使用示例:
- cost::CostKind dma_kind = cost::CostKind::DMA1;
- cost::CostKind vector_kind = cost::CostKind::VECTOR1;


关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/
enum class CostKind {
    DMA1,
    DMA2,
    DMA3,
    DMA4,
    MAC,
    VECTOR1,
    VECTOR2,
};

}  // namespace cost

/*
功能说明:
- 公开 `emit_c/gen_kernel(target="npu_demo")` 直接透传的成本 kind 模板实参别名。
- 让生成源码可直接写出 `DMA1` / `DMA2` / `DMA3` / `DMA4` / `MAC` / `VECTOR1` / `VECTOR2`，不再在 emit 阶段做额外映射。

使用示例:
- S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::VECTOR1>(out, lhs, rhs);
- S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::DMA1>(target, source);


关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/
inline constexpr cost::CostKind DMA = cost::CostKind::DMA1;
inline constexpr cost::CostKind DMA1 = cost::CostKind::DMA1;
inline constexpr cost::CostKind DMA2 = cost::CostKind::DMA2;
inline constexpr cost::CostKind DMA3 = cost::CostKind::DMA3;
inline constexpr cost::CostKind DMA4 = cost::CostKind::DMA4;
inline constexpr cost::CostKind MAC = cost::CostKind::MAC;
inline constexpr cost::CostKind VECTOR1 = cost::CostKind::VECTOR1;
inline constexpr cost::CostKind VECTOR2 = cost::CostKind::VECTOR2;
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_API_COST_CORE_H_
