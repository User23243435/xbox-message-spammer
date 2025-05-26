import streamlit as st
import asyncio
import aiohttp
import threading
import queue
import time
import os
import json
import re
import urllib.parse
import warnings

# --------- Initialize session state early ---------
if 'api_key_index' not in st.session_state:
    st.session_state['api_key_index'] = 0
if 'current_view' not in st.session_state:
    st.session_state['current_view'] = 'login'
if 'profile' not in st.session_state:
    st.session_state['profile'] = None
if 'last_spam_time' not in st.session_state:
    st.session_state['last_spam_time'] = 0

# --------- API Keys ---------
API_KEYS = [
    "your-api-key-1",
    "your-api-key-2",
    "your-api-key-3"
]

def get_next_api_key():
    index = st.session_state['api_key_index']
    key = API_KEYS[index]
    st.session_state['api_key_index'] = (index + 1) % len(API_KEYS)
    return key

# --------- Async functions ---------
async def convert_gamertag_to_xuid(gamertag):
    gamertag = str(gamertag)  # Ensure gamertag is a string to avoid quote error
    api_key = get_next_api_key()
    headers = {
        "accept": "*/*",
        "x-authorization": api_key,
        "Content-Type": "application/json"
    }
    url = f"https://xbl.io/api/v2/search/{urllib.parse.quote(gamertag)}"
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(url, headers=headers)
            data = await resp.json()
            if "people" in data and data["people"]:
                xuid = data["people"][0]["xuid"]
                return xuid
    except Exception as e:
        print("Error in convert_gamertag_to_xuid:", e)
    return None

async def send_message(xuid, message):
    headers = {
        "accept": "*/*",
        "x-authorization": get_next_api_key(),
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://xbl.io/api/v2/conversations",
            json={"message": message, "xuid": xuid},
            headers=headers
        )
        return await resp.json()

# --------- Load or create users ---------
users_file = "users.json"
if not os.path.exists(users_file):
    users = {
        "SlumpdOWN": {
            "password": "Slumpd9669$",
            "gamertag": "see slumpd",
            "xuid": ""
        }
    }
    with open(users_file, "w") as f:
        json.dump(users, f)
else:
    try:
        with open(users_file, "r") as f:
            users = json.load(f)
        if not isinstance(users, dict):
            raise json.JSONDecodeError("Invalid", "", 0)
    except:
        users = {
            "SlumpdOWN": {
                "password": "Slumpd9669$",
                "gamertag": "see slumpd",
                "xuid": ""
            }
        }
        with open(users_file, "w") as f:
            json.dump(users, f)

# --------- Helper to rerun ---------
def safe_rerun():
    st.experimental_rerun()

# --------- UI: Styles ---------
import warnings
warnings.filterwarnings("ignore", message="missing ScriptRunContext!")

st.set_page_config(page_title="Xbox Tools", page_icon="🎮")
st.markdown("""
<style>
body { margin:0; padding:0; }
.stApp {
    margin-top:0; padding-top:0;
    background-image: url("https://i.imgur.com/wg6k91A.jpeg");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    min-height: 100vh;
    font-family: 'Orbitron', sans-serif;
}
header { display:none !important; }
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
div[data-testid="stHelpSidebar"] { display:none; }
h1,h2,h3,h4,h5,h6 {
    color: #00ffff; 
    text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff;
}
button {
    background-color: #00ffff;
    border: none;
    padding: 12px 24px;
    border-radius: 50px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.3s ease;
    font-family: 'Orbitron', sans-serif;
    color: #000;
}
button:hover {
    background-color: #00cccc;
    transform: scale(1.05);
}
input[type=text], input[type=password], textarea, select, input[type=number] {
    width: 100%;
    padding: 14px 20px;
    margin-top: 8px;
    margin-bottom: 15px;
    border-radius: 10px;
    border: none;
    background: rgba(255,255,255,0.2);
    color: #00ffff;
    font-family: 'Orbitron', sans-serif;
    font-size: 1em;
}
input[type=text]:focus, input[type=password]:focus, textarea:focus {
    background: rgba(255,255,255,0.3);
    box-shadow: 0 0 10px #00ffff;
}
.small-text {
    color: #00ffff;
    font-family: 'Orbitron', sans-serif;
    font-size: 1em;
    text-shadow: 0 0 5px #00ffff, 0 0 10px #00ffff;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;">
    <img src="https://i.imgur.com/uAQOm2Y.png" 
         style="width:600px; max-width:90%; height:auto; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-top:20px;">
</div>
""", unsafe_allow_html=True)

