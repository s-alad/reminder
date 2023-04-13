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
account_sid = twilio_sid
auth_token = twilio_token
client = Client(account_sid, auth_token)
#==================================================================================================

def numbered(n): return str(n) + ('th' if 11<=n%100<=13 else {1:'st',2:'nd',3:'rd'}.get(n%10, 'th'))

app = Flask(__name__)

connect = sqlite3.connect('users.db')
connect.execute('''
    CREATE TABLE IF NOT EXISTS USERS
    ([user_id] INTEGER PRIMARY KEY, [phone] TEXT, [state] INTEGER DEFAULT 1, [reminder] INTEGER DEFAULT 1)
''')

def remind(text):
    #get list of phone numbers from users
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()

    cursor.execute('SELECT phone FROM USERS')
    numbers = cursor.fetchall()

    #send reminder to each phone number
    for phone in numbers:
        message = client.messages.create(body=text,from_=twilio_number, to=phone)
        print('Reminder sent to ' + str(phone) + ' | ' + message.sid)

    cursor.execute("UPDATE USERS SET state = 0 WHERE state = 1")
    connect.commit()

def reminder():
    remind("This is your daily reminder to take your medicine, reply with the number 1 to confirm")

def checker():
    print("Checking...")
    #open up users.db and check if the state column is not equal to 0
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute('SELECT * FROM USERS WHERE state = 0')
    data = cursor.fetchall()

    #if the state column is not equal to 0, send a reminder to the user
    for user in data:
        id = user[0]
        phone = user[1]
        reminder = user[3]
        text = "This is your {} reminder to take your medicine, reply with the number 1 to confirm".format(numbered(reminder))
        message = client.messages.create(body=text,from_=twilio_number, to=phone)
        print('{} Reminder sent to '.format(numbered(reminder)) + str(phone) + ' | ' + message.sid)

        cursor.execute("UPDATE USERS SET reminder = reminder + 1 WHERE user_id = ?", (id,))
        connect.commit()
    
    print("Checked")

@app.route("/check")
def check():
    checker()
    return redirect('/')

@app.route("/remind")
def remindme():
    remind("forced: This is your daily reminder, reply with the number 1 to confirm")
    return redirect('/')

@app.route("/adduser/<phone>")
def adduser(phone: str):
    print(phone)
    with sqlite3.connect("users.db") as users:
        cursor = users.cursor()
        cursor.execute("INSERT OR IGNORE INTO USERS (phone, state, reminder) VALUES (?,?,?)", (phone, 1, 1))
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

    recieved_number = request.values.get('From', None)
    print(recieved_number)

    resp = MessagingResponse()

    if body == '1':
        resp.message("confirmed!")

        connect = sqlite3.connect('users.db')
        cursor = connect.cursor()
        cursor.execute("UPDATE USERS SET state = 1 WHERE phone = ?", (recieved_number,))
        cursor.execute("UPDATE USERS SET reminder = 1 WHERE phone = ?", (recieved_number,))
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

sched = BackgroundScheduler(daemon=True)
sched.add_job(reminder,'cron', hour=9, minute=15, timezone='America/New_York')
sched.add_job(reminder,'cron', hour=21, minute=20, timezone='America/New_York')
sched.add_job(checker, 'interval', minutes=30, timezone='America/New_York')
sched.start()

if __name__ == "__main__":
    app.run(debug=True)
