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
- Two passes: `make_deck.py <url> --terms` makes only the vocab list; the full run makes two vocab cards per term (term → definition and definition → term, both written out, not Anki's reversed note type), built in code from the terms list (`llm.vocab_cards`), plus main-idea cards written by Claude.
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
12. **Vocab is concepts, not names or basics.** No product, model or company names (Llama 2, ChatGPT, Claude), no units of storage (byte, gigabyte), no programming languages (C, Python), and no generic words like "state-of-the-art", "data type" or "objective". General machine-learning words (training set, evaluation, optimization) can stay; the user can cut them. Only terms people in the field actually use: a phrase the speaker coins for an idea ("inscrutable artifact", "dreaming") gets a main-idea question instead, and nothing that appears only in one of the lecture's examples (ISBN).
13. **Definitions hold no numbers or trivia.** No sizes, counts, costs or lecture-specific examples ("140 GB for Llama 2 70B"). Never define a term by its synonym (parameters ↔ weights); say what it is.
14. **Definitions are atomic.** One clause with the core meaning only: no "i.e.", no "e.g.", no parentheses, no trailing "which…" clause, and nothing after a semicolon. Extra facts belong on their own cards, or nowhere.
15. **Important leftovers get one extra card.** If trimming a definition drops something important that no main-idea card covers, add one question card for it (not another vocab pair). Drop trivia, and drop anything a main-idea card already asks. Example: open-source vs open-weights → "LLMs: What does an open-source model release that an open-weights model doesn't?" → "Its training details and data."
16. **No near-duplicate terms.** When two terms mean almost the same thing in this lecture (open-source model and open-weights model; language model and LLM), keep only the one the lecture leans on.
17. **Main-idea answers are atomic too.** The shortest answer that is still right: drop secondary clauses and "and how…" add-ons. "In the parameter values", not "In the parameter values and how they are obtained; the architecture is fully understood."
18. **Ask the general lesson, not the lecture's example.** "How do models improve?" → "By scaling data and compute", not "How do state-of-the-art models get beyond Llama 2?" But keep the lecture's analogies: they make an idea easier to digest and remember. Ask about the analogy itself, not who said it: "How can we picture the result of training?" → "A zip file of the internet", not "What analogy does Karpathy use?"
19. **Contrasts name both sides.** "How does training's compression differ from a zip file?" → "Training's compression is lossy; a zip file is lossless."
20. **No overlapping cards.** Each card must test something no other card in the deck tests. Don't circle one idea from several angles ("we don't understand the parameters", "LLMs are inscrutable artifacts", "unlike a car, we don't understand the parts"): pick the single best card for it, and prefer the one with the lecture's analogy.
21. **Cards stand alone.** Cards get merged into larger decks later, so no card or definition may mention "the lecture", "the speaker" or "this video". Not "The lecture's description of LLMs as…"; say what the thing is.

### Examples
- Bad: "What are the characteristics of the Dead Sea?" (too broad). Good: "Where is the Dead Sea located?" → "On the border between Israel and Jordan."
- Bad: "Does chicken stock make vegetable dishes taste like chicken?" (yes/no). Good: an open question about how stock changes the flavor of vegetables.
- Bad: "What does GRE stand for in biochemistry?" Good: "Biochem: GRE" → "glucocorticoid response element."
- Bad definition: "Neural network trained on huge amounts of text to generate text; in essence a parameters file plus code that runs it." Good: "A neural network trained on huge amounts of text to generate text."
- Bad definition: "The structure of a neural network, i.e. how its computations are arranged." Good: "The structure of a neural network."
- Bad definition of parroting: "Reproducing training documents verbatim." Good: "Generating statistically likely text by mimicking patterns from training data without genuine comprehension."
- Bad definition: "Small program (e.g. in C) that runs the neural network using the parameters." Good: "Small program that runs the neural network using the parameters."

### A good main-idea set (Spencer's cards for the first part of Karpathy's "Intro to LLMs")
Copy this style, not the content.
- "LLMs: The two files that make up an LLM are {{c1::a parameters file}} and {{c2::a run file}}."
- "LLMs: What can you do with an open-weights model that you can't with ChatGPT?" → "Download it and fine-tune it yourself."
- "LLMs: Where does a model's "magic" lie, given its simple code?" → "In the parameter values."
- "LLMs: Why does training cost far more than running a model?" → "Training has to find the parameters; running uses the already-set parameters."
- "LLMs: How can we picture model training?" → "Compressing a chunk of the internet."
- "LLMs: What do we use to compress a chunk of the internet?" → "A GPU cluster."
- "LLMs: What is the result of compressing a chunk of the internet like?" → "A zip file of the internet."
- "LLMs: How does training's compression differ from a zip file?" → "Training's compression is lossy; a zip file is lossless."
- "LLMs: How do models improve?" → "By scaling data and compute."

Cards Spencer cut from that lecture, and why:
- "How do you run an open-weights LLM on a laptop?" (a how-to procedure, not an idea)
- "How is the size of a parameters file determined?" (arithmetic trivia)
- "How does the cost of training compare with running it?" (asks for a comparison; ask why instead)
- Vocab terms: dependencies, compression ratio, training run, computational complexity, data type, state-of-the-art (generic words, not concepts of the subject)
