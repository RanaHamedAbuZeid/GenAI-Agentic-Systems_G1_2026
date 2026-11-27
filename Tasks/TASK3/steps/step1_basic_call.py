"""
Step 1 - Basic Chat Completion call to Gemini (free tier)

Goal of this step:
    Send ONE request (system instruction + user prompt) and print:
      1. the model's answer
      2. the raw token usage the API reports back

Nothing else yet: no cost, no templates, no streaming (those are Steps 2-5).
"""

import os
from dotenv import load_dotenv   # reads the .env file into environment variables
from openai import OpenAI        # the standard "Chat Completion" client

# 1) Load the API key from .env (the key is never written in the code itself)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY not found. Check the .env file is in this folder.")

# 2) Point the OpenAI client at Google's OpenAI-compatible endpoint
client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

MODEL = "gemini-3.1-flash-lite"   # free-tier model (decision D1)

# 3) The messages: a system instruction + the user's question
messages = [
    {"role": "system",
     "content": "You are a concise health and study assistant. Answer only in short bullet points."},
    {"role": "user",
     "content": "Summarize the main benefits of drinking water in the morning in 3 lines short bullet points."},
]

# 4) Call the API
response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    reasoning_effort="minimal",   # decision D4: keep hidden "thinking" tokens as low as possible
)

# 5) Print the answer
print("=" * 60)
print("MODEL ANSWER")
print("=" * 60)
print(response.choices[0].message.content)

# 6) Print the token usage exactly as the API returned it
usage = response.usage
print("\n" + "=" * 60)
print("TOKEN USAGE (reported by the API)")
print("=" * 60)
print(f"Input  (prompt_tokens)     : {usage.prompt_tokens}")
print(f"Output (completion_tokens) : {usage.completion_tokens}")
print(f"Total  (total_tokens)      : {usage.total_tokens}")
print("\nFull usage object (to see any extra fields, e.g. thinking tokens):")
print(usage.model_dump())
