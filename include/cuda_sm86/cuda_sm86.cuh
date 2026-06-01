#pragma once

// 功能说明:
// - 定义 cuda_sm86 target 单入口 include，透传 include/api 的统一 Arch 声明并汇聚 CUDA 后端实现层。
// - 调用方通过该 aggregate header 获得 CUDA generated source 所需的 `cuda_sm86::ArgSlot` backend ABI。
//
// API 列表:
// - `namespace cuda_sm86`
// - `struct cuda_sm86::ArgSlot`
//
// helper 清单:
// - 无；当前文件只做公开聚合入口，不承接独立 helper 实现。
//
// 使用示例:
// - #include "include/cuda_sm86/cuda_sm86.cuh"
// - extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count);
//
// 关联文件:
// - spec/include/cuda_sm86/cuda_sm86.md
// - include/api/Arch.h
// - include/cuda_sm86/Arch.h

#include "include/api/Arch.h"
#include "include/cuda_sm86/Arch.h"
