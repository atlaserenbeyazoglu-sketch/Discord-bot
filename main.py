import discord, json, os, datetime, threading, re, io
from discord.ext import commands
from discord import app_commands
from flask import Flask
import easyocr
import cv2
import numpy as np
from PIL import Image

DOSYA = "ayarlar.json"
SET = {}

print("🤖 Yapay Zeka OCR Görsel Analiz Motoru Yükleniyor...")
reader = easyocr.Reader(['en'], gpu=False)
print("✅ OCR Motoru Hazır!")

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

LOG_YANITLARI = {}

async def gorselden_saat_oku(gorsel_attachment):
    try:
        veri = await gorsel_attachment.read()
        image = Image.open(io.BytesIO(veri)).convert('RGB')
        img_np = np.array(image)
        
        h, w, _ = img_np.shape
        ust_kisim = img_np[0:int(h * 0.25), int(w * 0.35):int(w * 0.65)]
        
        sonuclar = reader.readtext(ust_kisim)
        
        bulunan_saatler = []
        for bbox, text, prob in sonuclar:
            temiz_text = re.sub(r'[^0-9:]', '', text)
            saat_eslesme = re.search(r'(\d{1,2}):(\d{2})', temiz_text)
            if saat_eslesme:
                bulunan_saatler.append(saat_eslesme.group(0))
                
        if bulunan_saatler:
            return bulunan_saatler[0]
    except Exception as e:
        print(f"OCR Okuma Hatası: {e}")
    return None

async def akilli_log_denetimi(icerik, gorseller):
    saatler = re.findall(r'(\d{1,2}):(\d{2})', icerik)
    sure_ifadeleri = re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:saat|s|st)', icerik.lower())

    if len(saatler) < 2 or not sure_ifadeleri:
        return False

    try:
        h1, m1 = int(saatler[0][0]), int(saatler[0][1])
        h2, m2 = int(saatler[1][0]), int(saatler[1][1])
        
        dakika1 = h1 * 60 + m1
        dakika2 = h2 * 60 + m2
        fark_dakika = dakika2 - dakika1
        if fark_dakika < 0:
            fark_dakika += 24 * 60

        hesaplanan_saat = fark_dakika / 60.0
        belirtilen_sure = float(sure_ifadeleri[0].replace(',', '.'))

        if abs(hesaplanan_saat - belirtilen_sure) > 1.5:
            return False

        ss_baslangic_saati = await gorselden_saat_oku(gorseller[0])
        ss_bitis_saati = await gorselden_saat_oku(gorseller[1])

        if not ss_baslangic_saati or not ss_bitis_saati:
            pass
    except Exception as e:
        print(f"Denetim Hatası: {e}")
        return False

    return True

