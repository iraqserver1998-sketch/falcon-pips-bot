from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta

TOKEN = "8450630765:AAG0oBdaYc9uZavkmEJdoNRXhOwL3ITdG38"
CHANNEL = "@falconpips"

bot = Bot(token=TOKEN)
scheduler = BlockingScheduler(timezone="Asia/Baghdad")

def send(msg):
    bot.send_message(chat_id=CHANNEL, text=msg)

# ===== الجلسات =====
def asian():
    send("🌏 افتتاح الجلسة الآسيوية – Falcon Pips\n\nسيولة ضعيفة ⚠️")

def london():
    send("🇪🇺 افتتاح الجلسة الأوروبية – Falcon Pips\n\nأعلى سيولة 🔥")

def newyork():
    send("🇺🇸 افتتاح الجلسة الأمريكية – Falcon Pips\n\nتقلبات قوية 💥")

scheduler.add_job(asian, 'cron', hour=2, minute=0)
scheduler.add_job(london, 'cron', hour=10, minute=0)
scheduler.add_job(newyork, 'cron', hour=15, minute=30)

print("Falcon Pips Bot Running...")
scheduler.start()
