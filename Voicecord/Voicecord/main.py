import os
import sys
import json
import time
import requests
import websocket._core as websocket
import threading
from keep_alive import keep_alive

status = "dnd"  # online/dnd/idle
GUILD_ID = 1369197776596111440
CHANNEL_ID = 1414553057517371546
SELF_MUTE = False
SELF_DEAF = False

# Load tokens from tokens.txt
if not os.path.exists("tokens.txt"):
    print("[ERROR] tokens.txt file not found.")
    sys.exit()

with open("tokens.txt", "r") as f:
    tokens = [line.strip() for line in f if line.strip()]

if not tokens:
    print("[ERROR] No tokens found in tokens.txt.")
    sys.exit()


def validate_token(token):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    r = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
    if r.status_code == 200:
        return r.json()
    return None


def joiner(token, status):
    try:
        ws = websocket.create_connection('wss://gateway.discord.gg/?v=10&encoding=json')
        start = json.loads(ws.recv())
        heartbeat_interval = start['d']['heartbeat_interval'] / 1000

        # Authenticate
        auth = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {"$os": "Windows 10", "$browser": "Google Chrome", "$device": "Windows"},
                "presence": {"status": status, "afk": False}
            },
            "s": None,
            "t": None
        }
        ws.send(json.dumps(auth))

        # Wait for READY
        while True:
            msg = json.loads(ws.recv())
            if msg.get('t') == 'READY':
                break

        # Join VC
        vc = {"op": 4, "d": {"guild_id": GUILD_ID, "channel_id": CHANNEL_ID, "self_mute": SELF_MUTE, "self_deaf": SELF_DEAF}}
        ws.send(json.dumps(vc))

        last_heartbeat = time.time()
        while True:
            if time.time() - last_heartbeat >= heartbeat_interval:
                ws.send(json.dumps({"op": 1, "d": None}))
                last_heartbeat = time.time()

            ws.settimeout(0.1)
            try:
                msg = ws.recv()
                data = json.loads(msg)
                if data.get('op') == 11:  # Heartbeat ACK
                    print("Heartbeat acknowledged")
            except:
                pass

            time.sleep(0.1)

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        ws.close()


def run_all_tokens():
    os.system("cls" if os.name == "nt" else "clear")
    threads = []

    for token in tokens:
        userinfo = validate_token(token)
        if userinfo:
            print(f"Logged in as {userinfo['username']}#{userinfo['discriminator']} ({userinfo['id']})")
            t = threading.Thread(target=joiner, args=(token, status))
            t.start()
            threads.append(t)
        else:
            print(f"[ERROR] Invalid token: {token}")

    # Optional: wait for all threads (they never actually finish unless connection drops)
    for t in threads:
        t.join()


keep_alive()
run_all_tokens()
