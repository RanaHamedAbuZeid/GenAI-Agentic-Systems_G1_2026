# Week 03 — Chat Completion API with Automated Token & Cost Analysis

**Course:** GenAI & Agentic Systems (ITI)
**Week 03 topic:** Gen-AI Tools for the Modern Developer
**Task:** Python script calling a Chat Completion API with automated token & cost analysis
**Author:** Rana Hamed

---

## 1. Overview

This project calls a Large Language Model (LLM) directly from Python through the
**Chat Completion API** format, and automatically measures how many **tokens** each
call uses and how much it **costs**.

It covers all the Week 03 topics:

| Week 03 topic | Where it is in the code |
|---|---|
| Direct API integration | `OpenAI(...)` client + `client.chat.completions.create(...)` |
| System instructions | `SYSTEM_INSTRUCTION`, sent as the `system` message |
| Prompt templates | `PROMPT_TEMPLATE` with `{topic}` and `{length}` placeholders |
| Token economics | Input vs output tokens, pre-call estimate with `tiktoken` |
| Streaming responses | `--stream` mode, `stream=True`, usage taken from the last chunk |
| Cost calculation | `calculate_cost()` using the official price table |

**Provider and model:** Google Gemini `gemini-3.1-flash-lite`, called through Google's
**OpenAI-compatible endpoint** with the official `openai` Python library.

**Cost to run: $0.** The project uses the Gemini API **free tier**, with no billing account linked.
The script reports the actual cost ($0) and the **paid-tier equivalent cost**, which is
what the same calls would cost on the paid tier.

---

## 2. Key concepts

**Chat Completion API.** The standard way to talk to an LLM from code. You send a
list of messages, each with a `role`:
- `system` sets the model's behaviour and style.
- `user` is the actual question.

The API returns the answer plus a `usage` object with the token counts.

**Tokens.** Models read and write text in small pieces called tokens, not words.
In English one word is roughly 1 to 1.5 tokens. Providers charge per token.

**Input vs output tokens.**
- *Input tokens* (`prompt_tokens`): the system instruction and the prompt you send.
- *Output tokens* (`completion_tokens`): the answer the model writes.

Output tokens are more expensive. For this model they cost **6× more** than input tokens.

**Cost formula** (prices are quoted per 1 million tokens):

```
cost = input_tokens / 1,000,000 × input_price
     + output_tokens / 1,000,000 × output_price
```

**Pre-call estimate.** `tiktoken` counts tokens locally **before** sending, at no cost.
It is OpenAI's tokenizer, not Gemini's, so the estimate is approximate and is compared
with the exact count returned by the API.

**Streaming.** With `stream=True` the answer arrives in pieces (chunks) while it is
being generated, instead of all at once.
- **TTFT (Time To First Token)** measures how quickly the first words appear.
- **Total time** is when the full answer has arrived.
- In streaming mode the token usage is sent in the **last chunk**, requested with
  `stream_options={"include_usage": True}`.

---

## 3. Project structure

```
TASK3/
├── token_cost_analyzer.py   # final script (normal + streaming modes)
├── steps/                   # step-by-step development history
│   ├── step1_basic_call.py  # 1 call, print answer + raw token usage
│   ├── step2_cost.py        # + automatic cost calculation
│   ├── step3_templates.py   # + system instruction, prompt template, 3 topics, summary table
│   ├── step4_estimate.py    # + pre-call token estimate (tiktoken) vs actual
│   └── step5_streaming.py   # + streaming, TTFT and total time
├── reports/                 # CSV + JSON report generated on every run
├── screenshots/             # output screenshots for the submission
├── requirements.txt         # Python libraries
├── .env.example             # template for the API key file
├── .gitignore               # keeps .env and .venv out of Git
└── README.md
```

The real `.env` file holds the private API key. It is **not** part of the submission.

---

## 4. Setup (Windows)

1. **Get a free API key** at Google AI Studio (aistudio.google.com) → *Get API key*.
   Do **not** click *Set up billing*. Without a billing account the project stays on the
   free tier and cannot be charged.
2. **Create `.env`.** Copy `.env.example` to `.env` and put your key after `GEMINI_API_KEY=`.
3. **Open a terminal in the project folder.** In File Explorer, click the address bar,
   type `cmd`, and press Enter.
4. **Create and activate a virtual environment:**
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
5. **Install the libraries:**
   ```
   python -m pip install -r requirements.txt
   ```
   `python -m pip` is used instead of `pip` because managed Windows devices
   (Device Guard) may block the unsigned `pip.exe` launcher.

