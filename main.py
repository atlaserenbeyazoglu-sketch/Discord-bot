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


# --- DİSCORD MODERASYON KOMUTLARI ---

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 **{member.mention}** başarıyla yasaklandı.")
    except:
        await ctx.send(f"❌ Yasaklama başarısız!")

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Yetkin yok.")

# --- WEB PANELİ ---
app = Flask(__name__)
app.secret_key = "gizli123"

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # BURAYI DÜZELTTİM:
    bot.run(os.environ.get("TOKEN"))
    
