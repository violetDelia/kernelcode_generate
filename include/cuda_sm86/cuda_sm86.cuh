#pragma once

#include <cuda_runtime.h>

#include <cstdio>
#include <cstdlib>

namespace cuda_sm86 {

struct ArgSlot {
  int kind;
  void *data;
  long long *shape;
  long long *stride;
  unsigned long long rank;
  int dtype_code;
  long long int_value;
  double float_value;
};

inline void check_cuda(cudaError_t status, const char *expr, const char *file, int line) {
  if (status == cudaSuccess) {
    return;
  }
  std::fprintf(stderr, "cuda_runtime_failed: %s at %s:%d for %s\n", cudaGetErrorString(status), file, line, expr);
  std::abort();
}

#define KG_CUDA_CHECK(expr) ::cuda_sm86::check_cuda((expr), #expr, __FILE__, __LINE__)

}  // namespace cuda_sm86
