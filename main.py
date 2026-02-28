import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- سيرفر ويب لإبقاء البوت حياً ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- قائمة التصفية الموحدة (القيم يجب أن تكون كلمات مفتاحية للبحث) ---
QUICK_FILTER_OPTIONS = [
    discord.SelectOption(label="Blox Fruits: Kitsune", value="Kitsune", emoji="🦊"),
    discord.SelectOption(label="Blox Fruits: Leopard", value="Leopard", emoji="🐆"),
    discord.SelectOption(label="Blox Spin: Mega Spin", value="Mega Spin", emoji="🎡"),
    discord.SelectOption(label="Blox Spin: Rare Box", value="Rare Box", emoji="📦"),
    discord.SelectOption(label="Pet Sim 99: Huge Pet", value="Huge", emoji="🐱"),
    discord.SelectOption(label="MM2: Harvester", value="Harvester", emoji="🏹"),
]

# --- نموذج التعبئة ---
class TradeForm(discord.ui.Modal, title='إنشاء عرض مقايضة جديد'):
    map_name = discord.ui.TextInput(label='اسم الماب', placeholder='مثال: Blox Fruits')
    item = discord.ui.TextInput(label='الغرض اللي عندك', placeholder='مثال: Kitsune')
    looking_for = discord.ui.TextInput(label='وش تبي مقابلها', placeholder='مثال: Leopard')

    async def on_submit(self, interaction: discord.Interaction):
        if not bot.offers_channel_id:
            return await interaction.response.send_message("❌ لم يتم تحديد قناة العروض!", ephemeral=True)
        
        offers_channel = interaction.guild.get_channel(bot.offers_channel_id)
        embed = discord.Embed(title="📦 عرض مقايضة جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="🗺️ الماب", value=self.map_name.value, inline=True)
        embed.add_field(name="📤 يعرض", value=self.item.value, inline=True)
        embed.add_field(name="📥 يطلب", value=self.looking_for.value, inline=True)
        
        await offers_channel.send(embed=embed)
        await interaction.response.send_message("✅ تم نشر عرضك!", ephemeral=True)

# --- واجهة التصفية مع منطق البحث ---
class MainFilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.select(placeholder="🔍 اختر للبحث عن عروض...", options=QUICK_FILTER_OPTIONS)
    async def quick_filter(self, interaction: discord.Interaction, select: discord.ui.Select):
        search_query = select.values[0].lower() # الكلمة التي سنبحث عنها
        
        if not bot.offers_channel_id:
            return await interaction.response.send_message("❌ قناة العروض غير محددة بعد.", ephemeral=True)
            
        channel = interaction.guild.get_channel(bot.offers_channel_id)
        found_offers = []

        # إخبار المستخدم أن البحث جارٍ (لأن البحث في الرسائل قد يأخذ ثانية)
        await interaction.response.defer(ephemeral=True)

        # البحث في آخر 100 رسالة في قناة العروض
        async for message in channel.history(limit=100):
            if message.embeds:
                content = ""
                for embed in message.embeds:
                    # تجميع نصوص الإمبد للبحث داخلها
                    content += f" {embed.title} {embed.description}"
                    for field in embed.fields:
                        content += f" {field.name} {field.value}"
                
                # التحقق إذا كانت الكلمة موجودة في الإمبد
                if search_query in content.lower():
                    found_offers.append(message.jump_url)

        # النتيجة النهائية
        if found_offers:
            links = "\n".join([f"🔹 [اضغط هنا للانتقال للعرض]({url})" for url in found_offers[:5]]) # عرض أول 5 نتائج
            await interaction.followup.send(f"✅ تم العثور على عروض لـ **{select.values[0]}**:\n{links}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ لا يوجد عروض حالياً لـ **{select.values[0]}**.", ephemeral=True)

    @discord.ui.button(label="➕ إضافة عرضك", style=discord.ButtonStyle.green)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TradeForm())

class TradeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.offers_channel_id = None 

    async def setup_hook(self):
        await self.tree.sync()

bot = TradeBot()

@bot.tree.command(name="setup_trade", description="إرسال واجهة التصفية")
@app_commands.checks.has_permissions(administrator=True)
async def setup_trade(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 مركز المقايضة", description="اختر غرضاً للبحث عنه في قناة العروض.", color=0x3498db)
    await interaction.channel.send(embed=embed, view=MainFilterView())
    await interaction.response.send_message("✅ تم الإعداد.", ephemeral=True)

@bot.tree.command(name="set_offers_channel", description="تحديد قناة العروض")
@app_commands.checks.has_permissions(administrator=True)
async def set_offers(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.offers_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم تحديد قناة العروض: {channel.mention}", ephemeral=True)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.getenv('DISCORD_TOKEN'))
