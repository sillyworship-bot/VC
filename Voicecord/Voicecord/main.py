import os
import sys
import json
import time
import requests
import websocket._core as websocket
from keep_alive import keep_alive

status = "dnd" #online/dnd/idle

GUILD_ID = 1400099069111832716
CHANNEL_ID = 1407074952934330368
SELF_MUTE = False
SELF_DEAF = False

usertoken = os.getenv("TOKEN")
if not usertoken:
  print("[ERROR] Please add a token inside Secrets.")
  sys.exit()

headers = {"Authorization": usertoken, "Content-Type": "application/json"}

validate = requests.get('https://canary.discordapp.com/api/v9/users/@me', headers=headers)
if validate.status_code != 200:
  print("[ERROR] Your token might be invalid. Please check it again.")
  sys.exit()

userinfo = requests.get('https://canary.discordapp.com/api/v9/users/@me', headers=headers).json()
username = userinfo["username"]
discriminator = userinfo["discriminator"]
userid = userinfo["id"]

def joiner(token, status):
    ws = websocket.create_connection('wss://gateway.discord.gg/?v=9&encoding=json')
    start = json.loads(ws.recv())
    heartbeat_interval = start['d']['heartbeat_interval'] / 1000
    
    # Send authentication
    auth = {"op": 2,"d": {"token": token,"properties": {"$os": "Windows 10","$browser": "Google Chrome","$device": "Windows"},"presence": {"status": status,"afk": False}},"s": None,"t": None}
    ws.send(json.dumps(auth))
    
    # Wait for READY event
    while True:
        msg = json.loads(ws.recv())
        if msg['t'] == 'READY':
            break
    
    # Join voice channel
    vc = {"op": 4,"d": {"guild_id": GUILD_ID,"channel_id": CHANNEL_ID,"self_mute": SELF_MUTE,"self_deaf": SELF_DEAF}}
    ws.send(json.dumps(vc))
    
    # Maintain connection with heartbeats
    last_heartbeat = time.time()
    while True:
        try:
            # Check if we need to send heartbeat
            if time.time() - last_heartbeat >= heartbeat_interval:
                ws.send(json.dumps({"op": 1,"d": None}))
                last_heartbeat = time.time()
            
            # Check for incoming messages (non-blocking)
            ws.settimeout(0.1)
            try:
                msg = ws.recv()
                data = json.loads(msg)
                if data['op'] == 11:  # Heartbeat ACK
                    print("Heartbeat acknowledged")
            except:
                pass  # Timeout is expected
                
            time.sleep(0.1)
        except Exception as e:
            print(f"Connection error: {e}")
            break
    
    ws.close()

def run_joiner():
  os.system("clear")
  print(f"Logged in as {username}#{discriminator} ({userid}).")
  print("Connecting to voice channel...")
  joiner(usertoken, status)

keep_alive()
run_joiner()
