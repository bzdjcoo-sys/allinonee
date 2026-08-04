import asyncio
import os
import random
import re
import discord
from discord.ext import commands

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

TAX_CHANNEL_ID = 1534238494015361104
COME_ROLES = [1534238229002191060]
LINE_ROLES = [1534238250158526644]
BC_ROLES = [1534238273440977006]

TICKET_STAFF_ROLE_ID = 1534294981727227944
TICKET_CATEGORY_ID = 1534294859320525031

# ---------------------------------------------------------
# 🎵 الـ Playlists والروابط المباشرة للاغاني
# ---------------------------------------------------------
MUSIC_PLAYLISTS = {
    "playlist_1": {
        "name": "🎧 Chill & Relax Hits",
        "description": "موسيقى هادئة للاسترخاء والتركيز",
        "tracks": [
            {"title": "Chill Vibes Radio 24/7", "url": "https://stream.zeno.fm/f3wvbbqmdg8uv"},
            {"title": "Lo-Fi Beats Station", "url": "https://stream.zeno.fm/0r0xa792kwzuv"}
        ]
    },
    "playlist_2": {
        "name": "🔥 Gaming & Bass Boosted",
        "description": "أغاني حماسية للألعاب والـ Gaming",
        "tracks": [
            {"title": "FIP Radio Smooth Hits", "url": "https://icecast.radiofrance.fr/fip-midfi.mp3"},
            {"title": "NCS Style Energy Stream", "url": "https://stream.zeno.fm/f3wvbbqmdg8uv"}
        ]
    },
    "playlist_3": {
        "name": "📻 Pop & Top Charts Radio",
        "description": "أحدث الأغاني والراديو العالمي",
        "tracks": [
            {"title": "BBC Radio 1 Hits", "url": "http://stream.live.vc.bbcmedia.co.uk/bbc_radio_one"},
            {"title": "Global Hits Station", "url": "https://icecast.radiofrance.fr/fip-midfi.mp3"}
        ]
    }
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# متغيّرات عامة لتتبع الأغنية الحالية والـ Voice Client
current_track_info = {"title": "No music playing", "url": "None"}
active_playlist_key = "playlist_1"


def check_roles(allowed_roles):
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id == BOT_ADMIN_ID or interaction.user.guild_permissions.administrator:
            return True

        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except Exception:
            member = interaction.user

        user_role_ids = [role.id for role in member.roles]
        if any(role_id in allowed_roles for role_id in user_role_ids):
            return True

        await interaction.response.send_message("⛔ **عذراً!** ليس لديك الرتبة المخصصة لاستخدام هذا الأمر.", ephemeral=True)
        return False

    return discord.app_commands.check(predicate)


# ---------------------------------------------------------
# 🎛️ لوحة تحكم الموسيقى (LunaBot Style Player Panel)
# ---------------------------------------------------------
def create_music_embed(guild):
    embed = discord.Embed(
        title="🎵 Luna Music Player | لوحة تشغيل الموسيقى",
        description=f"**🔊 الأغنية الشغالة حالياً:**\n▶️ `{current_track_info['title']}`\n\n"
                    f"**📋 قوائم الموسيقى المتاحة (Playlists):**\n"
                    f"1️⃣ **Playlist 1:** Chill & Relax Hits\n"
                    f"2️⃣ **Playlist 2:** Gaming & Bass Boosted\n"
                    f"3️⃣ **Playlist 3:** Pop & Top Charts Radio",
        color=discord.Color.purple()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="اختر Playlist من القائمة أسفله أو استعمل الأزراز للتحكم فـ الموسيقى")
    return embed


class PlaylistSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Playlist 1: Chill Hits", value="playlist_1", description="Chill & Relax Beats", emoji="🎧"),
            discord.SelectOption(label="Playlist 2: Gaming Hits", value="playlist_2", description="Bass & High Energy Music", emoji="🔥"),
            discord.SelectOption(label="Playlist 3: Radio Hits", value="playlist_3", description="BBC & Global Radio Charts", emoji="📻")
        ]
        super().__init__(placeholder="🎵 اختر Playlist لتغير نوع الموسيقى...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        global active_playlist_key
        active_playlist_key = self.values[0]
        vc = interaction.guild.voice_client

        if vc and vc.is_connected():
            if vc.is_playing() or vc.is_paused():
                vc.stop()  # سيتم الانتقال تلقائياً للأغنية التالية من الـ Playlist الجديدة
            await interaction.response.edit_message(content=f"✅ تم تغيير الـ Playlist إلى **{MUSIC_PLAYLISTS[active_playlist_key]['name']}**", embed=create_music_embed(interaction.guild))
        else:
            await interaction.response.send_message("❌ البوت غير متصل بأي روم صوتية حالياً!", ephemeral=True)


class MusicControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PlaylistSelect())

    @discord.ui.button(label="Pause / Play", style=discord.ButtonStyle.primary, emoji="⏯️", custom_id="music_pause_play")
    async def pause_play(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            await interaction.response.send_message("❌ البوت غير متصل بالروم الصوتية!", ephemeral=True)
            return

        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ تم إيقاف الموسيقى مؤقتاً (Paused).", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ تم استئناف تشغيل الموسيقى (Resumed).", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لا توجد موسيقى شغالة حالياً.", ephemeral=True)

    @discord.ui.button(label="Pass / Skip", style=discord.ButtonStyle.secondary, emoji="⏭️", custom_id="music_skip")
    async def skip_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ تم تخطي الأغنية الحالية وتغيير الموسيقى!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لا توجد أغنية لتخطيها.", ephemeral=True)

    @discord.ui.button(label="Stop / Leave", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="music_stop")
    async def stop_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            await vc.disconnect()
            await interaction.response.send_message("⏹️ تم إيقاف الموسيقى وإخراج البوت من الروم الصوتية.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ البوت غير متصل بأي روم صوتية.", ephemeral=True)

    @discord.ui.button(label="Give Link", style=discord.ButtonStyle.success, emoji="🔗", custom_id="music_link")
    async def give_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        if current_track_info["url"] != "None":
            await interaction.response.send_message(
                f"🔗 **رابط الموسيقى الشغالة حالياً:**\n📌 **الاسم:** `{current_track_info['title']}`\n🌐 **الرابط:** {current_track_info['url']}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ لا تتوفر أي أغنية شغالة حالياً للحصول على رابطها.", ephemeral=True)


async def play_playlist_loop(vc: discord.VoiceClient, interaction: discord.Interaction):
    """دالة تدوير وتشغيل الموسيقى"""
    global current_track_info
    while vc and vc.is_connected():
        if not vc.is_playing() and not vc.is_paused():
            try:
                playlist_data = MUSIC_PLAYLISTS.get(active_playlist_key, MUSIC_PLAYLISTS["playlist_1"])
                selected_track = random.choice(playlist_data["tracks"])
                
                current_track_info = selected_track
                
                source = discord.FFmpegPCMAudio(selected_track["url"], **ffmpeg_options)
                vc.play(source)

                # تحديث البنل بالمعلومات الجديدة
                try:
                    await interaction.edit_original_response(embed=create_music_embed(interaction.guild), view=MusicControlView())
                except Exception:
                    pass

            except Exception as e:
                print(f"Error in music loop: {e}")
        
        await asyncio.sleep(4)


@bot.tree.command(name="join_voice", description="إدخال البوت للروم الصوتية وإظهار بنل التحكم فـ الموسيقى")
@discord.app_commands.describe(channel="الروم الصوتية المراد إدخال البوت إليها")
@discord.app_commands.checks.has_permissions(administrator=True)
async def join_voice(interaction: discord.Interaction, channel: discord.VoiceChannel):
    await interaction.response.defer()
    try:
        vc = interaction.guild.voice_client
        if vc:
            if vc.channel.id != channel.id:
                await vc.move_to(channel)
        else:
            vc = await channel.connect(reconnect=True, timeout=20.0)

        if vc.is_playing():
            vc.stop()

        bot.loop.create_task(play_playlist_loop(vc, interaction))

        await interaction.followup.send(embed=create_music_embed(interaction.guild), view=MusicControlView())
    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ أثناء الاتصال بالروم: `{e}`", ephemeral=True)


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
        member = interaction.user
        user_role_ids = [role.id for role in member.roles]

        is_staff = (
            TICKET_STAFF_ROLE_ID in user_role_ids 
            or member.guild_permissions.administrator 
            or member.id == BOT_ADMIN_ID
        )

        if not is_staff:
            await interaction.response.send_message("⛔ **عذراً!** فقط أعضاء طاقم الدعم هم من يمكنهم إغلاق التيكيت.", ephemeral=True)
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
# Event On Ready & Bot Events
# ---------------------------------------------------------
@bot.event
async def on_ready():
    bot.add_view(TicketLaunchView())
    bot.add_view(TicketControlView())
    bot.add_view(MusicControlView())

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
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id == TAX_CHANNEL_ID:
        content = message.content.strip().lower()

        if re.match(r"^\d+(\.\d+)?[kmb]?$", content):
            try:
                clean_amount = content.replace("k", "000").replace("m", "000000").replace("b", "000000000").replace(",", "")
                number = int(float(clean_amount))

                if number > 0:
                    with_tax = int(number / 0.95) + 1
                    tax_only = with_tax - number

                    embed = discord.Embed(title="💳 حاسبة ضريبة تلقائية", color=discord.Color.green())
                    embed.add_field(name="💵 المبلغ المطلوب وصوله:", value=f"`{number:,}`", inline=False)
                    embed.add_field(name="💰 المبلغ الذي يجب تحويله (مع الضريبة):", value=f"`{with_tax:,}`", inline=False)
                    embed.add_field(name="📉 قيمة الضريبة (5%):", value=f"`{tax_only:,}`", inline=False)
                    embed.set_footer(text=f"Requested by {message.author.display_name}")

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
        await interaction.response.send_message(f"❌ عذراً، أمر الـ Tax مسموح به فقط في روم <#{TAX_CHANNEL_ID}>!", ephemeral=True)
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
        await interaction.response.send_message(f"❌ ما قدرتش نرسل الخط: `{e}`", ephemeral=True)


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
