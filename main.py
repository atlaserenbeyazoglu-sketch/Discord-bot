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

# JSON ile Flask/Discord aynı anda çalıştığı için kilit
SET_LOCK = threading.RLock()

# Render Environment Variables
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "2904")

# Render kendi adresini otomatik kullanır
PANEL_URL = os.environ.get(
    "RENDER_EXTERNAL_URL",
    "http://127.0.0.1:10000"
)


# =========================================================
# VARSAYILAN SUNUCU AYARLARI
# =========================================================

def varsayilan_ayarlar(guild=None):
    return {
        "name": guild.name if guild else "",
        "otorol_id": "",
        "hosgeldin_kanal_id": "",
        "log_kanal_id": ""
    }


# =========================================================
# JSON YÜKLEME
# =========================================================

def yukle():
    global SET

    if not os.path.exists(DOSYA):
        return

    try:
        with open(DOSYA, "r", encoding="utf-8") as f:
            data = json.load(f)

        with SET_LOCK:
            SET = {
                int(k): v
                for k, v in data.items()
            }

    except Exception as e:
        print(f"⚠️ Ayarlar yüklenirken hata: {e}")


# =========================================================
# JSON KAYDETME
# =========================================================

def kaydet():
    try:
        with SET_LOCK:

            gecici_dosya = DOSYA + ".tmp"

            with open(
                gecici_dosya,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    SET,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

            # Dosyanın yarım kalmasını engeller
            os.replace(
                gecici_dosya,
                DOSYA
            )

    except Exception as e:
        print(f"⚠️ Ayarlar kaydedilirken hata: {e}")


# Başlangıçta ayarları yükle
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

    with SET_LOCK:

        for guild in bot.guilds:

            SET.setdefault(
                guild.id,
                varsayilan_ayarlar(guild)
            )

            SET[guild.id]["name"] = guild.name

    kaydet()

    try:

        await bot.tree.sync()

        print(
            "✅ Slash komutları başarıyla senkronize edildi."
        )

    except Exception as e:

        print(
            f"❌ Slash komut sync hatası: {e}"
        )

    print(
        f"🤖 Bot aktif: {bot.user} | ID: {bot.user.id}"
    )

    print(
        f"📡 Bağlı sunucu sayısı: {len(bot.guilds)}"
    )

    print(
        "--------------------------------------------------"
    )

    print(
        "🌐 WEB PANELİ AKTİF"
    )

    print(
        "🔄 AUTO RECONNECT AKTİF"
    )

    print(
        "💓 WATCHDOG AKTİF"
    )

    print(
        "🛡️ HEALTH CHECK AKTİF"
    )

    print(
        "--------------------------------------------------"
    )


# =========================================================
# MESAJ DİNLEYİCİ
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
# YETKİ KONTROL
# =========================================================

def yetki_kontrol(
    interaction,
    perm
):

    return bool(
        getattr(
            interaction.user.guild_permissions,
            perm,
            False
        )
    )


# =========================================================
# HATA MESAJI
# =========================================================

async def hata_mesaji(
    interaction,
    metin
):

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

    except Exception:
        pass


# =========================================================
# PANEL KOMUTU
# =========================================================

@bot.tree.command(
    name="panel",
    description="Web kontrol panelini açar."
)
async def panel(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🌐 Gelişmiş Bot Kontrol Paneli",
        description=(
            "Sunucu ayarlarını yönetmek için panel:\n"
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
    description="Sunucudaki bot komutlarını gösterir."
)
async def komutlar(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="📜 Bot Komut Listesi",
        description=(
            "Aşağıdan mevcut bot komutlarını "
            "inceleyebilirsin:"
        ),
        color=0x5865F2
    )

    embed.add_field(
        name="🛠️ Yönetim ve Moderasyon",
        value=(
            "**/komutlar** - Komut listesini gösterir.\n"
            "**/panel** - Web panelini açar.\n"
            "**/sunucu-kur** - Sunucu yapısını kurar.\n"
            "**/sil** - Mesajları temizler.\n"
            "**/kanalayazmaerişimi** - Rol yazma izinlerini ayarlar.\n"
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
# ROL DEĞİŞİKLİĞİ LOG SİSTEMİ
# =========================================================

@bot.event
async def on_member_update(
    before,
    after
):

    if before.roles == after.roles:
        return

    with SET_LOCK:

        s = dict(
            SET.get(
                after.guild.id,
                {}
            )
        )

    log_kanal_id = s.get(
        "log_kanal_id"
    )

    if not log_kanal_id:
        return

    try:

        log_kanali = after.guild.get_channel(
            int(log_kanal_id)
        )

    except (
        ValueError,
        TypeError
    ):

        return

    if not log_kanali:
        return

    islem_yapan = (
        "Bilinmiyor / Otomatik"
    )

    try:

        async for entry in after.guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.member_role_update
        ):

            if (
                entry.target
                and
                entry.target.id == after.id
            ):

                islem_yapan = (
                    entry.user.mention
                )

                break

    except Exception:
        pass

    eklenen_roller = [
        rol
        for rol in after.roles
        if rol not in before.roles
    ]

    alinan_roller = [
        rol
        for rol in before.roles
        if rol not in after.roles
    ]

    # -------------------------
    # ROL VERİLDİ
    # -------------------------

    for rol in eklenen_roller:

        embed = discord.Embed(
            title="✅ Rol Verildi",
            color=0x57F287,
            timestamp=datetime.datetime.now(
                datetime.timezone.utc
            )
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

            await log_kanali.send(
                embed=embed
            )

        except Exception:
            pass

    # -------------------------
    # ROL ALINDI
    # -------------------------

    for rol in alinan_roller:

        embed = discord.Embed(
            title="⚠️ Rol Alındı",
            color=0xED4245,
            timestamp=datetime.datetime.now(
                datetime.timezone.utc
            )
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

            await log_kanali.send(
                embed=embed
            )

        except Exception:
            pass


# =========================================================
# SUNUCU KUR
# =========================================================

@bot.tree.command(
    name="sunucu-kur",
    description="Kategorileri ve kanalları oluşturur."
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
            "Kanal yönetme yetkiniz yok!"
        )

    await interaction.response.defer()

    guild = interaction.guild

    if guild is None:

        return await interaction.followup.send(
            "❌ Bu komut sadece sunucularda kullanılabilir."
        )

    try:

        yapilar = [

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

        for kategori_adi, kanallar in yapilar:

            kategori = await guild.create_category(
                kategori_adi
            )

            for kanal_adi in kanallar:

                await guild.create_text_channel(
                    kanal_adi,
                    category=kategori
                )

        await interaction.followup.send(
            "✅ **Sistem başarıyla kuruldu!**\n"
            "Tüm kategoriler ve kanallar oluşturuldu."
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Botun kategori veya kanal oluşturma yetkisi yok."
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Kurulum sırasında hata oluştu:\n`{e}`"
        )


# =========================================================
# MESAJ SİL
# =========================================================

@bot.tree.command(
    name="sil",
    description="Belirtilen miktarda mesajı temizler."
)
@app_commands.describe(
    limit="Silinecek mesaj sayısı (1-100)"
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

    if not 1 <= limit <= 100:

        return await hata_mesaji(
            interaction,
            "Mesaj sayısı 1 ile 100 arasında olmalıdır."
        )

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        silinenler = await interaction.channel.purge(
            limit=limit
        )

        await interaction.followup.send(
            f"🧹 Başarıyla **{len(silinenler)}** mesaj silindi.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Botun mesaj silme yetkisi yok.",
            ephemeral=True
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ İşlem başarısız: `{e}`",
            ephemeral=True
        )


# =========================================================
# KANALA YAZMA ERİŞİMİ
# =========================================================

@bot.tree.command(
    name="kanalayazmaerişimi",
    description="Rollerin kanala yazma iznini ayarlar."
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
        r
        for r in [
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

    try:

        for rol in roller:

            await interaction.channel.set_permissions(
                rol,
                send_messages=durum
            )

        isimler = ", ".join(
            f"**{r.name}**"
            for r in roller
        )

        durum_metni = (
            "açıldı ✍️"
            if durum
            else
            "kapatıldı 🚫"
        )

        await interaction.response.send_message(
            f"⚙️ {isimler} rollerinin "
            f"yazma izni **{durum_metni}**."
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

    if not 1 <= saat <= 672:

        return await hata_mesaji(
            interaction,
            "Süre 1 ile 672 saat arasında olmalıdır."
        )

    try:

        await üye.timeout(
            datetime.timedelta(
                hours=saat
            ),
            reason=sebep
        )

        await interaction.response.send_message(
            f"🔇 **{üye.name}** adlı kullanıcı "
            f"**{saat} saat** süreyle susturuldu.\n"
            f"📝 Sebep: `{sebep}`"
        )

    except discord.Forbidden:

        await hata_mesaji(
            interaction,
            "Bu kullanıcıya zaman aşımı uygulayamıyorum. "
            "Rol hiyerarşisini ve bot yetkilerini kontrol edin."
        )

    except Exception as e:

        await hata_mesaji(
            interaction,
            f"İşlem başarısız: `{e}`"
        )


# =========================================================
#
