"""
Step 3 - Prompt templates + system instructions + cost per call

New in this step (compared to Step 2):
    1. SYSTEM_INSTRUCTION -> one general instruction reused for every call
    2. PROMPT_TEMPLATE    -> a prompt with blanks {topic} and {length}
    3. TOPICS list        -> the values that fill the blanks
    4. ask_model()        -> one reusable function: send prompt, return answer + usage + cost
    5. Summary table      -> tokens and cost for every topic + totals
"""

import os
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


# ------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------
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
print(f"System instruction : {SYSTEM_INSTRUCTION}")
print(f"Prompt template    : {PROMPT_TEMPLATE}")

results = []
for i, topic in enumerate(TOPICS, start=1):
    # Fill the blanks of the template
    user_prompt = PROMPT_TEMPLATE.format(topic=topic, length=LENGTH)

    result = ask_model(client, user_prompt)
    result["topic"] = topic
    results.append(result)

    print("\n" + "=" * 70)
    print(f"CALL {i}: {topic}")
    print("=" * 70)
    print(f"Prompt sent: {user_prompt}\n")
    print(result["answer"])
    print(f"\nTokens -> input: {result['input_tokens']}, "
          f"output: {result['output_tokens']}, total: {result['total_tokens']}  |  "
          f"paid-tier cost: ${result['cost']:.8f}")

# ------------------------------------------------------------------
# SUMMARY TABLE
# ------------------------------------------------------------------
total_in = sum(r["input_tokens"] for r in results)
total_out = sum(r["output_tokens"] for r in results)
total_cost = sum(r["cost"] for r in results)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"{'Topic':<48}{'In':>5}{'Out':>6}{'Cost (USD)':>12}")
print("-" * 70)
for r in results:
    print(f"{r['topic'][:47]:<48}{r['input_tokens']:>5}{r['output_tokens']:>6}{r['cost']:>12.8f}")
print("-" * 70)
print(f"{'TOTAL':<48}{total_in:>5}{total_out:>6}{total_cost:>12.8f}")
print(f"\nPaid-tier equivalent cost : ${total_cost:.8f}")
print(f"ACTUAL cost (free tier)   : ${0.0 if USING_FREE_TIER else total_cost:.2f}")
