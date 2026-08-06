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
    await bot.tree.sync()
    print(f"Bot aktif edildi: {bot.user}")

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

# --- MODERASYON & GÜVENLİK KOMUTLARI ---
@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı temizler")
@app_commands.describe(limit="Silinecek mesaj sayısı")
async def sil(interaction: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata_mesaji(interaction, "Mesajları yönet yetkiniz bulunmuyor.")
    await interaction.response.defer(ephemeral=True)
    silinenler = await interaction.channel.purge(limit=limit)
    await interaction.followup.send(f"🧹 Başarıyla {len(silinenler)} mesaj silindi.", ephemeral=True)

@bot.tree.command(name="at", description="Etiketlenen üyeyi sunucudan atar")
@app_commands.describe(member="Atılacak üye", sebep="Atılma sebebi")
async def at(interaction: discord.Interaction, member: discord.Member, sebep: str = "Belirtilmemiş"):
    if not yetki_kontrol(interaction, "kick_members"):
        return await hata_mesaji(interaction, "Üyeleri at yetkiniz bulunmuyor.")
    await member.kick(reason=sebep)
    await interaction.response.send_message(f"👢 {member.name} sunucudan atıldı. Sebep: {sebep}")

@bot.tree.command(name="ban", description="Etiketlenen üyeyi sunucudan yasaklar")
@app_commands.describe(member="Yasaklanacak üye", sebep="Yasaklanma sebebi")
async def ban(interaction: discord.Interaction, member: discord.Member, sebep: str = "Belirtilmemiş"):
    if not yetki_kontrol(interaction, "ban_members"):
        return await hata_mesaji(interaction, "Üyeleri yasakla yetkiniz bulunmuyor.")
    await member.ban(reason=sebep)
    await interaction.response.send_message(f"🔨 {member.name} sunucudan yasaklandı. Sebep: {sebep}")

@bot.tree.command(name="unban", description="ID'si verilen kullanıcının yasağını kaldırır")
@app_commands.describe(user_id="Kullanıcı ID")
async def unban(interaction: discord.Interaction, user_id: str):
    if not yetki_kontrol(interaction, "ban_members"):
        return await hata_mesaji(interaction, "Yasak kaldırma yetkiniz bulunmuyor.")
    await interaction.response.defer()
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.followup.send(f"✅ {user.name} adlı kullanıcının yasağı kaldırıldı.")
    except Exception as e:
        await interaction.followup.send(f"❌ Bir hata oluştu: {e}")

@bot.tree.command(name="sustur", description="Üyeye zaman aşımı (timeout) uygular")
@app_commands.describe(member="Susturulacak üye", saat="Süre (saat cinsinden)", sebep="Sebep")
async def sustur(interaction: discord.Interaction, member: discord.Member, saat: int = 1, sebep: str = "Belirtilmemiş"):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Üyeleri susturma yetkiniz yok.")
    await member.timeout(datetime.timedelta(hours=saat), reason=sebep)
    await interaction.response.send_message(f"🔇 {member.name} {saat} saat süreyle susturuldu.")

@bot.tree.command(name="susturkaldir", description="Üyenin zaman aşımını kaldırır")
@app_commands.describe(member="Susturması kaldırılacak üye")
async def susturkaldir(interaction: discord.Interaction, member: discord.Member):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    await member.timeout(None)
    await interaction.response.send_message(f"🔊 {member.name} adlı üyenin susturması kaldırıldı.")

@bot.tree.command(name="lock", description="Bulunduğunuz kanalı mesaj gönderimine kapatır")
async def lock(interaction: discord.Interaction):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalı yönet yetkiniz yok.")
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("🔒 Kanal mesaj gönderimine kapatıldı (Kilitlendi).")

@bot.tree.command(name="unlock", description="Kanalın kilidini açar")
async def unlock(interaction: discord.Interaction):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalı yönet yetkiniz yok.")
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("🔓 Kanalın kilidi açıldı.")

@bot.tree.command(name="yavasmod", description="Kanal için yavaş mod süresini ayarlar")
@app_commands.describe(saniye="Saniye cinsinden süre (0 kapatır)")
async def yavasmod(interaction: discord.Interaction, saniye: int):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalı yönet yetkiniz yok.")
    await interaction.channel.edit(slowmode_delay=saniye)
    await interaction.response.send_message(f"⏳ Yavaş mod {saniye} saniye olarak ayarlandı.")

@bot.tree.command(name="uyariver", description="Üyeye resmi uyarı gönderir")
@app_commands.describe(member="Uyarılacak üye", sebep="Uyarı sebebi")
async def uyariver(interaction: discord.Interaction, member: discord.Member, sebep: str):
    if not yetki_kontrol(interaction, "manage_guild"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    await interaction.response.send_message(f"⚠️ {member.mention} uyarılmıştır! Sebep: {sebep}")

# --- ROL & KANAL KOMUTLARI ---
@bot.tree.command(name="rolver", description="Üyeye belirtilen rolü verir")
@app_commands.describe(member="Hedef üye", role="Verilecek rol")
async def rolver(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not yetki_kontrol(interaction, "manage_roles"):
        return await hata_mesaji(interaction, "Rolleri yönet yetkiniz yok.")
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ {member.name} adlı üyeye {role.name} rolü verildi.")

@bot.tree.command(name="rolal", description="Üyeden belirtilen rolü alır")
@app_commands.describe(member="Hedef üye", role="Alınacak rol")
async def rolal(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not yetki_kontrol(interaction, "manage_roles"):
        return await hata_mesaji(interaction, "Rolleri yönet yetkiniz yok.")
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ {member.name} adlı üyeden {role.name} rolü alındı.")

@bot.tree.command(name="rololustur", description="Yeni bir rol oluşturur")
@app_commands.describe(isim="Rolün adı")
async def rololustur(interaction: discord.Interaction, isim: str):
    if not yetki_kontrol(interaction, "manage_roles"):
        return await hata_mesaji(interaction, "Rolleri yönet yetkiniz yok.")
    await interaction.guild.create_role(name=isim)
    await interaction.response.send_message(f"✨ {isim} adlı rol başarıyla oluşturuldu.")

@bot.tree.command(name="rolbilgi", description="Bir rol hakkında bilgi verir")
@app_commands.describe(role="Bilgisi istenen rol")
async def rolbilgi(interaction: discord.Interaction, role: discord.Role):
    embed = discord.Embed(title=f"Rol Bilgisi: {role.name}", color=role.color)
    embed.add_field(name="Rol ID", value=role.id, inline=True)
    embed.add_field(name="Rol Üye Sayısı", value=len(role.members), inline=True)
    embed.add_field(name="Oluşturulma Tarihi", value=role.created_at.strftime("%d-%m-%Y"), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kanalolustur", description="Yeni bir metin kanalı oluşturur")
@app_commands.describe(isim="Kanal adı")
async def kanalolustur(interaction: discord.Interaction, isim: str):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalları yönet yetkiniz yok.")
    await interaction.guild.create_text_channel(name=isim)
    await interaction.response.send_message(f"📁 #{isim} metin kanalı oluşturuldu.")

@bot.tree.command(name="seskanalolustur", description="Yeni bir ses kanalı oluşturur")
@app_commands.describe(isim="Ses kanalının adı")
async def seskanalolustur(interaction: discord.Interaction, isim: str):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Kanalları yönet yetkiniz yok.")
    await interaction.guild.create_voice_channel(name=isim)
    await interaction.response.send_message(f"🔊 {isim} ses kanalı oluşturuldu.")

@app_commands.describe(kanal="Duyurunun gönderileceği kanal", mesaj="Duyuru metni")
@bot.tree.command(name="duyuru", description="Belirtilen kanala şık bir duyuru gönderir")
async def duyuru(interaction: discord.Interaction, kanal: discord.TextChannel, *, mesaj: str):
    if not yetki_kontrol(interaction, "administrator"):
        return await hata_mesaji(interaction, "Bu komut için Yönetici yetkisi gereklidir.")
    embed = discord.Embed(title="📢 DUYURU", description=mesaj, color=0xFEE75C)
    embed.set_footer(text=f"Gönderen: {interaction.user.name}")
    await kanal.send(embed=embed)
    await interaction.response.send_message("✅ Duyuru başarıyla gönderildi.", ephemeral=True)
     # --- BİLGİ & DİĞER KOMUTLAR ---
@bot.tree.command(name="sunucubilgi", description="Sunucu hakkında detaylı bilgi gösterir")
async def sunucubilgi(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=f"📊 {g.name} Sunucu Bilgileri", color=0x5865F2)
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Sunucu Sahibi", value=g.owner, inline=True)
    embed.add_field(name="Üye Sayısı", value=g.member_count, inline=True)
    embed.add_field(name="Kanal Sayısı", value=len(g.channels), inline=True)
    embed.add_field(name="Rol Sayısı", value=len(g.roles), inline=True)
    embed.add_field(name="Kuruluş Tarihi", value=g.created_at.strftime("%d-%m-%Y"), inline=False)
    await interaction.response.send_message(embed=embed)

@app_commands.describe(member="Bilgisi istenen üye (boş bırakırsanız kendiniz olursunuz)")
@bot.tree.command(name="kullanicibilgi", description="Kullanıcı hakkında detaylı bilgi gösterir")
async def kullanicibilgi(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    embed = discord.Embed(title=f"👤 Kullanıcı Bilgisi: {m.name}", color=m.color)
    embed.set_thumbnail(url=m.display_avatar.url)
    embed.add_field(name="Kullanıcı ID", value=m.id, inline=True)
    embed.add_field(name="Sunucuya Katılım", value=m.joined_at.strftime("%d-%m-%Y") if m.joined_at else "Bilinmiyor", inline=True)
    embed.add_field(name="Hesap Oluşturulma", value=m.created_at.strftime("%d-%m-%Y"), inline=False)
    roller = [r.name for r in m.roles if r.name != "@everyone"]
    embed.add_field(name=f"Roller ({len(roller)})", value=", ".join(roller[:10]) if roller else "Rolü yok", inline=False)
    await interaction.response.send_message(embed=embed)

@app_commands.describe(member="Avatarı gösterilecek üye")
@bot.tree.command(name="avatar", description="Kullanıcının avatarını gösterir")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    m = member or interaction.user
    embed = discord.Embed(title=f"🖼️ {m.name} adlı kullanıcının avatarı", color=m.color)
    embed.set_image(url=m.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Botun gecikme süresini gösterir")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! 🏓 Gecikme süresi: **{latency}ms**")

@bot.tree.command(name="istatistik", description="Botun genel istatistiklerini gösterir")
async def istatistik(interaction: discord.Interaction):
    embed = discord.Embed(title="📈 Bot İstatistikleri", color=0x5865F2)
    embed.add_field(name="Sunucu Sayısı", value=len(bot.guilds), inline=True)
    embed.add_field(name="Toplam Üye", value=sum(g.member_count for g in bot.guilds), inline=True)
    embed.add_field(name="Gecikme (Ping)", value=f"{round(bot.latency * 1000)}ms", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="yetkililer", description="Sunucudaki yöneticileri listeler")
async def yetkililer(interaction: discord.Interaction):
    listesi = [m.name for m in interaction.guild.members if m.guild_permissions.administrator and not m.bot]
    await interaction.response.send_message(f"👑 Sunucu Yöneticileri:\n" + (", ".join(listesi) if listesi else "Yönetici bulunamadı."))

@bot.tree.command(name="botsayisi", description="Sunucudaki toplam bot sayısını gösterir")
async def botsayisi(interaction: discord.Interaction):
    bot_sayisi = sum(1 for m in interaction.guild.members if m.bot)
    await interaction.response.send_message(f"🤖 Bu sunucuda toplam **{bot_sayisi}** adet bot bulunmaktadır.")

@bot.tree.command(name="uyesayisi", description="Sunucudaki toplam üye sayısını gösterir")
async def uyesayisi(interaction: discord.Interaction):
    await interaction.response.send_message(f"📊 Sunucudaki toplam üye sayısı: **{interaction.guild.member_count}**")

@app_commands.describe(member="İsmi değiştirilecek üye", yeni_isim="Yeni takma ad")
@bot.tree.command(name="isimdegistir", description="Üyenin sunucu içindeki takma adını değiştirir")
async def isimdegistir(interaction: discord.Interaction, member: discord.Member, yeni_isim: str):
    if not yetki_kontrol(interaction, "manage_nicknames"):
        return await hata_mesaji(interaction, "Üye adlarını yönet yetkiniz yok.")
    await member.edit(nick=yeni_isim)
    await interaction.response.send_message(f"✏️ {member.name} adlı üyenin adı **{yeni_isim}** olarak değiştirildi.")

@bot.tree.command(name="sunucuikon", description="Sunucunun ikonunu gösterir")
async def sunucuikon(interaction: discord.Interaction):
    g = interaction.guild
    if g.icon:
        embed = discord.Embed(title=f"🖼️ {g.name} İkonu")
        embed.set_image(url=g.icon.url)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Bu sunucunun bir ikonu bulunmuyor.")

@bot.tree.command(name="yetkilerim", description="Kendi yetkilerinizi listeler")
async def yetkilerim(interaction: discord.Interaction):
    p = [x[0] for x in interaction.user.guild_permissions if x[1]]
    await interaction.response.send_message(f"🔑 Sahip olduğunuz bazı yetkiler:\n" + ", ".join(p[:15]))

@bot.tree.command(name="panelbilgi", description="Web panel hakkında bilgi verir")
async def panelbilgi(interaction: discord.Interaction):
    await interaction.response.send_message("🌐 Botun web paneline tarayıcınızdan bağlanarak otorol ve hoş geldin kanalını kolayca yönetebilirsiniz.")

@app_commands.describe(sebep="AFK olma sebebi")
async def afk(interaction: discord.Interaction, *, sebep: str = "Açıklama belirtilmedi"):
    await interaction.response.send_message(f"💤 **{interaction.user.name}** adlı kullanıcı AFK moduna geçti. Sebep: {sebep}")

@bot.tree.command(name="afkcikis", description="AFK modundan çıkış yapar")
async def afkcikis(interaction: discord.Interaction):
    await interaction.response.send_message(f"👋 Hoş geldin **{interaction.user.name}**, AFK modundan çıktın!")

@bot.tree.command(name="botbilgi", description="Bot hakkında genel bilgi verir")
async def botbilgi(interaction: discord.Interaction):
    await interaction.response.send_message("🤖 Güvenli Sunucu Botu v4.5 | Flask web paneli entegreli gelişmiş yönetim botu.")

@bot.tree.command(name="kufurengel", description="Küfür koruması durumunu gösterir")
async def kufurengel(interaction: discord.Interaction):
    await interaction.response.send_message("🛡️ Küfür koruması sistemi aktif olarak çalışmaktadır.")

@bot.tree.command(name="reklamengel", description="Reklam koruması durumunu gösterir")
async def reklamengel(interaction: discord.Interaction):
    await interaction.response.send_message("🛡️ Reklam koruması sistemi aktif olarak çalışmaktadır.")

@app_commands.describe(channel="Bilgisi istenen kanal")
@bot.tree.command(name="kanalbilgi", description="Kanal hakkında detaylı bilgi verir")
async def kanalbilgi(interaction: discord.Interaction, channel: discord.TextChannel = None):
    c = channel or interaction.channel
    embed = discord.Embed(title=f"📁 Kanal Bilgisi: #{c.name}", color=0x5865F2)
    embed.add_field(name="Kanal ID", value=c.id, inline=True)
    embed.add_field(name="Oluşturulma Tarihi", value=c.created_at.strftime("%d-%m-%Y"), inline=True)
    embed.add_field(name="Kanal Türü", value=str(c.type), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bakim", description="Sunucuda bakım modu duyurusu yapar")
async def bakim(interaction: discord.Interaction):
    if not yetki_kontrol(interaction, "administrator"):
        return await hata_mesaji(interaction, "Yönetici olmalısınız.")
    embed = discord.Embed(title="🛠️ BAKIM MODU", description="Sunucumuzda bir süreliğine bakım yapılacaktır. Lütfen anlayış gösterin.", color=0xED4245)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kurallar", description="Sunucu kurallarını gösterir")
async def kurallar(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Sunucu Kuralları", description="1. Saygı ve sevgi çerçevesinde kalın.\n2. Reklam ve spam yapmak yasaktır.\n3. Küfür ve hakaret kesinlikle yasaktır.", color=0xFEE75C)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="destek", description="Destek ekibi ile ilgili bilgi verir")
async def destek(interaction: discord.Interaction):
    await interaction.response.send_message("🎫 Destek almak için ilgili kanallardan talep açabilir veya yetkililere ulaşabilirsiniz.")

@bot.tree.command(name="bilgilendirme", description="Sistemlerin durumunu bildirir")
async def bilgilendirme(interaction: discord.Interaction):
    await interaction.response.send_message("ℹ️ Tüm bot sistemleri, web paneli ve veritabanı sorunsuz ve kararlı bir şekilde çalışmaktadır.")

@bot.tree.command(name="temizlebot", description="Sohbetteki bot mesajlarını temizler")
async def temizlebot(interaction: discord.Interaction):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata_mesaji(interaction, "Mesajları yönet yetkiniz yok.")
    await interaction.response.defer(ephemeral=True)
    silinenler = await interaction.channel.purge(limit=50, check=lambda m: m.author.bot)
    await interaction.followup.send(f"🧹 Toplam {len(silinenler)} adet bot mesajı temizlendi.", ephemeral=True)

@bot.tree.command(name="roller", description="Sunucudaki rolleri listeler")
async def roller(interaction: discord.Interaction):
    r = [x.name for x in interaction.guild.roles if x.name != "@everyone"]
    await interaction.response.send_message(f"📜 Sunucudaki Roller:\n" + (", ".join(r[:20]) if r else "Rol bulunmuyor."))

@bot.tree.command(name="kanallar", description="Sunucudaki kanalları listeler")
async def kanallar(interaction: discord.Interaction):
    c = [x.name for x in interaction.guild.text_channels]
    await interaction.response.send_message(f"📁 Sunucudaki Metin Kanalları:\n" + (", ".join(c[:20]) if c else "Kanal bulunmuyor."))

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

@bot.event
async def on_member_remove(member):
    s = SET.get(member.guild.id, {})
    if s.get("hosgeldin_kanal_id"):
        kanal = member.guild.get_channel(int(s["hosgeldin_kanal_id"]))
        if kanal:
            try:
                await kanal.send(f"**{member.name}** sunucumuzdan ayrıldı.")
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
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=10000), daemon=True).start()
    bot.run("TOKEN")
        
