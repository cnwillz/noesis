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
    file_append,
    file_edit,
    shell_exec,
)


class TestFileRead:
    """测试 file_read"""

    def setup_method(self):
        """创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"
        self.test_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    def teardown_method(self):
        """清理临时文件"""
        self.test_file.unlink()
        Path(self.temp_dir).rmdir()

    def test_read_full_file(self):
        """读取整个文件"""
        result = file_read(str(self.test_file))
        assert result["success"] is True
        assert "line 1" in result["content"]
        assert result["total_lines"] == 5
        assert result["returned_lines"] == 5

    def test_read_with_line_range(self):
        """指定行范围读取"""
        result = file_read(str(self.test_file), start_line=1, end_line=3)
        assert result["success"] is True
        assert result["content"] == "line 2\nline 3\n"
        assert result["returned_lines"] == 2

    def test_read_nonexistent_file(self):
        """读取不存在的文件"""
        result = file_read("/nonexistent/file.txt")
        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_read_directory(self):
        """读取目录（应该失败）"""
        result = file_read(str(self.temp_dir))
        assert result["success"] is False
        assert "不是文件" in result["error"]


class TestFileAppend:
    """测试 file_append"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"

    def teardown_method(self):
        if self.test_file.exists():
            self.test_file.unlink()
        # 使用 shutil.rmtree 清理可能存在的子目录
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_append_to_new_file(self):
        """追加到新文件（自动创建）"""
        result = file_append(str(self.test_file), "hello\n")
        assert result["success"] is True
        assert self.test_file.exists()
        assert self.test_file.read_text(encoding="utf-8") == "hello\n"

    def test_append_to_existing_file(self):
        """追加到已有文件"""
        self.test_file.write_text("existing\n", encoding="utf-8")
        result = file_append(str(self.test_file), "new\n")
        assert result["success"] is True
        content = self.test_file.read_text(encoding="utf-8")
        assert content == "existing\nnew\n"

    def test_append_creates_parent_dirs(self):
        """追加时自动创建父目录"""
        nested_file = Path(self.temp_dir) / "subdir" / "test.txt"
        result = file_append(str(nested_file), "content\n")
        assert result["success"] is True
        assert nested_file.exists()


class TestFileEdit:
    """测试 file_edit"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"

    def teardown_method(self):
        if self.test_file.exists():
            self.test_file.unlink()
        Path(self.temp_dir).rmdir()

    def test_edit_single_occurrence(self):
        """编辑单次出现"""
        self.test_file.write_text("DEBUG = True", encoding="utf-8")
        result = file_edit(str(self.test_file), "DEBUG = True", "DEBUG = False")
        assert result["success"] is True
        assert self.test_file.read_text(encoding="utf-8") == "DEBUG = False"

    def test_edit_multiple_occurrences(self):
        """编辑多次出现（需指定 occurrence）"""
        self.test_file.write_text("a = 1\na = 2\na = 3", encoding="utf-8")
        result = file_edit(str(self.test_file), "a", "b")
        assert result["success"] is False
        assert "出现 3 次" in result["error"]

        # 指定 occurrence
        result = file_edit(str(self.test_file), "a", "b", occurrence=2)
        assert result["success"] is True
        content = self.test_file.read_text(encoding="utf-8")
        assert content == "a = 1\nb = 2\na = 3"

    def test_edit_not_found(self):
        """编辑未找到的文本"""
        self.test_file.write_text("hello world", encoding="utf-8")
        result = file_edit(str(self.test_file), "notfound", "replacement")
        assert result["success"] is False
        assert "未找到" in result["error"]


class TestShellExec:
    """测试 shell_exec"""

    def test_echo_command(self):
        """测试简单命令"""
        result = shell_exec("echo 'hello world'")
        assert result["success"] is True
        assert "hello world" in result["stdout"]
        assert result["returncode"] == 0

    def test_pwd_command(self):
        """测试 pwd 命令"""
        result = shell_exec("pwd")
        assert result["success"] is True
        assert result["returncode"] == 0

    def test_command_with_cwd(self):
        """指定工作目录"""
        result = shell_exec("pwd", cwd="/tmp")
        assert result["success"] is True
        assert "/tmp" in result["stdout"]

    def test_command_with_error(self):
        """测试错误命令"""
        result = shell_exec("exit 1")
        assert result["success"] is True  # 命令执行成功，但返回码非 0
        assert result["returncode"] == 1

    def test_invalid_command(self):
        """测试不存在的命令"""
        result = shell_exec("nonexistent_command_xyz")
        assert result["success"] is True
        assert result["returncode"] != 0
