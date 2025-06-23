import asyncio
import json
import random
import websockets
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# معلومات السيرفر والرومات
GUILD_ID = "1226151418793169008"
CHANNEL_IDS = [
    "1385378291271336058",
    "1385378295113060546",
    "1386010541570523298",
    "1385378309491261554"
]

# إبقاء البوت شغال داخل استضافة bot-hosting
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot Alive!')

def keep_alive():
    server = HTTPServer(('0.0.0.0', 8080), PingHandler)
    server.serve_forever()

threading.Thread(target=keep_alive).start()

# تحميل التوكنات من الملف
with open("tokens.txt", "r") as f:
    TOKENS = [line.strip() for line in f if line.strip()]

# تغيير الحالة الصوتية أو تفعيل البث
async def voice_behavior(ws, token, channel_id, stream=False):
    if stream:
        voice_state = {
            "op": 4,
            "d": {
                "guild_id": GUILD_ID,
                "channel_id": channel_id,
                "self_mute": False,
                "self_deaf": False,
                "self_video": False,
                "self_stream": True
            }
        }
        await ws.send(json.dumps(voice_state))
        await asyncio.sleep(2)

        stream_event = {
            "op": 18,
            "d": {
                "type": "guild",
                "guild_id": GUILD_ID,
                "channel_id": channel_id,
                "preferred_region": "europe"
            }
        }
        await ws.send(json.dumps(stream_event))
        print(f"[✓] {token[:15]}... بث وهمي مفعّل في {channel_id}")
    else:
        while True:
            mode = random.choice(["mute", "deaf", "none"])
            voice_state = {
                "op": 4,
                "d": {
                    "guild_id": GUILD_ID,
                    "channel_id": channel_id,
                    "self_mute": mode == "mute",
                    "self_deaf": mode == "deaf"
                }
            }
            await ws.send(json.dumps(voice_state))
            print(f"[~] {token[:15]}... الحالة: {mode}")
            await asyncio.sleep(300)  # كل 5 دقائق

# إرسال heartbeat كل عدة ثواني
async def send_heartbeat(ws, token, interval):
    try:
        while True:
            await ws.send(json.dumps({"op": 1, "d": None}))
            await asyncio.sleep(interval)
    except Exception as e:
        print(f"[!] خطأ في heartbeat: {token[:15]} | {e}")

# الاتصال بـ Discord Gateway
async def connect(token, index):
    channel_id = CHANNEL_IDS[index % len(CHANNEL_IDS)]
    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                hello = await ws.recv()
                hello = json.loads(hello)
                hb_interval = hello["d"]["heartbeat_interval"] / 1000

                identify = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "os": "Windows",
                            "browser": "Chrome",
                            "device": "Desktop"
                        },
                        "presence": {
                            "status": "online",
                            "since": 0,
                            "activities": [],
                            "afk": False
                        }
                    }
                }

                await ws.send(json.dumps(identify))
                asyncio.create_task(send_heartbeat(ws, token, hb_interval))

                voice_ready = False

                while True:
                    message = await ws.recv()
                    data = json.loads(message)

                    if data.get("t") == "READY" and not voice_ready:
                        voice_ready = True
                        asyncio.create_task(
                            voice_behavior(ws, token, channel_id, stream=(index < 2))
                        )

        except Exception as e:
            print(f"[X] فقد الاتصال بـ {token[:15]}... إعادة بعد 5 ثواني | {e}")
            await asyncio.sleep(5)

# تشغيل جميع التوكنات مع تأخير بسيط
async def main():
    tasks = []
    for i, token in enumerate(TOKENS):
        await asyncio.sleep(1.5)  # تأخير لتخفيف الضغط
        tasks.append(connect(token, i))
    await asyncio.gather(*tasks)

# تشغيل البوت
asyncio.run(main())
