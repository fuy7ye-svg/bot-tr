import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- سيرفر ويب لإبقاء البوت حياً على Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- بيانات المابات والأغراض ---
MAPS_DATA = {
    "Blox Fruits": ["Kitsune", "Leopard", "Dragon", "Dough"],
    "Blox Spin": ["Mega Spin", "Super Spin", "Rare Box"],
    "Pet Sim 99": ["Huge Pet", "Titanic", "Gems"],
    "MM2": ["Harvester", "IcePiercer", "Bat"]
}

# --- 1. واجهة التصفية والبحث الذكي ---
class DynamicFilterView(discord.ui.View):
    def __init__(self, selected_map=None):
        super().__init__(timeout=None)
        # القائمة الأولى: اختيار الماب (تكون مفعلة دائماً)
        self.add_item(MapDropdown(selected_map))
        
        # القائمة الثانية: تظهر فقط إذا تم اختيار ماب وتعمل كقائمة بحث
        if selected_map:
            self.add_item(ItemDropdown(selected_map))
        
        # زر إضافة عرض جديد
        add_btn = discord.ui.Button(label="➕ إضافة عرضك", style=discord.ButtonStyle.green, custom_id="add_trade_btn")
        add_btn.callback = self.add_trade_callback
        self.add_item(add_btn)

    async def add_trade_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TradeForm())

class MapDropdown(discord.ui.Select):
    def __init__(self, selected_map):
        options = [
            discord.SelectOption(label=m, value=m, default=(m == selected_map)) 
            for m in MAPS_DATA.keys()
        ]
        super().__init__(placeholder="🗺️ 1. اختر الماب أولاً...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_map = self.values[0]
        embed = discord.Embed(
            title="🛒 مركز المقايضة الذكي",
            description=f"✅ الماب الحالي: **{selected_map}**\nالآن اختر الغرض من القائمة بالأسفل للبحث عنه:",
            color=0x3498db
        )
        await interaction.response.edit_message(embed=embed, view=DynamicFilterView(selected_map))

class ItemDropdown(discord.ui.Select):
    def __init__(self, map_name):
        self.map_name = map_name
        options = [discord.SelectOption(label=i, value=i) for i in MAPS_DATA[map_name]]
        super().__init__(placeholder=f"🔍 2. ابحث عن غرض في {map_name}...", options=options)

    async def callback(self, interaction: discord.Interaction):
        search_query = self.values[0].lower()
        
        # تجنب فشل التفاعل (Interaction Failed) بإعطاء مهلة للبحث
        await interaction.response.defer(ephemeral=True)
        
        if not bot.offers_channel_id:
            return await interaction.followup.send("❌ قناة العروض غير محددة!", ephemeral=True)
            
        channel = interaction.guild.get_channel(bot.offers_channel_id)
        found_offers = []

        # البحث الفعلي في آخر 100 رسالة (Embeds)
        async for message in channel.history(limit=100):
            if message.embeds:
                content = ""
                for embed in message.embeds:
                    content += f" {embed.title} {embed.description}"
                    for field in embed.fields:
                        content += f" {field.name} {field.value}"
                
                if search_query in content.lower():
                    found_offers.append(message.jump_url)

        if found_offers:
            links = "\n".join([f"🔹 [اضغط هنا للعرض]({url})" for url in found_offers[:5]])
            await interaction.followup.send(f"✅ تم العثور على عروض لـ **{self.values[0]}**:\n{links}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ لا يوجد عروض حالياً لـ **{self.values[0]}** في قناة العروض.", ephemeral=True)

# --- 2. نموذج تقديم العروض (Modal) ---
class TradeForm(discord.ui.Modal, title='إنشاء عرض مقايضة جديد'):
    map_name = discord.ui.TextInput(label='اسم الماب', placeholder='Blox Fruits, MM2...')
    item = discord.ui.TextInput(label='الغرض الذي تعرضه', placeholder='مثال: Kitsune')
    looking_for = discord.ui.TextInput(label='المطلوب مقابلها', placeholder='مثال: Leopard + Add')

    async def on_submit(self, interaction: discord.Interaction):
        if not bot.offers_channel_id:
            return await interaction.response.send_message("❌ قناة العروض غير محددة!", ephemeral=True)
        
        offers_channel = interaction.guild.get_channel(bot.offers_channel_id)
        embed = discord.Embed(title="📦 عرض مقايضة جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="🗺️ الماب", value=self.map_name.value, inline=True)
        embed.add_field(name="📤 يعرض", value=self.item.value, inline=True)
        embed.add_field(name="📥 يطلب", value=self.looking_for.value, inline=True)
        
        await offers_channel.send(embed=embed)
        await interaction.response.send_message("✅ تم نشر عرضك في قناة العروض!", ephemeral=True)

# --- 3. إعدادات البوت والتشغيل ---
class TradeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.offers_channel_id = None 

    async def setup_hook(self):
        await self.tree.sync()

bot = TradeBot()

@bot.tree.command(name="setup_trade", description="إرسال واجهة المقايضة والتصفية")
@app_commands.checks.has_permissions(administrator=True)
async def setup_trade(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛒 مركز المقايضة الذكي",
        description="اختر الماب أولاً لتظهر لك قائمة البحث عن الأغراض.",
        color=0x3498db
    )
    await interaction.channel.send(embed=embed, view=DynamicFilterView())
    await interaction.response.send_message("✅ تم إعداد الواجهة في هذه القناة.", ephemeral=True)

@bot.tree.command(name="set_offers_channel", description="تحديد القناة التي تظهر فيها عروض الناس")
@app_commands.checks.has_permissions(administrator=True)
async def set_offers(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.offers_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم تحديد قناة العروض: {channel.mention}", ephemeral=True)

# التشغيل النهائي الآمن لـ Render
if __name__ == "__main__":
    Thread(target=run_web).start()
    # سحب التوكن من البيئة (Environment) وليس من الكود مباشرة
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ خطأ: التوكن غير موجود في Environment Variables!")
