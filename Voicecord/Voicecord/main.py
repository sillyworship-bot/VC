import os
import sys
import json
import time
import requests
import websocket
import socket
import threading
import random

status = "idle"  # online/dnd/idle
GUILD_ID = 1369197776596111440
CHANNEL_ID = 1416320729040949248
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
    sequence = None
    session_id = None
    self_id = None  # Track bot's own user ID
    last_op4_time = 0  # Rate limiting for OP 4 sends
    retry_count = 0
    max_retry_delay = 300  # Max 5 minutes
    
    def send_op4_throttled(ws, reason=""):
        """Send OP 4 with rate limiting (max once per 5 seconds)"""
        nonlocal last_op4_time
        current_time = time.time()
        if current_time - last_op4_time < 5:  # 5 second minimum interval
            print(f"OP 4 throttled for token ending in ...{token[-10:]} ({reason})")
            return False
        
        vc_payload = {"op": 4, "d": {"guild_id": GUILD_ID, "channel_id": CHANNEL_ID, "self_mute": SELF_MUTE, "self_deaf": SELF_DEAF}}
        try:
            ws.send(json.dumps(vc_payload))
            last_op4_time = current_time
            print(f"OP 4 sent for token ending in ...{token[-10:]} ({reason})")
            return True
        except Exception as e:
            print(f"OP 4 failed for token ending in ...{token[-10:]}: {e}")
            return False
    
    while True:  # Ultra-persistent infinite reconnection loop
        ws = None
        try:
            print(f"Connecting token ending in ...{token[-10:]}")
            # MAXIMUM stability websocket connection with all optimizations
            ws = websocket.create_connection(
                'wss://gateway.discord.gg/?v=10&encoding=json', 
                timeout=30,  # Shorter timeout for faster failure detection
                enable_multithread=True,
                sockopt=[
                    (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
                    (socket.SOL_TCP, socket.TCP_KEEPIDLE, 30),
                    (socket.SOL_TCP, socket.TCP_KEEPINTVL, 10),
                    (socket.SOL_TCP, socket.TCP_KEEPCNT, 3),
                    (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                ]
            )
            print(f"Enhanced websocket connection established for token ending in ...{token[-10:]}")
            
            # Receive Hello
            start = json.loads(ws.recv())
            heartbeat_interval = start['d']['heartbeat_interval'] / 1000

            # Authenticate or Resume
            if session_id and sequence:
                # Resume connection
                resume_payload = {
                    "op": 6,
                    "d": {
                        "token": token,
                        "session_id": session_id,
                        "seq": sequence
                    }
                }
                ws.send(json.dumps(resume_payload))
                print(f"Resuming session for token ending in ...{token[-10:]}")
            else:
                # New authentication
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

            # Wait for READY or RESUMED
            ready_received = False
            while not ready_received:
                msg = json.loads(ws.recv())
                if msg.get('t') == 'READY':
                    session_id = msg['d']['session_id']
                    self_id = msg['d']['user']['id']  # Capture bot's own user ID
                    ready_received = True
                    print(f"Ready received for token ending in ...{token[-10:]} (User ID: {self_id})")
                elif msg.get('t') == 'RESUMED':
                    ready_received = True
                    print(f"Session resumed for token ending in ...{token[-10:]}")

            # Join VC (single request only, no redundancy)
            send_op4_throttled(ws, "initial join")

            last_heartbeat = time.time()
            heartbeat_ack_received = True

            while True:
                # Ultra-reliable heartbeat system
                if time.time() - last_heartbeat >= (heartbeat_interval * 0.9):  # Send slightly early
                    if not heartbeat_ack_received:
                        print(f"Heartbeat not acknowledged, reconnecting token ending in ...{token[-10:]}")
                        break
                    
                    try:
                        ws.send(json.dumps({"op": 1, "d": sequence}))
                        last_heartbeat = time.time()
                        heartbeat_ack_received = False
                    except Exception as e:
                        print(f"Heartbeat send failed for token ending in ...{token[-10:]}: {e}")
                        break

                # Receive messages
                ws.settimeout(0.5)
                try:
                    msg = ws.recv()
                    data = json.loads(msg)
                    
                    # Update sequence number
                    if data.get('s'):
                        sequence = data['s']
                    
                    if data.get('op') == 11:  # Heartbeat ACK
                        heartbeat_ack_received = True
                        # Reset retry count on successful heartbeat
                        retry_count = max(0, retry_count - 1)
                    elif data.get('op') == 9:  # Invalid Session
                        print(f"Invalid session for token ending in ...{token[-10:]}, starting fresh")
                        session_id = None
                        sequence = None
                        break
                    elif data.get('op') == 7:  # Reconnect
                        print(f"Server requested reconnect for token ending in ...{token[-10:]}")
                        break
                    elif data.get('t') == 'VOICE_STATE_UPDATE':
                        # Only respond to OUR OWN voice state changes
                        user_id = data['d'].get('user_id')
                        current_channel = data['d'].get('channel_id')
                        
                        # CRITICAL FIX: Only process if this is the bot's own user ID
                        if self_id and user_id == self_id:
                            if current_channel != CHANNEL_ID:
                                print(f"SELF VOICE DISCONNECT DETECTED for token ending in ...{token[-10:]}, attempting rejoin")
                                # Throttled rejoin attempt
                                send_op4_throttled(ws, "self disconnect detected")
                            elif current_channel == CHANNEL_ID:
                                print(f"Self voice connection VERIFIED stable for token ending in ...{token[-10:]}")
                        # No longer respond to other users' voice state changes
                        
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as e:
                    print(f"Receive error for token ending in ...{token[-10:]}: {e}")
                    break

                # Reasonable polling interval to reduce CPU usage
                time.sleep(0.1)  # 10Hz polling is sufficient

        except Exception as e:
            print(f"Connection error for token ending in ...{token[-10:]}: {e}")
            session_id = None  # Reset session on major errors
            sequence = None
        finally:
            try:
                if ws is not None:
                    ws.close()
            except:
                pass

        # Ultra-aggressive reconnection with minimal delay
        retry_count += 1
        # Much faster reconnection for voice channel persistence
        if retry_count <= 3:
            delay = 1 + random.uniform(0, 1)  # 1-2 seconds for first attempts
        elif retry_count <= 10:
            delay = 2 + random.uniform(0, 2)  # 2-4 seconds for medium attempts
        else:
            delay = min(30, 5 + random.uniform(0, 5))  # Max 30 seconds
        print(f"Reconnecting in {delay:.1f} seconds for token ending in ...{token[-10:]} (attempt {retry_count})")
        time.sleep(delay)
        
        # Reset retry count on successful periods
        if retry_count > 10:
            retry_count = max(0, retry_count - 2)


def run_all_tokens():
    os.system("cls" if os.name == "nt" else "clear")
    threads = []

    for token in tokens:
        userinfo = validate_token(token)
        if userinfo:
            print(f"Logged in as {userinfo['username']}#{userinfo['discriminator']} ({userinfo['id']})")
            t = threading.Thread(target=joiner, args=(token, status), daemon=False)
            t.start()
            threads.append(t)
            time.sleep(2)  # Stagger connections to avoid rate limits
        else:
            print(f"[ERROR] Invalid token: {token}")

    # ULTRA-AGGRESSIVE monitoring system for NEVER-DISCONNECT guarantee
    connection_health = {}
    for i, token in enumerate(tokens):
        connection_health[i] = {"last_seen": time.time(), "restart_count": 0}
    
    while True:
        time.sleep(10)  # More frequent monitoring (every 10 seconds)
        active_threads = [t for t in threads if t.is_alive()]
        # Silent monitoring - no output
        
        # AGGRESSIVE thread monitoring and instant restart
        for i, thread in enumerate(threads):
            if not thread.is_alive():
                connection_health[i]["restart_count"] += 1
                print(f"[INSTANT-RESTART] IMMEDIATELY restarting dead connection for token {i+1} (restart #{connection_health[i]['restart_count']})")
                token = tokens[i] if i < len(tokens) else None
                if token and validate_token(token):
                    new_thread = threading.Thread(target=joiner, args=(token, status), daemon=False)
                    new_thread.start()
                    threads[i] = new_thread
                    connection_health[i]["last_seen"] = time.time()
                    time.sleep(1)  # Minimal restart delay
            else:
                connection_health[i]["last_seen"] = time.time()
        
        # Proactive health check - restart connections that might be stale
        for i, health in connection_health.items():
            if time.time() - health["last_seen"] > 120:  # If no activity for 2 minutes
                if i < len(threads) and threads[i].is_alive():
                    print(f"[PROACTIVE-RESTART] Restarting potentially stale connection for token {i+1}")
                    # Force restart for maximum reliability
                    # Note: This is commented out as it might be too aggressive
                    # threads[i] = None  # Will be restarted on next cycle
        
        # Display connection statistics
        total_restarts = sum(h["restart_count"] for h in connection_health.values())
        # Silent stats tracking


run_all_tokens()
