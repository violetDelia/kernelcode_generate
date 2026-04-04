/*
功能说明:
- 提供 include/api/Core.h 的 npu_demo 实现，补全 Vector 方法定义。

使用示例:
- #include "include/npu_demo/Core.h"
- long long coords_buf[3] = {5, 0, 7};
- Vector coords(coords_buf, 3);
- Status status = StatusCode::kOk;

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_

#include "include/api/Core.h"

/*
功能说明:
- 使用调用方提供的连续缓冲区与元素个数构造 Vector 视图。

使用示例:
- long long coords_buf[3] = {5, 0, 7};
- Vector coords(coords_buf, 3);

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(long long* data, unsigned long long size) : data_(data), size_(size) {}

/*
功能说明:
- 使用只读连续缓冲区与元素个数构造 Vector 视图。

使用示例:
- const long long coords_buf[3] = {5, 0, 7};
- Vector coords(coords_buf, 3);

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(const long long* data, unsigned long long size) : data_(data), size_(size) {}

/*
功能说明:
- 返回当前 Vector 视图的元素个数。

使用示例:
- unsigned long long n = coords.size();

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
inline unsigned long long Vector::size() const {
    return size_;
}

/*
功能说明:
- 返回底层连续元素缓冲区首地址（可写）。

使用示例:
- long long* raw = coords.data();

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
inline long long* Vector::data() {
    return const_cast<long long*>(data_);
}

/*
功能说明:
- 返回底层连续元素缓冲区首地址（只读）。

使用示例:
- const long long* raw = coords.data();

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
inline const long long* Vector::data() const {
    return data_;
}

/*
功能说明:
- 读取或写入指定下标的元素。

使用示例:
- long long axis0 = coords[0];

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
inline long long& Vector::operator[](unsigned long long index) {
    return const_cast<long long&>(data_[index]);
}

/*
功能说明:
- 读取指定下标的元素。

使用示例:
- long long axis0 = coords[0];

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
inline const long long& Vector::operator[](unsigned long long index) const {
    return data_[index];
}

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_
