"""Guards for the website's promise: visitors' API keys never reach our server.

Run with:  python -m unittest discover tests

The page sends the key only to api.anthropic.com. These tests make sure
nobody later changes the server or page in a way that breaks that.
"""

import unittest
from pathlib import Path

import re

from app import KATEX_SCRIPT, PAGE, app, page_script_hash

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
        # No outside scripts that could read it. The one script file is our own
        # copy of KaTeX (it draws math), served by us, never another site.
        self.assertEqual(re.findall(r'<script src="([^"]*)"', page), [KATEX_SCRIPT])

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
        # Plus exactly one file on our own server: our copy of KaTeX.
        self.assertEqual(script_rule, f"script-src {page_script_hash()} localhost{KATEX_SCRIPT}")
        self.assertNotIn("unsafe", script_rule)
        page = PAGE.read_text()
        self.assertEqual(page.count("<script>"), 1)  # the fingerprint covers one inline block
        self.assertEqual(page.count("<script"), 2)  # and the KaTeX file
        self.assertNotIn("innerHTML", page)  # card text is shown as text, never as HTML

    def test_page_refuses_to_send_a_key_to_our_server(self):
        # Every request to our server goes through postJson, which stops if
        # the data holds a key (a visitor pasting it into the wrong box).
        page = PAGE.read_text()
        self.assertIn("if (looksLikeKey(text))", page)
        self.assertIn("/sk-ant-/i.test(text)", page)

    def test_page_blocks_pasting_a_key_into_other_boxes(self):
        # A key pasted into the transcript, URL or a card box is stopped right away.
        page = PAGE.read_text()
        self.assertIn('document.addEventListener("paste"', page)
        self.assertIn('if (box.id === "api-key"', page)
        self.assertEqual(page.count("fetch("), 2)  # postJson (us) and fetchClaude (Anthropic)

    def test_site_insists_on_https(self):
        response = app.test_client().get("/")
        self.assertIn("max-age=", response.headers["Strict-Transport-Security"])


if __name__ == "__main__":
    unittest.main()
