import os
from dotenv import load_dotenv
from groq import AsyncGroq

# Load environment variables
load_dotenv()

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
CONTEXT_WINDOW = 10

SYSTEM_PROMPT = """You are Pingy, a friendly and helpful assistant 
inside the PingBee chat app. Keep replies concise and conversational — 
this is a chat app, not an essay. If you don't know something, say so honestly."""


async def get_bot_reply(conversation_history: list[dict]) -> str:
    try:
        recent = conversation_history[-CONTEXT_WINDOW:]
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *recent
            ],
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[AI Service] Groq API error: {e}", flush=True)
        return "Sorry, I'm having trouble thinking right now. Try again in a moment! 🤖"
