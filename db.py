"""
VisionMate AI — Database Configuration & Operations Module
Connects to XAMPP MySQL database (ai_blind_guide)
"""

import os
import time
import logging
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash

log = logging.getLogger("VisionMateAI.Database")

# ── Database Connection Settings ──────────────────────────────────────────────
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "ai_blind_guide")
DB_CHARSET = "utf8mb4"

DB_CONFIG = {
    "host": DB_HOST,
    "port": DB_PORT,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "charset": DB_CHARSET,
    "cursorclass": DictCursor,
    "autocommit": False,
    "connect_timeout": 5,
}


def get_db_connection():
    """
    Establish and return a new MySQL connection.
    Raises pymysql.MySQLError on failure.
    """
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.MySQLError as e:
        log.error("Failed to connect to MySQL database '%s' at %s:%s: %s", DB_NAME, DB_HOST, DB_PORT, e)
        raise


def test_connection():
    """
    Test the database connection.
    Returns (success: bool, message: str).
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()
        conn.close()
        if row and row.get("ok") == 1:
            return True, f"Connected to MySQL database '{DB_NAME}' at {DB_HOST}:{DB_PORT}"
        return False, "Database responded with unexpected result"
    except Exception as e:
        return False, str(e)


def execute_query(sql, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Execute a parameterized SQL query safely.
    Handles cursor, transaction commit/rollback, and connection closure.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()

            if commit:
                conn.commit()
                result = cursor.lastrowid if cursor.lastrowid else cursor.rowcount
            return result
    except Exception as e:
        if conn and commit:
            try:
                conn.rollback()
            except Exception:
                pass
        log.error("Database query failed: %s | Params: %s | Error: %s", sql, params, e)
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ── Activity Logging ──────────────────────────────────────────────────────────

def log_activity(user_id=None, session_id=None, action="INFO", details=None):
    """Log user or system activity into activity_logs table."""
    try:
        sql = """
            INSERT INTO activity_logs (user_id, session_id, action, details)
            VALUES (%s, %s, %s, %s)
        """
        # Truncate details to 500 chars if necessary
        truncated_details = (details[:497] + "...") if details and len(details) > 500 else details
        execute_query(sql, (user_id, session_id, action, truncated_details), commit=True)
    except Exception as e:
        log.warning("Could not log activity '%s': %s", action, e)


# ── User Authentication & Profile ─────────────────────────────────────────────

def register_user(full_name: str, email: str, password: str):
    """
    Register a new user with hashed password and default preferences.
    Returns (success: bool, data_or_error_message: dict | str).
    """
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()

    if not full_name:
        return False, "Full name is required."
    if not email or "@" not in email:
        return False, "A valid email address is required."
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."

    try:
        # Check if email is already registered
        existing = execute_query("SELECT user_id FROM users WHERE email = %s", (email,), fetch_one=True)
        if existing:
            return False, "An account with this email address already exists."

        # Secure password hash
        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 1. Insert user
                cursor.execute(
                    "INSERT INTO users (full_name, email, password_hash, is_active) VALUES (%s, %s, %s, 1)",
                    (full_name, email, password_hash)
                )
                user_id = cursor.lastrowid

                # 2. Insert default preferences
                cursor.execute(
                    """
                    INSERT INTO user_preferences 
                        (user_id, language_code, speech_enabled, speech_rate, high_contrast_mode)
                    VALUES (%s, 'en', 1, 1.00, 0)
                    """,
                    (user_id,)
                )

                # 3. Insert activity log
                cursor.execute(
                    "INSERT INTO activity_logs (user_id, action, details) VALUES (%s, %s, %s)",
                    (user_id, "USER_REGISTERED", f"New user registered: {email}")
                )

                conn.commit()

            return True, {
                "user_id": user_id,
                "full_name": full_name,
                "email": email,
                "preferences": {
                    "language_code": "en",
                    "speech_enabled": True,
                    "speech_rate": 1.0,
                    "high_contrast_mode": False
                }
            }
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    except Exception as e:
        log.exception("Error registering user")
        return False, f"Registration failed: {str(e)}"


def authenticate_user(email: str, password: str):
    """
    Verify user credentials and return user profile + preferences.
    Returns (success: bool, user_data_or_error: dict | str).
    """
    email = (email or "").strip().lower()
    if not email or not password:
        return False, "Email and password are required."

    try:
        sql = """
            SELECT u.user_id, u.full_name, u.email, u.password_hash, u.is_active,
                   p.language_code, p.speech_enabled, p.speech_rate, p.high_contrast_mode
            FROM users u
            LEFT JOIN user_preferences p ON u.user_id = p.user_id
            WHERE u.email = %s
        """
        user = execute_query(sql, (email,), fetch_one=True)

        if not user:
            return False, "Invalid email or password."

        if not user.get("is_active"):
            return False, "This account has been deactivated."

        if not check_password_hash(user["password_hash"], password):
            log_activity(user_id=user["user_id"], action="LOGIN_FAILED", details=f"Failed login attempt for {email}")
            return False, "Invalid email or password."

        # Successful login
        log_activity(user_id=user["user_id"], action="USER_LOGIN", details=f"User {email} logged in successfully")

        return True, {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "preferences": {
                "language_code": user.get("language_code") or "en",
                "speech_enabled": bool(user.get("speech_enabled", 1)),
                "speech_rate": float(user.get("speech_rate") or 1.0),
                "high_contrast_mode": bool(user.get("high_contrast_mode", 0)),
            }
        }

    except Exception as e:
        log.exception("Authentication error")
        return False, f"Login failed: {str(e)}"


def get_user_profile(user_id: int):
    """Fetch user profile and preferences by user_id."""
    try:
        sql = """
            SELECT u.user_id, u.full_name, u.email, u.is_active, u.created_at,
                   p.language_code, p.speech_enabled, p.speech_rate, p.high_contrast_mode
            FROM users u
            LEFT JOIN user_preferences p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """
        user = execute_query(sql, (user_id,), fetch_one=True)
        if not user:
            return None

        return {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "created_at": user["created_at"].strftime("%Y-%m-%d %H:%M:%S") if user.get("created_at") else None,
            "preferences": {
                "language_code": user.get("language_code") or "en",
                "speech_enabled": bool(user.get("speech_enabled", 1)),
                "speech_rate": float(user.get("speech_rate") or 1.0),
                "high_contrast_mode": bool(user.get("high_contrast_mode", 0)),
            }
        }
    except Exception as e:
        log.error("Failed to get profile for user %s: %s", user_id, e)
        return None


def update_user_preferences(user_id: int, language_code=None, speech_enabled=None, speech_rate=None, high_contrast_mode=None):
    """Update user preferences."""
    try:
        # Validate speech rate (must be between 0.50 and 2.00)
        if speech_rate is not None:
            speech_rate = max(0.50, min(2.00, float(speech_rate)))

        # Check existing preferences record
        pref = execute_query("SELECT preference_id FROM user_preferences WHERE user_id = %s", (user_id,), fetch_one=True)

        if not pref:
            # Insert if missing
            sql = """
                INSERT INTO user_preferences (user_id, language_code, speech_enabled, speech_rate, high_contrast_mode)
                VALUES (%s, %s, %s, %s, %s)
            """
            execute_query(
                sql,
                (
                    user_id,
                    language_code or "en",
                    1 if speech_enabled in (True, 1, "1") else 0,
                    speech_rate if speech_rate is not None else 1.00,
                    1 if high_contrast_mode in (True, 1, "1") else 0
                ),
                commit=True
            )
        else:
            # Build dynamic UPDATE query
            updates = []
            params = []
            if language_code is not None:
                updates.append("language_code = %s")
                params.append(str(language_code)[:10])
            if speech_enabled is not None:
                updates.append("speech_enabled = %s")
                params.append(1 if speech_enabled in (True, 1, "1") else 0)
            if speech_rate is not None:
                updates.append("speech_rate = %s")
                params.append(speech_rate)
            if high_contrast_mode is not None:
                updates.append("high_contrast_mode = %s")
                params.append(1 if high_contrast_mode in (True, 1, "1") else 0)

            if updates:
                sql = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = %s"
                params.append(user_id)
                execute_query(sql, tuple(params), commit=True)

        log_activity(user_id=user_id, action="PREFERENCES_UPDATED", details="User updated preferences")
        return True, "Preferences updated successfully."
    except Exception as e:
        log.exception("Error updating preferences")
        return False, str(e)


# ── Detection Sessions & Results ──────────────────────────────────────────────

def start_detection_session(user_id, feature_type: str, input_source: str = "CAMERA"):
    """
    Create a new detection session in detection_sessions.
    feature_type: 'OBJECT_DETECTION','TEXT_RECOGNITION','MEDICINE_LABEL_READING','BUS_IDENTIFICATION','VOICE_COMMAND'
    input_source: 'CAMERA', 'UPLOAD', 'VOICE', 'TEXT'
    """
    valid_features = {
        "OBJECT_DETECTION",
        "TEXT_RECOGNITION",
        "MEDICINE_LABEL_READING",
        "BUS_IDENTIFICATION",
        "VOICE_COMMAND"
    }
    valid_sources = {"CAMERA", "UPLOAD", "VOICE", "TEXT"}

    feature = feature_type if feature_type in valid_features else "OBJECT_DETECTION"
    source = input_source if input_source in valid_sources else "CAMERA"

    try:
        sql = """
            INSERT INTO detection_sessions (user_id, feature_type, input_source, status)
            VALUES (%s, %s, %s, 'PROCESSING')
        """
        session_id = execute_query(sql, (user_id, feature, source), commit=True)
        return session_id
    except Exception as e:
        log.warning("Could not start detection session in database: %s", e)
        return None


def finish_detection_session(session_id: int, status: str = "COMPLETED", processing_time_ms: int = None,
                             results: list = None, error_message: str = None, user_id: int = None):
    """
    Finalize a detection session and insert result records into detection_results.
    results list format:
      [{"result_type": 'OBJECT'|'OCR_TEXT'|'MEDICINE_TEXT'|'BUS'|'VOICE_INTENT',
        "result_text": "...", "confidence": 0.95, "spoken_response": "..."}]
    """
    if not session_id:
        return

    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 1. Update session status
                err_truncated = (error_message[:497] + "...") if error_message and len(error_message) > 500 else error_message
                cursor.execute(
                    """
                    UPDATE detection_sessions 
                    SET status = %s, processing_time_ms = %s, error_message = %s, completed_at = NOW()
                    WHERE session_id = %s
                    """,
                    (status, processing_time_ms, err_truncated, session_id)
                )

                # 2. Insert results
                if results and status == "COMPLETED":
                    for r in results:
                        rtype = r.get("result_type", "OBJECT")
                        rtext = r.get("result_text", "")
                        conf = r.get("confidence")
                        if conf is not None:
                            try:
                                conf = float(conf)
                                if conf > 1.0:  # If percentage like 95.0, convert to 0.95
                                    conf = conf / 100.0
                                conf = max(0.0000, min(1.0000, conf))
                            except (ValueError, TypeError):
                                conf = None
                        spoken = r.get("spoken_response")

                        cursor.execute(
                            """
                            INSERT INTO detection_results (session_id, result_type, result_text, confidence, spoken_response)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (session_id, rtype, rtext, conf, spoken)
                        )

                # 3. Log activity
                action = f"{status}_{session_id}"
                cursor.execute(
                    "INSERT INTO activity_logs (user_id, session_id, action, details) VALUES (%s, %s, %s, %s)",
                    (user_id, session_id, f"SESSION_{status}", f"Processed {len(results or [])} results in {processing_time_ms or 0}ms")
                )

                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    except Exception as e:
        log.warning("Could not finish detection session %s in database: %s", session_id, e)


