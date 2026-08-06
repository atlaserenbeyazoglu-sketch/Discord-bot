import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for, session
import threading

# --- 1. DİSCORD BOTU AYARLARI ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Her sunucunun otorol ID'sini tutacağız
SERVER_SETTINGS = {}

@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.id not in SERVER_SETTINGS:
            SERVER_SETTINGS[guild.id] = {
                "name": guild.name,
                "otorol_id": None
            }
    print(f"Bot aktif: {bot.user}")

@bot.event
async def on_guild_join(guild):
    if guild.id not in SERVER_SETTINGS:
        SERVER_SETTINGS[guild.id] = {
            "name": guild.name,
            "otorol_id": None
        }

@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    settings = SERVER_SETTINGS.get(guild_id)
    if not settings or not settings["otorol_id"]:
        return
    
    rol_id = settings["otorol_id"]
    rol = member.guild.get_role(rol_id)
    if rol:
        try:
            await member.add_roles(rol)
        except:
            pass

# --- 2. FLASK WEB PANELİ ---
app = Flask(__name__)
app.secret_key = "cok_gizli_bir_anahtar_belirle"

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Panel Giriş</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #313338; color: #dbdee1; text-align: center; padding-top: 100px; }
        .login-box { background-color: #2b2d31; padding: 30px; display: inline-block; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        input, button { padding: 10px; margin: 10px; border-radius: 5px; border: none; font-size: 16px; }
        input { background-color: #1e1f22; color: white; width: 200px; }
        button { background-color: #5865f2; color: white; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #4752c4; }
        .hata { color: #f23f43; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 Bot Paneli Giriş</h2>
        {% if hata %}
            <p class="hata">{{ hata }}</p>
        {% endif %}
        <form method="POST">
            <input type="password" name="sifre" placeholder="Yönetici Şifresi" required><br>
            <button type="submit">Giriş Yap</button>
        </form>
        <p style="font-size: 12px; color: #949ba4; margin-top: 15px;">Varsayılan Şifre: <b>admin123</b></p>
    </div>
</body>
</html>
"""

SERVER_LIST_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunucu Seçimi</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #313338; color: #dbdee1; padding: 20px; text-align: center; }
        .container { max-width: 500px; margin: 0 auto; }
        .card { background-color: #2b2d31; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        h1 { color: #5865f2; font-size: 22px; }
        .server-btn { display: block; background-color: #5865f2; color: white; padding: 12px; margin: 10px 0; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .server-btn:hover { background-color: #4752c4; }
        .logout { background-color: #f23f43; display: inline-block; padding: 8px 15px; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🤖 Botunun Bulunduğu Sunucular</h1>
            <p style="font-size: 13px; color: #949ba4;">Yönetmek istediğin sunucuyu seç:</p>
            
            {% for g_id, data in servers.items() %}
                <a href="/panel/{{ g_id }}" class="server-btn">⚙️ {{ data.name }} Yönet</a>
            {% endfor %}
        </div>
        <a href="/cikis" class="logout">Güvenli Çıkış Yap</a>
    </div>
</body>
</html>
"""

SERVER_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ server_name }} - Otorol Ayarları</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #313338; color: #dbdee1; padding: 20px; margin: 0; }
        .container { max-width: 500px; margin: 0 auto; }
        .card { background-color: #2b2d31; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        h1, h3 { color: #5865f2; margin-top: 0; }
        select, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 5px; border: none; font-size: 14px; box-sizing: border-box; }
        select { background-color: #1e1f22; color: white; }
        button { background-color: #23a55a; color: white; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #1d8a48; }
        .back-btn { background-color: #4e5058; display: inline-block; padding: 8px 15px; color: white; text-decoration: none; border-radius: 5px; margin-bottom: 15px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/panel" class="back-btn">⬅️ Sunucu Seçimine Dön</a>
        
        <div class="card">
            <h1>⚙️ {{ server_name }}</h1>
            <p style="color: #23a55a; font-weight: bold;">● Otomatik Rol (Otorol) Yönetimi</p>
        </div>

        <div class="card">
            <h3>🛡️ Sunucu Rollerinden Seç</h3>
            <form method="POST" action="/panel/{{ guild_id }}/guncelle-otorol">
                <label style="font-size: 13px; color: #b5bac1;">Şu anki Rol: <b>{{ current_role_name }}</b></label>
                <select name="rol_id">
                    <option value="">-- Rol Seçin (Devre Dışı Bırak) --</option>
                    {% for role in roles %}
                        <option value="{{ role.id }}" {% if role.id == settings.otorol_id %}selected{% endif %}>{{ role.name }}</option>
                    {% endfor %}
                </select>
                <button type="submit">Seçilen Rolü Kaydet</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def login():
    hata = None
    if request.method == "POST":
        if request.form.get("sifre") == "admin123":
            session["giris_yapildi"] = True
            return redirect(url_for("server_list"))
        else:
            hata = "Hatalı şifre!"
    return render_template_string(LOGIN_HTML, hata=hata)

@app.route("/panel")
def server_list():
    if not session.get("giris_yapildi"):
        return redirect(url_for("login"))
    for guild in bot.guilds:
        if guild.id not in SERVER_SETTINGS:
            SERVER_SETTINGS[guild.id] = {
                "name": guild.name,
                "otorol_id": None
            }
    return render_template_string(SERVER_LIST_HTML, servers=SERVER_SETTINGS)

@app.route("/panel/<int:guild_id>")
def server_dashboard(guild_id):
    if not session.get("giris_yapildi"):
        return redirect(url_for("login"))
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return "Sunucu bulunamadı!", 404
        
    settings = SERVER_SETTINGS.get(guild_id, {"name": guild.name, "otorol_id": None})
    
    roles = [r for r in guild.roles if r.name != "@everyone"]
    
    current_role_name = "Ayarlanmamış"
    if settings["otorol_id"]:
        r_obj = guild.get_role(settings["otorol_id"])
        if r_obj:
            current_role_name = r_obj.name

    return render_template_string(
        SERVER_DASHBOARD_HTML, 
        guild_id=guild_id, 
        server_name=guild.name, 
        settings=settings, 
        roles=roles, 
        current_role_name=current_role_name
    )

@app.route("/panel/<int:guild_id>/guncelle-otorol", methods=["POST"])
def guncelle_otorol(guild_id):
    if not session.get("giris_yapildi"):
        return redirect(url_for("login"))
        
    rol_id_str = request.form.get("rol_id")
    if guild_id in SERVER_SETTINGS and rol_id_str:
        SERVER_SETTINGS[guild_id]["otorol_id"] = int(rol_id_str)
    elif guild_id in SERVER_SETTINGS:
        SERVER_SETTINGS[guild_id]["otorol_id"] = None
        
    return redirect(url_for("server_dashboard", guild_id=guild_id))

@app.route("/cikis")
def cikis():
    session.pop("giris_yapildi", None)
    return redirect(url_for("login"))

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    bot.run("MTUzNDkzMDc0NzQ3NDA1MTI3NQ.GMBi67.1gGQDV4oojcyKGY_kDGPrjOE01OzgafkLb6t1w")
