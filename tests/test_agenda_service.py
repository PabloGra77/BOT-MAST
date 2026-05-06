import unittest
from unittest.mock import patch

from agenda_app.application.job_service import clear_all_jobs, crear_job_agenda, get_job_snapshot, jobs
from agenda_app.domain.requests import AgendaRequest


class AgendaServiceTest(unittest.TestCase):
    def setUp(self):
        clear_all_jobs()

    @patch("agenda_app.application.job_service.run_bot_job")
    def test_crear_job_valido(self, _mock_run_bot_job):
        data = {
            "sede": "RM MANIZALES",
            "cc": "29816379",
            "fecha": "hoy",
            "hora_inicio": "08:00",
            "duracion_min": 15,
            "cantidad": 2,
        }
        req = AgendaRequest.from_dict(data)
        job_id = crear_job_agenda(req)
        self.assertIn(job_id, jobs)
        self.assertIsNotNone(get_job_snapshot(job_id))

    def test_validacion_fecha_invalida(self):
        data = {
            "sede": "X",
            "cc": "123",
            "fecha": "99/99/9999",
            "hora_inicio": "08:00",
            "duracion_min": 15,
            "cantidad": 1,
        }
        with self.assertRaises(ValueError):
            AgendaRequest.from_dict(data)


if __name__ == "__main__":
    unittest.main()

