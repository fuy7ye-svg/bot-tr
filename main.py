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

# --- البيانات ---
GAMES_DATA = {
    "Roblox": ["Blox Fruits", "Blox Spin", "Pet Sim 99", "MM2"],
    "Fortnite": ["Skins", "Accounts"],
    "Minecraft": ["Servers", "Items"]
}

# --- 1. نظام إضافة العروض (روم التقديم) ---
class FormView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ إضافة عرضك الجديد", style=discord.ButtonStyle.green, custom_id="add_btn_main")
    async def start_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CreateTradeSelection()
        await interaction.response.send_message("🎮 اختر اللعبة التي تود الإعلان فيها:", view=view, ephemeral=True)

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
        self.item = discord.ui.TextInput(label='الغرض الذي تعرضه', placeholder='مثال: Kitsune / سكن...')
        self.looking_for = discord.ui.TextInput(label='المطلوب مقابلها', placeholder='مثال: Leopard / عرض مناسب...')
        self.add_item(self.item)
        self.add_item(self.looking_for)

    async def on_submit(self, interaction: discord.Interaction):
        if not bot.offers_channel_id: 
            return await interaction.response.send_message("❌ لم يتم تحديد روم العروض من قبل الإدارة!", ephemeral=True)
        
        channel = interaction.guild.get_channel(bot.offers_channel_id)
        embed = discord.Embed(title="📦 عرض مقايضة جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="🎮 اللعبة", value=self.game, inline=True)
        if self.map_name != "N/A": 
            embed.add_field(name="🗺️ الماب", value=self.map_name, inline=True)
        embed.add_field(name="📤 يعرض", value=self.item.value, inline=False)
        embed.add_field(name="📥 يطلب", value=self.looking_for.value, inline=False)
        
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ تم نشر عرضك بنجاح في روم العروض!", ephemeral=True)

# --- 2. نظام التصفية (روم التصفية) ---
class FilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=g, value=g) for g in GAMES_DATA.keys()]
        self.add_item(self.GameFilterSelect(options))

    class GameFilterSelect(discord.ui.Select):
        def __init__(self, options):
            super().__init__(placeholder="🔍 1. اختر اللعبة للبحث...", options=options)

        async def callback(self, interaction: discord.Interaction):
            game = self.values[0]
            view = discord.ui.View()
            map_options = [discord.SelectOption(label=m, value=m) for m in GAMES_DATA[game]]
            map_sel = discord.ui.Select(placeholder=f"🔍 2. اختر الماب في {game}...", options=map_options)
            
            async def map_search_callback(inter):
                await inter.response.defer(ephemeral=True)
                selected_target = map_sel.values[0]
                
                if not bot.offers_channel_id:
                    return await inter.followup.send("❌ روم العروض غير محدد!", ephemeral=True)
                
                channel = inter.guild.get_channel(bot.offers_channel_id)
                found_links = []
                
                async for message in channel.history(limit=150): # يبحث في آخر 150 رسالة
                    if message.embeds:
                        for embed in message.embeds:
                            content = f"{embed.title} " + " ".join([f.value for f in embed.fields])
                            if selected_target.lower() in content.lower():
                                found_links.append(message.jump_url)
                
                if found_links:
                    results = "\n".join([f"🔹 [اضغط هنا للانتقال للعرض]({url})" for url in found_links[:10]])
                    await inter.followup.send(f"✅ تم العثور على عروض في **{selected_target}**:\n{results}", ephemeral=True)
                else:
                    await inter.followup.send(f"❌ لا توجد عروض حالياً لماب **{selected_target}**.", ephemeral=True)

            map_sel.callback = map_search_callback
            view.add_item(map_sel)
            await interaction.response.send_message(f"🔎 تصفية **{game}**: اختر الماب المطلوب:", view=view, ephemeral=True)

# --- 3. إعدادات البوت والتشغيل ---
class TradeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.offers_channel_id = None 

    async def setup_hook(self):
        await self.tree.sync()

bot = TradeBot()

@bot.tree.command(name="setup_form", description="إرسال زر التقديم (روم الإضافة)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_form(interaction: discord.Interaction):
    embed = discord.Embed(title="📝 إضافة مقايضة", description="اضغط الزر بالأسفل لإضافة عرضك الجديد إلى السوق.", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=FormView())
    await interaction.response.send_message("✅ تم وضع نظام التقديم.", ephemeral=True)

@bot.tree.command(name="setup_filter", description="إرسال قائمة التصفية (روم التصفية)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_filter(interaction: discord.Interaction):
    embed = discord.Embed(title="🔍 تصفية العروض", description="اختر اللعبة والماب للبحث عن العروض فوراً.", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=FilterView())
    await interaction.response.send_message("✅ تم وضع نظام التصفية.", ephemeral=True)

@bot.tree.command(name="set_offers_channel", description="تحديد روم النتائج (روم العروض)")
@app_commands.checks.has_permissions(administrator=True)
async def set_offers(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.offers_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم تحديد روم العروض: {channel.mention}", ephemeral=True)

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ خطأ: لم يتم العثور على DISCORD_TOKEN في إعدادات Render!")
