from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser
from .models import ChatMessage
import ollama
from rest_framework.permissions import IsAuthenticated


HIGH_RISK_KEYWORDS = [
    "suicide",
    "kill myself",
    "end my life",
    "self harm",
    "hurt myself",
    "no reason to live",
    "want to die",
    "cut myself"
]

CRISIS_RESPONSE = """
I’m really sorry that you’re feeling this way.
You’re not alone, and help is available.

If you are in immediate danger or thinking about harming yourself,
please contact your local emergency number right now.

📞Suicide Prevention Helpline: Talk to someone now
91-9820466726
If you’re thinking about suicide, are worried about a friend or loved one, 
or would like emotional support, AASRA is available 24/7 across India. 
The Lifeline is available for everyone, is free, and confidential.
If possible, please reach out to a trusted person nearby.
"""

class ChatAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser]

    def post(self, request):
        # 1️⃣ Validate request body
        if not request.data:
            return Response(
                {"error": "Empty request body"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_message = request.data.get("message")

        if not user_message:
            return Response(
                {"error": "message required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2️⃣ SAFETY CHECK — MUST COME IMMEDIATELY AFTER VALIDATION
        lower_msg = user_message.lower()

        for keyword in HIGH_RISK_KEYWORDS:
            if keyword in lower_msg:
                # Log risky message
                ChatMessage.objects.create(
                    role="user",
                    content=user_message
                )
                ChatMessage.objects.create(
                    role="bot",
                    content="CRISIS_INTERVENTION_TRIGGERED"
                )

                return Response(
                    {"reply": CRISIS_RESPONSE},
                    status=status.HTTP_200_OK
                )

        # 3️⃣ Retrieve recent NON-CRISIS memory
        recent_messages = (
            ChatMessage.objects
            .exclude(content="CRISIS_INTERVENTION_TRIGGERED")
            .order_by("-created_at")[:4]
        )
        recent_messages = reversed(recent_messages)

        memory_text = ""
        for msg in recent_messages:
            memory_text += f"{msg.role}: {msg.content}\n"

        # 4️⃣ Build prompt
        prompt = f"""
You are a supportive mental wellness assistant.
If previous thoughts are provided, consider them
before responding.
Do not give medical advice.

Conversation so far:
{memory_text}

User says: {user_message}
"""

        # 5️⃣ Call Ollama (SAFE PATH ONLY)
        try:
            response = ollama.chat(
    model="phi",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a mental wellness support chatbot.\n"
                "- Speak directly to the user.\n"
                "- Be empathetic and supportive.\n"
                "- NEVER mention instructions, rules, probabilities, or system design.\n"
                "- NEVER role-play as an engineer, AI, or developer.\n"
                "- NEVER explain how the chatbot works.\n"
                "- Do NOT mention policies or internal logic.\n"
                "- Do NOT give medical advice.\n"
                "- Keep responses natural and human."
            )
        },
        {
            "role": "user",
            "content": f"Previous context:\n{memory_text}\n\nUser: {user_message}"
        }
    ],
    options={
        "num_predict": 120,
        "temperature": 0.6,
        "top_p": 0.9
    }
)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        bot_reply = response["message"]["content"]

        # 6️⃣ Store messages
        ChatMessage.objects.create(
            role="user",
            content=user_message
        )
        ChatMessage.objects.create(
            role="bot",
            content=bot_reply
        )

        return Response(
            {"reply": bot_reply},
            status=status.HTTP_200_OK
        )
