"""
Shell 执行工具
"""

import subprocess
from typing import Optional

from ..tools import ToolRegistry


def register_shell_tools(registry: ToolRegistry):
    """注册 Shell 执行工具"""

    @registry.register(
        name="run_shell",
        description="执行 Shell 命令",
    )
    def run_shell(
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        执行 Shell 命令

        Args:
            command: 命令内容
            cwd: 工作目录
            timeout: 超时时间（秒）

        Returns:
            包含 stdout, stderr, returncode 的字典
        """
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )

            return {
                "ok": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"Command timed out after {timeout}s",
                "returncode": -1,
            }

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "returncode": -1,
            }

    @registry.register(
        name="run_python",
        description="执行 Python 代码或脚本",
    )
    def run_python(code: str, timeout: Optional[int] = 60) -> dict:
        """
        执行 Python 代码

        Args:
            code: Python 代码
            timeout: 超时时间（秒）

        Returns:
            执行结果
        """
        return run_shell(
            f"python3 -c '{code.replace("'", "'\\''")}'",
            timeout=timeout,
        )

    @registry.register(
        name="check_command",
        description="检查命令是否存在",
    )
    def check_command(command: str) -> bool:
        """检查命令是否在 PATH 中"""
        import shutil
        return shutil.which(command) is not None

    @registry.register(
        name="get_env",
        description="获取环境变量",
    )
    def get_env(name: str) -> Optional[str]:
        """获取环境变量值"""
        import os
        return os.environ.get(name)

    @registry.register(
        name="set_env",
        description="设置环境变量（当前进程）",
    )
    def set_env(name: str, value: str) -> dict:
        """设置环境变量"""
        import os
        os.environ[name] = value
        return {"ok": True, "name": name, "value": value}

    @registry.register(
        name="which",
        description="查找命令的完整路径",
    )
    def which(command: str) -> Optional[str]:
        """查找命令路径"""
        import shutil
        return shutil.which(command)

    @registry.register(
        name="pwd",
        description="获取当前工作目录",
    )
    def pwd() -> str:
        """获取当前工作目录"""
        import os
        return os.getcwd()

    @registry.register(
        name="cd",
        description="切换工作目录",
    )
    def cd(path: str) -> dict:
        """切换工作目录"""
        import os
        try:
            os.chdir(path)
            return {"ok": True, "cwd": os.getcwd()}
        except Exception as e:
            return {"ok": False, "error": str(e)}
