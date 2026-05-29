# Janani Sakhi 🌸
### AI Pregnancy Companion — WhatsApp Bot

Janani Sakhi is a personal AI-powered WhatsApp companion for pregnant women. It analyzes food (via text or photo), estimates key pregnancy nutrients, and flags items as SAFE, CAUTION, or AVOID — all through a simple WhatsApp chat.

---

## Features
- 📸 Food photo analysis via WhatsApp
- 🥗 Nutrient estimation: protein, iron, folate, calcium
- ✅ Pregnancy safety classification (SAFE / CAUTION / AVOID)
- 🇮🇳 Culturally relevant advice for Indian food habits
- 💬 Supports Hindi and English

## Tech Stack
| Component | Technology |
|---|---|
| Messaging | Twilio WhatsApp API |
| AI Model | Claude Sonnet (Anthropic) |
| Backend | Python Flask |
| Hosting | Render |

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/janani-sakhi.git
cd janani-sakhi
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Edit .env and add your credentials
```

### 4. Run locally
```bash
python app.py
```

### 5. Expose with ngrok (for Twilio webhook)
```bash
ngrok http 5000
```
Set the ngrok URL as your Twilio sandbox webhook URL.

---

## Cost (Personal Use)
~₹300/month for a single user.

---

*Built with love for a healthier pregnancy journey* 🤱
