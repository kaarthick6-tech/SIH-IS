import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_llm_client():
    # Try Groq first (free), fallback to OpenAI if GROQ_API_KEY is missing
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        return OpenAI(
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1"
        )
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return OpenAI(api_key=openai_key)
        
    raise RuntimeError("Either GROQ_API_KEY or OPENAI_API_KEY must be set in .env")

def rerank_and_justify(user_input: str, candidates: list) -> dict:
    candidates_json = json.dumps([
        {"is_number": c["is_number"], "title": c["title"], "scope_text": c["scope_text"]} 
        for c in candidates
    ])
    
    prompt = f"""You are an expert Indian procurement compliance assistant.
Evaluate if the provided Indian Standard (IS) scopes genuinely match the user's requirement.
User Requirement: "{user_input}"
Candidates: {candidates_json}
Rules: 
1. ONLY select from the provided list. DO NOT invent IS numbers. 
2. Output valid JSON with keys: "selected_is_numbers" (array of strings) and "justification" (string)."""

    client = get_llm_client()
    
    # Model is configurable so a provider-side change does not break the app.
    # openai/gpt-oss-20b: cheapest fast chat model, ~1000 tok/s, supports JSON mode.
    # Note: llama3-8b-8192 is decommissioned (HTTP 400) and llama-3.1-8b-instant
    # is Enterprise-only, so a free Groq key cannot use it (HTTP 404).
    if os.getenv("GROQ_API_KEY"):
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    else:
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "Analyze and return JSON."}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)
