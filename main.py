import os
import random
import discord
import json
import platform
from discord.ext import commands
from discord import app_commands
from aiohttp import web
import asyncio
import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='+', intents=intents)

# Error handling for all commands
@bot.event
async def on_command_error(ctx, error):
    embed = discord.Embed(color=discord.Color.red())

    if isinstance(error, commands.MissingRequiredArgument):
        embed.title = "❌ Missing Argument"
        embed.description = f"The command `{ctx.command}` is missing the argument: `{error.param.name}`"
        embed.add_field(name="Correct Usage", value=f"`+{ctx.command.name} {ctx.command.signature}`")
    elif isinstance(error, commands.BadArgument):
        embed.title = "❌ Invalid Argument"
        embed.description = str(error)
        if ctx.command:
            embed.add_field(name="Correct Usage", value=f"`+{ctx.command.name} {ctx.command.signature}`")
    elif isinstance(error, commands.CommandNotFound):
        embed.title = "❌ Unknown Command"
        embed.description = "This command doesn't exist! Use `+help` to see all available commands."
        similar_commands = difflib.get_close_matches(ctx.message.content.split()[0][1:], [cmd.name for cmd in bot.commands], n=3)
        if similar_commands:
            embed.add_field(name="Did you mean?", value="\n".join([f"`+{cmd}`" for cmd in similar_commands]))
    elif isinstance(error, commands.MissingPermissions):
        embed.title = "❌ Missing Permissions"
        embed.description = "You don't have the required permissions to use this command!"
    elif isinstance(error, commands.CommandNotFound):
        embed.title = "❌ Unknown Command"
        embed.description = "This command doesn't exist! Use `+help` to see all available commands."
    else:
        embed.title = "❌ Error"
        embed.description = str(error)

    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        await bot.tree.sync(guild=None)  # Sync to all guilds
        print("Commands synced globally!")

        # Start web server with improved health check
        app = web.Application()

        async def health_check(request):
            if bot.is_ready():
                return web.Response(
                    text="Bot is alive and connected to Discord!",
                    status=200,
                    headers={'Cache-Control': 'no-cache'}
                )
            return web.Response(text="Bot starting up...", status=503)

        app.router.add_get("/", health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Web server started on port 5000!")
    except Exception as e:
        print(f"Failed to sync commands or start server: {e}")
        try:
            # Attempt to recover
            await asyncio.sleep(5)
            await bot.tree.sync()
            print("Commands synced after recovery!")
        except Exception as sync_error:
            print(f"Failed to sync commands after recovery: {sync_error}")
    finally:
        print("Bot startup sequence completed")

# Utility Commands
@bot.hybrid_command(name="ping", description="Shows the bot's latency")
async def ping(ctx):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="serverinfo", description="Shows server information")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Info", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner.mention)
    embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Member Count", value=guild.member_count)
    embed.add_field(name="Boost Level", value=guild.premium_tier)
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Channels", value=len(guild.channels))
    await ctx.send(embed=embed)

@bot.hybrid_command(name="userinfo", description="Shows info about a user")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles[1:]]
    embed = discord.Embed(title="User Information", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Username", value=member.name)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Roles", value=" ".join(roles) if roles else "No roles")
    await ctx.send(embed=embed)

# Fun Commands
@bot.hybrid_command(name="8ball", description="Ask the magic 8ball a question")
async def eightball(ctx, *, question: str):
    responses = [
        "It is certain.", "Without a doubt.", "Yes definitely.",
        "You may rely on it.", "As I see it, yes.", "Most likely.",
        "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
        "Cannot predict now.", "Don't count on it.", "My sources say no.",
        "Very doubtful."
    ]
    embed = discord.Embed(title="🎱 Magic 8-Ball", color=discord.Color.purple())
    embed.add_field(name="Question", value=question)
    embed.add_field(name="Answer", value=random.choice(responses))
    await ctx.send(embed=embed)

@bot.hybrid_command(name="coinflip", description="Flip a coin")
async def coinflip(ctx):
    result = random.choice(["Heads", "Tails"])
    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=f"The coin landed on: **{result}**",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="roll", description="Roll a dice (format: NdN, e.g., 2d6)")
