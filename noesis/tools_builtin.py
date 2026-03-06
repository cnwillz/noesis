"""
内置工具实现

提供文件操作和 shell 执行能力，带有沙盒安全限制。
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List


# ============ 沙盒配置 ============

class SandboxConfig:
    """沙盒配置"""

    # 文件系统沙盒：允许访问的目录列表（白名单）
    # 默认为当前工作目录下的 workspace 子目录
    allowed_directories: List[Path]

    # Shell 命令白名单：允许执行的命令前缀
    # 默认为空，表示不允许任何命令
    allowed_commands: List[str]

    # 是否启用沙盒限制
    enabled: bool = True

    def __init__(self):
        # 默认允许访问的目录
        self.allowed_directories = [
            Path.cwd() / "workspace",
        ]

        # 默认允许的命令（安全命令）
        self.allowed_commands = [
            "ls ",
            "cat ",
            "head ",
            "tail ",
            "wc ",
            "pwd",
            "echo ",
            "mkdir -p ",
            "rm -rf workspace/",
            "touch ",
            "cp ",
            "mv ",
            "find workspace/",
            "grep ",
        ]

    def is_path_allowed(self, path: Path) -> tuple[bool, str]:
        """
        检查路径是否在允许访问的范围内

        Returns:
            (is_allowed, reason) - 是否允许及原因
        """
        if not self.enabled:
            return True, ""

        try:
            resolved = path.expanduser().resolve()
        except Exception as e:
            return False, f"无法解析路径：{e}"

        # 检查是否在允许的目录内
        for allowed_dir in self.allowed_directories:
            try:
                allowed_resolved = allowed_dir.expanduser().resolve()
                # Python 3.9 兼容：使用 os.path.commonpath
                try:
                    # 检查路径是否是允许目录的子目录或就是该目录
                    common = os.path.commonpath([resolved, allowed_resolved])
                    if common == str(allowed_resolved):
                        return True, ""
                except ValueError:
                    # 不同驱动器等情况
                    continue
            except (ValueError, RuntimeError):
                continue

        # 检查是否是允许目录本身（字符串前缀匹配）
        for allowed_dir in self.allowed_directories:
            path_str = str(resolved)
            allowed_str = str(allowed_dir)
            if path_str == allowed_str or path_str.startswith(allowed_str + os.sep):
                return True, ""

        allowed_paths = ", ".join(str(d) for d in self.allowed_directories)
        return False, f"路径不在允许的范围内：{resolved}\n允许的目录：{allowed_paths}"

    def is_command_allowed(self, command: str) -> tuple[bool, str]:
        """
        检查命令是否在白名单内

        Returns:
            (is_allowed, reason) - 是否允许及原因
        """
        if not self.enabled:
            return True, ""

        command_stripped = command.strip()

        # 检查是否匹配任何允许的命令前缀
        for allowed_cmd in self.allowed_commands:
            if command_stripped.startswith(allowed_cmd):
                return True, ""

        allowed_list = ", ".join(f'"{cmd.strip()}"' for cmd in self.allowed_commands[:10])
        if len(self.allowed_commands) > 10:
            allowed_list += f" 等 {len(self.allowed_commands)} 个命令"
        return False, f"命令不在白名单内：{command_stripped}\n允许的命令：{allowed_list}"


# 全局沙盒配置
_sandbox_config = SandboxConfig()


def configure_sandbox(
    allowed_directories: Optional[List[str]] = None,
    allowed_commands: Optional[List[str]] = None,
    enabled: Optional[bool] = None,
):
    """
    配置沙盒参数

    Args:
        allowed_directories: 允许访问的目录列表
        allowed_commands: 允许执行的命令列表（前缀匹配）
        enabled: 是否启用沙盒
    """
    global _sandbox_config

    if allowed_directories is not None:
        _sandbox_config.allowed_directories = [Path(d) for d in allowed_directories]
    if allowed_commands is not None:
        _sandbox_config.allowed_commands = allowed_commands
    if enabled is not None:
        _sandbox_config.enabled = enabled


def get_sandbox_config() -> SandboxConfig:
    """获取沙盒配置"""
    return _sandbox_config


class FileTool:
    """文件操作工具（带沙盒限制）"""

    def _check_sandbox(self, path: Path) -> tuple[bool, str]:
        """检查路径是否在沙盒允许范围内"""
        return _sandbox_config.is_path_allowed(path)

    def read(self, path: str, start_line: int = 0, end_line: Optional[int] = None) -> dict:
        """读取文件内容"""
        try:
            file_path = Path(path).expanduser()

            # 沙盒检查
            is_allowed, reason = self._check_sandbox(file_path)
            if not is_allowed:
                return {"success": False, "error": f"沙盒限制：{reason}"}

            resolved_path = file_path.resolve()

            if not resolved_path.exists():
                return {"success": False, "error": f"文件不存在：{path}"}

            if not resolved_path.is_file():
                return {"success": False, "error": f"不是文件：{path}"}

            with open(resolved_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            selected_lines = lines[start_line:end_line]
            content = "".join(selected_lines)

            return {
                "success": True,
                "content": content,
                "path": str(resolved_path),
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
            file_path = Path(path).expanduser()

            # 沙盒检查
            is_allowed, reason = self._check_sandbox(file_path)
            if not is_allowed:
                return {"success": False, "error": f"沙盒限制：{reason}"}

            resolved_path = file_path.resolve()
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(resolved_path),
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
            file_path = Path(path).expanduser()

            # 沙盒检查
            is_allowed, reason = self._check_sandbox(file_path)
            if not is_allowed:
                return {"success": False, "error": f"沙盒限制：{reason}"}

            resolved_path = file_path.resolve()
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            with open(resolved_path, "a", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(resolved_path),
                "bytes_written": len(content.encode("utf-8")),
                "operation": "append"
            }

        except PermissionError:
            return {"success": False, "error": f"无权限写入：{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update(self, path: str, changes: list[dict]) -> dict:
        """
        更新文件内容（基于内容的唯一匹配替换）

        不需要指定行号，通过 old_text 在文件中查找并替换为 new_text。
        如果 old_text 出现多次或不存在，将返回错误。

        Args:
            path: 文件路径
            changes: 变更列表，每组包含:
                - old_text: 原文本（可以是多行，必须精确匹配且唯一）
                - new_text: 新的文本

        Example:
            file_update("config.py", changes=[
                {"old_text": "DEBUG = True", "new_text": "DEBUG = False"},
                {"old_text": "PORT = 8080", "new_text": "PORT = 3000"},
            ])

            # 多行替换
            file_update("app.py", changes=[{
                "old_text": "def hello():\n    print('Hi')",
                "new_text": "def hello():\n    print('Hello')"
            }])
        """
        try:
            file_path = Path(path).expanduser()

            # 沙盒检查
            is_allowed, reason = self._check_sandbox(file_path)
            if not is_allowed:
                return {"success": False, "error": f"沙盒限制：{reason}"}

            resolved_path = file_path.resolve()

            if not resolved_path.exists():
                return {"success": False, "error": f"文件不存在：{path}"}

            with open(resolved_path, "r", encoding="utf-8") as f:
                content = f.read()

            applied_changes = []
            failed_changes = []

            for change in changes:
                old_text = change.get("old_text")
                new_text = change.get("new_text")

                if old_text is None or new_text is None:
                    failed_changes.append({
                        "change": change,
                        "error": "缺少 old_text 或 new_text 参数"
                    })
                    continue

                # 查找 old_text 在文件中的出现次数
                count = content.count(old_text)

                if count == 0:
                    failed_changes.append({
                        "change": change,
                        "error": f"未找到匹配的内容：{old_text[:50]}..." if len(old_text) > 50 else f"未找到匹配的内容：{old_text}"
                    })
                    continue

                if count > 1:
                    failed_changes.append({
                        "change": change,
                        "error": f"内容出现 {count} 次，必须唯一匹配：{old_text[:50]}..." if len(old_text) > 50 else f"内容出现 {count} 次，必须唯一匹配：{old_text}"
                    })
                    continue

                # 唯一匹配，执行替换
                content = content.replace(old_text, new_text, 1)

                applied_changes.append({
                    "old_text": old_text,
                    "new_text": new_text,
                    "matched": True
                })

            # 如果有成功的变更，写入文件
            if applied_changes:
                with open(resolved_path, "w", encoding="utf-8") as f:
                    f.write(content)

            result = {
                "success": len(failed_changes) == 0,
                "path": str(resolved_path),
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
    """Shell 命令执行工具（带白名单限制）"""

    def _check_sandbox(self, command: str) -> tuple[bool, str]:
        """检查命令是否在白名单内"""
        return _sandbox_config.is_command_allowed(command)

    def exec(self, command: str, cwd: Optional[str] = None, timeout: int = 300) -> dict:
        """执行 shell 命令"""
        try:
            # 白名单检查
            is_allowed, reason = self._check_sandbox(command)
            if not is_allowed:
                return {"success": False, "error": f"沙盒限制：{reason}"}

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


# file_edit 是 file_update 的别名
file_edit = file_update


def shell_exec(command: str, cwd: Optional[str] = None, timeout: int = 300) -> dict:
    """执行 shell 命令"""
    return _shell_tool.exec(command, cwd, timeout)


# 工具元数据（用于注册）
TOOLS_BUILTIN = {
    "file_read": {
        "func": file_read,
        "description": "读取文件内容，支持指定行范围（沙盒限制：仅限 workspace 目录）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径（必须在 workspace 目录内）"},
                "start_line": {"type": "integer", "description": "起始行号", "default": 0},
                "end_line": {"type": "integer", "description": "结束行号（不包含）"}
            },
            "required": ["path"]
        }
    },
    "file_write": {
        "func": file_write,
        "description": "写入文件（覆盖模式，沙盒限制：仅限 workspace 目录）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径（必须在 workspace 目录内）"},
                "content": {"type": "string", "description": "要写入的内容"}
            },
            "required": ["path", "content"]
        }
    },
    "file_append": {
        "func": file_append,
        "description": "追加内容到文件末尾（文件不存在则创建，沙盒限制：仅限 workspace 目录）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径（必须在 workspace 目录内）"},
                "content": {"type": "string", "description": "要追加的内容"}
            },
            "required": ["path", "content"]
        }
    },
    "file_update": {
        "func": file_update,
        "description": "更新文件内容（基于内容的唯一匹配替换，沙盒限制：仅限 workspace 目录）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径（必须在 workspace 目录内）"},
                "changes": {
                    "type": "array",
                    "description": "变更列表，每组包含 old_text, new_text",
                    "items": {
                        "type": "object",
                        "properties": {
                            "old_text": {"type": "string", "description": "原文本（可以是多行，必须精确匹配且在文件中唯一）"},
                            "new_text": {"type": "string", "description": "新的文本"}
                        },
                        "required": ["old_text", "new_text"]
                    }
                }
            },
            "required": ["path", "changes"]
        }
    },
    "shell_exec": {
        "func": shell_exec,
        "description": "执行 shell 命令（沙盒限制：命令必须在白名单内）",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令（必须在白名单内）"},
                "cwd": {"type": "string", "description": "工作目录"},
                "timeout": {"type": "integer", "description": "超时时间（秒）", "default": 300}
            },
            "required": ["command"]
        }
    }
}


def register_builtin_tools():
    """
    注册所有内置工具

    沙盒安全限制：
    - 文件操作：仅限 workspace 目录内
    - Shell 命令：仅限白名单内的命令

    自定义沙盒配置：
        from noesis import configure_sandbox

        # 添加允许的目录
        configure_sandbox(allowed_directories=["./workspace", "./tmp"])

        # 添加允许的命令
        configure_sandbox(allowed_commands=["ls ", "cat ", "python3 "])

        # 禁用沙盒（不推荐）
        configure_sandbox(enabled=False)
    """
    from .tools import register_tool

    for name, tool in TOOLS_BUILTIN.items():
        register_tool(
            name,
            tool["func"],
            description=tool["description"],
            parameters=tool["parameters"]
        )
