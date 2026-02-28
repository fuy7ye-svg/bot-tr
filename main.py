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

# --- 1. واجهة التصفية الديناميكية ---
class DynamicFilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # القائمة الأولى (الماب) تكون مفعلة دائماً
        self.add_item(MapDropdown())

# قائمة اختيار الماب
class MapDropdown(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=m, value=m) for m in MAPS_DATA.keys()]
        super().__init__(placeholder="🗺️ 1. اختر الماب أولاً...", options=options, custom_id="map_select")

    async def callback(self, interaction: discord.Interaction):
        selected_map = self.values[0]
        # إنشاء القائمة الثانية بناءً على الماب المختار
        view = discord.ui.View(timeout=None)
        view.add_item(MapDropdown()) # إعادة إضافة قائمة الماب لتبقى موجودة
        view.add_item(ItemDropdown(selected_map)) # إضافة قائمة الأغراض الخاصة بالماب
        
        await interaction.response.edit_message(content=f"✅ اخترت **{selected_map}**، الآن اختر الغرض للبحث عنه:", view=view)

# قائمة اختيار الغرض (تظهر بعد اختيار الماب)
class ItemDropdown(discord.ui.Select):
    def __init__(self, map_name):
        self.map_name = map_name
        options = [discord.SelectOption(label=i, value=i) for i in MAPS_DATA[map_name]]
        super().__init__(placeholder=f"🔍 2. اختر غرض من {map_name}...", options=options, custom_id="item_select")

    async def callback(self, interaction: discord.Interaction):
        search_query = self.values[0].lower()
        
        if not bot.offers_channel_id:
            return await interaction.response.send_message("❌ قناة العروض غير محددة!", ephemeral=True)
            
        channel = interaction.guild.get_channel(bot.offers_channel_id)
        found_offers = []

        await interaction.response.defer(ephemeral=True)

        # البحث في آخر 100 رسالة في قناة العروض
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
            await interaction.followup.send(f"✅ عروض لـ **{self.values[0]}** في **{self.map_name}**:\n{links}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ لا يوجد عروض حالياً لـ **{self.values[0]}** في هذا الماب.", ephemeral=True)

# --- 2. نموذج التعبئة (Modal) ---
class TradeForm(discord.ui.Modal, title='إنشاء عرض جديد'):
    map_name = discord.ui.TextInput(label='اسم الماب', placeholder='مثال: Blox Fruits')
    item = discord.ui.TextInput(label='الغرض اللي عندك', placeholder='مثال: Kitsune')
    looking_for = discord.ui.TextInput(label='المطلوب', placeholder='مثال: Leopard')

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
        await interaction.response.send_message("✅ تم نشر عرضك بنجاح!", ephemeral=True)

# --- 3. إعدادات البوت وأوامر الإدارة ---
class TradeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.offers_channel_id = None 

    async def setup_hook(self):
        await self.tree.sync()

bot = TradeBot()

@bot.tree.command(name="setup_trade", description="إرسال واجهة التصفية (للمدراء)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_trade(interaction: discord.Interaction):
    view = DynamicFilterView()
    # إضافة زر "إضافة عرض" تحت القوائم
    add_btn = discord.ui.Button(label="➕ إضافة عرضك", style=discord.ButtonStyle.green, custom_id="add_trade")
    
    async def add_callback(inter):
        await inter.response.send_modal(TradeForm())
    
    add_btn.callback = add_callback
    view.add_item(add_btn)

    embed = discord.Embed(
        title="🛒 مركز المقايضة الذكي",
        description="اختر الماب أولاً لتفتح لك قائمة الأغراض والبحث.",
        color=0x3498db
    )
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ تم إرسال الواجهة.", ephemeral=True)

@bot.tree.command(name="set_offers_channel", description="تحديد قناة العروض")
@app_commands.checks.has_permissions(administrator=True)
async def set_offers(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.offers_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم تحديد قناة العروض: {channel.mention}", ephemeral=True)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.getenv('DISCORD_TOKEN'))
