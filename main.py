import asyncio
import os
import random
import re
import discord
from discord.ext import commands
import yt_dlp

# ---------------------------------------------------------
# 1. إعداد الـ Intents
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="+", intents=intents)

# ---------------------------------------------------------
# الإعدادات العامة والأيدي (IDs)
# ---------------------------------------------------------
BOT_ADMIN_ID = 1241496820455313533
DEVELOPER_NAME = "JrOmar"

# 🆔 أيدي الروم المخصصة لأمر والـ Auto-Tax
TAX_CHANNEL_ID = 1534238494015361104

# 🆔 أيدي الرولات (Role IDs) المخصصة لكل أمر
COME_ROLES = [1534238229002191060]   # رولات أمر /come
LINE_ROLES = [1534238250158526644]   # رولات أمر /line
BC_ROLES = [1534238273440977006]     # رولات أوامر الإعلانات /bc و /bc_dm

# 🆔 إعدادات نظام التيكيت
TICKET_STAFF_ROLE_ID = 1534238229002191060
TICKET_CATEGORY_ID = None

# 🎵 قائمة الأغاني العشوائية
RANDOM_PLAYLIST = [
    "https://www.youtube.com/watch?v=5qap5aO4i9A",
    "https://www.youtube.com/watch?v=DWcJFNfaw9c",
    "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
    "https://www.youtube.com/watch?v=fJ9rUzIMcZQ"
]

# خيارات yt-dlp & ffmpeg
ytdl_format_options = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


def check_roles(allowed_roles):
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id == BOT_ADMIN_ID:
            return True
        if interaction.user.guild_permissions.administrator:
            return True

        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except Exception:
            member = interaction.user

        user_role_ids = [role.id for role in member.roles]

        if any(role_id in allowed_roles for role_id in user_role_ids):
            return True

        await interaction.response.send_message(
            "⛔ **عذراً!** ليس لديك الرتبة المخصصة لاستخدام هذا الأمر.",
            ephemeral=True,
        )
        return False

    return discord.app_commands.check(predicate)


# ---------------------------------------------------------
# 🎧 نظام تشغيل الأغاني العشوائية والمكوث في الـ Voice
# ---------------------------------------------------------
async def play_random_music(vc: discord.VoiceClient):
    """تشغيل أغنية عشوائية فـ الروم وباش يسالي يعاود يطلق أغانٍ أخرى تلقائياً"""
    while vc and vc.is_connected():
        if not vc.is_playing():
            try:
                song_url = random.choice(RANDOM_PLAYLIST)
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(song_url, download=False))
                
                if 'entries' in data:
                    data = data['entries'][0]
                
                stream_url = data['url']
                source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)
                vc.play(source)
            except Exception as e:
                print(f"Error playing voice music: {e}")
        
        await asyncio.sleep(2)


@bot.tree.command(name="join_voice", description="إدخال البوت لروم صوتية والبدء بتشغيل أغانٍ عشوائية تلقائياً")
@discord.app_commands.describe(channel="روم الصوت المراد إدخال البوت لها (اختر الروم)")
@discord.app_commands.checks.has_permissions(administrator=True)
async def join_voice(interaction: discord.Interaction, channel: discord.VoiceChannel):
    await interaction.response.defer(ephemeral=True)
    try:
        vc = interaction.guild.voice_client
        if vc:
            await vc.move_to(channel)
        else:
            vc = await channel.connect(reconnect=True)

        # يوقف أي حاجة خدامة ويطلق الموسيقى المباشرة
        if vc.is_playing():
            vc.stop()

        bot.loop.create_task(play_random_music(vc))

        await interaction.followup.send(f"✅ تم دخول البوت إلى {channel.mention} وبدأت الموسيقى التلقائية فوراً!")
    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ أثناء الاتصال بالروم: `{e}`")


