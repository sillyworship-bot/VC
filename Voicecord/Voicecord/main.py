
import os
import sys
import json
import time
import requests
import websocket._core as websocket
import threading
from keep_alive import keep_alive

# Configuration
STATUS = "idle"
GUILD_ID = 1369197776596111440
CHANNEL_ID = 1416019406269452298
SELF_MUTE = True
SELF_DEAF = False

# Load tokens
if not os.path.exists("tokens.txt"):
    print("[ERROR] tokens.txt not found")
    sys.exit()

with open("tokens.txt", "r") as f:
    tokens = [line.strip() for line in f if line.strip()]

if not tokens:
    print("[ERROR] No tokens found")
    sys.exit()


def validate_token(token):
    try:
        r = requests.get('https://discord.com/api/v10/users/@me', 
                        headers={"Authorization": token}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def joiner(token):
    while True:
        try:
            ws = websocket.create_connection('wss://gateway.discord.gg/?v=10&encoding=json')
            
            # Get heartbeat interval
            heartbeat_interval = json.loads(ws.recv())['d']['heartbeat_interval'] / 1000
            
            # Auth payload
            ws.send(json.dumps({
                "op": 2,
                "d": {
                    "token": token,
                    "properties": {"$os": "linux", "$browser": "chrome", "$device": "linux"},
                    "presence": {"status": STATUS, "afk": False}
                }
            }))
            
            # Wait for READY event
            while json.loads(ws.recv()).get('t') != 'READY':
                pass
            
            # Join voice channel
            ws.send(json.dumps({
                "op": 4,
                "d": {
                    "guild_id": GUILD_ID,
                    "channel_id": CHANNEL_ID,
                    "self_mute": SELF_MUTE,
                    "self_deaf": SELF_DEAF
                }
            }))
            
            print("Connected to voice channel")
            
            # Heartbeat loop
            last_heartbeat = time.time()
            while True:
                if time.time() - last_heartbeat >= heartbeat_interval:
                    ws.send(json.dumps({"op": 1, "d": None}))
                    last_heartbeat = time.time()
                
                ws.settimeout(0.5)
                try:
                    ws.recv()
                except:
                    pass
                
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Error: {e}")
            try:
                ws.close()
            except:
                pass
            time.sleep(10)


def main():
    os.system("clear")
    
    for token in tokens:
        user = validate_token(token)
        if user:
            print(f"Starting: {user['username']}#{user['discriminator']}")
            threading.Thread(target=joiner, args=(token,), daemon=True).start()
        else:
            print(f"Invalid token: {token[:20]}...")
    
    # Keep main thread alive
    while True:
        time.sleep(60)


if __name__ == "__main__":
    keep_alive()
    main()
