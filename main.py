import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for, session
import threading
import json
import os

# --- VERİLERİ GÜVENLİ DOSYADA SAKLAMA ---
DOSYA_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ayarlar.json")

def verileri_yukle():
    if os.path.exists(DOSYA_YOLU):
        try:
            with open(DOSYA_YOLU, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except:
            return {}
    return {}

def verileri_kaydet():
    try:
        with open(DOSYA_YOLU, "w", encoding="utf-8") as f:
            json.dump(SERVER_SETTINGS, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Kayıt hatası:", e)

# --- 1. DİSCORD BOTU AYARLARI ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Ayarları dosyadan yüklüyoruz
SERVER_SETTINGS = verileri_yukle()

@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.id not in SERVER_SETTINGS:
            SERVER_SETTINGS[guild.id] = {
                "name": guild.name,
                "otorol_id": None,
                "log_kanal_id": None
            }
    verileri_kaydet()
    print(f"Bot aktif: {bot.user}")

@bot.event
async def on_guild_join(guild):
    if guild.id not in SERVER_SETTINGS:
        SERVER_SETTINGS[guild.id] = {
            "name": guild.name,
            "otorol_id": None,
            "log_kanal_id": None
        }
        verileri_kaydet()

@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    settings = SERVER_SETTINGS.get(guild_id)
    if not settings or not settings.get("otorol_id"):
        return
    
    rol_id = settings["otorol_id"]
    rol = member.guild.get_role(rol_id)
    if rol:
        try:
            await member.add_roles(rol)
        except:
            pass


# --- DETAYLI ROL LOG SİSTEMİ ---
@bot.event
async def on_member_update(before, after):
    guild_id = after.guild.id
    settings = SERVER_SETTINGS.get(guild_id)
    if not settings or not settings.get("log_kanal_id"):
        return
        
    log_id = settings["log_kanal_id"]
    kanal = after.guild.get_channel(log_id)
    if not kanal:
        return

    eklenen_roller = [r for r in after.roles if r not in before.roles]
    kaldirilan_roller = [r for r in before.roles if r not in after.roles]

    if not eklenen_roller and not kaldirilan_roller:
        return

    yetkili = "Bilinmiyor"
    try:
        async for entry in after.guild.audit_logs(limit=3, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                yetkili = entry.user.mention
                break
    except:
        pass

    avatar_url = after.avatar.url if after.avatar else after.default_avatar.url

    for rol in eklenen_roller:
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(name=f"{after.name} ({after.display_name})", icon_url=avatar_url)
        embed.description = f"🟢 **{after.mention}** adlı kullanıcıya bir rol eklendi.\n\n" \
                            f"📌 **Eklenen Rol:** {rol.mention}\n" \
                            f"🛠️ **İşlemi Yapan:** {yetkili}"
        await kanal.send(embed=embed)

    for rol in kaldirilan_roller:
        embed = discord.Embed(color=discord.Color.red())
        embed.set_author(name=f"{after.name} ({after.display_name})", icon_url=avatar_url)
        embed.description = f"🔴 **{after.mention}** adlı kullanıcından bir rol kaldırıldı.\n\n" \
                            f"📌 **Kaldırılan Rol:** {rol.mention}\n" \
                            f"🛠️ **İşlemi Yapan:** {yetkili}"
        await kanal.send(embed=embed)


# --- DİSCORD MODERASYON KOMUTLARI (BAN & UNBAN) ---

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 **{member.mention}** başarıyla sunucudan yasaklandı. Sebep: {reason or 'Belirtilmedi'}")
    except Exception as e:
        await ctx.send(f"Kullanıcı yasaklanamadı! Yetkim yetmiyor olabilir.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ **{user.name}** adlı kullanıcının yasağı kaldırıldı.")
    except Exception as e:
        await ctx.send(f"Kullanıcının yasağı kaldırılamadı. ID'yi yanlış girmiş olabilirsin.")

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için `Üyeleri Yasakla` yetkisine sahip olmalısın.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Eksik kullanım! Örnek: `!ban @kullanici sebep`")

@unban.error
async def unban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için `Üyeleri Yasakla` yetkisine sahip olmalısın.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Eksik kullanım! Örnek: `!unban 123456789012345678`")


# --- 2. FLASK WEB PANELİ (HTML & CSS) ---
app = Flask(__name__)
app.secret_key = "cok_gizli_bir_anahtar_belirle"

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Panel Giriş</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #313338; color: #dbdee1; text-align: center; padding-top: 100px; margin: 0; }
        .login-box { background-color: #2b2d31; padding: 40px; display: inline-block; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.4); width: 320px; }
        h2 { color: #ffffff; margin-bottom: 20px; }
        input, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: none; font-size: 15px; box-sizing: border-box; outline: none; }
        input { background-color: #1e1f22; color: white; border: 1px solid #383a40; }
        input:focus { border-color: #5865f2; }
        button { background-color: #5865f2; color: white; cursor: pointer; font-weight: bold; transition: background 0.2s; }
        button:hover { background-color: #4752c4; }
        .hata { color: #f23f43; font-size: 14px; margin-bottom: 10px; }
        .info { font-size: 12px; color: #949ba4; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 Bot Paneli Giriş</h2>
        {% if hata %}
            <p class="hata">{{ hata }}</p>
        {% endif %}
        <form method="POST">
            <input type="password" name="sifre" placeholder="Yönetici Şifresi" required>
            <button type="submit">Giriş Yap</button>
        </form>
        <p class="info">Varsayılan Şifre: <b>admin123</b></p>
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
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #313338; color: #dbdee1; padding: 30px; margin: 0; text-align: center; }
        .container { max-width: 600px; margin: 0 auto; }
        .card { background-color: #2b2d31; border-radius: 12px; padding: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.4); }
        h1 { color: #ffffff; font-size: 24px; margin-bottom: 10px; }
        p { color: #949ba4; font-size: 14px; margin-bottom: 25px; }
        .server-btn { display: block; background-color: #2b2d31; border: 1px solid #3f4147; color: white; padding: 15px; margin: 12px 0; text-decoration: none; border-radius: 8px; font-weight: bold; text-align: left; transition: all 0.2s; display: flex; justify-content: space-between; align-items: center; }
        .server-btn:hover { background-color: #35373c; border-color: #5865f2; }
        .logout { background-color: #f23f43; display: inline-block; padding: 10px 20px; color: white; text-decoration: none; border-radius: 6px; margin-top: 25px; font-size: 14px; font-weight: bold; transition: background 0.2s; }
        .logout:hover { background-color: #d83c3f; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🤖 Botun Bulunduğu Sunucular</h1>
            <p>Yönetmek istediğin sunucuyu seç:</p>
            
            {% for g_id, data in servers.items() %}
                <a href="/panel/{{ g_id }}" class="server-btn">
                    <span>⚙️ {{ data.name }}</span>
                    <span style="color: #5865f2; font-size: 13px;">Yönet &rarr;</span>
                </a>
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
    <title>{{ server_name }} - Kontrol Paneli</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #313338; color: #dbdee1; padding: 30px; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; }
        .card { background-color: #2b2d31; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.4); }
        h1, h3 { color: #ffffff; margin-top: 0; }
        select, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: none; font-size: 14px; box-sizing: border-box; outline: none; }
        select { background-color: #1e1f22; color: white; border: 1px solid #383a40; }
        button { background-color: #23a55a; color: white; cursor: pointer; font-weight: bold; transition: background 0.2s; }
        button:hover { background-color: #1d8a48; }
        .back-btn { background-color: #4e5058; display: inline-block; padding: 8px 16px; color: white; text-decoration: none; border-radius: 6px; margin-bottom: 20px; font-size: 14px; font-weight: bold; transition: background 0.2s; }
        .back-btn:hover { background-color: #6d6f78; }
        .badge { background-color: #23a55a; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/panel" class="back-btn">&larr; Sunucu Seçimine Dön</a>
        
        <div class="card">
            <h1>⚙️ {{ server_name }}</h1>
            <p style="color: #949ba4; font-size: 13px; margin: 0;">Durum: <span class="badge">Aktif</span></p>
        </div>

        <!-- OTOROL AYARI -->
        <div class="card">
            <h3>🛡️ Otomatik Rol (Otorol) Ayarı</h3>
            <p style="font-size: 13px; color: #949ba4;">Sunucuya yeni katılan kullanıcılara otomatik verilecek rol:</p>
            
            <form method="POST" action="/panel/{{ guild_id }}/guncelle-otorol">
                <label style="font-size: 13px; color: #b5bac1; display: block; margin-bottom: 5px;">Mevcut Rol: <b>{{ current_role_name }}</b></label>
                <select name="rol_id">
                    <option value="">-- Rol Seçin (Devre Dışı) --</option>
                    {% for role in roles %}
                        <option value="{{ role.id }}" {% if role.id == settings.otorol_id %}selected{% endif %}>{{ role.name }}</option>
                    {% endfor %}
                </select>
                <button type="submit">Otorolü Kaydet</button>
            </form>
        </div>

        <!-- ROL LOG KANALI AYARI -->
        <div class="card">
            <h3>📜 Rol Log Kanalı Ayarı</h3>
            <p style="font-size: 13px; color: #949ba4;">Rol verilip alındığında bilgilendirme mesajının atılacağı kanal:</p>
            
            <form method="POST" action="/panel/{{ guild_id }}/guncelle-logkanal">
                <label style="font-size: 13px; color: #b5bac1; display: block; margin-bottom: 5px;">Mevcut Kanal: <b>{{ current_channel_name }}</b></label>
                <select name="kanal_id">
                    <option value="">-- Kanal Seçin (Devre Dışı) --</option>
                    {% for channel in channels %}
                        <option value="{{ channel.id }}" {% if channel.id == settings.log_kanal_id %}selected{% endif %}># {{ channel.name }}</option>
                    {% endfor %}
                </select>
                <button type="submit" style="background-color: #5865f2;">Log Kanalını Kaydet</button>
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
                "otorol_id": None,
                "log_kanal_id": None
            }
    verileri_kaydet()
    return render_template_string(SERVER_LIST_HTML, servers=SERVER_SETTINGS)

@app.route("/panel/<int:guild_id>")
def server_dashboard(guild_id):
    if not session.get("giris_yapildi"):
        return redirect(url_for("login"))
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return "Sunucu bulunamadı!", 404
        
    settings = SERVER_SETTINGS.get(guild_id, {"name": guild.name, "otorol_id": None, "log_kanal_id": None})
    roles = [r for r in guild.roles if r.name != "@everyone"]
    channels = guild.text_channels
    
    current_role_name = "Ayarlanmamış"
    if settings["otorol_id"]:
        r_obj = guild.get_role(settings["otorol_id"])
        if r_obj:
            current_role_name = r_obj.name

    current_channel_name = "Ayarlanmamış"
    if settings["log_kanal_id"]:
        c_obj = guild.get_channel(settings["log_kanal_id"])
        if c_obj:
            current_channel_name = f"#{c_obj.name}"

    return render_template_string(
        SERVER_DASHBOARD_HTML, 
        guild_id=guild_id, 
        server_name=guild.name, 
        settings=settings, 
        roles=roles, 
        channels=channels,
        current_role_name=current_role_name,
        current_channel_name=current_channel_name
    )

@app.route("/panel/<int:guild_id>/guncelle-otorol", methods=["POST"])
def guncelle_otorol(guild_id):
    if not session.get("giris_yapildi"):
        return redirect(url_for("login"))
        
    rol_id_str = request.form.get("rol_id")
    if guild_id in SERVER_SETTINGS:
        SERVER_SETTINGS[guild_id]["otorol_id"] = int(rol_id_str) if rol_id_str else None
        verileri_kaydet()
        
    return redirect(url_for("server_dashboard", guild_id=guild_id))

@app.route("/panel/<int:guild_id>/guncelle-logkanal", methods=["POST"])
def guncelle_logkanal(guild_id):
    if not session.get("giris_yapildi"):
        return redirect(url_for("login"))
        
    kanal_id_str = request.form.get("kanal_id")
    if guild_id in SERVER_SETTINGS:
        SERVER_SETTINGS[guild_id]["log_kanal_id"] = int(kanal_id_str) if kanal_id_str else None
        verileri_kaydet()
        
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

    bot.run("MTUzNDkzMDc0NzQ3NDA1MTI3NQ.GwgI9A.UqOIBJg3dJ0rjp9CI9Sp8RkZGjr4fwSWnkHuo0")
                              
