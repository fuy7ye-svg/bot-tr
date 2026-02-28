import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- سيرفر ويب ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- البيانات ---
GAMES_DATA = {
    "روبلوكس": ["Blox Fruits", "Blox Spin", "Pet Sim 99", "MM2"],
    "فورتنايت": ["سكينات", "حسابات"],
    "ماين كرافت": ["سيرفرات", "أغراض نادرة"]
}

# --- نظام التصفية (مع حل مشكلة الاختيار المتكرر) ---
class FilterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_main_menu()

    def add_main_menu(self):
        # نقوم بإنشاء القائمة وإضافتها
        options = [discord.SelectOption(label=g, value=g) for g in GAMES_DATA.keys()]
        self.add_item(self.GameFilterSelect(options))

    class GameFilterSelect(discord.ui.Select):
        def __init__(self, options):
            # نضع placeholder واضح ليعرف المستخدم أنه يمكنه الاختيار دائماً
            super().__init__(placeholder="🎮 اختر اللعبة للبحث...", options=options, custom_id="game_select_main")

        async def callback(self, interaction: discord.Interaction):
            game = self.values[0]
            
            # 1. إنشاء قائمة الأطوار
            view = discord.ui.View(timeout=None)
            mode_options = [discord.SelectOption(label=m, value=m) for m in GAMES_DATA[game]]
            mode_sel = discord.ui.Select(placeholder=f"🕹️ اختر الطور في {game}...", options=mode_options)
            
            async def mode_callback(inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                selected_mode = mode_sel.values[0]
                
                # البحث عن النتائج
                if not bot.offers_channel_id:
                    return await inter.followup.send("❌ روم العروض غير محدد!", ephemeral=True)
                
                channel = inter.guild.get_channel(bot.offers_channel_id)
                found_links = []
                async for message in channel.history(limit=150):
                    if message.embeds:
                        for embed in message.embeds:
                            content = f"{embed.title} " + " ".join([f.value for f in embed.fields])
                            if selected_mode.lower() in content.lower():
                                found_links.append(message.jump_url)
                
                if found_links:
                    results = "\n".join([f"🔹 [اضغط هنا للعرض]({url})" for url in found_links[:10]])
                    await inter.followup.send(f"✅ عروض **{selected_mode}**:\n{results}", ephemeral=True)
                else:
                    await inter.followup.send(f"❌ لا توجد عروض حالياً في **{selected_mode}**.", ephemeral=True)

            mode_sel.callback = mode_callback
            view.add_item(mode_sel)
            
            # 2. السر هنا: تحديث الرسالة الأصلية لتعود القائمة لوضعها الافتراضي (Reset)
            # نقوم بإعادة إنشاء الـ View الأصلي لكي لا يظهر الخيار كأنه "مختار"
            await interaction.response.edit_message(view=FilterView())
            
            # 3. إرسال قائمة الأطوار في رسالة خاصة
            await interaction.followup.send(f"🔎 تصفية **{game}**: اختر الطور:", view=view, ephemeral=True)

# --- نظام إضافة العروض (مع إعادة التعيين أيضاً) ---
class FormView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ إضافة عرضك الجديد", style=discord.ButtonStyle.green)
    async def start_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        # إظهار القائمة في رسالة خاصة لضمان عدم تداخل الخيارات
        view = CreateTradeSelection()
        await interaction.response.send_message("🎮 اختر اللعبة للإعلان فيها:", view=view, ephemeral=True)

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
            view = discord.ui.View()
            mode_opts = [discord.SelectOption(label=m, value=m) for m in GAMES_DATA[game]]
            mode_sel = discord.ui.Select(placeholder="اختر الطور...", options=mode_opts)
            
            async def m_callback(inter):
                await inter.response.send_modal(TradeForm(game=game, mode=mode_sel.values[0]))
                # حذف القائمة بعد الاختيار لتنظيف الشاشة
                await inter.delete_original_response()
                
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
        embed = discord.Embed(title="📦 عرض مقايضة جديد", color=0x2f3136)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        embed.description = f"**━━━━━━━━━━━━━━━**\n** القسم: {self.game} | الطور: {self.mode} **\n**━━━━━━━━━━━━━━━**"
        embed.add_field(name="📤 يملك:", value=f"```\n{self.item.value}\n```", inline=False)
        embed.add_field(name="📥 يطلب:", value=f"```\n{self.req.value}\n```", inline=False)
        
        await channel.send(content=f"🔔 عرض جديد في قسم **#{self.game}**", embed=embed)
        await interaction.response.send_message("✅ نُشر عرضك بنجاح!", ephemeral=True)

# --- إعدادات البوت ---
class TradeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.offers_channel_id = None 
    async def setup_hook(self): await self.tree.sync()

bot = TradeBot()

@bot.tree.command(name="setup_form")
async def setup_form(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(title="🛒 سوق المقايضات", description="اضغط الزر لإضافة عرضك."), view=FormView())
    await interaction.response.send_message("✅ تم.", ephemeral=True)

@bot.tree.command(name="setup_filter")
async def setup_filter(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(title="🔍 تصفية سريعة", description="اختر اللعبة والطور فوراً."), view=FilterView())
    await interaction.response.send_message("✅ تم.", ephemeral=True)

@bot.tree.command(name="set_offers_channel")
async def set_offers(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.offers_channel_id = channel.id
    await interaction.response.send_message(f"✅ تم تحديد روم العروض: {channel.mention}", ephemeral=True)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.getenv('DISCORD_TOKEN'))
