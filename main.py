İmport discord, json, os, datetime, threading
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

# --- YETKİ KONTROL FONKSİYONLARI ---
def yetki_kontrol(interaction, perm):
    return getattr(interaction.user.guild_permissions, perm, False)

async def hata_mesaji(interaction, metin):
    await interaction.response.send_message(f"❌ {metin}", ephemeral=True)

# --- 1. YARDIM VE PANEL KOMUTLARI ---
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
            "**/kanalgörünülürlük** - Birden fazla rolün kanalı görüp görmeyeceğini ayarlar."
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- 2. OTOMATİK ROL DEĞİŞİM (LOG) DİNLEYİCİSİ ---
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
