"""
内置工具实现

提供文件操作和 shell 执行能力。
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


class FileTool:
    """文件操作工具"""

    def read(self, path: str, start_line: int = 0, end_line: Optional[int] = None) -> dict:
        """
        读取文件内容

        Args:
            path: 文件路径
            start_line: 起始行号（从 0 开始）
            end_line: 结束行号（不包含），None 表示读到末尾

        Returns:
            包含文件内容的字典
        """
        try:
            file_path = Path(path).expanduser().resolve()

            if not file_path.exists():
                return {"success": False, "error": f"文件不存在：{path}"}

            if not file_path.is_file():
                return {"success": False, "error": f"不是文件：{path}"}

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 截取指定行范围
            selected_lines = lines[start_line:end_line]
            content = "".join(selected_lines)

            return {
                "success": True,
                "content": content,
                "path": str(file_path),
                "total_lines": len(lines),
                "returned_lines": len(selected_lines),
                "start_line": start_line,
                "end_line": end_line or len(lines)
            }

        except PermissionError:
            return {"success": False, "error": f"无权限读取：{path}"}
        except UnicodeDecodeError:
            return {"success": False, "error": f"文件编码不支持：{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def append(self, path: str, content: str) -> dict:
        """
        追加内容到文件末尾（文件不存在则创建）

        Args:
            path: 文件路径
            content: 要追加的内容

        Returns:
            操作结果
        """
        try:
            file_path = Path(path).expanduser().resolve()

            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(file_path),
                "bytes_written": len(content.encode("utf-8")),
                "operation": "append"
            }

        except PermissionError:
            return {"success": False, "error": f"无权限写入：{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def edit(self, path: str, old_text: str, new_text: str, occurrence: int = 1) -> dict:
        """
        精确编辑文件内容

        Args:
            path: 文件路径
            old_text: 要替换的原文本
            new_text: 新的文本内容
            occurrence: 替换第几次出现（默认 1）

        Returns:
            操作结果
        """
        try:
            file_path = Path(path).expanduser().resolve()

            if not file_path.exists():
                return {"success": False, "error": f"文件不存在：{path}"}

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找所有出现位置
            matches = []
            start = 0
            while True:
                pos = content.find(old_text, start)
                if pos == -1:
                    break
                matches.append(pos)
                start = pos + 1

            if not matches:
                return {
                    "success": False,
                    "error": "未找到指定的文本内容",
                    "hint": "请检查 old_text 是否与文件内容精确匹配"
                }

            if len(matches) > 1 and occurrence == 1:
                return {
                    "success": False,
                    "error": f"文本出现 {len(matches)} 次，请指定 occurrence 参数"
                }

            if occurrence < 1 or occurrence > len(matches):
                return {
                    "success": False,
                    "error": f"occurrence 值超出范围 (1-{len(matches)})"
                }

            # 执行替换
            target_pos = matches[occurrence - 1]
            new_content = content[:target_pos] + new_text + content[target_pos + len(old_text):]

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "success": True,
                "path": str(file_path),
                "old_text_length": len(old_text),
                "new_text_length": len(new_text),
                "occurrence_replaced": occurrence,
                "total_matches": len(matches)
            }

        except PermissionError:
            return {"success": False, "error": f"无权限写入：{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ShellTool:
    """Shell 命令执行工具"""

    def exec(self, command: str, cwd: Optional[str] = None, timeout: int = 300) -> dict:
        """
        执行 shell 命令

        Args:
            command: 要执行的命令
            cwd: 工作目录（可选）
            timeout: 超时时间（秒），默认 300 秒

        Returns:
            执行结果
        """
        try:
            # 解析命令（支持简单的管道）
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": True,
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "cwd": cwd or os.getcwd()
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"命令执行超时（{timeout}秒）",
                "command": command
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# 单例实例
_file_tool = FileTool()
_shell_tool = ShellTool()


# 导出为工具函数（便于注册）
def file_read(path: str, start_line: int = 0, end_line: Optional[int] = None) -> dict:
    """读取文件内容"""
    return _file_tool.read(path, start_line, end_line)


def file_append(path: str, content: str) -> dict:
    """追加内容到文件末尾"""
    return _file_tool.append(path, content)


def file_edit(path: str, old_text: str, new_text: str, occurrence: int = 1) -> dict:
    """精确编辑文件内容"""
    return _file_tool.edit(path, old_text, new_text, occurrence)


def shell_exec(command: str, cwd: Optional[str] = None, timeout: int = 300) -> dict:
    """执行 shell 命令"""
    return _shell_tool.exec(command, cwd, timeout)


# 工具元数据（用于注册）
TOOLS_BUILTIN = {
    "file_read": {
        "func": file_read,
        "description": "读取文件内容，支持指定行范围",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "start_line": {"type": "integer", "description": "起始行号", "default": 0},
                "end_line": {"type": "integer", "description": "结束行号（不包含）"}
            },
            "required": ["path"]
        }
    },
    "file_append": {
        "func": file_append,
        "description": "追加内容到文件末尾（文件不存在则创建）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要追加的内容"}
            },
            "required": ["path", "content"]
        }
    },
    "file_edit": {
        "func": file_edit,
        "description": "精确编辑文件内容，需要指定原文本进行替换",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "old_text": {"type": "string", "description": "要替换的原文本"},
                "new_text": {"type": "string", "description": "新的文本内容"},
                "occurrence": {"type": "integer", "description": "替换第几次出现", "default": 1}
            },
            "required": ["path", "old_text", "new_text"]
        }
    },
    "shell_exec": {
        "func": shell_exec,
        "description": "执行 shell 命令",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"},
                "cwd": {"type": "string", "description": "工作目录"},
                "timeout": {"type": "integer", "description": "超时时间（秒）", "default": 300}
            },
            "required": ["command"]
        }
    }
}


def register_builtin_tools():
    """
    注册所有内置工具到全局工具注册表

    Usage:
        from noesis import register_builtin_tools
        register_builtin_tools()

        # 现在可以使用内置工具
        result = call("读取文件", tools=["file_read"])
    """
    from .tools import register_tool

    for name, tool in TOOLS_BUILTIN.items():
        register_tool(
            name,
            tool["func"],
            description=tool["description"],
            parameters=tool["parameters"]
        )