---

## 5. Usage

```
python token_cost_analyzer.py            # normal mode
python token_cost_analyzer.py --stream   # streaming mode
```

Each run:
1. fills the prompt template for every topic in `TOPICS`;
2. prints the estimated input tokens **before** each call;
3. prints the answer, either all at once or live in streaming mode;
4. prints the actual tokens, the estimate difference, the cost and the timing;
5. prints a summary table and saves `reports/run_<date>_<time>_<mode>.csv` and `.json`.

All settings (model, prices, system instruction, template, topics) are in the
**SETTINGS** section at the top of `token_cost_analyzer.py`.

---

## 6. Pricing used

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| `gemini-3.1-flash-lite` | $0.25 | $1.50 |

These are the Standard paid-tier text prices, from https://ai.google.dev/pricing (checked 2026-11-25).
Prices change over time; update the `PRICING` dictionary if Google changes them.

---

## 7. Results

All results below are from real calls to `gemini-3.1-flash-lite` on the free tier,
and match the screenshots in `screenshots/`.

**System instruction:** `You are a concise educational assistant. Answer only in short bullet points.`
**Prompt template:** `Summarize the main benefits of {topic} in {length} short bullet points.`
(`length = "3 lines"`)

### 7.1 Final script — normal mode (`python token_cost_analyzer.py`)

| Topic | Est. input | Actual input | Diff | Output | Total time (s) | Paid-tier cost (USD) |
|---|---|---|---|---|---|---|
| drinking water in the morning | 34 | 35 | +2.9% | 33 | 1.27 | 0.00005825 |
| learning data structures and algorithms early | 35 | 36 | +2.8% | 40 | 36.46 | 0.00006900 |
| using Git version control in student projects | 36 | 37 | +2.7% | 65 | 24.08 | 0.00010675 |
| **Total** | **105** | **108** | **+2.8%** | **138** | | **0.00023400** |

**Actual cost (free tier): $0.00.** Reports: `reports/run_20261127_124628_normal.csv` / `.json`

### 7.2 Final script — streaming mode (`python token_cost_analyzer.py --stream`)

| Topic | Est. input | Actual input | Output | TTFT (s) | Total time (s) | Chunks | Paid-tier cost (USD) |
|---|---|---|---|---|---|---|---|
| drinking water in the morning | 34 | 35 | 31 | 33.41 | 33.44 | 3 | 0.00005525 |
| learning data structures and algorithms early | 35 | 36 | 40 | 1.16 | 1.28 | 3 | 0.00006900 |
| using Git version control in student projects | 36 | 37 | 49 | 4.82 | 5.08 | 4 | 0.00008275 |
| **Total** | **105** | **108** | **120** | | | | **0.00020700** |

**Actual cost (free tier): $0.00.** Reports: `reports/run_20261127_124843_stream.csv` / `.json`

### 7.3 Development runs (steps 1–5)

**Steps 1–2: single call (water topic, earlier system instruction "health and study assistant")**

| Run | Input | Output | Total | Paid-tier cost (USD) |
|---|---|---|---|---|
| Step 1 — basic call | 37 | 29 | 66 | 0.00005275 |
| Step 2 — cost calculation | 37 | 36 | 73 | 0.00006325 |

**Step 3: prompt template, 3 topics**

| Topic | Input | Output | Paid-tier cost (USD) |
|---|---|---|---|
| drinking water in the morning | 35 | 33 | 0.00005825 |
| learning data structures and algorithms early | 36 | 41 | 0.00007050 |
| using Git version control in student projects | 37 | 45 | 0.00007675 |
| **Total** | **108** | **119** | **0.00020550** |

**Step 4: pre-call estimate vs actual**

| Topic | Est. input | Actual input | Diff | Output | Paid-tier cost (USD) |
|---|---|---|---|---|---|
| drinking water in the morning | 34 | 35 | +2.9% | 33 | 0.00005825 |
| learning data structures and algorithms early | 35 | 36 | +2.8% | 38 | 0.00006600 |
| using Git version control in student projects | 36 | 37 | +2.7% | 53 | 0.00008875 |
| **Total** | **105** | **108** | **+2.8%** | **124** | **0.00021300** |

**Step 5: streaming**

