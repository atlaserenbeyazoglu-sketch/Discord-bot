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
    
    # --- KOMUTLARIN ANINDA ÇALIŞMASI İÇİN SENKRODİZASYON AYARI ---
    # Botun katıldığı tüm sunucularda komutların anında senkronize olması için:
    try:
        await bot.tree.sync()
        print("✅ Tüm komutlar başarıyla senkronize edildi (Sync aktif)!")
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

# --- WEB PANEL LİNK KOMUTU ---
@bot.tree.command(name="panel", description="Web kontrol paneli linkini gönderir")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Web Kontrol Paneli", 
        description="Sunucu ayarlarını (Otorol ve Hoş Geldin Kanalı) yönetmek için web panelini kullanabilirsin.", 
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- İSTEDİĞİN ÖZEL KOMUTLAR ---
@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı temizler")
@app_commands.describe(limit="Silinecek mesaj sayısı")
async def sil(interaction: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata_mesaji(interaction, "Mesajları yönet yetkiniz bulunmuyor.")
    await interaction.response.defer(ephemeral=True)
    silinenler = await interaction.channel.purge(limit=limit)
    await interaction.followup.send(f"🧹 Başarıyla {len(silinenler)} mesaj silindi.", ephemeral=True)

@bot.tree.command(name="rolver", description="Üyeye belirtilen rolü verir")
@app_commands.describe(member="Hedef üye", role="Verilecek rol")
async def rolver(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not yetki_kontrol(interaction, "manage_roles"):
        return await hata_mesaji(interaction, "Rolleri yönet yetkiniz bulunmuyor.")
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ {member.name} adlı üyeye {role.name} rolü verildi.")

@bot.tree.command(name="rolal", description="Üyeden belirtilen rolü alır")
@app_commands.describe(member="Hedef üye", role="Alınacak rol")
async def rolal(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not yetki_kontrol(interaction, "manage_roles"):
        return await hata_mesaji(interaction, "Rolleri yönet yetkiniz bulunmuyor.")
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ {member.name} adlı üyeden {role.name} alındı.")

@bot.tree.command(name="rololustur", description="Yeni bir rol oluşturur")
@app_commands.describe(isim="Rolün adı")
async def rololustur(interaction: discord.Interaction, isim: str):
    if not yetki_kontrol(interaction, "manage_roles"):
        return await hata_mesaji(interaction, "Rolleri yönet yetkiniz bulunmuyor.")
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

# --- DİĞER TEMEL KOMUTLAR VE BİLGİLER ---
@bot.tree.command(name="ping", description="Botun gecikme süresini gösterir")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! 🏓 Gecikme süresi: **{latency}ms**")

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
    await interaction.response.send_message(embed=embed)

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
    
    # Render'daki 'TOKEN' değişkenini okur
    discord_token = os.environ.get("TOKEN")
    bot.run(discord_token)
    
