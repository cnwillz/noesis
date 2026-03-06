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
        """读取文件内容"""
        try:
            file_path = Path(path).expanduser().resolve()

            if not file_path.exists():
                return {"success": False, "error": f"文件不存在：{path}"}

            if not file_path.is_file():
                return {"success": False, "error": f"不是文件：{path}"}

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            selected_lines = lines[start_line:end_line]
            content = "".join(selected_lines)

            return {
                "success": True,
                "content": content,
                "path": str(file_path),
                "total_lines": len(lines),
                "returned_lines": len(selected_lines),
            }

        except PermissionError:
            return {"success": False, "error": f"无权限读取：{path}"}
        except UnicodeDecodeError:
            return {"success": False, "error": f"文件编码不支持：{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write(self, path: str, content: str) -> dict:
        """写入文件（覆盖模式）"""
        try:
            file_path = Path(path).expanduser().resolve()
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(file_path),
                "bytes_written": len(content.encode("utf-8")),
                "operation": "write"
            }

        except PermissionError:
            return {"success": False, "error": f"无权限写入：{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def append(self, path: str, content: str) -> dict:
        """追加内容到文件末尾"""
        try:
            file_path = Path(path).expanduser().resolve()
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

    def update(self, path: str, changes: list[dict]) -> dict:
        """
        更新文件指定行（支持多组更新）

        Args:
            path: 文件路径
            changes: 变更列表，每组包含:
                - line: 行号（从 0 开始）
                - old_text: 原整行文本（必须精确匹配，不含换行符）
                - new_text: 新的整行文本（不含换行符）

        Example:
            file_update("config.py", changes=[
                {"line": 5, "old_text": "DEBUG = True", "new_text": "DEBUG = False"},
                {"line": 10, "old_text": "PORT = 8080", "new_text": "PORT = 3000"},
            ])
        """
        try:
            file_path = Path(path).expanduser().resolve()

            if not file_path.exists():
                return {"success": False, "error": f"文件不存在：{path}"}

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            applied_changes = []
            failed_changes = []

            for change in changes:
                line_num = change.get("line")
                old_text = change.get("old_text")
                new_text = change.get("new_text")

                if line_num is None or old_text is None or new_text is None:
                    failed_changes.append({
                        "change": change,
                        "error": "缺少 line, old_text 或 new_text 参数"
                    })
                    continue

                if line_num < 0 or line_num >= len(lines):
                    failed_changes.append({
                        "change": change,
                        "error": f"行号 {line_num} 超出范围 (0-{len(lines)-1})"
                    })
                    continue

                # 移除换行符进行比较
                current_line = lines[line_num].rstrip("\n")
                old_text_cmp = old_text.rstrip("\n")

                if current_line != old_text_cmp:
                    failed_changes.append({
                        "change": change,
                        "error": f"第 {line_num} 行内容不匹配",
                        "expected": old_text_cmp,
                        "actual": current_line
                    })
                    continue

                # 执行更新（保留换行符）
                if lines[line_num].endswith("\n"):
                    lines[line_num] = new_text + "\n"
                else:
                    lines[line_num] = new_text

                applied_changes.append({
                    "line": line_num,
                    "old_text": old_text_cmp,
                    "new_text": new_text
                })

            # 如果有成功的变更，写入文件
            if applied_changes:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)

            result = {
                "success": len(failed_changes) == 0,
                "path": str(file_path),
                "changes_applied": len(applied_changes),
                "changes_failed": len(failed_changes),
                "applied": applied_changes
            }

            if failed_changes:
                result["failed"] = failed_changes

            return result

        except PermissionError:
            return {"success": False, "error": f"无权限写入：{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ShellTool:
    """Shell 命令执行工具"""

    def exec(self, command: str, cwd: Optional[str] = None, timeout: int = 300) -> dict:
        """执行 shell 命令"""
        try:
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


# 导出为工具函数
def file_read(path: str, start_line: int = 0, end_line: Optional[int] = None) -> dict:
    """读取文件内容"""
    return _file_tool.read(path, start_line, end_line)


def file_write(path: str, content: str) -> dict:
    """写入文件（覆盖模式）"""
    return _file_tool.write(path, content)


def file_append(path: str, content: str) -> dict:
    """追加内容到文件末尾"""
    return _file_tool.append(path, content)


def file_update(path: str, changes: list[dict]) -> dict:
    """更新文件指定行"""
    return _file_tool.update(path, changes)


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
    "file_write": {
        "func": file_write,
        "description": "写入文件（覆盖模式）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"}
            },
            "required": ["path", "content"]
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
    "file_update": {
        "func": file_update,
        "description": "更新文件指定行（需要 old_text 精确匹配整行）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "changes": {
                    "type": "array",
                    "description": "变更列表，每组包含 line, old_text, new_text",
                    "items": {
                        "type": "object",
                        "properties": {
                            "line": {"type": "integer", "description": "行号（从 0 开始）"},
                            "old_text": {"type": "string", "description": "原整行文本（必须精确匹配）"},
                            "new_text": {"type": "string", "description": "新的整行文本"}
                        },
                        "required": ["line", "old_text", "new_text"]
                    }
                }
            },
            "required": ["path", "changes"]
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
    """注册所有内置工具"""
    from .tools import register_tool

    for name, tool in TOOLS_BUILTIN.items():
        register_tool(
            name,
            tool["func"],
            description=tool["description"],
            parameters=tool["parameters"]
        )
