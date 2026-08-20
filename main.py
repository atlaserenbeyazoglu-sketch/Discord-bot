import discord, json, os, datetime, threading, re
from discord.ext import commands
from discord import app_commands
from flask import Flask

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

LOG_YANITLARI = {}

async def akilli_metin_log_denetimi(icerik, gorsel_sayisi):
    # En az 1 görsel eklenmiş mi kontrol et
    if gorsel_sayisi < 1:
        return False

    # Saatleri yakala (Örn: 18:00, 22:00 veya 18.00)
    saatler = re.findall(r'(\d{1,2})[:\.](\d{2})', icerik)
    
    # Süre ifadelerini yakala (Örn: 4 saat, 4s, 3.5 saat, 2,5 saat)
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
            fark_dakika += 24 * 60 # Gece yarısını geçenler için (Örn: 23:00 - 02:00)

        hesaplanan_saat = fark_dakika / 60.0
        belirtilen_sure = float(sure_ifadeleri[0].replace(',', '.'))

        # SIFIR TOLERANS: Hesaplanan süre ile yazılan süre birebir aynı olmalıdır.
        if abs(hesaplanan_saat - belirtilen_sure) > 0.01:
            return False
            
    except Exception as e:
        print(f"Metin Denetim Hatası: {e}")
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
            gorsel_sayisi = len(message.attachments)
            
            if not icerik or len(icerik) < 5 or gorsel_sayisi < 1:
                try:
                    await message.add_reaction("❌")
                    yanit = await message.reply("Lütfen gerekli kanıtların ekran görüntüsünü ve uygun formatı giriniz!")
                    LOG_YANITLARI[message.id] = yanit.id
                except:
                    pass
                return

            for gorsel in message.attachments:
                if not any(gorsel.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                    try:
                        await message.add_reaction("❌")
                        yanit = await message.reply("Lütfen geçerli görsel formatları (png, jpg) yükleyin!")
                        LOG_YANITLARI[message.id] = yanit.id
                    except:
                        pass
                    return

            basarili_mi = await akilli_metin_log_denetimi(icerik, gorsel_sayisi)
            
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
                    yanit = await message.reply("Girilen saatler ile belirtilen süre uyuşmuyor, lütfen kontrol edin.")
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
async def on_message_edit(before, after):
    if after.author.bot:
        return
    if not after.guild:
        return

    if bot.user.mentioned_in(after) and not after.mention_everyone:
        yukle()
        gid = after.guild.id
        s = SET.get(gid, {})
        
        if s.get("log_dogrulama_aktif", False):
            if after.id in LOG_YANITLARI:
                try:
                    eski_yanit = await after.channel.fetch_message(LOG_YANITLARI[after.id])
                    await eski_yanit.delete()
                except:
                    pass
                del LOG_YANITLARI[after.id]

            try:
                await after.clear_reactions()
            except:
                pass

            icerik = after.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
            gorsel_sayisi = len(after.attachments)
            
            if not icerik or len(icerik) < 5 or gorsel_sayisi < 1:
                try:
                    await after.add_reaction("❌")
                    yanit = await after.reply("Lütfen gerekli kanıtların ekran görüntüsünü ve uygun formatı giriniz!")
                    LOG_YANITLARI[after.id] = yanit.id
                except:
                    pass
                return

            for gorsel in after.attachments:
                if not any(gorsel.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                    try:
                        await after.add_reaction("❌")
                        yanit = await after.reply("Lütfen geçerli görsel formatları (png, jpg) yükleyin!")
                        LOG_YANITLARI[after.id] = yanit.id
                    except:
                        pass
                    return

            basarili_mi = await akilli_metin_log_denetimi(icerik, gorsel_sayisi)
            
            if basarili_mi:
                try:
                    await after.add_reaction("✅")
                    yanit = await after.channel.send("Onay!")
                    LOG_YANITLARI[after.id] = yanit.id
                except:
                    pass
            else:
                try:
                    await after.add_reaction("❌")
                    yanit = await after.reply("Girilen saatler ile belirtilen süre uyuşmuyor, lütfen kontrol edin.")
                    LOG_YANITLARI[after.id] = yanit.id
                except:
                    pass

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
            placeholder="🤖 Metin Tabanlı Akıllı Log Doğrulama...",
            options=[
                discord.SelectOption(label="Aktif Et (Aç)", value="ac", description="Bot etiketlenince SS ve saat matematiğini denetler.", emoji="✅"),
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
        await interaction.followup.send(f"📌 Otorol seçildi: **{role_obj.name}**", ephemeral=True)

    async def hosgeldin_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.secilen_hg_kanal = interaction.data["values"][0]
        kanal_obj = interaction.guild.get_channel(int(self.secilen_hg_kanal))
        await interaction.followup.send(f"🚪 Hoş geldin kanalı seçildi: {kanal_obj.mention}", ephemeral=True)

    async def log_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.secilen_log_kanal = interaction.data["values"][0]
        kanal_obj = interaction.guild.get_channel(int(self.secilen_log_kanal))
        await interaction.followup.send(f"🧾 Log kanalı seçildi: {kanal_obj.mention}", ephemeral=True)

    async def dogrulama_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        val = interaction.data["values"][0]
        self.secilen_log_durum = True if val == "ac" else False
        durum_str = "Aktif (Açık)" if self.secilen_log_durum else "Devre Dışı (Kapalı)"
        await interaction.followup.send(f"🤖 Akıllı Doğrulama seçildi: **{durum_str}**", ephemeral=True)

    @discord.ui.button(label="💾 Ayarları Kalıcı Olarak Kaydet", style=discord.ButtonStyle.success, emoji="✅", row=4)
    async def kaydet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        yukle()
        SET.setdefault(self.guild_id, {"name": interaction.guild.name, "otorol_id": "", "hosgeldin_kanal_id": "", "log_kanal_id": "", "log_dogrulama_aktif": False})

        if self.secilen_otorol is not None:
            SET[self.guild_id]["otorol_id"] = str(self.secilen_otorol)
        if self.secilen_hg_kanal is not None:
            SET[self.guild_id]["hosgeldin_kanal_id"] = str(self.secilen_hg_kanal)
        if self.secilen_log_kanal is not None:
            SET[self.guild_id]["log_kanal_id"] = str(self.secilen_log_kanal)
        if self.secilen_log_durum is not None:
            SET[self.guild_id]["log_dogrulama_aktif"] = self.secilen_log_durum

        kaydet()
        await interaction.followup.send("✅ Ayarlar başarıyla kaydedildi!", ephemeral=True)

@bot.tree.command(name="özelkontrolpaneli", description="Şifre ile korunan gelişmiş Discord GUI kontrol panelini açar.")
@app_commands.describe(sifre="Panel erişim şifresi")
async def ozel_kontrol_paneli(interaction: discord.Interaction, sifre: str):
    if not yetki_kontrol(interaction, "manage_guild"):
        return await hata_mesaji(interaction, "Bu paneli açmak için yetkiniz yok.")
    if sifre != "2904":
        return await hata_mesaji(interaction, "Hatalı şifre!")
    await interaction.response.send_message("⚙️ Gelişmiş Sunucu Yönetim Paneli:", view=SistemYonetimView(interaction.guild.id), ephemeral=True)

@bot.tree.command(name="komutlar", description="Aktif bot komutlarını gösterir.")
async def komutlar(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Bot Komut Listesi", description="/özelkontrolpaneli, /ayarlar, /sunucu-kur, /sil, /mute, /unmute, /yavaşmod", color=0x5865F2)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ayarlar", description="Sunucu ayarlarını gösterir.")
async def ayarlar_komut(interaction: discord.Interaction):
    yukle()
    s = SET.get(interaction.guild.id, {})
    embed = discord.Embed(title="⚙️ Sunucu Ayarları", color=0x5865F2)
    embed.add_field(name="Otorol", value=f"<@&{s.get('otorol_id')}>" if s.get('otorol_id') else "Yok", inline=False)
    embed.add_field(name="Hoş Geldin Kanalı", value=f"<#{s.get('hosgeldin_kanal_id')}>" if s.get('hosgeldin_kanal_id') else "Yok", inline=False)
    embed.add_field(name="Rol Log Kanalı", value=f"<#{s.get('log_kanal_id')}>" if s.get('log_kanal_id') else "Yok", inline=False)
    embed.add_field(name="Akıllı Log Doğrulama", value="Aktif ✅" if s.get('log_dogrulama_aktif', False) else "Kapalı ❌", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles: return
    guild = after.guild
    yukle()
    s = SET.get(guild.id, {})
    log_kanal_id = s.get("log_kanal_id")
    if not log_kanal_id: return
    log_kanali = guild.get_channel(int(log_kanal_id))
    if not log_kanali: return
    for rol in [r for r in after.roles if r not in before.roles]:
        embed = discord.Embed(title="✅ Rol Verildi", description=f"{after.mention} adlı kullanıcıya {rol.mention} rolü verildi.", color=0x57F287)
        try: await log_kanali.send(embed=embed)
        except: pass
    for rol in [r for r in before.roles if r not in after.roles]:
        embed = discord.Embed(title="❌ Rol Alındı", description=f"{after.mention} adlı kullanıcıdan {rol.mention} rolü alındı.", color=0xED4245)
        try: await log_kanali.send(embed=embed)
        except: pass

@bot.tree.command(name="mute", description="Kullanıcıyı muteler.")
@app_commands.describe(kullanici="Kullanıcı", dakika="Dakika", sebep="Sebep")
async def mute(interaction: discord.Interaction, kullanici: discord.Member, dakika: int, sebep: str = "Yok"):
    if not yetki_kontrol(interaction, "moderate_members"): return await hata_mesaji(interaction, "Yetkiniz yok.")
    try:
        await kullanici.timeout(datetime.timedelta(minutes=dakika), reason=sebep)
        await interaction.response.send_message(f"🔇 {kullanici.mention} mutelendi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="Muteden çıkarır.")
async def unmute(interaction: discord.Interaction, kullanici: discord.Member):
    if not yetki_kontrol(interaction, "moderate_members"): return await hata_mesaji(interaction, "Yetkiniz yok.")
    try:
        await kullanici.timeout(None)
        await interaction.response.send_message(f"🔊 {kullanici.mention} mutesi açıldı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="yavaşmod", description="Yavaş mod.")
async def yavasmod(interaction: discord.Interaction, saniye: int):
    if not yetki_kontrol(interaction, "manage_channels"): return await hata_mesaji(interaction, "Yetkiniz yok.")
    try:
        await interaction.channel.edit(slowmode_delay=saniye)
        await interaction.response.send_message(f"⏱️ Yavaş mod {saniye} saniye.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="sunucu-kur", description="Sunucuyu kurar.")
async def sunucu_kur(interaction: discord.Interaction, sifre: str):
    if sifre != "2904": return await hata_mesaji(interaction, "Hatalı şifre!")
    if not yetki_kontrol(interaction, "manage_channels"): return await hata_mesaji(interaction, "Yetkiniz yok!")
    await interaction.response.defer()
    try:
        kat1 = await interaction.guild.create_category("Genel Bilgi")
        await interaction.guild.create_text_channel("biz-kimiz", category=kat1)
        await interaction.guild.create_text_channel("gelen-giden", category=kat1)
        await interaction.followup.send("✅ Kurulum tamamlandı.")
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}")

@bot.tree.command(name="sil", description="Mesaj siler.")
async def sil(interaction: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(interaction, "manage_messages"): return await hata_mesaji(interaction, "Yetkiniz yok.")
    await interaction.response.defer(ephemeral=True)
    silinenler = await interaction.channel.purge(limit=limit)
    await interaction.followup.send(f"🧹 {len(silinenler)} mesaj silindi.", ephemeral=True)

@bot.event
async def on_member_join(member):
    yukle()
    s = SET.get(member.guild.id, {})
    if s.get("otorol_id"):
        rol = member.guild.get_role(int(s["otorol_id"]))
        if rol:
            try: await member.add_roles(rol)
            except: pass
    if s.get("hosgeldin_kanal_id"):
        kanal = member.guild.get_channel(int(s["hosgeldin_kanal_id"]))
        if kanal:
            try: await kanal.send(f"Hoş geldin {member.mention}!")
            except: pass

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Aktif!", 200

if __name__ == "__main__":
    discord_token = os.environ.get("TOKEN")
    if not discord_token:
        print("❌ HATA: TOKEN bulunamadı!")
        exit(1)
    threading.Thread(target=lambda: bot.run(discord_token), daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
                
