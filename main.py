import discord
from discord import app_commands
from discord.ext import tasks, commands
import os
from flask import Flask
from threading import Thread

# --- إعداد سيرفر الويب لإبقاء البوت حياً ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- نظام القوائم المنسدلة (التصفية) ---
class FilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # القائمة الأولى: اختيار اللعبة
    @discord.ui.select(placeholder="🎮 1. اختر اللعبة لتبدأ التصفية...", options=[
        discord.SelectOption(label="روبلوكس", value="roblox", emoji="🧱"),
        discord.SelectOption(label="روكيت ليغ", value="rl", emoji="⚽")
    ])
    async def select_game(self, interaction: discord.Interaction, select: discord.ui.Select):
        game = select.values[0]
        # هنا البوت يرسل رسالة مخفية للمستخدم فيها خيارات الماب
        if game == "roblox":
            msg = "لقد اخترت روبلوكس، يرجى اختيار الماب من القائمة القادمة (تحت التطوير)."
        else:
            msg = "لقد اخترت روكيت ليغ، يرجى اختيار الفئة."
            
        await interaction.response.send_message(msg, ephemeral=True)

# --- كلاس البوت الرئيسي ---
class TradeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.market_channel_id = None 
        self.last_menu_message = None

    async def setup_hook(self):
        # مزامنة أوامر السلاش (Slash Commands)
        await self.tree.sync()

    @tasks.loop(minutes=1)
    async def refresh_menu(self):
        if not self.market_channel_id:
            return
            
        channel = self.get_channel(self.market_channel_id)
        if not channel: return

        # حذف الرسالة القديمة ليبقى الشريط في الأسفل
        if self.last_menu_message:
            try: await self.last_menu_message.delete()
            except: pass

        embed = discord.Embed(
            title="🔍 مركز تصفية المقايضات الذكي",
            description="استخدم القائمة أدناه للبحث عن غرض معين.\nتتحدث هذه القائمة تلقائياً كل دقيقة لتبقى في الأسفل.",
            color=0x2ecc71
        )
        embed.set_footer(text="سيرفر المقايضة الرسمي")
        
        self.last_menu_message = await channel.send(embed=embed, view=FilterView())

    async def on_ready(self):
        print(f'✅ {self.user} متصل الآن وجاهز للعمل!')
        if not self.refresh_menu.is_running():
            self.refresh_menu.start()

bot = TradeBot()

# --- أمر تحديد الروم (للإدارة فقط) ---
@bot.tree.command(name="set_market", description="تحديد الروم التي يرسل فيها البوت القائمة التلقائية")
@app_commands.checks.has_permissions(administrator=True)
async def set_market(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.market_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم ضبط روم التصفية بنجاح في: {channel.mention}", ephemeral=True)

# --- تشغيل البوت ---
if __name__ == "__main__":
    # تشغيل سيرفر الويب في خلفية الكود
    Thread(target=run_web).start()
    
    # سحب التوكن من إعدادات البيئة (Render Environment Variables)
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ خطأ: لم يتم العثور على التوكن (DISCORD_TOKEN) في الإعدادات!")
