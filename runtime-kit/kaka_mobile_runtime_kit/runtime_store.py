from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .pairing import MobileTokenRecord, PairingSession
from .recall_export import build_recall_export_artifact
from .recall_search import RecallSearchProvider, TokenOverlapRecallSearchProvider


@dataclass(frozen=True)
class RuntimeRecallItem:
    item_id: str
    summary: str
    created_at: str
    source_task_id: str = ""
    source_inbox_item_id: str = ""
    source_surface: str = ""
    metadata: Mapping[str, Any] | None = None

    def to_mobile_bridge(self) -> dict[str, Any]:
        provenance: dict[str, Any] = {}
        if self.source_task_id:
            provenance["source_task_id"] = self.source_task_id
        if self.source_inbox_item_id:
            provenance["source_inbox_item_id"] = self.source_inbox_item_id
        if self.source_surface:
            provenance["source_surface"] = self.source_surface
        return {
            "item_id": self.item_id,
            "summary": self.summary,
            "created_at": self.created_at,
            "provenance": provenance,
        }


@dataclass(frozen=True)
class RuntimeDeletionReceipt:
    status: str
    deleted_item_ids: list[str]
    deleted_index_ids: list[str]

    def to_mobile_bridge(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "deleted_item_ids": self.deleted_item_ids,
            "deleted_index_ids": self.deleted_index_ids,
        }


@dataclass(frozen=True)
class RuntimeTaskRecord:
    task_id: str
    title: str
    status: str
    updated_at: str
    detail: str = ""
    approval_required: bool = False
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class RuntimeTaskEvent:
    event_id: str
    task_id: str
    type: str
    message: str
    created_at: str
    metadata: Mapping[str, Any] | None = None


TERMINAL_TASK_STATUSES = ("cancelled", "completed", "failed")


@dataclass(frozen=True)
class RuntimeTaskHistoryPurgeReceipt:
    status: str
    cutoff_iso: str
    deleted_task_ids: list[str]
    deleted_task_event_ids: list[str]
    preserved_active_task_ids: list[str]


@dataclass(frozen=True)
class RuntimeAssetRecord:
    asset_id: str
    role: str
    created_at: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    body: bytes
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class RuntimeAssetPurgeReceipt:
    eligible_input_asset_ids: list[str]
    eligible_output_asset_ids: list[str]
    deleted_input_asset_ids: list[str]
    deleted_output_asset_ids: list[str]
    untracked_asset_ids: list[str]