async def roll(ctx, dice: str):
    try:
        rolls, limit = map(int, dice.split('d'))
        if rolls > 100:
            raise ValueError("Too many rolls")
        if limit > 1000:
            raise ValueError("Dice limit too high")

        results = [random.randint(1, limit) for _ in range(rolls)]
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"Rolling {rolls}d{limit}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Results", value=', '.join(map(str, results)))
        embed.add_field(name="Total", value=str(sum(results)))
        await ctx.send(embed=embed)
    except ValueError:
        embed = discord.Embed(
            title="❌ Invalid Format",
            description="Format must be NdN (e.g., 2d6)",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Moderation Commands
@bot.hybrid_command(name="clear", description="Clear messages in a channel")
@app_commands.default_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    embed = discord.Embed(
        title="🧹 Messages Cleared",
        description=f"Cleared {amount} messages",
        color=discord.Color.blue()
    )
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(5)
    await msg.delete()

@bot.hybrid_command(name="kick", description="Kick a member")
@app_commands.default_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member.top_role >= ctx.author.top_role:
        embed = discord.Embed(
            title="❌ Error",
            description="You cannot kick someone with a higher or equal role!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    await member.kick(reason=reason)
    embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.red())
    embed.add_field(name="Member", value=member.mention)
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Moderator", value=ctx.author.mention)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="ban", description="Ban a member")
@app_commands.default_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member.top_role >= ctx.author.top_role:
        embed = discord.Embed(
            title="❌ Error",
            description="You cannot ban someone with a higher or equal role!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    await member.ban(reason=reason)
    embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
    embed.add_field(name="Member", value=member.mention)
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Moderator", value=ctx.author.mention)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="timeout", description="Timeout a member")
@app_commands.default_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
    if member.top_role >= ctx.author.top_role:
        embed = discord.Embed(
            title="❌ Error",
            description="You cannot timeout someone with a higher or equal role!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    embed = discord.Embed(title="⏰ Member Timed Out", color=discord.Color.orange())
    embed.add_field(name="Member", value=member.mention)
    embed.add_field(name="Duration", value=f"{minutes} minutes")
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Moderator", value=ctx.author.mention)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="warn", description="Warn a member")
@app_commands.default_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str):
    # Check for role hierarchy
    if member.top_role >= ctx.author.top_role:
        embed = discord.Embed(title="❌ Error", description="You cannot warn someone with a higher or equal role!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Get or create warning roles
    warning_roles = {
        1: discord.utils.get(ctx.guild.roles, name="First Warning") or await ctx.guild.create_role(name="First Warning", color=discord.Color.gold()),
        2: discord.utils.get(ctx.guild.roles, name="Second Warning") or await ctx.guild.create_role(name="Second Warning", color=discord.Color.orange()),
        3: discord.utils.get(ctx.guild.roles, name="Final Warning") or await ctx.guild.create_role(name="Final Warning", color=discord.Color.red())
    }

    # Count existing warnings
    warning_count = sum(1 for role in member.roles if role.name in [r.name for r in warning_roles.values()])
    warning_count += 1

    if warning_count <= 3:
        # Add warning role
        await member.add_roles(warning_roles[warning_count])
        action = f"Received Warning #{warning_count}"
    else:
        # Fourth warning results in timeout
        await member.timeout(datetime.timedelta(minutes=10), reason="Exceeded warning limit")
        action = "Timed out for 10 minutes (Warning limit exceeded)"

    embed = discord.Embed(title="⚠️ Warning System", color=discord.Color.yellow())
    embed.add_field(name="Member", value=member.mention)
    embed.add_field(name="Warning #", value=str(warning_count))
    embed.add_field(name="Action", value=action)
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Moderator", value=ctx.author.mention)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="unwarn", description="Remove a warning from a member")
@app_commands.default_permissions(kick_members=True)
async def unwarn(ctx, member: discord.Member):
    warning_roles = ["Final Warning", "Second Warning", "First Warning"]
    removed_role = None

    for role_name in warning_roles:
        role = discord.utils.get(member.roles, name=role_name)
        if role:
            await member.remove_roles(role)
            removed_role = role
            break

    if removed_role:
        embed = discord.Embed(title="Warning Removed", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Removed Warning", value=removed_role.name)
        embed.add_field(name="Moderator", value=ctx.author.mention)
    else:
        embed = discord.Embed(title="No Warnings", color=discord.Color.blue())
        embed.description = f"{member.mention} has no warnings to remove."

    await ctx.send(embed=embed)

@bot.hybrid_command(name="unmute", description="Unmute a member")
@app_commands.default_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    if not member.is_timed_out():
        embed = discord.Embed(title="❌ Error", description=f"{member.mention} is not muted!", color=discord.Color.red())
    else:
        await member.timeout(None)
        embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="commands", description="Shows all available commands")
async def commands(ctx, command: str = None):
    if command:
        cmd = bot.get_command(command.lower())
        if cmd:
            embed = discord.Embed(
                title=f"📚 Command Help: {cmd.name}",
                description=cmd.description or "No description available",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Usage",
                value=f"`{bot.command_prefix}{cmd.name} {cmd.signature}`" if cmd.signature else f"`{bot.command_prefix}{cmd.name}`"
            )
            embed.set_footer(text=f"Tip: All commands work with both {bot.command_prefix} prefix and /")
            await ctx.send(embed=embed)
            return

    embed = discord.Embed(
        title="📚 Command List",
        description=f"Use `{bot.command_prefix}commands <command>` for detailed information about a command",
        color=discord.Color.blue()
    )

    # Organize commands by category
    categories = {
        "🛡️ Moderation": ['ban', 'kick', 'timeout', 'warn', 'unwarn', 'clear', 'slowmode', 'unmute', 'nickname', 'report'],
        "🎮 Fun": ['8ball', 'coinflip', 'roll', 'random', 'joke', 'say', 'giveaway', 'quickpoll'],
        "🔧 Utility": ['ping', 'avatar', 'remind', 'poll', 'servericon', 'roles', 'channelinfo', 'remindme', 'embed', 'invites', 'urban'],
        "📊 Statistics": ['serverinfo', 'userinfo', 'serverstats', 'botstats', 'membercount', 'channelstats', 'roleinfo'],
        "🌍 Server": ['serveremojis', 'weather', 'roles', 'serveremotes', 'firstmessage'],
        "💾 Backup": ['serverbackup', 'restorebackup']
    }

    for category, command_list in categories.items():
        commands_in_category = []
        for cmd_name in command_list:
            cmd = bot.get_command(cmd_name)
            if cmd and not cmd.hidden:
                commands_in_category.append(f"`{bot.command_prefix}{cmd.name}` - {cmd.description or 'No description'}")

        if commands_in_category:
            embed.add_field(
                name=category,
                value="\n".join(commands_in_category),
                inline=False
            )

    embed.set_footer(text=f"Total Commands: {len(bot.commands)} | All commands work with both {bot.command_prefix} and /")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="avatar", description="Shows a user's avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s Avatar", color=member.color)
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="remind", description="Sets a reminder")
async def remind(ctx, time: int, *, reminder: str):
    embed = discord.Embed(title="⏰ Reminder Set", color=discord.Color.blue())
    embed.add_field(name="Reminder", value=reminder)
    embed.add_field(name="Time", value=f"{time} minutes")
    await ctx.send(embed=embed)

    await asyncio.sleep(time * 60)
    remind_embed = discord.Embed(title="⏰ Reminder!", description=reminder, color=discord.Color.green())
    await ctx.author.send(embed=remind_embed)

@bot.hybrid_command(name="poll", description="Create a simple poll")
async def poll(ctx, question: str, options: str):
    option_list = options.split(",")
    if len(option_list) < 2:
        await ctx.send("You need at least 2 options! Separate them with commas.")
        return
    if len(option_list) > 10:
        await ctx.send("You can only have up to 10 options!")
        return

    emoji_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.blue())
    for i, option in enumerate(option_list):
        embed.add_field(name=f"Option {i+1}", value=f"{emoji_numbers[i]} {option.strip()}", inline=False)

    poll_msg = await ctx.send(embed=embed)
    for i in range(len(option_list)):
        await poll_msg.add_reaction(emoji_numbers[i])

