import discord, json, os, datetime, threading
from discord.ext import commands
from discord import app_commands
from flask import Flask, render_template_string, request

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
        SET.setdefault(g.id, {"name": g.name, "otorol_id": "", "hosgeldin_kanal_id": ""})
        SET[g.id]["name"] = g.name
    kaydet()
    try:
        await bot.tree.sync()
        print("✅ Tüm komutlar başarıyla senkronize edildi!")
    except Exception as e:
        print(f"❌ Sync hatası: {e}")
    print(f"Bot aktif edildi: {bot.user}")
    print("--------------------------------------------------")
    print("🌐 WEB KONTROL PANELİ AKTİF")
    print("--------------------------------------------------")

@bot.event
async def on_message(message):
    if not message.author.bot and message.content.strip().lower() == "sa":
        try:
            await message.channel.send(f"Aleykümselam {message.author.mention}")
        except:
            pass
    await bot.process_commands(message)

# --- YETKİ KONTROL FONKSİYONLARI ---
def yetki_kontrol(interaction, perm):
    return getattr(interaction.user.guild_permissions, perm, False)

async def hata_mesaji(interaction, metin):
    await interaction.response.send_message(f"❌ {metin}", ephemeral=True)

# --- 1. WEB PANEL LİNKİ VE YARDIM/KOMUTLAR ---
@bot.tree.command(name="panel", description="Web kontrol paneli linkini gönderir.")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Web Kontrol Paneli", 
        description="Sunucu ayarlarını yönetmek için web panelini kullanabilirsin.", 
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
            "**/panel** - Web panel linkini atar.\n"
            "**/sil** - Belirtilen miktarda mesajı temizler.\n"
            "**/lock** - Kanalı kitler ve seçilen rolün yazma iznini ayarlar.\n"
            "**/unlock** - Kanalın kilidini açar.\n"
            "**/mute** - Kullanıcıya zaman aşımı (susturma) uygular.\n"
            "**/unmute** - Kullanıcının susturmasını kaldırır.\n"
            "**/yavasmod** - Kanalın yavaş mod süresini ayarlar.\n"
            "**/kanalizin** - Kanalı hangi rollerin görüp göremeyeceğini ayarlar."
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- 2. MESAJ TEMİZLEME ---
@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı temizler.")
@app_commands.describe(limit="Silinecek mesaj sayısı")
async def sil(interaction: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata_mesaji(interaction, "Mesajları yönet yetkiniz bulunmuyor.")
    await interaction.response.defer(ephemeral=True)
    silinenler = await interaction.channel.purge(limit=limit)
    await interaction.followup.send(f"🧹 Başarıyla {len(silinenler)} mesaj silindi.", ephemeral=True)

# --- 3. GELİŞMİŞ LOCK (KİLİTLEME VE ROL YAZMA İZNİ) ---
@bot.tree.command(name="lock", description="Kanalı kilitler ve seçilen rolün yazma iznini belirler.")
@app_commands.describe(
    rol="İzin verilecek veya kısıtlanacak rol", 
    durum="True (Yazabilsin), False (Yazamasın)"
)
async def lock(interaction: discord.Interaction, rol: discord.Role, durum: bool):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalları yönet yetkiniz yok.")
    
    # Herkesin (@everyone) mesaj göndermesini kapat
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    # Belirtilen rolün yazma iznini ayarla
    await interaction.channel.set_permissions(rol, send_messages=durum)
    
    durum_metni = "açıldı" if durum else "kapatıldı"
    await interaction.response.send_message(f"🔒 Kanal kilitlendi. **{rol.name}** rolünün bu kanala yazma izni **{durum_metni}**.")

@bot.tree.command(name="unlock", description="Kanalın kilidini açar ve herkesin yazmasını sağlar.")
async def unlock(interaction: discord.Interaction):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalları yönet yetkiniz yok.")
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("🔓 Kanalın kilidi açıldı, herkes mesaj yazabilir.")

# --- 4. SUSTURMA (MUTE / UNMUTE) VE YAVAŞMOD ---
@bot.tree.command(name="mute", description="Kullanıcıya belirtilen süre kadar zaman aşımı uygular.")
@app_commands.describe(uye="Susturulacak üye", saat="Süre (saat cinsinden)", sebep="Susturma sebebi")
async def mute(interaction: discord.Interaction, uye: discord.Member, saat: int = 1, sebep: str = "Belirtilmedi"):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Üyeleri susturma yetkiniz yok.")
    await uye.timeout(datetime.timedelta(hours=saat), reason=sebep)
    await interaction.response.send_message(f"🔇 {uye.name} adlı kullanıcı {saat} saat süreyle susturuldu. Sebep: {sebep}")

@bot.tree.command(name="unmute", description="Kullanıcının zaman aşımı susturmasını kaldırır.")
@app_commands.describe(uye="Susturması kaldırılacak üye")
async def unmute(interaction: discord.Interaction, uye: discord.Member):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    await uye.timeout(None)
    await interaction.response.send_message(f"🔊 {uye.name} adlı kullanıcının susturması kaldırıldı.")

@bot.tree.command(name="yavasmod", description="Kanal için yavaş mod süresini saniye cinsinden ayarlar.")
@app_commands.describe(saniye="Saniye cinsini girin (0 kapatır)")
async def yavasmod(interaction: discord.Interaction, saniye: int):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalı yönet yetkiniz yok.")
    await interaction.channel.edit(slowmode_delay=saniye)
    await interaction.response.send_message(f"⏳ Yavaş mod {saniye} saniye olarak ayarlandı.")

# --- 5. GELİŞMİŞ KANAL GÖRÜNÜRLÜK AYARI ---
@bot.tree.command(name="kanalizin", description="Kanalı belirli bir rolün görüp görmeyeceğini ayarlar.")
@app_commands.describe(
    rol="İşlem yapılacak rol", 
    goruntuleme="True (Görebilsin), False (Göremesin/Gizlesin)"
)
async def kanalizin(interaction: discord.Interaction, rol: discord.Role, goruntuleme: bool):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalları yönet yetkiniz yok.")
    
    await interaction.channel.set_permissions(rol, view_channel=goruntuleme)
    durum_metni = "görebilecek" f"şekilde açıldı" if goruntuleme else "göremeyecek" f"şekilde gizlendi"
    await interaction.response.send_message(f"👁️ Kanal görünürlüğü güncellendi: **{rol.name}** rolü artık bu kanalı {durum_metni}.")

# --- ÜYE ETKİNLİKLERİ ---
@bot.event
async def on_member_join(member):
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

# --- WEB PANELİ (FLASK) ---
app = Flask(__name__)

INDEX_H = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Panel</title><style>body{background:#2b2d31;color:#fff;font-family:sans-serif;padding:20px;}.box{max-width:500px;margin:auto;background:#313338;padding:20px;border-radius:8px;}.card{background:#111;padding:12px;margin-bottom:10px;border-radius:6px;display:flex;justify-content:space-between;align-items:center;}.btn{background:#5865f2;color:#fff;padding:8px 14px;border-radius:4px;text-decoration:none;font-weight:bold;}</style></head><body><div class="box"><h2>🤖 Sunucu Seç</h2>{% for g in guilds %}<div class="card"><span>📢 {{g.name}}</span><a href="/server/{{g.id}}" class="btn">Yönet</a></div>{% endfor %}</div></body></html>"""

SERVER_H = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Ayarlar</title><style>body{background:#2b2d31;color:#fff;font-family:sans-serif;padding:20px;}.box{max-width:500px;margin:auto;background:#313338;padding:20px;border-radius:8px;}select,button{width:100%;padding:10px;margin:10px 0;background:#1e1f22;color:#fff;border:1px solid #444;border-radius:5px;}button{background:#5865f2;font-weight:bold;cursor:pointer;}.back{display:block;margin-bottom:15px;color:#00aff4;text-decoration:none;}</style></head><body><div class="box"><a href="/" class="back">⬅️ Geri</a><h2>⚙️ {{g.name}}</h2><form method="POST"><label>Otorol:</label><select name="otorol_id"><option value="">-- Seçilmedi --</option>{% for r in g.roles %}{% if r.name != "@everyone" %}<option value="{{r.id}}" {% if set.get('otorol_id')|string == r.id|string %}selected{% endif %}>{{r.name}}</option>{% endif %}{% endfor %}</select><label>Hoş Geldin Kanalı:</label><select name="hosgeldin_kanal_id"><option value="">-- Seçilmedi --</option>{% for c in g.text_channels %}<option value="{{c.id}}" {% if set.get('hosgeldin_kanal_id')|string == c.id|string %}selected{% endif %}>#{{c.name}}</option>{% endfor %}</select><button type="submit">Kaydet</button></form></div></body></html>"""

@app.route("/")
def index():
    yukle()
    return render_template_string(INDEX_H, guilds=bot.guilds)

@app.route("/server/<int:gid>", methods=["GET", "POST"])
def server(gid):
    yukle()
    g = bot.get_guild(gid)
    if not g:
        return "Bulunamadı", 404
    SET.setdefault(gid, {"name": g.name, "otorol_id": "", "hosgeldin_kanal_id": ""})
    if request.method == "POST":
        SET[gid]["otorol_id"] = request.form.get("otorol_id")
        SET[gid]["hosgeldin_kanal_id"] = request.form.get("hosgeldin_kanal_id")
        kaydet()
    return render_template_string(SERVER_H, g=g, set=SET[gid])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    
    discord_token = os.environ.get("TOKEN")
    bot.run(discord_token)
    
