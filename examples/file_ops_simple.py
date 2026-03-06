#!/usr/bin/env python3
"""
内置工具使用示例 - LLM 调用

演示如何通过 LLM 调用 file_read, file_write, file_append, file_update 工具。
"""

from noesis import register_builtin_tools, call

# 注册内置工具
register_builtin_tools()

# 测试文件路径
TEST_FILE = "./workspace/demo.txt"

print("=" * 50)
print("内置工具使用示例 - LLM 调用")
print("=" * 50)

# ========== 1. 创建文件（file_write） ==========
print("\n1. 创建文件 (file_write)")
print("-" * 40)

result = call(
    f"""
请创建一个配置文件：
- 文件路径：{TEST_FILE}
- 内容：应用名称、版本号、调试模式、端口号
使用 file_write 工具。
""",
    profile="default",
    tools=["file_write"]
)

print(f"LLM 输出：{result.output}")

# 查看工具调用过程
print("\n工具调用过程:")
for step in result.thought_chain:
    if step.kind in ["tool_call", "tool_result"]:
        print(f"  [{step.kind}] {step.content[:100]}")


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


# ========== 4. 再次读取查看追加效果 ==========
print("\n4. 再次读取文件")
print("-" * 40)

result = call(
    f"请读取 {TEST_FILE} 展示最终内容",
    profile="default",
    tools=["file_read"]
)

print(f"LLM 输出：{result.output}")


# ========== 5. 修改配置（file_update） ==========
print("\n5. 修改配置 (file_update)")
print("-" * 40)

result = call(
    f"""
请修改 {TEST_FILE} 文件：
- 将调试模式从 true 改为 false
- 将端口号从 8080 改为 3000
使用 file_update 工具，直接指定原文本和新文本，不需要行号。
""",
    profile="default",
    tools=["file_read", "file_update"]
)

print(f"LLM 输出：{result.output}")


# ========== 6. 查看最终内容 ==========
print("\n6. 查看最终文件内容")
print("-" * 40)

result = call(
    f"请读取 {TEST_FILE} 展示最终内容",
    profile="default",
    tools=["file_read"]
)
print(f"LLM 输出：{result.output}")


# ========== 7. 演示更新失败（内容不唯一） ==========
print("\n7. 演示更新失败（内容不唯一）")
print("-" * 40)

result = call(
    f"""
请尝试修改 {TEST_FILE} 文件：
- 将 "DemoApp" 改为 "MyApp"
使用 file_update 工具。（注意：如果文件中出现多次 "DemoApp"，会失败）
""",
    profile="default",
    tools=["file_update"]
)
print(f"LLM 输出：{result.output}")

# 查看工具调用结果
for step in result.thought_chain:
    if step.kind == "tool_result":
        print(f"工具结果：{step.content}")


print("\n" + "=" * 50)
print("示例完成！")
print("=" * 50)