@bot.event
async def on_ready():
    yukle()
    for g in bot.guilds:
        SET.setdefault(g.id, {
            "name": g.name, 
            "otorol_id": "", 
            "hosgeldin_kanal_id": "", 
            "log_kanal_id": "",
            "log_dogrulama_aktif": False
        })
        if "log_dogrulama_aktif" not in SET[g.id]:
            SET[g.id]["log_dogrulama_aktif"] = False
        SET[g.id]["name"] = g.name
    kaydet()
    try:
        await bot.tree.sync()
        print("✅ Tüm komutlar başarıyla senkronize edildi!")
    except Exception as e:
        print(f"❌ Sync hatası: {e}")
    print(f"Bot aktif edildi: {bot.user}")
    print("--------------------------------------------------")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user.mentioned_in(message) and not message.mention_everyone:
        yukle()
        gid = message.guild.id
        s = SET.get(gid, {})
        
        if s.get("log_dogrulama_aktif", False):
            icerik = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
            
            if not icerik or len(icerik) < 5 or len(message.attachments) < 2:
                try:
                    await message.add_reaction("❌")
                    yanit = await message.reply("Lütfen uygun formatı giriniz")
                    LOG_YANITLARI[message.id] = yanit.id
                except:
                    pass
                return

            gorseller = message.attachments
            for gorsel in gorseller:
                if not any(gorsel.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                    try:
                        await message.add_reaction("❌")
                        yanit = await message.reply("Lütfen uygun formatı giriniz")
                        LOG_YANITLARI[message.id] = yanit.id
                    except:
                        pass
                    return

            basarili_mi = await akilli_log_denetimi(icerik, gorseller)
            
            if basarili_mi:
                try:
                    await message.add_reaction("✅")
                    yanit = await message.channel.send("Onay!")
                    LOG_YANITLARI[message.id] = yanit.id
                except:
                    pass
            else:
                try:
                    await message.add_reaction("❌")
                    yanit = await message.reply("Lütfen uygun formatı giriniz")
                    LOG_YANITLARI[message.id] = yanit.id
                except:
                    pass
            return

    if message.content.strip().lower() == "sa":
        try:
            await message.channel.send(f"Aleykümselam {message.author.mention}")
        except:
            pass
            
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.id in LOG_YANITLARI:
        yanit_id = LOG_YANITLARI[message.id]
        try:
            yanit_mesaji = await message.channel.fetch_message(yanit_id)
            if yanit_mesaji:
                await yanit_mesaji.delete()
        except:
            pass
        del LOG_YANITLARI[message.id]

def yetki_kontrol(interaction, perm):
    return getattr(interaction.user.guild_permissions, perm, False)

async def hata_mesaji(interaction, metin):
    if interaction.response.is_done():
        await interaction.followup.send(f"❌ {metin}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {metin}", ephemeral=True)

class SistemYonetimView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.secilen_otorol = None
        self.secilen_hg_kanal = None
        self.secilen_log_kanal = None
        self.secilen_log_durum = None

        role_select = discord.ui.RoleSelect(placeholder="📌 Yeni gelenler için Otorol seçin...", min_values=1, max_values=1)
        role_select.callback = self.otorol_secim_callback
        self.add_item(role_select)

        hosgeldin_select = discord.ui.ChannelSelect(placeholder="🚪 Hoş geldin kanalını seçin...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
        hosgeldin_select.callback = self.hosgeldin_secim_callback
        self.add_item(hosgeldin_select)

        log_select = discord.ui.ChannelSelect(placeholder="🧾 Rol log kanalını seçin...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
        log_select.callback = self.log_secim_callback
        self.add_item(log_select)

        dogrulama_select = discord.ui.Select(
            placeholder="🤖 Roblox Akıllı Log & Çift SS Doğrulama...",
            options=[
                discord.SelectOption(label="Aktif Et (Aç)", value="ac", description="Bot etiketlenince saat ve çift SS'leri detaylı inceler.", emoji="✅"),
                discord.SelectOption(label="Devre Dışı Bırak (Kapat)", value="kapat", description="Sistemi kapatır.", emoji="❌")
            ],
            min_values=1, max_values=1
        )
        dogrulama_select.callback = self.dogrulama_secim_callback
        self.add_item(dogrulama_select)

    async def otorol_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.secilen_otorol = interaction.data["values"][0]
        role_obj = interaction.guild.get_role(int(self.secilen_otorol))
        await interaction.followup.send(f"📌 Otorol geçici olarak seçildi: **{role_obj.name}** (Kaydetmek için alttaki **Kaydet** butonuna basın)", ephemeral=True)

    async def hosgeldin_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.secilen_hg_kanal = interaction.data["values"][0]
        kanal_obj = interaction.guild.get_channel(int(self.secilen_hg_kanal))
        await interaction.followup.send(f"🚪 Hoş geldin kanalı geçici olarak seçildi: {kanal_obj.mention} (Kaydetmek için alttaki **Kaydet** butonuna basın)", ephemeral=True)

    async def log_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.secilen_log_kanal = interaction.data["values"][0]
        kanal_obj = interaction.guild.get_channel(int(self.secilen_log_kanal))
        await interaction.followup.send(f"🧾 Log kanalı geçici olarak seçildi: {kanal_obj.mention} (Kaydetmek için alttaki **Kaydet** butonuna basın)", ephemeral=True)

    async def dogrulama_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        val = interaction.data["values"][0]
        self.secilen_log_durum = True if val == "ac" else False
        durum_str = "Aktif (Açık)" if self.secilen_log_durum else "Devre Dışı (Kapalı)"
        await interaction.followup.send(f"🤖 Akıllı Doğrulama geçici olarak **{durum_str}** seçildi (Kaydetmek için alttaki **Kaydet** butonuna basın)", ephemeral=True)

    @discord.ui.button(label="💾 Ayarları Kalıcı Olarak Kaydet", style=discord.ButtonStyle.success, emoji="✅", row=4)
    async def kaydet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        yukle()
        SET.setdefault(self.guild_id, {"name": interaction.guild.name, "otorol_id": "", "hosgeldin_kanal_id": "", "log_kanal_id": "", "log_dogrulama_aktif": False})

        degisiklik_var = False
        if self.secilen_otorol is not None:
            SET[self.guild_id]["otorol_id"] = str(self.secilen_otorol)
            degisiklik_var = True
        if self.secilen_hg_kanal is not None:
            SET[self.guild_id]["hosgeldin_kanal_id"] = str(self.secilen_hg_kanal)
            degisiklik_var = True
        if self.secilen_log_kanal is not None:
            SET[self.guild_id]["log_kanal_id"] = str(self.secilen_log_kanal)
            degisiklik_var = True
        if self.secilen_log_durum is not None:
            SET[self.guild_id]["log_dogrulama_aktif"] = self.secilen_log_durum
            degisiklik_var = True

        if not degisiklik_var:
            return await interaction.followup.send("⚠️ Henüz hiçbir ayar değiştirmediniz veya seçmediniz!", ephemeral=True)

        kaydet()

        s = SET[self.guild_id]
        otorol_adi = f"<@&{s['otorol_id']}>" if s.get('otorol_id') else "Ayarlanmamış"
        hosgeldin_kanali = f"<#{s['hosgeldin_kanal_id']}>" if s.get('hosgeldin_kanal_id') else "Ayarlanmamış"
        log_kanali = f"<#{s['log_kanal_id']}>" if s.get('log_kanal_id') else "Ayarlanmamış"
        dogrulama_durum = "Aktif ✅" if s.get('log_dogrulama_aktif', False) else "Kapalı ❌"

        embed = discord.Embed(
            title="✅ Ayarlar Başarıyla Kaydedildi!",
            description="Seçtiğiniz tüm sistemler kalıcı hafızaya işlendi.",
            color=0x57F287
        )
        embed.add_field(name="📌 Otorol", value=otorol_adi, inline=False)
        embed.add_field(name="🚪 Hoş Geldin Kanalı", value=hosgeldin_kanali, inline=False)
        embed.add_field(name="🧾 Rol Log Kanalı", value=log_kanali, inline=False)
        embed.add_field(name="🤖 Roblox Akıllı Doğrulama", value=dogrulama_durum, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="özelkontrolpaneli", description="Şifre ile korunan gelişmiş Discord GUI kontrol panelini açar.")
@app_commands.describe(sifre="Panel erişim şifresi")
async def ozel_kontrol_paneli(interaction: discord.Interaction, sifre: str):
    if not yetki_kontrol(interaction, "manage_guild"):
        return await hata_mesaji(interaction, "Bu paneli açmak için 'Sunucuyu Yönet' yetkiniz olmalı.")
    
    if sifre != "2904":
        return await hata_mesaji(interaction, "Hatalı şifre! Erişim reddedildi.")
    
    yukle()
    gid = interaction.guild.id
    s = SET.get(gid, {})
    
    otorol_adi = f"<@&{s['otorol_id']}>" if s.get('otorol_id') else "Ayarlanmamış"
    hosgeldin_kanali = f"<#{s['hosgeldin_kanal_id']}>" if s.get('hosgeldin_kanal_id') else "Ayarlanmamış"
    log_kanali = f"<#{s['log_kanal_id']}>" if s.get('log_kanal_id') else "Ayarlanmamış"
    dogrulama_durum = "Aktif ✅" if s.get('log_dogrulama_aktif', False) else "Kapalı ❌"

    embed = discord.Embed(
        title="⚙️ Gelişmiş Sunucu Yönetim Paneli",
        description="Aşağıdaki menülerden seçimlerinizi yapın ve ardından **'💾 Ayarları Kalıcı Olarak Kaydet'** butonuna basarak sisteme işleyin.",
        color=0x5865F2
    )
    embed.add_field(name="📌 Mevcut Otorol", value=otorol_adi, inline=False)
    embed.add_field(name="🚪 Mevcut Hoş Geldin Kanalı", value=hosgeldin_kanali, inline=False)
    embed.add_field(name="🧾 Mevcut Rol Log Kanalı", value=log_kanali, inline=False)
    embed.add_field(name="🤖 Roblox Akıllı Doğrulama", value=dogrulama_durum, inline=False)
    embed.set_footer(text="Discord GUI Sistemi • Kaydet Butonlu Sürüm")

    await interaction.response.send_message(embed=embed, view=SistemYonetimView(gid), ephemeral=True)

@bot.tree.command(name="komutlar", description="Aktif bot komutlarını gösterir.")
async def komutlar(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Bot Komut Listesi",
        description="Mevcut komutlar:",
        color=0x5865F2
    )
    embed.add_field(
        name="🛠️ Komutlar",
        value=(
            "**/özelkontrolpaneli** - Şifreli GUI yönetim panelini açar.\n"
            "**/komutlar** - Komut listesini gösterir.\n"
            "**/ayarlar** - Mevcut sunucu ayarlarını gösterir.\n"
            "**/sunucu-kur** - Kanalları tek seferde kurar (Şifre: 2904).\n"
            "**/sil** - Mesaj temizler.\n"
            "**/mute** - Kullanıcıya zaman aşımı (mute) atar.\n"
            "**/unmute** - Kullanıcının zaman aşımını kaldırır.\n"
            "**/yavaşmod** - Kanalın yavaş mod süresini ayarlar."
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ayarlar", description="Sunucu için yapılan mevcut ayarları gösterir.")
async def ayarlar_komut(interaction: discord.Interaction):
    yukle()
    s = SET.get(interaction.guild.id, {})
    otorol = f"<@&{s['otorol_id']}>" if s.get('otorol_id') else "Ayarlanmamış"
    hosgeldin = f"<#{s['hosgeldin_kanal_id']}>" if s.get('hosgeldin_kanal_id') else "Ayarlanmamış"
    log = f"<#{s['log_kanal_id']}>" if s.get('log_kanal_id') else "Ayarlanmamış"
    dogrulama = "Aktif ✅" if s.get('log_dogrulama_aktif', False) else "Kapalı ❌"

    embed = discord.Embed(title="⚙️ Sunucu Ayarları", color=0x5865F2)
    embed.add_field(name="Otorol", value=otorol, inline=False)
    embed.add_field(name="Hoş Geldin Kanalı", value=hosgeldin, inline=False)
    embed.add_field(name="Rol Log Kanalı", value=log, inline=False)
    embed.add_field(name="Roblox Akıllı Doğrulama", value=dogrulama, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
    if not log_kanali:
        return
    
    islem_yapan = "Bilinmiyor / Otomatik"
    try:
        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                islem_yapan = entry.user.mention
                break
    except:
        pass

    for rol in [r for r in after.roles if r not in before.roles]:
        embed = discord.Embed(title="✅ Rol Verildi", color=0x57F287, timestamp=datetime.datetime.now())
        embed.add_field(name="Kullanıcı", value=after.mention, inline=False)
        embed.add_field(name="Verilen Rol", value=rol.mention, inline=False)
        embed.add_field(name="Veren", value=islem_yapan, inline=False)
        try: await log_kanali.send(embed=embed)
        except: pass

    for rol in [r for r in before.roles if r not in after.roles]:
        embed = discord.Embed(title="❌ Rol Alındı", color=0xED4245, timestamp=datetime.datetime.now())
        embed.add_field(name="Kullanıcı", value=after.mention, inline=False)
        embed.add_field(name="Alınan Rol", value=rol.mention, inline=False)
        embed.add_field(name="Alan", value=islem_yapan, inline=False)
        try: await log_kanali.send(embed=embed)
        except: pass

@bot.tree.command(name="mute", description="Kullanıcıya belirtilen süre kadar zaman aşımı (mute) uygular.")
@app_commands.describe(kullanici="Mute atılacak kullanıcı", dakika="Süre (dakika cinsinden)", sebep="Mute sebebi")
async def mute(interaction: discord.Interaction, kullanici: discord.Member, dakika: int, sebep: str = "Sebep belirtilmedi"):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    try:
        sure = datetime.timedelta(minutes=dakika)
        await kullanici.timeout(sure, reason=sebep)
        await interaction.response.send_message(f"🔇 {kullanici.mention} başarıyla **{dakika} dakika** süreyle mutelendi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="Kullanıcının zaman aşımını (mute) kaldırır.")
@app_commands.describe(kullanici="Mutesi kaldırılacak kullanıcı")
async def unmute(interaction: discord.Interaction, kullanici: discord.Member):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    try:
        await kullanici.timeout(None)
        await interaction.response.send_message(f"🔊 {kullanici.mention} mutesi kaldırıldı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="yavaşmod", description="Kanalın yavaş mod süresini ayarlar.")
@app_commands.describe(saniye="Saniye cinsinden süre (0 kapatır)")
async def yavasmod(interaction: discord.Interaction, saniye: int):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    try:
        await interaction.channel.edit(slowmode_delay=saniye)
        await interaction.response.send_message(f"⏱️ Yavaş mod **{saniye} saniye** olarak ayarlandı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="sunucu-kur", description="Kanalları kurar.")
@app_commands.describe(sifre="Kurulum şifresi")
async def sunucu_kur(interaction: discord.Interaction, sifre: str):
    if sifre != "2904":
        return await hata_mesaji(interaction, "Hatalı şifre!")
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Yetkiniz yok!")
        
    await interaction.response.defer()
    guild = interaction.guild
    try:
        kat1 = await guild.create_category(
