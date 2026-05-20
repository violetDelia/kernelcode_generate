/*
功能说明:
- 提供 runtime trance kernel log 的 npu_demo header-only 实现。
- 仅在 `TRANCE` 宏开启时引入标准库打印、字符串拼接与文件管理依赖。
- 负责 stdout/file sink、函数入口、参数和返回值文本输出，不决定 Python 侧 dump_dir 或 kernel_name。
- 负责 block trace 目录准备、旧 `block_*.log` 清理、文件命名和当前线程 block sink 安装。
- 活动 sink 按线程隔离；未建立 `ScopedTranceSink` 的线程必须回退到 stdout sink。

API 列表:
- `kernelcode::trance::make_stdout_sink() -> TranceSink`
- `kernelcode::trance::make_file_sink(const char* file_path) -> TranceSink`
- `kernelcode::trance::make_default_sink() -> TranceSink`
- `kernelcode::trance::close_sink(TranceSink& sink) -> void`
- `kernelcode::trance::current_sink() -> const TranceSink&`
- `kernelcode::trance::ScopedTranceSink::ScopedTranceSink()`
- `kernelcode::trance::ScopedTranceSink::~ScopedTranceSink()`
- `kernelcode::trance::prepare_block_trace_dir(const char* dir_path) -> void`
- `kernelcode::trance::ScopedBlockTranceSink::ScopedBlockTranceSink(const char* dir_path, long long block_id, long long block_num, long long thread_id, long long thread_num)`
- `kernelcode::trance::ScopedBlockTranceSink::~ScopedBlockTranceSink()`
- `kernelcode::trance::write_line(const TranceSink& sink, const char* text) -> void`
- `kernelcode::trance::write_log_failed_and_fallback(const char* file_path) -> void`
- `kernelcode::trance::print_func_begin(const TranceSink& sink, const char* func_name, const char* template_desc) -> void`
- `kernelcode::trance::print_return_i64(const TranceSink& sink, long long value) -> void`
- `template <typename Callable> kernelcode::trance::print_callable_arg(const TranceSink& sink, const char* name, Callable&& callable) -> void`
- `template <typename T> kernelcode::trance::print_value_arg(const TranceSink& sink, const char* name, const T& value) -> void`

helper 清单:
- `kernelcode::trance::detail::*`：当前头文件内部 sink 状态、格式化与类型名辅助。

使用示例:
- #include "include/npu_demo/Trance.h"
- kernelcode::trance::ScopedTranceSink scope;
- kernelcode::trance::write_line(kernelcode::trance::current_sink(), "in func: demo template=<none>");

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_public_namespace.py
- 功能实现: include/api/Trance.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_TRANCE_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_TRANCE_H_

#include "include/api/Trance.h"

#ifdef TRANCE
#include <cstdio>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <mutex>
#include <sstream>
#include <string>
#include <type_traits>

#include "include/api/Memory.h"

#ifndef KG_TRANCE_FILE_PATH
#define KG_TRANCE_FILE_PATH ""
#endif

#ifndef KG_TRANCE_DIR_PATH
#define KG_TRANCE_DIR_PATH ""
#endif

#ifndef KG_TRANCE_KERNEL_NAME
#define KG_TRANCE_KERNEL_NAME "kernel"
#endif

namespace kernelcode {
namespace trance {
namespace detail {

inline TranceSink*& current_sink_storage() {
    // Keep active sink scoped to the calling host thread; unrelated threads
    // must not inherit another thread's file sink.
    thread_local TranceSink* sink = nullptr;
    return sink;
}

inline std::mutex& write_mutex() {
    static std::mutex mutex;
    return mutex;
}

inline const char* value_or_empty(const char* value) {
    return value == nullptr ? "" : value;
}

/*
功能说明:
- 判断 trace 路径宏是否为空，用于统一 stdout fallback 与 block 文件模式分支。

使用示例:
- bool empty = is_empty_path(KG_TRANCE_DIR_PATH);

关联文件:
- spec: spec/include/api/Trance.md
- test: test/include/api/test_trance.py
- 功能实现: include/npu_demo/Trance.h
*/
inline bool is_empty_path(const char* value) {
    return value_or_empty(value)[0] == '\0';
}

/*
功能说明:
- 判断目录项是否是本轮 runtime trance 管理的 `block_*.log` 文件。
- 只服务 `prepare_block_trace_dir(...)` 清理旧 block 文件，不删除其它诊断文件。

使用示例:
- if (is_block_trace_file_name(path)) { ... }

关联文件:
- spec: spec/include/api/Trance.md
- test: test/include/api/test_trance.py
- 功能实现: include/npu_demo/Trance.h
*/
inline bool is_block_trace_file_name(const std::filesystem::path& path) {
    const std::string filename = path.filename().string();
    return filename.rfind("block_", 0) == 0
        && filename.size() >= 10
        && filename.substr(filename.size() - 4) == ".log";
}

