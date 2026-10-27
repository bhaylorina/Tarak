from flask import Flask, request, Response
import requests
import json
import os
import shutil
import pytz
import re
import urllib.parse
from datetime import datetime, time

app = Flask(__name__)

# --- CONFIGURATION ---
MASTER_FILE = "/data/master_episodes.json"
# Purani file ka backup path agar migrate karna ho
OLD_MASTER_FILE = "master_episodes.json"

# --- SHOWS CONFIGURATION ---
# Note: Pushpa aur Hosiyarpur ki Show ID aapko SonyLIV app se nikalni hogi.
SHOWS_CONFIG = [
    {
        "name": "Tarak Maheta",
        "id": "1700000084",
        "update_time": time(20, 31), # 8:31 PM
        "is_new": False
    },
    {
        "name": "Hosiyarpur",
        "id": "1700007734", # <-- Yahan Hosiyarpur ki actual SonyLIV ID dalein
        "update_time": time(00, 1),  # 9:01 PM
        "is_new": True
    },
    {
        "name": "Pushpa Impossible",
        "id": "1700000921", # <-- Yahan Pushpa ki actual SonyLIV ID dalein
        "update_time": time(00, 1), # 9:31 PM
        "is_new": True
    }
]

# --- API TOKENS & HEADERS ---
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjaGFubmVsUGFydG5lcklEIjoiTVNNSU5EIiwiY29udGFjdElEIjoiNDczNTI0MjI2IiwiZGF0ZU9mQmlydGgiOjc3ODk2MjYwMDAwMCwiZW1haWwiOiJ5azcwOTMwNTZAZ21haWwuY29tIiwiZXhwIjoxODExODA5OTYyLCJleHBpcmF0aW9uTW9tZW50IjoiMjAyNy0wNi0wMVQwMDozMjo0Mi43NzRaIiwiZmlyc3ROYW1lIjoiQXJ2aW5kIiwiZ2VuZGVyIjoiRmVtYWxlIiwiaWF0IjoxNzgwMjczOTYyLCJpc0N1c3RvbWVyRWxpZ2libGVGb3JGcmVlVHJpYWwiOmZhbHNlLCJpc0VtYWlsVmVyaWZpZWQiOnRydWUsImlzTW9iaWxlVmVyaWZpZWQiOnRydWUsImlzUHJvZmlsZUNvbXBsZXRlIjp0cnVlLCJsYXN0TmFtZSI6IkdmeCIsIm1vYmlsZU51bWJlciI6IjYzOTU4MDI3NTgiLCJwcm9maWxlUGljIjoiaHR0cHM6Ly9vcmlnaW4tc3RhdGljdjIuc29ueWxpdi5jb20vVUlfaWNvbnMvTW9iaWxlX0F2YXRhcnNfMDMucG5nIiwic2Vzc2lvbkNyZWF0aW9uVGltZSI6IjIwMjYtMDYtMDFUMDA6MzI6NDIuNzc0WiIsInNvY2lhbExvZ2luSUQiOiJHVV8xMTE2MDc5MDM3NDMxNDU5NjA4MzMiLCJzb2NpYWxMb2dpblR5cGUiOiJHb29nbGUiLCJzb2NpYWxQcm9maWxlUGljIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jSWZwTFVjbUg4YklSVW5lRHFHUzV1dU1rU1p3cWo4d3RxemNEUkJGRlFBSllnaDhRPXMxMDAiLCJ0b2tlbiI6ImU1V20tM09KVi00Tjh0LUcwVnktY1Vpai1nblRjLU13IiwidXNlcklkIjoiMjQwOTEwMTAwODE5OTczODYyNyJ9.nbO7tqv7JDcO-zvnekXirhoXJjoeXh_uH87W8dHh_tg"
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
    """Loads JSON, auto-migrates old format, and ensures structure is correct"""
    data = {}
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    elif os.path.exists(OLD_MASTER_FILE):
        # Agar purani file root me hai, toh volume me copy karein
        shutil.copy(OLD_MASTER_FILE, MASTER_FILE)
        with open(MASTER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("✅ Old Data copied to /data/")

    # MIGRATION LOGIC: Agar data list format me hai (purana TMKOC wala), toh dictionary me convert karo
    if isinstance(data, list):
        print("🔄 Migrating old list format to new multi-show dictionary format...")
        new_data = {"Tarak Maheta": data}
        save_db(new_data)
        return new_data
    
    # Agar dictionary hai, par shows missing hain, toh add karo
    if not isinstance(data, dict):
        data = {}
    
    for show in SHOWS_CONFIG:
        if show["name"] not in data:
            data[show["name"]] = []
            
    return data

def save_db(data):
    with open(MASTER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_last_update_date(show_name):
    """File read karke check karta hai ki aaj is show ka update hua hai ya nahi"""
    file_path = f"/data/last_update_{show_name.replace(' ', '_')}.txt"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read().strip()
    return ""

def set_last_update_date(show_name):
    file_path = f"/data/last_update_{show_name.replace(' ', '_')}.txt"
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    with open(file_path, 'w') as f:
        f.write(now_ist.strftime("%Y-%m-%d"))

def check_and_update_new_episodes():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    today_str = now_ist.strftime("%Y-%m-%d")
    current_time = now_ist.time()
    
    db = load_db()
    db_changed = False

    for show in SHOWS_CONFIG:
        show_name = show["name"]
        show_id = show["id"]
        update_time = show["update_time"]
        is_new = show["is_new"]
        
        # 1. Time check (Agar time nahi hua hai, toh skip karo)
        if current_time < update_time:
            continue
            
        # 2. Aaj ka update check (Agar aaj ho chuka hai, toh skip karo)
        if get_last_update_date(show_name) == today_str:
            continue

        print(f"⏰ {update_time.strftime('%I:%M %p')} ho gaya hai! Checking for {show_name}...")
        
        api_url = f"https://apiv3.sonyliv.com/AGL/4.7/SR/ENG/ANDROID_PHONE/IN/GJ/DETAIL-V3/{show_id}"
        # Agar naya show hai, toh sirf 2 episodes fetch karenge taaki yesterday ka mil jaye
        # Warna latest 10 fetch karenge
        fetch_count = "2" if is_new and len(db[show_name]) == 0 else "10"
        
        params = {'from': "0", 'to': fetch_count, 'kids_safe': "false"}
        headers = {
            'User-Agent': USER_AGENT, 'Accept-Encoding': "gzip",
            'app_version': "6.34.4", 'device_id': DEVICE_ID, 'session_id': SESSION_ID
        }

        try:
            res = requests.get(api_url, params=params, headers=headers).json()
            
            existing_ep_numbers = {ep['episodeNumber'] for ep in db[show_name]}
            new_episodes_added = 0

            def extract_episodes(data):
                nonlocal new_episodes_added
                if isinstance(data, dict):
                    if "episodeNumber" in data and "contentId" in data:
                        ep_num = data["episodeNumber"]
                        if ep_num not in existing_ep_numbers:
                            date_str = "Unknown Date"
                            if data.get("originalAirDate"):
                                date_str = datetime.fromtimestamp(data["originalAirDate"]/1000.0).strftime('%Y-%m-%d')
                            
                            db[show_name].append({
                                "episodeNumber": ep_num,
                                "episodeTitle": data.get("episodeTitle", "Unknown"),
                                "contentId": data.get("contentId"),
                                "airDate": date_str,
                                "originalUnixDate": data.get("originalAirDate")
                            })
                            existing_ep_numbers.add(ep_num)
                            new_episodes_added += 1
                            print(f"✅ {show_name}: Added Ep {ep_num} ({date_str})")
                    
                    for v in data.values():
                        extract_episodes(v)
                elif isinstance(data, list):
                    for item in data:
                        extract_episodes(item)

            extract_episodes(res)
            
            if new_episodes_added > 0:
                db[show_name].sort(key=lambda x: x['episodeNumber'])
                db_changed = True
                
            set_last_update_date(show_name)
            
        except Exception as e:
            print(f"❌ API Error for {show_name}: {e}")

    if db_changed:
        save_db(db)
        print("💾 Database saved successfully.")


# --- ROUTES ---

@app.route('/playlist.m3u', methods=['GET'])
def generate_m3u():
    # Step 1: Check for all shows based on their times
    check_and_update_new_episodes()

    # Step 2: Load latest DB
    db = load_db()
    base_url = f"http://{request.host}/play"
    
    m3u_content = ["#EXTM3U"]
    
    # Loop through all shows and their episodes
    for show_name, episodes in db.items():
        if not episodes:
            continue
            
        # Group name banayenge (Jaisa aap chahte hain: SAB | ShowName)
        group_title = f"SAB | {show_name}"
        
        # Episodes ko reverse karenge taaki latest sabse upar dikhe
        for ep in reversed(episodes):
            ep_num = ep['episodeNumber']
            title = ep['episodeTitle']
            date = ep['airDate']
            
            display_name = f"{date} - Ep {ep_num} - {title}"
            
            # Play route me show name aur ep number dono pass karenge
            safe_show_name = urllib.parse.quote(show_name)
            stream_url = f"{base_url}?show={safe_show_name}&ep={ep_num}&date={date}"
            
            m3u_content.append(f'#EXTINF:10 tvg-id="{ep_num}" group-title="{group_title}", {display_name}')
            m3u_content.append(stream_url)

    return Response("\n".join(m3u_content), mimetype='application/vnd.apple.mpegurl')


@app.route('/play', methods=['GET'])
def play_episode():
    ep_num = request.args.get('ep')
    show_name = request.args.get('show') # Ab show ka naam bhi aa raha hai
    
    if not ep_num or not show_name:
        return "Missing 'ep' or 'show' parameter", 400
        
    db = load_db()
    
    # Correct show ke andar episode dhundenge
    show_episodes = db.get(show_name, [])
    ep_data = next((item for item in show_episodes if str(item["episodeNumber"]) == str(ep_num)), None)
    
    if not ep_data:
        return f"Episode {ep_num} not found for show {show_name}", 404

    content_id = str(ep_data['contentId'])

    # --- Video URL API Logic ---
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

    # --- MPD Proxy Logic ---
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
    # Server start hote hi DB load/initialize karega
    load_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