| Topic | Est. input | Input | Output | TTFT (s) | Total time (s) | Chunks | Paid-tier cost (USD) |
|---|---|---|---|---|---|---|---|
| drinking water in the morning | 34 | 35 | 32 | 22.47 | 22.56 | 3 | 0.00005675 |
| learning data structures and algorithms early | 35 | 36 | 39 | 80.68 | 80.78 | 3 | 0.00006750 |
| using Git version control in student projects | 36 | 37 | 48 | 2.25 | 2.40 | 4 | 0.00008125 |
| **Total** | | **108** | **119** | | | | **0.00020550** |

### 7.4 Output tokens across all runs (same prompts)

| Topic | Step 3 | Step 4 | Step 5 | Final normal | Final stream | Range |
|---|---|---|---|---|---|---|
| drinking water in the morning | 33 | 33 | 32 | 33 | 31 | 31–33 |
| learning data structures and algorithms early | 41 | 38 | 39 | 40 | 40 | 38–41 |
| using Git version control in student projects | 45 | 53 | 48 | 65 | 49 | 45–65 |

Input tokens were identical in every run: 35, 36 and 37.

---

## 8. Findings

1. **Output tokens drive the cost.** Input and output tokens are roughly equal in
   count, but output accounts for **≈87–88% of the cost** in every 3-topic run,
   because output is 6× more expensive. For example, the final normal run had 108
   input and 138 output tokens, and output was 88% of the cost. Limiting answer
   length is the most effective way to cut cost.
2. **Input tokens are predictable; output tokens are not.** The same prompt always
   gave the same input count (35, 36, 37) in every run. Output varied between runs
   (Git topic: 45 to 65 tokens, table 7.4), because the model generates text
   probabilistically. As a result, the total cost of the same three prompts ranged
   from $0.00020550 to $0.00023400.
3. **Formatting costs tokens.** In the final normal run the model added Markdown
   bold headings (`**Collaboration:**`, `**Safety:**`, `**Backup:**`) to the Git
   answer without being asked. That answer used 65 output tokens, the most of any
   call, and was the most expensive call ($0.00010675).
4. **The `tiktoken` estimate was ≈97% accurate.** In all 12 estimated calls it was
   exactly **1 token lower** than Gemini's count. The constant gap suggests a fixed
   formatting token added by the API rather than a tokenizer difference; this is
   an inference from the data, not documented behaviour.
5. **The system instruction is paid on every call.** Shortening it by two words
   ("health and study" → "educational") lowered the input from 37 to 35 tokens for
   the same question.
6. **Streaming improves the waiting experience, not cost or total time.**
   - Most of the response time was spent **before the first token** (TTFT): between
     91% and 99.9% of the total in the six streamed calls.
   - Generating the short answers took only 0.03–0.26 s.
   - TTFT varied enormously, from 1.16 s to 80.68 s, independent of answer length.
     Normal-mode total times also varied (1.27–36.46 s). The likely cause is queueing
     on shared free-tier servers and network conditions.
   - Gemini sent each short answer in only 3–4 chunks, so the live-typing effect is
     small for short answers. It matters more for long answers.
7. **Scale.** One call costs about $0.00005–0.00011 on the paid tier, so about
   $0.05–0.11 per 1,000 similar calls. Small per call, but it adds up in real
   applications.

---

## 9. Screenshots

| # | File | Shows |
|---|---|---|
| 1 | `screenshots/step1.png` | First API call: answer + raw token usage |
| 2 | `screenshots/step2.png` | Automatic cost calculation |
| 3 | `screenshots/step3.png` | Prompt template, 3 topics, summary table |
| 4 | `screenshots/step4.png` | Pre-call estimate vs actual tokens |
| 5 | `screenshots/step5.png` | Streaming with TTFT and total time |
| 6 | `screenshots/token_cost_analyzer.png` | Final script, normal mode |
| 7 | `screenshots/token_cost_analyzer_stream.png` | Final script, streaming mode |

---

## 10. Notes and limitations

- **Free tier:** limited requests per minute and per day. Prompts and responses may be
  used by Google to improve its products, so no private data was sent.
- **Thinking tokens:** `reasoning_effort="minimal"` keeps hidden reasoning low. The
  OpenAI-compatible endpoint returned no separate thinking-token count
  (`completion_tokens_details: None`), so any thinking is included in output tokens.
- **Estimate accuracy:** `tiktoken` is OpenAI's tokenizer, so counts for Gemini are approximate.
- **Portability:** because the script uses the standard Chat Completion format,
  switching to another OpenAI-compatible provider only requires changing `BASE_URL`,
  `MODEL`, the API key and `PRICING`.

## 11. Reference

Course material: Mahara-Tech — *Gen-AI: Tools for the Modern Developer*
(https://maharatech.gov.eg/course/view.php?id=2299)
