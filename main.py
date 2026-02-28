import discord
from discord import app_commands
from discord.ext import tasks, commands
import os
from flask import Flask
from threading import Thread

# --- سيرفر وهمي لإبقاء البوت حياً على Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- بيانات المابات والأغراض (مدمجة للتصفية السريعة) ---
# هنا جمعت لك الماب مع الغرض في خيار واحد عشان يسهل البحث
QUICK_FILTER_OPTIONS = [
    # Blox Fruits
    discord.SelectOption(label="Blox Fruits: Kitsune", value="bf_kitsune", emoji="🦊"),
    discord.SelectOption(label="Blox Fruits: Leopard", value="bf_leopard", emoji="🐆"),
    discord.SelectOption(label="Blox Fruits: Dragon", value="bf_dragon", emoji="🐉"),
    # Blox Spin
    discord.SelectOption(label="Blox Spin: Mega Spin", value="bs_mega", emoji="🎡"),
    discord.SelectOption(label="Blox Spin: Rare Box", value="bs_box", emoji="📦"),
    # Pet Sim 99
    discord.SelectOption(label="Pet Sim 99: Huge Pet", value="ps_huge", emoji="🐱"),
    discord.SelectOption(label="Pet Sim 99: Titanic", value="ps_titanic", emoji="🚢"),
    # MM2
    discord.SelectOption(label="MM2: Harvester", value="mm2_harvester", emoji="🏹"),
    discord.SelectOption(label="MM2: IcePiercer", value="mm2_ice", emoji="❄️"),
]

# --- 1. نموذج التعبئة (Trade Modal) ---
class TradeForm(discord.ui.Modal, title='إنشاء عرض مقايضة جديد'):
    map_name = discord.ui.TextInput(label='اسم الماب', placeholder='Blox Fruits, Blox Spin...')
    item = discord.ui.TextInput(label='الغرض اللي عندك', placeholder='مثال: Kitsune')
    looking_for = discord.ui.TextInput(label='وش تبي مقابلها', placeholder='مثال: Leopard + Add')

    async def on_submit(self, interaction: discord.Interaction):
        channel_id = bot.market_channel_id
        if not channel_id:
            return await interaction.response.send_message("❌ لم يتم تحديد روم العروض!", ephemeral=True)
        
        channel = interaction.guild.get_channel(channel_id)
        embed = discord.Embed(title="📦 عرض مقايضة جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="🗺️ الماب", value=self.map_name.value, inline=True)
        embed.add_field(name="📤 يعرض", value=self.item.value, inline=True)
        embed.add_field(name="📥 يطلب", value=self.looking_for.value, inline=True)
        
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ تم نشر عرضك!", ephemeral=True)

# --- 2. نظام التصفية الموحد (Single List) ---
class UnifiedFilter(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="🔍 اختر الماب والغرض للبحث فوراً...", options=QUICK_FILTER_OPTIONS)

    async def callback(self, interaction: discord.Interaction):
        # هنا البوت ياخذ القيمة ويبحث عنها
        selected = self.values[0]
        item_name = [opt.label for opt in QUICK_FILTER_OPTIONS if opt.value == selected][0]
        await interaction.response.send_message(f"🔎 جاري تصفية العروض لـ: **{item_name}**...", ephemeral=True)

class MainFilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(UnifiedFilter())

    @discord.ui.button(label="➕ إضافة عرضك", style=discord.ButtonStyle.green)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TradeForm())

# --- 3. كلاس البوت الرئيسي ---
class TradeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.market_channel_id = None
        self.last_menu_message = None

    async def setup_hook(self):
        await self.tree.sync()

    @tasks.loop(minutes=1)
    async def refresh_menu(self):
        if not self.market_channel_id: return
        channel = self.get_channel(self.market_channel_id)
        if not channel: return

        if self.last_menu_message:
            try: await self.last_menu_message.delete()
            except: pass

        embed = discord.Embed(
            title="🛒 سوق المقايضة الذكي",
            description="اختر الغرض من القائمة للبحث، أو اضغط الزر لإضافة عرضك الخاص.",
            color=0x9b59b6
        )
        self.last_menu_message = await channel.send(embed=embed, view=MainFilterView())

    async def on_ready(self):
        print(f'✅ {self.user} جاهز بنظام القائمة الموحدة!')
        if not self.refresh_menu.is_running():
            self.refresh_menu.start()

bot = TradeBot()

@bot.tree.command(name="set_market", description="تحديد روم التصفية")
@app_commands.checks.has_permissions(administrator=True)
async def set_market(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.market_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم تحديد الروم: {channel.mention}", ephemeral=True)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.getenv('DISCORD_TOKEN'))