def get_detection_history(user_id=None, limit=20):
    """
    Retrieve past detection sessions and their results.
    If user_id is provided, filters by that user.
    """
    try:
        where_clause = "WHERE s.user_id = %s" if user_id else ""
        params = (user_id, limit) if user_id else (limit,)

        sql = f"""
            SELECT s.session_id, s.user_id, s.feature_type, s.input_source, s.status,
                   s.processing_time_ms, s.created_at, s.completed_at,
                   r.result_id, r.result_type, r.result_text, r.confidence, r.spoken_response
            FROM detection_sessions s
            LEFT JOIN detection_results r ON s.session_id = r.session_id
            {where_clause}
            ORDER BY s.created_at DESC, r.result_id ASC
            LIMIT %s
        """
        rows = execute_query(sql, params, fetch_all=True) or []

        # Group by session_id
        sessions = {}
        for row in rows:
            sid = row["session_id"]
            if sid not in sessions:
                sessions[sid] = {
                    "session_id": sid,
                    "feature_type": row["feature_type"],
                    "input_source": row["input_source"],
                    "status": row["status"],
                    "processing_time_ms": row["processing_time_ms"],
                    "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if row["created_at"] else None,
                    "results": []
                }
            if row.get("result_id"):
                sessions[sid]["results"].append({
                    "result_type": row["result_type"],
                    "result_text": row["result_text"],
                    "confidence": float(row["confidence"]) if row["confidence"] is not None else None,
                    "spoken_response": row["spoken_response"]
                })

        return list(sessions.values())
    except Exception as e:
        log.error("Failed to get detection history: %s", e)
        return []
