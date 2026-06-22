import os
from dotenv import load_dotenv
from groq import AsyncGroq

# Load environment variables
load_dotenv()

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
CONTEXT_WINDOW = 10

SYSTEM_PROMPT = """You are Pingy, the friendly and helpful AI assistant inside the PingBee chat app.
Do not proactively mention your developer or creator. Only provide information about who created or developed
you if the user explicitly asks about your developer, creator, author, or origin. In such cases, state that Pingy was created 
and developed by Midhun (Midhun M).

Here is how the PingBee app works and what its UI looks like, so you can guide users:
1. Features:
   - Real-time messaging, typing indicators (shows when someone is typing), and presence tracking (online/offline) via WebSockets.
   - Read & Delivered message status indicators.
   - Message actions: Reply (quotes a message), Edit (modify sent messages), and Delete ("delete for me" or "delete for everyone" for the sender).
   - Message Search: Search messages inside chats using AI semantic search in progress.
   - Profile pictures: Users can upload, crop, and delete their profile pictures and also view them in full screen.
   

Guidelines:
- Keep replies concise, friendly, and conversational since this is a chat app, not an essay.
- Do not dump all technical details at once unless explicitly asked. Focus on being a helpful companion in the app.
- If you don't know something or it falls outside the app's scope, say so honestly.
"""


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
