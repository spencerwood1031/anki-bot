"""Math on cards: LaTeX between \\( and \\) that Anki draws with its built-in MathJax.

Run with:  python -m unittest discover tests
"""

import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from app import KATEX_SCRIPT, app
from ankibot import deck, prompts


class MathTest(unittest.TestCase):
    def test_katex_files_are_served(self):
        client = app.test_client()
        self.assertEqual(client.get(KATEX_SCRIPT).status_code, 200)
        self.assertEqual(client.get("/static/katex/katex.min.css").status_code, 200)
        self.assertEqual(client.get("/static/katex/fonts/KaTeX_Main-Regular.woff2").status_code, 200)

    def test_terms_step_gets_the_math_rule(self):
        self.assertIn("Math is written in LaTeX", prompts.terms_system())

    def test_deck_keeps_latex_and_escapes_html(self):
        # "<" inside math must reach Anki as text, or Anki reads it as an HTML tag.
        cards = [{"card_type": "basic", "front": r"What does \(x < y\) say?", "back": r"\(\sqrt{2}\)"}]
        path = Path(tempfile.mkdtemp()) / "deck.apkg"
        deck.build_deck("test", "Test", cards, str(path))
        with zipfile.ZipFile(path) as apkg:
            apkg.extract("collection.anki2", path.parent)
        fields = sqlite3.connect(path.parent / "collection.anki2").execute("select flds from notes").fetchone()[0]
        self.assertIn(r"What does \(x &lt; y\) say?", fields)
        self.assertIn(r"\(\sqrt{2}\)", fields)


if __name__ == "__main__":
    unittest.main()
