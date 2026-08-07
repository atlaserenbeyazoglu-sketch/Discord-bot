import os
import json
import datetime
import threading

import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask, render_template_string, request, redirect, url_for


# =========================================================
# AYARLAR
# =========================================================

DOSYA = "ayarlar.json"
SET = {}
LOCK = threading.Lock()

TOKEN = os.getenv("TOKEN")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", "2904")

PANEL_URL = "https://discord-bot-fa6e.onrender.com/"


# =========================================================
# JSON SİSTEMİ
# =========================================================

def yukle():
    global SET

    if not os.path.exists(DOSYA):
        SET = {}
        return

    try:
        with LOCK:
            with open(DOSYA, "r", encoding="utf-8") as f:
                data = json.load(f)

        SET = {int(k): v for k, v in data.items()}

    except Exception as e:
        print(f"⚠️ Ayarlar yüklenemedi: {e}")
        SET = {}


def kaydet():
    try:
        with LOCK:
            with open(DOSYA, "w", encoding="utf-8") as f:
                json.dump(
                    SET,
                    f,
                    ensure_ascii=False,
                    indent=4
                )
    except Exception as e:
        print(f"⚠️ Ayarlar kaydedilemedi: {e}")


def varsayilan_ayarlar(guild):
    return {
        "name": guild.name,
        "otorol_id": "",
        "hosgeldin_kanal_id": "",
        "log_kanal_id": ""
    }


yukle()


# =========================================================
# DISCORD BOT
# =========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# BOT HAZIR
# =========================================================

@bot.event
async def on_ready():
    print("========================================")
    print(f"🤖 Bot: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Sunucu sayısı: {len(bot.guilds)}")
    print("========================================")

    yukle()

    for guild in bot.guilds:
        if guild.id not in SET:
            SET[guild.id] = varsayilan_ayarlar(guild)
        else:
            SET[guild.id]["name"] = guild.name

    kaydet()

    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"❌ Slash komut senkronizasyon hatası: {e}")

    print("🟢 Discord bağlantısı aktif.")
    print("🔄 Auto reconnect aktif.")


# =========================================================
# MESAJ SİSTEMİ
# =========================================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.strip().lower() == "sa":
        try:
            await message.channel.send(
                f"Aleykümselam {message.author.mention}"
            )
        except Exception:
            pass

    await bot.process_commands(message)


# =========================================================
# YETKİ
# =========================================================

def yetki_kontrol(interaction, yetki):
    return getattr(
        interaction.user.guild_permissions,
        yetki,
        False
    )


async def hata(interaction, mesaj):
    if interaction.response.is_done():
        await interaction.followup.send(
            f"❌ {mesaj}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {mesaj}",
            ephemeral=True
        )


# =========================================================
# PANEL KOMUTU
# =========================================================

@bot.tree.command(
    name="panel",
    description="Web kontrol panelini açar."
)
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Bot Kontrol Paneli",
        description=(
            f"Paneli açmak için aşağıdaki adresi kullan:\n\n"
            f"{PANEL_URL}"
        ),
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# KOMUTLAR
# =========================================================

