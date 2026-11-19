"""Guards for the website's promise: visitors' API keys never reach our server.

Run with:  python -m unittest discover tests

The page sends the key only to api.anthropic.com. These tests make sure
nobody later changes the server or page in a way that breaks that.
"""

import unittest
from pathlib import Path

from app import PAGE, app

ROOT = Path(__file__).parent.parent


class KeyPrivacyTest(unittest.TestCase):
    def test_server_never_reads_an_api_key(self):
        # No server code should accept a key: the browser talks to Claude itself.
        server_code = (ROOT / "app.py").read_text()
        self.assertNotIn("api_key", server_code)
        self.assertNotIn("x-api-key", server_code.lower())

    def test_page_only_sends_the_key_to_anthropic(self):
        # The key may appear in exactly one request header, sent by fetchClaude
        # to https://api.anthropic.com. Any new use of it needs a careful look.
        page = PAGE.read_text()
        self.assertEqual(page.count('"x-api-key": apiKey'), 1)
        self.assertNotIn("localStorage", page)
        self.assertNotIn("sessionStorage", page)
        self.assertNotIn("<script src", page)  # no outside scripts that could read it

    def test_browser_may_only_connect_to_us_and_anthropic(self):
        response = app.test_client().get("/")
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("connect-src 'self' https://api.anthropic.com;", policy)


if __name__ == "__main__":
    unittest.main()
