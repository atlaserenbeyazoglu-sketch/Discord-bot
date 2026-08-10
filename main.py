import discord, json, os, datetime, threading
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

@bot.event
async def on_message(message):
    if not message.author.bot and message.content.strip().lower() == "sa":
        try:
            await message.channel.send(f"Aleykümselam {message.author.mention}")
        except:
            pass
    await bot.process_commands(message)

def yetki_kontrol(interaction, perm):
    return getattr(interaction.user.guild_permissions, perm, False)

async def hata_mesaji(interaction, metin):
    await interaction.response.send_message(f"❌ {metin}", ephemeral=True)

# --- GELİŞMİŞ DİSCORD GUI KONTROL PANELİ SİSTEMİ ---

class SistemYonetimView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=180)
        
        # Otorol Seçim Menüsü
        role_select = discord.ui.RoleSelect(placeholder="📌 Yeni gelenler için Otorol seçin...", min_values=1, max_values=1)
        role_select.callback = self.otorol_secim_callback
        self.add_item(role_select)

        # Hoş Geldin Kanalı Seçim Menüsü
        hosgeldin_select = discord.ui.ChannelSelect(placeholder="🚪 Hoş geldin kanalını seçin...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
        hosgeldin_select.callback = self.hosgeldin_secim_callback
        self.add_item(hosgeldin_select)

        # Log Kanalı Seçim Menüsü
        log_select = discord.ui.ChannelSelect(placeholder="🧾 Rol log kanalını seçin...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
        log_select.callback = self.log_secim_callback
        self.add_item(log_select)

    async def otorol_secim_callback(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        secilen_rol = interaction.values[0]
        yukle()
        SET.setdefault(gid, {"name": interaction.guild.name, "otorol_id": "", "hosgeldin_kanal_id": "", "log_kanal_id": ""})
        SET[gid]["otorol_id"] = str(secilen_rol.id)
        kaydet()
        await interaction.response.send_message(f"✅ Otorol başarıyla **{secilen_rol.name}** olarak ayarlandı ve kaydedildi!", ephemeral=True)

    async def hosgeldin_secim_callback(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        secilen_kanal = interaction.values[0]
        yukle()
        SET.setdefault(gid, {"name": interaction.guild.name, "otorol_id": "", "hosgeldin_kanal_id": "", "log_kanal_id": ""})
        SET[gid]["hosgeldin_kanal_id"] = str(secilen_kanal.id)
        kaydet()
        await interaction.response.send_message(f"✅ Hoş geldin kanalı başarıyla {secilen_kanal.mention} olarak ayarlandı ve kaydedildi!", ephemeral=True)

    async def log_secim_callback(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        secilen_kanal = interaction.values[0]
        yukle()
        SET.setdefault(gid, {"name": interaction.guild.name, "otorol_id": "", "hosgeldin_kanal_id": "", "log_kanal_id": ""})
        SET[gid]["log_kanal_id"] = str(secilen_kanal.id)
        kaydet()
        await interaction.response.send_message(f"✅ Rol log kanalı başarıyla {secilen_kanal.mention} olarak ayarlandı ve kaydedildi!", ephemeral=True)


class SifreModal(discord.ui.Modal, title="🛡️ Güvenlik Doğrulaması"):
    sifre_input = discord.ui.TextInput(
        label="Panel Şifresi",
        placeholder="4 haneli şifreyi girin (2904)...",
        style=discord.TextStyle.short,
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.sifre_input.value != "2904":
            return await interaction.response.send_message("❌ Hatalı şifre! Erişim reddedildi.", ephemeral=True)
        
        yukle()
        gid = interaction.guild.id
        s = SET.get(gid, {})
        
        otorol_adi = f"<@&{s['otorol_id']}>" if s.get('otorol_id') else "Ayarlanmamış"
        hosgeldin_kanali = f"<#{s['hosgeldin_kanal_id']}>" if s.get('hosgeldin_kanal_id') else "Ayarlanmamış"
        log_kanali = f"<#{s['log_kanal_id']}>" if s.get('log_kanal_id') else "Ayarlanmamış"

        embed = discord.Embed(
            title="⚙️ Gelişmiş Sunucu Yönetim Paneli",
            description="Aşağıdaki interaktif menüleri kullanarak sunucu sistemlerini anında yapılandırabilirsin. Yapılan değişiklikler **kalıcı olarak** saklanır.",
            color=0x5865F2
        )
        embed.add_field(name="📌 Mevcut Otorol", value=otorol_adi, inline=False)
        embed.add_field(name="🚪 Mevcut Hoş Geldin Kanalı", value=hosgeldin_kanali, inline=False)
        embed.add_field(name="🧾 Mevcut Rol Log Kanalı", value=log_kanali, inline=False)
        embed.set_footer(text="Yeni Nesil Discord GUI Sistemi • Güvenli Oturum Açıldı")

        await interaction.response.send_message(embed=embed, view=SistemYonetimView(interaction.guild), ephemeral=True)


class PanelGirisView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔐 Kontrol Paneline Giriş Yap", style=discord.ButtonStyle.primary, emoji="🚀")
    async def giris_yap(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetki_kontrol(interaction, "manage_guild"):
            return await interaction.response.send_message("❌ Bu paneli açmak için 'Sunucuyu Yönet' yetkiniz olmalı.", ephemeral=True)
        await interaction.response.send_modal(SifreModal())


@bot.tree.command(name="panel", description="Şifreli yeni nesil Discord GUI yönetim panelini açar.")
async def panel_komut(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Ultra Teknolojik Sunucu Yönetim Paneli",
        description="Aşağıdaki butona tıklayıp şifreyi girerek sunucu sistemlerini (Otorol, Hoş Geldin, Log) tamamen Discord içinden yönetebileceğin arayüze ulaşabilirsin.",
        color=0x5865F2
    )
    embed.set_footer(text="Fender & Bot GUI Sistemi")
    await interaction.response.send_message(embed=embed, view=PanelGirisView(), ephemeral=True)


# --- DİĞER KOMUTLAR VE SİSTEMLER ---
@bot.tree.command(name="komutlar", description="Sunucudaki aktif bot komutlarını gösterir.")
async def komutlar(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Bot Komut Listesi",
        description="Mevcut komutlar:",
        color=0x5865F2
    )
    embed.add_field(
        name="🛠️ Yönetim ve Sistemler",
        value=(
            "**/panel** - Şifreli Discord GUI yönetim panelini açar.\n"
            "**/komutlar** - Komut listesini gösterir.\n"
            "**/ayarlar** - Mevcut sunucu ayarlarını gösterir.\n"
            "**/sunucu-kur** - Kanalları tek seferde kurar (Şifre: 2904).\n"
            "**/sil** - Mesaj temizler.\n"
            "**/kanalayazmaerişimi** - Rollerin yazma iznini ayarlar.\n"
            "**/mute** / **/unmute** - Zaman aşımı işlemleri.\n"
            "**/yavaşmod** - Yavaş mod ayarlar.\n"
            "**/kanalgörünülürlük** - Kanal gizleme/gösterme."
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

    embed = discord.Embed(title="⚙️ Sunucu Ayarları", color=0x5865F2)
    embed.add_field(name="Otorol", value=otorol, inline=False)
    embed.add_field(name="Hoş Geldin Kanalı", value=hosgeldin, inline=False)
    embed.add_field(name="Rol Log Kanalı", value=log, inline=False)
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

@bot.tree.command(name="sunucu-kur", description="Tüm kategorileri ve kanalları tek seferde kurar.")
@app_commands.describe(sifre="Kurulum şifresi")
async def sunucu_kur(interaction: discord.Interaction, sifre: str):
    if sifre != "2904":
        return await hata_mesaji(interaction, "Hatalı şifre!")
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Yetkiniz yok!")
    await interaction.response.defer()
    guild = interaction.guild
    try:
        kat1 = await guild.create_category("「📌」Önemli")
        for isim in ["「❓」biz-kimiz", "「🚪」gelen-giden"]:
            await guild.create_text_channel(isim, category=kat1)
        await interaction.followup.send("✅ Kurulum tamamlandı.")
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}")

@bot.tree.command(name="sil", description="Mesaj siler.")
@app_commands.describe(limit="Sayı")
async def sil(interaction: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
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
            try: await kanal.send(f"Hoş geldin {member.mention}! Toplam **{member.guild.member_count}** kişiyiz.")
            except: pass

# --- RENDER PORT HATASINI ÖNLEYEN SİTE (Sadece "Bot Aktif!" yazar) ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Aktif!"

if __name__ == "__main__":
    discord_token = os.environ.get("TOKEN")
    if not discord_token:
        print("❌ HATA: TOKEN bulunamadı!")
        exit(1)

    # Botu arka planda thread olarak başlatıyoruz
    threading.Thread(target=lambda: bot.run(discord_token), daemon=True).start()
    
    # Sitede sadece "Bot Aktif!" yazacak şekilde Flask portunu açıyoruz (Render port hatası vermez)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
