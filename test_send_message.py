"""Test script to send a WhatsApp message directly via API"""
import os
import sys
from dotenv import load_dotenv
import requests

load_dotenv()

token = os.getenv('WHATSAPP_ACCESS_TOKEN')
phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')

print(f"Using Phone Number ID: {phone_id}")
print(f"Token valid: {token[:20]}...")

# Get recipient phone number from command line or prompt
if len(sys.argv) > 1:
    recipient = sys.argv[1]
else:
    recipient = input("Enter recipient phone number (with country code, e.g., 34612345678): ")

# Remove any + or spaces
recipient = recipient.replace('+', '').replace(' ', '')

print(f"\nSending test message to: {recipient}")

url = f'https://graph.facebook.com/v18.0/{phone_id}/messages'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}
data = {
    'messaging_product': 'whatsapp',
    'to': recipient,
    'type': 'text',
    'text': {'body': 'Test message from RPmini API test script'}
}

response = requests.post(url, headers=headers, json=data)

print(f"\nStatus Code: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    print("\n✓ Message sent successfully!")
else:
    print("\n✗ Message failed. Check the error above.")
