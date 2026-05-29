import os
import base64
import threading
import requests as req
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are Janani Sakhi, a warm and knowledgeable AI pregnancy companion speaking to an Indian woman who is pregnant.

Your role:
- Analyze food items (from text or photo descriptions) for pregnancy safety
- Estimate key nutrients: protein, iron, folate, calcium
- Flag each food as SAFE, CAUTION, or AVOID for pregnancy
- Give practical, culturally relevant advice for Indian food habits
- Be warm, supportive, and encouraging — like a trusted female friend

For each food analysis, respond in this format:
🍽️ *Food:* [name]
✅/⚠️/❌ *Status:* SAFE / CAUTION / AVOID
📊 *Nutrients (approx per serving):*
  - Protein: Xg
  - Iron: Xmg
  - Folate: Xmcg
  - Calcium: Xmg
💬 *Note:* [brief pregnancy-specific advice]

Keep responses concise and friendly. Always respond in the language the user writes in (Hindi or English)."""


def process_and_reply(sender, incoming_msg, media_url):
    try:
        messages = []

        if media_url:
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            image_response = req.get(media_url, auth=(account_sid, auth_token))
            media_type = image_response.headers.get("Content-Type", "image/jpeg")
            image_data = base64.standard_b64encode(image_response.content).decode("utf-8")

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        },
                    },
                    {
                        "type": "text",
                        "text": incoming_msg if incoming_msg else "Please analyze this food for pregnancy safety."
                    }
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": incoming_msg
            })

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        reply = response.content[0].text

    except Exception as e:
        import traceback
        reply = "Sorry, Janani is unavailable right now. Please try again in a moment. 🙏"
        print(f"Error: {e}")
        traceback.print_exc()

    # Split message if over 1500 chars
    chunks = [reply[i:i+1500] for i in range(0, len(reply), 1500)]
    for chunk in chunks:
        twilio_client.messages.create(
            from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
            to=sender,
            body=chunk
        )


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    media_url = request.values.get("MediaUrl0", None)
    sender = request.values.get("From", "")

    # Process in background so Twilio doesn't timeout
    thread = threading.Thread(target=process_and_reply, args=(sender, incoming_msg, media_url))
    thread.start()

    # Immediately return empty response to Twilio
    return str(MessagingResponse())


@app.route("/", methods=["GET"])
def health():
    return "Janani Sakhi is running 🌸"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
