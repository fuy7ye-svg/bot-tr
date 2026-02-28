import discord
from discord.ext import tasks, commands

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.market_channel_id = 1234567890  # حط هنا آيدي روم العروض
        self.last_menu_message = None # هنا بنخزن الرسالة عشان نحذفها

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.refresh_menu.start() # تشغيل حلقة التحديث التلقائي

    @tasks.loop(minutes=1) # الحلقة تتكرر كل دقيقة
    async def refresh_menu(self):
        channel = self.get_channel(self.market_channel_id)
        if channel:
            # 1. حذف الرسالة القديمة إذا كانت موجودة
            if self.last_menu_message:
                try:
                    await self.last_menu_message.delete()
                except:
                    pass # إذا أحد حذفها يدوياً ما يوقف البوت

            # 2. تصميم "الإمبد" أو القائمة
            embed = discord.Embed(
                title="🔍 مركز تصفية المقايضات",
                description="القائمة تتحدث تلقائياً كل دقيقة لتكون دائماً في الأسفل 👇",
                color=discord.Color.green()
            )
            embed.add_field(name="التعليمات", value="1️⃣ اختر اللعبة\n2️⃣ اختر الماب\n3️⃣ اختر الغرض")

            # 3. إرسال القائمة الجديدة مع خيارات التصفية (Select Menus)
            # ملاحظة: FilterView هو الكلاس اللي فيه القوائم المنسدلة
            self.last_menu_message = await channel.send(embed=embed, view=FilterView())

# كلاس القوائم المنسدلة (مثال مبسط)
class FilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="🎮 اختر اللعبة...", options=[
        discord.SelectOption(label="روبلوكس", value="roblox", emoji="🧱"),
        discord.SelectOption(label="روكيت ليغ", value="rl", emoji="⚽")
    ])
    async def select_game(self, interaction: discord.Interaction, select: discord.ui.Select):
        # هنا تكمل منطق التصفية اللي تكلمنا عنه
        await interaction.response.send_message(f"تم اختيار {select.values[0]}، جاري تحميل المابات...", ephemeral=True)