/*
功能说明:
- 生成当前 block 对应的 `block_XXXX.log` 文件路径。
- 编号至少 4 位，超过 9999 时保留完整十进制文本。

使用示例:
- std::string path = block_trace_file_path(dir, 0);

关联文件:
- spec: spec/include/api/Trance.md
- test: test/include/api/test_trance.py
- 功能实现: include/npu_demo/Trance.h
*/
inline std::string block_trace_file_path(const char* dir_path, long long block_id) {
    std::ostringstream filename;
    filename << "block_" << std::setfill('0') << std::setw(4) << block_id << ".log";
    return (std::filesystem::path(value_or_empty(dir_path)) / filename.str()).string();
}

template <typename T>
inline const char* dtype_name() {
    if constexpr (std::is_same<T, float>::value) {
        return "f32";
    }
    if constexpr (std::is_same<T, double>::value) {
        return "f64";
    }
    if constexpr (std::is_same<T, int>::value || std::is_same<T, std::int32_t>::value) {
        return "i32";
    }
    if constexpr (std::is_same<T, long long>::value || std::is_same<T, std::int64_t>::value) {
        return "i64";
    }
    if constexpr (std::is_same<T, bool>::value) {
        return "bool";
    }
    return "unknown";
}

inline const char* memory_space_name(MemorySpace space) {
    switch (space) {
        case MemorySpace::GM:
            return "GM";
        case MemorySpace::SM:
            return "SM";
        case MemorySpace::LM:
            return "LM";
        case MemorySpace::TSM:
            return "TSM";
        case MemorySpace::TLM1:
            return "TLM1";
        case MemorySpace::TLM2:
            return "TLM2";
        case MemorySpace::TLM3:
            return "TLM3";
    }
    return "unknown";
}

}  // namespace detail

inline TranceSink make_stdout_sink() {
    return TranceSink{true, "", nullptr};
}

inline void write_log_failed_and_fallback(const char* file_path) {
    const char* path = detail::value_or_empty(file_path);
    std::lock_guard<std::mutex> lock(detail::write_mutex());
    std::fprintf(stdout, "log failed: %s\n", path);
    std::fflush(stdout);
}

inline TranceSink make_file_sink(const char* file_path) {
    const char* path = detail::value_or_empty(file_path);
    if (path[0] == '\0') {
        return make_stdout_sink();
    }
    std::FILE* fp = std::fopen(path, "w");
    if (fp == nullptr) {
        write_log_failed_and_fallback(path);
        return make_stdout_sink();
    }
    return TranceSink{false, path, fp};
}

inline TranceSink make_default_sink() {
    return make_file_sink(KG_TRANCE_FILE_PATH);
}

inline void close_sink(TranceSink& sink) {
    if (!sink.to_stdout && sink.file_handle != nullptr) {
        std::fclose(static_cast<std::FILE*>(sink.file_handle));
        sink.file_handle = nullptr;
    }
}

inline const TranceSink& current_sink() {
    TranceSink* sink = detail::current_sink_storage();
    if (sink == nullptr) {
        static TranceSink stdout_sink = make_stdout_sink();
        return stdout_sink;
    }
    return *sink;
}

inline ScopedTranceSink::ScopedTranceSink()
    : sink_(make_default_sink()), previous_(detail::current_sink_storage()) {
    detail::current_sink_storage() = &sink_;
}

inline ScopedTranceSink::~ScopedTranceSink() {
    close_sink(sink_);
    detail::current_sink_storage() = previous_;
}

/*
功能说明:
- 准备 block trace 输出目录，并清理上次运行遗留的 `block_*.log`。
- 空目录路径 no-op；创建或遍历失败时输出 `log failed: <path>` 并让后续 sink 自行 fallback。

使用示例:
- kernelcode::trance::prepare_block_trace_dir(KG_TRANCE_DIR_PATH);

关联文件:
- spec: spec/include/api/Trance.md
- test: test/include/api/test_trance.py
- test: test/include/npu_demo/test_runtime_launch.py
- 功能实现: include/npu_demo/Trance.h
*/
inline void prepare_block_trace_dir(const char* dir_path) {
    if (detail::is_empty_path(dir_path)) {
        return;
    }
    const std::filesystem::path trace_dir(detail::value_or_empty(dir_path));
    std::error_code error;
    std::filesystem::create_directories(trace_dir, error);
    if (error) {
        write_log_failed_and_fallback(detail::value_or_empty(dir_path));
        return;
    }
    std::filesystem::directory_iterator it(trace_dir, error);
    if (error) {
        write_log_failed_and_fallback(detail::value_or_empty(dir_path));
        return;
    }
    for (const std::filesystem::directory_entry& entry : it) {
        if (entry.is_regular_file(error) && detail::is_block_trace_file_name(entry.path())) {
            std::filesystem::remove(entry.path(), error);
            error.clear();
        } else {
            error.clear();
        }
    }
}

