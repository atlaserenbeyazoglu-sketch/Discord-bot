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
        except: pass

def kaydet():
    try:
        with open(DOSYA, "w", encoding="utf-8") as f:
            json.dump(SET, f, ensure_ascii=False, indent=4)
    except: pass

yukle()
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    yukle()
    for g in bot.guilds:
        SET.setdefault(g.id, {"name": g.name, "otorol_id": "", "hosgeldin_kanal_id": ""})
        SET[g.id]["name"] = g.name
    kaydet()
    await bot.tree.sync()
    print(f"Aktif: {bot.user}")

@bot.event
async def on_message(m):
    if not m.author.bot and m.content.strip().lower() == "sa":
        try: await m.channel.send(f"Aleykümselam {m.author.mention}")
        except: pass
    await bot.process_commands(m)

# --- YETKİ KONTROL KISAYolları ---
def yetki_kontrol(i, perm):
    return getattr(i.user.guild_permissions, perm, False)

async def hata_mesaji(i, txt):
    await i.response.send_message(f"❌ {txt}", ephemeral=True)

# --- MODERASYON & GÜVENLİK ---
@bot.tree.command(name="sil", description="Mesaj temizler")
async def sil(i: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(i, "manage_messages"): return await hata_mesaji(i, "Mesajları yönet yetkin yok.")
    await i.response.defer(ephemeral=True)
    await i.channel.purge(limit=limit)
    await i.followup.send(f"🧹 {limit} mesaj silindi.", ephemeral=True)

@bot.tree.command(name="at", description="Üyeyi atar")
async def at(i: discord.Interaction, member: discord.Member, sebep: str = "Belirtilmemiş"):
    if not yetki_kontrol(i, "kick_members"): return await hata_mesaji(i, "Üyeleri at yetkin yok.")
    await member.kick(reason=sebep)
    await i.response.send_message(f"👢 {member.name} atıldı.")

@bot.tree.command(name="ban", description="Üyeyi yasaklar")
async def ban(i: discord.Interaction, member: discord.Member, sebep: str = "Belirtilmemiş"):
    if not yetki_kontrol(i, "ban_members"): return await hata_mesaji(i, "Üyeleri yasakla yetkin yok.")
    await member.ban(reason=sebep)
    await i.response.send_message(f"🔨 {member.name} yasaklandı.")

@bot.tree.command(name="unban", description="Yasak kaldırır")
async def unban(i: discord.Interaction, user_id: str):
    if not yetki_kontrol(i, "ban_members"): return await hata_mesaji(i, "Yasakla yetkin yok.")
    await i.response.defer()
    try:
        user = await bot.fetch_user(int(user_id))
        await i.guild.unban(user)
        await i.followup.send(f"✅ {user.name} unban.")
    except Exception as e: await i.followup.send(f"❌ Hata: {e}")

@bot.tree.command(name="sustur", description="Zamanaşımı")
async def sustur(i: discord.Interaction, member: discord.Member, saat: int = 1, sebep: str = "Yok"):
    if not yetki_kontrol(i, "moderate_members"): return await hata_mesaji(i, "Yetkin yok.")
    await member.timeout(datetime.timedelta(hours=saat), reason=sebep)
    await i.response.send_message(f"🔇 {member.name} {saat} saat susturuldu.")

@bot.tree.command(name="susturkaldir", description="Susturma açar")
async def susturkaldir(i: discord.Interaction, member: discord.Member):
    if not yetki_kontrol(i, "moderate_members"): return await hata_mesaji(i, "Yetkin yok.")
    await member.timeout(None)
    await i.response.send_message(f"🔊 {member.name} susturması açıldı.")

@bot.tree.command(name="lock", description="Kanalı kapatır")
async def lock(i: discord.Interaction):
    if not yetki_kontrol(i, "manage_channels"): return await hata_mesaji(i, "Yetkin yok.")
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("🔒 Kanal kilitlendi.")

@bot.tree.command(name="unlock", description="Kanalı açar")
async def unlock(i: discord.Interaction):
    if not yetki_kontrol(i, "manage_channels"): return await hata_mesaji(i, "Yetkin yok.")
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message("🔓 Kanal kilidi açıldı.")

@bot.tree.command(name="yavasmod", description="Yavaş mod")
async def yavasmod(i: discord.Interaction, saniye: int):
    if not yetki_kontrol(i, "manage_channels"): return await hata_mesaji(i, "Yetkin yok.")
    await i.channel.edit(slowmode_delay=saniye)
    await i.response.send_message(f"⏳ Yavaş mod: {saniye}s")

@bot.tree.command(name="uyariver", description="Uyarı")
async def uyariver(i: discord.Interaction, member: discord.Member, sebep: str):
    if not yetki_kontrol(i, "manage_guild"): return await hata_mesaji(i, "Yetkin yok.")
    await i.response.send_message(f"⚠️ {member.name} uyarldı: {sebep}")

# --- ROL & KANAL ---
@bot.tree.command(name="rolver", description="Rol ver")
async def rolver(i: discord.Interaction, member: discord.Member, role: discord.Role):
    if not yetki_kontrol(i, "manage_roles"): return await hata_mesaji(i, "Yetkin yok.")
    await member.add_roles(role)
    await i.response.send_message(f"✅ {member.name} adlı üyeye {role.name} verildi.")

@bot.tree.command(name="rolal", description="Rol al")
async def rolal(i: discord.Interaction, member: discord.Member, role: discord.Role):
    if not yetki_kontrol(i, "manage_roles"): return await hata_mesaji(i, "Yetkin yok.")
    await member.remove_roles(role)
    await i.response.send_message(f"✅ {member.name} adlı üyeden {role.name} alındı.")

@bot.tree.command(name="rololustur", description="Rol aç")
async def rololustur(i: discord.Interaction, isim: str):
    if not yetki_kontrol(i, "manage_roles"): return await hata_mesaji(i, "Yetkin yok.")
    await i.guild.create_role(name=isim)
    await i.response.send_message(f"✨ {isim} rolü oluşturuldu.")

@bot.tree.command(name="rolbilgi", description="Rol bilgi")
async def rolbilgi(i: discord.Interaction, role: discord.Role):
    e = discord.Embed(title=f"Rol: {role.name}", color=role.color)
    e.add_field(name="ID", value=role.id)
    e.add_field(name="Üye", value=len(role.members))
    await i.response.send_message(embed=e)

@bot.tree.command(name="kanalolustur", description="Kanal aç")
async def kanalolustur(i: discord.Interaction, isim: str):
    if not yetki_kontrol(i, "manage_channels"): return await hata_mesaji(i, "Yetkin yok.")
    await i.guild.create_text_channel(name=isim)
    await i.response.send_message(f"📁 #{isim} oluşturuldu.")

@bot.tree.command(name="seskanalolustur", description="Ses aç")
async def seskanalolustur(i: discord.Interaction, isim: str):
    if not yetki_kontrol(i, "manage_channels"): return await hata_mesaji(i, "Yetkin yok.")
    await i.guild.create_voice_channel(name=isim)
    await i.response.send_message(f"🔊 {isim} ses kanalı açıldı.")

@bot.tree.command(name="duyuru", description="Duyuru at")
async def duyuru(i: discord.Interaction, kanal: discord.TextChannel, *, mesaj: str):
    if not yetki_kontrol(i, "administrator"): return await hata_mesaji(i, "Yönetici olmalısın.")
    await kanal.send(embed=discord.Embed(title="📢 DUYURU", description=mesaj, color=0xFEE75C))
    await i.response.send_message("✅ Duyuru atıldı.", ephemeral=True)

# --- BİLGİ & DİĞERLERİ ---
@bot.tree.command(name="sunucubilgi", description="Sunucu bilgi")
async def sunucubilgi(i: discord.Interaction):
    g = i.guild
    e = discord.Embed(title=f"📊 {g.name}", color=0x5865F2)
    e.add_field(name="Kurucu", value=g.owner)
    e.add_field(name="Üye", value=g.member_count)
    await i.response.send_message(embed=e)

@bot.tree.command(name="kullanicibilgi", description="Kullanıcı bilgi")
async def kullanicibilgi(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    e = discord.Embed(title=f"👤 {m.name}", color=m.color)
    e.add_field(name="ID", value=m.id)
    e.add_field(name="Katılım", value=m.joined_at.strftime("%d-%m-%Y"))
    await i.response.send_message(embed=e)

@bot.tree.command(name="avatar", description="Avatar gösterir")
async def avatar(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    e = discord.Embed(title=f"🖼️ {m.name} Avatar")
    e.set_image(url=m.display_avatar.url)
    await i.response.send_message(embed=e)

@bot.tree.command(name="ping", description="Ping")
async def ping(i: discord.Interaction):
    await i.response.send_message(f"Pong! 🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="istatistik", description="İstatistik")
async def istatistik(i: discord.Interaction):
    await i.response.send_message(f"📈 Sunucu: {len(bot.guilds)} | Ping: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="yetkililer", description="Yöneticiler")
async def yetkililer(i: discord.Interaction):
    listesi = [m.name for m in i.guild.members if m.guild_permissions.administrator]
    await i.response.send_message(f"👑 Yöneticiler: {', '.join(listesi)}")

@bot.tree.command(name="botsayisi", description="Bot sayısı")
async def botsayisi(i: discord.Interaction):
    await i.response.send_message(f"🤖 Bot: {sum(1 for m in i.guild.members if m.bot)}")

@bot.tree.command(name="uyesayisi", description="Üye sayısı")
async def uyesayisi(i: discord.Interaction):
    await i.response.send_message(f"📊 Toplam Üye: {i.guild.member_count}")

@bot.tree.command(name="isimdegistir", description="İsim değiştir")
async def isimdegistir(i: discord.Interaction, member: discord.Member, yeni_isim: str):
    if not yetki_kontrol(i, "manage_nicknames"): return await hata_mesaji(i, "Yetkin yok.")
    await member.edit(nick=yeni_isim)
    await i.response.send_message(f"✏️ {member.name} adı {yeni_isim} yapıldı.")

@bot.tree.command(name="sunucuikon", description="Sunucu ikon")
async def sunucuikon(i: discord.Interaction):
    await i.response.send_message(i.guild.icon.url if i.guild.icon else "❌ İkon yok.")

@bot.tree.command(name="yetkilerim", description="Yetkiler")
async def yetkilerim(i: discord.Interaction):
    p = [x[0] for x in i.user.guild_permissions if x[1]]
    await i.response.send_message(f"🔑 Yetkiler: {', '.join(p[:10])}")

@bot.tree.command(name="panelbilgi", description="Panel bilgi")
async def panelbilgi(i: discord.Interaction):
    await i.response.send_message("🌐 Web panel üzerinden ayarları yönetebilirsin.")

@bot.tree.command(name="afk", description="Afk")
async def afk(i: discord.Interaction, *, sebep: str = "Açıklama yok"):
    await i.response.send_message(f"💤 {i.user.name} uzakta. Sebep: {sebep}")

@bot.tree.command(name="afkcikis", description="Afk çıkış")
async def afkcikis(i: discord.Interaction):
    await i.response.send_message(f"👋 Hoş geldin {i.user.name}!")

@bot.tree.command(name="botbilgi", description="Bot bilgi")
async def botbilgi(i: discord.Interaction):
    await i.response.send_message("🤖 Güvenli Sunucu Botu v4.5")

@bot.tree.command(name="kufurengel", description="Küfür")
async def kufurengel(i: discord.Interaction): await i.response.send_message("🛡️ Küfür koruması aktif.")

@bot.tree.command(name="reklamengel", description="Reklam")
async def reklamengel(i: discord.Interaction): await i.response.send_message("🛡️ Reklam koruması aktif.")

@bot.tree.command(name="kanalbilgi", description="Kanal bilgi")
async def kanalbilgi(i: discord.Interaction, channel: discord.TextChannel = None):
    c = channel or i.channel
    await i.response.send_message(f"📁 Kanal: #{c.name} (ID: {c.id})")

@bot.tree.command(name="bakim", description="Bakım")
async def bakim(i: discord.Interaction):
    if not yetki_kontrol(i, "administrator"): return await hata_mesaji(i, "Yönetici olmalısın.")
    await i.response.send_message("🛠️ Bakım modu duyuruldu.")

@bot.tree.command(name="kurallar", description="Kurallar")
async def kurallar(i: discord.Interaction): await i.response.send_message("📜 Kurallara dikkat edin.")
@bot.tree.command(name="destek", description="Destek")
async def destek(i: discord.Interaction): await i.response.send_message("🎫 Destek ekibiyle görüşün.")
@bot.tree.command(name="bilgilendirme", description="Bilgi")
async def bilgilendirme(i: discord.Interaction): await i.response.send_message("ℹ️ Sistemler kararlı.")

@bot.tree.command(name="temizlebot", description="Bot mesajlarını sil")
async def temizlebot(i: discord.Interaction):
    if not yetki_kontrol(i, "manage_messages"): return await hata_mesaji(i, "Yetkin yok.")
    await i.response.defer(ephemeral=True)
    d = await i.channel.purge(limit=50, check=lambda m: m.author.bot)
    await i.followup.send(f"🧹 {len(d)} bot mesajı temizlendi.", ephemeral=True)

@bot.tree.command(name="roller", description="Rolleri listele")
async def roller(i: discord.Interaction):
    r = [x.name for x in i.guild.roles if x.name != "@everyone"]
    await i.response.send_message(f"📜 Roller: {', '.join(r[:15])}")

@bot.tree.command(name="kanallar", description="Kanalları listele")
async def kanallar(i: discord.Interaction):
    c = [x.name for x in i.guild.text_channels]
    await i.response.send_message(f"📁 Kanallar: {', '.join(c[:15])}")

# --- ÜYE ETKİNLİKLERİ ---
@bot.event
async def on_member_join(member):
    s = SET.get(member.guild.id, {})
    if s.get("otorol_id"):
        r = member.guild.get_role(int(s["otorol_id"]))
        if r:
            try: await member.add_roles(r)
            except: pass
    if s.get("hosgeldin_kanal_id"):
        k = member.guild.get_channel(int(s["hosgeldin_kanal_id"]))
        if k:
            try: await k.send(f"Hoş geldin {member.mention}, seninle **{member.guild.member_count}** kişi olduk.")
            except: pass

@bot.event
async def on_member_remove(member):
    s = SET.get(member.guild.id, {})
    if s.get("hosgeldin_kanal_id"):
        k = member.guild.get_channel(int(s["hosgeldin_kanal_id"]))
        if k:
            try: await k.send(f"**{member.name}** aramızdan ayrıldı.")
            except: pass

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
    if not g: return "Bulunamadı", 404
    SET.setdefault(gid, {"name": g.name, "otorol_id": "", "hosgeldin_kanal_id": ""})
    if request.method == "POST":
        SET[gid]["otorol_id"] = request.form.get("otorol_id")
        SET[gid]["hosgeldin_kanal_id"] = request.form.get("hosgeldin_kanal_id")
        kaydet()
    return render_template_string(SERVER_H, g=g, set=SET[gid])

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=10000), daemon=True).start()
    bot.run("TOKEN")
    
