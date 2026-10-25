from flask import Flask, request, Response
import requests
import json
import os
import shutil
import pytz
import re
from datetime import datetime, time

app = Flask(__name__)

# --- CONFIGURATION ---
MASTER_FILE = "/data/master_episodes.json"
LAST_UPDATE_FILE = "/data/last_update.txt"
SHOW_ID = "1700000084"
TIME_TO_UPDATE = time(20, 31) # 20:31 = 8:31 PM

# --- API TOKENS & HEADERS ---
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjaGFubmVsUGFydG5lcklEIjoiTVNNSU5EIiwiY29udGFjdElEIjoiNDczNTI0MjI2IiwiZGF0ZU9mQmlydGgiOjc3ODk2MjYwMDAwMCwiZW1haWwiOiJ5azcwOTMwNTZAZ21haWwuY29tIiwiZXhwIjoxODExODA5OTYyLCJleHBpcmF0aW9uTW9tZW50IjoiMjAyNy0wNi0wMVQwMDozMjo0Mi43NzRaIiwiZmlyc3ROYW1lIjoiQXJ2aW5kIiwiZ2VuZGVyIjoiRmVtYWxlIiwiaWF0IjoxNzgwMjczOTYyLCJpc0N1c3RvbWVyRWxpZ2libGVGb3JGcmVlVHJpYWwiOmZhbHNlLCJpc0VtYWlsVmVyaWZpZWQiOnRydWUsImlzTW9iaWxlVmVyaWZpZWQiOnRydWUsImlzUHJvZmlsZUNvbXBsZXRlIjp0cnVlLCJsYXN0TmFtZSI6IkdmeCIsIm1vYmlsZU51bWJlciI6IjYzOTU4MDI3NTgiLCJwcm9maWxlUGljIjoiaHR0cHM6Ly9vcmlnaW4tc3RhdGljdjIuc29ueWxpdi5jb20vVUlfaWNvbnMvTW9iaWxlX0F2YXRhcnNfMDMucG5nIiwic2Vzc2lvbkNyZWF0aW9uVGltZSI6IjIwMjYtMDYtMDFUMDA6MzI6NDIuNzc0WiIsInNvY2lhbExvZ2luSUQiOiJHVV8xMTE2MDc5MDM3NDMxNDU5NjA4MzMiLCJzb2NpYWxMb2dpblR5cGUiOiJHb29nbGUiLCJzb2NpYWxQcm9maWxlUGljIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jSWZwTFVjbUg4YklSVW5lRHFHUzV1dU1rU1p3cWo4d3RxemNEUkJGWFFBSllnaDhRPXMxMDAiLCJ0b2tlbiI6ImU1V20tM09KVi00Tjh0LUcwVnktY1Vpai1nblRjLU13IiwidXNlcklkIjoiMjQwOTEwMTAwODE5OTczODYyNyJ9.nbO7tqv7JDcO-zvnekXirhoXJjoeXh_uH87W8dHh_tg"
SESSION_ID = "c5e7c4ef0f091d5e_1780273929491"
DEVICE_ID = "83a25beee1317224"
USER_AGENT = "com.sonyliv/6.34.4 ( Android17; en_IN; SM-S928B; Build/CP2A.260605.016 )"

PROXY_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept-Encoding': 'identity',
    'x-playback-session-id': SESSION_ID
}

# --- HELPER FUNCTIONS ---

def load_db():
    # Agar /data me file nahi hai, par purani file root me hai, toh auto-copy karein
    if not os.path.exists(MASTER_FILE):
        if os.path.exists("master_episodes.json"):
            shutil.copy("master_episodes.json", MASTER_FILE)
            print("✅ Data volume me copy ho gaya!")
            
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_db(data):
    with open(MASTER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_last_update_time():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, 'r') as f:
            return f.read().strip()
    return ""

def set_last_update_time():
    with open(LAST_UPDATE_FILE, 'w') as f:
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        f.write(now_ist.strftime("%Y-%m-%d"))

