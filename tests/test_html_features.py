import unittest

from app.html_features import extract_features


class HTMLFeatureTests(unittest.TestCase):
    def test_extracts_core_publication_features(self):
        html = """
        <!doctype html>
        <html lang="ru">
          <head>
            <title>Интерактивное издание</title>
            <meta name="description" content="Тестовый лонгрид">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>@media (max-width: 700px) { body { font-size: 16px; } }</style>
          </head>
          <body>
            <nav><a href="#part1">Раздел</a></nav>
            <main>
              <h1>Главная тема</h1>
              <h2 id="part1">Первый раздел</h2>
              <p>Это большой фрагмент текста про цифровое интерактивное издание.</p>
              <img src="cover.jpg" alt="Обложка">
              <img src="chart.jpg">
              <video controls></video>
              <button aria-label="Открыть карту"></button>
            </main>
          </body>
        </html>
        """

        features = extract_features(html)

        self.assertEqual(features.title, "Интерактивное издание")
        self.assertEqual(features.language, "ru")
        self.assertTrue(features.has_viewport_meta)
        self.assertEqual(features.css_media_queries_count, 1)
        self.assertEqual(features.images_count, 2)
        self.assertEqual(features.images_without_alt, 1)
        self.assertEqual(features.videos_count, 1)
        self.assertEqual(features.nav_count, 1)
        self.assertEqual(features.headings["h1"], ["Главная тема"])

    def test_detects_autoplay_and_unlabeled_controls(self):
        html = """
        <html><body>
          <h1>Материал</h1>
          <video autoplay></video>
          <audio autoplay></audio>
          <button></button>
          <a href="/empty"></a>
        </body></html>
        """

        features = extract_features(html)

        self.assertEqual(features.videos_autoplay_count, 1)
        self.assertEqual(features.audios_autoplay_count, 1)
        self.assertEqual(features.unlabeled_buttons_count, 1)
        self.assertEqual(features.unlabeled_links_count, 1)


if __name__ == "__main__":
    unittest.main()
