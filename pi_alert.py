import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP
from twilio.rest import Client
from bs4 import BeautifulSoup
import requests

def send_sms(curr_price):
    account_sid = os.environ.get("TWILIO_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        from_=os.environ.get("TWILIO_FROM_NUMBER"),
        to=os.environ.get("TWILIO_TO_NUMBER"),
        body=f'Pi Price: {curr_price}'
    )
    print(message.sid)

def send_alert(curr_price):
    my_email = os.environ.get("SMTP_EMAIL")
    password = os.environ.get("SMTP_PASSWORD")
    to_email = os.environ.get("TO_EMAIL")

    msg = f"Sell PI with current price: {curr_price}"
    message = MIMEMultipart()
    message['From'] = my_email
    message['To'] = to_email
    message['Subject'] = msg
    message.attach(MIMEText(msg, 'plain'))

    with SMTP("smtp-relay.brevo.com", port=587) as connection:
        connection.starttls()
        connection.login(user=my_email, password=password)
        connection.sendmail(from_addr=my_email, to_addrs=to_email, msg=message.as_string())

def send_telegram_msg(curr_price):
    # Your credentials
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")  # Use the negative ID for groups

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    message = f'Pi Price: {curr_price}'
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Message sent to family!")
        else:
            print(f"Failed to send: {response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

URL = "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/market-pairs/latest?slug=pi&start=1&limit=10&category=spot&centerType=all&sort=cmc_rank_advanced&direction=desc&spotUntracked=true"
response = requests.get(url=URL)
for market in response.json()['data']['marketPairs']:
    if market['exchangeName'] == 'Bitget':
        if float(market['price']) >= 0.1 :
            send_telegram_msg(market['price'])
        else:
            print("Price is less than 1")
        exit(0)
print("unable to fetch PI value")
        

    
