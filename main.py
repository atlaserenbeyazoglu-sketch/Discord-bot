import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for
import threading
import json
import os

# --- AYARLAR VE DOSYA YÖNETİMİ ---
DOSYA_YOLU = "ayarlar.json"
SERVER_SETTINGS = {}

def verileri_yukle():
    global SERVER_SETTINGS
    if os.path.exists(DOSYA_YOLU):
        try:
            with open(DOSYA_YOLU, "r", encoding="utf-8") as f:
                data = json.load(f)
                SERVER_SETTINGS = {int(k): v for k, v in data.items()}
        except:
            SERVER_SETTINGS = {}

def verileri_kaydet():
    try:
        with open(DOSYA_YOLU, "w", encoding="utf-8") as f:
            json.dump(SERVER_SETTINGS, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Kayıt hatası:", e)

# --- BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    verileri_yukle()
    for guild in bot.guilds:
        if guild.id not in SERVER_SETTINGS:
            SERVER_SETTINGS[guild.id] = {
                "name": guild.name,
                "otorol_id": "",
                "log_kanal_id": ""
            }
    verileri_kaydet()
    print(f"Bot aktif: {bot.user}")

# --- WEB PANELİ (ARKA PLANLI) ---
app = Flask(__name__)

PANEL_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Discord Bot Kontrol Paneli</title>
    <style>
        body { 
            /* Arka plan görseli ve karartma efekti */
            background: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), 
                        url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920&auto=format&fit=crop') no-repeat center center fixed;
            background-size: cover;
            color: #dbdee1; 
            font-family: sans-serif; 
            padding: 20px; 
        }
        .container { 
            max-width: 600px; 
            margin: auto; 
            background: rgba(43, 45, 49, 0.85); /* Hafif şeffaf panel */
            backdrop-filter: blur(8px); /* Arkayı hafif bulanıklaştırır */
            padding: 25px; 
            border-radius: 12px; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.5); 
        }
        h2, h3 { color: #fff; text-align: center; }
        input, button { width: 100%; padding: 12px; margin: 10px 0; background: #1e1f22; color: #fff; border: 1px solid #383a40; border-radius: 6px; box-sizing: border-box; }
        button { background: #5865f2; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #4752c4; }
        .server-box { background: rgba(17, 18, 20, 0.9); padding: 18px; margin-bottom: 15px; border-radius: 8px; border: 1px solid #2b2d31; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🤖 Bot Yönetim Paneli</h2>
        <hr style="border:0; border-top:1px solid #383a40; margin-bottom: 20px;">
        <h3>Sunucularınız</h3>
        {% for gid, data in settings.items() %}
            <div class="server-box">
                <h3>📢 {{ data.name }}</h3>
                <form method="POST">
                    <input type="hidden" name="guild_id" value="{{ gid }}">
                    <label>Otorol ID:</label>
                    <input type="text" name="otorol_id" value="{{ data.otorol_id or '' }}" placeholder="Rol ID girin">
                    <label>Log Kanal ID:</label>
                    <input type="text" name="log_kanal_id" value="{{ data.log_kanal_id or '' }}" placeholder="Kanal ID girin">
                    <button type="submit" name="kaydet" value="1">Ayarları Kaydet</button>
                </form>
            </div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def panel():
    verileri_yukle()
    if request.method == "POST":
        if "kaydet" in request.form:
            gid = int(request.form.get("guild_id"))
            if gid in SERVER_SETTINGS:
                SERVER_SETTINGS[gid]["otorol_id"] = request.form.get("otorol_id")
                SERVER_SETTINGS[gid]["log_kanal_id"] = request.form.get("log_kanal_id")
                verileri_kaydet()
            return redirect(url_for("panel"))

    return render_template_string(PANEL_HTML, settings=SERVER_SETTINGS)

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.environ.get("TOKEN"))
    
