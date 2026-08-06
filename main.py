import discord
from discord.ext import commands
from flask import Flask, render_template_string, request
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
                SERVER_SETTINGS = {int(k): v for k, v in json.load(f).items()}
        except: pass

def verileri_kaydet():
    with open(DOSYA_YOLU, "w", encoding="utf-8") as f:
        json.dump(SERVER_SETTINGS, f, ensure_ascii=False, indent=4)

# --- BOT AYARLARI ---
intents = discord.Intents.default()
intents.message_content = True  # MESAJLARI OKUMAK İÇİN ZORUNLU
intents.members = True          # ÜYE GİRİŞ/ÇIKIŞ İÇİN ZORUNLU
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user}")

# --- MESAJ SİSTEMİ ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    if message.content.strip().lower() == "sa":
        await message.channel.send(f"Aleyküm selam {message.author.mention}")
    
    await bot.process_commands(message)

# --- GİRİŞ / ÇIKIŞ SİSTEMİ ---
@bot.event
async def on_member_join(member):
    settings = SERVER_SETTINGS.get(member.guild.id, {})
    rol_id = settings.get("otorol_id")
    if rol_id:
        rol = member.guild.get_role(int(rol_id))
        if rol: await member.add_roles(rol)
    
    kanal_id = settings.get("hosgeldin_kanal_id")
    if kanal_id:
        kanal = member.guild.get_channel(int(kanal_id))
        if kanal:
            await kanal.send(f"Hoşgeldin {member.mention} seninle birlikte {member.guild.member_count} kişi olduk")

@bot.event
async def on_member_remove(member):
    settings = SERVER_SETTINGS.get(member.guild.id, {})
    kanal_id = settings.get("hosgeldin_kanal_id")
    if kanal_id:
        kanal = member.guild.get_channel(int(kanal_id))
        if kanal: await kanal.send(f"{member.name} ayrıldı...")

# --- WEB PANELİ (FLASK) ---
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        guild_id = int(request.form.get("guild_id"))
        SERVER_SETTINGS[guild_id] = {
            "otorol_id": request.form.get("otorol_id"),
            "hosgeldin_kanal_id": request.form.get("hosgeldin_kanal_id")
        }
        verileri_kaydet()
    return render_template_string(HTML_TEMPLATE, guilds=bot.guilds, settings=SERVER_SETTINGS)

HTML_TEMPLATE = """
<form method="POST">
    <select name="guild_id">{% for g in guilds %}<option value="{{g.id}}">{{g.name}}</option>{% endfor %}</select>
    <input name="otorol_id" placeholder="Otorol ID">
    <input name="hosgeldin_kanal_id" placeholder="Kanal ID">
    <button type="submit">Kaydet</button>
</form>
"""

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    verileri_yukle()
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.environ.get("TOKEN"))
    
