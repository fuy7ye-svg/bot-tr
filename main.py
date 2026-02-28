import discord
import os
from discord.ext import tasks, commands
from flask import Flask
from threading import Thread

# --- إعداد سيرفر وهمي لإبقاء Render مستيقظاً ---
app = Flask('')
@app.route('/')
def home():
    return "I am alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- كود البوت ---
class TradeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.last_menu_message = None

    async def on_ready(self):
        print(f'✅ {self.user} is online on Render!')
        if not self.refresh_menu.is_running():
            self.refresh_menu.start()

    @tasks.loop(minutes=1)
    async def refresh_menu(self):
        channel_id = int(os.getenv('1477106003756585075'))
        channel = self.get_channel(1477106022232621056)
        if not channel: return

        if self.last_menu_message:
            try: await self.last_menu_message.delete()
            except: pass

        embed = discord.Embed(
            title="🔍 تصفية المقايضات الذكية",
            description="اختر اللعبة والماب من القوائم أدناه للتصفية 👇",
            color=0x2ecc71
        )
        # هنا يتم استدعاء كلاس التصفية (الذي يحتوي على اللعبة والماب والغرض)
        self.last_menu_message = await channel.send(embed=embed, view=FilterView())

# تشغيل السيرفر والبوت
Thread(target=run_web).start()
token = os.getenv('DISCORD_TOKEN')
bot = TradeBot()
bot.run(token)