@bot.tree.command(name="leave_voice", description="إخراج البوت من الروم الصوتية")
@discord.app_commands.checks.has_permissions(administrator=True)
async def leave_voice(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message("✅ تم إخراج البوت من الروم الصوتية.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ البوت غير متصل بأي روم صوتية حالياً.", ephemeral=True)


# ---------------------------------------------------------
# 🛠️ نظام الـ Dual Ticket (نظام التيكيت المزدوجة)
# ---------------------------------------------------------
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إغلاق / Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # التحقق من أن المستخدم لديه رتبة الدعم أو أدمين
        member = interaction.user
        user_role_ids = [role.id for role in member.roles]

        is_staff = (
            TICKET_STAFF_ROLE_ID in user_role_ids 
            or member.guild_permissions.administrator 
            or member.id == BOT_ADMIN_ID
        )

        if not is_staff:
            await interaction.response.send_message(
                "⛔ **عذراً!** فقط أعضاء طاقم الدعم (Ticket Support) هم من يمكنهم إغلاق التيكيت.", 
                ephemeral=True
            )
            return

        await interaction.response.send_message("🔒 سيتم إغلاق التيكيت خلال 5 ثوانٍ...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="حفظ السجل / Transcript", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="ticket_transcript")
    async def transcript_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        messages = [message async for message in interaction.channel.history(limit=500, oldest_first=True)]
        
        transcript_text = f"--- Ticket Transcript for {interaction.channel.name} ---\n\n"
        for msg in messages:
            transcript_text += f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author}: {msg.content}\n"

        file_path = f"transcript_{interaction.channel.id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        await interaction.followup.send(file=discord.File(file_path), ephemeral=True)
        os.remove(file_path)


class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        user = interaction.user

        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        staff_role = guild.get_role(TICKET_STAFF_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"{'📩' if ticket_type == 'general' else '🛒'}-{ticket_type}-{user.name}"
        
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"🎫 تيكيت جديدة | {ticket_type.capitalize()} Ticket",
            description=f"مرحباً بك {user.mention}!\nيرجى كتابة مشكلتك أو طلبك وسيتم الرد عليك من قبل الإدارة قريباً.\n\n"
                        f"• **النوع:** `{ticket_type.upper()}`\n"
                        f"• **صاحب التيكيت:** {user.mention}",
            color=discord.Color.blue() if ticket_type == "general" else discord.Color.gold()
        )
        embed.set_footer(text=f"Ticket Tool System | Requested by {user.display_name}")

        staff_mention = staff_role.mention if staff_role else ""
        await ticket_channel.send(content=f"{user.mention} {staff_mention}", embed=embed, view=TicketControlView())

        await interaction.response.send_message(f"✅ تم إنشاء التيكيت بنجاح: {ticket_channel.mention}", ephemeral=True)

    @discord.ui.button(label="الدعم العام / General Support", style=discord.ButtonStyle.primary, emoji="📩", custom_id="ticket_general")
    async def open_general_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "general")

    @discord.ui.button(label="قسم الشراء / Buy Ticket", style=discord.ButtonStyle.success, emoji="🛒", custom_id="ticket_buy")
    async def open_buy_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "buy")


@bot.tree.command(name="setup_ticket", description="إرسال بنل التيكيت المزدوجة فـ الروم الحالية")
@discord.app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 مركز الدعم والخدمات / Support & Purchase Center",
        description="مرحباً بك! لاختيار الخدمة المناسبة يرجى الضغط على أحد الأزرار أسفله:\n\n"
                    "📩 **الدعم العام:** للاستفسارات العامة، المشاكل، أو تقديم بلاغ.\n"
                    "🛒 **قسم الشراء:** للطلبات، شراء المنتجات، أو الخدمات.",
        color=discord.Color.blue()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
        
    embed.set_footer(text=f"{interaction.guild.name} • Ticket System")

    await interaction.channel.send(embed=embed, view=TicketLaunchView())
    await interaction.response.send_message("✅ تم إرسال لوحة التيكيت بنجاح!", ephemeral=True)


# ---------------------------------------------------------
# Event On Ready & Errors Handling
# ---------------------------------------------------------
@bot.event
async def on_ready():
    bot.add_view(TicketLaunchView())
    bot.add_view(TicketControlView())

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} global slash command(s) successfully!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    print("==========================================")
    print(f"System Bot is online as: {bot.user.name}")
    print(f"Developer: {DEVELOPER_NAME}")
    print("==========================================")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


# ---------------------------------------------------------
# التفاعل التلقائي مع حساب الضريبة (Auto-Tax on Message)
# ---------------------------------------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id == TAX_CHANNEL_ID:
        content = message.content.strip().lower()

        if re.match(r"^\d+(\.\d+)?[kmb]?$", content):
            try:
                clean_amount = (
                    content.replace("k", "000")
                    .replace("m", "000000")
                    .replace("b", "000000000")
                    .replace(",", "")
                )
                number = int(float(clean_amount))

                if number > 0:
                    with_tax = int(number / 0.95) + 1
                    tax_only = with_tax - number

                    embed = discord.Embed(
                        title="💳 حاسبة ضريبة تلقائية",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name="💵 المبلغ المطلوب وصوله:",
                        value=f"`{number:,}`",
                        inline=False,
                    )
                    embed.add_field(
                        name="💰 المبلغ الذي يجب تحويله (مع الضريبة):",
                        value=f"`{with_tax:,}`",
                        inline=False,
                    )
                    embed.add_field(
                        name="📉 قيمة الضريبة (5%):",
                        value=f"`{tax_only:,}`",
                        inline=False,
                    )
                    embed.set_footer(
                        text=f"Requested by {message.author.display_name}"
                    )

                    try:
                        await message.delete()
                    except Exception:
                        pass

                    await message.channel.send(embed=embed)
            except ValueError:
                pass

    await bot.process_commands(message)


