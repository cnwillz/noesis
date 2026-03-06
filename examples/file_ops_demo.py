#!/usr/bin/env python3
"""
内置工具使用示例 - 文件操作

演示如何使用 file_read, file_write, file_append, file_update 进行文件操作。
"""

from noesis import register_builtin_tools, call

# 注册内置工具
register_builtin_tools()

# 测试文件路径
TEST_FILE = "./workspace/demo.txt"

print("=" * 50)
print("内置工具使用示例 - 文件操作")
print("=" * 50)

# ========== 1. 创建文件（file_write） ==========
print("\n1. 创建文件 (file_write)")
print("-" * 40)

result = call(
    f"""
请创建一个配置文件，内容包括：
- 文件名：{TEST_FILE}
- 内容包含：应用名称、版本号、调试模式、端口号
使用 file_write 工具创建文件。
""",
    profile="default",
    tools=["file_write"]
)

print(f"LLM 输出：{result.output}")

# 查看思维链
for step in result.thought_chain:
    if step.kind in ["tool_call", "tool_result"]:
        print(f"  [{step.kind}] {step.content[:80]}")


# ========== 2. 读取文件（file_read） ==========
print("\n2. 读取文件 (file_read)")
print("-" * 40)

result = call(
    f"""
请读取 {TEST_FILE} 的内容并展示给我。
使用 file_read 工具。
""",
    profile="default",
    tools=["file_read"]
)

print(f"LLM 输出：{result.output}")


# ========== 3. 追加日志（file_append） ==========
print("\n3. 追加日志 (file_append)")
print("-" * 40)

result = call(
    f"""
请在 {TEST_FILE} 文件末尾追加一行日志：
"# 最后更新时间：2026-03-06"
使用 file_append 工具。
""",
    profile="default",
    tools=["file_append"]
)

print(f"LLM 输出：{result.output}")


# ========== 4. 修改配置（file_update） ==========
print("\n4. 修改配置 (file_update)")
print("-" * 40)

result = call(
    f"""
请修改 {TEST_FILE} 文件：
- 将调试模式从 true 改为 false
- 将端口号从 8080 改为 3000
使用 file_update 工具，直接指定要替换的原文本和新文本，不需要行号。
""",
    profile="default",
    tools=["file_read", "file_update"]
)

print(f"LLM 输出：{result.output}")

# 查看修改后的文件
result = call(
    f"请读取 {TEST_FILE} 展示最终内容",
    profile="default",
    tools=["file_read"]
)
print(f"\n最终文件内容:\n{result.output}")


# ========== 5. 完整示例：多行更新 ==========
print("\n5. 多行同时更新")
print("-" * 40)

result = call(
    f"""
请一次性修改 {TEST_FILE} 的多行配置：
- 更新调试模式
- 更新端口号
- 更新版本号
使用 file_update 工具，传入多组 changes。
""",
    profile="default",
    tools=["file_read", "file_update"]
)

print(f"LLM 输出：{result.output}")


print("\n" + "=" * 50)
print("示例完成！")
print("=" * 50)
