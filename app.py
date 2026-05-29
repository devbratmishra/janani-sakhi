import os
import json
import base64
import threading
from datetime import datetime, date
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

USERS_FILE = "users.json"


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)


def get_pregnancy_week(due_date_str):
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        conception_date = due_date - __import__('datetime').timedelta(weeks=40)
        weeks = (date.today() - conception_date).days // 7
        return max(1, min(weeks, 42))
    except:
        return None


def build_system_prompt(name, due_date_str):
    week = get_pregnancy_week(due_date_str)
    week_info = f"She is currently in week {week} of her pregnancy." if week else ""

    return f"""You are Janani Sakhi, a warm and knowledgeable AI pregnancy companion.

You are speaking to {name}, an Indian woman who is pregnant. {week_info}

Your role:
- Always address her by name: {name}
- Analyze food items (from text or photo) for pregnancy safety
- Estimate key nutrients: protein, iron, folate, calcium
- Flag each food as SAFE, CAUTION, or AVOID for pregnancy
- Give week-specific pregnancy advice relevant to week {week}
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

Keep responses concise and friendly. Always respond in the language {name} writes in (Hindi or English)."""


def send_message(to, body):
    chunks = [body[i:i+1500] for i in range(0, len(body), 1500)]
    for chunk in chunks:
        twilio_client.messages.create(
            from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
            to=to,
            body=chunk
        )


def process_and_reply(sender, incoming_msg, media_url):
    users = load_users()
    user = users.get(sender, {})

    # ONBOARDING: Step 1 — new user, ask for name
    if not user:
        users[sender] = {"state": "awaiting_name"}
        save_users(users)
        send_message(sender,
            "Namaste! 🌸 I'm *Janani Sakhi*, your personal AI pregnancy companion!\n\n"
            "I'm here to help you eat well and stay healthy through your pregnancy journey. 💛\n\n"
            "To get started, may I know your name? 😊"
        )
        return

    # ONBOARDING: Step 2 — have name, ask for due date
    if user.get("state") == "awaiting_name":
        name = incoming_msg.strip().title()
        users[sender] = {"state": "awaiting_due_date", "name": name}
        save_users(users)
        send_message(sender,
            f"What a beautiful name! Welcome, *{name}*! 🌺\n\n"
            f"To give you the best advice for your pregnancy stage, could you share your *due date*?\n\n"
            f"Please reply in this format: *DD-MM-YYYY*\n"
            f"For example: 15-10-2026"
        )
        return

    # ONBOARDING: Step 3 — save due date, complete onboarding
    if user.get("state") == "awaiting_due_date":
        try:
            due_date = datetime.strptime(incoming_msg.strip(), "%d-%m-%Y")
            due_date_str = due_date.strftime("%Y-%m-%d")
            name = user["name"]
            week = get_pregnancy_week(due_date_str)
            users[sender] = {"state": "active", "name": name, "due_date": due_date_str}
            save_users(users)
            send_message(sender,
                f"Wonderful, {name}! 🎉\n\n"
                f"You're in *week {week}* of your pregnancy — how exciting! 🤱\n\n"
                f"I'm all set to be your companion on this beautiful journey. "
                f"Just send me a photo or text of anything you eat and I'll tell you if it's safe and nutritious for you and your baby. 💛\n\n"
                f"Try sending me a food photo or type what you just ate! 🍽️"
            )
        except ValueError:
            send_message(sender,
                "Hmm, I couldn't read that date 😊 Please use the format *DD-MM-YYYY*\n"
                "For example: *15-10-2026*"
            )
        return

    # ACTIVE USER — food analysis
    name = user.get("name", "")
    due_date_str = user.get("due_date", "")
    system_prompt = build_system_prompt(name, due_date_str)

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
                        "source": {"type": "base64", "media_type": media_type, "data": image_data},
                    },
                    {
                        "type": "text",
                        "text": incoming_msg if incoming_msg else "Please analyze this food for pregnancy safety."
                    }
                ]
            })
        else:
            messages.append({"role": "user", "content": incoming_msg})

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=system_prompt,
            messages=messages
        )
        reply = response.content[0].text

    except Exception as e:
        import traceback
        reply = "Sorry, Janani is unavailable right now. Please try again in a moment. 🙏"
        print(f"Error: {e}")
        traceback.print_exc()

    send_message(sender, reply)


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    media_url = request.values.get("MediaUrl0", None)
    sender = request.values.get("From", "")

    thread = threading.Thread(target=process_and_reply, args=(sender, incoming_msg, media_url))
    thread.start()

    return str(MessagingResponse())


@app.route("/", methods=["GET"])
def health():
    return "Janani Sakhi is running 🌸"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