# ---------------------------------------------------------
# باقي الأوامر (Tax, Come, Line, Broadcast, Purge, Open/Close)
# ---------------------------------------------------------
@bot.tree.command(name="tax", description="حساب ضريبة التحويل ProBot 5%")
@discord.app_commands.describe(amount="المبلغ المراد حسابه (مثال: 100k أو 50000)")
async def calculate_tax(interaction: discord.Interaction, amount: str):
    if interaction.channel.id != TAX_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ عذراً، أمر الـ Tax مسموح به فقط في روم <#{TAX_CHANNEL_ID}>!",
            ephemeral=True,
        )
        return

    try:
        clean_amount = amount.lower().replace("k", "000").replace("m", "000000").replace(",", "")
        number = int(clean_amount)

        if number <= 0:
            await interaction.response.send_message("❌ يرجى إدخال مبلغ صحيح أكبر من 0.", ephemeral=True)
            return

        with_tax = int(number / 0.95) + 1
        tax_only = with_tax - number

        embed = discord.Embed(title="💳 حاسبة ضريبة", color=discord.Color.green())
        embed.add_field(name="💵 المبلغ المطلوب وصوله:", value=f"`{number:,}`", inline=False)
        embed.add_field(name="💰 المبلغ الذي يجب تحويله (مع الضريبة):", value=f"`{with_tax:,}`", inline=False)
        embed.add_field(name="📉 قيمة الضريبة (5%):", value=f"`{tax_only:,}`", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    except ValueError:
        await interaction.response.send_message("❌ صيغة المبلغ غير صحيحة! مثال: `50k` أو `10000`.", ephemeral=True)


@bot.tree.command(name="come", description="إرسال طلب حضور (استدعاء) لعضو في الخاص")
@discord.app_commands.describe(user_id="أيدي العضو المراد استدعاؤه")
@check_roles(COME_ROLES)
async def come_user(interaction: discord.Interaction, user_id: str):
    try:
        uid = int(user_id)
        member = await interaction.guild.fetch_member(uid)
        if not member:
            await interaction.response.send_message("❌ هذا العضو غير موجود في هذا السيرفر.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📩 استدعاء / Summon Request",
            description=f"سلام **{member.display_name}**، العضو **{interaction.user.mention}** يطلب حضورك الآن في سيرفر **{interaction.guild.name}**!",
            color=discord.Color.gold(),
        )

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text=f"Server: {interaction.guild.name}")

        try:
            await member.send(embed=embed)
            await interaction.response.send_message(f"✅ تم إرسال طلب الحضور إلى {member.mention} في الخاص!")
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ ما قدرتش نصيفط لـ {member.mention} فـ الخاص حيت ساد الـ DM.", ephemeral=True)

    except ValueError:
        await interaction.response.send_message("❌ يرجى إدخال أيدي (ID) صحيح للعضو.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ لم يتم العثور على هذا العضو فـ السيرفر.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ حدث خطأ: `{e}`", ephemeral=True)


@bot.tree.command(name="line", description="إرسال خط فاصل بصورة في الشات")
@discord.app_commands.describe(image_url="رابط الصورة المراد إرسالها")
@check_roles(LINE_ROLES)
async def send_line(interaction: discord.Interaction, image_url: str):
    try:
        await interaction.response.send_message(image_url)
    except Exception as e:
        await interaction.response.send_message(f"❌ ما قدرتش نرسل الخط. تأكد من الرابط. الخطأ: `{e}`", ephemeral=True)


@bot.tree.command(name="bc", description="إرسال إعلان لشات معين مع صورة")
@discord.app_commands.describe(channel="الشات المراد الإرسال فيه", title="عنوان الإعلان", message="نص الإعلان", image_url="رابط الصورة (اختياري)")
@check_roles(BC_ROLES)
async def broadcast_channel(interaction: discord.Interaction, channel: discord.TextChannel, title: str, message: str, image_url: str = None):
    try:
        embed = discord.Embed(title=title, description=message, color=discord.Color.gold())
        embed.set_footer(text=f"Sent by {interaction.user.display_name}")
        if image_url:
            embed.set_image(url=image_url)

        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ تم الإرسال في {channel.mention} بنجاح!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ: `{e}`", ephemeral=True)


