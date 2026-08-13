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
        print("âœ… TÃ¼m komutlar baÅŸarÄ±yla senkronize edildi!")
    except Exception as e:
        print(f"âŒ Sync hatasÄ±: {e}")
    print(f"Bot aktif edildi: {bot.user}")
    print("--------------------------------------------------")

@bot.event
async def on_message(message):
    if not message.author.bot and message.content.strip().lower() == "sa":
        try:
            await message.channel.send(f"AleykÃ¼mselam {message.author.mention}")
        except:
            pass
    await bot.process_commands(message)

def yetki_kontrol(interaction, perm):
    return getattr(interaction.user.guild_permissions, perm, False)

async def hata_mesaji(interaction, metin):
    if interaction.response.is_done():
        await interaction.followup.send(f"âŒ {metin}", ephemeral=True)
    else:
        await interaction.response.send_message(f"âŒ {metin}", ephemeral=True)

# --- GUI KONTROL PANELÄ° VE GEÃ‡Ä°CÄ° HAFIZA + KAYDET BUTONU ---
class SistemYonetimView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.secilen_otorol = None
        self.secilen_hg_kanal = None
        self.secilen_log_kanal = None

        # Otorol SeÃ§im MenÃ¼sÃ¼
        role_select = discord.ui.RoleSelect(placeholder="ğŸ“Œ Yeni gelenler iÃ§in Otorol seÃ§in...", min_values=1, max_values=1)
        role_select.callback = self.otorol_secim_callback
        self.add_item(role_select)

        # HoÅŸ Geldin KanalÄ± SeÃ§im MenÃ¼sÃ¼
        hosgeldin_select = discord.ui.ChannelSelect(placeholder="ğŸšª HoÅŸ geldin kanalÄ±nÄ± seÃ§in...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
        hosgeldin_select.callback = self.hosgeldin_secim_callback
        self.add_item(hosgeldin_select)

        # Log KanalÄ± SeÃ§im MenÃ¼sÃ¼
        log_select = discord.ui.ChannelSelect(placeholder="ğŸ§¾ Rol log kanalÄ±nÄ± seÃ§in...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
        log_select.callback = self.log_secim_callback
        self.add_item(log_select)

    async def otorol_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.secilen_otorol = interaction.data["values"][0]
        role_obj = interaction.guild.get_role(int(self.secilen_otorol))
        await interaction.followup.send(f"ğŸ“Œ Otorol geÃ§ici olarak seÃ§ildi: **{role_obj.name}** (Kaydetmek iÃ§in alttaki **Kaydet** butonuna basÄ±n)", ephemeral=True)

    async def hosgeldin_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.secilen_hg_kanal = interaction.data["values"][0]
        kanal_obj = interaction.guild.get_channel(int(self.secilen_hg_kanal))
        await interaction.followup.send(f"ğŸšª HoÅŸ geldin kanalÄ± geÃ§ici olarak seÃ§ildi: {kanal_obj.mention} (Kaydetmek iÃ§in alttaki **Kaydet** butonuna basÄ±n)", ephemeral=True)

    async def log_secim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.secilen_log_kanal = interaction.data["values"][0]
        kanal_obj = interaction.guild.get_channel(int(self.secilen_log_kanal))
        await interaction.followup.send(f"ğŸ§¾ Log kanalÄ± geÃ§ici olarak seÃ§ildi: {kanal_obj.mention} (Kaydetmek iÃ§in alttaki **Kaydet** butonuna basÄ±n)", ephemeral=True)

    @discord.ui.button(label="ğŸ’¾ AyarlarÄ± KalÄ±cÄ± Olarak Kaydet", style=discord.ButtonStyle.success, emoji="âœ…", row=3)
    async def kaydet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        yukle()
        SET.setdefault(self.guild_id, {"name": interaction.guild.name, "otorol_id": "", "hosgeldin_kanal_id": "", "log_kanal_id": ""})

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

        if not degisiklik_var:
            return await interaction.followup.send("âš ï¸ HenÃ¼z hiÃ§bir rol veya kanal seÃ§mediniz!", ephemeral=True)

        kaydet()

        s = SET[self.guild_id]
        otorol_adi = f"<@&{s['otorol_id']}>" if s.get('otorol_id') else "AyarlanmamÄ±ÅŸ"
        hosgeldin_kanali = f"<#{s['hosgeldin_kanal_id']}>" if s.get('hosgeldin_kanal_id') else "AyarlanmamÄ±ÅŸ"
        log_kanali = f"<#{s['log_kanal_id']}>" if s.get('log_kanal_id') else "AyarlanmamÄ±ÅŸ"

        embed = discord.Embed(
            title="âœ… Ayarlar BaÅŸarÄ±yla Kaydedildi!",
            description="SeÃ§tiÄŸiniz tÃ¼m sistemler kalÄ±cÄ± hafÄ±zaya iÅŸlendi.",
            color=0x57F287
        )
        embed.add_field(name="ğŸ“Œ Otorol", value=otorol_adi, inline=False)
        embed.add_field(name="ğŸšª HoÅŸ Geldin KanalÄ±", value=hosgeldin_kanali, inline=False)
        embed.add_field(name="ğŸ§¾ Rol Log KanalÄ±", value=log_kanali, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


# --- Ã–ZEL KONTROL PANELÄ° KOMUTU ---
@bot.tree.command(name="Ã¶zelkontrolpaneli", description="Åifre ile korunan geliÅŸmiÅŸ Discord GUI kontrol panelini aÃ§ar.")
@app_commands.describe(sifre="Panel eriÅŸim ÅŸifresi")
async def ozel_kontrol_paneli(interaction: discord.Interaction, sifre: str):
    if not yetki_kontrol(interaction, "manage_guild"):
        return await hata_mesaji(interaction, "Bu paneli aÃ§mak iÃ§in 'Sunucuyu YÃ¶net' yetkiniz olmalÄ±.")
    
    if sifre != "2904":
        return await hata_mesaji(interaction, "HatalÄ± ÅŸifre! EriÅŸim reddedildi.")
    
    yukle()
    gid = interaction.guild.id
    s = SET.get(gid, {})
    
    otorol_adi = f"<@&{s['otorol_id']}>" if s.get('otorol_id') else "AyarlanmamÄ±ÅŸ"
    hosgeldin_kanali = f"<#{s['hosgeldin_kanal_id']}>" if s.get('hosgeldin_kanal_id') else "AyarlanmamÄ±ÅŸ"
    log_kanali = f"<#{s['log_kanal_id']}>" if s.get('log_kanal_id') else "AyarlanmamÄ±ÅŸ"

    embed = discord.Embed(
        title="âš™ï¸ GeliÅŸmiÅŸ Sunucu YÃ¶netim Paneli",
        description="AÅŸaÄŸÄ±daki menÃ¼lerden seÃ§imlerinizi yapÄ±n ve ardÄ±ndan **'ğŸ’¾ AyarlarÄ± KalÄ±cÄ± Olarak Kaydet'** butonuna basarak sisteme iÅŸleyin.",
        color=0x5865F2
    )
    embed.add_field(name="ğŸ“Œ Mevcut Otorol", value=otorol_adi, inline=False)
    embed.add_field(name="ğŸšª Mevcut HoÅŸ Geldin KanalÄ±", value=hosgeldin_kanali, inline=False)
    embed.add_field(name="ğŸ§¾ Mevcut Rol Log KanalÄ±", value=log_kanali, inline=False)
    embed.set_footer(text="Discord GUI Sistemi â€¢ Kaydet Butonlu SÃ¼rÃ¼m")

    await interaction.response.send_message(embed=embed, view=SistemYonetimView(gid), ephemeral=True)


# --- DÄ°ÄER TEMEL SÄ°STEMLER VE KOMUTLAR ---
@bot.tree.command(name="komutlar", description="Aktif bot komutlarÄ±nÄ± gÃ¶sterir.")
async def komutlar(interaction: discord.Interaction):
    embed = discord.Embed(
        title="ğŸ“œ Bot Komut Listesi",
        description="Mevcut komutlar:",
        color=0x5865F2
    )
    embed.add_field(
        name="ğŸ› ï¸ Komutlar",
        value=(
            "**/Ã¶zelkontrolpaneli** - Åifreli Discord GUI yÃ¶netim panelini aÃ§ar.\n"
            "**/komutlar** - Komut listesini gÃ¶sterir.\n"
            "**/ayarlar** - Mevcut sunucu ayarlarÄ±nÄ± gÃ¶sterir.\n"
            "**/sunucu-kur** - KanallarÄ± tek seferde kurar (Åifre: 2904).\n"
            "**/sil** - Mesaj temizler.\n"
            "**/mute** - KullanÄ±cÄ±ya zaman aÅŸÄ±mÄ± (mute) atar.\n"
            "**/unmute** - KullanÄ±cÄ±nÄ±n zaman aÅŸÄ±mÄ±nÄ± kaldÄ±rÄ±r.\n"
            "**/yavaÅŸmod** - KanalÄ±n yavaÅŸ mod sÃ¼resini ayarlar."
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ayarlar", description="Sunucu iÃ§in yapÄ±lan mevcut ayarlarÄ± gÃ¶sterir.")
async def ayarlar_komut(interaction: discord.Interaction):
    yukle()
    s = SET.get(interaction.guild.id, {})
    otorol = f"<@&{s['otorol_id']}>" if s.get('otorol_id') else "AyarlanmamÄ±ÅŸ"
    hosgeldin = f"<#{s['hosgeldin_kanal_id']}>" if s.get('hosgeldin_kanal_id') else "AyarlanmamÄ±ÅŸ"
    log = f"<#{s['log_kanal_id']}>" if s.get('log_kanal_id') else "AyarlanmamÄ±ÅŸ"

    embed = discord.Embed(title="âš™ï¸ Sunucu AyarlarÄ±", color=0x5865F2)
    embed.add_field(name="Otorol", value=otorol, inline=False)
    embed.add_field(name="HoÅŸ Geldin KanalÄ±", value=hosgeldin, inline=False)
    embed.add_field(name="Rol Log KanalÄ±", value=log, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- ROL LOG SÄ°STEMÄ° (VERÄ°LEN VE ALINAN ROLLER DÃœZELTÄ°LDÄ°) ---
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

    # Verilen Roller
    for rol in [r for r in after.roles if r not in before.roles]:
        embed = discord.Embed(title="âœ… Rol Verildi", color=0x57F287, timestamp=datetime.datetime.now())
        embed.add_field(name="KullanÄ±cÄ±", value=after.mention, inline=False)
        embed.add_field(name="Verilen Rol", value=rol.mention, inline=False)
        embed.add_field(name="Veren", value=islem_yapan, inline=False)
        try: await log_kanali.send(embed=embed)
        except: pass

    # AlÄ±nan (Silinen) Roller
    for rol in [r for r in before.roles if r not in after.roles]:
        embed = discord.Embed(title="âŒ Rol AlÄ±ndÄ±", color=0xED4245, timestamp=datetime.datetime.now())
        embed.add_field(name="KullanÄ±cÄ±", value=after.mention, inline=False)
        embed.add_field(name="AlÄ±nan Rol", value=rol.mention, inline=False)
        embed.add_field(name="Alan", value=islem_yapan, inline=False)
        try: await log_kanali.send(embed=embed)
        except: pass

# --- MUTE (ZAMAN AÅIMI) SÄ°STEMÄ° ---
@bot.tree.command(name="mute", description="KullanÄ±cÄ±ya belirtilen sÃ¼re kadar zaman aÅŸÄ±mÄ± (mute) uygular.")
@app_commands.describe(kullanici="Mute atÄ±lacak kullanÄ±cÄ±", dakika="SÃ¼re (dakika cinsinden)", sebep="Mute sebebi")
async def mute(interaction: discord.Interaction, kullanici: discord.Member, dakika: int, sebep: str = "Sebep belirtilmedi"):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Bu komutu kullanmak iÃ§in 'Ãœyeleri Zaman AÅŸÄ±mÄ±na UÄŸrat' yetkiniz olmalÄ±.")
    try:
        sure = datetime.timedelta(minutes=dakika)
        await kullanici.timeout(sure, reason=sebep)
        await interaction.response.send_message(f"ğŸ”‡ {kullanici.mention} isimli kullanÄ±cÄ± baÅŸarÄ±yla **{dakika} dakika** sÃ¼reyle muteleendi. Sebep: `{sebep}`", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"âŒ Mute atÄ±lÄ±rken bir hata oluÅŸtu: {e}", ephemeral=True)

# --- UNMUTE SÄ°STEMÄ° ---
@bot.tree.command(name="unmute", description="KullanÄ±cÄ±nÄ±n zaman aÅŸÄ±mÄ±nÄ± (mute) kaldÄ±rÄ±r.")
@app_commands.describe(kullanici="Mutesi kaldÄ±rÄ±lacak kullanÄ±cÄ±")
async def unmute(interaction: discord.Interaction, kullanici: discord.Member):
    if not yetki_kontrol(interaction, "moderate_members"):
        return await hata_mesaji(interaction, "Bu komutu kullanmak iÃ§in 'Ãœyeleri Zaman AÅŸÄ±mÄ±na UÄŸrat' yetkiniz olmalÄ±.")
    try:
        await kullanici.timeout(None)
        await interaction.response.send_message(f"ğŸ”Š {kullanici.mention} isimli kullanÄ±cÄ±nÄ±n mutesi kaldÄ±rÄ±ldÄ±.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"âŒ Mute kaldÄ±rÄ±lÄ±rken hata oluÅŸtu: {e}", ephemeral=True)

# --- YAVAÅMOD (SLOWMODE) SÄ°STEMÄ° DÃœZELTÄ°LDÄ° ---
@bot.tree.command(name="yavaÅŸmod", description="BulunduÄŸunuz kanalÄ±n yavaÅŸ mod sÃ¼resini ayarlar.")
@app_commands.describe(saniye="Saniye cinsinden yavaÅŸ mod sÃ¼resi (0 kapatÄ±r)")
async def yavasmod(interaction: discord.Interaction, saniye: int):
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Bu komutu kullanmak iÃ§in 'KanallarÄ± YÃ¶net' yetkiniz olmalÄ±.")
    try:
        await interaction.channel.edit(slowmode_delay=saniye)
        if saniye == 0:
            await interaction.response.send_message("â±ï¸ Bu kanaldaki yavaÅŸ mod kapatÄ±ldÄ±.", ephemeral=True)
        else:
            await interaction.response.send_message(f"â±ï¸ Bu kanalÄ±n yavaÅŸ mod sÃ¼resi **{saniye} saniye** olarak ayarlandÄ±.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"âŒ YavaÅŸ mod ayarlanÄ±rken hata oluÅŸtu: {e}", ephemeral=True)

@bot.tree.command(name="sunucu-kur", description="TÃ¼m kategorileri ve kanallarÄ± tek seferde kurar.")
@app_commands.describe(sifre="Kurulum ÅŸifresi")
async def sunucu_kur(interaction: discord.Interaction, sifre: str):
    if sifre != "2904":
        return await hata_mesaji(interaction, "HatalÄ± ÅŸifre!")
    if not yetki_kontrol(interaction, "manage_channels"):
        return await hata_mesaji(interaction, "Yetkiniz yok!")
    await interaction.response.defer()
    guild = interaction.guild
    try:
        kat1 = await guild.create_category("ã€ŒğŸ“Œã€Ã–nemli")
        for isim in ["ã€Œâ“ã€biz-kimiz", "ã€ŒğŸšªã€gelen-giden"]:
            await guild.create_text_channel(isim, category=kat1)
        await interaction.followup.send("âœ… Kurulum tamamlandÄ±.")
    except Exception as e:
        await interaction.followup.send(f"âŒ Hata: {e}")

@bot.tree.command(name="sil", description="Mesaj siler.")
@app_commands.describe(limit="SayÄ±")
async def sil(interaction: discord.Interaction, limit: int = 5):
    if not yetki_kontrol(interaction, "manage_messages"):
        return await hata_mesaji(interaction, "Yetkiniz yok.")
    await interaction.response.defer(ephemeral=True)
    silinenler = await interaction.channel.purge(limit=limit)
    await interaction.followup.send(f"ğŸ§¹ {len(silinenler)} mesaj silindi.", ephemeral=True)

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
            try: await kanal.send(f"HoÅŸ geldin {member.mention}! Toplam **{member.guild.member_count}** kiÅŸiyiz.")
            except: pass

# --- RENDER PORT HATASINI Ã–NLEYEN BASÄ°T SÄ°TE ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Aktif!"

if __name__ == "__main__":
    discord_token = os.environ.get("TOKEN")
    if not discord_token:
        print("âŒ HATA: TOKEN bulunamadÄ±!")
        exit(1)

    threading.Thread(target=lambda: bot.run(discord_token), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
