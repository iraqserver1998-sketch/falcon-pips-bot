import logging
import asyncio
import cloudscraper
import pytz
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= إعدادات البوت =================
# ⚠️ استبدل هذا التوكن بتوكن بوتك من BotFather
BOT_TOKEN = "8450630765:AAG0oBdaYc9uZavkmEJdoNRXhOwL3ITdG38"
# معرف القناة (تأكد ان البوت مشرف بالقناة)
CHANNEL_ID = "@falcon_pips"

# توقيت بغداد (لضبط المواعيد)
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')

# ================= اللوج (Logging) =================
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= المتغيرات العامة =================
# لتخزين الأخبار التي تم التنبيه عنها لتجنب التكرار
NOTIFIED_NEWS = set()

# ================= دوال التحليل والترجمة =================

def clean_number(text):
    """تحويل الأرقام من نص (مثل 1.2K) إلى رقم فعلي للمقارنة"""
    if not text: return None
    text = text.replace(',', '').replace('%', '').strip()
    multiplier = 1
    if 'K' in text:
        multiplier = 1000
        text = text.replace('K', '')
    elif 'M' in text:
        multiplier = 1000000
        text = text.replace('M', '')
    elif 'B' in text:
        multiplier = 1000000000
        text = text.replace('B', '')
    
    try:
        return float(text) * multiplier
    except ValueError:
        return None

def analyze_impact(event_name, actual, forecast, impact_str):
    """
    تحليل تأثير الخبر على الذهب بناءً على النتيجة
    القاعدة العامة: إيجابي للدولار = سلبي للذهب (والعكس)
    """
    if actual is None or forecast is None:
        return "⚪️ النتيجة متعادلة أو غير واضحة."

    # تحديد نوع العلاقة (معظم الأخبار إيجابية للدولار إذا كانت النتيجة أعلى من المتوقع)
    # ما عدا البطالة (Unemployment) وتطالبات الإعانة (Jobless Claims) فهي عكسية
    reverse_logic = any(x in event_name.lower() for x in ['unemployment', 'jobless', 'budget deficit'])
    
    diff = actual - forecast
    
    if diff == 0:
        return "⚪️ النتيجة طابقت التوقعات (تأثير محايد)."

    # منطق الدولار
    usd_positive = (diff > 0) if not reverse_logic else (diff < 0)
    
    if usd_positive:
        return f"🇺🇸 **إيجابي للدولار** (أفضل من المتوقع)\n📉 **سلبي للذهب (هبوط محتمل)**"
    else:
        return f"🇺🇸 **سلبي للدولار** (أسوأ من المتوقع)\n📈 **إيجابي للذهب (صعود محتمل)**"

# ================= دوال السكرابينج (Forex Factory) =================

def get_forex_news():
    """سحب الأخبار من موقع Forex Factory لليوم الحالي"""
    scraper = cloudscraper.create_scraper()
    url = "https://www.forexfactory.com/calendar?day=today"
    
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            logger.error("فشل الاتصال بالموقع")
            return []

        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.find('table', class_='calendar__table')
        
        if not table:
            return []

        news_list = []
        rows = table.find_all('tr', class_='calendar__row')

        for row in rows:
            try:
                # استخراج العملة
                currency_cell = row.find('td', class_='calendar__currency')
                currency = currency_cell.text.strip() if currency_cell else ""
                
                # نركز فقط على USD
                if currency != 'USD':
                    continue

                # استخراج قوة الخبر (Impact)
                impact_cell = row.find('td', class_='calendar__impact')
                impact_span = impact_cell.find('span') if impact_cell else None
                impact_class = impact_span['class'][0] if impact_span else ""
                
                # High (Red) or Medium (Orange)
                impact_level = "Low"
                if 'high' in impact_class or 'red' in impact_class:
                    impact_level = "High"
                elif 'medium' in impact_class or 'orange' in impact_class:
                    impact_level = "Medium"
                else:
                    continue # تجاهل الأخبار الضعيفة

                # استخراج الوقت
                time_cell = row.find('td', class_='calendar__time')
                time_str = time_cell.text.strip()
                
                # استخراج الاسم
                event_cell = row.find('td', class_='calendar__event')
                event_name = event_cell.text.strip() if event_cell else "News"

                # الأرقام (للمقارنة لاحقاً)
                actual_cell = row.find('td', class_='calendar__actual')
                forecast_cell = row.find('td', class_='calendar__forecast')
                
                actual_val = clean_number(actual_cell.text)
                forecast_val = clean_number(forecast_cell.text)
                actual_txt = actual_cell.text.strip()
                forecast_txt = forecast_cell.text.strip()

                news_item = {
                    'id': row['data-eventid'],
                    'time': time_str,
                    'currency': currency,
                    'event': event_name,
                    'impact': impact_level,
                    'actual': actual_val,
                    'forecast': forecast_val,
                    'actual_txt': actual_txt,
                    'forecast_txt': forecast_txt
                }
                news_list.append(news_item)

            except Exception as e:
                continue
        
        return news_list

    except Exception as e:
        logger.error(f"Error scraping: {e}")
        return []

