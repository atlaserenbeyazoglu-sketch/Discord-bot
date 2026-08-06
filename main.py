import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for
import threading
import json
import os

# --- AYARLAR VE DOSYA YÃ–NETÄ°MÄ° ---
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
        print("KayÄ±t hatasÄ±:", e)

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

# --- WEB PANELÄ° (ROL VE KANAL LÄ°STELÄ°) ---
app = Flask(__name__)

PANEL_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Discord Bot Kontrol Paneli</title>
    <style>
        body { 
            background: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), 
                        url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920&auto=format&fit=crop') no-repeat center center fixed;
            background-size: cover;
            color: #dbdee1; 
            font-family: sans-serif; 
            padding: 20px; 
        }
        .container { 
            max-width: 650px; 
            margin: auto; 
            background: rgba(43, 45, 49, 0.9); 
            backdrop-filter: blur(10px); 
            padding: 25px; 
            border-radius: 12px; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.5); 
        }
        h2, h3 { color: #fff; text-align: center; }
        select, button { width: 100%; padding: 12px; margin: 10px 0; background: #1e1f22; color: #fff; border: 1px solid #383a40; border-radius: 6px; box-sizing: border-box; }
        button { background: #5865f2; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #4752c4; }
        .server-box { background: rgba(17, 18, 20, 0.9); padding: 18px; margin-bottom: 20px; border-radius: 8px; border: 1px solid #2b2d31; }
        label { font-size: 14px; color: #b5bac1; font-weight: bold; display: block; margin-top: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>ğŸ¤– Bot YÃ¶netim Paneli</h2>
        <hr style="border:0; border-top:1px solid #383a40; margin-bottom: 20px;">
        <h3>SunucularÄ±nÄ±z ve Ayarlar</h3>
        
        {% for guild in bot_guilds %}
            <div class="server-box">
                <h3>ğŸ“¢ {{ guild.name }}</h3>
                <form method="POST">
                    <input type="hidden" name="guild_id" value="{{ guild.id }}">
                    
                    <label>Otorol SeÃ§in:</label>
                    <select name="otorol_id">
                        <option value="">-- Rol SeÃ§ilmedi --</option>
                        {% for role in guild.roles %}
                            {% if role.name != "@everyone" %}
                                <option value="{{ role.id }}" {% if settings.get(guild.id, {}).get('otorol_id')|string == role.id|string %}selected{% endif %}>
                                    {{ role.name }}
                                </option>
                            {% endif %}
                        {% endfor %}
                    </select>

                    <label>Log KanalÄ± SeÃ§in:</label>
                    <select name="log_kanal_id">
                        <option value="">-- Kanal SeÃ§ilmedi --</option>
                        {% for channel in guild.text_channels %}
                            <option value="{{ channel.id }}" {% if settings.get(guild.id, {}).get('log_kanal_id')|string == channel.id|string %}selected{% endif %}>
                                #{{ channel.name }}
                            </option>
                        {% endfor %}
                    </select>

                    <button type="submit" name="kaydet" value="1">Kaydet</button>
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
            if gid not in SERVER_SETTINGS:
                SERVER_SETTINGS[gid] = {}
            
            SERVER_SETTINGS[gid]["otorol_id"] = request.form.get("otorol_id")
            SERVER_SETTINGS[gid]["log_kanal_id"] = request.form.get("log_kanal_id")
            verileri_kaydet()
            return redirect(url_for("panel"))

    return render_template_string(PANEL_HTML, bot_guilds=bot.guilds, settings=SERVER_SETTINGS)

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.environ.get("TOKEN"))
    
