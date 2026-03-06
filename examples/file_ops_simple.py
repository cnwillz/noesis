#!/usr/bin/env python3
"""
内置工具使用示例 - 直接调用

演示如何直接使用 file_read, file_write, file_append, file_update 工具。
"""

from noesis import file_read, file_write, file_append, file_update

# 测试文件路径
TEST_FILE = "./workspace/demo.txt"

print("=" * 50)
print("内置工具使用示例 - 直接调用")
print("=" * 50)

# ========== 1. 创建文件（file_write） ==========
print("\n1. 创建文件 (file_write)")
print("-" * 40)

result = file_write(TEST_FILE, """# 应用配置
app_name = MyApplication
version = 1.0.0
debug = true
port = 8080
""")

print(f"结果：{result}")


# ========== 2. 读取文件（file_read） ==========
print("\n2. 读取文件 (file_read)")
print("-" * 40)

result = file_read(TEST_FILE)
print(f"读取结果：{result['success']}")
print(f"文件内容:\n{result['content']}")


# ========== 3. 追加日志（file_append） ==========
print("\n3. 追加日志 (file_append)")
print("-" * 40)

result = file_append(TEST_FILE, "# 最后更新时间：2026-03-06\n")
print(f"追加结果：{result}")


# ========== 4. 再次读取查看追加效果 ==========
print("\n4. 再次读取文件")
print("-" * 40)

result = file_read(TEST_FILE)
print(f"文件内容:\n{result['content']}")


# ========== 5. 修改配置（file_update） ==========
print("\n5. 修改配置 (file_update)")
print("-" * 40)

# 行号从 0 开始：行 0=# 应用配置，行 1=app_name=..., 行 3=debug, 行 4=port
result = file_update(TEST_FILE, changes=[
    {"line": 3, "old_text": "debug = true", "new_text": "debug = false"},
    {"line": 4, "old_text": "port = 8080", "new_text": "port = 3000"}
])
print(f"更新结果：{result}")


# ========== 6. 查看最终内容 ==========
print("\n6. 查看最终文件内容")
print("-" * 40)

result = file_read(TEST_FILE)
print(f"文件内容:\n{result['content']}")


# ========== 7. 演示更新失败（old_text 不匹配） ==========
print("\n7. 演示更新失败（old_text 不匹配）")
print("-" * 40)

# 故意使用错误的 old_text
result = file_update(TEST_FILE, changes=[
    {"line": 3, "old_text": "debug = false", "new_text": "debug = true"}  # 实际是 debug = true，这里故意写错
])
print(f"更新结果：{result}")
if not result["success"]:
    print(f"失败原因：{result.get('failed', [{}])[0].get('error', '未知错误')}")


print("\n" + "=" * 50)
print("示例完成！")
print("=" * 50)
