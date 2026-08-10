import discord, json, os, datetime, threading
from discord.ext import commands
from discord import app_commands
from flask import Flask, render_template_string, request, redirect, url_for

DOSYA = "ayarlar.json"
SET = {}

def yukle():
    global SET
    if os.path.exists(DOSYA):
        try:
            with open(DOSYA, "r", encoding="utf-8") as f:
                SET = {int(k): v for k, v in json.load(f).items()}
        except:
            pass

def kaydet():
    try:
        with open(DOSYA, "w", encoding="utf-8") as f:
            json.dump(SET, f, ensure_ascii=False, indent=4)
    except:
        pass

yukle()
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    yukle()
    for g in bot.guilds:
        SET.setdefault(g.id, {
            "name": g.name, 
            "otorol_id": "", 
            "hosgeldin_kanal_id": "", 
            "log_kanal_id": ""
        })
        SET[g.id]["name"] = g.name
    kaydet()
    try:
        await bot.tree.sync()
        print("✅ Tüm komutlar başarıyla senkronize edildi!")
    except Exception as e:
        print(f"❌ Sync hatası: {e}")
    print(f"Bot aktif edildi: {bot.user}")
    print("--------------------------------------------------")
    print("🌐 WEB PANELİ VE PORT SİSTEMİ AKTİF")
    print("--------------------------------------------------")

@bot.event
async def on_message(message):
    if not message.author.bot and message.content.strip().lower() == "sa":
        try:
            await message.channel.send(f"Aleykümselam {message.author.mention}")
        except:
            pass
    await bot.process_commands(message)

def yetki_kontrol(interaction, perm):
    return getattr(interaction.user.guild_permissions, perm, False)

async def hata_mesaji(interaction, metin):
    await interaction.response.send_message(f"❌ {metin}", ephemeral=True)

# --- KOMUTLAR ---
@bot.tree.command(name="panel", description="Web kontrol paneli linkini gönderir.")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Gelişmiş Bot Kontrol Paneli", 
        description="Sunucu ayarlarını yönetmek için panel: https://discord-bot-fa6e.onrender.com/", 
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="komutlar", description="Aktif bot komutlarını gösterir.")
async def komutlar(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Bot Komut Listesi",
        description="Mevcut komutlar:",
        color=0x5865F2
    )
    embed.add_field(
        name="🛠️ Yönetim",
        value="**/komutlar**\n**/panel**\n**/sunucu-kur**\n**/sil**\n**/kanalayazmaerişimi**\n**/mute**\n**/unmute**\n**/yavaşmod**\n**/kanalgörünülürlük**",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles:
        return
    guild = after.guild
    yukle()
    s = SET.get(guild.id, {})
    log_kanal_id = s.get("log_kanal_id")
    if not log_kanal_id:
        return
    log_kanali = guild.get_channel(int(log_kanal_id))
    if not log_kanali:
        return
    islem_yapan = "Bilinmiyor"
    try:
        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                islem_yapan = entry.user.mention
                break
    except:
        pass
    for rol in [r for r in after.roles if r not in before.roles]:
        embed = discord.Embed(title="✅ Rol Verildi", color=0x57F287)
        embed.add_field(name="Kullanıcı", value=after.mention)
        embed.add_field(name="Rol", value=rol.mention)
        embed.add_field(name="Veren", value=islem_yapan)
        try: await log_kanali.send(embed=embed)
        except: pass

@bot.tree.command(name="sunucu-kur", description="Kanalları kurar.")
@app_commands.describe(sifre="Şifre")
async def sunucu_kur(interaction: discord.Interaction, sifre: str):
    if sifre != "2904":
        return await hata_mesaji(interaction, "Hatalı şifre!")
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Yetkiniz yok!")
    await interaction.response.defer()
    guild = interaction.guild
    try:
        kat1 = await guild.create_category("「📌」Önemli")
        for isim in ["「❓」biz-kimiz", "「🚪」gelen-giden"]:
            await guild.create_text_channel(isim, category=kat1)
        await interaction.followup.send("✅ Kurulum tamamlandı.")
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}")

