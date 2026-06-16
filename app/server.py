from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from .config import get_settings
from .fetcher import FetchError, URLValidationError, fetch_url
from .html_features import extract_features
from .llm import generate_ai_report
from .reporting import build_heuristic_report, build_payload
from .rubric import RUBRIC_DEFINITION, evaluate_page


def _json_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


class ExpertAnalysisHandler(BaseHTTPRequestHandler):
    server_version = "ExpertAnalysisHTTP/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        body = _json_bytes(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(HTTPStatus.NO_CONTENT, {})

    def do_GET(self) -> None:  # noqa: N802
        settings = get_settings()
        if self.path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "ai_enabled": settings.ai_enabled,
                    "openai_model": settings.openai_model,
                    "runtime": "stdlib-http",
                },
            )
            return

        if self.path == "/api/rubric":
            self._send_json(HTTPStatus.OK, {"criteria": RUBRIC_DEFINITION})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/analyze":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        try:
            payload = self._read_json_body()
            result = analyze_url_request(payload)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except URLValidationError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except FetchError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, result)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Request body is empty.")
        if content_length > 64_000:
            raise ValueError("Request body is too large.")
        raw = self.rfile.read(content_length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object.")
        return data


def analyze_url_request(data: dict[str, Any]) -> dict[str, Any]:
    url = str(data.get("url", "")).strip()
    if not url:
        raise ValueError("Field 'url' is required.")

    use_ai = bool(data.get("use_ai", True))
    include_features = bool(data.get("include_features", True))
    settings = get_settings()

    snapshot = fetch_url(
        url,
        timeout_seconds=settings.fetch_timeout_seconds,
        max_bytes=settings.fetch_max_bytes,
        allow_private=settings.allow_private_urls,
    )
    features = extract_features(snapshot.html)
    rubric_result = evaluate_page(features, snapshot)
    analysis_payload = build_payload(snapshot, features, rubric_result)
    heuristic_report = build_heuristic_report(snapshot, features, rubric_result)
    ai_report = generate_ai_report(
        analysis_payload,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        enabled=use_ai and settings.ai_enabled,
    )

    return {
        "status": "ok",
        "page": analysis_payload["page"],
        "features": analysis_payload["features"] if include_features else None,
        "rubric": analysis_payload["rubric"],
        "heuristic_report": heuristic_report,
        "ai": {
            "used": ai_report.used,
            "model": ai_report.model,
            "report": ai_report.report,
            "error": ai_report.error,
        },
    }


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), ExpertAnalysisHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run expert analysis backend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    server = build_server(args.host, args.port)
    print(f"Expert analysis backend: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
