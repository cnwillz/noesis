"""
内置工具测试
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path

from noesis.tools_builtin import (
    FileTool,
    ShellTool,
    file_read,
    file_write,
    file_append,
    file_update,
    shell_exec,
    configure_sandbox,
)


class TestFileRead:
    """测试 file_read"""

    def setup_method(self):
        # 使用 workspace 目录内的临时文件
        self.workspace_dir = Path("./workspace/test_tmp")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.test_file = self.workspace_dir / "test.txt"
        self.test_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    def teardown_method(self):
        shutil.rmtree(self.workspace_dir, ignore_errors=True)

    def test_read_full_file(self):
        result = file_read(str(self.test_file))
        assert result["success"] is True
        assert "line 1" in result["content"]
        assert result["total_lines"] == 5

    def test_read_with_line_range(self):
        result = file_read(str(self.test_file), start_line=1, end_line=3)
        assert result["success"] is True
        assert result["content"] == "line 2\nline 3\n"

    def test_read_nonexistent_file(self):
        result = file_read(str(self.workspace_dir / "nonexistent.txt"))
        assert result["success"] is False
        assert "不存在" in result["error"]


class TestFileWrite:
    """测试 file_write（覆盖模式）"""

    def setup_method(self):
        # 使用 workspace 目录内的临时文件
        self.workspace_dir = Path("./workspace/test_tmp")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.test_file = self.workspace_dir / "test.txt"

    def teardown_method(self):
        shutil.rmtree(self.workspace_dir, ignore_errors=True)

    def test_write_new_file(self):
        result = file_write(str(self.test_file), "hello\n")
        assert result["success"] is True
        assert self.test_file.read_text(encoding="utf-8") == "hello\n"

    def test_write_overwrites(self):
        self.test_file.write_text("existing content\n", encoding="utf-8")
        result = file_write(str(self.test_file), "new content\n")
        assert result["success"] is True
        assert self.test_file.read_text(encoding="utf-8") == "new content\n"

    def test_write_creates_parent_dirs(self):
        nested_file = self.workspace_dir / "subdir" / "test.txt"
        result = file_write(str(nested_file), "content\n")
        assert result["success"] is True
        assert nested_file.exists()


class TestFileAppend:
    """测试 file_append"""

    def setup_method(self):
        # 使用 workspace 目录内的临时文件
        self.workspace_dir = Path("./workspace/test_tmp")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.test_file = self.workspace_dir / "test.txt"

    def teardown_method(self):
        shutil.rmtree(self.workspace_dir, ignore_errors=True)

    def test_append_to_new_file(self):
        result = file_append(str(self.test_file), "hello\n")
        assert result["success"] is True
        assert self.test_file.read_text(encoding="utf-8") == "hello\n"

    def test_append_to_existing_file(self):
        self.test_file.write_text("existing\n", encoding="utf-8")
        result = file_append(str(self.test_file), "new\n")
        assert result["success"] is True
        assert self.test_file.read_text(encoding="utf-8") == "existing\nnew\n"


class TestFileUpdate:
    """测试 file_update（基于内容的唯一匹配替换）"""

    def setup_method(self):
        # 使用 workspace 目录内的临时文件
        self.workspace_dir = Path("./workspace/test_tmp")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.test_file = self.workspace_dir / "test.txt"

    def teardown_method(self):
        shutil.rmtree(self.workspace_dir, ignore_errors=True)

    def test_update_single_line(self):
        """测试单行替换"""
        self.test_file.write_text("DEBUG = True\nPORT = 8080\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"old_text": "DEBUG = True", "new_text": "DEBUG = False"}
        ])
        assert result["success"] is True
        assert result["changes_applied"] == 1
        assert self.test_file.read_text(encoding="utf-8") == "DEBUG = False\nPORT = 8080\n"

    def test_update_multiple_changes(self):
        """测试多组替换"""
        self.test_file.write_text("DEBUG = True\nPORT = 8080\nHOST = localhost\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"old_text": "DEBUG = True", "new_text": "DEBUG = False"},
            {"old_text": "PORT = 8080", "new_text": "PORT = 3000"}
        ])
        assert result["success"] is True
        assert result["changes_applied"] == 2
        content = self.test_file.read_text(encoding="utf-8")
        assert "DEBUG = False" in content
        assert "PORT = 3000" in content

    def test_update_multiline(self):
        """测试多行文本替换"""
        self.test_file.write_text("def hello():\n    print('Hi')\n\ndef goodbye():\n    pass\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"old_text": "def hello():\n    print('Hi')", "new_text": "def hello():\n    print('Hello')"}
        ])
        assert result["success"] is True
        content = self.test_file.read_text(encoding="utf-8")
        assert "print('Hello')" in content
        assert "print('Hi')" not in content

    def test_update_not_found(self):
        """测试未找到匹配内容"""
        self.test_file.write_text("DEBUG = True\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"old_text": "DEBUG = False", "new_text": "DEBUG = True"}
        ])
        assert result["success"] is False
        assert "未找到" in result["failed"][0]["error"]

    def test_update_not_unique(self):
        """测试内容不唯一"""
        self.test_file.write_text("DEBUG = True\nDEBUG = True\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"old_text": "DEBUG = True", "new_text": "DEBUG = False"}
        ])
        assert result["success"] is False
        assert "唯一" in result["failed"][0]["error"] or "出现" in result["failed"][0]["error"]

    def test_update_missing_params(self):
        """测试缺少必要参数"""
        self.test_file.write_text("content\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"new_text": "something"}  # 缺少 old_text
        ])
        assert result["success"] is False
        assert "缺少" in result["failed"][0]["error"]


class TestShellExec:
    """测试 shell_exec"""

    def setup_method(self):
        # 配置沙盒允许测试命令
        configure_sandbox(allowed_commands=[
            "echo ",
            "pwd",
            "ls ",
            "exit ",
        ])

    def test_echo_command(self):
        result = shell_exec("echo 'hello world'")
        assert result["success"] is True
        assert "hello world" in result["stdout"]
        assert result["returncode"] == 0

    def test_pwd_command(self):
        result = shell_exec("pwd")
        assert result["success"] is True
        assert result["returncode"] == 0

    def test_command_with_cwd(self):
        result = shell_exec("pwd", cwd="/tmp")
        assert result["success"] is True
        assert "/tmp" in result["stdout"]

    def test_command_with_error(self):
        result = shell_exec("exit 1")
        assert result["success"] is True
        assert result["returncode"] == 1


class TestSandboxRestrictions:
    """测试沙盒限制"""

    def test_file_read_outside_workspace(self):
        """测试读取 workspace 外文件被拒绝"""
        result = file_read("/etc/passwd")
        assert result["success"] is False
        assert "沙盒限制" in result["error"]

    def test_file_write_outside_workspace(self):
        """测试写入 workspace 外文件被拒绝"""
        result = file_write("./test_outside.txt", "content")
        assert result["success"] is False
        assert "沙盒限制" in result["error"]

    def test_shell_command_not_in_whitelist(self):
        """测试执行不在白名单的命令被拒绝"""
        # 恢复默认白名单
        configure_sandbox(allowed_commands=["ls ", "pwd"])
        result = shell_exec("whoami")
        assert result["success"] is False
        assert "沙盒限制" in result["error"]

    def test_shell_command_in_whitelist(self):
        """测试执行白名单内的命令成功"""
        configure_sandbox(allowed_commands=["ls "])
        result = shell_exec("ls workspace/")
        assert result["success"] is True

    def test_sandbox_disabled(self):
        """测试禁用沙盒后可以访问任意路径"""
        configure_sandbox(enabled=False)
        result = file_write("./test_outside_sandbox.txt", "content")
        assert result["success"] is True
        # 清理
        Path("./test_outside_sandbox.txt").unlink(missing_ok=True)
        # 恢复沙盒
        configure_sandbox(enabled=True)
