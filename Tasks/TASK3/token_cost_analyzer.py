"""
token_cost_analyzer.py
======================
Calls a Chat Completion API (Google Gemini through its OpenAI-compatible endpoint)
using a system instruction and a prompt template, then analyses tokens and cost.

Features
--------
1. System instruction + prompt template filled for several topics
2. Pre-call input-token estimate with tiktoken (local, free)
3. Actual token usage reported by the API
4. Automatic cost calculation (paid-tier equivalent + actual free-tier cost)
5. Optional streaming mode (--stream) with timing: TTFT and total time
6. Report saved to CSV and JSON in the reports/ folder

Usage
-----
    python token_cost_analyzer.py            # normal (non-streaming) mode
    python token_cost_analyzer.py --stream   # streaming mode
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

# ==================================================================
# SETTINGS (edit here)
# ==================================================================
MODEL = "gemini-3.1-flash-lite"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# USD per 1,000,000 tokens, Standard paid tier, text
# Source: https://ai.google.dev/pricing  (checked 2026-11-25)
PRICING = {
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
}
USING_FREE_TIER = True          # no billing account linked -> actual cost is $0

ENCODING_NAME = "o200k_base"    # tiktoken encoding used for the pre-call estimate
REASONING_EFFORT = "minimal"    # keep hidden "thinking" tokens as low as possible

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

REPORTS_DIR = "reports"

encoding = tiktoken.get_encoding(ENCODING_NAME)


# ==================================================================
# FUNCTIONS
# ==================================================================
def estimate_tokens(text):
    """Count tokens of a text locally with tiktoken (no API request, free)."""
    return len(encoding.encode(text))


def calculate_cost(model, prompt_tokens, completion_tokens):
    """Return (input_cost, output_cost, total_cost) in USD at paid-tier prices."""
    price = PRICING[model]
    input_cost = prompt_tokens / 1_000_000 * price["input"]
    output_cost = completion_tokens / 1_000_000 * price["output"]
    return input_cost, output_cost, input_cost + output_cost


def build_messages(user_prompt):
    """System instruction + user prompt in the Chat Completion message format."""
    return [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_prompt},
    ]


def ask_model(client, user_prompt):
    """Normal mode: wait for the full answer, then print it."""
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=build_messages(user_prompt),
        reasoning_effort=REASONING_EFFORT,
    )
    total_time = time.perf_counter() - start
    print(response.choices[0].message.content)
    usage = response.usage
    return {
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "ttft_s": None,                 # not applicable without streaming
        "total_time_s": total_time,
        "chunks": None,
    }


def ask_model_stream(client, user_prompt):
    """Streaming mode: print each chunk as it arrives; usage comes in the last chunk."""
    start = time.perf_counter()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=build_messages(user_prompt),
        reasoning_effort=REASONING_EFFORT,
        stream=True,
        stream_options={"include_usage": True},
    )
    first_token_time, usage, n_chunks = None, None, 0
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if first_token_time is None:
                first_token_time = time.perf_counter() - start
            n_chunks += 1
            print(chunk.choices[0].delta.content, end="", flush=True)
        if getattr(chunk, "usage", None):
            usage = chunk.usage
    total_time = time.perf_counter() - start
    print()
    if usage is None:
        print("WARNING: the API did not send token usage in the stream.")
        return None
    return {
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "ttft_s": first_token_time if first_token_time is not None else total_time,
        "total_time_s": total_time,
        "chunks": n_chunks,
    }


def save_reports(results, mode):
    """Save the results to reports/run_<timestamp>_<mode>.csv and .json"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(REPORTS_DIR, f"run_{stamp}_{mode}")

    # CSV: one row per call (opens directly in Excel)
    fields = list(results[0].keys())
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    # JSON: run settings + all calls + totals
    report = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "model": MODEL,
        "pricing_usd_per_1M_tokens": PRICING[MODEL],
        "free_tier": USING_FREE_TIER,
        "system_instruction": SYSTEM_INSTRUCTION,
        "prompt_template": PROMPT_TEMPLATE,
        "calls": results,
        "totals": {
            "input_tokens": sum(r["input_tokens"] for r in results),
            "output_tokens": sum(r["output_tokens"] for r in results),
            "paid_tier_cost_usd": sum(r["paid_tier_cost_usd"] for r in results),
            "actual_cost_usd": sum(r["actual_cost_usd"] for r in results),
        },
    }
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return base + ".csv", base + ".json"