@bot.tree.command(name="bc_dm", description="إرسال إعلان لجميع أعضاء السيرفر في الخاص")
@discord.app_commands.describe(message="نص الإعلان المراد إرساله")
@check_roles(BC_ROLES)
async def broadcast_dm(interaction: discord.Interaction, message: str):
    members = [m for m in interaction.guild.members if not m.bot]
    await interaction.response.send_message(f"⏳ جاري الإرسال إلى **{len(members)}** عضو في الخاص...", ephemeral=True)

    success, failed_dm_closed, failed_other = 0, 0, 0
    embed = discord.Embed(title=f"🔔 إعلان من {interaction.guild.name}", description=message, color=discord.Color.blue())

    for member in members:
        try:
            user = await bot.fetch_user(member.id)
            await user.send(embed=embed)
            success += 1
            await asyncio.sleep(2.0)
        except discord.Forbidden:
            failed_dm_closed += 1
        except discord.HTTPException as e:
            failed_other += 1
            if e.status == 429:
                retry_after = int(e.response.headers.get("Retry-After", 5))
                await asyncio.sleep(retry_after)
        except Exception:
            failed_other += 1

    result_text = f"✅ **اكتمل الإرسال!**\n📥 **نجح:** `{success}`\n🚫 **فشل (DM مغلق):** `{failed_dm_closed}`\n❌ **فشل (أخرى):** `{failed_other}`"
    await interaction.edit_original_response(content=result_text)


class ConfirmDeleteAll(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=30)
        self.author = author

    @discord.ui.button(label="تأكيد الحذف", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ ليس مسموحاً لك استخدام هذا الزر.", ephemeral=True)
            return

        await interaction.response.edit_message(content="⏳ جاري مسح جميع رسائل الروم...", view=None)
        try:
            deleted = await interaction.channel.purge(limit=None)
            temp_msg = await interaction.channel.send(f"✅ تم مسح `{len(deleted)}` رسالة بنجاح!")
            await asyncio.sleep(3)
            await temp_msg.delete()
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ أثناء الحذف: {e}", ephemeral=True)

    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ ليس مسموحاً لك استخدام هذا الزر.", ephemeral=True)
            return
        await interaction.edit_original_response(content="❌ تم إلغاء عملية الحذف.", view=None)


@bot.tree.command(name="ms7", description="مسح جميع الرسائل في الروم الحالية")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def ms7_all(interaction: discord.Interaction):
    view = ConfirmDeleteAll(interaction.user)
    await interaction.response.send_message("⚠️ **هل أنت متأكد من أنك تريد حذف جميع رسائل هذه الروم؟**", view=view, ephemeral=True)


@bot.tree.command(name="ms7_count", description="مسح عدد محدد من الرسائل فوق رسالة الأمر")
@discord.app_commands.describe(count="عدد الرسائل المراد حذفها")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def mss7_count(interaction: discord.Interaction, count: int):
    if count <= 0:
        await interaction.response.send_message("❌ يرجى إدخال عدد أكبر من 0.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=count)
        temp_msg = await interaction.channel.send(f"✅ تم مسح `{len(deleted)}` رسالة بنجاح!")
        await asyncio.sleep(3)
        await temp_msg.delete()
    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ: {e}", ephemeral=True)


@bot.tree.command(name="7l", description="فتح الروم لتسمح للأعضاء بالكتابة فيها")
@discord.app_commands.checks.has_permissions(manage_channels=True)
async def open_channel(interaction: discord.Interaction):
    try:
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        embed = discord.Embed(title="🔓 تم فتح الروم", description="يمكن لجميع الأعضاء الآن التحدث والكتابة في هذه الروم.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ حدث خطأ أثناء فتح الروم: {e}", ephemeral=True)


@bot.tree.command(name="sd", description="إغلاق الروم لمنع الأعضاء من التحدث فيها")
@discord.app_commands.checks.has_permissions(manage_channels=True)
async def close_channel(interaction: discord.Interaction):
    try:
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        embed = discord.Embed(title="🔒 تم إغلاق الروم", description="تم منع الأعضاء من الكتابة في هذه الروم.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ حدث خطأ أثناء إغلاق الروم: {e}", ephemeral=True)


# ---------------------------------------------------------
# تشغيل البوت
# ---------------------------------------------------------
bot.run(os.environ.get("BOT_TOKEN"))
