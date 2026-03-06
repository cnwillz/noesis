#!/usr/bin/env python3
"""
Tool Calling 使用示例

展示如何使用 noesis 的工具调用功能。
"""

from noesis import call, register_tool, list_tools


# ============ 步骤 1: 定义工具函数 ============

def get_weather(city: str, unit: str = "celsius") -> str:
    """获取城市天气信息"""
    temp = 25 if unit == "celsius" else 77
    return f"Weather in {city}: Sunny, {temp}°{unit[0].upper()}"


def calculator(expression: str) -> str:
    """计算数学表达式"""
    try:
        # 注意：实际生产环境中需要更安全的表达式求值
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def search_web(query: str, limit: int = 5) -> str:
    """搜索网络信息"""
    return f"Search results for '{query}': Found {limit} results"


# ============ 步骤 2: 注册工具 ============

register_tool("get_weather", get_weather, description="获取城市当前天气")
register_tool("calculator", calculator, description="计算数学表达式")
register_tool("search_web", search_web, description="搜索网络信息")


# ============ 步骤 3: 查看已注册的工具 ============

print("已注册的工具:")
for tool_name in list_tools():
    print(f"  - {tool_name}")

print("\n" + "=" * 50 + "\n")


# ============ 步骤 4: 使用工具调用 LLM ============

examples = [
    ("北京天气怎么样？", ["get_weather"]),
    ("计算 123 + 456 * 2", ["calculator"]),
    ("帮我搜索 Python 异步编程的最新资料", ["search_web"]),
    ("上海天气，然后用计算器计算 100 * 1.8 + 32", ["get_weather", "calculator"]),
]

for prompt, tools in examples:
    print(f"Prompt: {prompt}")
    print(f"Tools: {tools}")
    print("-" * 40)

    # 调用 LLM
    result = call(prompt, profile="default", tools=tools)

    # 查看思维链（包含工具调用过程）
    print("\n思维链:")
    for step in result.thought_chain:
        print(f"[{step.kind}] {step.content[:100]}...")

    print(f"\n最终输出：{result.output}\n")
    print("-" * 40)

print("=" * 50)
print("完成！")
