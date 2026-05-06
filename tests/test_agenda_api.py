import os
import unittest
from unittest.mock import patch

os.environ.setdefault("AGENDA_API_KEY", "test-api-key")
os.environ.setdefault("AGENDA_SECRET_KEY", "test-secret-key")
os.environ.setdefault("AGENDA_RESET_TOKEN", "test-reset-token")

from agenda_app import create_app


class AgendaApiTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.api_key = self.app.config["API_KEY"]
        self.reset_token = self.app.config["ADMIN_RESET_TOKEN"]

    def test_crear_agenda_sin_api_key(self):
        resp = self.client.post("/api/agenda", json={})
        self.assertEqual(resp.status_code, 401)

    def test_crear_agenda_con_api_key(self):
        data = {
            "sede": "X",
            "cc": "123456",
            "fecha": "hoy",
            "hora_inicio": "08:00",
            "duracion_min": 15,
            "cantidad": 1,
        }
        resp = self.client.post(
            "/api/agenda",
            json=data,
            headers={"X-API-Key": self.api_key},
        )
        self.assertIn(resp.status_code, (202, 400))

    def test_reset_requiere_token_adicional(self):
        resp = self.client.post(
            "/api/reset",
            headers={"X-API-Key": self.api_key},
        )
        self.assertEqual(resp.status_code, 403)

    @patch("subprocess.run")
    def test_reset_con_token(self, _mock_run):
        resp = self.client.post(
            "/api/reset",
            headers={
                "X-API-Key": self.api_key,
                "X-Reset-Token": self.reset_token,
            },
        )
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()

