import os
import google.generativeai as genai
from groq import Groq
import requests

# ============ КЛЮЧИ ============
GEMINI_KEY = os.environ.get("GEMINI_KEY", "").strip().strip('"').strip("'")
GROQ_KEY = os.environ.get("GROQ_KEY", "").strip().strip('"').strip("'")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

SYSTEM_PROMPT = """Ты — умный и дружелюбный AI-ассистент.
Отвечай на русском языке, кратко и по делу.
Используй эмодзи где уместно.
Если не знаешь ответ — честно скажи об этом."""

AVAILABLE_MODELS = {
    "gemini": {
        "name": "Gemini 2.0 Flash",
        "icon": "🔮",
        "description": "Быстрый и умный"
    },
    "groq-llama": {
        "name": "LLaMA 3.3 70B",
        "icon": "🦙",
        "description": "Мощная открытая модель"
    },
    "groq-mixtral": {
        "name": "Mixtral 8x7B",
        "icon": "🌀",
        "description": "Быстрая модель"
    },
}


# ============ МОДЕЛИ ============

def ask_gemini(message, history):
    if not GEMINI_KEY:
        return "⚠️ Gemini API ключ не настроен"

    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=SYSTEM_PROMPT
    )

    gemini_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(message)
    return response.text


def ask_groq(message, history, model_name="llama-3.3-70b-versatile"):
    if not groq_client:
        return "⚠️ Groq API ключ не настроен"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in history:
        role = msg["role"] if msg["role"] in ("user", "assistant") else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({"role": "user", "content": message})

    response = groq_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.7,
        max_tokens=2000
    )
    return response.choices[0].message.content


def get_ai_response(message, history, model="gemini"):
    """Главный роутер моделей"""
    try:
        if model == "gemini":
            return ask_gemini(message, history)
        elif model == "groq-llama":
            return ask_groq(message, history, "llama-3.3-70b-versatile")
        elif model == "groq-mixtral":
            return ask_groq(message, history, "mixtral-8x7b-32768")
        else:
            return ask_gemini(message, history)
    except Exception as e:
        print(f"❌ Ошибка {model}: {e}")
        # Пробуем запасную модель
        try:
            if model != "gemini" and GEMINI_KEY:
                print("🔄 Переключаюсь на Gemini...")
                return ask_gemini(message, history)
            elif model != "groq-llama" and groq_client:
                print("🔄 Переключаюсь на Groq...")
                return ask_groq(message, history)
        except Exception as e2:
            print(f"❌ Запасная модель тоже упала: {e2}")

        return f"⚠️ Ошибка: {str(e)}. Попробуйте другую модель."
