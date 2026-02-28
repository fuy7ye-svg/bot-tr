import discord
from discord import app_commands
from discord.ext import tasks, commands
import os
from flask import Flask
from threading import Thread

# --- سيرفر وهمي لإبقاء Render مستيقظاً ---
app = Flask('')
@app.route('/')
def home(): return "I'm alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- كلاس القوائم المنسدلة (التصفية) ---
class FilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="🎮 1. اختر اللعبة", options=[
        discord.SelectOption(label="روبلوكس", value="roblox"),
        discord.SelectOption(label="روكيت ليغ", value="rl")
    ])
    async def select_game(self, interaction: discord.Interaction, select: discord.ui.Select):
        # هنا يمكنك تخصيص مابات كل لعبة
        if select.values[0] == "roblox":
            options = [discord.SelectOption(label="Blox Fruits"), discord.SelectOption(label="Adopt Me")]
        else:
            options = [discord.SelectOption(label="Ranked Match"), discord.SelectOption(label="Trading")]
        
        await interaction.response.send_message("اختر الماب الآن من القائمة الجديدة (كمثال)", ephemeral=True)

# --- كلاس البوت الرئيسي ---
class TradeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.market_channel_id = None 
        self.last_menu_message = None

    async def setup_hook(self):
        await self.tree.sync() # مزامنة أوامر السلاش

    @tasks.loop(minutes=1)
    async def refresh_menu(self):
        if not self.market_channel_id: return
        channel = self.get_channel(self.market_channel_id)
        if not channel: return

        if self.last_menu_message:
            try: await self.last_menu_message.delete()
            except: pass

        embed = discord.Embed(title="🔍 مركز التصفية", description="تحديث تلقائي كل دقيقة...", color=0x00ff00)
        self.last_menu_message = await channel.send(embed=embed, view=FilterView())

    async def on_ready(self):
        print(f'✅ {self.user} متصل الآن!')
        if not self.refresh_menu.is_running():
            self.refresh_menu.start()

bot = TradeBot()

# --- أمر تحديد الروم (للأونر/الإدارة فقط) ---
@bot.tree.command(name="set_market", description="تحديد روم القائمة")
@app_commands.checks.has_permissions(administrator=True)
async def set_market(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.market_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم ضبط الروم: {channel.mention}", ephemeral=True)

# --- التشغيل ---
if __name__ == "__main__":
    Thread(target=run_web).start() # تشغيل السيرفر الجانبي
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ خطأ: لم يتم العثور على التوكن في إعدادات Render!")
