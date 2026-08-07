import discord
import json
import os
import datetime
import threading

from discord.ext import commands
from discord import app_commands
from flask import Flask, render_template_string, request, redirect, url_for


# =========================================================
# AYARLAR
# =========================================================

DOSYA = "ayarlar.json"

# Render Environment Variables
TOKEN = os.environ.get("TOKEN")
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "2904")

PANEL_URL = "https://discord-bot-fa6e.onrender.com/"

SET = {}


# =========================================================
# JSON SİSTEMİ
# =========================================================

def varsayilan_ayarlar(guild):
    return {
        "name": guild.name,
        "otorol_id": "",
        "hosgeldin_kanal_id": "",
        "log_kanal_id": ""
    }


def yukle():
    global SET

    if not os.path.exists(DOSYA):
        SET = {}
        return

    try:
        with open(DOSYA, "r", encoding="utf-8") as f:
            data = json.load(f)

        SET = {
            int(k): v
            for k, v in data.items()
        }

    except Exception as e:
        print(f"⚠️ Ayarlar yüklenemedi: {e}")
        SET = {}


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
        print(f"⚠️ Ayarlar kaydedilemedi: {e}")


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
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    yukle()

    for guild in bot.guilds:

        SET.setdefault(
            guild.id,
            varsayilan_ayarlar(guild)
        )

        SET[guild.id]["name"] = guild.name

    kaydet()

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ {len(synced)} slash komutu senkronize edildi."
        )

    except Exception as e:

        print(
            f"❌ Slash komut senkronizasyon hatası: {e}"
        )

    print("--------------------------------------------------")
    print(f"🤖 Bot aktif: {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print("🔄 Discord bağlantısı hazır.")
    print("🌐 Web paneli hazır.")
    print("--------------------------------------------------")


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

        except Exception as e:

            print(
                f"⚠️ SA mesajı gönderilemedi: {e}"
            )

    await bot.process_commands(message)


# =========================================================
# YETKİ SİSTEMİ
# =========================================================

def yetki_kontrol(interaction, perm):

    return bool(
        getattr(
            interaction.user.guild_permissions,
            perm,
            False
        )
    )


async def hata_mesaji(interaction, metin):

    try:

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

    except Exception as e:

        print(
            f"⚠️ Hata mesajı gönderilemedi: {e}"
        )


# =========================================================
# PANEL KOMUTU
# =========================================================

@bot.tree.command(
    name="panel",
    description="Web kontrol panelini gönderir."
)
async def panel(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🌐 Gelişmiş Bot Kontrol Paneli",
        description=(
            "Sunucu ayarlarını yönetmek için panel:\n\n"
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
    description="Botun aktif komutlarını gösterir."
)
async def komutlar(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📜 Bot Komut Listesi",
        description="Aktif yönetim komutları:",
        color=0x5865F2
    )

    embed.add_field(
        name="🛠️ Yönetim",
        value=(
            "**/komutlar** — Komut listesini gösterir.\n"
            "**/panel** — Web kontrol panelini açar.\n"
            "**/sunucu-kur** — Sunucu kategorilerini oluşturur.\n"
            "**/sil** — Mesajları temizler.\n"
            "**/kanalayazma** — Roller için yazma izni ayarlar.\n"
            "**/mute** — Kullanıcıya zaman aşımı uygular.\n"
            "**/unmute** — Zaman aşımını kaldırır.\n"
            "**/yavasmod** — Kanalın yavaş modunu ayarlar.\n"
            "**/kanalgorunurluk** — Roller için kanal görünürlüğünü ayarlar."
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# ROL LOG SİSTEMİ
# =========================================================

@bot.event
async def on_member_update(before, after):

    if before.roles == after.roles:
        return

    guild = after.guild

    yukle()

    settings = SET.get(
        guild.id,
        {}
    )

    log_id = settings.get(
        "log_kanal_id"
    )

    if not log_id:
        return

    try:

        log_channel = guild.get_channel(
            int(log_id)
        )

    except Exception:

        return

    if not log_channel:
        return

    executor = "Bilinmiyor / Otomatik"

    try:

        async for entry in guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.member_role_update
        ):

            if (
                entry.target
                and entry.target.id == after.id
            ):

                executor = entry.user.mention
                break

    except Exception:

        pass

    added_roles = [
        role
        for role in after.roles
        if role not in before.roles
    ]

    removed_roles = [
        role
        for role in before.roles
        if role not in after.roles
    ]

    # VERİLEN ROLLER

    for role in added_roles:

        embed = discord.Embed(
            title="✅ Rol Verildi",
            color=0x57F287,
            timestamp=datetime.datetime.now(
                datetime.timezone.utc
            )
        )

        embed.add_field(
            name="Kullanıcı",
            value=after.mention,
            inline=False
        )

        embed.add_field(
            name="Verilen Rol",
            value=role.mention,
            inline=False
        )

        embed.add_field(
            name="İşlemi Yapan",
            value=executor,
            inline=False
        )

        try:

            await log_channel.send(
                embed=embed
            )

        except Exception:

            pass

    # ALINAN ROLLER

    for role in removed_roles:

        embed = discord.Embed(
            title="⚠️ Rol Alındı",
            color=0xED4245,
            timestamp=datetime.datetime.now(
                datetime.timezone.utc
            )
        )

        embed.add_field(
            name="Kullanıcı",
            value=after.mention,
            inline=False
        )

        embed.add_field(
            name="Alınan Rol",
            value=role.name,
            inline=False
        )

        embed.add_field(
            name="İşlemi Yapan",
            value=executor,
            inline=False
        )

        try:

            await log_channel.send(
                embed=embed
            )

        except Exception:

            pass


# =========================================================
# SUNUCU KUR
# =========================================================

@bot.tree.command(
    name="sunucu-kur",
    description="Sunucu kategorilerini ve kanallarını oluşturur."
)
async def sunucu_kur(
    interaction: discord.Interaction
):

    if not yetki_kontrol(
        interaction,
        "manage_channels"
    ):

        return await hata_mesaji(
            interaction,
            "Kanal yönetme yetkiniz yok."
        )

    await interaction.response.defer()

    guild = interaction.guild

    if guild is None:

        return await interaction.followup.send(
            "❌ Bu komut sadece sunucuda kullanılabilir."
        )

    kategoriler = [

        (
            "「📌」Önemli",
            [
                "❓biz-kimiz",
                "❓görevlerimiz",
                "⬛kara-liste",
                "🚪gelen-giden",
                "👔kılık-kıyafet"
            ]
        ),

        (
            "「📢」Duyuru",
            [
                "📢personel-duyuru",
                "📢aktiflik-duyuru",
                "📢operasyon-duyuru",
                "📜kararname",
                "📋hiyerarşi"
            ]
        ),

        (
            "「🗨」Sohbet Kanalları",
            [
                "🗨sohbet",
                "📸galeri-kanalı",
                "🤖bot-komut",
                "🤔öneri-istek",
                "📤i̇stifa-i̇zin",
                "😴inaktiflik-izin"
            ]
        ),

        (
            "「🧾」Kayıtlar",
            [
                "🧾alım-logs",
                "🧾alım-sistemi",
                "🧾eğitim-logs",
                "🧾eğitim-sistemi"
            ]
        )

    ]

    created = 0

    try:

        for category_name, channels in kategoriler:

            category = await guild.create_category(
                category_name
            )

            for channel_name in channels:

                await guild.create_text_channel(
                    channel_name,
                    category=category
                )

                created += 1

        await interaction.followup.send(
            "✅ **Sunucu kurulumu tamamlandı!**\n\n"
            f"📁 Kategori: **{len(kategoriler)}**\n"
            f"📋 Kanal: **{created}**"
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Botun kanal/kategori oluşturma yetkisi yok."
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Kurulum hatası:\n`{e}`"
        )


# =========================================================
# SİL
# =========================================================

@bot.tree.command(
    name="sil",
    description="Mesajları temizler."
)
@app_commands.describe(
    limit="1 ile 100 arasında mesaj sayısı"
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
            "Mesajları yönetme yetkiniz yok."
        )

    if limit < 1 or limit > 100:

        return await hata_mesaji(
            interaction,
            "Mesaj sayısı 1 ile 100 arasında olmalıdır."
        )

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        deleted = await interaction.channel.purge(
            limit=limit
        )

        await interaction.followup.send(
            f"🧹 **{len(deleted)}** mesaj silindi.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Botun mesaj silme yetkisi yok.",
            ephemeral=True
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Hata: `{e}`",
            ephemeral=True
        )


# =========================================================
# KANALA YAZMA
# =========================================================

@bot.tree.command(
    name="kanalayazma",
    description="Rollerin kanala yazma iznini ayarlar."
)
@app_commands.describe(
    durum="True: yazabilsin / False: yazamasın",
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
async def kanalayazma(
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
            "Kanalları yönetme yetkiniz yok."
        )

    roller = [
        role
        for role in [
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
        if role is not None
    ]

    if not roller:

        return await hata_mesaji(
            interaction,
            "En az bir rol seçmelisiniz."
        )

    try:

        for role in roller:

            await interaction.channel.set_permissions(
                role,
                send_messages=durum
            )

        names = ", ".join(
            f"**{role.name}**"
            for role in roller
        )

        status = (
            "açıldı ✍️"
            if durum
            else
            "kapatıldı 🚫"
        )

        await interaction.response.send_message(
            f"⚙️ {names} rollerinin yazma izni "
            f"**{status}**."
        )

    except discord.Forbidden:

        await hata_mesaji(
            interaction,
            "Botun kanal izinlerini değiştirme yetkisi yok."
        )

    except Exception as e:

        await hata_mesaji(
            interaction,
            f"İşlem başarısız: `{e}`"
        )


# =========================================================
# MUTE
# =========================================================

@bot.tree.command(
    name="mute",
    description="Kullanıcıya zaman aşımı uygular."
)
@app_commands.describe(
    uye="Susturulacak üye",
    saat="Süre (saat)",
    sebep="Susturma sebebi"
)
async def mute(
    interaction: discord.Interaction,
    uye: discord.Member,
    saat: int = 1,
    sebep: str = "Belirtilmedi"
):

    if not yetki_kontrol(
        interaction,
        "moderate_members"
    ):

        return await hata_mesaji(
            interaction,
            "Üyeleri zaman aşımına alma yetkiniz yok."
        )

    if saat < 1 or saat > 672:

        return await hata_mesaji(
            interaction,
            "Süre 1 ile 672 saat arasında olmalıdır."
        )

    try:

        await uye.timeout(
            datetime.timedelta(hours=saat),
            reason=sebep
        )

        await interaction.response.send_message(
            f"🔇 **{uye.display_name}** adlı kullanıcı "
            f"**{saat} saat** susturuldu.\n"
            f"📝 Sebep: `{sebep}`"
        )

    except discord.Forbidden:

        await hata_mesaji(
            interaction,
            "Bu kullanıcıya zaman aşımı uygulayamıyorum."
        )

    except Exception as e:

        await hata_mesaji(
            interaction,
            f"Hata: `{e}`"
        )


# =========================================================
# UNMUTE
# =========================================================

@bot.tree.command(
    name="unmute",
    description="Kullanıcının zaman aşımını kaldırır."
)
@app_commands.describe(
    uye="Susturması kaldırılacak üye"
)
async def unmute(
    interaction: discord.Interaction,
    uye: discord.Member
):

    if not yetki_kontrol(
        interaction,
        "moderate_members"
    ):

        return await hata_mesaji(
            interaction,
            "Üyeleri yönetme yetkiniz yok."
        )

    try:

        await uye.timeout(None)

        await interaction.response.send_message(
            f"🔊 **{uye.display_name}** adlı kullanıcının "
            "susturması kaldırıldı."
        )

    except discord.Forbidden:

        await hata_mesaji(
            interaction,
            "Bu kullanıcının zaman aşımını kaldıramıyorum."
        )

    except Exception as e:

        await hata_mesaji(
            interaction,
            f"Hata: `{e}`"
        )


# =========================================================
# YAVAŞ MOD
# =========================================================

@bot.tree.command(
    name="yavasmod",
    description="Kanalın yavaş modunu ayarlar."
)
@app_commands.describe(
    saniye="0 ile 21600 arasında saniye. 0 kapatır."
)
async def yavasmod(
    interaction: discord.Interaction,
    saniye: int
):

    if not yetki_kontrol(
        interaction,
        "manage_channels"
    ):

        return await hata_mesaji(
            interaction,
            "Kanalı yönetme yetkiniz yok."
        )

    if saniye < 0 or saniye > 21600:

        return await hata_mesaji(
            interaction,
            "Süre 0 ile 21600 saniye arasında olmalıdır."
        )

    try:

        await interaction.channel.edit(
            slowmode_delay=saniye
        )

        if saniye == 0:

            await interaction.response.send_message(
                "⏳ Yavaş mod kapatıldı."
            )

        else:

            await interaction.response.send_message(
                f"⏳ Yavaş mod **{saniye} saniye** olarak ayarlandı."
            )

    except discord.Forbidden:

        await hata_mesaji(
            interaction,
            "Botun kanal yönetme yetkisi yok."
        )

    except Exception as e:

        await hata_mesaji(
            interaction,
            f"Hata: `{e}`"
        )


# =========================================================
# KANAL GÖRÜNÜRLÜĞÜ
# =========================================================

@bot.tree.command(
    name="kanalgorunurluk",
    description="Rollerin kanal görünürlüğünü ayarlar."
)
@app_commands.describe(
    rol1="1. Rol",
    gorunurluk="True: görebilsin / False: gizlensin",
    rol2="2. Rol",
    rol3="3. Rol",
    rol4="4. Rol"
)
async def kanalgorunurluk(
    interaction: discord.Interaction,
    rol1: discord.Role,
    gorunurluk: bool,
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
            "Kanalları yönetme yetkiniz yok."
        )

    roller = [
        role
        for role in [
            rol1,
            rol2,
            rol3,
            rol4
        ]
        if role is not None
    ]

    try:

        for role in roller:

            await interaction.channel.set_permissions(
                role,
                view_channel=gorunurluk
            )

        names = ", ".join(
            f"**{role.name}**"
            for role in roller
        )

        status = (
            "görebilecek"
            if gorunurluk
            else
            "göremeyecek"
        )

        await interaction.response.send_message(
            f"👁️ {names} rolleri artık kanalı "
            f"*