@bot.hybrid_command(name="showicon", description="Shows the server's icon")
async def showicon(ctx):
    if not ctx.guild.icon:
        await ctx.send("This server has no icon!")
        return

    embed = discord.Embed(title=f"{ctx.guild.name}'s Icon", color=discord.Color.blue())
    embed.set_image(url=ctx.guild.icon.url)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="random", description="Generate a random number")
async def random_number(ctx, start: int = 1, end: int = 100):
    number = random.randint(start, end)
    embed = discord.Embed(
        title="🎲 Random Number",
        description=f"Generated number between {start} and {end}:",
        color=discord.Color.blue()
    )
    embed.add_field(name="Result", value=str(number))
    await ctx.send(embed=embed)

@bot.hybrid_command(name="joke", description="Tells a random joke")
async def joke(ctx):
    jokes = [
        "Why don't programmers like nature? It has too many bugs.",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why don't scientists trust atoms? Because they make up everything!",
        "What did the grape say when it got stepped on? Nothing, it just let out a little wine!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!"
    ]
    embed = discord.Embed(
        title="😄 Random Joke",
        description=random.choice(jokes),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="slowmode", description="Set slowmode in the channel")
@app_commands.default_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    embed = discord.Embed(
        title="⏱️ Slowmode Set",
        description=f"Slowmode set to {seconds} seconds",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="membercount", description="Shows server member count")
