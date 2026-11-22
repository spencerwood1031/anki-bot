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
