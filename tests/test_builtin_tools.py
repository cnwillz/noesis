"""
内置工具测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from noesis.tools_builtin import (
    FileTool,
    ShellTool,
    file_read,
    file_write,
    file_append,
    file_update,
    shell_exec,
)


class TestFileRead:
    """测试 file_read"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"
        self.test_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

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
        result = file_read("/nonexistent/file.txt")
        assert result["success"] is False
        assert "不存在" in result["error"]


class TestFileWrite:
    """测试 file_write（覆盖模式）"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

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
        nested_file = Path(self.temp_dir) / "subdir" / "test.txt"
        result = file_write(str(nested_file), "content\n")
        assert result["success"] is True
        assert nested_file.exists()


class TestFileAppend:
    """测试 file_append"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

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
    """测试 file_update"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_update_single_line(self):
        self.test_file.write_text("DEBUG = True\nPORT = 8080\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"line": 0, "old_text": "DEBUG = True", "new_text": "DEBUG = False"}
        ])
        assert result["success"] is True
        assert result["changes_applied"] == 1
        assert self.test_file.read_text(encoding="utf-8") == "DEBUG = False\nPORT = 8080\n"

    def test_update_multiple_lines(self):
        self.test_file.write_text("DEBUG = True\nPORT = 8080\nHOST = localhost\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"line": 0, "old_text": "DEBUG = True", "new_text": "DEBUG = False"},
            {"line": 1, "old_text": "PORT = 8080", "new_text": "PORT = 3000"}
        ])
        assert result["success"] is True
        assert result["changes_applied"] == 2
        content = self.test_file.read_text(encoding="utf-8")
        assert "DEBUG = False" in content
        assert "PORT = 3000" in content

    def test_update_mismatch(self):
        self.test_file.write_text("DEBUG = True\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"line": 0, "old_text": "DEBUG = False", "new_text": "DEBUG = True"}
        ])
        assert result["success"] is False
        assert "不匹配" in result["failed"][0]["error"]

    def test_update_out_of_range(self):
        self.test_file.write_text("line 1\nline 2\n", encoding="utf-8")
        result = file_update(str(self.test_file), changes=[
            {"line": 10, "old_text": "test", "new_text": "test"}
        ])
        assert result["success"] is False
        assert "超出范围" in result["failed"][0]["error"]


class TestShellExec:
    """测试 shell_exec"""

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
