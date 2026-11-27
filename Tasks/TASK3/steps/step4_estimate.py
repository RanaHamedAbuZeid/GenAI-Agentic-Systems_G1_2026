"""
Step 4 - Estimate tokens BEFORE sending (tiktoken) and compare with the ACTUAL count

New in this step (compared to Step 3):
    1. estimate_tokens()  -> counts input tokens locally, before any API request (free)
    2. Pre-call estimate  -> estimated input tokens + estimated input cost, printed BEFORE the call
    3. Comparison         -> estimated vs actual input tokens, difference in %

Note: tiktoken is OpenAI's tokenizer. Gemini splits text with its own tokenizer,
so the estimate is APPROXIMATE. Measuring how close it is, is part of this step.
"""

import os
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

# ------------------------------------------------------------------
# SETTINGS (edit here)
# ------------------------------------------------------------------
MODEL = "gemini-3.1-flash-lite"

# USD per 1,000,000 tokens, Standard paid tier, text
# Source: https://ai.google.dev/pricing  (checked 2026-11-25)
PRICING = {
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
}
USING_FREE_TIER = True   # no billing account linked -> actual cost is $0

# tiktoken encoding used for the estimate (OpenAI's newest, used by GPT-4o)
ENCODING_NAME = "o200k_base"

SYSTEM_INSTRUCTION = (
    "You are a concise educational assistant. Answer only in short bullet points."
)

PROMPT_TEMPLATE = "Summarize the main benefits of {topic} in {length} short bullet points."

TOPICS = [
    "drinking water in the morning",
    "learning data structures and algorithms early",
    "using Git version control in student projects",
]
LENGTH = "3 lines"

# Load the tokenizer once (first run downloads a small dictionary file, then it is cached)
encoding = tiktoken.get_encoding(ENCODING_NAME)


# ------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------
def estimate_tokens(text):
    """Count tokens of a text locally with tiktoken (no API request, free)."""
    return len(encoding.encode(text))


def calculate_cost(model, prompt_tokens, completion_tokens):
    """Return (input_cost, output_cost, total_cost) in USD at paid-tier prices."""
    price = PRICING[model]
    input_cost = prompt_tokens / 1_000_000 * price["input"]
    output_cost = completion_tokens / 1_000_000 * price["output"]
    return input_cost, output_cost, input_cost + output_cost


def ask_model(client, user_prompt):
    """Send system instruction + user prompt, return a dict with answer, tokens, cost."""
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_prompt},
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        reasoning_effort="minimal",
    )
    usage = response.usage
    _, _, total_cost = calculate_cost(MODEL, usage.prompt_tokens, usage.completion_tokens)
    return {
        "answer": response.choices[0].message.content,
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "cost": total_cost,
    }


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY not found. Check the .env file is in this folder.")

client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

print(f"Model              : {MODEL}")
print(f"Estimate tokenizer : tiktoken '{ENCODING_NAME}'")
print(f"System instruction : {SYSTEM_INSTRUCTION}")
print(f"Prompt template    : {PROMPT_TEMPLATE}")

results = []
for i, topic in enumerate(TOPICS, start=1):
    user_prompt = PROMPT_TEMPLATE.format(topic=topic, length=LENGTH)

    # --- NEW: estimate BEFORE sending -----------------------------
    est_in = estimate_tokens(SYSTEM_INSTRUCTION) + estimate_tokens(user_prompt)
    est_in_cost, _, _ = calculate_cost(MODEL, est_in, 0)

    print("\n" + "=" * 70)
    print(f"CALL {i}: {topic}")
    print("=" * 70)
    print(f"Prompt: {user_prompt}")
    print(f"[BEFORE] estimated input tokens: {est_in}  -> estimated input cost: ${est_in_cost:.8f}")

    # --- Send the request (same as Step 3) ------------------------
    result = ask_model(client, user_prompt)
    result["topic"] = topic
    result["est_in"] = est_in
    result["diff_pct"] = (result["input_tokens"] - est_in) / result["input_tokens"] * 100
    results.append(result)

    print(f"\n{result['answer']}\n")
    print(f"[AFTER]  actual input tokens   : {result['input_tokens']}  "
          f"(estimate off by {result['diff_pct']:+.1f}%)")
    print(f"         output tokens         : {result['output_tokens']}  |  "
          f"paid-tier cost: ${result['cost']:.8f}")

# ------------------------------------------------------------------
# SUMMARY TABLE
# ------------------------------------------------------------------
total_est = sum(r["est_in"] for r in results)
total_in = sum(r["input_tokens"] for r in results)
total_out = sum(r["output_tokens"] for r in results)
total_cost = sum(r["cost"] for r in results)

print("\n" + "=" * 78)
print("SUMMARY")
print("=" * 78)
print(f"{'Topic':<40}{'Est.In':>7}{'In':>5}{'Diff%':>8}{'Out':>6}{'Cost (USD)':>12}")
print("-" * 78)
for r in results:
    print(f"{r['topic'][:39]:<40}{r['est_in']:>7}{r['input_tokens']:>5}"
          f"{r['diff_pct']:>+7.1f}%{r['output_tokens']:>6}{r['cost']:>12.8f}")
print("-" * 78)
total_diff = (total_in - total_est) / total_in * 100
print(f"{'TOTAL':<40}{total_est:>7}{total_in:>5}{total_diff:>+7.1f}%{total_out:>6}{total_cost:>12.8f}")
print(f"\nPaid-tier equivalent cost : ${total_cost:.8f}")
print(f"ACTUAL cost (free tier)   : ${0.0 if USING_FREE_TIER else total_cost:.2f}")
