from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import pytz

# =========================
# الإعدادات
# =========================
TOKEN = "ضع_توكن_بوتك_هنا"
CHANNEL  = "@falconpips"  # ضع هنا رقم القناة الخاص بك

bot = Bot(token=TOKEN)
scheduler = BlockingScheduler(timezone="Asia/Baghdad")  # توقيت العراق

# =========================
# دالة الإرسال للقناة فقط
# =========================
def send(msg):
    bot.send_message(chat_id=CHANNEL_ID, text=msg)

# =========================
# تنبيهات الجلسات
# =========================
def asian_session():
    send("🌏 افتتاح الجلسة الآسيوية – Falcon Pips\n\nسيولة ضعيفة ⚠️")

def london_session():
    send("🇪🇺 افتتاح الجلسة الأوروبية – Falcon Pips\n\nأعلى سيولة 🔥")

def newyork_session():
    send("🇺🇸 افتتاح الجلسة الأمريكية – Falcon Pips\n\nتقلبات قوية 💥")


scheduler.add_job(asian_session, 'cron', hour=2, minute=0)
scheduler.add_job(london_session, 'cron', hour=10, minute=0)
scheduler.add_job(newyork_session, 'cron', hour=15, minute=30)


scheduler.add_job(newyork_alert, 'date', run_date=datetime.now() + timedelta(seconds=30), coalesce=True)
scheduler.add_job(newyork_session, 'date', run_date=datetime.now() + timedelta(seconds=60), coalesce=True)

# =========================
# دالة جلب الأخبار الاقتصادية المهمة
# =========================
def fetch_news():
    url = "https://www.forexfactory.com/calendar"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        events = soup.select("tr.calendar_row")

        for event in events:
            try:
                currency = event.select_one(".currency").text.strip()
                impact_class = event.select_one(".impact span")["class"]
                impact = "low"
                if "high" in impact_class:
                    impact = "high"

                # فقط أخبار الدولار العالية
                if currency == "USD" and impact == "high":
                    title = event.select_one(".event").text.strip()
                    time_str = event.select_one(".time").text.strip()

                    if time_str == "":
                        continue

                    # تحويل الوقت لتوقيت العراق
                    event_time = datetime.strptime(time_str, "%I:%M%p")
                    now = datetime.now()
                    event_time = event_time.replace(
                        year=now.year, month=now.month, day=now.day
                    )
                    tz = pytz.timezone("Asia/Baghdad")
                    event_time = tz.localize(event_time)

                    # التنبيه قبل 30 دقيقة
                    alert_time = event_time - timedelta(minutes=30)

                    # رسالة قبل الخبر
                    send_before = (
                        f"🚨 خبر اقتصادي مرتقب – Falcon Pips\n\n"
                        f"📊 {title}\n"
                        f"⏰ بعد 30 دقيقة\n"
                        f"🔥 التأثير: عالي\n"
                        f"⚠️ الذهب قد يشهد تقلبات\n\n"
                        f"— Falcon Pips 🦅"
                    )

                    scheduler.add_job(
                        send,
                        'date',
                        run_date=alert_time,
                        args=[send_before]
                    )

                    # رسالة بعد الخبر
                    send_after = (
                        f"📊 نتيجة الخبر – Falcon Pips\n\n"
                        f"📈 {title} صدرت الآن\n"
                        f"🔥 التأثير: عالي\n"
                        f"⚠️ الذهب قد يتحرك بقوة\n\n"
                        f"— Falcon Pips 🦅"
                    )

                    scheduler.add_job(
                        send,
                        'date',
                        run_date=event_time,
                        args=[send_after]
                    )

            except Exception:
                continue
    except Exception:
        send("⚠️ خطأ في جلب الأخبار – حاول لاحقاً")

# =========================
# جدولة جلب الأخبار كل يوم 00:05 صباحاً
# =========================
scheduler.add_job(fetch_news, 'cron', hour=0, minute=5)

# =========================
# تشغيل البوت
# =========================
print("Falcon Pips Bot Running...")
scheduler.start()





