"""
Step 2 - Chat Completion call + automatic cost calculation

New in this step (compared to Step 1):
    1. PRICING table  -> official Gemini paid-tier prices (USD per 1M tokens)
    2. calculate_cost -> turns the token usage into money
    3. Cost report    -> actual cost (free tier = $0) + paid-tier equivalent
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# ------------------------------------------------------------------
# PRICING TABLE (USD per 1,000,000 tokens, Standard paid tier, text)
# Source: https://ai.google.dev/pricing  (checked 2026-11-25)
# Prices change over time -> edit these numbers if Google updates them.
# ------------------------------------------------------------------
PRICING = {
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
}

USING_FREE_TIER = True   # no billing account linked -> we are actually charged $0

MODEL = "gemini-3.1-flash-lite"


def calculate_cost(model, prompt_tokens, completion_tokens):
    """Return (input_cost, output_cost, total_cost) in USD at paid-tier prices."""
    price = PRICING[model]
    input_cost = prompt_tokens / 1_000_000 * price["input"]
    output_cost = completion_tokens / 1_000_000 * price["output"]
    return input_cost, output_cost, input_cost + output_cost


# --- Setup (same as Step 1) ---------------------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY not found. Check the .env file is in this folder.")

client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

messages = [
    {"role": "system",
     "content": "You are a concise health and study assistant. Answer only in short bullet points."},
    {"role": "user",
     "content": "Summarize the main benefits of drinking water in the morning in 3 lines short bullet points."},
]

# --- API call (same as Step 1) ------------------------------------
response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    reasoning_effort="minimal",
)

print("=" * 60)
print("MODEL ANSWER")
print("=" * 60)
print(response.choices[0].message.content)

# --- Token usage --------------------------------------------------
usage = response.usage
print("\n" + "=" * 60)
print("TOKEN USAGE (reported by the API)")
print("=" * 60)
print(f"Input  tokens : {usage.prompt_tokens}")
print(f"Output tokens : {usage.completion_tokens}")
print(f"Total  tokens : {usage.total_tokens}")

# --- NEW: Cost analysis -------------------------------------------
input_cost, output_cost, total_cost = calculate_cost(
    MODEL, usage.prompt_tokens, usage.completion_tokens
)
price = PRICING[MODEL]

print("\n" + "=" * 60)
print(f"COST ANALYSIS  (model: {MODEL})")
print("=" * 60)
print(f"Prices used   : ${price['input']:.2f} / 1M input,  ${price['output']:.2f} / 1M output")
print(f"Input  cost   : {usage.prompt_tokens:>6} tokens  -> ${input_cost:.8f}")
print(f"Output cost   : {usage.completion_tokens:>6} tokens  -> ${output_cost:.8f}")
print("-" * 60)
print(f"Paid-tier equivalent cost : ${total_cost:.8f}")
actual = 0.0 if USING_FREE_TIER else total_cost
print(f"ACTUAL cost (free tier)   : ${actual:.2f}")
print(f"Estimated cost for 1,000 calls like this (paid tier): ${total_cost * 1000:.4f}")
