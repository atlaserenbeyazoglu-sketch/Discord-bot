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

# --- WEB PANELİ (ÇOKLU SAYFA / SUNUCU SEÇMELİ) ---
app = Flask(__name__)

# 1. ANA SAYFA (Sunucu Listesi)
INDEX_HTML = """
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
            color: #dbdee1; font-family: sans-serif; padding: 20px; 
        }
        .container { max-width: 650px; margin: auto; background: rgba(43, 45, 49, 0.9); backdrop-filter: blur(10px); padding: 25px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        h2, h3 { color: #fff; text-align: center; }
        .server-card { display: flex; justify-content: space-between; align-items: center; background: rgba(17, 18, 20, 0.9); padding: 15px; margin-bottom: 12px; border-radius: 8px; border: 1px solid #2b2d31; transition: 0.2s; }
        .server-card:hover { border-color: #5865f2; }
        .server-name { font-weight: bold; color: #fff; font-size: 16px; }
        .btn { background: #5865f2; color: #fff; padding: 10px 18px; border: none; border-radius: 6px; font-weight: bold; text-decoration: none; cursor: pointer; transition: 0.2s; }
        .btn:hover { background: #4752c4; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🤖 Bot Yönetim Paneli</h2>
        <hr style="border:0; border-top:1px solid #383a40; margin-bottom: 20px;">
        <h3>Yönetmek İstediğiniz Sunucuyu Seçin</h3>
        
        {% for guild in bot_guilds %}
            <div class="server-card">
                <span class="server-name">📢 {{ guild.name }}</span>
                <a href="/server/{{ guild.id }}" class="btn">Yönet</a>
            </div>
        {% endfor %}
    </div>
</body>
</html>
"""

# 2. SUNUCU DETAY SAYFASI (Seçilen Sunucunun Ayarları)
SERVER_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>{{ guild.name }} - Ayarlar</title>
    <style>
        body { 
            background: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), 
                        url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920&auto=format&fit=crop') no-repeat center center fixed;
            background-size: cover;
            color: #dbdee1; font-family: sans-serif; padding: 20px; 
        }
        .container { max-width: 650px; margin: auto; background: rgba(43, 45, 49, 0.9); backdrop-filter: blur(10px); padding: 25px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        h2, h3 { color: #fff; text-align: center; }
        select, button { width: 100%; padding: 12px; margin: 10px 0; background: #1e1f22; color: #fff; border: 1px solid #383a40; border-radius: 6px; box-sizing: border-box; }
        button { background: #5865f2; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #4752c4; }
        .back-btn { background: #4e5058; margin-bottom: 15px; display: inline-block; text-align: center; text-decoration: none; color: white; padding: 10px; border-radius: 6px; width: 100%; font-weight: bold; }
        .back-btn:hover { background: #6d6f78; }
        label { font-size: 14px; color: #b5bac1; font-weight: bold; display: block; margin-top: 10px; }
        .success-msg { background: #248046; color: white; padding: 10px; border-radius: 6px; text-align: center; margin-bottom: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">⬅️ Sunucu Seçimine Dön</a>
        <h2>⚙️ {{ guild.name }} Ayarları</h2>
        <hr style="border:0; border-top:1px solid #383a40; margin-bottom: 20px;">
        
        {% if saved %}
            <div class="success-msg">✅ Ayarlar başarıyla kaydedildi!</div>
        {% endif %}

        <form method="POST">
            <label>Otorol Seçin:</label>
            <select name="otorol_id">
                <option value="">-- Rol Seçilmedi --</option>
                {% for role in guild.roles %}
                    {% if role.name != "@everyone" %}
                        <option value="{{ role.id }}" {% if current_settings.get('otorol_id')|string == role.id|string %}selected{% endif %}>
                            {{ role.name }}
                        </option>
                    {% endif %}
                {% endfor %}
            </select>

            <label>Log Kanalı Seçin:</label>
            <select name="log_kanal_id">
                <option value="">-- Kanal Seçilmedi --</option>
                {% for channel in guild.text_channels %}
                    <option value="{{ channel.id }}" {% if current_settings.get('log_kanal_id')|string == channel.id|string %}selected{% endif %}>
                        #{{ channel.name }}
                    </option>
                {% endfor %}
            </select>

            <button type="submit">Ayarları Kaydet</button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML, bot_guilds=bot.guilds)

@app.route("/server/<int:guild_id>", methods=["GET", "POST"])
def server_settings(guild_id):
    verileri_yukle()
    guild = bot.get_guild(guild_id)
    if not guild:
        return "Sunucu bulunamadı!", 404

    if guild_id not in SERVER_SETTINGS:
        SERVER_SETTINGS[guild_id] = {"name": guild.name, "otorol_id": "", "log_kanal_id": ""}

    saved = False
    if request.method == "POST":
        SERVER_SETTINGS[guild_id]["otorol_id"] = request.form.get("otorol_id")
        SERVER_SETTINGS[guild_id]["log_kanal_id"] = request.form.get("log_kanal_id")
        verileri_kaydet()
        saved = True

    return render_template_string(SERVER_HTML, guild=guild, current_settings=SERVER_SETTINGS[guild_id], saved=saved)

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.environ.get("TOKEN"))
    
