import os
from twilio.rest import Client

# Twilio Credentials from environment variables
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Initialize Twilio Client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Send a WhatsApp message
message = client.messages.create(
    from_="whatsapp:+14155238886",  # Twilio Sandbox Number
    to="whatsapp:+919673839208",  # User's WhatsApp Number
    body="Hello Ranjeet"
)

# Print message SID
print(f"Message sent with SID: {message.sid}")