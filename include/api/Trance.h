/*
功能说明:
- 定义 runtime trance kernel log 的公开 sink、打印函数与作用域入口。
- `TRANCE` 未开启时只提供无副作用占位实现，不引入标准库打印或文件管理依赖。
- `TRANCE` 开启时由 include/npu_demo/Trance.h 提供 stdout/file sink 与格式化打印实现。
- `ScopedTranceSink/current_sink()` 的活动 sink 仅作用于当前线程，未建 scope 的线程回退 stdout sink。

API 列表:
- `struct kernelcode::trance::TranceSink`
- `kernelcode::trance::make_stdout_sink() -> TranceSink`
- `kernelcode::trance::make_file_sink(const char* file_path) -> TranceSink`
- `kernelcode::trance::make_default_sink() -> TranceSink`
- `kernelcode::trance::close_sink(TranceSink& sink) -> void`
- `kernelcode::trance::current_sink() -> const TranceSink&`
- `class kernelcode::trance::ScopedTranceSink`
- `ScopedTranceSink::ScopedTranceSink()`
- `ScopedTranceSink::~ScopedTranceSink()`
- `kernelcode::trance::write_line(const TranceSink& sink, const char* text) -> void`
- `kernelcode::trance::write_log_failed_and_fallback(const char* file_path) -> void`
- `kernelcode::trance::print_func_begin(const TranceSink& sink, const char* func_name, const char* template_desc) -> void`
- `kernelcode::trance::print_return_i64(const TranceSink& sink, long long value) -> void`
- `template <typename Callable> kernelcode::trance::print_callable_arg(const TranceSink& sink, const char* name, Callable&& callable) -> void`
- `template <typename T> kernelcode::trance::print_value_arg(const TranceSink& sink, const char* name, const T& value) -> void`

helper 清单:
- 无；当前文件只声明公开 runtime trance 边界。

使用示例:
- #include "include/api/Trance.h"
- kernelcode::trance::ScopedTranceSink scope;
- kernelcode::trance::print_func_begin(kernelcode::trance::current_sink(), "kernel", "template=<none>");

关联文件:
- spec: spec/include/api/Trance.md
- test: test/include/api/test_trance.py
- 功能实现: include/npu_demo/Trance.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_TRANCE_H_
#define KERNELCODE_GENERATE_INCLUDE_API_TRANCE_H_

namespace kernelcode {
namespace trance {

struct TranceSink {
#ifdef TRANCE
    bool to_stdout;
    const char* file_path;
    void* file_handle;
#endif
};

#ifdef TRANCE

TranceSink make_stdout_sink();
TranceSink make_file_sink(const char* file_path);
TranceSink make_default_sink();
void close_sink(TranceSink& sink);
const TranceSink& current_sink();
void write_line(const TranceSink& sink, const char* text);
void write_log_failed_and_fallback(const char* file_path);
void print_func_begin(const TranceSink& sink, const char* func_name, const char* template_desc);
void print_return_i64(const TranceSink& sink, long long value);

class ScopedTranceSink {
public:
    ScopedTranceSink();
    ~ScopedTranceSink();

private:
    TranceSink sink_;
    TranceSink* previous_;
};

template <typename Callable>
void print_callable_arg(const TranceSink& sink, const char* name, Callable&& callable);

template <typename T>
void print_value_arg(const TranceSink& sink, const char* name, const T& value);

#else

inline TranceSink make_stdout_sink() {
    return TranceSink{};
}

inline TranceSink make_file_sink(const char* file_path) {
    (void)file_path;
    return TranceSink{};
}

inline TranceSink make_default_sink() {
    return TranceSink{};
}

inline void close_sink(TranceSink& sink) {
    (void)sink;
}

inline const TranceSink& current_sink() {
    static TranceSink sink;
    return sink;
}

class ScopedTranceSink {
public:
    ScopedTranceSink() = default;
    ~ScopedTranceSink() = default;
};

inline void write_line(const TranceSink& sink, const char* text) {
    (void)sink;
    (void)text;
}

inline void write_log_failed_and_fallback(const char* file_path) {
    (void)file_path;
}

inline void print_func_begin(const TranceSink& sink, const char* func_name, const char* template_desc) {
    (void)sink;
    (void)func_name;
    (void)template_desc;
}

inline void print_return_i64(const TranceSink& sink, long long value) {
    (void)sink;
    (void)value;
}

template <typename Callable>
inline void print_callable_arg(const TranceSink& sink, const char* name, Callable&& callable) {
    (void)sink;
    (void)name;
    (void)callable;
}

template <typename T>
inline void print_value_arg(const TranceSink& sink, const char* name, const T& value) {
    (void)sink;
    (void)name;
    (void)value;
}

#endif

}  // namespace trance
}  // namespace kernelcode

#endif  // KERNELCODE_GENERATE_INCLUDE_API_TRANCE_H_
