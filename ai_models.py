# -*- coding: utf-8 -*-
import os
import sys
import traceback

os.environ['PYTHONIOENCODING'] = 'utf-8'

# ============ ИМПОРТ ============
GEMINI_AVAILABLE = False
GROQ_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("google-generativeai OK")
except ImportError as e:
    print(f"google-generativeai FAIL: {e}")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
    print("groq OK")
except ImportError as e:
    print(f"groq FAIL: {e}")

# ============ КЛЮЧИ ============
GEMINI_KEY = os.environ.get("GEMINI_KEY", "").strip().strip('"').strip("'")
GROQ_KEY = os.environ.get("GROQ_KEY", "").strip().strip('"').strip("'")

print(f"GEMINI_KEY: {'YES' if GEMINI_KEY else 'NO'}")
print(f"GROQ_KEY: {'YES' if GROQ_KEY else 'NO'}")

if GEMINI_KEY and GEMINI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_KEY)
        print("Gemini configured")
    except Exception as e:
        print(f"Gemini config error: {e}")
        GEMINI_AVAILABLE = False

groq_client = None
if GROQ_KEY and GROQ_AVAILABLE:
    try:
        groq_client = Groq(api_key=GROQ_KEY)
        print("Groq configured")
    except Exception as e:
        print(f"Groq config error: {e}")

# Промпт на английском чтобы избежать проблем с кодировкой
SYSTEM_PROMPT = "You are a friendly AI assistant. Always respond in Russian language. Be concise and helpful. Use emoji where appropriate."

AVAILABLE_MODELS = {
    "gemini": {
        "name": "Gemini 1.5 Flash",
        "icon": "🔮",
        "description": "Fast and smart"
    },
    "groq-llama": {
        "name": "LLaMA 3.3 70B",
        "icon": "🦙",
        "description": "Powerful open model"
    },
    "groq-mixtral": {
        "name": "Mixtral 8x7B",
        "icon": "🌀",
        "description": "Fast model"
    },
}


def ask_gemini(message, history):
    if not GEMINI_KEY or not GEMINI_AVAILABLE:
        return "Gemini is not available. Check GEMINI_KEY."

    model_names = ['gemini-1.5-flash', 'gemini-pro']

    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)

            if not history:
                response = model.generate_content(message)
                return response.text

            gemini_history = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({
                    "role": role,
                    "parts": [msg["content"]]
                })

            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(message)
            return response.text

        except Exception as e:
            print(f"Gemini {model_name} error: {e}")
            continue

    return "All Gemini models failed."


def ask_groq(message, history, model_name="llama-3.3-70b-versatile"):
    if not groq_client:
        return "Groq is not available. Check GROQ_KEY."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in history:
        role = msg["role"] if msg["role"] in ("user", "assistant") else "assistant"
        messages.append({
            "role": role,
            "content": str(msg["content"])
        })

    messages.append({"role": "user", "content": str(message)})

    groq_models = [model_name, "llama-3.1-8b-instant", "gemma2-9b-it"]

    for m in groq_models:
        try:
            response = groq_client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq {m} error: {e}")
            continue

    return "All Groq models failed."


def get_ai_response(message, history, model="gemini"):
    try:
        # Принудительно строки
        message = str(message)
        safe_history = []
        for h in history:
            safe_history.append({
                "role": str(h.get("role", "user")),
                "content": str(h.get("content", ""))
            })

        if model == "gemini":
            return ask_gemini(message, safe_history)
        elif model == "groq-llama":
            return ask_groq(message, safe_history, "llama-3.3-70b-versatile")
        elif model == "groq-mixtral":
            return ask_groq(message, safe_history, "mixtral-8x7b-32768")
        else:
            return ask_gemini(message, safe_history)

    except Exception as e:
        error_text = str(e)
        print(f"AI error: {error_text}")
        print(traceback.format_exc())

        # Fallback
        try:
            if model != "gemini" and GEMINI_KEY and GEMINI_AVAILABLE:
                return ask_gemini(str(message), [])
            elif model == "gemini" and groq_client:
                return ask_groq(str(message), [], "llama-3.1-8b-instant")
        except Exception as e2:
            print(f"Fallback error: {e2}")

        return f"Error: {error_text}"
