import os
import sqlite3
from dotenv import load_dotenv
from flask import Flask, request, redirect
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from tzlocal import get_localzone
#==================================================================================================
load_dotenv()
twilio_sid = os.getenv('TWILIO_SID')
twilio_token = os.getenv('TWILIO_TOKEN')
twilio_number = os.getenv('TWILIO_NUMBER')
twilio_to = os.getenv('TWILIO_TO')
#==================================================================================================
replied = True #prime this with True

nth = 0
def numbered(n): return str(n) + ('th' if 11<=n%100<=13 else {1:'st',2:'nd',3:'rd'}.get(n%10, 'th'))

app = Flask(__name__)

connect = sqlite3.connect('users.db')
connect.execute('''
          CREATE TABLE IF NOT EXISTS USERS
          ([user_id] INTEGER PRIMARY KEY, [phone] TEXT, [state] INTEGER DEFAULT 1, [reminder] INTEGER DEFAULT 1)
          ''')

def remind(text):
    account_sid = twilio_sid
    auth_token = twilio_token
    client = Client(account_sid, auth_token)
    message = client.messages.create(body=text,from_=twilio_number, to=twilio_to)

    print(message.sid)
    print('Reminder sent')
    global replied 
    print(replied)
    replied = False
    print(replied)

    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("UPDATE USERS SET state = 1 WHERE state = 0")
    connect.commit()


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
sched.add_job(reminder,'cron', hour=21, minute=7, timezone='America/New_York')
sched.add_job(check, 'interval', minutes=30, timezone='America/New_York')
sched.start()

@app.route("/remind")
def remindme():
    remind("force push 1")
    return redirect('/')

@app.route("/adduser/<phone>")
def adduser(phone: str):
    print(phone)
    with sqlite3.connect("users.db") as users:
        cursor = users.cursor()
        cursor.execute("INSERT INTO USERS (phone, state, reminder) VALUES (?,?,?)", (phone, 0, 1))
        users.commit()
    return redirect('/')

@app.route("/updateuser/<phone>/<state>")
def updateuser(phone: str, state: int):
    print(phone, state)
    with sqlite3.connect("users.db") as users:
        cursor = users.cursor()
        cursor.execute("UPDATE USERS SET state = ? WHERE phone = ?", (state, phone))
        users.commit()
    return redirect('/')

@app.route("/getusers")
def getusers():
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute('SELECT * FROM USERS')
    data = cursor.fetchall()
    return str(data)

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

        connect = sqlite3.connect('users.db')
        cursor = connect.cursor()
        cursor.execute("UPDATE USERS SET state = 0 WHERE state = 1")
        connect.commit()

    return str(resp)

@app.route("/drop")
def drop():
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("DROP TABLE USERS")
    connect.commit()
    return redirect('/')

@app.route("/")
def index():
    return "/"

if __name__ == "__main__":
    app.run(debug=True)