def check_and_update_new_episodes():
    """Check if it's past 8:31 PM and update hasn't run today"""
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    today_str = now_ist.strftime("%Y-%m-%d")
    
    current_time = now_ist.time()
    last_update = get_last_update_time()

    # Agar aaj update ho chuka hai, toh wapas jao
    if last_update == today_str:
        return False

    # Agar time 8:31 PM se pehle hai, toh update mat karo
    if current_time < TIME_TO_UPDATE:
        return False

    print("⏰ 8:31 PM ho gaya hai! Checking for new episodes...")
    
    # Nayi API se latest 10 episodes fetch karo
    api_url = f"https://apiv3.sonyliv.com/AGL/4.7/SR/ENG/ANDROID_PHONE/IN/GJ/DETAIL-V3/{SHOW_ID}"
    params = {'from': "0", 'to': "10", 'kids_safe': "false"}
    headers = {
        'User-Agent': USER_AGENT,
        'Accept-Encoding': "gzip",
        'build_number': "20495",
        'app_version': "6.34.4",
        'device_id': DEVICE_ID,
        'session_id': SESSION_ID
    }

    try:
        res = requests.get(api_url, params=params, headers=headers).json()
        db = load_db()
        existing_ep_numbers = {ep['episodeNumber'] for ep in db}
        new_episodes_added = 0

        # JSON me deeply search karo episodes ke liye
        def extract_episodes(data):
            nonlocal new_episodes_added
            if isinstance(data, dict):
                if "episodeNumber" in data and "contentId" in data:
                    ep_num = data["episodeNumber"]
                    if ep_num not in existing_ep_numbers:
                        # Naya episode mil gaya!
                        date_str = "Unknown Date"
                        if data.get("originalAirDate"):
                            date_str = datetime.fromtimestamp(data["originalAirDate"]/1000.0).strftime('%Y-%m-%d')
                        
                        db.append({
                            "episodeNumber": ep_num,
                            "episodeTitle": data.get("episodeTitle", "Unknown"),
                            "contentId": data.get("contentId"),
                            "airDate": date_str,
                            "originalUnixDate": data.get("originalAirDate")
                        })
                        existing_ep_numbers.add(ep_num)
                        new_episodes_added += 1
                        print(f"✅ Added new Ep {ep_num}")
                
                for v in data.values():
                    extract_episodes(v)
            elif isinstance(data, list):
                for item in data:
                    extract_episodes(item)

        extract_episodes(res)
        
        if new_episodes_added > 0:
            db.sort(key=lambda x: x['episodeNumber'])
            save_db(db)
            
        set_last_update_time()
        return True
    except Exception as e:
        print(f"❌ API Error: {e}")
        return False


# --- ROUTES ---

@app.route('/playlist.m3u', methods=['GET'])
def generate_m3u():
    # Step 1: Check if we need to auto-update
    check_and_update_new_episodes()

    # Step 2: Load latest DB and generate M3U
    db = load_db()
    base_url = f"http://{request.host}/play"
    
    m3u_content = ["#EXTM3U"]
    for ep in db:
        ep_num = ep['episodeNumber']
        title = ep['episodeTitle']
        date = ep['airDate']
        
        display_name = f"{date} - Ep {ep_num} - {title}"
        stream_url = f"{base_url}?ep={ep_num}&date={date}"
        
        m3u_content.append(f'#EXTINF:10 tvg-id="{ep_num}" tvg-name="{display_name}",{display_name}')
        m3u_content.append(stream_url)

    return Response("\n".join(m3u_content), mimetype='application/vnd.apple.mpegurl')


@app.route('/play', methods=['GET'])
def play_episode():
    ep_num = request.args.get('ep')
    if not ep_num:
        return "Missing 'ep' parameter", 400
        
    db = load_db()
    ep_data = next((item for item in db if str(item["episodeNumber"]) == str(ep_num)), None)
    
    if not ep_data:
        return f"Episode {ep_num} not found in database", 404

    content_id = str(ep_data['contentId'])

    # ... (Video URL API logic) ...
    api_url = f"https://apiv2.sonyliv.com/AGL/5.0/SR/ENG/ANDROID_PHONE/IN/GJ/CONTENT/VIDEOURL/VOD/{content_id}"
    params = {'contactId': "473524226", 'kids_safe': "false", 'partnerName': "NA"}
    payload = {
        "actionType": "play",
        "adsParams": {"app_ver": "6.34.4", "gId": "bac199fc2fcb6eb25bec614ba3025f6f", "Idtype": "adid", "Is_lat": "0", "ppid": "0bd46cd548b8d5ca1f5be9ef68f392b2", "rdid": "6ffdd4c9-6ac7-47d4-b34c-f4c5d017f625"},
        "assetId": content_id, "browser": "chrome", "deviceId": DEVICE_ID, "drmDeviceId": "67039276-c513-407b-bddd-0be9bb897e98", "os": "android", "platform": "web"
    }
    headers = {'User-Agent': USER_AGENT, 'Accept-Encoding': "identity", 'Content-Type': "application/json", 'authorization': TOKEN, 'device_id': DEVICE_ID, 'session_id': SESSION_ID}

    try:
        response = requests.post(api_url, params=params, json=payload, headers=headers)
        video_url = response.json().get("resultObj", {}).get("videoURL")
        if not video_url:
            return f"API Error: Could not find videoURL", 500
    except Exception as e:
        return f"Server Error: {str(e)}", 500

    # --- 2. Fetch and Modify .mpd using Regex ---
    try:
        mpd_resp = requests.get(video_url, headers=PROXY_HEADERS)
        mpd_resp.raise_for_status()
        mpd_text = mpd_resp.text

        base_dir = video_url.split('?')[0].rsplit('/', 1)[0] + '/'
        mpd_text = re.sub(r'<BaseURL>.*?</BaseURL>', '', mpd_text)
        mpd_text = re.sub(r'(<MPD[^>]*>)', rf'\1<BaseURL>{base_dir}</BaseURL>', mpd_text, count=1)

        return Response(mpd_text, mimetype='application/dash+xml')

    except Exception as e:
        return f"Manifest Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
