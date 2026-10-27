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
OLD_MASTER_FILE = "master_episodes.json"

SHOWS_CONFIG = [
    {
        "name": "Tarak Maheta",
        "id": "1700000084",
        "update_time": time(20, 31), # 8:31 PM IST
        "is_new": False
    },
    {
        "name": "Hastinapur ke veer",
        "id": "1790007734", 
        "update_time": time(21, 1),  # 9:01 PM IST
        "is_new": True
    },
    {
        "name": "Pushpa Impossible",
        "id": "1700000921", 
        "update_time": time(21, 31), # 9:31 PM IST
        "is_new": True
    }
]

TOKEN = "YOUR_NEW_TOKEN_HERE" # <-- Apna naya token daal lein
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
    data = {}
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    elif os.path.exists(OLD_MASTER_FILE):
        shutil.copy(OLD_MASTER_FILE, MASTER_FILE)
        with open(MASTER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    if isinstance(data, list):
        new_data = {"Tarak Maheta": data}
        save_db(new_data)
        return new_data
    
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

# YAHAN FORCE PARAMETER ADD KIYA HAI
def check_and_update_new_episodes(force_update=False):
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
        
        # Agar force update nahi hai, tabhi time aur date check karo
        if not force_update:
            if current_time < update_time:
                continue
            if get_last_update_date(show_name) == today_str:
                continue

        print(f"⏰ Checking for {show_name} (Force: {force_update})...")
        
        api_url = f"https://apiv3.sonyliv.com/AGL/4.7/SR/ENG/ANDROID_PHONE/IN/GJ/DETAIL-V3/{show_id}"
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
                    
                    for v in data.values():
                        extract_episodes(v)
                elif isinstance(data, list):
                    for item in data:
                        extract_episodes(item)

            extract_episodes(res)
            
            if new_episodes_added > 0:
                db[show_name].sort(key=lambda x: x['episodeNumber'])
                db_changed = True
                print(f"✅ Added {new_episodes_added} new episodes for {show_name}")
            else:
                print(f"ℹ️ No new episodes found for {show_name}")
                
            set_last_update_date(show_name)
            
        except Exception as e:
            print(f"❌ API Error for {show_name}: {e}")

    if db_changed:
        save_db(db)

# --- ROUTES ---

@app.route('/playlist.m3u', methods=['GET'])
def generate_m3u():
    # Check karo agar URL me ?force=1 hai
    force = request.args.get('force') == '1'
    
    check_and_update_new_episodes(force_update=force)
    db = load_db()
    
    base_url = request.host_url
    if "localhost" not in base_url and "127.0.0.1" not in base_url:
        base_url = base_url.replace("http://", "https://")
    base_url += "play"
    
    m3u_content = ["#EXTM3U"]
    
    for show_name, episodes in db.items():
        if not episodes:
            continue
            
        group_title = f"SAB | {show_name}"
        show_id_for_url = next((s["id"] for s in SHOWS_CONFIG if s["name"] == show_name), "")
        
        for ep in reversed(episodes):
            ep_num = ep['episodeNumber']
            title = ep['episodeTitle']
            date = ep['airDate']
            
            display_name = f"{date} - Ep {ep_num} - {title}"
            
            unique_tvg_id = f"{show_id_for_url}_{ep_num}"
            stream_url = f"{base_url}?show={show_id_for_url}&ep={ep_num}&date={date}"
            
            m3u_content.append(f'#EXTINF:10 tvg-id="{unique_tvg_id}" group-title="{group_title}", {display_name}')
            m3u_content.append(stream_url)

    return Response("\n".join(m3u_content), mimetype='application/vnd.apple.mpegurl')


# ... (Play route waisa hi rahega, use same rakhein) ...
@app.route('/play', methods=['GET'])
def play_episode():
    # (Aapka play route ka code yahan aayega, jo bilkul same hai pichle code jaisa)
    pass 

if __name__ == '__main__':
    load_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
