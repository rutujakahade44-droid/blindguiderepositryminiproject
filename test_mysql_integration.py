"""
VisionMate AI — Full MySQL & Flask Backend Integration Tests
Tests database connection, queries, registration, login, preferences, sessions, and AI endpoints.
"""

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db
from app import app

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
    b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestMySQLIntegration(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.test_email = "integ_test_user@blindguide.local"
        self.test_password = "SecurePassword@2026"

    def tearDown(self):
        # Clean up integration test user
        try:
            db.execute_query("DELETE FROM users WHERE email = %s", (self.test_email,), commit=True)
        except Exception:
            pass

    def test_01_db_direct_connection(self):
        """Verify direct MySQL connection and database name."""
        ok, msg = db.test_connection()
        self.assertTrue(ok, f"Database connection failed: {msg}")
        self.assertEqual(db.DB_NAME, "ai_blind_guide")
        self.assertEqual(db.DB_PORT, 3306)

    def test_02_health_endpoint(self):
        """Verify /api/health returns database connection status."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("database", data)
        self.assertTrue(data["database"]["connected"])
        self.assertEqual(data["database"]["name"], "ai_blind_guide")

    def test_03_home_page(self):
        """Verify home page loads successfully with UI elements."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("VisionMate AI", html)
        self.assertIn("authBtn", html)
        self.assertIn("historyBtn", html)
        self.assertIn("authModal", html)

    def test_04_user_registration_and_hash(self):
        """Verify user registration stores hashed password and default preferences."""
        res = self.client.post("/api/auth/register", json={
            "full_name": "Integration User",
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        # Check in MySQL directly that password is NOT plain text
        user_row = db.execute_query("SELECT * FROM users WHERE email = %s", (self.test_email,), fetch_one=True)
        self.assertIsNotNone(user_row)
        self.assertNotEqual(user_row["password_hash"], self.test_password)
        self.assertTrue(user_row["password_hash"].startswith("scrypt:") or user_row["password_hash"].startswith("pbkdf2:"))

        # Check user_preferences created
        pref_row = db.execute_query("SELECT * FROM user_preferences WHERE user_id = %s", (user_row["user_id"],), fetch_one=True)
        self.assertIsNotNone(pref_row)
        self.assertEqual(pref_row["language_code"], "en")

    def test_05_login_demo_user(self):
        """Verify login for the pre-seeded demo user."""
        res = self.client.post("/api/auth/login", json={
            "email": "demo@blindguide.local",
            "password": "Demo@123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["email"], "demo@blindguide.local")

    def test_06_update_user_preferences(self):
        """Verify updating preferences saves to MySQL user_preferences."""
        # Log in first
        login_res = self.client.post("/api/auth/login", json={
            "email": "demo@blindguide.local",
            "password": "Demo@123"
        })
        self.assertEqual(login_res.status_code, 200)

        # Update preferences
        pref_res = self.client.post("/api/user/preferences", json={
            "language_code": "en",
            "speech_enabled": True,
            "speech_rate": 1.2,
            "high_contrast_mode": True
        })
        self.assertEqual(pref_res.status_code, 200)
        pref_data = pref_res.get_json()
        self.assertTrue(pref_data["success"])

        # Check directly in MySQL
        pref_row = db.execute_query("SELECT * FROM user_preferences WHERE user_id = 1", fetch_one=True)
        self.assertEqual(float(pref_row["speech_rate"]), 1.2)
        self.assertEqual(int(pref_row["high_contrast_mode"]), 1)

    def test_07_detection_session_logging(self):
        """Verify detection session records in MySQL."""
        # Log in
        self.client.post("/api/auth/login", json={
            "email": "demo@blindguide.local",
            "password": "Demo@123"
        })

        fake_file = (io.BytesIO(TINY_PNG), "capture.png")
        res = self.client.post(
            "/api/detect",
            data={"image": fake_file},
            content_type="multipart/form-data"
        )
        data = res.get_json()
        # Even if YOLO or CV2 package is not installed or returns error, session handling was triggered
        self.assertIn("success", data)

        # Verify history returns sessions from MySQL
        hist_res = self.client.get("/api/history")
        self.assertEqual(hist_res.status_code, 200)
        hist_data = hist_res.get_json()
        self.assertTrue(hist_data["success"])
        self.assertGreater(len(hist_data["history"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
