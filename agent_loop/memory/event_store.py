"""
事件存储

结构化事件的 JSONL 存储。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..types import Event


class EventStore:
    """
    事件存储器

    将所有事件以 JSONL 格式存储，便于后续分析和回放。
    """

    def __init__(self, output_file: Optional[str] = None):
        if output_file:
            self.path = Path(output_file).expanduser().resolve()
            self.path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.path = None

    def append(self, event: Event) -> dict:
        """添加事件到存储"""
        if self.path is None:
            return {"ok": False, "error": "Event store not configured"}

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_json(), ensure_ascii=False) + "\n")

        return {"ok": True, "path": str(self.path)}

    def query(
        self,
        event_type: Optional[str] = None,
        cycle_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict]:
        """查询事件"""
        if not self.path or not self.path.exists():
            return []

        results = []

        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                # 过滤
                if event_type and event.get("event") != event_type:
                    continue
                if cycle_id and event.get("cycle_id") != cycle_id:
                    continue
                if start_time and event.get("timestamp", "") < start_time.isoformat():
                    continue
                if end_time and event.get("timestamp", "") > end_time.isoformat():
                    continue

                results.append(event)

                if len(results) >= limit:
                    break

        return results

    def get_cycle_events(self, cycle_id: int) -> list[dict]:
        """获取指定周期的所有事件"""
        return self.query(cycle_id=cycle_id, limit=1000)

    def get_last_cycle(self) -> Optional[int]:
        """获取最后一个周期 ID"""
        events = self.query(limit=1)
        if not events:
            return None
        return events[0].get("cycle_id")

    def clear(self):
        """清空事件存储"""
        if self.path and self.path.exists():
            self.path.unlink()

    def export_json(self, output_path: str) -> dict:
        """导出为 JSON 文件"""
        if not self.path or not self.path.exists():
            return {"ok": False, "error": "Event store empty"}

        events = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        output_file = Path(output_path).expanduser().resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

        return {"ok": True, "path": str(output_file), "count": len(events)}
