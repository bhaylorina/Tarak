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
    {"name": "Tarak Maheta", "id": "1700000084", "update_time": time(20, 31), "is_new": False},
    {"name": "Hastinapur ke veer", "id": "1790007734", "update_time": time(21, 1), "is_new": True},
    {"name": "chudel", "id": "1790007924", "update_time": time(1, 5), "is_new": True},
    {"name": "Pushpa Impossible", "id": "1700000921", "update_time": time(21, 31), "is_new": True}
]

# YAHAN APNA NAYA TOKEN DAALEIN (Agar abhi bhi purana hai toh)
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjaGFubmVsUGFydG5lcklEIjoiTVNNSU5EIiwiY29udGFjdElEIjoiNTMxODE4NDAiLCJkYXRlT2ZCaXJ0aCI6MzY1OTkwNDAwMDAwLCJlbWFpbCI6Imxha2hvYmltQGdtYWlsLmNvbSIsImV4cCI6MTgyNzI0NTQwNCwiZXhwaXJhdGlvbk1vbWVudCI6IjIwMjctMTEtMjZUMTY6MTA6MDQuMzM1WiIsImZpcnN0TmFtZSI6IlJpcGFsIiwiZ2VuZGVyIjoiTWFsZSIsImlhdCI6MTc5NTcwOTQwNCwiaXNDdXN0b21lckVsaWdpYmxlRm9yRnJlZVRyaWFsIjpmYWxzZSwiaXNFbWFpbFZlcmlmaWVkIjp0cnVlLCJpc01vYmlsZVZlcmlmaWVkIjp0cnVlLCJpc1Byb2ZpbGVDb21wbGV0ZSI6ZmFsc2UsImxhc3ROYW1lIjoiY2hhbmQiLCJtb2JpbGVOdW1iZXIiOiI5ODc5NzAwNjI5IiwicHJvZmlsZVBpYyI6Imh0dHBzOi8vb3JpZ2luLXN0YXRpY3YyLnNvbnlsaXYuY29tL1VJX2ljb25zL01vYmlsZV9BdmF0YXJzXzAxLnBuZyIsInNlc3Npb25DcmVhdGlvblRpbWUiOiIyMDI2LTExLTI2VDE2OjEwOjA0LjMzNVoiLCJzb2NpYWxMb2dpbklEIjoiMTAwNjU5MDcwNDc5ODg3MTI1NTc5Iiwic29jaWFsTG9naW5UeXBlIjoiR29vZ2xlIiwic29jaWFsUHJvZmlsZVBpYyI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FBVFhBSnp0M2JHUG1zdE1hSm90U0Z3YUZ0SE5NaEEwUmw0LThLSEZTSmotPXMxMDAiLCJ0b2tlbiI6InVMVVQtNk9DZi1NVEFvLVdTbVAtZllQZi1rbkh4LXlYIiwidXNlcklkIjoiMTgwMjAxMTgwNTUzMTc5NjU5In0.nvMJnzUwSZPs3QBJFn17KmzANZVOOPp-dEQ1mAoBX-Q"
SESSION_ID = "0f9d8f8bd761f4ea_1795709225600"
DEVICE_ID = "0f9d8f8bd761f4ea"
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
        
        if not force_update:
            if current_time < update_time:
                continue
            if get_last_update_date(show_name) == today_str:
                continue

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


@app.route('/play', methods=['GET'])
def play_episode():
    try:
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
        
        params = {'contactId': "473524226", 'kids_safe': "false", 'partnerName': "NA"}
        
        payload = {
            "actionType": "play",
            "adsParams": {
                "app_ver": "6.34.4", "gId": "9cf9b8c468051508104fcba470383a38",
                "Idtype": "adid", "Is_lat": "0", "ppid": "5a3bd61489e7fbf1b46298516b940162", "rdid": "1fc3d968-4a01-4cbf-892d-d3cec3838dd3"
            },
            "assetId": content_id, "browser": "chrome", "deviceId": DEVICE_ID,
            "drmDeviceId": "4e537b9d-8fbd-4126-b732-aa234c93ae3d",
            "hasLAURLEnabled": False, "os": "android", "platform": "web"
        }

        headers = {
            'User-Agent': USER_AGENT, 'Accept-Encoding': "gzip", 'Content-Type': "application/json",
            'x-via-device': "true", 'authorization': TOKEN,
            'td_client_hints': "{\"os_name\":\"Android\",\"os_version\":\"17\",\"ram\":11,\"device_type\":\"phone\",\"device_make\":\"samsung\",\"device_model\":\"SM-S928B\",\"conn_type\":\"4G\",\"auto_retry\":false,\"app_version\":\"6.34.4\",\"client_throughput\":357,\"td_user_useragent\":\"Dalvik\\/2.1.0 (Linux; U; Android 17; SM-S928B Build\\/CP2A.260605.016)\",\"display_res\":2160,\"viewport_res\":2160,\"supp_codec\":\"AC3,H264,HEVC,AV1,\",\"hdr_decoder\":\"HDR10,HLG,HDR10_PLUS,\",\"audio_decoder\":\"AC3\"}",
            'advertiserid': "1fc3d968-4a01-4cbf-892d-d3cec3838dd3",
            'device_id': DEVICE_ID, 'app_version': "6.34.4", 'session_id': SESSION_ID, 'build_number': "20495"
        }

        # 1. API Call
        response = requests.post(api_url, params=params, data=json.dumps(payload), headers=headers)
        
        # 2. Check if API returned valid JSON (Catch HTML blocks)
        try:
            res_json = response.json()
        except ValueError:
            return f"API Block Error: SonyLIV ne JSON nahi bheja. Status Code: {response.status_code}. Response: {response.text[:200]}", 500

        # 3. Safely extract videoURL
        result_obj = res_json.get("resultObj")
        if not result_obj:
            return f"API Error: resultObj not found. Full Response: {res_json}", 500
            
        video_url = result_obj.get("videoURL")
        if not video_url:
            return f"API Error: videoURL missing for content {content_id}.", 500

        # ================== PROXY LOGIC (HOST REWRITE) ==================
        SOURCE_HOST = "sonynondrmvod.akamaized.net"
        TARGET_HOST = "securetoken.sonyliv.com"

        # Sirf host badal do, path + query (hdntl token) same rahega
        video_url = video_url.replace(
            f"https://{SOURCE_HOST}/",
            f"https://{TARGET_HOST}/"
        )

        mpd_resp = requests.get(video_url, headers=PROXY_HEADERS)
        mpd_resp.raise_for_status()
        mpd_text = mpd_resp.text

        base_dir = video_url.split('?')[0].rsplit('/', 1)[0] + '/'
        mpd_text = re.sub(r'<BaseURL>.*?</BaseURL>', '', mpd_text)
        mpd_text = re.sub(r'(<MPD[^>]*>)', rf'\1<BaseURL>{base_dir}</BaseURL>', mpd_text, count=1)

        return Response(mpd_text, mimetype='application/dash+xml')
        # ================== END PROXY LOGIC ==================

    except Exception as e:
        # Ye block kisi bhi unexpected crash ko pakad lega aur error dikhayega
        import traceback
        error_details = traceback.format_exc()
        print(error_details) # Railway logs me dikhega
        return f"CRITICAL SERVER ERROR:\n{str(e)}\n\nDetails:\n{error_details}", 500

if __name__ == '__main__':
    load_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
