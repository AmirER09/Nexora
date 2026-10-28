from unittest.mock import Mock, patch
import socket

from django.test import SimpleTestCase, override_settings

from .ai import _safe_base_url, call_ai

class FakeAIConfig:
    def __init__(self, provider, base_url="https://api.example.com/v1", model="test-model"):
        self.provider = provider
        self.base_url = base_url
        self.model = model
        self.system_prompt = "Be a practical learning mentor."
        self.temperature = 0.4
        self.max_output_tokens = 512

    def get_api_key(self):
        return "test-secret"

def mock_response(data, status=200):
    result = Mock()
    result.status_code = status
    result.ok = 200 <= status < 300
    result.json.return_value = data
    result.text = ""
    return result

class AIAdapterTests(SimpleTestCase):
    public_dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    messages = [{"role": "user", "content": "Say hello."}]

    @override_settings(DEBUG=True)
    @patch("core.ai.socket.getaddrinfo")
    @patch("core.ai.requests.post")
    def test_openai_compatible_endpoint(self, post, getaddrinfo):
        getaddrinfo.return_value = self.public_dns
        post.return_value = mock_response({"choices": [{"message": {"content": "works"}}]})
        result = call_ai(FakeAIConfig("openai_compatible"), self.messages)
        self.assertEqual(result, "works")
        self.assertEqual(post.call_args.args[0], "https://api.example.com/v1/chat/completions")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])

    @override_settings(DEBUG=True)
    @patch("core.ai.socket.getaddrinfo")
    @patch("core.ai.requests.post")
    def test_anthropic_messages_api(self, post, getaddrinfo):
        getaddrinfo.return_value = self.public_dns
        post.return_value = mock_response({"content": [{"type": "text", "text": "Claude works"}]})
        result = call_ai(FakeAIConfig("anthropic", "https://api.anthropic.com"), self.messages)
        self.assertEqual(result, "Claude works")
        self.assertEqual(post.call_args.args[0], "https://api.anthropic.com/v1/messages")
        self.assertEqual(post.call_args.kwargs["headers"]["x-api-key"], "test-secret")

    @override_settings(DEBUG=True)
    @patch("core.ai.requests.post")
    def test_gemini_uses_api_key_header(self, post):
        post.return_value = mock_response({"candidates": [{"content": {"parts": [{"text": "Gemini works"}]}}]})
        result = call_ai(FakeAIConfig("gemini"), self.messages)
        self.assertEqual(result, "Gemini works")
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-secret")

    def test_public_http_endpoint_is_rejected(self):
        with self.assertRaises(RuntimeError):
            _safe_base_url("http://example.com/v1")

    def test_private_ip_endpoint_is_rejected(self):
        with self.assertRaises(RuntimeError):
            _safe_base_url("https://192.168.1.10/v1")

    @override_settings(DEBUG=True)
    def test_localhost_endpoint_allowed_only_for_development(self):
        self.assertEqual(_safe_base_url("http://127.0.0.1:4096/v1"), "http://127.0.0.1:4096/v1")

    @override_settings(DEBUG=False)
    def test_localhost_endpoint_rejected_in_production(self):
        with self.assertRaises(RuntimeError):
            _safe_base_url("http://127.0.0.1:4096/v1")
