from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import os
import time

from .models import ChatSession, ChatMessage

# 🔹 Lazy Groq client (IMPORTANT)
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


MAX_RAG_SECONDS = 1.5  # HARD LIMIT for Render Free


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

            # 3️⃣ RAG (TIME-BOUND + SAFE)
            knowledge_text = ""
            start = time.time()

            try:
                from rag.rag_utils import retrieve_knowledge

                if time.time() - start < MAX_RAG_SECONDS:
                    chunks = retrieve_knowledge(user_message, k=1)

                    if (
                        chunks
                        and time.time() - start < MAX_RAG_SECONDS
                    ):
                        knowledge_text = chunks[0][:300]

            except Exception:
                # 🔕 Fail silently — never block chat
                knowledge_text = ""

            # 4️⃣ Build LLM messages
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

            if knowledge_text:
                messages.append({
                    "role": "system",
                    "content": f"Relevant mental health context:\n{knowledge_text}"
                })

            for msg in recent_messages:
                messages.append({
                    "role": "assistant" if msg.role == "bot" else "user",
                    "content": msg.content
                })

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
                    "I’m here with you. I may be a bit slow right now, "
                    "but you can keep talking — I’m listening."
                )

            # 6️⃣ Save bot reply
            ChatMessage.objects.create(
                session=session,
                role="bot",
                content=bot_reply
            )

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
