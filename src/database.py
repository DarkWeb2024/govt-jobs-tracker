"""SQLite storage with dedup, change detection and edit history."""
import json
import os
import sqlite3
from datetime import datetime

from .models import Notification
from .logger import get_logger

log = get_logger("database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT, finished_at TEXT,
    new_count INTEGER, updated_count INTEGER, error_count INTEGER,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS aliases (
    alias_id TEXT PRIMARY KEY,
    canonical_id TEXT NOT NULL
);
"""

# fields the pipeline may not overwrite once a human set them
PROTECTED_FIELDS = {"status", "notes"}


class Store:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    def all(self):
        rows = self.conn.execute("SELECT data FROM notifications").fetchall()
        return [Notification(**json.loads(r[0])) for r in rows]

    def get(self, nid):
        row = self.conn.execute(
            "SELECT data FROM notifications WHERE notification_id=?", (nid,)).fetchone()
        return Notification(**json.loads(row[0])) if row else None

    def resolve(self, nid):
        """Follow a merge alias: a scraped duplicate's id maps to the record
        the user chose to keep, so re-scrapes update the keeper instead of
        resurrecting the duplicate."""
        row = self.conn.execute(
            "SELECT canonical_id FROM aliases WHERE alias_id=?", (nid,)).fetchone()
        return row[0] if row else nid

    def upsert(self, n: Notification):
        """Insert or merge. Returns 'new', 'updated' or 'unchanged'."""
        now = datetime.now().isoformat(timespec="seconds")
        n.notification_id = self.resolve(n.notification_id)
        existing = self.get(n.notification_id)
        if existing is None:
            self.conn.execute(
                "INSERT INTO notifications VALUES (?,?,?,?)",
                (n.notification_id, json.dumps(n.to_dict(), ensure_ascii=False), now, now))
            self.conn.commit()
            log.info("new notification: %s (%s)", n.job_name, n.notification_id)
            return "new"
        changed = False
        old, new = existing.to_dict(), n.to_dict()
        for k, v in new.items():
            if k in PROTECTED_FIELDS or k in ("first_seen",):
                continue
            if v and v != old.get(k):
                if k not in ("last_checked", "verification_timestamp"):
                    self.conn.execute(
                        "INSERT INTO history (notification_id, changed_at, field, old_value, new_value)"
                        " VALUES (?,?,?,?,?)",
                        (n.notification_id, now, k, str(old.get(k, "")), str(v)))
                    changed = True
                old[k] = v
        old["last_checked"] = now
        self.conn.execute(
            "UPDATE notifications SET data=?, updated_at=? WHERE notification_id=?",
            (json.dumps(old, ensure_ascii=False), now, n.notification_id))
        self.conn.commit()
        return "updated" if changed else "unchanged"

    def set_status(self, nid, status, note=""):
        n = self.get(nid)
        if not n:
            return False
        now = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            "INSERT INTO history (notification_id, changed_at, field, old_value, new_value)"
            " VALUES (?,?,?,?,?)", (nid, now, "status", n.status, status))
        d = n.to_dict()
        d["status"] = status
        if note:
            d["notes"] = (d["notes"] + " | " if d["notes"] else "") + note
        self.conn.execute(
            "UPDATE notifications SET data=?, updated_at=? WHERE notification_id=?",
            (json.dumps(d, ensure_ascii=False), now, nid))
        self.conn.commit()
        return True

    def merge(self, keep_id, dup_id):
        """Merge dup into keep: fill keep's empty fields from dup, carry over
        an applied status, delete dup, and remember the mapping so future
        scrapes of the duplicate update the keeper. Returns False if either
        id is missing."""
        keep, dup = self.get(keep_id), self.get(dup_id)
        if keep is None or dup is None or keep_id == dup_id:
            return False
        now = datetime.now().isoformat(timespec="seconds")
        kd, dd = keep.to_dict(), dup.to_dict()
        for k, v in dd.items():
            if k in ("notification_id", "first_seen"):
                continue
            if v and not kd.get(k):
                kd[k] = v
        if kd.get("status") in (None, "", "Not Applied") and dd.get("status") not in (None, "", "Not Applied"):
            kd["status"] = dd["status"]
        kd["notes"] = ((kd.get("notes") or "") + f" | merged duplicate {dup_id} on {now[:10]}").strip(" |")
        self.conn.execute(
            "UPDATE notifications SET data=?, updated_at=? WHERE notification_id=?",
            (json.dumps(kd, ensure_ascii=False), now, keep_id))
        self.conn.execute("DELETE FROM notifications WHERE notification_id=?", (dup_id,))
        self.conn.execute("INSERT OR REPLACE INTO aliases VALUES (?,?)", (dup_id, keep_id))
        # any older aliases pointing at the deleted duplicate follow the keeper
        self.conn.execute("UPDATE aliases SET canonical_id=? WHERE canonical_id=?",
                          (keep_id, dup_id))
        self.conn.execute(
            "INSERT INTO history (notification_id, changed_at, field, old_value, new_value)"
            " VALUES (?,?,?,?,?)", (keep_id, now, "merged", dup_id, dup.job_name[:120]))
        self.conn.commit()
        log.info("merged %s into %s", dup_id, keep_id)
        return True

    def append_note(self, nid, note):
        """Add a dated note line (history-logged); used by the applied-updates
        watcher. Returns False if the id is unknown."""
        n = self.get(nid)
        if not n:
            return False
        now = datetime.now().isoformat(timespec="seconds")
        d = n.to_dict()
        d["notes"] = ((d.get("notes") or "") + " | " + note).strip(" |")
        self.conn.execute(
            "INSERT INTO history (notification_id, changed_at, field, old_value, new_value)"
            " VALUES (?,?,?,?,?)", (nid, now, "update_spotted", "", note[:200]))
        self.conn.execute(
            "UPDATE notifications SET data=?, updated_at=? WHERE notification_id=?",
            (json.dumps(d, ensure_ascii=False), now, nid))
        self.conn.commit()
        return True

    def changes_since(self, iso_ts):
        rows = self.conn.execute(
            "SELECT notification_id, changed_at, field, old_value, new_value FROM history"
            " WHERE changed_at > ? ORDER BY changed_at DESC", (iso_ts,)).fetchall()
        return rows

    def record_run(self, started, new, updated, errors, summary):
        self.conn.execute(
            "INSERT INTO runs (started_at, finished_at, new_count, updated_count, error_count, summary)"
            " VALUES (?,?,?,?,?,?)",
            (started, datetime.now().isoformat(timespec="seconds"), new, updated, errors, summary))
        self.conn.commit()