class SQLiteRuntimeStore:
    def __init__(
        self,
        path: str | Path,
        recall_search_provider: RecallSearchProvider | None = None,
    ) -> None:
        self.path = Path(path)
        self.recall_search_provider = recall_search_provider or TokenOverlapRecallSearchProvider()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS recall_items (
                    item_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    source_task_id TEXT NOT NULL DEFAULT '',
                    source_inbox_item_id TEXT NOT NULL DEFAULT '',
                    source_surface TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS recall_index_entries (
                    index_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES recall_items(item_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS runtime_tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    approval_required INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS task_events (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (task_id) REFERENCES runtime_tasks(task_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS runtime_assets (
                    asset_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    body BLOB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS runtime_assets_retention_idx
                    ON runtime_assets(role, created_at, asset_id);
                CREATE TABLE IF NOT EXISTS pairing_sessions (
                    pairing_code TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    runtime TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT
                );
                CREATE TABLE IF NOT EXISTS mobile_tokens (
                    token TEXT PRIMARY KEY,
                    device_name TEXT NOT NULL,
                    device_public_id TEXT NOT NULL,
                    runtime TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT,
                    revoked_at TEXT
                );
                """
            )
            self._ensure_column(db, "recall_items", "source_inbox_item_id", "TEXT NOT NULL DEFAULT ''")

    def upsert_asset(self, asset: RuntimeAssetRecord) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO runtime_assets (
                    asset_id, role, created_at, filename, mime_type, size_bytes, sha256, metadata_json, body
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_id) DO UPDATE SET
                    role=excluded.role,
                    created_at=excluded.created_at,
                    filename=excluded.filename,
                    mime_type=excluded.mime_type,
                    size_bytes=excluded.size_bytes,
                    sha256=excluded.sha256,
                    metadata_json=excluded.metadata_json,
                    body=excluded.body
                """,
                (
                    asset.asset_id,
                    asset.role.strip().lower(),
                    asset.created_at,
                    asset.filename,
                    asset.mime_type,
                    int(asset.size_bytes),
                    asset.sha256,
                    json.dumps(dict(asset.metadata or {}), ensure_ascii=False, sort_keys=True),
                    sqlite3.Binary(asset.body),
                ),
            )

    def get_asset(self, asset_id: str) -> RuntimeAssetRecord | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT asset_id, role, created_at, filename, mime_type, size_bytes, sha256, metadata_json, body
                FROM runtime_assets
                WHERE asset_id = ?
                """,
                (asset_id,),
            ).fetchone()
        if row is None:
            return None
        return self._asset_from_row(row)

    def list_assets(self, role: str | None = None) -> list[RuntimeAssetRecord]:
        where = ""
        values: list[Any] = []
        if role is not None:
            where = "WHERE role = ?"
            values.append(role.strip().lower())
        with self._connect() as db:
            rows = db.execute(
                f"""
                SELECT asset_id, role, created_at, filename, mime_type, size_bytes, sha256, metadata_json, body
                FROM runtime_assets
                {where}
                ORDER BY created_at ASC, asset_id ASC
                """,
                values,
            ).fetchall()
        return [self._asset_from_row(row) for row in rows]

    def purge_assets(
        self,
        input_cutoff_iso: str,
        output_cutoff_iso: str,
        dry_run: bool = True,
    ) -> RuntimeAssetPurgeReceipt:
        input_cutoff = _parse_asset_utc(input_cutoff_iso)
        output_cutoff = _parse_asset_utc(output_cutoff_iso)
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT asset_id, role, created_at
                FROM runtime_assets
                ORDER BY asset_id ASC
                """
            ).fetchall()
            eligible_input_asset_ids: list[str] = []
            eligible_output_asset_ids: list[str] = []
            untracked_asset_ids: list[str] = []
            for row in rows:
                asset_id = str(row["asset_id"])
                role = str(row["role"])
                created_at = _parse_asset_utc(str(row["created_at"]))
                if role not in {"input", "output"} or created_at is None:
                    untracked_asset_ids.append(asset_id)
                    continue
                if role == "input" and input_cutoff is not None and created_at < input_cutoff:
                    eligible_input_asset_ids.append(asset_id)
                if role == "output" and output_cutoff is not None and created_at < output_cutoff:
                    eligible_output_asset_ids.append(asset_id)
            deleted_input_asset_ids: list[str] = []
            deleted_output_asset_ids: list[str] = []
            if not dry_run:
                deleted_input_asset_ids = self._delete_runtime_assets(db, eligible_input_asset_ids)
                deleted_output_asset_ids = self._delete_runtime_assets(db, eligible_output_asset_ids)

        return RuntimeAssetPurgeReceipt(
            eligible_input_asset_ids=eligible_input_asset_ids,
            eligible_output_asset_ids=eligible_output_asset_ids,
            deleted_input_asset_ids=deleted_input_asset_ids,
            deleted_output_asset_ids=deleted_output_asset_ids,
            untracked_asset_ids=untracked_asset_ids,
        )

    def save_pairing_session(self, session: PairingSession) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO pairing_sessions (
                    pairing_code, session_id, endpoint, runtime, display_name, issued_at, expires_at, used_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pairing_code) DO UPDATE SET
                    session_id=excluded.session_id,
                    endpoint=excluded.endpoint,
                    runtime=excluded.runtime,
                    display_name=excluded.display_name,
                    issued_at=excluded.issued_at,
                    expires_at=excluded.expires_at,
                    used_at=excluded.used_at
                """,
                (
                    session.pairing_code,
                    session.session_id,
                    session.endpoint,
                    session.runtime,
                    session.display_name,
                    _datetime_to_store(session.issued_at),
                    _datetime_to_store(session.expires_at),
                    _datetime_to_store(session.used_at),
                ),
            )

    def load_pairing_session(self, pairing_code: str) -> PairingSession | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT pairing_code, session_id, endpoint, runtime, display_name, issued_at, expires_at, used_at
                FROM pairing_sessions
                WHERE pairing_code = ?
                """,
                (pairing_code,),
            ).fetchone()
        if row is None:
            return None
        return PairingSession(
            session_id=str(row["session_id"]),
            pairing_code=str(row["pairing_code"]),
            endpoint=str(row["endpoint"]),
            runtime=str(row["runtime"]),
            display_name=str(row["display_name"]),
            issued_at=_datetime_from_store(str(row["issued_at"])),
            expires_at=_datetime_from_store(str(row["expires_at"])),
            used_at=_datetime_from_store(row["used_at"]) if row["used_at"] else None,
        )

    def mark_pairing_session_used(self, pairing_code: str, used_at) -> PairingSession | None:
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE pairing_sessions SET used_at = ? WHERE pairing_code = ? AND used_at IS NULL",
                (_datetime_to_store(used_at), pairing_code),
            )
            if cursor.rowcount == 0:
                return None
        return self.load_pairing_session(pairing_code)

    def save_mobile_token(self, record: MobileTokenRecord) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO mobile_tokens (
                    token, device_name, device_public_id, runtime, issued_at, expires_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token) DO UPDATE SET
                    device_name=excluded.device_name,
                    device_public_id=excluded.device_public_id,
                    runtime=excluded.runtime,
                    issued_at=excluded.issued_at,
                    expires_at=excluded.expires_at,
                    revoked_at=excluded.revoked_at
                """,
                (
                    record.token,
                    record.device_name,
                    record.device_public_id,
                    record.runtime,
                    _datetime_to_store(record.issued_at),
                    _datetime_to_store(record.expires_at),
                    _datetime_to_store(record.revoked_at),
                ),
            )

    def load_mobile_token(self, token: str) -> MobileTokenRecord | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT token, device_name, device_public_id, runtime, issued_at, expires_at, revoked_at
                FROM mobile_tokens
                WHERE token = ?
                """,
                (token,),
            ).fetchone()
        if row is None:
            return None
        return _mobile_token_from_row(row)

    def revoke_mobile_token(self, token: str, revoked_at) -> bool:
        with self._connect() as db:
            existing = db.execute("SELECT 1 FROM mobile_tokens WHERE token = ?", (token,)).fetchone()
            if existing is None:
                return False
            db.execute(
                "UPDATE mobile_tokens SET revoked_at = ? WHERE token = ?",
                (_datetime_to_store(revoked_at), token),
            )
        return True

    def list_mobile_tokens(self) -> list[MobileTokenRecord]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT token, device_name, device_public_id, runtime, issued_at, expires_at, revoked_at
                FROM mobile_tokens
                ORDER BY issued_at ASC, device_public_id ASC
                """
            ).fetchall()
        return [_mobile_token_from_row(row) for row in rows]

    def remember_recall(self, item: RuntimeRecallItem, index_ids: Sequence[str] = ()) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO recall_items (
                    item_id, summary, created_at, source_task_id, source_inbox_item_id, source_surface, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    summary=excluded.summary,
                    created_at=excluded.created_at,
                    source_task_id=excluded.source_task_id,
                    source_inbox_item_id=excluded.source_inbox_item_id,
                    source_surface=excluded.source_surface,
                    metadata_json=excluded.metadata_json
                """,
                (
                    item.item_id,
                    item.summary,
                    item.created_at,
                    item.source_task_id,
                    item.source_inbox_item_id,
                    item.source_surface,
                    json.dumps(dict(item.metadata or {}), ensure_ascii=False, sort_keys=True),
                ),
            )
            for index_id in index_ids:
                db.execute(
                    "INSERT OR REPLACE INTO recall_index_entries (index_id, item_id) VALUES (?, ?)",
                    (index_id, item.item_id),
                )

    def list_recall(self, query: str = "", limit: int | None = 50) -> list[RuntimeRecallItem]:
        where = ""
        values: list[Any] = []
        normalized = query.strip()
        if normalized:
            where = "WHERE lower(summary) LIKE ?"
            values.append(f"%{normalized.lower()}%")
        sql = f"""
            SELECT item_id, summary, created_at, source_task_id, source_inbox_item_id, source_surface, metadata_json
            FROM recall_items
            {where}
            ORDER BY created_at DESC, item_id DESC
        """
        if limit is not None:
            sql += " LIMIT ?"
            values.append(max(int(limit), 0))
        with self._connect() as db:
            rows = db.execute(sql, values).fetchall()
        return [self._recall_from_row(row) for row in rows]

    def search_recall_semantic(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        items = self.list_recall(limit=None)
        results = self.recall_search_provider.search(query=query, items=items, limit=limit)
        return [result.to_mobile_bridge() for result in results]

    def export_recall(self) -> dict[str, Any]:
        return build_recall_export_artifact(
            items=[item.to_mobile_bridge() for item in self.list_recall(limit=None)],
            generated_at=_utc_now(),
        )

    def delete_recall(self, item_id: str) -> RuntimeDeletionReceipt:
        with self._connect() as db:
            index_rows = db.execute(
                "SELECT index_id FROM recall_index_entries WHERE item_id = ? ORDER BY index_id",
                (item_id,),
            ).fetchall()
            item_exists = db.execute(
                "SELECT 1 FROM recall_items WHERE item_id = ?",
                (item_id,),
            ).fetchone()
            db.execute("DELETE FROM recall_index_entries WHERE item_id = ?", (item_id,))
            db.execute("DELETE FROM recall_items WHERE item_id = ?", (item_id,))
        return RuntimeDeletionReceipt(
            status="forgotten",
            deleted_item_ids=[item_id] if item_exists else [],
            deleted_index_ids=[str(row["index_id"]) for row in index_rows],
        )

    def delete_recall_by_source(
        self,
        source_task_id: str = "",
        source_inbox_item_id: str = "",
    ) -> RuntimeDeletionReceipt:
        clauses: list[str] = []
        values: list[Any] = []
        if source_task_id:
            clauses.append("source_task_id = ?")
            values.append(source_task_id)
        if source_inbox_item_id:
            clauses.append("source_inbox_item_id = ?")
            values.append(source_inbox_item_id)
        if not clauses:
            return RuntimeDeletionReceipt(status="forgotten", deleted_item_ids=[], deleted_index_ids=[])

        where = " AND ".join(clauses)
        with self._connect() as db:
            item_rows = db.execute(
                f"SELECT item_id FROM recall_items WHERE {where} ORDER BY item_id",
                values,
            ).fetchall()
            deleted_item_ids = [str(row["item_id"]) for row in item_rows]
            if not deleted_item_ids:
                return RuntimeDeletionReceipt(status="forgotten", deleted_item_ids=[], deleted_index_ids=[])

            placeholders = ", ".join("?" for _ in deleted_item_ids)
            index_rows = db.execute(
                f"""
                SELECT index_id
                FROM recall_index_entries
                WHERE item_id IN ({placeholders})
                ORDER BY index_id
                """,
                deleted_item_ids,
            ).fetchall()
            db.execute(
                f"DELETE FROM recall_index_entries WHERE item_id IN ({placeholders})",
                deleted_item_ids,
            )
            db.execute(
                f"DELETE FROM recall_items WHERE item_id IN ({placeholders})",
                deleted_item_ids,
            )
        return RuntimeDeletionReceipt(
            status="forgotten",
            deleted_item_ids=deleted_item_ids,
            deleted_index_ids=[str(row["index_id"]) for row in index_rows],
        )

    def upsert_task(self, task: RuntimeTaskRecord) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO runtime_tasks (
                    task_id, title, status, updated_at, detail, approval_required, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    title=excluded.title,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    detail=excluded.detail,
                    approval_required=excluded.approval_required,
                    metadata_json=excluded.metadata_json
                """,
                (
                    task.task_id,
                    task.title,
                    task.status,
                    task.updated_at,
                    task.detail,
                    1 if task.approval_required else 0,
                    json.dumps(dict(task.metadata or {}), ensure_ascii=False, sort_keys=True),
                ),
            )

    def list_tasks(self) -> list[RuntimeTaskRecord]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT task_id, title, status, updated_at, detail, approval_required, metadata_json
                FROM runtime_tasks
                ORDER BY updated_at DESC, task_id DESC
                """
            ).fetchall()
        return [self._task_from_row(row) for row in rows]

    def get_task(self, task_id: str) -> RuntimeTaskRecord | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT task_id, title, status, updated_at, detail, approval_required, metadata_json
                FROM runtime_tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return self._task_from_row(row)

    def append_task_event(self, event: RuntimeTaskEvent) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT OR REPLACE INTO task_events (
                    event_id, task_id, type, message, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.task_id,
                    event.type,
                    event.message,
                    event.created_at,
                    json.dumps(dict(event.metadata or {}), ensure_ascii=False, sort_keys=True),
                ),
            )

    def list_task_events(self, task_id: str) -> list[RuntimeTaskEvent]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT event_id, task_id, type, message, created_at, metadata_json
                FROM task_events
                WHERE task_id = ?
                ORDER BY created_at ASC, event_id ASC
                """,
                (task_id,),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def purge_task_history(self, cutoff_iso: str, dry_run: bool = True) -> RuntimeTaskHistoryPurgeReceipt:
        terminal_placeholders = ", ".join("?" for _ in TERMINAL_TASK_STATUSES)
        terminal_values = list(TERMINAL_TASK_STATUSES)
        with self._connect() as db:
            task_rows = db.execute(
                f"""
                SELECT task_id
                FROM runtime_tasks
                WHERE status IN ({terminal_placeholders}) AND updated_at < ?
                ORDER BY task_id ASC
                """,
                [*terminal_values, cutoff_iso],
            ).fetchall()
            deleted_task_ids = [str(row["task_id"]) for row in task_rows]

            active_rows = db.execute(
                f"""
                SELECT task_id
                FROM runtime_tasks
                WHERE status NOT IN ({terminal_placeholders}) AND updated_at < ?
                ORDER BY task_id ASC
                """,
                [*terminal_values, cutoff_iso],
            ).fetchall()
            preserved_active_task_ids = [str(row["task_id"]) for row in active_rows]

            deleted_task_event_ids: list[str] = []
            if deleted_task_ids:
                task_placeholders = ", ".join("?" for _ in deleted_task_ids)
                event_rows = db.execute(
                    f"""
                    SELECT event_id
                    FROM task_events
                    WHERE task_id IN ({task_placeholders})
                    ORDER BY event_id ASC
                    """,
                    deleted_task_ids,
                ).fetchall()
                deleted_task_event_ids = [str(row["event_id"]) for row in event_rows]
                if not dry_run:
                    db.execute(
                        f"DELETE FROM runtime_tasks WHERE task_id IN ({task_placeholders})",
                        deleted_task_ids,
                    )

        return RuntimeTaskHistoryPurgeReceipt(
            status="dry_run" if dry_run else "applied",
            cutoff_iso=cutoff_iso,
            deleted_task_ids=deleted_task_ids,
            deleted_task_event_ids=deleted_task_event_ids,
            preserved_active_task_ids=preserved_active_task_ids,
        )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _ensure_column(self, db: sqlite3.Connection, table: str, column: str, declaration: str) -> None:
        rows = db.execute(f"PRAGMA table_info({table})").fetchall()
        if any(str(row["name"]) == column for row in rows):
            return
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    def _recall_from_row(self, row: sqlite3.Row) -> RuntimeRecallItem:
        return RuntimeRecallItem(
            item_id=str(row["item_id"]),
            summary=str(row["summary"]),
            created_at=str(row["created_at"]),
            source_task_id=str(row["source_task_id"]),
            source_inbox_item_id=str(row["source_inbox_item_id"]),
            source_surface=str(row["source_surface"]),
            metadata=_load_json_object(str(row["metadata_json"])),
        )

    def _task_from_row(self, row: sqlite3.Row) -> RuntimeTaskRecord:
        return RuntimeTaskRecord(
            task_id=str(row["task_id"]),
            title=str(row["title"]),
            status=str(row["status"]),
            updated_at=str(row["updated_at"]),
            detail=str(row["detail"]),
            approval_required=bool(row["approval_required"]),
            metadata=_load_json_object(str(row["metadata_json"])),
        )

    def _event_from_row(self, row: sqlite3.Row) -> RuntimeTaskEvent:
        return RuntimeTaskEvent(
            event_id=str(row["event_id"]),
            task_id=str(row["task_id"]),
            type=str(row["type"]),
            message=str(row["message"]),
            created_at=str(row["created_at"]),
            metadata=_load_json_object(str(row["metadata_json"])),
        )

    def _asset_from_row(self, row: sqlite3.Row) -> RuntimeAssetRecord:
        return RuntimeAssetRecord(
            asset_id=str(row["asset_id"]),
            role=str(row["role"]),
            created_at=str(row["created_at"]),
            filename=str(row["filename"]),
            mime_type=str(row["mime_type"]),
            size_bytes=int(row["size_bytes"]),
            sha256=str(row["sha256"]),
            body=bytes(row["body"]),
            metadata=_load_json_object(str(row["metadata_json"])),
        )

    def _delete_runtime_assets(self, db: sqlite3.Connection, asset_ids: Sequence[str]) -> list[str]:
        if not asset_ids:
            return []
        placeholders = ", ".join("?" for _ in asset_ids)
        db.execute(
            f"DELETE FROM runtime_assets WHERE asset_id IN ({placeholders})",
            list(asset_ids),
        )
        return list(asset_ids)


def _load_json_object(raw: str) -> dict[str, Any]:
    try:
        decoded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return dict(decoded) if isinstance(decoded, MappingABC) else {}


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _datetime_to_store(value) -> str | None:
    if value is None:
        return None
    return value.astimezone(_timezone_utc()).replace(microsecond=0).isoformat()


def _datetime_from_store(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(_timezone_utc()).replace(microsecond=0)


def _parse_asset_utc(value: str):
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(timezone.utc).replace(microsecond=0)
    except ValueError:
        return None


def _timezone_utc():
    from datetime import timezone

    return timezone.utc


def _mobile_token_from_row(row) -> MobileTokenRecord:
    return MobileTokenRecord(
        token=str(row["token"]),
        device_name=str(row["device_name"]),
        device_public_id=str(row["device_public_id"]),
        runtime=str(row["runtime"]),
        issued_at=_datetime_from_store(str(row["issued_at"])),
        expires_at=_datetime_from_store(row["expires_at"]) if row["expires_at"] else None,
        revoked_at=_datetime_from_store(row["revoked_at"]) if row["revoked_at"] else None,
    )
