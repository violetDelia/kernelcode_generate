/*
功能说明:
- 定义 include/api/Core.h 的统一状态码/状态类型与基础 Vector 视图声明。

使用示例:
- #include "include/api/Core.h"
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

#ifndef KERNELCODE_GENERATE_INCLUDE_API_CORE_H_
#define KERNELCODE_GENERATE_INCLUDE_API_CORE_H_

/*
功能说明:
- 定义统一状态码枚举，kOk 表示成功，其余值表示失败。

使用示例:
- StatusCode code = StatusCode::kOk;

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
enum StatusCode {
    kOk = 0,
    kError = 1,
};

/*
功能说明:
- 定义统一返回状态类型，与 StatusCode 可互换。

使用示例:
- Status status = StatusCode::kOk;

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/test_core.py
- 功能实现: include/npu_demo/Core.h
*/
using Status = StatusCode;

/*
功能说明:
- 轻量坐标/索引向量视图，封装调用方提供的连续 int64 缓冲区。

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
class Vector {
public:
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
    Vector(long long* data, unsigned long long size);

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
    Vector(const long long* data, unsigned long long size);

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
    unsigned long long size() const;

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
    long long* data();

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
    const long long* data() const;

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
    long long& operator[](unsigned long long index);

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
    const long long& operator[](unsigned long long index) const;

private:
    const long long* data_;
    unsigned long long size_;
};

#endif  // KERNELCODE_GENERATE_INCLUDE_API_CORE_H_