/*
功能说明:
- 为当前 block worker 建立 block 文件 sink，写入 block/thread header，并安装当前线程 sink。
- 空 `dir_path` 或文件打开失败时复用 stdout fallback，不改变 kernel 返回码。

使用示例:
- kernelcode::trance::ScopedBlockTranceSink scope(KG_TRANCE_DIR_PATH, 0, 2, 0, 1);

关联文件:
- spec: spec/include/api/Trance.md
- test: test/include/api/test_trance.py
- test: test/include/npu_demo/test_runtime_launch.py
- 功能实现: include/npu_demo/Trance.h
*/
inline ScopedBlockTranceSink::ScopedBlockTranceSink(
    const char* dir_path,
    long long block_id,
    long long block_num,
    long long thread_id,
    long long thread_num)
    : file_path_(detail::is_empty_path(dir_path) ? "" : detail::block_trace_file_path(dir_path, block_id)),
      sink_(make_file_sink(file_path_.c_str())),
      previous_(detail::current_sink_storage()) {
    detail::current_sink_storage() = &sink_;
    if (!detail::is_empty_path(dir_path)) {
        std::ostringstream header;
        header << "block_id = " << block_id;
        write_line(sink_, header.str().c_str());
        header.str("");
        header.clear();
        header << "block_num = " << block_num;
        write_line(sink_, header.str().c_str());
        header.str("");
        header.clear();
        header << "thread_id = " << thread_id;
        write_line(sink_, header.str().c_str());
        header.str("");
        header.clear();
        header << "thread_num = " << thread_num;
        write_line(sink_, header.str().c_str());
    }
}

/*
功能说明:
- 关闭当前 block 文件 sink，并恢复进入 block scope 前的线程局部 sink。

使用示例:
- { kernelcode::trance::ScopedBlockTranceSink scope(dir, 0, 1, 0, 1); }

关联文件:
- spec: spec/include/api/Trance.md
- test: test/include/api/test_trance.py
- 功能实现: include/npu_demo/Trance.h
*/
inline ScopedBlockTranceSink::~ScopedBlockTranceSink() {
    close_sink(sink_);
    detail::current_sink_storage() = previous_;
}

inline void write_line(const TranceSink& sink, const char* text) {
    const char* line = detail::value_or_empty(text);
    std::lock_guard<std::mutex> lock(detail::write_mutex());
    if (sink.to_stdout || sink.file_handle == nullptr) {
        std::fprintf(stdout, "%s\n", line);
        std::fflush(stdout);
        return;
    }
    std::FILE* fp = static_cast<std::FILE*>(sink.file_handle);
    std::fprintf(fp, "%s\n", line);
    std::fflush(fp);
}

inline void print_func_begin(const TranceSink& sink, const char* func_name, const char* template_desc) {
    std::ostringstream line;
    line << "in func: " << detail::value_or_empty(func_name) << " " << detail::value_or_empty(template_desc);
    write_line(sink, line.str().c_str());
}

inline void print_return_i64(const TranceSink& sink, long long value) {
    std::ostringstream line;
    line << "return = " << value;
    write_line(sink, line.str().c_str());
}

template <typename Callable>
inline void print_callable_arg(const TranceSink& sink, const char* name, Callable&& callable) {
    (void)callable;
    std::ostringstream line;
    line << "  " << detail::value_or_empty(name) << " = callable[kernel_body]";
    write_line(sink, line.str().c_str());
}

template <MemorySpace Space, typename T>
inline void print_value_arg(const TranceSink& sink, const char* name, const Memory<Space, T>& value) {
    value.trance_print(sink, name);
}

template <typename T>
inline void print_value_arg(const TranceSink& sink, const char* name, const T& value) {
    std::ostringstream line;
    line << "  " << detail::value_or_empty(name) << " = " << value;
    write_line(sink, line.str().c_str());
}

}  // namespace trance
}  // namespace kernelcode

#endif  // TRANCE

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_TRANCE_H_
