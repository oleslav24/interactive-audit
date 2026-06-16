import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from app.domain import PageSnapshot
from app.server import build_server
from app.server import analyze_url_request


class ServerTests(unittest.TestCase):
    def test_health_endpoint(self):
        server = build_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            with urlopen(f"http://{host}:{port}/health", timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["runtime"], "stdlib-http")

    def test_analyze_request_pipeline_without_network(self):
        html = """
        <html lang="ru">
          <head>
            <title>Проверяемое издание</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
          </head>
          <body>
            <nav><a href="#intro">Введение</a><a href="#media">Медиа</a><a href="#end">Итог</a></nav>
            <main>
              <h1>Проверяемое издание</h1>
              <h2 id="intro">Введение</h2>
              <p>Текст интерактивного издания с понятной структурой.</p>
              <h2 id="media">Медиа</h2>
              <img src="cover.jpg" alt="Обложка">
              <button>Открыть карту</button>
              <h2 id="end">Итог</h2>
            </main>
          </body>
        </html>
        """
        snapshot = PageSnapshot(
            requested_url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            html=html,
            elapsed_ms=50,
            fetched_at="2026-06-15T00:00:00+00:00",
        )

        with patch("app.server.fetch_url", return_value=snapshot):
            result = analyze_url_request(
                {
                    "url": "https://example.com",
                    "use_ai": False,
                    "include_features": False,
                }
            )

        self.assertEqual(result["status"], "ok")
        self.assertIsNone(result["features"])
        self.assertEqual(result["ai"]["used"], False)
        self.assertIn("heuristic_report", result)
        self.assertGreaterEqual(result["rubric"]["overall_score"], 1)


if __name__ == "__main__":
    unittest.main()
