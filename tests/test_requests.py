"""The request the website sends Claude must match the one make_deck.py sends."""

import unittest

from app import app


class RequestOrderTest(unittest.TestCase):
    def test_answer_format_keeps_field_order(self):
        # Claude fills in the answer in the order the fields are listed. If the
        # server sorts them, a term's definition comes before the term, and
        # Claude often gives up with a blank placeholder.
        response = app.test_client().post("/api/claude-request", json={"step": "terms", "transcript_text": "[0] hi"})
        schema = response.get_json()["output_config"]["format"]["schema"]
        term_fields = list(schema["$defs"]["Term"]["properties"])
        self.assertEqual(term_fields, ["term", "definition", "start_seconds"])


if __name__ == "__main__":
    unittest.main()
