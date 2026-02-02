from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import os

from .models import ChatSession, ChatMessage

# 🔹 Lazy Groq client (safe on Render)
_groq_client = None


def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set")
        from groq import Groq
        _groq_client = Groq(api_key=api_key)
    return _groq_client


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
            # 1️⃣ Save user message
            ChatMessage.objects.create(
                session=session,
                role="user",
                content=user_message
            )

            # 2️⃣ Load recent memory (session-scoped)
            recent_messages = (
                ChatMessage.objects
                .filter(session=session)
                .order_by("created_at")[:6]
            )

            # 3️⃣ RAG — TEMPORARILY DISABLED ON RENDER FREE
            # (Codebase still has RAG, just not executed here)
            knowledge_text = ""

            # 4️⃣ Build LLM messages
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a supportive mental wellness companion.\n"
                        "Speak calmly, warmly, and practically.\n"
                        "Focus primarily on the user's latest message.\n"
                        "Do not give generic filler responses.\n"
                        "Do not analyze or label the user.\n"
                        "Do not give medical advice."
                    )
                }
            ]

            # (RAG injection skipped intentionally)

            # Conversation memory
            for msg in recent_messages:
                messages.append({
                    "role": "assistant" if msg.role == "bot" else "user",
                    "content": msg.content
                })

            # Latest user message
            messages.append({
                "role": "user",
                "content": user_message
            })

            # 5️⃣ LLM call (SAFE)
            try:
                client = get_groq_client()

                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=messages,
                    temperature=0.5,
                    max_tokens=400
                )

                bot_reply = response.choices[0].message.content.strip()

            except Exception:
                bot_reply = (
                    "I’m here with you. I might be a bit slow right now, "
                    "but you can keep talking — I’m listening."
                )

            # 6️⃣ Save bot reply
            ChatMessage.objects.create(
                session=session,
                role="bot",
                content=bot_reply
            )

            # Auto-set chat title
            if session.title == "New Chat":
                session.title = user_message[:30]
                session.save()

        return redirect("chat_page", session_id=session.id)

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
