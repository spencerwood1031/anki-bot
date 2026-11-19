# Anki Bot

Turns YouTube lecture videos into Anki flashcards.
Pipeline: YouTube URL → timestamped transcript → technical terms → 5–15 key ideas → cards → .apkg (genanki).

## Working on this project
- Spencer is learning to build with AI: explain choices as you go, and check in before major decisions.
- Keep code simple and readable over clever.
- Never write or edit anything in `golden/`. Those files are Spencer's hand-written ground truth.
- The pipeline is Phase 1 (no critic pass or frame captures yet). The website (`app.py`, `templates/index.html`, hosted on Render) has a review screen where visitors edit, delete and add cards before downloading.
- The `## Card rules` section below is also sent to Claude in the card-drafting prompt (`ankibot/prompts.py` reads it), so edit the rules there and only there.
- Website: visitors' API keys must never reach our server. The browser calls Claude directly; the server only builds requests (`llm.browser_request`). Never add a server endpoint that takes a key, and never log or store one. `tests/test_key_privacy.py` guards this.
- Two passes: `make_deck.py <url> --terms` makes only the vocab list; the full run writes two vocab cards per term (term → definition and definition → term, both written out, not Anki's reversed note type) plus cards for the main ideas.
- Evals: `evals/eval_terms.py <id>` compares `outputs/<id>/terms.json` against `golden/<id>/jargon.txt` (recall and precision, with Claude judging whether two terms match). `evals/eval_cards.py <id>` compares the main-idea cards against `golden/<id>/cards.md` and checks them against the card rules.


## Card rules
Distilled from Andy Matuschak's "How to write good prompts" and Piotr Wozniak's "20 rules of formulating knowledge".

1. **One idea per card.** Never stitch several clauses into one answer. Extra details go on their own cards.
2. **Why/how over cloze.** Prefer genuine why/how questions. Use cloze only for bare facts like a term or a number.
3. **Sharp why/how.** A why-question needs a specific mechanism as its answer, not a vague one. "Why use bones in stock?" invites "they're cheap"; "How do bones give stock its rich texture?" doesn't.
4. **Precise.** The question must rule out other reasonable answers, so the answer is the same on every review, and short enough to be clearly right or wrong.
5. **No yes/no questions.** Reframe them as open questions.
6. **No sets or lists as answers.** Never ask "What are the parts of X?" Split a list into one-blank cloze cards that keep the list in the same order.
7. **Cues narrow, never give away.** "(a type of function)" is fine; a rhyme or anything containing the answer is not.
8. **Minimum wording.** Cut every word that isn't needed to get the answer. Start the front with a short topic label (e.g. "Neural nets:") instead of long setup wording; this also keeps similar cards from being confused.
9. **Follow the lecture's story.** Main-idea cards walk through the lecture's main line of reasoning, one step per card, so together they read as a chain (training is like compressing the internet → done on a GPU cluster → the result is like a zip file → but lossy). Few cards, no side angles.
10. **No trivia.** No cards on illustrative numbers (costs, counts, sizes, durations), on things mentioned only in passing, or about the speaker ("What analogy does Karpathy use…"). Ask about the idea itself.
11. **Every technical word gets two vocab cards.** Any technical word the lecture uses, even a general one it doesn't explain (GPU, zip file, neural network, compile, binary). Card one: "LLMs: Lossy compression" → its short definition. Card two: "LLMs: " + that definition → "Lossy compression". Write both out as basic cards.
12. **Vocab is concepts, not names or basics.** No product, model or company names (Llama 2, ChatGPT, Claude), no units of storage (byte, gigabyte), no programming languages (C, Python), and no generic words like "state-of-the-art" or "data type".
13. **Definitions hold no numbers or trivia.** No sizes, counts, costs or lecture-specific examples ("140 GB for Llama 2 70B"). Never define a term by its synonym (parameters ↔ weights); say what it is.
14. **Definitions are atomic.** One clause with the core meaning only: no "i.e.", no "e.g.", no parentheses, and nothing after a semicolon. Extra facts belong on their own cards, or nowhere.
15. **Important leftovers get one extra card.** If trimming a definition drops something important that no main-idea card covers, add one question card for it (not another vocab pair). Drop trivia, and drop anything a main-idea card already asks. Example: open-source vs open-weights → "LLMs: What does an open-source model release that an open-weights model doesn't?" → "Its training details and data."
16. **No near-duplicate terms.** When two terms mean almost the same thing in this lecture (open-source model, open-weights model), keep only the one the lecture leans on.

### Examples
- Bad: "What are the characteristics of the Dead Sea?" (too broad). Good: "Where is the Dead Sea located?" → "On the border between Israel and Jordan."
- Bad: "Does chicken stock make vegetable dishes taste like chicken?" (yes/no). Good: an open question about how stock changes the flavor of vegetables.
- Bad: "What does GRE stand for in biochemistry?" Good: "Biochem: GRE" → "glucocorticoid response element."
- Bad definition: "Neural network trained on huge amounts of text to generate text; in essence a parameters file plus code that runs it." Good: "A neural network trained on huge amounts of text to generate text."
- Bad definition: "The structure of a neural network, i.e. how its computations are arranged." Good: "The structure of a neural network."
- Bad definition: "Small program (e.g. in C) that runs the neural network using the parameters." Good: "Small program that runs the neural network using the parameters."
