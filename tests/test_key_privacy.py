"""Guards for the website's promise: visitors' API keys never reach our server.

Run with:  python -m unittest discover tests

The page sends the key only to api.anthropic.com. These tests make sure
nobody later changes the server or page in a way that breaks that.
"""

import unittest
from pathlib import Path

from app import PAGE, app, page_script_hash

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

    def test_only_our_own_script_may_run(self):
        # An injected script could read the key off the page, so the browser is
        # told to run only the page's own script (matched by its fingerprint).
        response = app.test_client().get("/")
        policy = response.headers["Content-Security-Policy"]
        script_rule = [rule for rule in policy.split("; ") if rule.startswith("script-src")][0]
        self.assertEqual(script_rule, "script-src " + page_script_hash())
        self.assertNotIn("unsafe", script_rule)
        page = PAGE.read_text()
        self.assertEqual(page.count("<script"), 1)  # the fingerprint covers one block
        self.assertNotIn("innerHTML", page)  # card text is shown as text, never as HTML

    def test_page_refuses_to_send_a_key_to_our_server(self):
        # Every request to our server goes through postJson, which stops if
        # the data holds a key (a visitor pasting it into the wrong box).
        page = PAGE.read_text()
        self.assertIn('text.includes("sk-ant-")', page)
        self.assertEqual(page.count("fetch("), 2)  # postJson (us) and fetchClaude (Anthropic)

    def test_site_insists_on_https(self):
        response = app.test_client().get("/")
        self.assertIn("max-age=", response.headers["Strict-Transport-Security"])


if __name__ == "__main__":
    unittest.main()
