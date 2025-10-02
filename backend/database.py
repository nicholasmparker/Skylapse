"""
SQLite database for session and capture metadata tracking.

Stores:
- Capture sessions (sunrise/sunset/daytime periods)
- Per-image metadata (exposure, lux, timing)
- Session statistics and tags
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionDatabase:
    """Manages capture session metadata in SQLite."""

    def __init__(self, db_path: str = "/data/db/skylapse.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    profile TEXT NOT NULL,
                    date TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    image_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    tags TEXT,
                    weather_conditions TEXT,

                    -- Exposure statistics
                    lux_min REAL,
                    lux_max REAL,
                    lux_avg REAL,
                    iso_min INTEGER,
                    iso_max INTEGER,
                    wb_min INTEGER,
                    wb_max INTEGER,

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_lookup ON sessions(profile, date, schedule)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON sessions(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON sessions(date)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS captures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    filename TEXT NOT NULL,

                    -- Exposure settings
                    iso INTEGER,
                    shutter_speed TEXT,
                    exposure_compensation REAL,
                    lux REAL,
                    wb_temp INTEGER,
                    wb_mode INTEGER,

                    -- Camera info
                    analog_gain REAL,
                    digital_gain REAL,

                    created_at TEXT NOT NULL,

                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """
            )

            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON captures(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON captures(timestamp)")

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_or_create_session(self, profile: str, date: str, schedule: str) -> str:
        """
        Get existing session or create new one.

        Returns:
            session_id string (e.g., "a_20251001_sunset")
        """
        session_id = f"{profile}_{date.replace('-', '')}_{schedule}"
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            # Check if session exists
            result = conn.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()

            if result:
                return session_id

            # Create new session
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, profile, date, schedule,
                    start_time, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (session_id, profile, date, schedule, now, now, now),
            )
            conn.commit()
            logger.info(f"📊 Created session: {session_id}")

        return session_id

    def record_capture(
        self,
        session_id: str,
        filename: str,
        timestamp: datetime,
        settings: Dict,
    ):
        """Record a single capture with its metadata."""
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            # Insert capture record
            conn.execute(
                """
                INSERT INTO captures (
                    session_id, timestamp, filename,
                    iso, shutter_speed, exposure_compensation,
                    lux, wb_temp, wb_mode,
                    analog_gain, digital_gain,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    timestamp.isoformat(),
                    filename,
                    settings.get("iso"),
                    settings.get("shutter_speed"),
                    settings.get("exposure_compensation"),
                    settings.get("lux"),
                    settings.get("wb_temp"),
                    settings.get("awb_mode"),
                    settings.get("analog_gain"),
                    settings.get("digital_gain"),
                    now,
                ),
            )

            # Update session statistics
            self._update_session_stats(conn, session_id, timestamp, settings)
            conn.commit()

    def _update_session_stats(
        self, conn: sqlite3.Connection, session_id: str, timestamp: datetime, settings: Dict
    ):
        """Update session-level statistics."""
        lux = settings.get("lux")
        iso = settings.get("iso")
        wb_temp = settings.get("wb_temp")

        # Get current stats
        current = conn.execute(
            """
            SELECT image_count, lux_min, lux_max, lux_avg,
                   iso_min, iso_max, wb_min, wb_max
            FROM sessions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

        if not current:
            return

        # Update counts and ranges
        new_count = (current["image_count"] or 0) + 1

        # Lux stats
        lux_min = current["lux_min"]
        lux_max = current["lux_max"]
        lux_avg = current["lux_avg"]
        if lux is not None:
            lux_min = min(lux, lux_min) if lux_min is not None else lux
            lux_max = max(lux, lux_max) if lux_max is not None else lux
            if lux_avg is None:
                lux_avg = lux
            else:
                lux_avg = (lux_avg * (new_count - 1) + lux) / new_count

        # ISO stats
        iso_min = current["iso_min"]
        iso_max = current["iso_max"]
        if iso is not None:
            iso_min = min(iso, iso_min) if iso_min is not None else iso
            iso_max = max(iso, iso_max) if iso_max is not None else iso

        # WB stats
        wb_min = current["wb_min"]
        wb_max = current["wb_max"]
        if wb_temp is not None:
            wb_min = min(wb_temp, wb_min) if wb_min is not None else wb_temp
            wb_max = max(wb_temp, wb_max) if wb_max is not None else wb_temp

        # Update session
        conn.execute(
            """
            UPDATE sessions SET
                end_time = ?,
                image_count = ?,
                lux_min = ?, lux_max = ?, lux_avg = ?,
                iso_min = ?, iso_max = ?,
                wb_min = ?, wb_max = ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (
                timestamp.isoformat(),
                new_count,
                lux_min,
                lux_max,
                lux_avg,
                iso_min,
                iso_max,
                wb_min,
                wb_max,
                datetime.utcnow().isoformat(),
                session_id,
            ),
        )

    def get_stale_sessions(self, idle_minutes: int = 5) -> List[Dict]:
        """
        Find sessions that haven't had captures recently.

        Args:
            idle_minutes: Minutes since last capture to consider stale

        Returns:
            List of session dicts ready for timelapse generation
        """
        cutoff = datetime.utcnow().timestamp() - (idle_minutes * 60)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

        with self._get_connection() as conn:
            results = conn.execute(
                """
                SELECT * FROM sessions
                WHERE status = 'active'
                  AND end_time IS NOT NULL
                  AND end_time < ?
                  AND image_count > 0
                ORDER BY end_time ASC
                """,
                (cutoff_iso,),
            ).fetchall()

            return [dict(row) for row in results]

    def mark_session_complete(self, session_id: str):
        """Mark session as complete (captures done, waiting for timelapse)."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions SET
                    status = 'complete',
                    updated_at = ?
                WHERE session_id = ?
                """,
                (datetime.utcnow().isoformat(), session_id),
            )
            conn.commit()
            logger.info(f"✓ Session marked complete: {session_id}")

    def mark_timelapse_generated(self, session_id: str):
        """Mark session timelapse as generated."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions SET
                    status = 'timelapse_generated',
                    updated_at = ?
                WHERE session_id = ?
                """,
                (datetime.utcnow().isoformat(), session_id),
            )
            conn.commit()
            logger.info(f"🎬 Timelapse marked generated: {session_id}")

    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get session statistics."""
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()

            return dict(result) if result else None
