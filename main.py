import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
import asyncio

# --- سيرفر ويب ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- بيانات الألعاب والأطوار ---
GAMES_DATA = {
    "روبلوكس": ["Blox Fruits", "Blox Spin", "Pet Sim 99", "MM2"],
    "فورتنايت": ["سكينات", "حسابات"],
    "ماين كرافت": ["سيرفرات", "أغراض نادرة"]
}

# --- نظام التصفية (مع التنظيف التلقائي) ---
class FilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=g, value=g) for g in GAMES_DATA.keys()]
        self.add_item(self.GameFilterSelect(options))

    class GameFilterSelect(discord.ui.Select):
        def __init__(self, options):
            super().__init__(placeholder="🎮 اختر اللعبة للبحث...", options=options)

        async def callback(self, interaction: discord.Interaction):
            game = self.values[0]
            # حذف رسالة الاختيار السابقة لإبقاء الروم نظيفاً
            await interaction.response.defer()
            
            view = discord.ui.View()
            mode_options = [discord.SelectOption(label=m, value=m) for m in GAMES_DATA[game]]
            mode_sel = discord.ui.Select(placeholder=f"🕹️ اختر الطور في {game}...", options=mode_options)
            
            async def mode_callback(inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                selected_mode = mode_sel.values[0]
                
                # حذف رسالة اختيار الطور بعد الاختيار
                await inter.delete_original_response()
                
                if not bot.offers_channel_id:
                    return await inter.followup.send("❌ روم العروض غير محدد!", ephemeral=True)
                
                channel = inter.guild.get_channel(bot.offers_channel_id)
                found_links = []
                
                async for message in channel.history(limit=200):
                    if message.embeds:
                        for embed in message.embeds:
                            content = f"{embed.title} " + " ".join([f.value for f in embed.fields])
                            if selected_mode.lower() in content.lower():
                                found_links.append(message.jump_url)
                
                if found_links:
                    results = "\n".join([f"🔹 [اضغط هنا للانتقال للعرض]({url})" for url in found_links[:10]])
                    await inter.followup.send(f"✅ عروض طور **{selected_mode}**:\n{results}", ephemeral=True)
                else:
                    await inter.followup.send(f"❌ لا توجد عروض حالياً في **{selected_mode}**.", ephemeral=True)

            mode_sel.callback = mode_callback
            view.add_item(mode_sel)
            # إرسال قائمة الأطوار وحذف القديمة
            await interaction.followup.send(f"🔎 اختر الطور المطلوب في **{game}**:", view=view, ephemeral=True)

# --- نظام إضافة العروض (مع تقسيم الأقسام) ---
class FormView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="➕ إضافة عرضك الجديد", style=discord.ButtonStyle.green)
    async def start_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎮 اختر اللعبة:", view=CreateTradeSelection(), ephemeral=True)

class CreateTradeSelection(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=g, value=g) for g in GAMES_DATA.keys()]
        self.add_item(self.GameSelect(options))

    class GameSelect(discord.ui.Select):
        def __init__(self, options): super().__init__(placeholder="اختر اللعبة...", options=options)
        async def callback(self, interaction: discord.Interaction):
            game = self.values[0]
            view = discord.ui.View()
            mode_opts = [discord.SelectOption(label=m, value=m) for m in GAMES_DATA[game]]
            mode_sel = discord.ui.Select(placeholder="اختر الطور...", options=mode_opts)
            
            async def m_callback(inter):
                await inter.response.send_modal(TradeForm(game=game, mode=mode_sel.values[0]))
                await inter.delete_original_response() # حذف القائمة بعد فتح النموذج
                
            mode_sel.callback = m_callback
            view.add_item(mode_sel)
            await interaction.response.edit_message(content=f"✅ حدد الطور في **{game}**:", view=view)

class TradeForm(discord.ui.Modal):
    def __init__(self, game, mode):
        super().__init__(title="إنشاء عرض جديد")
        self.game, self.mode = game, mode
        self.item = discord.ui.TextInput(label='الغرض المعروض')
        self.req = discord.ui.TextInput(label='المطلوب مقابلها')
        self.add_item(self.item); self.add_item(self.req)

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(bot.offers_channel_id)
        # تنسيق العرض كقسم واضح
        embed = discord.Embed(title="📦 عرض مقايضة جديد", color=0x2f3136)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        
        # إضافة الأقسام بشكل مرئي
        embed.description = f"**━━━━━━━━━━━━━━━**\n** القسم: {self.game} | الطور: {self.mode} **\n**━━━━━━━━━━━━━━━**"
        
        embed.add_field(name="📤 يملك:", value=f"```\n{self.item.value}\n```", inline=False)
        embed.add_field(name="📥 يطلب:", value=f"```\n{self.req.value}\n```", inline=False)
        
        embed.set_footer(text=f"ID: {interaction.user.id} • للتواصل مع صاحب العرض اضغط على المنشن")
        
        await channel.send(content=f"🔔 عرض جديد في قسم **#{self.game}**", embed=embed)
        await interaction.response.send_message("✅ نُشر عرضك بنجاح!", ephemeral=True)

# --- إعدادات البوت الأساسية ---
class TradeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.offers_channel_id = None 
    async def setup_hook(self): await self.tree.sync()

bot = TradeBot()

@bot.tree.command(name="setup_form")
async def setup_form(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 سوق المقايضات", description="لإضافة عرضك الخاص في الرومات المخصصة اضغط الزر بالأسفل.", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=FormView())
    await interaction.response.send_message("✅ تم تفعيل نظام الإضافة.", ephemeral=True)

@bot.tree.command(name="setup_filter")
async def setup_filter(interaction: discord.Interaction):
    embed = discord.Embed(title="🔍 تصفية سريعة", description="اختر اللعبة والطور لتظهر لك روابط العروض فوراً في رسالة خاصة.", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=FilterView())
    await interaction.response.send_message("✅ تم تفعيل نظام التصفية.", ephemeral=True)

@bot.tree.command(name="set_offers_channel")
async def set_offers(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.offers_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم تحديد روم العروض: {channel.mention}", ephemeral=True)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.getenv('DISCORD_TOKEN'))
