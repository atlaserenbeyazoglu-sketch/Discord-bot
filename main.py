import discord
import json
import os
import datetime
import threading
import asyncio

from discord.ext import commands
from discord import app_commands
from flask import Flask, render_template_string, request, redirect, url_for


# =========================================================
# AYARLAR
# =========================================================

DOSYA = "ayarlar.json"
SET = {}

# Panel şifresi VPS/Render environment variable'dan alınır.
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "2904")


# =========================================================
# JSON SİSTEMİ
# =========================================================

def yukle():
    global SET

    if os.path.exists(DOSYA):
        try:
            with open(DOSYA, "r", encoding="utf-8") as f:
                data = json.load(f)

            SET = {int(k): v for k, v in data.items()}

        except Exception as e:
            print(f"⚠️ Ayarlar yüklenirken hata: {e}")


def kaydet():
    try:
        with open(DOSYA, "w", encoding="utf-8") as f:
            json.dump(
                SET,
                f,
                ensure_ascii=False,
                indent=4
            )

    except Exception as e:
        print(f"⚠️ Ayarlar kaydedilirken hata: {e}")


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
# BOT HAZIR OLDUĞUNDA
# =========================================================

@bot.event
async def on_ready():

    yukle()

    for g in bot.guilds:

        SET.setdefault(
            g.id,
            {
                "name": g.name,
                "otorol_id": "",
                "hosgeldin_kanal_id": "",
                "log_kanal_id": ""
            }
        )

        SET[g.id]["name"] = g.name

    kaydet()

    try:
        await bot.tree.sync()

        print("✅ Tüm komutlar başarıyla senkronize edildi!")

    except Exception as e:

        print(f"❌ Sync hatası: {e}")

    print(f"🤖 Bot aktif: {bot.user}")
    print(f"📡 Discord bağlantısı hazır.")
    print("--------------------------------------------------")
    print("🌐 GELİŞMİŞ BOT KONTROL PANELİ AKTİF")
    print("🛡️ OTOMATİK RECONNECT SİSTEMİ AKTİF")
    print("💓 WATCHDOG SİSTEMİ AKTİF")
    print("--------------------------------------------------")


# =========================================================
# MESAJ DİNLEYİCİ
# =========================================================

@bot.event
async def on_message(message):

    if not message.author.bot:

        if message.content.strip().lower() == "sa":

            try:
                await message.channel.send(
                    f"Aleykümselam {message.author.mention}"
                )

            except Exception:
                pass

    await bot.process_commands(message)


# =========================================================
# YETKİ KONTROL
# =========================================================

def yetki_kontrol(interaction, perm):

    return getattr(
        interaction.user.guild_permissions,
        perm,
        False
    )


async def hata_mesaji(interaction, metin):

    if interaction.response.is_done():

        await interaction.followup.send(
            f"❌ {metin}",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            f"❌ {metin}",
            ephemeral=True
        )


# =========================================================
# PANEL KOMUTU
# =========================================================