# --------- Login/Register UI ---------
if st.session_state['current_view'] == 'login':
    with st.container():
        st.title("🎮 Welcome to Xbox Tools")
        mode = st.radio("Mode", ["Login", "Register"], index=0)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if mode == "Register":
            st.markdown('<div class="small-text">**Example Profile URL:**</div>', unsafe_allow_html=True)
            st.write("https://www.xbox.com/en-US/play/user/User1234")
            profile_link = st.text_input("Paste your Xbox profile URL")
            if st.button("Verify Profile Link"):
                if not profile_link:
                    st.error("Please paste your profile URL.")
                else:
                    match = re.search(r"/user/([^/]+)", profile_link)
                    if not match:
                        st.error("Invalid URL.")
                    else:
                        gamertag = urllib.parse.unquote(match.group(1))
                        with st.spinner("Verifying gamertag..."):
                            xuid = asyncio.run(convert_gamertag_to_xuid(gamertag))
                        if xuid:
                            st.success(f"Verified! Gamertag: {gamertag} (XUID: {xuid})")
                            st.session_state['verified_gamertag'] = gamertag
                            st.session_state['verified_xuid'] = xuid
                        else:
                            st.error("Gamertag not found.")
            if st.button("Register"):
                # Load users if not loaded
                if 'users' not in globals():
                    with open(users_file, "r") as f:
                        users = json.load(f)
                if not username:
                    st.error("Enter username")
                elif not password:
                    st.error("Enter password")
                elif 'verified_gamertag' not in st.session_state:
                    st.error("Verify profile first")
                elif username in users:
                    st.error("Username exists")
                else:
                    users[username] = {
                        "password": password,
                        "gamertag": st.session_state['verified_gamertag'],
                        "xuid": st.session_state['verified_xuid']
                    }
                    with open(users_file, "w") as f:
                        json.dump(users, f)
                    st.success("Registered! Please login.")
                    st.experimental_rerun()
        elif st.button("Login"):
            if 'users' not in globals():
                with open(users_file, "r") as f:
                    users = json.load(f)
            if not username:
                st.error("Enter username")
            elif not password:
                st.error("Enter password")
            elif username in users and users[username]['password'] == password:
                st.session_state['current_user'] = username
                st.session_state['profile'] = users[username]
                st.session_state['current_view'] = 'main'
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

