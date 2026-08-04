import asyncio
import discord
from discord.ext import commands

# 1. إعداد الـ Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="+", intents=intents)

# ---------------------------------------------------------
# الإعدادات العامة والأيدي (IDs)
# ---------------------------------------------------------
BOT_ADMIN_ID = 1241496820455313533
DEVELOPER_NAME = "JrOmar"

# 🆔 أيدي الروم المخصصة لأمر الـ Tax
TAX_CHANNEL_ID = 1533847382742011964

# 🆔 أيدي روم الترحيب (Welcome Room ID)
WELCOME_CHANNEL_ID = 1533855396433760287

# 🆔 أيدي الرولات (Role IDs) المخصصة لكل أمر
COME_ROLES = [1533850449705308210]  # رولات أمر /come
LINE_ROLES = [1533850521285300335]  # رولات أمر /line
BC_ROLES = [1533850549261439157]  # رولات أوامر الإعلانات /bc و /bc_dm


# دالة للتحقق من الرولات والصلاحيات
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


@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print("Synced global slash commands successfully!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    print("==========================================")
    print(f"System Bot is online as: {bot.user.name}")
    print(f"Developer: {DEVELOPER_NAME}")
    print("==========================================")


# ---------------------------------------------------------
# حدث الترحيب (Welcome Event)
# ---------------------------------------------------------
@bot.event
async def on_member_join(member: discord.Member):
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    embed = discord.Embed(
        title="👋 مرحباً بك في السيرفر!",
        description=f"أهلاً بك يا {member.mention} في سيرفر **{member.guild.name}**!\n\nنتمنى لك قضاء وقت ممتع معنا، ولا تنسَ قراءة القوانين.",
        color=discord.Color.blurple(),
    )

    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    else:
        embed.set_thumbnail(url=member.default_avatar.url)

    embed.set_footer(
        text=f"العضو رقم: {member.guild.member_count}",
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )

    await channel.send(content=f"Welcome {member.mention}! 🎉", embed=embed)


# ---------------------------------------------------------
# 1. أمر الـ Tax
# ---------------------------------------------------------
@bot.tree.command(name="tax", description="حساب ضريبة التحويل ProBot 5%")
@discord.app_commands.describe(
    amount="المبلغ المراد حسابه (مثال: 100k أو 50000)"
)
async def calculate_tax(interaction: discord.Interaction, amount: str):
    if interaction.channel.id != TAX_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ عذراً، أمر الـ Tax مسموح به فقط في روم <#{TAX_CHANNEL_ID}>!",
            ephemeral=True,
        )
        return

    try:
        clean_amount = (
            amount.lower()
            .replace("k", "000")
            .replace("m", "000000")
            .replace(",", "")
        )
        number = int(clean_amount)

        if number <= 0:
            await interaction.response.send_message(
                "❌ يرجى إدخال مبلغ صحيح أكبر من 0.", ephemeral=True
            )
            return

        with_tax = int(number / 0.95) + 1
        tax_only = with_tax - number

        embed = discord.Embed(
            title="💳 حاسبة ضريبة ", color=discord.Color.green()
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
            name="📉 قيمة الضريبة (5%):", value=f"`{tax_only:,}`", inline=False
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    except ValueError:
        await interaction.response.send_message(
            "❌ صيغة المبلغ غير صحيحة! مثال: `50k` أو `10000`.", ephemeral=True
        )


# ---------------------------------------------------------
# 2. أمر /come
# ---------------------------------------------------------
@bot.tree.command(
    name="come", description="إرسال طلب حضور (استدعاء) لعضو في الخاص"
)
@discord.app_commands.describe(user_id="أيدي العضو المراد استدعاؤه")
@check_roles(COME_ROLES)
async def come_user(interaction: discord.Interaction, user_id: str):
    try:
        uid = int(user_id)
        member = await interaction.guild.fetch_member(uid)
        if not member:
            await interaction.response.send_message(
                "❌ هذا العضو غير موجود في هذا السيرفر.", ephemeral=True
            )
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
            await interaction.response.send_message(
                f"✅ تم إرسال طلب الحضور إلى {member.mention} في الخاص!"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ ما قدرتش نصيفط لـ {member.mention} فـ الخاص حيت ساد الـ DM.",
                ephemeral=True,
            )

    except ValueError:
        await interaction.response.send_message(
            "❌ يرجى إدخال أيدي (ID) صحيح للعضو.", ephemeral=True
        )
    except discord.NotFound:
        await interaction.response.send_message(
            "❌ لم يتم العثور على هذا العضو فـ السيرفر.", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ حدث خطأ: `{e}`", ephemeral=True
        )


# ---------------------------------------------------------
# 3. أمر /line
# ---------------------------------------------------------
@bot.tree.command(name="line", description="إرسال خط فاصل بصورة في الشات")
@discord.app_commands.describe(image_url="رابط الصورة المراد إرسالها")
@check_roles(LINE_ROLES)
async def send_line(interaction: discord.Interaction, image_url: str):
    try:
        await interaction.response.send_message(image_url)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ ما قدرتش نرسل الخط. تأكد من الرابط. الخطأ: `{e}`",
            ephemeral=True,
        )


# ---------------------------------------------------------
# 4. أوامر الـ Broadcast
# ---------------------------------------------------------
@bot.tree.command(name="bc", description="إرسال إعلان لشات معين مع صورة")
@discord.app_commands.describe(
    channel="الشات المراد الإرسال فيه",
    title="عنوان الإعلان",
    message="نص الإعلان",
    image_url="رابط الصورة (اختياري)",
)
@check_roles(BC_ROLES)
async def broadcast_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    title: str,
    message: str,
    image_url: str = None,
):
    try:
        embed = discord.Embed(
            title=title, description=message, color=discord.Color.gold()
        )
        embed.set_footer(text=f"Sent by {interaction.user.display_name}")

        if image_url:
            embed.set_image(url=image_url)

        await channel.send(embed=embed)
        await interaction.response.send_message(
            f"✅ تم الإرسال في {channel.mention} بنجاح!", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ خطأ: `{e}`", ephemeral=True
        )