# ==================================================================
# MAIN
# ==================================================================
def main():
    parser = argparse.ArgumentParser(description="Chat Completion call with token & cost analysis")
    parser.add_argument("--stream", action="store_true", help="use streaming responses")
    args = parser.parse_args()
    mode = "stream" if args.stream else "normal"

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found. Create a .env file (see .env.example).")
    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    print(f"Model              : {MODEL}   |   Mode: {mode.upper()}")
    print(f"System instruction : {SYSTEM_INSTRUCTION}")
    print(f"Prompt template    : {PROMPT_TEMPLATE}")

    results = []
    for i, topic in enumerate(TOPICS, start=1):
        user_prompt = PROMPT_TEMPLATE.format(topic=topic, length=LENGTH)
        est_in = estimate_tokens(SYSTEM_INSTRUCTION) + estimate_tokens(user_prompt)
        est_in_cost, _, _ = calculate_cost(MODEL, est_in, 0)

        print("\n" + "=" * 72)
        print(f"CALL {i}: {topic}")
        print("=" * 72)
        print(f"[BEFORE] estimated input tokens: {est_in}  (est. input cost ${est_in_cost:.8f})")
        print("[ANSWER] " + ("" if args.stream else "\n"), end="")

        r = ask_model_stream(client, user_prompt) if args.stream else ask_model(client, user_prompt)
        if r is None:
            continue

        in_cost, out_cost, total_cost = calculate_cost(MODEL, r["input_tokens"], r["output_tokens"])
        row = {
            "call": i,
            "mode": mode,
            "topic": topic,
            "estimated_input_tokens": est_in,
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "total_tokens": r["input_tokens"] + r["output_tokens"],
            "estimate_diff_pct": round((r["input_tokens"] - est_in) / r["input_tokens"] * 100, 2),
            "input_cost_usd": round(in_cost, 10),
            "output_cost_usd": round(out_cost, 10),
            "paid_tier_cost_usd": round(total_cost, 10),
            "actual_cost_usd": 0.0 if USING_FREE_TIER else round(total_cost, 10),
            "ttft_s": None if r["ttft_s"] is None else round(r["ttft_s"], 3),
            "total_time_s": round(r["total_time_s"], 3),
            "chunks": r["chunks"],
        }
        results.append(row)

        timing = f"total time: {row['total_time_s']:.2f} s"
        if args.stream:
            timing = f"TTFT: {row['ttft_s']:.2f} s  |  " + timing + f"  |  chunks: {row['chunks']}"
        print(f"[AFTER]  input: {row['input_tokens']} (est. {est_in}, diff {row['estimate_diff_pct']:+.1f}%)"
              f"  |  output: {row['output_tokens']}  |  paid-tier cost: ${total_cost:.8f}")
        print(f"         {timing}")

    if not results:
        print("No results to report.")
        return

    # ---- Summary table -------------------------------------------
    t_est = sum(r["estimated_input_tokens"] for r in results)
    t_in = sum(r["input_tokens"] for r in results)
    t_out = sum(r["output_tokens"] for r in results)
    t_cost = sum(r["paid_tier_cost_usd"] for r in results)

    print("\n" + "=" * 84)
    print(f"SUMMARY ({mode})")
    print("=" * 84)
    print(f"{'Topic':<36}{'Est.In':>7}{'In':>5}{'Out':>5}{'TTFT(s)':>9}{'Total(s)':>9}{'Cost (USD)':>13}")
    print("-" * 84)
    for r in results:
        ttft = "-" if r["ttft_s"] is None else f"{r['ttft_s']:.2f}"
        print(f"{r['topic'][:35]:<36}{r['estimated_input_tokens']:>7}{r['input_tokens']:>5}"
              f"{r['output_tokens']:>5}{ttft:>9}{r['total_time_s']:>9.2f}{r['paid_tier_cost_usd']:>13.8f}")
    print("-" * 84)
    print(f"{'TOTAL':<36}{t_est:>7}{t_in:>5}{t_out:>5}{'':>9}{'':>9}{t_cost:>13.8f}")
    print(f"\nPaid-tier equivalent cost : ${t_cost:.8f}")
    print(f"ACTUAL cost (free tier)   : ${0.0 if USING_FREE_TIER else t_cost:.2f}")

    csv_path, json_path = save_reports(results, mode)
    print(f"\nReport saved: {csv_path}")
    print(f"Report saved: {json_path}")


if __name__ == "__main__":
    main()