# --------- Main Dashboard ---------
elif st.session_state['current_view'] == 'main':
    user = st.session_state['profile']
    username = st.session_state['current_user']

    # Show profile info
    if username == "SlumpdOWN":
        st.markdown("### 👑 Admin Dashboard")
        st.write("Profile URL: https://www.xbox.com/en-US/play/user/see%20slumpd")
        xuid_str = user.get('xuid')
        if not xuid_str:
            xuid_str = asyncio.run(convert_gamertag_to_xuid(user.get('gamertag')))
        try:
            xuid_dec = int(xuid_str)
            xuid_hex = format(xuid_dec, '016X')
            st.write(f"XUID (hex): {xuid_hex}")
        except:
            st.write("XUID (hex): N/A")
    else:
        st.markdown("### User Dashboard")
        st.write(f"Logged in as: {username}")

    linked_gt = user.get('gamertag')
    linked_xuid = user.get('xuid')

    if linked_gt:
        st.markdown(f"**Linked Gamertag:** {linked_gt}")
        if st.button("Unlink Gamertag"):
            users[username].pop('gamertag', None)
            users[username].pop('xuid', None)
            with open(users_file, "w") as f:
                json.dump(users, f)
            st.success("Unlinked.")
            st.experimental_rerun()
        st.markdown(f"**XUID:** {linked_xuid or 'N/A'}")
    else:
        st.markdown('<div class="small-text">**Link a new Gamertag:**</div>', unsafe_allow_html=True)
        profile_url = st.text_input("Xbox profile URL")
        if st.button("Verify & Link") and profile_url:
            match = re.search(r"/user/([^/]+)", profile_url)
            if not match:
                st.error("Invalid URL.")
            else:
                gamertag = urllib.parse.unquote(match.group(1))
                with st.spinner("Verifying..."):
                    xuid = asyncio.run(convert_gamertag_to_xuid(gamertag))
                if xuid:
                    # check duplicate
                    if any(d.get('gamertag') == gamertag for u, d in users.items() if u != username):
                        st.error("This gamertag is linked to another user.")
                    elif gamertag == linked_gt:
                        st.info("Already linked")
                    else:
                        users[username]['gamertag'] = gamertag
                        users[username]['xuid'] = xuid
                        with open(users_file, "w") as f:
                            json.dump(users, f)
                        st.success("Linked!")
                        st.experimental_rerun()
                else:
                    st.error("Gamertag not found.")

    # --------- Tools sidebar ---------
    st.sidebar.title("Tools")
    tool = st.sidebar.selectbox("Select Tool", ["Convert Gamertag to XUID", "Spam Message", "Flood Reports", "Ban XUID"])

    # --------- Convert Gamertag ---------
    if tool == "Convert Gamertag to XUID":
        st.title("Convert Gamertag to XUID")
        gtag = st.text_input("Gamertag")
        if st.button("Convert"):
            with st.spinner("Converting..."):
                result = asyncio.run(convert_gamertag_to_xuid(gtag))
            if result:
                st.success(f"XUID (hex): {result}")
            else:
                st.error("Failed to convert.")

    # --------- Spam Message ---------
    elif tool == "Spam Message":
        st.title("Message Spammer")
        target_gt = st.text_input("Target Gamertag")
        message = st.text_area("Message")
        count = st.number_input("Number of messages", min_value=1, max_value=100, value=10)

        if st.button("Start Spamming"):
            now = time.time()
            if now - st.session_state['last_spam_time'] < 10:
                remaining = int(10 - (now - st.session_state['last_spam_time']))
                st.warning(f"Wait {remaining}s before spamming again.")
            else:
                st.session_state['last_spam_time'] = now

                # Thread-safe log queue
                log_queue = queue.Queue()

                # Run spam in background thread
                def spam(target_gt, message, count, log_q):
                    # Call async functions with asyncio.run() inside thread
                    try:
                        xuid = asyncio.run(convert_gamertag_to_xuid(target_gt))
                        if not xuid:
                            log_q.put("Failed to get XUID.")
                            return
                    except Exception as e:
                        log_q.put(f"Error converting gamertag: {e}")
                        return
                    for i in range(int(count)):
                        try:
                            result = asyncio.run(send_message(xuid, message))
                            if "limitType" in result:
                                log_q.put(f"[ERROR] Rate Limited at message {i+1}")
                                break
                            else:
                                log_q.put(f"[SUCCESS] Sent message {i+1}")
                        except Exception as e:
                            log_q.put(f"Error at message {i+1}: {e}")
                        time.sleep(0.5)

                threading.Thread(target=spam, args=(target_gt, message, count, log_queue)).start()

                # Poll logs
                log_placeholder = st.empty()
                while threading.active_count() > 1:
                    logs = []
                    while not log_queue.empty():
                        logs.append(log_queue.get())
                    if logs:
                        log_placeholder.write("\n".join(logs))
                    time.sleep(0.5)

                # Final logs
                logs = []
                while not log_queue.empty():
                    logs.append(log_queue.get())
                if logs:
                    log_placeholder.write("\n".join(logs))

    # --------- Flood Reports ---------
    elif tool == "Flood Reports":
        st.title("Flood Reports")
        target_gt = st.text_input("Target Gamertag")
        report_msg = st.text_area("Report message")
        count = st.number_input("Number of reports", min_value=1, max_value=100, value=30)
        if st.button("Flood Reports"):
            placeholder = st.empty()
            def flood():
                for i in range(int(count)):
                    placeholder.write(f"🚩 Reporting: {target_gt} - {report_msg} ({i+1}/{count})")
                    time.sleep(0.2)
            threading.Thread(target=flood).start()

    # --------- Ban XUID ---------
    elif tool == "Ban XUID":
        st.title("Ban XUID")
        ban_xuid = st.text_input("XUID to ban")
        if st.button("Ban"):
            banned = set()
            if os.path.exists("banned_xuids.json"):
                with open("banned_xuids.json", "r") as f:
                    banned = set(json.load(f))
            banned.add(ban_xuid)
            with open("banned_xuids.json", "w") as f:
                json.dump(list(banned), f)

    # --------- Logout ---------
    if st.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()
