from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

TOKEN = "8450630765:AAG0oBdaYc9uZavkmEJdoNRXhOwL3ITdG38"
CHANNEL = "@falconpips"

bot = Bot(token=TOKEN)
scheduler = BlockingScheduler(timezone="Asia/Baghdad")

def send(msg):
    bot.send_message(chat_id=CHANNEL, text=msg)

# =====================
# الجلسات
# =====================
def asian():
    send("🌏 افتتاح الجلسة الآسيوية – Falcon Pips\n\nسيولة ضعيفة ⚠️")

def london():
    send("🇪🇺 افتتاح الجلسة الأوروبية – Falcon Pips\n\nأعلى سيولة 🔥")

def newyork():
    send("🇺🇸 افتتاح الجلسة الأمريكية – Falcon Pips\n\nتقلبات قوية 💥")

scheduler.add_job(asian, 'cron', hour=2, minute=0)
scheduler.add_job(london, 'cron', hour=10, minute=0)
scheduler.add_job(newyork, 'cron', hour=15, minute=30)

# =====================
# جلب الأخبار
# =====================
def fetch_news():
    url = "https://www.forexfactory.com/calendar"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    events = soup.select("tr.calendar_row")

    for event in events:
        try:
            currency = event.select_one(".currency").text.strip()
            impact = event.select_one(".impact span")["class"][1]

            if currency == "USD" and impact == "high":
                title = event.select_one(".event").text.strip()
                time_str = event.select_one(".time").text.strip()

                if time_str == "":
                    continue

                event_time = datetime.strptime(time_str, "%I:%M%p")
                event_time = event_time.replace(
                    year=datetime.now().year,
                    month=datetime.now().month,
                    day=datetime.now().day
                )

                alert_time = event_time - timedelta(minutes=30)

                scheduler.add_job(
                    send,
                    'date',
                    run_date=alert_time,
                    args=[f"🚨 تنبيه خبر مهم – Falcon Pips\n\n📊 {title}\n🔥 التأثير: قوي\n⏰ بعد 30 دقيقة\n⚠️ الذهب قد يشهد تقلبات"]
                )

        except:
            pass

# =====================
# جدولة جلب الأخبار
# =====================
scheduler.add_job(fetch_news, 'cron', hour=0, minute=5)

print("Falcon Pips Bot Running...")
scheduler.start()