@bot.tree.command(
    name="komutlar",
    description="Botun komutlarını gösterir."
)
async def komutlar(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Bot Komutları",
        color=0x5865F2
    )

    embed.add_field(
        name="🛠️ Yönetim",
        value=(
            "**/panel** → Web panelini açar.\n"
            "**/komutlar** → Komut listesini gösterir.\n"
            "**/sunucu-kur** → Sunucu yapısını kurar.\n"
            "**/sil** → Mesajları temizler.\n"
            "**/kanala-yazma** → Rol yazma izni ayarlar.\n"
            "**/mute** → Kullanıcıyı susturur.\n"
            "**/unmute** → Susturmayı kaldırır.\n"
            "**/yavasmod** → Yavaş modu ayarlar.\n"
            "**/kanal-gorunurluk** → Kanal görünürlüğünü ayarlar."
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# SUNUCU KUR
# =========================================================

@bot.tree.command(
    name="sunucu-kur",
    description="Sunucu kategorilerini ve kanallarını oluşturur."
)
async def sunucu_kur(interaction: discord.Interaction):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata(
            interaction,
            "Kanal yönetme yetkiniz yok."
        )

    await interaction.response.defer()
    guild = interaction.guild

    kategoriler = {
        "「📌」Önemli": [
            "❓biz-kimiz",
            "❓görevlerimiz",
            "⬛kara-liste",
            "🚪gelen-giden",
            "👔kılık-kıyafet"
        ],
        "「📢」Duyuru": [
            "📢personel-duyuru",
            "📢aktiflik-duyuru",
            "📢operasyon-duyuru",
            "📜kararname",
            "📋hiyerarşi"
        ],
        "「🗨」Sohbet Kanalları": [
            "🗨sohbet",
            "📸galeri-kanalı",
            "🤖bot-komut",
            "🤔öneri-istek",
            "📤i̇stifa-i̇zin",
            "😴inaktiflik-izin"
        ],
        "「🧾」Kayıtlar": [
            "🧾alım-logs",
            "🧾alım-sistemi",
            "🧾eğitim-logs",
            "🧾eğitim-sistemi"
        ]
    }

    try:
        for kategori_adi, kanallar in kategoriler.items():
            kategori = await guild.create_category(kategori_adi)

            for kanal_adi in kanallar:
                await guild.create_text_channel(
                    kanal_adi,
                    category=kategori
                )

        await interaction.followup.send(
            "✅ Sunucu yapısı başarıyla oluşturuldu."
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Kurulum hatası: `{e}`"
        )


# =========================================================
# MESAJ SİL
# =========================================================

@bot.tree.command(
    name="sil",
    description="Belirtilen miktarda mesajı siler."
)
@app_commands.describe(
    limit="1 ile 100 arasında mesaj sayısı"
)
async def sil(
    interaction: discord.Interaction,
    limit: int = 5
):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata(
            interaction,
            "Mesajları yönetme yetkiniz yok."
        )

    if not 1 <= limit <= 100:
        return await hata(
            interaction,
            "Mesaj sayısı 1-100 arasında olmalıdır."
        )

    await interaction.response.defer(ephemeral=True)

    try:
        silinen = await interaction.channel.purge(
            limit=limit
        )

        await interaction.followup.send(
            f"🧹 **{len(silinen)}** mesaj silindi.",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Silme hatası: `{e}`",
            ephemeral=True
        )


# =========================================================
# ROLLERİN YAZMA İZNİ
# =========================================================

@bot.tree.command(
    name="kanala-yazma",
    description="Rollerin kanala yazma iznini değiştirir."
)
@app_commands.describe(
    durum="True: Yazabilir, False: Yazamaz",
    rol1="1. rol",
    rol2="2. rol",
    rol3="3. rol",
    rol4="4. rol",
    rol5="5. rol"
)
async def kanala_yazma(
    interaction: discord.Interaction,
    durum: bool,
    rol1: discord.Role = None,
    rol2: discord.Role = None,
    rol3: discord.Role = None,
    rol4: discord.Role = None,
    rol5: discord.Role = None
):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata(
            interaction,
            "Kanalları yönetme yetkiniz yok."
        )

    roller = [
        r for r in [rol1, rol2, rol3, rol4, rol5]
        if r
    ]

    if not roller:
        return await hata(
            interaction,
            "En az bir rol seçmelisiniz."
        )

    for rol in roller:
        await interaction.channel.set_permissions(
            rol,
            send_messages=durum
        )

    durum_yazi = "açıldı ✍️" if durum else "kapatıldı 🚫"

    await interaction.response.send_message(
        f"⚙️ Seçilen rollerin yazma izni **{durum_yazi}**."
    )


# =========================================================
# MUTE
# =========================================================

@bot.tree.command(
    name="mute",
    description="Kullanıcıya zaman aşımı uygular."
)
@app_commands.describe(
    uye="Susturulacak kullanıcı",
    saat="Süre",
    sebep="Sebep"
)
async def mute(
    interaction: discord.Interaction,
    uye: discord.Member,
    saat: int = 1,
    sebep: str = "Belirtilmedi"
):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata(
            interaction,
            "Üyeleri susturma yetkiniz yok."
        )

    if saat < 1:
        return await hata(
            interaction,
            "Süre en az 1 saat olmalıdır."
        )

    try:
        await uye.timeout(
            datetime.timedelta(hours=saat),
            reason=sebep
        )

        await interaction.response.send_message(
            f"🔇 **{uye}** kullanıcısı "
            f"**{saat} saat** susturuldu.\n"
            f"📝 Sebep: `{sebep}`"
        )

    except Exception as e:
        await hata(
            interaction,
            f"Mute uygulanamadı: `{e}`"
        )


# =========================================================
# UNMUTE
# =========================================================

@bot.tree.command(
    name="unmute",
    description="Kullanıcının susturmasını kaldırır."
)
@app_commands.describe(
    uye="Susturması kaldırılacak kullanıcı"
)
async def unmute(
    interaction: discord.Interaction,
    uye: discord.Member
):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata(
            interaction,
            "Üyeleri yönetme yetkiniz yok."
        )

    try:
        await uye.timeout(None)

        await interaction.response.send_message(
            f"🔊 **{uye}** kullanıcısının susturması kaldırıldı."
        )

    except Exception as e:
        await hata(
            interaction,
            f"Unmute uygulanamadı: `{e}`"
        )


# =========================================================
# YAVAŞ MOD
# =========================================================

@bot.tree.command(
    name="yavasmod",
    description="Kanalın yavaş modunu ayarlar."
)
@app_commands.describe(
    saniye="0-21600 saniye. 0 kapatır."
)
async def yavasmod(
    interaction: discord.Interaction,
    saniye: int
):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata(
            interaction,
            "Kanal yönetme yetkiniz yok."
        )

    if not 0 <= saniye <= 21600:
        return await hata(
            interaction,
            "Süre 0-21600 saniye arasında olmalıdır."
        )

    try:
        await interaction.channel.edit(
            slowmode_delay=saniye
        )

        if saniye == 0:
            mesaj = "⏳ Yavaş mod kapatıldı."
        else:
            mesaj = (
                f"⏳ Yavaş mod **{saniye} saniye** olarak ayarlandı."
            )

        await interaction.response.send_message(mesaj)

    except Exception as e:
        await hata(
            interaction,
            f"Yavaş mod ayarlanamadı: `{e}`"
        )


# =========================================================
# KANAL GÖRÜNÜRLÜĞÜ
# =========================================================

@bot.tree.command(
    name="kanal-gorunurluk",
    description="Rollerin kanal görünürlüğünü ayarlar."
)
@app_commands.describe(
    rol1="1. rol",
    gorunurluk="True: Görür, False: Göremez",
    rol2="2. rol",
    rol3="3. rol",
    rol4="4. rol"
)
async def kanal_gorunurluk(
    interaction: discord.Interaction,
    rol1: discord.Role,
    gorunurluk: bool,
    rol2: discord.Role = None,
    rol3: discord.Role = None,
    rol4: discord.Role = None
):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata(
            interaction,
            "Kanalları yönetme yetkiniz yok."
        )

    roller = [
        r for r in [rol1, rol2, rol3, rol4]
        if r
    ]

    for rol in roller:
        await interaction.channel.set_permissions(
            rol,
            view_channel=gorunurluk
        )

    durum = "görebilecek 👁️" if gorunurluk else "göremeyecek 🚫"

    await interaction.response.send_message(
        f"👁️ Seçilen roller kanalı artık **{durum}**."
    )


# =========================================================
# ROL LOG SİSTEMİ
# =========================================================

@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles:
        return

    yukle()

    ayar = SET.get(after.guild.id, {})
    kanal_id = ayar.get("log_kanal_id")

    if not kanal_id:
        return

    try:
        kanal = after.guild.get_channel(int(kanal_id))
    except Exception:
        return

    if not kanal:
        return

    eklenen = [
        r for r in after.roles
        if r not in before.roles
    ]

    alinan = [
        r for r in before.roles
        if r not in after.roles
    ]

    veren = "Bilinmiyor / Otomatik"

    try:
        async for entry in after.guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.member_role_update
        ):
            if entry.target.id == after.id:
                veren = entry.user.mention
                break
    except Exception:
        pass

    for rol in eklenen:
        embed = discord.Embed(
            title="✅ Rol Verildi",
            color=0x57F287,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(
            name="Kullanıcı",
            value=after.mention,
            inline=False
        )
        embed.add_field(
            name="Rol",
            value=rol.mention,
            inline=False
        )
        embed.add_field(
            name="İşlemi Yapan",
            value=veren,
            inline=False
        )

        try:
            await kanal.send(embed=embed)
        except Exception:
            pass

    for rol in alinan:
        embed = discord.Embed(
            title="⚠️ Rol Alındı",
            color=0xED4245,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(
            name="Kullanıcı",
            value=after.mention,
            inline=False
        )
        embed.add_field(
            name="Rol",
            value=rol.name,
            inline=False
        )
        embed.add_field(
            name="İşlemi Yapan",
            value=veren,
            inline=False
        )

        try:
            await kanal.send(embed=embed)
        except Exception:
            pass


# =========================================================
# ÜYE GİRİŞİ
# =========================================================

@bot.event
async def on_member_join(member):
    yukle()

    ayar = SET.get(member.guild.id, {})

    otorol = ayar.get("otorol_id")
    hosgeldin = ayar.get("hosgeldin_kanal_id")

    if otorol:
        try:
            rol = member.guild.get_role(int(otorol))
            if rol:
                await member.add_roles(rol)
        except Exception as e:
            print(f"⚠️ Otorol hatası: {e}")

    if hosgeldin:
        try:
            kanal = member.guild.get_channel(int(hosgeldin))
            if kanal:
                await kanal.send(
                    f"Hoş geldin {member.mention}! "
                    f"Sunucumuzda **{member.guild.member_count}** kişiyiz."
                )
        except Exception as e:
            print(f"⚠️ Hoş geldin mesajı hatası: {e}")


# =========================================================
# FLASK PANELİ
# =========================================================

app = Flask(__name__)


LOGIN_H = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Bot Paneli</title>
<style>
body{
background:#1e1f22;color:white;font-family:Arial;
display:flex;justify-content:center;align-items:center;
height:100vh;margin:0
}
.box{
background:#2b2d31;padding:35px;border-radius:14px;
width:320px;text-align:center
}
input,button{
width:100%;box-sizing:border-box;padding:12px;
margin-top:12px;border-radius:7px;border:1px solid #444;
background:#1e1f22;color:white
}
button{
background:#5865f2;border:0;font-weight:bold;cursor:pointer
}
.err{color:#ed4245}
</style>
</head>
<body>
<div class="box">
<h2>🛡️ Güvenli Panel</h2>
{% if error %}<p class="err">{{error}}</p>{% endif %}
<form method="POST">
<input type="password" name="password"
placeholder="Panel şifresi" required>
<button type="submit">Giriş Yap</button>
</form>
</div>
</body>
</html>
"""


INDEX_H = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Bot Paneli</title>
<style>
body{
background:#1e1f22;color:white;font-family:Arial;padding:25px
}
.box{
max-width:650px;margin:auto;background:#2b2d31;
padding:25px;border-radius:14px
}
.card{
background:#111;padding:16px;margin:10px 0;
border-radius:9px;display:flex;
justify-content:space-between;align-items:center
}
a{
color:white;text-decoration:none
}
.btn{
background:#5865f2;padding:9px 15px;border-radius:7px
}
.logout{color:#ed4245;float:right}
</style>
</head>
<body>
<div class="box">
<a class="logout" href="/logout">Çıkış</a>
<h2>🤖 Sunucu Yönetimi</h2>
{% for g in guilds %}
<div class="card">
<span>📢 {{g.name}}</span>
<a class="btn" href="/server/{{g.id}}">Yönet</a>
</div>
{% endfor %}
</div>
</body>
</html>
"""


SERVER_H = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Sunucu Ayarları</title>
<style>
body{
background:#1e1f22;color:white;font-family:Arial;padding:25px
}
.box{
max-width:650px;margin:auto;background:#2b2d31;
padding:25px;border-radius:14px
}
select,button{
width:100%;box-sizing:border-box;padding:12px;
margin:10px 0;background:#1e1f22;color:white;
border:1px solid #444;border-radius:7px
}
button{
background:#57F287;color:#111;font-weight:bold
}
a{color:#00aff4;text-decoration:none}
.alert{
background:#57F287;color:#111;padding:10px;
border-radius:7px;text-align:center
}
</style>
</head>
<body>
<div class="box">

<a href="/">⬅️ Geri</a>

<h2>⚙️ {{g.name}}</h2>

{% if saved %}
<div class="alert">✅ Ayarlar kaydedildi.</div>
{% endif %}

<form method="POST">

<label>Otorol:</label>
<select name="otorol_id">
<option value="">-- Seçilmedi --</option>

{% for r in g.roles %}
{% if r.name != "@everyone" %}
<option value="{{r.id}}"
{% if se