# ================= وظائف البوت المجدولة =================

async def send_msg(text):
    """إرسال رسالة للتليجرام"""
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Telegram Error: {e}")

async def check_sessions():
    """فحص افتتاح الجلسات"""
    now = datetime.now(BAGHDAD_TZ)
    current_time = now.strftime("%H:%M")
    
    # مواعيد الجلسات (بتوقيت بغداد التقريبي - يفضل تحديثها حسب التوقيت الصيفي/الشتوي)
    # لندن عادة 10:00 ص أو 11:00 ص حسب الموسم
    # نيويورك عادة 4:00 م أو 3:00 م حسب الموسم
    
    if current_time == "10:00":
        await send_msg("🔴 **تنبيه جلسات:**\nتم افتتاح **جلسة لندن (London Session)** 🇬🇧.\nتوقع بدء ارتفاع السيولة.")
    elif current_time == "15:00":
        await send_msg("🔴 **تنبيه جلسات:**\nتم افتتاح **جلسة نيويورك (New York Session)** 🇺🇸.\nالسيولة في ذروتها، انتبه لحركة الذهب!")

async def market_watch_job():
    """الوظيفة الرئيسية: فحص الأخبار والتنبيه"""
    logger.info("Checking markets...")
    news_data = await asyncio.to_thread(get_forex_news)
    
    now_baghdad = datetime.now(BAGHDAD_TZ)
    
    for item in news_data:
        # تحويل وقت الخبر إلى كائن datetime
        # ForexFactory وقته عادة بتوقيت السيرفر او امريكا، هذا الجزء يحتاج معايرة دقيقة
        # للتبسيط: سنفترض ان السكرابر يجيب وقت، ونحن نقارن بالساعة الحالية تقريباً
        # (الحل الادق هو تحويل وقت الموقع الى توقيت بغداد)
        
        # ملاحظة: في النسخة المبسطة هذه سنعتمد على التنبيه عند صدور النتيجة (Actual)
        
        # 1. تنبيه قبل الخبر (اذا لم تصدر النتيجة بعد)
        # هذا يحتاج ضبط توقيت دقيق جداً (Timezone mapping)
        # سأركز هنا على الأهم: "صدور النتيجة وتحليلها"
        
        if item['actual_txt'] and item['id'] not in NOTIFIED_NEWS:
            # الخبر صدر للتو!
            analysis = analyze_impact(item['event'], item['actual'], item['forecast'], item['impact'])
            
            icon = "🔥" if item['impact'] == "High" else "⚠️"
            
            msg = f"""
{icon} **عاجل: صدور نتائج اقتصادية**

📰 **الخبر:** {item['event']}
🇺🇸 **العملة:** {item['currency']}
📊 **التأثير:** {item['impact']} Impact

🔢 **الحالي:** `{item['actual_txt']}`
🔮 **المتوقع:** `{item['forecast_txt']}`

💡 **التحليل الفوري:**
{analysis}

@falcon_pips
"""
            await send_msg(msg)
            NOTIFIED_NEWS.add(item['id'])

# ================= التشغيل =================

async def main():
    # جدولة المهام
    scheduler = AsyncIOScheduler(timezone=BAGHDAD_TZ)
    
    # فحص الأخبار كل دقيقة
    scheduler.add_job(market_watch_job, 'interval', minutes=1)
    
    # فحص الجلسات كل دقيقة
    scheduler.add_job(check_sessions, 'cron', second='0')
    
    scheduler.start()
    logger.info("Bot started and scheduler running...")
    
    # إبقاء البوت يعمل للأبد
    while True:
        await asyncio.sleep(1000)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
