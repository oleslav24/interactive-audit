import json
import unittest
from unittest.mock import MagicMock, patch

from app.llm import generate_ai_report


def _base_kwargs(**overrides):
    values = {
        "payload": {
            "page": {},
            "features": {"title": "Demo", "word_count": 10},
            "rubric": {"overall_score": 3, "criteria": []},
        },
        "provider": "none",
        "enabled": True,
        "openai_api_key": None,
        "openai_model": "gpt-5.4-mini",
        "gemini_api_key": None,
        "gemini_model": "gemini-2.5-flash",
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_model": "qwen2.5:7b",
        "timeout_seconds": 1,
    }
    values.update(overrides)
    return values


class LLMProviderTests(unittest.TestCase):
    def test_none_provider_skips_ai(self):
        report = generate_ai_report(**_base_kwargs())

        self.assertFalse(report.used)
        self.assertEqual(report.provider, "none")
        self.assertIsNone(report.model)
        self.assertEqual(report.error, "AI provider is disabled.")

    def test_unknown_provider_returns_configuration_error(self):
        report = generate_ai_report(**_base_kwargs(provider="unknown"))

        self.assertFalse(report.used)
        self.assertEqual(report.provider, "unknown")
        self.assertIn("Unsupported AI_PROVIDER", report.error)

    def test_ollama_provider_parses_json_response(self):
        expected = {
            "summary": "ok",
            "advantages": [],
            "problems": [],
            "recommendations": [],
            "cognitive_load_risk": "low",
            "manual_checks": [],
        }
        fake_response = MagicMock()
        fake_response.__enter__.return_value.read.return_value = json.dumps(
            {"response": json.dumps(expected, ensure_ascii=False)}
        ).encode("utf-8")

        with patch("app.llm.urlopen", return_value=fake_response):
            report = generate_ai_report(**_base_kwargs(provider="ollama"))

        self.assertTrue(report.used)
        self.assertEqual(report.provider, "ollama")
        self.assertEqual(report.model, "qwen2.5:7b")
        self.assertEqual(report.report, expected)


if __name__ == "__main__":
    unittest.main()
