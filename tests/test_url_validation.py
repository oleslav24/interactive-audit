import unittest

from app.fetcher import URLValidationError, normalize_url, validate_public_url


class URLValidationTests(unittest.TestCase):
    def test_normalize_adds_https_scheme(self):
        self.assertEqual(normalize_url("example.com/demo"), "https://example.com/demo")

    def test_rejects_non_http_scheme(self):
        with self.assertRaises(URLValidationError):
            validate_public_url("file:///etc/passwd")

    def test_rejects_loopback_ip(self):
        with self.assertRaises(URLValidationError):
            validate_public_url("http://127.0.0.1:8000")

    def test_allows_loopback_when_explicitly_enabled(self):
        self.assertEqual(
            validate_public_url("http://127.0.0.1:8000", allow_private=True),
            "http://127.0.0.1:8000",
        )


if __name__ == "__main__":
    unittest.main()
