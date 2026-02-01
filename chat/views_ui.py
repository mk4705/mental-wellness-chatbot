from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ChatMessage
from groq import Groq
import os
from rag.rag_utils import retrieve_knowledge
from .models import ChatSession, ChatMessage
from django.views.decorators.http import require_POST

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

FORBIDDEN_OUTPUT_PATTERNS = [
    "the user",
    "the assistant",
    "the response",
    "it would be helpful",
    "should provide",
    "appears to be",
    "they may be experiencing",
    "in this situation",
    "encourage them to",
    "provide them with resources"
]

@login_required
def new_chat(request):
    session = ChatSession.objects.create(user=request.user)
    return redirect("chat_page", session_id=session.id)

@login_required
def chat_page(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if user_message:
            # 1️⃣ Save user message (SESSION-AWARE)
            ChatMessage.objects.create(
                session=session,
                role="user",
                content=user_message
            )

            # 2️⃣ Load recent memory ONLY for this session (last 6 messages)
            recent_messages = (
            ChatMessage.objects
            .filter(session=session)
            .order_by("created_at")[:6]
        )
            # 3️⃣ RAG knowledge
            knowledge_chunks = retrieve_knowledge(user_message, k=1)
            knowledge_text = ""
            if knowledge_chunks:
                knowledge_text = knowledge_chunks[0][:400]

            # 4️⃣ Build messages PROPERLY (THIS IS THE FIX)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a supportive mental wellness companion.\n"
                        "Speak calmly, warmly, and practically.\n"
                        "Focus primarily on the user's latest message.\n"
                        "Use the provided mental health context only if relevant.\n"
                        "Do not give generic filler responses.\n"
                        "Do not analyze or label the user.\n"
                        "Do not give medical advice."
                    )
                }
            ]

            # Inject RAG context explicitly
            if knowledge_text:
                messages.append({
                    "role": "system",
                    "content": f"Relevant mental health context:\n{knowledge_text}"
                })

            # Add conversation memory as REAL chat turns
            for msg in recent_messages:
                messages.append({
                    "role": "assistant" if msg.role == "bot" else "user",
                    "content": msg.content
                })
            # Add latest user message LAST
            messages.append({
                "role": "user",
                "content": user_message
            })
            # 4️⃣ LLM call (UNCHANGED logic)
            response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0.5,
            max_tokens=400
        )

            # 5️⃣ Extract reply
            bot_reply = response.choices[0].message.content.strip()

            if not bot_reply:
                bot_reply = (
                    "I’m here with you. Take your time — what’s been on your mind lately?"
                )

            # 6️⃣ Save bot reply (SESSION-AWARE)
            ChatMessage.objects.create(
                session=session,
                role="bot",
                content=bot_reply
            )
            # 🔹 Auto-set chat title from first message
            if session.title == "New Chat":
                session.title = user_message[:30]  # first 30 chars
                session.save()

        return redirect(f"/chat/{session.id}/")

    # GET request
    messages = ChatMessage.objects.filter(session=session).order_by("created_at")
    sessions = ChatSession.objects.filter(user=request.user).order_by("-created_at")

    return render(
    request,
    "chat/chat.html",
    {
        "messages": messages,
        "sessions": sessions,
        "active_session": session,
    }
)

@login_required
@require_POST
def delete_chat(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.delete()

    remaining = ChatSession.objects.filter(user=request.user).order_by("-created_at")
    if remaining.exists():
        return redirect("chat_page", session_id=remaining.first().id)

    return redirect("new_chat")