@bot.tree.command(
    name="panel",
    description="Web kontrol paneli linkini gönderir."
)
async def panel(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🌐 Gelişmiş Bot Kontrol Paneli",
        description=(
            "Sunucu ayarlarını yönetmek için panel:\n"
            "https://discord-bot-fa6e.onrender.com/"
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
    description="Sunucudaki aktif bot komutlarını gösterir."
)
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
            "**/panel** - Web panelini gösterir.\n"
            "**/sunucu-kur** - Sunucu yapısını kurar.\n"
            "**/sil** - Mesajları temizler.\n"
            "**/kanalayazmaerişimi** - Roller için yazma izni ayarlar.\n"
            "**/mute** - Kullanıcıya zaman aşımı uygular.\n"
            "**/unmute** - Zaman aşımını kaldırır.\n"
            "**/yavaşmod** - Kanalın yavaş modunu ayarlar.\n"
            "**/kanalgörünülürlük** - Kanal görünürlüğünü ayarlar."
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# ROL DEĞİŞİKLİĞİ LOG
# =========================================================

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

    try:
        log_kanali = guild.get_channel(
            int(log_kanal_id)
        )
    except Exception:
        return

    if not log_kanali:
        return

    islem_yapan = "Bilinmiyor / Otomatik"

    try:

        async for entry in guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.member_role_update
        ):

            if entry.target.id == after.id:

                islem_yapan = entry.user.mention
                break

    except Exception:
        pass

    eklenen_roller = [
        r for r in after.roles
        if r not in before.roles
    ]

    alinan_roller = [
        r for r in before.roles
        if r not in after.roles
    ]

    for rol in eklenen_roller:

        embed = discord.Embed(
            title="✅ Rol Verildi",
            color=0x57F287,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        embed.add_field(
            name="Rol Verilen Kullanıcı",
            value=after.mention,
            inline=False
        )

        embed.add_field(
            name="Verilen Rol",
            value=rol.mention,
            inline=False
        )

        embed.add_field(
            name="Rolü Veren",
            value=islem_yapan,
            inline=False
        )

        try:
            await log_kanali.send(embed=embed)
        except Exception:
            pass

    for rol in alinan_roller:

        embed = discord.Embed(
            title="⚠️ Rol Alındı",
            color=0xED4245,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        embed.add_field(
            name="Rolü Alınan Kullanıcı",
            value=after.mention,
            inline=False
        )

        embed.add_field(
            name="Alınan Rol",
            value=rol.name,
            inline=False
        )

        embed.add_field(
            name="Rolü Alan",
            value=islem_yapan,
            inline=False
        )

        try:
            await log_kanali.send(embed=embed)
        except Exception:
            pass


# =========================================================
# SUNUCU KUR
# =========================================================

@bot.tree.command(
    name="sunucu-kur",
    description="Tüm kategorileri ve kanalları tek seferde kurar."
)
async def sunucu_kur(interaction: discord.Interaction):

    if not yetki_kontrol(
        interaction,
        "manage_channels"
    ):

        return await hata_mesaji(
            interaction,
            "Kanal yönetme yetkiniz yok!"
        )

    await interaction.response.defer()

    guild = interaction.guild

    try:

        kat1 = await guild.create_category(
            "「📌」Önemli"
        )

        for isim in [
            "❓biz-kimiz",
            "❓görevlerimiz",
            "⬛kara-liste",
            "🚪gelen-giden",
            "👔kılık-kıyafet"
        ]:

            await guild.create_text_channel(
                isim,
                category=kat1
            )

        kat2 = await guild.create_category(
            "「📢」Duyuru"
        )

        for isim in [
            "📢personel-duyuru",
            "📢aktiflik-duyuru",
            "📢operasyon-duyuru",
            "📜kararname",
            "📋hiyerarşi"
        ]:

            await guild.create_text_channel(
                isim,
                category=kat2
            )

        kat3 = await guild.create_category(
            "「🗨」Sohbet Kanalları"
        )

        for isim in [
            "🗨sohbet",
            "📸galeri-kanalı",
            "🤖bot-komut",
            "🤔öneri-istek",
            "📤i̇stifa-i̇zin",
            "😴inaktiflik-izin"
        ]:

            await guild.create_text_channel(
                isim,
                category=kat3
            )

        kat4 = await guild.create_category(
            "「🧾」Kayıtlar"
        )

        for isim in [
            "🧾alım-logs",
            "🧾alım-sistemi",
            "🧾eğitim-logs",
            "🧾eğitim-sistemi"
        ]:

            await guild.create_text_channel(
                isim,
                category=kat4
            )

        await interaction.followup.send(
            "✅ **Sistem başarıyla kuruldu!** "
            "Tüm kategoriler ve kanallar oluşturuldu."
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Kurulum sırasında hata oluştu: {e}"
        )


# =========================================================
# SİL
# =========================================================

@bot.tree.command(
    name="sil",
    description="Belirtilen miktarda mesajı temizler."
)
@app_commands.describe(
    limit="Silinecek mesaj sayısı"
)
async def sil(
    interaction: discord.Interaction,
    limit: int = 5
):

    if not yetki_kontrol(
        interaction,
        "manage_messages"
    ):

        return await hata_mesaji(
            interaction,
            "Mesajları yönet yetkiniz bulunmuyor."
        )

    if limit < 1 or limit > 100:

        return await hata_mesaji(
            interaction,
            "Mesaj sayısı 1 ile 100 arasında olmalıdır."
        )

    await interaction.response.defer(
        ephemeral=True
    )

    silinenler = await interaction.channel.purge(
        limit=limit
    )

    await interaction.followup.send(
        f"🧹 Başarıyla {len(silinenler)} mesaj silindi.",
        ephemeral=True
    )


# =========================================================
# KANALA YAZMA ERİŞİMİ
# =========================================================

@bot.tree.command(
    name="kanalayazmaerişimi",
    description="Birden fazla rolün kanala yazma iznini ayarlar."
)
@app_commands.describe(
    durum="True: Yazabilsin, False: Yazamasın",
    rol1="1. Rol",
    rol2="2. Rol",
    rol3="3. Rol",
    rol4="4. Rol",
    rol5="5. Rol",
    rol6="6. Rol",
    rol7="7. Rol",
    rol8="8. Rol",
    rol9="9. Rol",
    rol10="10. Rol"
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

    if not yetki_kontrol(
        interaction,
        "manage_channels"
    ):

        return await hata_mesaji(
            interaction,
            "Kanalları yönet yetkiniz yok."
        )

    roller = [
        r for r in [
            rol1,
            rol2,
            rol3,
            rol4,
            rol5,
            rol6,
            rol7,
            rol8,
            rol9,
            rol10
        ]
        if r is not None
    ]

    if not roller:

        return await hata_mesaji(
            interaction,
            "En az bir rol seçmelisiniz."
        )

    rol_isimleri = []

    for r in roller:

        await interaction.channel.set_permissions(
            r,
            send_messages=durum
        )

        rol_isimleri.append(r.name)

    durum_metni = (
        "açıldı ✍️"
        if durum
        else
        "kapatıldı 🚫"
    )

    liste_str = ", ".join(
        f"**{name}**"
        for name in rol_isimleri
    )

    await interaction.response.send_message(
        f"⚙️ İşlem tamamlandı. "
        f"{liste_str} rollerinin bu kanala mesaj yazma izni "
        f"**{durum_metni}**."
    )


# =========================================================
# MUTE
# =========================================================

@bot.tree.command(
    name="mute",
    description="Kullanıcıya belirtilen süre kadar zaman aşımı uygular."
)
@app_commands.describe(
    üye="Susturulacak üye",
    saat="Süre (saat)",
    sebep="Susturma sebebi"
)
async def mute(
    interaction: discord.Interaction,
    üye: discord.Member,
    saat: int = 1,
    sebep: str = "Belirtilmedi"
):

    if not yetki_kontrol(
        interaction,
        "moderate_members"
    ):

        return await hata_mesaji(
            interaction,
            "Üyeleri susturma yetkiniz yok."
        )

    if saat < 1:

        return await hata_mesaji(
            interaction,
            "Süre en az 1 saat olmalıdır."
        )

    await üye.timeout(
        datetime.timedelta(hours=saat),
        reason=sebep
    )

    await interaction.response.send_message(
        f"🔇 **{üye.name}** adlı kullanıcı "
        f"**{saat} saat** süreyle susturuldu.\n"
        f"📝 Sebep: `{sebep}`"
    )


# =========================================================
# UNMUTE
# =========================================================

@bot.tree.command(
    name="unmute",
    description="Kullanıcının zaman aşımını kaldırır."
)
@app_commands.describe(
    üye="Susturması kaldırılacak üye"
)
async def unmute(
    interaction: discord.Interaction,
    üye: discord.Member
):

    if not yetki_kontrol(
        interaction,
        "moderate_members"
    ):

        return await hata_mesaji(
            interaction,
            "Yetkiniz yok."
        )

    await üye.timeout(None)

    await interaction.response.send_message(
        f"🔊 **{üye.name}** adlı kullanıcının "
        f"susturması kaldırıldı."
    )


# =========================================================
# YAVAŞ MOD
# =========================================================

@bot.tree.command(
    name="yavaşmod",
    description="Kanal için yavaş mod süresini ayarlar."
)
@app_commands.describe(
    saniye="Saniye cinsinden süre. 0 kapatır."
)
async def yavaşmod(
    interaction: discord.Interaction,
    saniye: int
):

    if not yetki_kontrol(
        interaction,
        "manage_channels"
    ):

        return await hata_mesaji(
            interaction,
            "Kanalı yönet yetkiniz yok."
        )

    if saniye < 0 or saniye > 21600:

        return await hata_mesaji(
            interaction,
            "Süre 0 ile 21600 saniye arasında olmalıdır."
        )

    await interaction.channel.edit(
        slowmode_delay=saniye
    )

    if saniye == 0:

        await interaction.response.send_message(
            "⏳ Yavaş mod tamamen kapatıldı."
        )

    else:

        await interaction.response.send_message(
            f"⏳ Yavaş mod **{saniye} saniye** olarak ayarlandı."
        )


# =========================================================
# KANAL GÖRÜNÜRLÜĞÜ
# =========================================================

@bot.tree.command(
    name="kanalgörünülürlük",
    description="Rollerin kanalı görüp görmeyeceğini ayarlar."
)
@app_commands.describe(
    rol1="1. Rol",
    görünürlük="True: Görebilsin, False: Gizlensin",
    rol2="2. Rol",
    rol3="3. Rol",
    rol4="4. Rol"
)
async def kanalgörünülürlük(
    interaction: discord.Interaction,
    rol1: discord.Role,
    görünürlük: bool,
    rol2: discord.Role = None,
    rol3: discord.Role = None,
    rol4: discord.Role = None
):

    if not yetki_kontrol(
        interaction,
        "manage_channels"
    ):

        return await hata_mesaji(
            interaction,
            "Kanalları yönet yetkiniz yok."
        )

    roller = [
        r for r in [
            rol1,
            rol2,
            rol3,
            rol4
        ]
        if r is not None
    ]

    rol_isimleri = []

    for r in roller:

        await interaction.channel.set_permissions(
            r,
            view_channel=görünürlük
        )

        rol_isimleri.append(r.name)

    islem_metni = (
        "görebilecek"
        if görünürlük
        else
        "göremeyecek"
    )

    liste_str = ", ".join(
        f"**{name}**"
        for name in rol_isimleri
    )

    await interaction.response.send_message(
        f"👁️ {liste_str} rolleri artık kanalı "
        f"**{islem_metni}**."
    )


# =========================================================
# ÜYE GİRİŞİ
# =========================================================

@bot.event
async def on_member_join(member):

    yukle()

    s = SET.get(
        member.guild.id,
        {}
    )

    if s.get("otorol_id"):

        try:

            rol = member.guild.get_role(
                int(s["otorol_id"])
            )

            if rol:

                await member.add_roles(rol)

        except Exception:
            pass

    if s.get("hosgeldin_kanal_id"):

        try:

            kanal = member.guild.get_channel(
                int(s["hosgeldin_kanal_id"])
            )

            if kanal:

                await kanal.send(
                    f"Hoş geldin {member.mention}! "
                    f"Seninle birlikte "
                    f"**{member.guild.member_count}** kişi olduk."
                )

        except Exception:
            pass


# =========================================================
# FLASK PANELİ
# =========================================================

app = Flask(__name__)


LOGIN_H = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Güvenli Giriş</title>

<style>
body{
background:#1e1f22;
color:#fff;
font-family:sans-serif;
display:flex;
justify-content:center;
align-items:center;
height:100vh;
margin:0;
}

.box{
background:#2b2d31;
padding:40px;
border-radius:12px;
width:320px;
text-align:center;
box-shadow:0 8px 24px rgba(0,0,0,0.5);
}

input,button{
width:100%;
padding:12px;
margin:12px 0;
background:#1e1f22;
color:#fff;
border:1px solid #444;
border-radius:6px;
box-sizing:border-box;
font-size:16px;
}

button{
background:#5865f2;
font-weight:bold;
cursor:pointer;
}

.err{
color:#ed4245;
font-size:14px;
margin-bottom:10px;
}
</style>
</head>

<body>

<div class="box">

<h2>🛡️ Güvenli Panel</h2>

{% if error %}
<p class="err">{{error}}</p>
{% endif %}

<form method="POST">

<input
type="password"
name="password"
placeholder="Şifrenizi Girin"
required
>

<button type="submit">
Sisteme Bağlan
</button>

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

<title>Ultra Panel</title>

<style>

body{
background:#1e1f22;
color:#fff;
font-family:sans-serif;
padding:30px;
}

.box{
ma
