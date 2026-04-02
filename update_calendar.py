import os
import requests
import pytz
from datetime import datetime, timedelta
from icalendar import Calendar, Event

# --- 설정 ---
NX, NY = 60, 127             # 서울 격자
REG_ID = '11B10101'          # 중기육상(서울)
REG_TEMP_ID = '11B10101'     # 중기기온(서울)
API_KEY = os.environ.get('KMA_API_KEY')

def get_emoji(sky, pty):
    if pty and pty != '0':
        if pty in ['1', '4']: return "🌧️"
        if pty == '2': return "🌨️"
        if pty == '3': return "❄️"
    if sky == '1': return "☀️"
    if sky == '3': return "⛅"
    if sky == '4': return "☁️"
    return "🌡️"

def fetch_data(url):
    try:
        res = requests.get(url)
        if res.status_code == 200:
            return res.text
    except: return None
    return None

def main():
    seoul_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(seoul_tz)
    cal = Calendar()
    cal.add('X-WR-CALNAME', '기상청 날씨 달력')
    
    # 1. 단기 예보 (0~3일) 파싱 로직
    base_date = now.strftime('%Y%m%d')
    url_short = f"https://apihub.kma.go.kr/api/typ01/url/vsc_sfc_af_dtl.php?base_date={base_date}&nx={NX}&ny={NY}&authKey={API_KEY}"
    raw_short = fetch_data(url_short)
    
    daily_data = {} # 날짜별로 묶기
    if raw_short:
        lines = raw_short.split('\n')
        for line in lines:
            if line.startswith('#') or len(line) < 10: continue
            cols = line.split()
            # 기상청 단기예보 컬럼 순서: 일자(0), 시간(1), ... 기온(12), 하늘(13), 강수형태(14), 강수확률(15), 습도(16), 풍속(17)
            dt, tm = cols[0], cols[1]
            tmp, sky, pty, pop, reh, wsd = cols[12], cols[13], cols[14], cols[15], cols[16], cols[17]
            
            if dt not in daily_data: daily_data[dt] = {'tmps': [], 'details': []}
            daily_data[dt]['tmps'].append(float(tmp))
            emoji = get_emoji(sky, pty)
            daily_data[dt]['details'].append(f"[{tm[:2]}:00] {emoji} {tmp}°C, ☔{pop}%, 💧{reh}%, 💨{wsd}m/s")

    # 2. 캘린더 생성 (0~10일)
    for i in range(11):
        target_dt_obj = now + timedelta(days=i)
        target_dt_str = target_dt_obj.strftime('%Y%m%d')
        event = Event()
        
        if target_dt_str in daily_data:
            # 단기예보가 있는 날 (0~3일)
            d = daily_data[target_dt_str]
            t_min, t_max = min(d['tmps']), max(d['tmps'])
            # 대표 이모지는 낮 12시 기준으로 설정 (없으면 첫번째)
            rep_emoji = d['details'][len(d['details'])//2].split()[1]
            event.add('summary', f"{rep_emoji} {t_min}° / {t_max}°")
            event.add('description', "\n".join(d['details']))
        else:
            # 중기예보 구간 (4~10일) - 실제 중기 API 연동 전 샘플
            event.add('summary', f"⛅ {10+i}° / {20+i}°")
            event.add('description', "중기 예보 정보 데이터 준비 중")

        event.add('dtstart', target_dt_obj.date())
        event.add('dtend', target_dt_obj.date() + timedelta(days=1))
        cal.add_component(event)

    with open('weather.ics', 'wb') as f:
        f.write(cal.to_ical())
    print("Successfully updated weather.ics")

if __name__ == "__main__":
    main()