async def membercount(ctx):
    embed = discord.Embed(
        title="👥 Member Count",
        description=f"Total Members: {ctx.guild.member_count}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Humans", value=len([m for m in ctx.guild.members if not m.bot]))
    embed.add_field(name="Bots", value=len([m for m in ctx.guild.members if m.bot]))
    await ctx.send(embed=embed)

@bot.hybrid_command(name="serveremojis", description="Shows all server emojis")
async def serveremojis(ctx):
    emojis = [str(emoji) for emoji in ctx.guild.emojis]
    if not emojis:
        await ctx.send("This server has no custom emojis!")
        return

    embed = discord.Embed(
        title="😀 Server Emojis",
        description=" ".join(emojis),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="say", description="Make the bot say something")
@app_commands.default_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    await ctx.message.delete()
    embed = discord.Embed(
        description=message,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="weather", description="Get current weather info")
async def weather(ctx, *, location: str):
    embed = discord.Embed(
        title="🌤️ Weather Information",
        description=f"Weather information for {location}\nNote: This is a placeholder. Add weather API integration for real data.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="roles", description="Lists all server roles")
async def roles(ctx):
    roles = [role.mention for role in ctx.guild.roles[1:]]  # Skip @everyone
    embed = discord.Embed(
        title="📋 Server Roles",
        description="\n".join(reversed(roles)),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="channelinfo", description="Get information about a channel")
async def channelinfo(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    embed = discord.Embed(
        title="📺 Channel Information",
        color=discord.Color.blue()
    )
    embed.add_field(name="Name", value=channel.name)
    embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
    embed.add_field(name="Created At", value=channel.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="NSFW", value=channel.is_nsfw())
    embed.add_field(name="News Channel", value=channel.is_news())
    embed.add_field(name="Slowmode", value=f"{channel.slowmode_delay}s")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="serverstats", description="Shows detailed server statistics")
async def serverstats(ctx):
    guild = ctx.guild
    total_text_channels = len(guild.text_channels)
    total_voice_channels = len(guild.voice_channels)
    total_categories = len(guild.categories)
    total_roles = len(guild.roles)
    total_emojis = len(guild.emojis)

    embed = discord.Embed(
        title=f"📊 {guild.name} Statistics",
        color=discord.Color.blue()
    )
    embed.add_field(name="👥 Total Members", value=guild.member_count)
    embed.add_field(name="💬 Text Channels", value=total_text_channels)
    embed.add_field(name="🔊 Voice Channels", value=total_voice_channels)
    embed.add_field(name="📁 Categories", value=total_categories)
    embed.add_field(name="👑 Roles", value=total_roles)
    embed.add_field(name="😀 Emojis", value=total_emojis)
    embed.add_field(name="🚀 Boost Level", value=guild.premium_tier)
    embed.add_field(name="💎 Boosts", value=guild.premium_subscription_count)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="botstats", description="Shows bot statistics")
