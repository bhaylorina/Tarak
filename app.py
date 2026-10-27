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

# --- SHOWS CONFIGURATION (TIMES UPDATED) ---
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

# --- API TOKENS & HEADERS ---
# YAHAN APNA NAYA TOKEN DAALEIN
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
    data = {}
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    elif os.path.exists(OLD_MASTER_FILE):
        shutil.copy(OLD_MASTER_FILE, MASTER_FILE)
        with open(MASTER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("✅ Old Data copied to /data/")

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
        
        # Time check
        if current_time < update_time:
            continue
            
        # Daily update check
        if get_last_update_date(show_name) == today_str:
            continue

        print(f"⏰ {update_time.strftime('%I:%M %p')} ho gaya hai! Checking for {show_name}...")
        
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
                
            set_last_update_date(show_name)
            
        except Exception as e:
            print(f"❌ API Error for {show_name}: {e}")

    if db_changed:
        save_db(db)


# --- ROUTES ---

@app.route('/playlist.m3u', methods=['GET'])
def generate_m3u():
    check_and_update_new_episodes()
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


@app.route('/play', methods=['GET'])
def play_episode():
    ep_num = request.args.get('ep')
    show_id = request.args.get('show')
    
    if not ep_num or not show_id:
        return "Missing 'ep' or 'show' parameter", 400
        
    show_name = next((s["name"] for s in SHOWS_CONFIG if s["id"] == show_id), None)
    
    if not show_name:
        return f"Show not found for ID {show_id}", 404
        
    db = load_db()
    show_episodes = db.get(show_name, [])
    ep_data = next((item for item in show_episodes if str(item["episodeNumber"]) == str(ep_num)), None)
    
    if not ep_data:
        return f"Episode {ep_num} not found for show {show_name}", 404

    content_id = str(ep_data['contentId'])

    # --- Video URL API Logic ---
    api_url = f"https://apiv2.sonyliv.com/AGL/5.0/SR/ENG/ANDROID_PHONE/IN/GJ/CONTENT/VIDEOURL/VOD/{content_id}"
    
    params = {
        'contactId': "473524226",
        'kids_safe': "false",
        'partnerName': "NA"
    }

    payload = {
        "actionType": "play",
        "adsParams": {
            "app_ver": "6.34.4",
            "gId": "c06704015c0b184809d05c5b1a0a86a5",
            "Idtype": "adid",
            "Is_lat": "0",
            "ppid": "0bd46cd548b8d5ca1f5be9ef68f392b2",
            "rdid": "6ffdd4c9-6ac7-47d4-b34c-f4c5d017f625"
        },
        "assetId": content_id,
        "browser": "chrome",
        "deeplinkLang": "",
        "deviceId": DEVICE_ID,
        "drmDeviceId": "9fb7f6e7-fe3b-45c4-9808-fed2ff88314c",
        "hasLAURLEnabled": False,
        "os": "android",
        "platform": "web"
    }

    headers = {
        'User-Agent': USER_AGENT,
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json",
        'x-via-device': "true",
        'authorization': TOKEN,
        'td_client_hints': "{\"os_name\":\"Android\",\"os_version\":\"17\",\"ram\":11,\"device_type\":\"phone\",\"device_make\":\"samsung\",\"device_model\":\"SM-S928B\",\"conn_type\":\"4G\",\"auto_retry\":false,\"app_version\":\"6.34.4\",\"client_throughput\":357,\"td_user_useragent\":\"Dalvik\\/2.1.0 (Linux; U; Android 17; SM-S928B Build\\/CP2A.260605.016)\",\"display_res\":2160,\"viewport_res\":2160,\"supp_codec\":\"AC3,H264,HEVC,AV1,\",\"hdr_decoder\":\"HDR10,HLG,HDR10_PLUS,\",\"audio_decoder\":\"AC3\"}",
        'advertiserid': "6ffdd4c9-6ac7-47d4-b34c-f4c5d017f625",
        'device_id': DEVICE_ID,
        'app_version': "6.34.4",
        'session_id': SESSION_ID,
        'build_number': "20495"
    }

    try:
        response = requests.post(api_url, params=params, data=json.dumps(payload), headers=headers)
        res_json = response.json()
        video_url = res_json.get("resultObj", {}).get("videoURL")
        
        if not video_url:
            # DEBUG CODE HATA DIYA HAI. Ab ye player ko simple error bhejega
            return f"API Error: Could not find videoURL for content {content_id}", 500
            
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
    load_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
