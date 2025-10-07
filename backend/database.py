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
                    was_active INTEGER DEFAULT 0,
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

            # Add was_active column to existing tables (migration)
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN was_active INTEGER DEFAULT 0")
                logger.info("Added was_active column to sessions table")
            except sqlite3.OperationalError:
                # Column already exists
                pass

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

                    -- Profile info
                    profile TEXT,

                    -- Exposure settings
                    iso INTEGER,
                    shutter_speed TEXT,
                    exposure_compensation REAL,
                    lux REAL,
                    wb_temp INTEGER,
                    wb_mode INTEGER,

                    -- HDR/Bracketing
                    hdr_mode INTEGER,
                    bracket_count INTEGER,
                    bracket_ev TEXT,  -- JSON array

                    -- Metering
                    ae_metering_mode INTEGER,

                    -- Focus settings
                    af_mode INTEGER,
                    lens_position REAL,

                    -- Enhancement settings
                    sharpness REAL,
                    contrast REAL,
                    saturation REAL,

                    -- Camera info
                    analog_gain REAL,
                    digital_gain REAL,

                    created_at TEXT NOT NULL,

                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """
            )

            # Migrations for existing databases (safe for production)
            # Add new columns if they don't exist
            cursor = conn.cursor()

            # Check if profile column exists, add if missing
            columns = [row[1] for row in cursor.execute("PRAGMA table_info(captures)").fetchall()]

            new_columns = {
                'profile': 'TEXT',
                'hdr_mode': 'INTEGER',
                'bracket_count': 'INTEGER',
                'bracket_ev': 'TEXT',
                'ae_metering_mode': 'INTEGER',
                'af_mode': 'INTEGER',
                'lens_position': 'REAL',
                'sharpness': 'REAL',
                'contrast': 'REAL',
                'saturation': 'REAL'
            }

            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    logger.info(f"Adding column '{col_name}' to captures table")
                    conn.execute(f"ALTER TABLE captures ADD COLUMN {col_name} {col_type}")

            conn.commit()

            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON captures(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON captures(timestamp)")

            # Timelapses table for tracking generated videos
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS timelapses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    filename TEXT NOT NULL UNIQUE,
                    file_path TEXT NOT NULL,
                    file_size_mb REAL NOT NULL,

                    -- Video metadata
                    duration_seconds REAL,
                    frame_count INTEGER,
                    fps INTEGER,
                    quality TEXT,
                    quality_tier TEXT DEFAULT 'preview',  -- 'preview' or 'archive'

                    -- Session reference
                    profile TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    date TEXT NOT NULL,

                    -- Timestamps
                    created_at TEXT NOT NULL,

                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timelapse_session ON timelapses(session_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timelapse_date ON timelapses(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timelapse_profile ON timelapses(profile)")

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
            try:
                # Check if session exists
                result = conn.execute(
                    "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
                ).fetchone()

                if result:
                    return session_id

                # Create new session with transaction
                conn.execute("BEGIN IMMEDIATE")
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
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to get/create session: {e}", exc_info=True)
                raise

        return session_id

    def record_capture(
        self,
        session_id: str,
        filename: str,
        timestamp: datetime,
        settings: Dict,
    ):
        """Record a single capture with its metadata."""
        import json
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")

                # Serialize bracket_ev as JSON if present
                bracket_ev = settings.get("bracket_ev")
                bracket_ev_json = json.dumps(bracket_ev) if bracket_ev else None

                # Insert capture record with all camera settings
                conn.execute(
                    """
                    INSERT INTO captures (
                        session_id, timestamp, filename,
                        profile,
                        iso, shutter_speed, exposure_compensation,
                        lux, wb_temp, wb_mode,
                        hdr_mode, bracket_count, bracket_ev,
                        ae_metering_mode,
                        af_mode, lens_position,
                        sharpness, contrast, saturation,
                        analog_gain, digital_gain,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        timestamp.isoformat(),
                        filename,
                        settings.get("profile"),
                        settings.get("iso"),
                        settings.get("shutter_speed"),
                        settings.get("exposure_compensation"),
                        settings.get("lux"),
                        settings.get("wb_temp"),
                        settings.get("awb_mode"),
                        settings.get("hdr_mode"),
                        settings.get("bracket_count"),
                        bracket_ev_json,
                        settings.get("ae_metering_mode"),
                        settings.get("af_mode"),
                        settings.get("lens_position"),
                        settings.get("sharpness"),
                        settings.get("contrast"),
                        settings.get("saturation"),
                        settings.get("analog_gain"),
                        settings.get("digital_gain"),
                        now,
                    ),
                )

                # Update session statistics
                self._update_session_stats(conn, session_id, timestamp, settings)

                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to record capture: {e}", exc_info=True)
                raise

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

    def update_was_active(self, profile: str, date: str, schedule: str, was_active: bool):
        """
        Update the was_active state for a schedule.

        Args:
            profile: Profile identifier
            date: Date string (YYYY-MM-DD)
            schedule: Schedule name
            was_active: Whether schedule was active
        """
        session_id = f"{profile}_{date.replace('-', '')}_{schedule}"

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions SET
                    was_active = ?,
                    updated_at = ?
                WHERE session_id = ?
                """,
                (1 if was_active else 0, datetime.utcnow().isoformat(), session_id),
            )
            conn.commit()

    def get_was_active(self, profile: str, date: str, schedule: str) -> bool:
        """
        Get the was_active state for a schedule.

        Args:
            profile: Profile identifier
            date: Date string (YYYY-MM-DD)
            schedule: Schedule name

        Returns:
            Boolean indicating if schedule was previously active
        """
        session_id = f"{profile}_{date.replace('-', '')}_{schedule}"

        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT was_active FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()

            if result:
                return bool(result["was_active"])
            return False

    def record_timelapse(
        self,
        session_id: str,
        filename: str,
        file_path: str,
        file_size_mb: float,
        profile: str,
        schedule: str,
        date: str,
        duration_seconds: Optional[float] = None,
        frame_count: Optional[int] = None,
        fps: Optional[int] = None,
        quality: Optional[str] = None,
        quality_tier: Optional[str] = "preview",
    ):
        """
        Record a generated timelapse in the database.

        Args:
            session_id: Session ID this timelapse was generated from
            filename: Video filename (e.g., profile-a_sunset_2025-10-03.mp4)
            file_path: Full path to video file
            file_size_mb: File size in megabytes
            profile: Profile identifier (a-g)
            schedule: Schedule name (sunrise/daytime/sunset)
            date: Date string (YYYY-MM-DD)
            duration_seconds: Video duration in seconds
            frame_count: Number of frames in video
            fps: Frames per second
            quality: Quality setting (low/medium/high)
            quality_tier: Quality tier ('preview' or 'archive')
        """
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    """
                    INSERT INTO timelapses (
                        session_id, filename, file_path, file_size_mb,
                        duration_seconds, frame_count, fps, quality, quality_tier,
                        profile, schedule, date, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        filename,
                        file_path,
                        file_size_mb,
                        duration_seconds,
                        frame_count,
                        fps,
                        quality,
                        quality_tier,
                        profile,
                        schedule,
                        date,
                        now,
                    ),
                )
                conn.commit()
                logger.info(
                    f"📼 Recorded timelapse: {filename} ({file_size_mb:.1f} MB, {quality_tier})"
                )
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to record timelapse: {e}", exc_info=True)
                raise

    def get_timelapses(
        self,
        limit: Optional[int] = None,
        profile: Optional[str] = None,
        schedule: Optional[str] = None,
        date: Optional[str] = None,
    ) -> List[Dict]:
        """
        Query timelapses from database with optional filters.

        Args:
            limit: Maximum number of results (default: all)
            profile: Filter by profile (a-g)
            schedule: Filter by schedule (sunrise/daytime/sunset)
            date: Filter by date (YYYY-MM-DD)

        Returns:
            List of timelapse dictionaries sorted by created_at descending
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM timelapses WHERE 1=1"
            params = []

            if profile:
                query += " AND profile = ?"
                params.append(profile)

            if schedule:
                query += " AND schedule = ?"
                params.append(schedule)

            if date:
                query += " AND date = ?"
                params.append(date)

            query += " ORDER BY created_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            results = conn.execute(query, params).fetchall()
            return [dict(row) for row in results]
