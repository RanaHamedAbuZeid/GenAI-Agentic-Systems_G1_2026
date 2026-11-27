"""
Step 5 - Streaming responses + token/cost analysis + timing

New in this step (compared to Step 4):
    1. stream=True        -> the answer arrives piece by piece (chunks) and is printed live
    2. stream_options     -> asks the API to send the token usage in the LAST chunk
    3. Timing (time.perf_counter):
         TTFT  = Time To First Token (how fast the user sees the first words)
         Total = time until the full answer has arrived
"""

import os
import time
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

ENCODING_NAME = "o200k_base"   # tiktoken encoding for the pre-call estimate

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


def ask_model_stream(client, user_prompt):
    """Send the request with streaming, print the answer live, return tokens/cost/timing."""
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_prompt},
    ]

    start = time.perf_counter()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        reasoning_effort="minimal",
        stream=True,                              # NEW: receive the answer in chunks
        stream_options={"include_usage": True},   # NEW: ask for token usage in the last chunk
    )

    first_token_time = None
    usage = None
    n_chunks = 0

    for chunk in stream:
        # Text pieces arrive in chunk.choices[0].delta.content
        if chunk.choices and chunk.choices[0].delta.content:
            if first_token_time is None:
                first_token_time = time.perf_counter() - start
            n_chunks += 1
            print(chunk.choices[0].delta.content, end="", flush=True)  # print live
        # Token usage arrives in (one of) the last chunk(s)
        if getattr(chunk, "usage", None):
            usage = chunk.usage

    total_time = time.perf_counter() - start
    print()  # new line after the streamed answer

    if usage is None:
        print("WARNING: the API did not send token usage in the stream.")
        return None

    _, _, total_cost = calculate_cost(MODEL, usage.prompt_tokens, usage.completion_tokens)
    return {
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "cost": total_cost,
        "ttft": first_token_time if first_token_time is not None else total_time,
        "total_time": total_time,
        "chunks": n_chunks,
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

print(f"Model              : {MODEL}  (STREAMING mode)")
print(f"System instruction : {SYSTEM_INSTRUCTION}")
print(f"Prompt template    : {PROMPT_TEMPLATE}")

results = []
for i, topic in enumerate(TOPICS, start=1):
    user_prompt = PROMPT_TEMPLATE.format(topic=topic, length=LENGTH)
    est_in = estimate_tokens(SYSTEM_INSTRUCTION) + estimate_tokens(user_prompt)

    print("\n" + "=" * 70)
    print(f"CALL {i}: {topic}")
    print("=" * 70)
    print(f"[BEFORE] estimated input tokens: {est_in}")
    print("[STREAM] ", end="")

    result = ask_model_stream(client, user_prompt)
    if result is None:
        continue
    result["topic"] = topic
    result["est_in"] = est_in
    results.append(result)

    print(f"[AFTER]  input: {result['input_tokens']} (est. {est_in}), "
          f"output: {result['output_tokens']}, chunks received: {result['chunks']}")
    print(f"         TTFT: {result['ttft']:.2f} s  |  total time: {result['total_time']:.2f} s  |  "
          f"paid-tier cost: ${result['cost']:.8f}")

# ------------------------------------------------------------------
# SUMMARY TABLE
# ------------------------------------------------------------------
if results:
    total_in = sum(r["input_tokens"] for r in results)
    total_out = sum(r["output_tokens"] for r in results)
    total_cost = sum(r["cost"] for r in results)

    print("\n" + "=" * 80)
    print("SUMMARY (streaming)")
    print("=" * 80)
    print(f"{'Topic':<36}{'Est.In':>7}{'In':>5}{'Out':>5}{'TTFT(s)':>9}{'Total(s)':>9}{'Cost (USD)':>12}")
    print("-" * 80)
    for r in results:
        print(f"{r['topic'][:35]:<36}{r['est_in']:>7}{r['input_tokens']:>5}{r['output_tokens']:>5}"
              f"{r['ttft']:>9.2f}{r['total_time']:>9.2f}{r['cost']:>12.8f}")
    print("-" * 80)
    print(f"{'TOTAL':<36}{'':>7}{total_in:>5}{total_out:>5}{'':>9}{'':>9}{total_cost:>12.8f}")
    print(f"\nPaid-tier equivalent cost : ${total_cost:.8f}")
    print(f"ACTUAL cost (free tier)   : ${0.0 if USING_FREE_TIER else total_cost:.2f}")
