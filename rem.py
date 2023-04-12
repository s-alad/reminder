import os
from dotenv import load_dotenv
from flask import Flask, request, redirect
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from tzlocal import get_localzone

load_dotenv()
twilio_sid = os.getenv('TWILIO_SID')
twilio_token = os.getenv('TWILIO_TOKEN')
twilio_number = os.getenv('TWILIO_NUMBER')
twilio_to = os.getenv('TWILIO_TO')

replied = True #prime this with True

nth = 0
def numbered(n): return str(n) + ('th' if 11<=n%100<=13 else {1:'st',2:'nd',3:'rd'}.get(n%10, 'th'))

def remind(bo):
    account_sid = twilio_sid
    auth_token = twilio_token
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=bo,
        from_=twilio_number, to=twilio_to
    )
    print(message.sid)
    print('Reminder sent')
    global replied 
    print(replied)
    replied = False
    print(replied)

def reminder():
    remind("This is your daily reminder, reply with the number 1 to confirm")

def nth_reminder():
    global nth
    remind("This is your " + numbered(nth) + " reminder, reply with the number 1 to confirm")


def check():
    global replied
    global nth
    print(replied)
    if not replied:
        print('User did not reply')
        nth += 1
        nth_reminder()
    else:
        print('User replied')

sched = BackgroundScheduler(daemon=True)
sched.add_job(reminder,'cron', hour=20, minute=42, timezone='America/New_York')
sched.add_job(check, 'interval', minutes=30, timezone='America/New_York')
sched.start()

app = Flask(__name__)

@app.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
    body = request.values.get('Body', None)
    print("RECEIVED:", body)
    resp = MessagingResponse()

    if body == '1':
        resp.message("confirmed!")
        global replied
        global nth
        print(replied, nth)
        replied = True
        nth = 0
        print(replied, nth)

    return str(resp)

@app.route("/")
def index():
    return "/"

if __name__ == "__main__":
    app.run(debug=True)
