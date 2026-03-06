#!/usr/bin/env python3
"""
沙盒限制测试

演示文件系统沙盒和 Shell 命令白名单的使用。
"""

from noesis import (
    register_builtin_tools,
    call,
    configure_sandbox,
    get_sandbox_config,
    file_read,
    file_write,
    shell_exec,
)

print("=" * 60)
print("沙盒限制测试")
print("=" * 60)

# 注册内置工具
register_builtin_tools()

# ========== 1. 查看默认沙盒配置 ==========
print("\n1. 默认沙盒配置")
print("-" * 40)

config = get_sandbox_config()
print(f"沙盒启用：{config.enabled}")
print(f"允许访问的目录：{config.allowed_directories}")
print(f"允许的命令：{config.allowed_commands[:5]}...")


# ========== 2. 测试文件系统沙盒 ==========
print("\n2. 测试文件系统沙盒 - 允许workspace 目录")
print("-" * 40)

# 在 workspace 目录内写入文件（应该成功）
result = file_write("./workspace/test.txt", "沙盒测试内容")
print(f"写入 ./workspace/test.txt: {result}")

# 读取文件（应该成功）
result = file_read("./workspace/test.txt")
print(f"读取 ./workspace/test.txt: success={result.get('success')}")


# ========== 3. 测试文件系统沙盒 - 拒绝 workspace 外目录 ==========
print("\n3. 测试文件系统沙盒 - 拒绝 workspace 外目录")
print("-" * 40)

# 尝试写入父目录（应该被拒绝）
result = file_write("./test_outside.txt", "试图写入 workspace 外")
print(f"写入 ./test_outside.txt: {result}")

# 尝试读取 /etc/passwd（应该被拒绝）
result = file_read("/etc/passwd")
print(f"读取 /etc/passwd: {result}")


# ========== 4. 测试 Shell 命令白名单 ==========
print("\n4. 测试 Shell 命令白名单")
print("-" * 40)

# 允许的命令（应该成功）
result = shell_exec("ls workspace/")
print(f"执行 'ls workspace/': success={result.get('success')}")
if result.get("success"):
    print(f"  输出：{result.get('stdout', '')[:100]}")

# 允许的命令（应该成功）
result = shell_exec("pwd")
print(f"执行 'pwd': success={result.get('success')}")

# 不允许的命令（应该被拒绝）
result = shell_exec("whoami")
print(f"执行 'whoami': {result}")

# 危险的命令（应该被拒绝）
result = shell_exec("rm -rf /")
print(f"执行 'rm -rf /': {result}")


# ========== 5. 通过 LLM 调用工具（带沙盒限制） ==========
print("\n5. 通过 LLM 调用工具（带沙盒限制）")
print("-" * 40)

result = call(
    "请在 ./workspace/目录下创建一个名为 llm_test.txt 的文件，内容是'Hello from LLM'",
    profile="default",
    tools=["file_write"]
)
print(f"LLM 调用 file_write: {result.output[:200]}...")

# 查看工具调用过程
print("\n工具调用过程:")
for step in result.thought_chain:
    if step.kind in ["tool_call", "tool_result"]:
        print(f"  [{step.kind}] {step.content[:150]}...")


# ========== 6. 尝试让 LLM 写入 workspace 外（应该被拒绝） ==========
print("\n6. 尝试让 LLM 写入 workspace 外（应该被拒绝）")
print("-" * 40)

result = call(
    "请写入文件 ./outside_workspace.txt，内容是'test'",
    profile="default",
    tools=["file_write"]
)
print(f"LLM 调用 file_write: {result.output[:200]}...")

# 查看工具调用结果
print("\n工具调用结果:")
for step in result.thought_chain:
    if step.kind == "tool_result":
        print(f"  [{step.kind}] {step.content[:200]}...")


print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
