"""Each step's prompt must carry the rules meant for it, read from CLAUDE.md."""

from ankibot import prompts


def test_rules_picks_only_the_numbers_asked_for():
    lines = prompts.rules([11, 14]).splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("11. ") and lines[1].startswith("14. ")


def test_terms_step_gets_the_vocab_rules_and_examples():
    system = prompts.terms_system()
    assert "**Definitions are atomic.**" in system
    assert "- Bad definition" in system
    assert "**Why/how over cloze.**" not in system   # a card-wording rule: not this step's job


def test_ideas_step_gets_the_overlap_rule():
    assert "**No overlapping cards.**" in prompts.ideas_system()


def test_critic_sees_each_terms_seconds_so_it_can_keep_them():
    from ankibot.llm import Term
    text = prompts.critic_user("[0] hi", [Term(term="derivative", definition="A rate", start_seconds=754)], [])
    assert "[754] derivative" in text


def test_additional_context_reaches_every_step_only_when_given():
    from ankibot import llm
    data = {"transcript_text": "[0] hi", "terms": [], "ideas": [], "cards": [], "context": "I'm a nurse"}
    for step in ["terms", "ideas", "cards", "review"]:
        assert "I'm a nurse" in llm.browser_request(step, data)["messages"][0]["content"]
    data["context"] = "  "
    assert "learner_context" not in llm.browser_request("terms", data)["messages"][0]["content"]


def test_answers_never_end_with_a_period():
    from ankibot.deck import no_end_period
    assert no_end_period("Its training details and data.") == "Its training details and data"
    assert no_end_period("Lord Raglan") == "Lord Raglan"
    assert no_end_period("It trails off...") == "It trails off..."
    assert no_end_period("The U.S.") == "The U.S."
    assert no_end_period("$x = 1.$") == "$x = 1.$"


def test_notes_reach_every_step_only_when_given():
    from ankibot import llm
    # The website's "Your notes" box: added to every step, with or without extra ideas.
    data = {"transcript_text": "[0] hi", "terms": [], "ideas": [], "cards": [], "notes": "Softmax: makes probabilities"}
    for step in ["terms", "ideas", "cards", "review"]:
        content = llm.browser_request(step, data)["messages"][0]["content"]
        assert "<learner_notes>" in content and "Softmax: makes probabilities" in content
        assert "at most 5 extra ideas" in content
    data["notes_extras"] = False
    assert "Add no ideas or terms beyond the notes" in llm.browser_request("ideas", data)["messages"][0]["content"]
    data["notes"] = "  "
    assert "learner_notes" not in llm.browser_request("terms", data)["messages"][0]["content"]


def test_cards_carry_not_in_notes():
    from ankibot import llm
    # Extra ideas keep their mark through the card writer and the rules check.
    schema = llm.browser_request("review", {"transcript_text": "", "terms": [], "cards": []})["output_config"]["format"]["schema"]
    assert "not_in_notes" in str(schema)
    card = llm.Card(card_type="basic", front="Q", back="A", start_seconds=0, not_in_notes=True)
    assert "(not in notes)" in llm.prompts.critic_user("", [], [card])
