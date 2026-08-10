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
    print("🌐 GELİŞMİŞ BOT KONTROL PANELİ AKTİF (FENDER SİSTEMİ)")
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

@bot.tree.command(name="panel", description="Web kontrol paneli linkini gönderir.")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Gelişmiş Bot Kontrol Paneli", 
        description="Sunucu ayarlarını yönetmek için panel: https://discord-bot-fa6e.onrender.com/", 
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="komutlar", description="Sunucudaki aktif bot komutlarını gösterir.")
async def komutlar(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Bot Komut Listesi",
        description="Aşağıdan mevcut tüm komutları inceleyebilirsin:",
        color=0x5865F2
    )
    embed.add_field(
        name="🛠️ Yönetim ve Moderasyon",
        value=(
            "**/komutlar** - Komut listesini gösterir.\n"
            "**/panel** - Web panel linkini ve güncel yönetim detaylarını atar.\n"
            "**/sunucu-kur** - Tüm kategorileri ve kanalları tek seferde kurar (Şifre ister).\n"
            "**/sil** - Belirtilen miktarda mesajı temizler.\n"
            "**/kanalayazmaerişimi** - Birden fazla rolün kanala yazma iznini tek seferde ayarlar.\n"
            "**/mute** - Kullanıcıya zaman aşımı uygular.\n"
            "**/unmute** - Kullanıcının susturmasını kaldırır.\n"
            "**/yavaşmod** - Kanalın yavaş mod süresini ayarlar.\n"
            "**/kanalgörünülürlük** - Seçilen rollerin kanalı görüp görmeyeceğini ayarlar."
        ),
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

    islem_yapan = "Bilinmiyor / Otomatik"
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                islem_yapan = entry.user.mention
                break
    except:
        pass

    eklenen_roller = [r for r in after.roles if r not in before.roles]
    alinan_roller = [r for r in before.roles if r not in after.roles]

    for rol in eklenen_roller:
        embed = discord.Embed(title="✅ Rol Verildi", color=0x57F287, timestamp=datetime.datetime.now())
        embed.add_field(name="Rol Verilen Kullanıcı", value=after.mention, inline=False)
        embed.add_field(name="Verilen Rol", value=rol.mention, inline=False)
        embed.add_field(name="Rolü Veren", value=islem_yapan, inline=False)
        try:
            await log_kanali.send(embed=embed)
        except:
            pass

    for rol in alinan_roller:
        embed = discord.Embed(title="⚠️ Rol Alındı", color=0xED4245, timestamp=datetime.datetime.now())
        embed.add_field(name="Rolü Alınan Kullanıcı", value=after.mention, inline=False)
        embed.add_field(name="Alınan Rol", value=rol.name, inline=False)
        embed.add_field(name="Rolü Alan", value=islem_yapan, inline=False)
        try:
            await log_kanali.send(embed=embed)
        except:
            pass

@bot.tree.command(name="sunucu-kur", description="Tüm kategorileri ve kanalları tek seferde kurar.")
@app_commands.describe(sifre="Kurulum için gereken güvenlik şifresi")
async def sunucu_kur(interaction: discord.Interaction, sifre: str):
    if sifre != "2904":
        return await hata_mesaji(interaction, "Hatalı şifre! Sunucu kurulumu gerçekleştirilemedi.")
        
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanal yönetme yetkiniz yok!")
    
    await interaction.response.defer()
    guild = interaction.guild
    
    try:
        kat1 = await guild.create_category("「📌」Önemli")
        for isim in ["「❓」biz-kimiz", "「❓」görevlerimiz", "「⬛」kara-liste", "「🚪」gelen-giden", "「👔」kılık-kıyafet"]:
            await guild.create_text_channel(isim, category=kat1)
        
        kat2 = await guild.create_category("「📢」Duyuru")
        for isim in ["「📢」personel-duyuru", "「📢」aktiflik-duyuru", "「📢」operasyon-duyuru", "「📜」kararname", "「📋」hiyerarşi"]:
            await guild.create_text_channel(isim, category=kat2)

        kat3 = await guild.create_category("「🗨」Sohbet Kanalları")
        for isim in ["「🗨」sohbet", "「📸」galeri-kanalı", "「🤖」bot-komut", "「🤔」öneri-istek", "「📤」i̇stifa-i̇zin", "「😴」inaktiflik-izin"]:
            await guild.create_text_channel(isim, category=kat3)
            
        kat4 = await guild.create_category("「🧾」Kayıtlar")
        for isim in ["「🧾」alım-logs", "「🧾」alım-sistemi", "「🧾」eğitim-logs", "「🧾」eğitim-sistemi"]:
            await guild.create_text_channel(isim, category=kat4)
            
        await interaction.followup.send("✅ **Sistem başarıyla kuruldu!** Tüm kategoriler ve kanallar eksiksiz oluşturuldu.")
    except Exception as e:
        await interaction.followup.send(f"❌ Kurulum sırasında hata oluştu: {e}")

@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı temizler.")
@app_commands.describe(limit="Silinecek mesaj sayısı")
async def sil(interaction: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata_mesaji(interaction, "Mesajları yönet yetkiniz bulunmuyor.")
    await interaction.response.defer(ephemeral=True)
    silinenler = await interaction.channel.purge(limit=limit)
    await interaction.followup.send(f"🧹 Başarıyla {len(silinenler)} mesaj silindi.", ephemeral=True)

@bot.tree.command(name="kanalayazmaerişimi", description="Birden fazla rolün kanala yazma iznini tek seferde ayarlar.")
@app_commands.describe(
    durum="True (Yazabilsin), False (Yazamasın)",
    rol1="1. Rol", rol2="2. Rol", rol3="3. Rol", rol4="4. Rol", rol5="5. Rol",
    rol6="6. Rol", rol7="7. Rol", rol8="8. Rol", rol9="9. Rol", rol10="10. Rol"
)
async def kanalayazmaerişimi(
    interaction: discord.Interaction, 
    durum: bool,
    rol1: discord.Role = None, 
    rol2: discord.Role = None, 
    rol3: discord.Role = None, 
    rol4: discord.Role = None,
    rol5: discord.Role = None,
    rol6: discord.Role = None,
    rol7: discord.Role = None,
    rol8: discord.Role = None,
    rol9: discord.Role = None,
    rol10: discord.Role = None
):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalları yönet yetkiniz yok.")
    
    roller = [r for r in [rol1, rol2, rol3, rol4, rol5, rol6, rol7, rol8, rol9, rol10] if r is not None]
    if not roller:
        return await hata_mesaji(interaction, "En az bir rol seçmelisiniz.")

    rol_isimleri = []
    for r in roller:
        await interaction.channel.set_permissions(r, send_messages=durum)
        rol_isimleri.append(r.name)
        
    durum_metni = "açıldı ✍️" if durum else "kapatıldı 🚫"
    liste_str = ", ".join([f"**{name}**" for name in rol_isimleri])
    await interaction.response.send_message(f"⚙️ İşlem tamamlandı. {liste_str} rollerinin bu kanala mesaj yazma izni **{durum_metni}**.")

@bot.tree.command(name="mute", description="Kullanıcıya belirtilen süre kadar zaman aşımı uygular.")
@app_commands.describe(üye="Susturulacak üye", saat="Süre (saat cinsinden)", sebep="Susturma sebebi")
async def mute(interaction: discord.Interaction, üye: discord.Member, saat: int = 1, sebep: str = "Belirtilmedi"):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Üyeleri susturma yetkiniz yok.")
    await üye.timeout(datetime.timedelta(hours=saat), reason=sebep)
    await interaction.response.send_message(f"🔇 **{üye.name}** adlı kullanıcı başarıyla **{saat} saat** süreyle susturuldu.\n📝 Sebep: `{sebep}`")

@bot.tree.command(name="unmute", description="Kullanıcının zaman aşımı susturmasını kaldırır.")
@app_commands.describe(üye="Susturması kaldırılacak üye")
async def unmute(interaction: discord.Interaction, üye: discord.Member):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    await üye.timeout(None)
    await interaction.response.send_message(f"🔊 **{üye.name}** adlı kullanıcının susturması başarıyla kaldırıldı.")

@bot.tree.command(name="yavaşmod", description="Kanal için yavaş mod süresini saniye cinsinden ayarlar.")
@app_commands.describe(saniye="Saniye cinsini girin (0 kapatır)")
async def yavaşmod(interaction: discord.Interaction, saniye: int):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalı yönet yetkiniz yok.")
    await interaction.channel.edit(slowmode_delay=saniye)
    if saniye == 0:
        await interaction.response.send_message("⏳ Yavaş mod bu kanal için tamamen kapatıldı.")
    else:
        await interaction.response.send_message(f"⏳ Bu kanal için yavaş mod başarıyla **{saniye} saniye** olarak ayarlandı.")

@bot.tree.command(name="kanalgörünülürlük", description="Seçilen birden fazla rolün kanalı görüp görmeyeceğini ayarlar.")
@app_commands.describe(
    rol1="1. Rol", rol2="2. Rol (İsteğe bağlı)", 
    rol3="3. Rol (İsteğe bağlı)", rol4="4. Rol (İsteğe bağlı)", 
    görünürlük="True (Görebilsin), False (Gizlesin)"
)
async def kanalgörünülürlük(
    interaction: discord.Interaction, 
    rol1: discord.Role, 
    görünürlük: bool,
    rol2: discord.Role = None, 
    rol3: discord.Role = None, 
    rol4: discord.Role = None
):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalları yönet yetkiniz yok.")
    roller = [r for r in [rol1, rol2, rol3, rol4] if r is not None]
    islem_metni = "görebilecek" if görünürlük else "gizlenecek"
    rol_isimleri = []
    for r in roller:
        await interaction.channel.set_permissions(r, view_channel=görünürlük)
        rol_isimleri.append(r.name)
    liste_str = ", ".join([f"**{name}**" for name in rol_isimleri])
    await interaction.response.send_message(f"👁️ Kanal görünürlük ayarları güncellendi: {liste_str} rolleri için kanal artık {islem_metni}.")

@bot.event
async def on_member_join(member):
    yukle()
    s = SET.get(member.guild.id, {})
    if s.get("otorol_id"):
        rol = member.guild.get_role(int(s["otorol_id"]))
        if rol:
            try:
                await member.add_roles(rol)
            except:
                pass
    if s.get("hosgeldin_kanal_id"):
        kanal = member.guild.get_channel(int(s["hosgeldin_kanal_id"]))
        if kanal:
            try:
                await kanal.send(f"Hoş geldin {member.mention}! Seninle birlikte **{member.guild.member_count}** kişi olduk.")
            except:
                pass

app = Flask(__name__)

LOGIN_H = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Güvenli Giriş</title><style>body{background:#1e1f22;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}.box{background:#2b2d31;padding:40px;border-radius:12px;width:320px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,0.5);}input,button{width:100%;padding:12px;margin:12px 0;background:#1e1f22;color:#fff;border:1px solid #444;border-radius:6px;box-sizing:border-box;font-size:16px;}button{background:#5865f2;font-weight:bold;cursor:pointer;transition:background 0.2s;}button:hover{background:#4752c4;}.err{color:#ed4245;font-size:14px;margin-bottom:10px;}</style></head><body><div class="box"><h2>🛡️ Güvenli Panel</h2>{% if error %}<p class="err">{{error}}</p>{% endif %}<form method="POST"><input type="password" name="password" placeholder="Şifrenizi Girin" required><button type="submit">Sisteme Bağlan</button></form></div></body></html>"""
INDEX_H = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Ultra Panel</title><style>body{background:#1e1f22;color:#fff;font-family:sans-serif;padding:30px;}.box{max-width:600px;margin:auto;background:#2b2d31;padding:30px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.5);}.card{background:#111;padding:15px;margin-bottom:12px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;}.btn{background:#5865f2;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:bold;}.sync-btn{background:#57F287;color:#111;display:block;text-align:center;margin-bottom:15px;padding:12px;border-radius:6px;text-decoration:none;font-weight:bold;}.logout{color:#ed4245;text-decoration:none;float:right;font-size:14px;font-weight:bold;}.token-box{margin-top:25px;background:#111;padding:15px;border-radius:8px;font-size:13px;word-break:break-all;color:#b9bbbe;text-align:center;}</style></head><body><div class="box"><a href="/logout" class="logout">Oturumu Kapat</a><h2>🤖 Sunucu Seçimi</h2><hr style="border:0;border-top:1px solid #444;margin:15px 0;"><a href="/sync" class="sync-btn">🔄 Komutları Webden Senkronize Et</a>{% for g in guilds %}<div class="card"><span>📢 {{g.name}}</span><a href="/server/{{g.id}}" class="btn">Yönet</a></div>{% endfor %}<div class="token-box">🔑 <b>Aktif Token:</b> {{token_masked}}</div></div></body></html>"""
SERVER_H = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Sunucu Ayarları</title><style>body{background:#1e1f22;color:#fff;font-family:sans-serif;padding:30px;}.box{max-width:600px;margin:auto;background:#2b2d31;padding:30px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.5);}select,button{width:100%;padding:12px;margin:12px 0;background:#1e1f22;color:#fff;border:1px solid #444;border-radius:6px;font-size:16px;}button{background:#57F287;color:#111;font-weight:bold;cursor:pointer;transition:background 0.2s;}button:hover{background:#45b66c;}.back{display:inline-block;margin-bottom:15px;color:#00aff4;text-decoration:none;font-weight:bold;}.logout{color:#ed4245;text-decoration:none;float:right;font-size:14px;font-weight:bold;}.alert{background:#57F287;color:#111;padding:10px;border-radius:6px;text-align:center;font-weight:bold;margin-bottom:15px;}.token-box{margin-top:25px;background:#111;padding:15px;border-radius:8px;font-size:13px;word-break:break-all;color:#b9bbbe;text-align:center;}</style></head><body><div class="box"><a href="/logout" class="logout">Oturumu Kapat</a><a href="/" class="back">⬅️ Geri Dön</a><h2>⚙️ {{g.name}} Yönetim</h2><hr style="border:0;border-top:1px solid #444;margin:15px 0;">{% if saved %}<div class="alert">✅ Ayarlar kalıcı olarak kaydedildi!</div>{% endif %}<form method="POST"><label>Otorol:</label><select name="otorol_id"><option value="">-- Seçilmedi --</option>{% for r in g.roles %}{% if r.name != "@everyone" %}<option value="{{r.id}}" {% if set.get('otorol_id')|string == r.id|string %}selected{% endif %}>{{r.name}}</option>{% endif %}{% endfor %}</select><label>Hoş Geldin Kanalı:</label><select name="hosgeldin_kanal_id"><option value="">-- Seçilmedi --</option>{% for c in g.text_channels %}<option value="{{c.id}}" {% if set.get('hosgeldin_kanal_id')|string == c.id|string %}selected{% endif %}>#{{c.name}}</option>{% endfor %}</select><label>Rol Log Kanalı:</label><select name="log_kanal_id"><option value="">-- Seçilmedi --</option>{% for c in g.text_channels %}<option value="{{c.id}}" {% if set.get('log_kanal_id')|string == c.id|string %}selected{% endif %}>#{{c.name}}</option>{% endfor %}</select><button type="submit">Değişiklikleri Kalıcı Kaydet</button></form><div class="token-box">🔑 <b>Aktif Token:</b> {{token_masked}}</div></div></body></html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == "2904":
            response = redirect(url_for("index"))
            response.set_cookie("secure_auth", "ultra_secure_token_2904_active", max_age=60*60*24*365)
            return response
        else:
            error = "Hatalı Güvenlik Şifresi!"
    return render_template_string(LOGIN_H, error=error)

@app.route("/logout")
def logout():
    response = redirect(url_for("login"))
    response.set_cookie("secure_auth", "", expires=0)
    return response

@app.route("/")
def index():
    if request.cookies.get("secure_auth") != "ultra_secure_token_2904_active":
        return redirect(url_for("login"))
    yukle()
    raw_token = os.environ.get("TOKEN", "")
    token_masked = raw_token[:6] + "************************" if len(raw_token) > 6 else "Gizli / Bulunamadı"
    return render_template_string(INDEX_H, guilds=bot.guilds, token_masked=token_masked)

@app.route("/sync")
def web_sync():
    if request.cookies.get("secure_auth") != "ultra_secure_token_2904_active":
        return redirect(url_for("login"))
    import asyncio
    asyncio.run_coroutine_threadsafe(bot.tree.sync(), bot.loop)
    return redirect(url_for("index"))

@app.route("/server/<int:gid>", methods=["GET", "POST"])
def server(gid):
    if request.cookies.get("secure_auth") != "ultra_secure_token_2904_active":
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
    raw_token = os.environ.get("TOKEN", "")
    token_masked = raw_token[:6] + "************************" if len(raw_token) > 6 else "Gizli / Bulunamadı"
    return render_template_string(SERVER_H, g=g, set=SET[gid], saved=saved, token_masked=token_masked)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=
