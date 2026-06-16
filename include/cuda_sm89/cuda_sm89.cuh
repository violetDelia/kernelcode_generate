#pragma once

// 功能说明:
// - 定义 cuda_sm89 target 单入口 include，按 Core / Memory / Dma / Kernel / Arch 顺序汇聚 api 层与 CUDA 后端实现层。
// - 调用方通过该 aggregate header 获得 CUDA generated source 所需的 `cuda_sm89::ArgSlot` backend ABI。
//
// API 列表:
// - `namespace cuda_sm89`
// - `struct cuda_sm89::ArgSlot`
// - `class cuda_sm89::KernelContext`
// - `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status cuda_sm89::launch(Context& ctx, Args&&... args)`
// - `__device__ S_INT cuda_sm89::block_id()`
// - `__device__ S_INT cuda_sm89::thread_id()`
// - `__device__ S_INT cuda_sm89::thread_num()`
// - `__device__ void cuda_sm89::barrier()`
// - `template <MemorySpace Space, typename T, typename Context> __device__ Memory<Space, T> cuda_sm89::alloc(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm)`
// - `template <MemorySpace Space, typename SlotT, typename BackingT> class cuda_sm89::DmaRing`
// - `template <typename SlotT, MemorySpace Space, typename BackingT> __device__ cuda_sm89::DmaRing<Space, SlotT, BackingT> cuda_sm89::make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
// - `template <MemorySpace Space, typename T, typename Context> __device__ Status cuda_sm89::fill(Context& ctx, Memory<Space, T>& target, const T& value)`
// - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm89::slice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
// - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm89::deslice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
// - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::load(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
// - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::store(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
// - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::transpose(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
// - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::broadcast(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
// - `template <MemorySpace Space, typename T> __host__ __device__ Memory<Space, T> cuda_sm89::view(const Memory<Space, T>& source, long long offset, long long size, long long stride)`
// - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::add/sub/mul/truediv/max/exp/reduce_sum/reduce_max(...)`
// - `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context> __device__ Status cuda_sm89::matmul(Context& ctx, Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs, bool acc = false)`
// - `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::img2col2d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`
//
// helper 清单:
// - 无；当前文件只做公开聚合入口，不承接独立 helper 实现。
//
// 使用示例:
// - #include "include/cuda_sm89/cuda_sm89.cuh"
// - extern "C" int kg_execute_entry(cuda_sm89::ArgSlot* slots, unsigned long long count);
//
// 关联文件:
// - spec/include/cuda_sm89/cuda_sm89.md
// - include/api/Core.h
// - include/api/Memory.h
// - include/api/Dma.h
// - include/api/Kernel.h
// - include/api/Arch.h
// - include/cuda_sm89/Core.h
// - include/cuda_sm89/Memory.h
// - include/cuda_sm89/Dma.h
// - include/cuda_sm89/Kernel.h
// - include/cuda_sm89/Arch.h

#include "include/api/Core.h"
#include "include/api/Memory.h"
#include "include/api/Dma.h"
#include "include/api/Kernel.h"
#include "include/api/Arch.h"
#include "include/cuda_sm89/Core.h"
#include "include/cuda_sm89/Memory.h"
#include "include/cuda_sm89/Dma.h"
#include "include/cuda_sm89/Kernel.h"
#include "include/cuda_sm89/Arch.h"
