/*
功能说明:
- 定义 include/api/Nn.h 的逐元素算术、比较与显式 broadcast 接口声明。

使用示例:
- #include "include/api/Nn.h"
- Status status = add(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_NN_H_
#define KERNELCODE_GENERATE_INCLUDE_API_NN_H_

#include "include/api/Core.h"
#include "include/api/Memory.h"

/*
功能说明:
- 对两个内存视图执行逐元素加法，结果写入输出视图。

使用示例:
- Status status = add(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
Status add(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out);

/*
功能说明:
- 对两个内存视图执行逐元素减法，结果写入输出视图。

使用示例:
- Status status = sub(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
Status sub(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out);

/*
功能说明:
- 对两个内存视图执行逐元素乘法，结果写入输出视图。

使用示例:
- Status status = mul(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
Status mul(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out);

/*
功能说明:
- 对两个内存视图执行逐元素真除法，结果写入输出视图。

使用示例:
- Status status = truediv(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
Status truediv(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out);

/*
功能说明:
- 对两个内存视图执行逐元素相等比较。

使用示例:
- Status status = eq(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
Status eq(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out);

/*
功能说明:
- 对两个内存视图执行逐元素不等比较。

使用示例:
- Status status = ne(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
Status ne(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out);

/*
功能说明:
- 对两个内存视图执行逐元素小于比较。

使用示例:
- Status status = lt(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
Status lt(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out);

/*
功能说明:
- 对两个内存视图执行逐元素小于等于比较。

使用示例:
- Status status = le(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
Status le(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out);

/*
功能说明:
- 对两个内存视图执行逐元素大于比较。

使用示例:
- Status status = gt(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
Status gt(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out);

/*
功能说明:
- 对两个内存视图执行逐元素大于等于比较。

使用示例:
- Status status = ge(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
Status ge(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out);

/*
功能说明:
- 执行显式 broadcast，将 input 写入 out。

使用示例:
- Status status = broadcast(input, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
Status broadcast(const Memory<Space, T>& input, Memory<Space, T>& out);

#endif  // KERNELCODE_GENERATE_INCLUDE_API_NN_H_
