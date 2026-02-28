import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- سيرفر ويب بسيط ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- بيانات الألعاب والمابات ---
GAMES_DATA = {
    "Roblox": ["Blox Fruits", "Blox Spin", "Pet Sim 99", "MM2"],
    "Fortnite": None,
    "Minecraft": None
}

# --- 1. واجهة إضافة عرض جديد (توضع في روم التقديم) ---
class FormView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ إضافة عرضك", style=discord.ButtonStyle.green, custom_id="add_btn_main")
    async def start_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CreateTradeSelection()
        await interaction.response.send_message("🎮 اختر اللعبة:", view=view, ephemeral=True)

class CreateTradeSelection(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=g, value=g) for g in GAMES_DATA.keys()]
        self.add_item(self.GameSelect(options))

    class GameSelect(discord.ui.Select):
        def __init__(self, options):
            super().__init__(placeholder="اختر اللعبة...", options=options)

        async def callback(self, interaction: discord.Interaction):
            game = self.values[0]
            if game == "Roblox":
                view = discord.ui.View()
                map_options = [discord.SelectOption(label=m, value=m) for m in GAMES_DATA["Roblox"]]
                map_sel = discord.ui.Select(placeholder="اختر الماب...", options=map_options)
                
                async def map_callback(inter):
                    await inter.response.send_modal(TradeForm(game=game, map_name=map_sel.values[0]))
                
                map_sel.callback = map_callback
                view.add_item(map_sel)
                await interaction.response.edit_message(content=f"✅ اخترت **{game}**، حدد الماب الآن:", view=view)
            else:
                await interaction.response.send_modal(TradeForm(game=game, map_name="N/A"))

class TradeForm(discord.ui.Modal):
    def __init__(self, game, map_name):
        super().__init__(title=f"إضافة عرض: {game}")
        self.game, self.map_name = game, map_name
        self.item = discord.ui.TextInput(label='الغرض الذي تعرضه')
        self.looking_for = discord.ui.TextInput(label='المطلوب مقابلها')
        self.add_item(self.item)
        self.add_item(self.looking_for)

    async def on_submit(self, interaction: discord.Interaction):
        if not bot.offers_channel_id: return await interaction.response.send_message("❌ لم يتم تحديد روم العروض!", ephemeral=True)
        channel = interaction.guild.get_channel(bot.offers_channel_id)
        embed = discord.Embed(title="📦 عرض مقايضة جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="🎮 اللعبة", value=self.game, inline=True)
        if self.map_name != "N/A": embed.add_field(name="🗺️ الماب", value=self.map_name, inline=True)
        embed.add_field(name="📤 يعرض", value=self.item.value, inline=False)
        embed.add_field(name="📥 يطلب", value=self.looking_for.value, inline=False)
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ تم نشر عرضك بنجاح في روم العروض!", ephemeral=True)

# --- 2. واجهة التصفية (توضع في روم التصفية) ---
class FilterView(discord.ui.View):
    def __init__(self, selected_map=None):
        super().__init__(timeout=None)
        map_options = [discord.SelectOption(label=m, value=m, default=(m==selected_map)) for m in GAMES_DATA["Roblox"]]
        self.add_item(self.MapSelect(map_options))
        if selected_map:
            items = ["Kitsune", "Leopard", "Mega Spin", "Harvester"] # عينة أغراض للبحث
            item_opts = [discord.SelectOption(label=i, value=i) for i in items]
            self.add_item(self.ItemSearch(item_opts, selected_map))

    class MapSelect(discord.ui.Select):
        def __init__(self, options): super().__init__(placeholder="🔍 1. اختر الماب للبحث...", options=options)
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(view=FilterView(self.values[0]))

    class ItemSearch(discord.ui.Select):
        def __init__(self, options, m_name):
            self.m_name = m_name
            super().__init__(placeholder=f"🔍 2. ابحث عن غرض في {m_name}...", options=options)
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            # منطق البحث في روم العروض (كما في الكود السابق)
            await interaction.followup.send(f"🔎 جاري البحث عن **{self.values[0]}** في قناة العروض...", ephemeral=True)

# --- 3. إعدادات البوت والأوامر ---
class TradeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.offers_channel_id = None 

    async def setup_hook(self): await self.tree.sync()

bot = TradeBot()

@bot.tree.command(name="setup_form", description="إرسال زر التقديم في هذا الروم")
@app_commands.checks.has_permissions(administrator=True)
async def setup_form(interaction: discord.Interaction):
    embed = discord.Embed(title="📝 إضافة مقايضة", description="اضغط الزر بالأسفل لإضافة عرضك الجديد.", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=FormView())
    await interaction.response.send_message("✅ تم وضع نظام التقديم هنا.", ephemeral=True)

@bot.tree.command(name="setup_filter", description="إرسال قوائم التصفية في هذا الروم")
@app_commands.checks.has_permissions(administrator=True)
async def setup_filter(interaction: discord.Interaction):
    embed = discord.Embed(title="🔍 تصفية العروض", description="اختر الماب والغرض للبحث في العروض المنشورة.", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=FilterView())
    await interaction.response.send_message("✅ تم وضع نظام التصفية هنا.", ephemeral=True)

@bot.tree.command(name="set_offers_channel", description="تحديد روم عرض النتائج")
@app_commands.checks.has_permissions(administrator=True)
async def set_offers(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.offers_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم تحديد روم العروض: {channel.mention}", ephemeral=True)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.getenv('DISCORD_TOKEN'))