async def botstats(ctx):
    embed = discord.Embed(
        title="🤖 Bot Statistics",
        color=discord.Color.blue()
    )
    embed.add_field(name="Servers", value=len(bot.guilds))
    embed.add_field(name="Users", value=len(set(bot.get_all_members())))
    embed.add_field(name="Commands", value=len(bot.commands))
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms")
    embed.add_field(name="Python Version", value=platform.python_version())
    embed.add_field(name="Discord.py Version", value=discord.__version__)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="giveaway", description="Start a giveaway")
@app_commands.default_permissions(manage_guild=True)
async def giveaway(ctx, duration: int, *, prize: str):
    end_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)
    embed = discord.Embed(title="🎉 Giveaway!", description=f"Prize: {prize}", color=discord.Color.gold())
    embed.add_field(name="Duration", value=f"{duration} minutes")
    embed.add_field(name="Ends At", value=end_time.strftime("%Y-%m-%d %H:%M UTC"))
    embed.set_footer(text="React with 🎉 to enter!")
    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")
    await asyncio.sleep(duration * 60)

    message = await ctx.channel.fetch_message(message.id)
    users = [user async for user in message.reactions[0].users()]
    users.remove(bot.user)

    if users:
        winner = random.choice(users)
        await ctx.send(f"🎉 Congratulations {winner.mention}! You won: {prize}")
    else:
        await ctx.send("No one entered the giveaway 😔")

@bot.hybrid_command(name="embed", description="Create a custom embed message")
@app_commands.default_permissions(manage_messages=True)
async def embed(ctx, title: str, *, description: str):
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.hybrid_command(name="servericon", description="Change the server icon")
@app_commands.default_permissions(manage_guild=True)
async def servericon(ctx, url: str = None):
    if not url and not ctx.message.attachments:
        await ctx.send("Please provide a URL or attach an image!")
        return

    try:
        if url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    image_data = await resp.read()
        else:
            image_data = await ctx.message.attachments[0].read()

        await ctx.guild.edit(icon=image_data)
        await ctx.send("✅ Server icon updated successfully!")
    except Exception as e:
        await ctx.send(f"❌ Failed to update server icon: {str(e)}")

@bot.hybrid_command(name="nickname", description="Change a member's nickname")
@app_commands.default_permissions(manage_nicknames=True)
async def nickname(ctx, member: discord.Member, *, new_nickname: str = None):
    try:
        await member.edit(nick=new_nickname)
        await ctx.send(f"✅ Changed {member.name}'s nickname to: {new_nickname or 'Reset to default'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to change nickname: {str(e)}")

@bot.hybrid_command(name="invites", description="Show your invite statistics")
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    total_invites = 0
    async for invite in ctx.guild.invites():
        if invite.inviter == member:
            total_invites += invite.uses

    embed = discord.Embed(title="📨 Invite Statistics", color=member.color)
    embed.add_field(name="Member", value=member.mention)
    embed.add_field(name="Total Invites", value=str(total_invites))
    await ctx.send(embed=embed)

@bot.hybrid_command(name="remindme", description="Set a reminder with a custom message")
async def remindme(ctx, time: int, *, message: str):
    embed = discord.Embed(title="⏰ Reminder Set", color=discord.Color.blue())
    embed.add_field(name="Message", value=message)
    embed.add_field(name="Time", value=f"{time} minutes")
    await ctx.send(embed=embed)

    await asyncio.sleep(time * 60)
    remind_embed = discord.Embed(title="⏰ Reminder!", description=message, color=discord.Color.green())
    await ctx.author.send(embed=remind_embed)

