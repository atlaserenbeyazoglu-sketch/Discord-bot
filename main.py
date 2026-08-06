import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for, session
import threading
import json
import os

# --- AYARLAR ---
DOSYA_YOLU = "ayarlar.json"
SERVER_SETTINGS = {}

def verileri_yukle():
    global SERVER_SETTINGS
    if os.path.exists(DOSYA_YOLU):
        with open(DOSYA_YOLU, "r", encoding="utf-8") as f:
            data = json.load(f)
            SERVER_SETTINGS = {int(k): v for k, v in data.items()}

def verileri_kaydet():
    with open(DOSYA_YOLU, "w", encoding="utf-8") as f:
        json.dump(SERVER_SETTINGS, f, ensure_ascii=False, indent=4)

# --- BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    verileri_yukle()
    print("Bot hazır!")

# --- WEB PANELİ (FLASK) ---
app = Flask(__name__)
app.secret_key = "cok_gizli_anahtar"

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Giriş</title>
    <style>body { background: #313338; color: white; text-align: center; padding-top: 50px; font-family: sans-serif; }</style>
</head>
<body>
    <h2>Bot Paneli Giriş</h2>
    <form method="POST">
        <input type="password" name="sifre" placeholder="Şifre (admin123)" required>
        <button type="submit">Giriş Yap</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("sifre") == "admin123":
            session["giris"] = True
            return "Giriş başarılı! Bot ayarlarını yakında buraya ekleyeceğiz."
    return render_template_string(LOGIN_HTML)

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    # Flask'i başlat
    threading.Thread(target=run_flask, daemon=True).start()
    # Botu başlat
    bot.run(os.environ.get("TOKEN"))
    
