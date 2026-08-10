import discord, json, os, datetime
from discord.ext import commands
from discord import app_commands

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

# --- 1. YENİ NESİL DİSCORD GUI (KONTROL PANELİ) ---
class AyarModal(discord.ui.Modal, title="⚙️ Gelişmiş Sunucu Ayar Paneli"):
    otorol_input = discord.ui.TextInput(
        label="Otorol ID",
        placeholder="Verilecek rolün ID sini yazın (Örn: 123456789)",
        required=False,
        max_length=20
    )
    hosgeldin_input = discord.ui.TextInput(
        label="Hoş Geldin Kanal ID",
        placeholder="Kanal ID sini yazın",
        required=False,
        max_length=20
    )
    log_input = discord.ui.TextInput(
        label="Rol Log Kanal ID",
        placeholder="Rol log kanal ID sini yazın",
        required=False,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        yukle()
        gid = interaction.guild.id
        SET.setdefault(gid, {"name": interaction.guild.name, "otorol_id": "", "hosgeldin_kanal_id": "", "log_kanal_id": ""})

        if self.otorol_input.value.strip():
            SET[gid]["otorol_id"] = self.otorol_input.value.strip()
        if self.hosgeldin_input.value.strip():
            SET[gid]["hosgeldin_kanal_id"] = self.hosgeldin_input.value.strip()
        if self.log_input.value.strip():
            SET[gid]["log_kanal_id"] = self.log_input.value.strip()
        
        kaydet()

        embed = discord.Embed(
            title="✅ Ayarlar Başarıyla Güncellendi ve Kaydedildi!",
            description="Yeni sistem yapılandırması kalıcı olarak işlendi.",
            color=0x57F287
        )
        embed.add_field(name="Otorol ID", value=SET[gid]["otorol_id"] or "Ayarlanmamış", inline=False)
        embed.add_field(name="Hoş Geldin Kanal ID", value=SET[gid]["hosgeldin_kanal_id"] or "Ayarlanmamış", inline=False)
        embed.add_field(name="Rol Log Kanal ID", value=SET[gid]["log_kanal_id"] or "Ayarlanmamış", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SifreModal(discord.ui.Modal, title="🛡️ Güvenlik Doğrulaması"):
    sifre_input = discord.ui.TextInput(
        label="Panel Şifresi",
        placeholder="4 haneli güvenlik şifresini girin...",
        style=discord.TextStyle.short,
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.sifre_input.value != "2904":
            return await interaction.response.send_message("❌ Hatalı şifre! Erişim reddedildi.", ephemeral=True)
        
        # Şifre doğruysa yeni nesil GUI ayar penceresini aç
        await interaction.response.send_modal(AyarModal())

class PanelArayuzView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 Kontrol Paneline Giriş Yap", style=discord.ButtonStyle.primary, emoji="🔐")
    async def panel_giris(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetki_kontrol(interaction, "manage_guild"):
            return await interaction.response.send_message("❌ Bu paneli açmak için 'Sunucuyu Yönet' yetkiniz olmalı.", ephemeral=True)
        await interaction.response.send_modal(SifreModal())

@bot.tree.command(name="panel", description="Yeni nesil şifreli Discord kontrol panelini açar.")
async def panel_komut(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Ultra Teknolojik Sunucu Yönetim Paneli",
        description="Aşağıdaki butona tıklayarak güvenli şifre ekranına ulaşabilir ve sunucu yapılandırmalarını (Otorol, Log, Hoş geldin) anında yönetebilirsiniz.",
        color=0x5865F2
    )
    embed.set_footer(text="Fender & Bot GUI Sistemi • Kalıcı Hafıza Aktif")
    await interaction.response.send_message(embed=embed, view=PanelArayuzView(), ephemeral=True)

# --- 2. DİĞER KOMUTLAR VE SİSTEMLER ---
@bot.tree.command(name="komutlar", description="Aktif bot komutlarını gösterir.")
async def komutlar(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Bot Komut Listesi", color=0x5865F2)
    embed.add_field(
        name="🛠️ Komutlar",
        value=(
            "**/panel** - Şifreli yeni nesil GUI yönetim panelini açar.\n"
            "**/sunucu-kur** - Kanalları tek seferde kurar (Şifre: 2904).\n"
            "**/sil** - Mesaj temizler.\n"
            "**/kanalayazmaerişimi** - Rollerin yazma iznini ayarlar.\n"
            "**/mute** / **/unmute** - Zaman aşımı işlemleri.\n"
            "**/yavaşmod** - Kanal yavaş modu.\n"
            "**/kanalgörünülürlük** - Kanal gizleme/gösterme."
        ),
        inline=False
    )
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
        await interaction.followup.send("✅ Sistem başarıyla kuruldu.")
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}")

@bot.tree.command(name="sil", description="Mesaj temizler.")
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

if __name__ == "__main__":
    discord_token = os.environ.get("TOKEN")
    if discord_token:
        bot.run(discord_token)
    else:
        print("❌ HATA: TOKEN bulunamadı!")
    
