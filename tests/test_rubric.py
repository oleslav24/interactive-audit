import unittest

from app.domain import PageSnapshot
from app.html_features import extract_features
from app.rubric import evaluate_page


class RubricTests(unittest.TestCase):
    def test_rubric_penalizes_autoplay_and_missing_accessibility(self):
        html = """
        <html>
          <head><title>Demo</title></head>
          <body>
            <h1>Demo</h1>
            <p>Короткий текст.</p>
            <img src="x.png">
            <video autoplay></video>
            <button></button>
          </body>
        </html>
        """
        snapshot = PageSnapshot(
            requested_url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            html=html,
            elapsed_ms=100,
            fetched_at="2026-06-13T00:00:00+00:00",
        )
        rubric = evaluate_page(extract_features(html), snapshot)
        by_key = {criterion.key: criterion for criterion in rubric.criteria}

        self.assertLessEqual(by_key["multimedia_cognition"].score, 2)
        self.assertLessEqual(by_key["accessibility"].score, 3)
        self.assertTrue(rubric.recommendations)

    def test_rubric_rewards_structured_navigation(self):
        html = """
        <html lang="ru">
          <head>
            <title>Longread</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>@media (max-width: 700px) { main { display: block; } }</style>
          </head>
          <body>
            <nav><a href="#a">A</a><a href="#b">B</a><a href="#c">C</a></nav>
            <main>
              <h1>Тема</h1>
              <h2 id="a">A</h2><p>Текст раздела один.</p>
              <h2 id="b">B</h2><p>Текст раздела два.</p>
              <h2 id="c">C</h2><p>Текст раздела три.</p>
              <button>Показать карту</button>
              <img src="x.png" alt="Схема">
            </main>
          </body>
        </html>
        """
        rubric = evaluate_page(extract_features(html))
        by_key = {criterion.key: criterion for criterion in rubric.criteria}

        self.assertGreaterEqual(by_key["navigation_control"].score, 4)
        self.assertGreaterEqual(by_key["visual_structure"].score, 4)


if __name__ == "__main__":
    unittest.main()
