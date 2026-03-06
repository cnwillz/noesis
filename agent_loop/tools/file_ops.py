"""
文件操作工具
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from ..tools import ToolRegistry, register_tool


def register_file_tools(registry: ToolRegistry):
    """注册文件操作工具"""

    @registry.register(
        name="read_file",
        description="读取文件内容",
    )
    def read_file(path: str) -> str:
        """读取文件并返回内容"""
        file_path = Path(path).expanduser()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return file_path.read_text(encoding="utf-8")

    @registry.register(
        name="write_file",
        description="写入文件（覆盖原有内容）",
    )
    def write_file(path: str, content: str) -> dict:
        """写入文件内容"""
        file_path = Path(path).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(path), "bytes": len(content)}

    @registry.register(
        name="append_file",
        description="追加内容到文件末尾",
    )
    def append_file(path: str, content: str) -> dict:
        """追加内容到文件"""
        file_path = Path(path).expanduser()
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": str(path), "bytes_added": len(content)}

    @registry.register(
        name="edit_file",
        description="编辑文件（查找并替换内容）",
    )
    def edit_file(path: str, old: str, new: str) -> dict:
        """编辑文件内容"""
        file_path = Path(path).expanduser()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = file_path.read_text(encoding="utf-8")
        if old not in content:
            raise ValueError(f"Old string not found in file: {old[:50]}...")

        new_content = content.replace(old, new, 1)
        file_path.write_text(new_content, encoding="utf-8")

        # 计算 diff 统计
        old_lines = old.count("\n") + 1
        new_lines = new.count("\n") + 1

        return {
            "ok": True,
            "path": str(path),
            "lines_added": new_lines,
            "lines_removed": old_lines,
        }

    @registry.register(
        name="delete_file",
        description="删除文件",
    )
    def delete_file(path: str) -> dict:
        """删除文件"""
        file_path = Path(path).expanduser()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        file_path.unlink()
        return {"ok": True, "path": str(path)}

    @registry.register(
        name="create_dir",
        description="创建目录",
    )
    def create_dir(path: str) -> dict:
        """创建目录"""
        dir_path = Path(path).expanduser()
        dir_path.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(path)}

    @registry.register(
        name="list_dir",
        description="列出目录内容",
    )
    def list_dir(path: str) -> list[str]:
        """列出目录内容"""
        dir_path = Path(path).expanduser()
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return [str(p.name) for p in dir_path.iterdir()]

    @registry.register(
        name="move_file",
        description="移动/重命名文件",
    )
    def move_file(src: str, dst: str) -> dict:
        """移动或重命名文件"""
        src_path = Path(src).expanduser()
        if not src_path.exists():
            raise FileNotFoundError(f"File not found: {src}")
        dst_path = Path(dst).expanduser()
        shutil.move(str(src_path), str(dst_path))
        return {"ok": True, "from": str(src), "to": str(dst)}

    @registry.register(
        name="copy_file",
        description="复制文件",
    )
    def copy_file(src: str, dst: str) -> dict:
        """复制文件"""
        src_path = Path(src).expanduser()
        if not src_path.exists():
            raise FileNotFoundError(f"File not found: {src}")
        dst_path = Path(dst).expanduser()
        shutil.copy2(str(src_path), str(dst_path))
        return {"ok": True, "from": str(src), "to": str(dst)}

    @registry.register(
        name="file_exists",
        description="检查文件是否存在",
    )
    def file_exists(path: str) -> bool:
        """检查文件是否存在"""
        return Path(path).expanduser().exists()

    @registry.register(
        name="get_file_info",
        description="获取文件信息（大小、修改时间等）",
    )
    def get_file_info(path: str) -> dict:
        """获取文件信息"""
        file_path = Path(path).expanduser()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        stat = file_path.stat()
        return {
            "path": str(path),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir(),
        }


# 导出装饰器便捷用法
read_file = register_tool(name="read_file", description="读取文件内容")(lambda path: Path(path).read_text())
write_file = register_tool(name="write_file", description="写入文件")(lambda path, content: Path(path).write_text(content))
