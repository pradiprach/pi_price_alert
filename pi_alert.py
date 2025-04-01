import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP

from bs4 import BeautifulSoup
import requests

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

URL = "https://www.bitget.site/spot/PIUSDT"
response = requests.get(url=URL)
soup = BeautifulSoup(response.text, 'html.parser')

title = soup.select_one(selector="title")
current_price = float(title.text.split("|")[0].strip())
print(f"PI Current Price: {current_price}")
if current_price > 1.7:
    send_alert(current_price)

