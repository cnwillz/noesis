"""
共识管理器

负责读取、写入、版本控制共识文件。
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


class ConsensusManager:
    """
    共识文件管理器

    功能:
    - 读取共识
    - 写入共识（带备份）
    - 版本历史
    """

    def __init__(self, consensus_path: str):
        self.path = Path(consensus_path).expanduser().resolve()
        self.backup_path = self.path.with_suffix(self.path.suffix + ".bak")
        self.history_dir = self.path.parent / "consensus_history"

    def read(self) -> str:
        """读取共识内容"""
        if not self.path.exists():
            return self._create_initial_consensus()
        return self.path.read_text(encoding="utf-8")

    def _create_initial_consensus(self) -> str:
        """创建初始共识文件"""
        initial_content = """# Auto Company Consensus

## Last Updated
{timestamp}

## Current Phase
Day 0 - Initialization

## What We Did This Cycle
- 初始化共识文件

## Key Decisions Made
- 无

## Active Projects
- 无

## Next Action
探索产品方向，进行市场调研

## Company State
- Product: TBD
- Tech Stack: TBD
- Revenue: $0
- Users: 0

## Open Questions
- 我们要解决什么问题？
- 目标用户是谁？
""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(initial_content, encoding="utf-8")
        return initial_content

    def write(self, content: str) -> dict:
        """
        写入共识内容（带备份）

        Returns:
            写入结果
        """
        # 备份现有内容
        if self.path.exists():
            shutil.copy2(self.path, self.backup_path)
            self._save_version()

        # 写入新内容
        self.path.write_text(content, encoding="utf-8")

        return {
            "ok": True,
            "path": str(self.path),
            "bytes": len(content),
            "backup_created": self.backup_path.exists(),
        }

    def _save_version(self):
        """保存版本历史"""
        if not self.path.exists():
            return

        self.history_dir.mkdir(exist_ok=True)

        # 生成版本号
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_file = self.history_dir / f"consensus_{timestamp}.md"

        # 复制当前内容到历史
        shutil.copy2(self.path, version_file)

        # 清理旧版本（保留最近 10 个）
        self._cleanup_history()

    def _cleanup_history(self, keep: int = 10):
        """清理旧版本"""
        versions = sorted(self.history_dir.glob("consensus_*.md"))
        if len(versions) > keep:
            for old_file in versions[:-keep]:
                old_file.unlink()

    def get_history(self, limit: int = 10) -> list[dict]:
        """获取版本历史"""
        if not self.history_dir.exists():
            return []

        versions = sorted(
            self.history_dir.glob("consensus_*.md"),
            reverse=True,
        )[:limit]

        return [
            {
                "version": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "mtime": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
            for f in versions
        ]

    def restore_version(self, version: str) -> dict:
        """恢复指定版本"""
        version_file = self.history_dir / version
        if not version_file.exists():
            raise FileNotFoundError(f"Version not found: {version}")

        shutil.copy2(version_file, self.path)
        return {"ok": True, "restored": version}

    def get_diff(self, version1: str, version2: str) -> str:
        """比较两个版本的差异"""
        # 简单实现，可以使用 difflib
        import difflib

        v1_file = self.history_dir / version1
        v2_file = self.history_dir / version2

        if not v1_file.exists() or not v2_file.exists():
            raise FileNotFoundError("Version not found")

        v1_lines = v1_file.read_text().splitlines(keepends=True)
        v2_lines = v2_file.read_text().splitlines(keepends=True)

        diff = difflib.unified_diff(v1_lines, v2_lines, fromfile=version1, tofile=version2)
        return "".join(diff)