@bot.tree.command(name="sil", description="Mesaj siler.")
@app_commands.describe(limit="Sayı")
async def sil(interaction: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    await interaction.response.defer(ephemeral=True)
    silinenler = await interaction.channel.purge(limit=limit)
    await interaction.followup.send(f"🧹 {len(silinenler)} mesaj silindi.", ephemeral=True)

# --- FLASK WEB PANELİ ---
app = Flask(__name__)

LOGIN_H = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Güvenli Giriş</title><style>body{background:#1e1f22;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}.box{background:#2b2d31;padding:40px;border-radius:12px;width:320px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,0.5);}input,button{width:100%;padding:12px;margin:12px 0;background:#1e1f22;color:#fff;border:1px solid #444;border-radius:6px;box-sizing:border-box;font-size:16px;}button{background:#5865f2;font-weight:bold;cursor:pointer;}button:hover{background:#4752c4;}.err{color:#ed4245;font-size:14px;margin-bottom:10px;}</style></head><body><div class="box"><h2>🛡️ Güvenli Panel</h2>{% if error %}<p class="err">{{error}}</p>{% endif %}<form method="POST"><input type="password" name="password" placeholder="Şifrenizi Girin" required><button type="submit">Sisteme Bağlan</button></form></div></body></html>"""
INDEX_H = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Ultra Panel</title><style>body{background:#1e1f22;color:#fff;font-family:sans-serif;padding:30px;}.box{max-width:600px;margin:auto;background:#2b2d31;padding:30px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.5);}.card{background:#111;padding:15px;margin-bottom:12px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;}.btn{background:#5865f2;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:bold;}.logout{color:#ed4245;text-decoration:none;float:right;font-size:14px;font-weight:bold;}</style></head><body><div class="box"><a href="/logout" class="logout">Oturumu Kapat</a><h2>🤖 Sunucu Seçimi</h2><hr style="border:0;border-top:1px solid #444;margin:15px 0;">{% for g in guilds %}<div class="card"><span>📢 {{g.name}}</span><a href="/server/{{g.id}}" class="btn">Yönet</a></div>{% endfor %}</div></body></html>"""
SERVER_H = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Sunucu Ayarları</title><style>body{background:#1e1f22;color:#fff;font-family:sans-serif;padding:30px;}.box{max-width:600px;margin:auto;background:#2b2d31;padding:30px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.5);}select,button{width:100%;padding:12px;margin:12px 0;background:#1e1f22;color:#fff;border:1px solid #444;border-radius:6px;font-size:16px;}button{background:#57F287;color:#111;font-weight:bold;cursor:pointer;}.back{display:inline-block;margin-bottom:15px;color:#00aff4;text-decoration:none;font-weight:bold;}.logout{color:#ed4245;text-decoration:none;float:right;font-size:14px;font-weight:bold;}.alert{background:#57F287;color:#111;padding:10px;border-radius:6px;text-align:center;font-weight:bold;margin-bottom:15px;}</style></head><body><div class="box"><a href="/logout" class="logout">Oturumu Kapat</a><a href="/" class="back">⬅️ Geri Dön</a><h2>⚙️ {{g.name}} Yönetim</h2><hr style="border:0;border-top:1px solid #444;margin:15px 0;">{% if saved %}<div class="alert">✅ Kaydedildi!</div>{% endif %}<form method="POST"><label>Otorol ID:</label><input type="text" name="otorol_id" value="{{set.get('otorol_id','')}}" style="width:100%;padding:10px;background:#1e1f22;color:#fff;border:1px solid #444;border-radius:6px;margin-bottom:12px;"><label>Hoş Geldin Kanal ID:</label><input type="text" name="hosgeldin_kanal_id" value="{{set.get('hosgeldin_kanal_id','')}}" style="width:100%;padding:10px;background:#1e1f22;color:#fff;border:1px solid #444;border-radius:6px;margin-bottom:12px;"><label>Log Kanal ID:</label><input type="text" name="log_kanal_id" value="{{set.get('log_kanal_id','')}}" style="width:100%;padding:10px;background:#1e1f22;color:#fff;border:1px solid #444;border-radius:6px;margin-bottom:12px;"><button type="submit">Kaydet</button></form></div></body></html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == "2904":
            res = redirect(url_for("index"))
            res.set_cookie("auth", "ok", max_age=86400)
            return res
        error = "Hatalı şifre!"
    return render_template_string(LOGIN_H, error=error)

@app.route("/logout")
def logout():
    res = redirect(url_for("login"))
    res.set_cookie("auth", "", expires=0)
    return res

@app.route("/")
def index():
    if request.cookies.get("auth") != "ok":
        return redirect(url_for("login"))
    yukle()
    return render_template_string(INDEX_H, guilds=bot.guilds)

@app.route("/server/<int:gid>", methods=["GET", "POST"])
def server(gid):
    if request.cookies.get("auth") != "ok":
        return redirect(url_for("login"))
    yukle()
    g = bot.get_guild(gid)
    if not g:
        return "Bulunamadı", 404
    SET.setdefault(gid, {"name": g.name, "otorol_id": "", "hosgeldin_kanal_id": "", "log_kanal_id": ""})
    saved = False
    if request.method == "POST":
        SET[gid]["name"] = g.name
        SET[gid]["otorol_id"] = request.form.get("otorol_id", "")
        SET[gid]["hosgeldin_kanal_id"] = request.form.get("hosgeldin_kanal_id", "")
        SET[gid]["log_kanal_id"] = request.form.get("log_kanal_id", "")
        kaydet()
        saved = True
    return render_template_string(SERVER_H, g=g, set=SET[gid], saved=saved)

if __name__ == "__main__":
    discord_token = os.environ.get("TOKEN")
    if not discord_token:
        print("❌ TOKEN bulunamadı!")
        exit(1)

    # Botu arka planda başlatıyoruz ki portu engellemesin
    threading.Thread(target=lambda: bot.run(discord_token), daemon=True).start()
    
    # Flask ana akışta çalışarak Render'ın portu anında bulmasını sağlıyor
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
