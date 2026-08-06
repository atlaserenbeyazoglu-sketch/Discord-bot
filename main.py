import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for
import threading
import json
import os

# --- VERİ YÖNETİMİ ---
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
            pass

def verileri_kaydet():
    try:
        with open(DOSYA_YOLU, "w", encoding="utf-8") as f:
            json.dump(SERVER_SETTINGS, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Kayıt hatası:", e)

verileri_yukle()

# --- BOT AYARLARI ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    verileri_yukle()
    for guild in bot.guilds:
        if guild.id not in SERVER_SETTINGS:
            SERVER_SETTINGS[guild.id] = {
                "name": guild.name,
                "otorol_id": "",
                "hosgeldin_kanal_id": ""
            }
        else:
            SERVER_SETTINGS[guild.id]["name"] = guild.name
            SERVER_SETTINGS[guild.id].setdefault("otorol_id", "")
            SERVER_SETTINGS[guild.id].setdefault("hosgeldin_kanal_id", "")
    verileri_kaydet()
    print(f"Kesintisiz bot aktif: {bot.user}")

# --- MESAJ VE ETKİNLİK YÖNETİCİSİ ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # "sa" / "SA" kontrolü
    if message.content.strip().lower() == "sa":
        try:
            await message.channel.send(f"Aleyküm selam {message.author.mention}")
        except:
            pass

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    settings = SERVER_SETTINGS.get(guild_id, {})
    
    # Otorol
    rol_id = settings.get("otorol_id")
    if rol_id:
        rol = member.guild.get_role(int(rol_id))
        if rol:
            try:
                await member.add_roles(rol)
            except:
                pass

    # Hoş Geldin Mesajı
    HC_kanal_id = settings.get("hosgeldin_kanal_id")
    if HC_kanal_id:
        kanal = member.guild.get_channel(int(HC_kanal_id))
        if kanal:
            uye_sayisi = str(member.guild.member_count)
            mesaj = f"Hoşgeldin {member.mention} seninle birlikte {uye_sayisi} kişi olduk"
            try:
                await kanal.send(mesaj)
            except:
                pass

@bot.event
async def on_member_remove(member):
    guild_id = member.guild.id
    settings = SERVER_SETTINGS.get(guild_id, {})
    
    HC_kanal_id = settings.get("hosgeldin_kanal_id")
    if HC_kanal_id:
        kanal = member.guild.get_channel(int(HC_kanal_id))
        if kanal:
            mesaj = f"{member.name} ayrıldı..."
            try:
                await kanal.send(mesaj)
            except:
                pass


# --- WEB PANELİ (FLASK) ---
app = Flask(__name__)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Bot Kontrol Paneli</title>
    <style>
        body { background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920&auto=format&fit=crop') no-repeat center center fixed; background-size: cover; color: #dbdee1; font-family: sans-serif; padding: 20px; }
        .container { max-width: 650px; margin: auto; background: rgba(43, 45, 49, 0.9); backdrop-filter: blur(10px); padding: 25px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        h2, h3 { color: #fff; text-align: center; }
        .server-card { display: flex; justify-content: space-between; align-items: center; background: rgba(17, 18, 20, 0.9); padding: 15px; margin-bottom: 12px; border-radius: 8px; border: 1px solid #2b2d31; transition: 0.2s; }
        .server-card:hover { border-color: #5865f2; }
        .btn { background: #5865f2; color: #fff; padding: 10px 18px; border: none; border-radius: 6px; font-weight: bold; text-decoration: none; cursor: pointer; }
        .btn:hover { background: #4752c4; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🤖 Bot Paneli</h2>
        <hr style="border:0; border-top:1px solid #383a40; margin-bottom: 20px;">
        <h3>Yönetmek İstediğiniz Sunucuyu Seçin</h3>
        {% for guild in bot_guilds %}
            <div class="server-card">
                <span style="font-weight: bold; font-size: 16px;">📢 {{ guild.name }}</span>
                <a href="/server/{{ guild.id }}" class="btn">Yönet</a>
            </div>
        {% endfor %}
    </div>
</body>
</html>
"""

SERVER_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>{{ guild.name }} - Ayarlar</title>
    <style>
        body { background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920&auto=format&fit=crop') no-repeat center center fixed; background-size: cover; color: #dbdee1; font-family: sans-serif; padding: 20px; }
        .container { max-width: 650px; margin: auto; background: rgba(43, 45, 49, 0.9); backdrop-filter: blur(10px); padding: 25px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        h2, h3 { color: #fff; text-align: center; }
        select, button { width: 100%; padding: 12px; margin: 8px 0 15px 0; background: #1e1f22; color: #fff; border: 1px solid #383a40; border-radius: 6px; box-sizing: border-box; }
        button { background: #5865f2; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #4752c4; }
        .back-btn { background: #4e5058; margin-bottom: 15px; display: inline-block; text-align: center; text-decoration: none; color: white; padding: 10px; border-radius: 6px; width: 100%; font-weight: bold; }
        label { font-size: 14px; color: #b5bac1; font-weight: bold; display: block; }
        .success-msg { background: #248046; color: white; padding: 10px; border-radius: 6px; text-align: center; margin-bottom: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">⬅️ Sunucu Listesine Dön</a>
        <h2>⚙️ {{ guild.name }} Yönetim Paneli</h2>
        <hr style="border:0; border-top:1px solid #383a40; margin-bottom: 20px;">
        
        {% if saved %}
            <div class="success-msg">✅ Ayarlar kalıcı olarak kaydedildi!</div>
        {% endif %}

        <form method="POST">
            <label>Otorol (Otomatik Rol):</label>
            <select name="otorol_id">
                <option value="">-- Rol Seçilmedi --</option>
                {% for role in guild.roles %}
                    {% if role.name != "@everyone" %}
                        <option value="{{ role.id }}" {% if current_settings.get('otorol_id')|string == role.id|string %}selected{% endif %}>{{ role.name }}</option>
                    {% endif %}
                {% endfor %}
            </select>

            <label>Hoş Geldin & Ayrılış Kanalı:</label>
            <select name="hosgeldin_kanal_id">
                <option value="">-- Kanal Seçilmedi --</option>
                {% for channel in guild.text_channels %}
                    <option value="{{ channel.id }}" {% if current_settings.get('hosgeldin_kanal_id')|string == channel.id|string %}selected{% endif %}>#{{ channel.name }}</option>
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
    verileri_yukle()
    return render_template_string(INDEX_HTML, bot_guilds=bot.guilds)

@app.route("/server/<int:guild_id>", methods=["GET", "POST"])
def server_settings(guild_id):
    verileri_yukle()
    guild = bot.get_guild(guild_id)
    if not guild:
        return "Sunucuyu bulamadım!", 404

    if guild_id not in SERVER_SETTINGS:
        SERVER_SETTINGS[guild_id] = {
            "name": guild.name,
            "otorol_id": "",
            "hosgeldin_kanal_id": ""
        }

    saved = False
    if request.method == "POST":
        SERVER_SETTINGS[guild_id]["name"] = guild.name
        SERVER_SETTINGS[guild_id]["otorol_id"] = request.form.get("otorol_id")
        SERVER_SETTINGS[guild_id]["hosgeldin_kanal_id"] = request.form.get("hosgeldin_kanal_id")
        
        verileri_kaydet()
        saved = True

    return render_template_string(SERVER_HTML, guild=guild, current_settings=SERVER_SETTINGS[guild_id], saved=saved)

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.environ.get("TOKEN"))