@bot.hybrid_command(name="report", description="Report a user")
async def report(ctx, member: discord.Member, *, reason: str):
    # Send to a mod-log channel
    mod_log = discord.utils.get(ctx.guild.channels, name="mod-log")
    if modlog:
        embed = discord.Embed(title="⚠️ User Report", color=discord.Color.orange())
        embed.add_field(name="Reported User", value=member.mention)
        embed.add_field(name="Reported By", value=ctx.author.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Channel", value=ctx.channel.mention)
        await mod_log.send(embed=embed)
    await ctx.send("✅ Report submitted to moderators", ephemeral=True)



@bot.hybrid_command(name="urban", description="Look up a word in the Urban Dictionary")
async def urban(ctx, *, word: str):
    embed = discord.Embed(title=f"📚 Urban Dictionary: {word}", color=discord.Color.blue())
    embed.add_field(name="Note", value="This is a placeholder. Add Urban Dictionary API integration for real definitions.")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="serverbackup", description="Create a backup of server settings")
@app_commands.default_permissions(administrator=True)
async def serverbackup(ctx):
    """Create a backup of the server settings"""
    guild = ctx.guild
    backup_data = {
        "name": guild.name,
        "description": guild.description,
        "icon_url": str(guild.icon.url) if guild.icon else None,
        "roles": [{"name": role.name, "color": str(role.color), "permissions": role.permissions.value} 
                 for role in guild.roles if not role.is_default()],
        "channels": [{"name": channel.name, "type": str(channel.type), "category": channel.category.name if channel.category else None}
                    for channel in guild.channels]
    }

    # Save backup to a file
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{guild.id}_{timestamp}.txt"

    try:
        with open(filename, 'w') as f:
            json.dump(backup_data, f, indent=2)

        embed = discord.Embed(title="📑 Server Backup", color=discord.Color.green())
        embed.add_field(name="Server Name", value=guild.name)
        embed.add_field(name="Backup Time", value=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
        embed.add_field(name="Roles Backed Up", value=str(len(backup_data["roles"])))
        embed.add_field(name="Channels Backed Up", value=str(len(backup_data["channels"])))

        file = discord.File(filename)
        await ctx.author.send(embed=embed, file=file)
        await ctx.send("✅ Server backup has been created and sent to your DMs!")

        # Clean up the file
        os.remove(filename)
    except Exception as e:
        await ctx.send(f"❌ Failed to create backup: {str(e)}")

@bot.hybrid_command(name="serveremotes", description="List all available server emotes with IDs")
async def serveremotes(ctx):
    emotes = [f"{emote} - `{emote.id}`" for emote in ctx.guild.emojis]
    if not emotes:
        await ctx.send("This server has no custom emotes!")
        return

    embed = discord.Embed(title="Server Emotes", color=discord.Color.blue())
    # Split into chunks of 10 emotes per field
    chunks = [emotes[i:i + 10] for i in range(0, len(emotes), 10)]
    for i, chunk in enumerate(chunks, 1):
        embed.add_field(name=f"Page {i}", value="\n".join(chunk), inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="channelstats", description="Show detailed statistics about a channel")
async def channelstats(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    embed = discord.Embed(title=f"📊 Channel Statistics: #{channel.name}", color=discord.Color.blue())

    # Count messages in last 100
    messages = await channel.history(limit=100).flatten()
    user_messages = {}
    for msg in messages:
        user_messages[msg.author.name] = user_messages.get(msg.author.name, 0) + 1

    embed.add_field(name="Channel Type", value=str(channel.type))
    embed.add_field(name="Created On", value=channel.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
    embed.add_field(name="Position", value=str(channel.position))
    embed.add_field(name="NSFW", value="Yes" if channel.is_nsfw() else "No")
    embed.add_field(name="Slowmode", value=f"{channel.slowmode_delay}s")

    # Add top 5 active users
    top_users = sorted(user_messages.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_users:
        embed.add_field(name="Most Active Users (Last 100 msgs)", 
                       value="\n".join(f"{user}: {count} messages" for user, count in top_users),
                       inline=False)

    await ctx.send(embed=embed)

@bot.hybrid_command(name="roleinfo", description="Get detailed information about a role")
async def roleinfo(ctx, role: discord.Role):
    embed = discord.Embed(title=f"Role Information: {role.name}", color=role.color)

    permissions = [perm[0].replace('_', ' ').title() for perm, value in role.permissions if value]
    member_count = len(role.members)

    embed.add_field(name="Role ID", value=str(role.id))
    embed.add_field(name="Color", value=str(role.color))
    embed.add_field(name="Position", value=str(role.position))
    embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No")
    embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No")
    embed.add_field(name="Members", value=str(member_count))
    if permissions:
        embed.add_field(name="Key Permissions", value="\n".join(permissions[:10]) + 
                       (f"\n...and {len(permissions)-10} more" if len(permissions) > 10 else ""),
                       inline=False)

    await ctx.send(embed=embed)

@bot.hybrid_command(name="quickpoll", description="Create a quick yes/no poll")
async def quickpoll(ctx, *, question: str):
    embed = discord.Embed(title="📊 Quick Poll", description=question, color=discord.Color.blue())
    embed.set_footer(text=f"Poll by {ctx.author.name}")

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.hybrid_command(name="firstmessage", description="Find the first message in the channel")
async def firstmessage(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    first_message = None

    async for message in channel.history(limit=1, oldest_first=True):
        first_message = message

    if first_message:
        embed = discord.Embed(title="First Message", color=discord.Color.gold())
        embed.add_field(name="Content", value=first_message.content or "[No content]")
        embed.add_field(name="Author", value=first_message.author.mention)
        embed.add_field(name="Date", value=first_message.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="Jump to Message", value=f"[Click Here]({first_message.jump_url})")
    else:
        embed = discord.Embed(title="Error", description="No messages found!", color=discord.Color.red())

    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)

@bot.hybrid_command(name="restorebackup", description="Restore a server from a backup file")
@app_commands.default_permissions(administrator=True)
async def restorebackup(ctx, backup_file: discord.Attachment):
    try:
        # Download and read backup file
        backup_content = await backup_file.read()
        backup_data = json.loads(backup_content.decode('utf-8'))

        guild = ctx.guild
        progress_msg = await ctx.send("🔄 Starting server restoration...")

        # Delete existing channels except the current one
        for channel in guild.channels:
            if channel != ctx.channel:
                try:
                    await channel.delete()
                except:
                    continue

        # Delete existing roles
        for role in guild.roles:
            if not role.is_default() and role < guild.me.top_role:
                try:
                    await role.delete()
                except:
                    continue

        # Create roles from backup
        created_roles = {}
        for role_data in reversed(backup_data["roles"]):
            try:
                role = await guild.create_role(
                    name=role_data["name"],
                    color=discord.Color(int(role_data["color"].replace("#", ""), 16)),
                    permissions=discord.Permissions(int(role_data["permissions"]))
                )
                created_roles[role_data["name"]] = role
                await asyncio.sleep(0.5)  # Avoid rate limits
            except:
                continue

        # Create channels from backup
        for channel_data in backup_data["channels"]:
            try:
                category = None
                if channel_data["category"]:
                    category = discord.utils.get(guild.categories, name=channel_data["category"])
                    if not category:
                        category = await guild.create_category(name=channel_data["category"])

                if channel_data["type"] == "text":
                    await guild.create_text_channel(name=channel_data["name"], category=category)
                elif channel_data["type"] == "voice":
                    await guild.create_voice_channel(name=channel_data["name"], category=category)
                await asyncio.sleep(0.5)  # Avoid rate limits
            except:
                continue

        # Update server settings
        try:
            await guild.edit(name=backup_data["name"])
            if backup_data["description"]:
                await guild.edit(description=backup_data["description"])
        except:
            pass

        await progress_msg.edit(content="✅ Server restoration completed!")

    except Exception as e:
        await ctx.send(f"❌ Error restoring backup: {str(e)}")