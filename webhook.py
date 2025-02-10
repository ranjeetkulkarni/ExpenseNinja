import os
from flask import Flask, request, Response
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

RASA_SERVER_URL = os.getenv("RASA_SERVER_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

def send_whatsapp_message(to, message):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = {
        "From": TWILIO_WHATSAPP_NUMBER,
        "To": to,
        "Body": message,
    }
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    try:
        response = requests.post(url, data=data, auth=auth, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e}")
        return None

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_data = request.values  # Handles both form & query params
    message = incoming_data.get("Body")
    sender = incoming_data.get("From")  # WhatsApp sender's number

    if not message or not sender:
        return Response("Invalid request", status=400)

    # Send message to Rasa for processing
    payload = {"sender": sender, "message": message}

    try:
        rasa_response = requests.post(RASA_SERVER_URL, json=payload, timeout=5)
        rasa_response.raise_for_status()
        responses = rasa_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Rasa: {e}")
        return Response("Error processing request", status=500)

    # Send each Rasa response back to the user via WhatsApp
    for r in responses:
        if "text" in r:
            send_whatsapp_message(sender, r["text"])

    return Response("<Response></Response>", status=200, mimetype="application/xml")

if __name__ == "__main__":
    app.run(port=8000, debug=True)