@bot.tree.command(
    name="bc_dm", description="إرسال إعلان لجميع أعضاء السيرفر في الخاص"
)
@discord.app_commands.describe(message="نص الإعلان المراد إرساله")
@check_roles(BC_ROLES)
async def broadcast_dm(interaction: discord.Interaction, message: str):
    members = [m for m in interaction.guild.members if not m.bot]

    await interaction.response.send_message(
        f"⏳ جاري الإرسال إلى **{len(members)}** عضو في الخاص...", ephemeral=True
    )

    success = 0
    failed = 0

    embed = discord.Embed(
        title=f"🔔 إعلان من {interaction.guild.name}",
        description=message,
        color=discord.Color.blue(),
    )

    for member in members:
        try:
            await member.send(embed=embed)
            success += 1
            await asyncio.sleep(1)
        except Exception:
            failed += 1

    await interaction.edit_original_response(
        content=f"✅ **اكتمل الإرسال!**\n📥 نجح: `{success}` | ❌ فشل: `{failed}`"
    )


# ---------------------------------------------------------
# 5. أمر مسح جميع الرسائل في الروم مع زر التأكيد (ms7)
# ---------------------------------------------------------
class ConfirmDeleteAll(discord.ui.View):

    def __init__(self, author: discord.Member):
        super().__init__(timeout=30)
        self.author = author

    @discord.ui.button(
        label="تأكيد الحذف", style=discord.ButtonStyle.danger, emoji="🗑️"
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ ليس مسموحاً لك استخدام هذا الزر.", ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="⏳ جاري مسح جميع رسائل الروم...", view=None
        )
        try:
            deleted = await interaction.channel.purge(limit=None)
            # رسالة مؤقتة تخبره بعدد الرسائل المحذوفة ثم تختفي
            temp_msg = await interaction.channel.send(
                f"✅ تم مسح `{len(deleted)}` رسالة بنجاح!"
            )
            await asyncio.sleep(3)
            await temp_msg.delete()
        except Exception as e:
            await interaction.followup.send(
                f"❌ حدث خطأ أثناء الحذف: {e}", ephemeral=True
            )

    @discord.ui.button(
        label="إلغاء", style=discord.ButtonStyle.secondary, emoji="❌"
    )
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ ليس مسموحاً لك استخدام هذا الزر.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content="❌ تم إلغاء عملية الحذف.", view=None
        )


@bot.tree.command(name="ms7", description="مسح جميع الرسائل في الروم الحالية")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def ms7_all(interaction: discord.Interaction):
    view = ConfirmDeleteAll(interaction.user)
    await interaction.response.send_message(
        "⚠️ **هل أنت متأكد من أنك تريد حذف جميع رسائل هذه الروم؟**",
        view=view,
        ephemeral=True,
    )


# ---------------------------------------------------------
# 6. أمر مسح عدد معين من الرسائل (ms7 عدد)
# ---------------------------------------------------------
@bot.tree.command(
    name="ms7_count",
    description="مسح عدد محدد من الرسائل فوق رسالة الأمر",
)
@discord.app_commands.describe(count="عدد الرسائل المراد حذفها")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def mss7_count(interaction: discord.Interaction, count: int):
    if count <= 0:
        await interaction.response.send_message(
            "❌ يرجى إدخال عدد أكبر من 0.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    try:
        # يتم مسح العدد المطلوب + 1 (لإزالة رسالة الأمر نفسه أيضاً لتكون نظيفة)
        deleted = await interaction.channel.purge(limit=count + 1)
        temp_msg = await interaction.channel.send(
            f"✅ تم مسح `{len(deleted) - 1}` رسالة بنجاح!"
        )
        await asyncio.sleep(3)
        await temp_msg.delete()
    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ: {e}", ephemeral=True)


# ---------------------------------------------------------
# 7. أمر فتح الروم (7l)
# ---------------------------------------------------------
@bot.tree.command(name="7l", description="فتح الروم لتسمح للأعضاء بالكتابة فيها")
@discord.app_commands.checks.has_permissions(manage_channels=True)
async def open_channel(interaction: discord.Interaction):
    try:
        await interaction.channel.set_permissions(
            interaction.guild.default_role, send_messages=True
        )
        embed = discord.Embed(
            title="🔓 تم فتح الروم",
            description="يمكن لجميع الأعضاء الآن التحدث والكتابة في هذه الروم.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ حدث خطأ أثناء فتح الروم: {e}", ephemeral=True
        )


# ---------------------------------------------------------
# 8. أمر إغلاق الروم (sd)
# ---------------------------------------------------------
@bot.tree.command(name="sd", description="إغلاق الروم لمنع الأعضاء من التحدث فيها")
@discord.app_commands.checks.has_permissions(manage_channels=True)
async def close_channel(interaction: discord.Interaction):
    try:
        await interaction.channel.set_permissions(
            interaction.guild.default_role, send_messages=False
        )
        embed = discord.Embed(
            title="🔒 تم إغلاق الروم",
            description="تم منع الأعضاء من الكتابة في هذه الروم.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ حدث خطأ أثناء إغلاق الروم: {e}", ephemeral=True
        )


# ⚠️ التوكن الخاص بك
bot.run(os.environ.get("BOT_TOKEN"))