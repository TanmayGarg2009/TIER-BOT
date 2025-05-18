import os
import json
import discord
from discord import app_commands, Interaction, Member
from discord.ext import commands
from discord.ui import View, Button
from keep_alive import keep_alive
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_typing = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

TIERS = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT5", "HT4", "HT3", "HT2", "HT1"]
TIER_CHOICES = [app_commands.Choice(name=t, value=t) for t in TIERS]
REGION_CHOICES = [
    app_commands.Choice(name="AS", value="AS"),
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="EU", value="EU")
]

DATA_FILE = "tier_data.json"
LOG_CHANNEL_ID = 1346137032933642351  # Channel where messages will be sent publicly

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

tier_data = load_data()

def get_highest_tier(roles):
    for tier in reversed(TIERS):  # HT1 > ... > LT5
        if any(role.name == tier for role in roles):
            return tier
    return None

async def update_tier_data(member: discord.Member):
    highest = get_highest_tier(member.roles)
    if highest:
        tier_data[str(member.id)] = {
            "discord_name": member.display_name,
            "username": tier_data.get(str(member.id), {}).get("username", "unknown"),
            "tier": highest,
            "region": tier_data.get(str(member.id), {}).get("region", "unknown"),
            "date": datetime.now().strftime("%d/%m/%Y")
        }
    else:
        if str(member.id) in tier_data:
            del tier_data[str(member.id)]
    save_data(tier_data)

def check_user_role_permission(member: discord.Member, bot_member: discord.Member) -> bool:
    # Returns True if the user can use commands (user top role >= bot top role)
    if not member.guild:
        return False
    user_top = member.top_role.position
    bot_top = bot_member.top_role.position
    return user_top >= bot_top

async def send_log_message(guild: discord.Guild, description: str):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        print(f"Log channel with ID {LOG_CHANNEL_ID} not found in guild {guild.name}")
        return
    embed = discord.Embed(
        description=description,
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="Tier System Log")
    await log_channel.send(embed=embed)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot is ready. Logged in as {bot.user}")

@bot.event
async def on_member_update(before, after):
    await update_tier_data(after)

# Universal check decorator for commands - ensures user top role >= bot top role
def user_has_permission():
    async def predicate(interaction: Interaction) -> bool:
        bot_member = interaction.guild.me
        if not check_user_role_permission(interaction.user, bot_member):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command (your role is lower than the bot's role).",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# Tier commands
@tree.command(name="givetier", description="Assign a tier role to a player")
@user_has_permission()
@app_commands.describe(player="The member to give the role to", username="In-game username", tier="Tier", region="Region")
@app_commands.choices(tier=TIER_CHOICES, region=REGION_CHOICES)
async def givetier(interaction: Interaction, player: Member, username: str, tier: app_commands.Choice[str], region: app_commands.Choice[str]):
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if not role:
        await interaction.response.send_message("Role not found.", ephemeral=True)
        return

    await player.add_roles(role)
    tier_data[str(player.id)] = {
        "discord_name": player.display_name,
        "username": username,
        "tier": tier.value,
        "region": region.value,
        "date": datetime.now().strftime("%d/%m/%Y")
    }
    save_data(tier_data)
    await update_tier_data(player)

    await interaction.response.send_message(f"✅ Assigned {tier.value} to {player.mention}", ephemeral=True)

    # Send public log message to designated channel
    description = (
        f"**Tier Assigned**\n"
        f"👤 {player.mention} ({player.display_name})\n"
        f"🎮 Username: `{username}`\n"
        f"🏷️ Tier: **{tier.value}**\n"
        f"🌍 Region: {region.value}\n"
        f"📅 Date: {datetime.now().strftime('%d/%m/%Y')}\n"
        f"🔧 By: {interaction.user.mention}"
    )
    await send_log_message(interaction.guild, description)

@tree.command(name="removetier", description="Remove a tier role from a player")
@user_has_permission()
@app_commands.describe(player="The member to remove the role from", tier="Tier")
@app_commands.choices(tier=TIER_CHOICES)
async def removetier(interaction: Interaction, player: Member, tier: app_commands.Choice[str]):
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if not role:
        await interaction.response.send_message("Role not found.", ephemeral=True)
        return

    await player.remove_roles(role)
    await update_tier_data(player)
    await interaction.response.send_message(f"✅ Removed {tier.value} from {player.mention}", ephemeral=True)

    # Send public log message to designated channel
    description = (
        f"**Tier Removed**\n"
        f"👤 {player.mention} ({player.display_name})\n"
        f"🏷️ Tier: **{tier.value}**\n"
        f"📅 Date: {datetime.now().strftime('%d/%m/%Y')}\n"
        f"🔧 By: {interaction.user.mention}"
    )
    await send_log_message(interaction.guild, description)

@tree.command(name="tier", description="Check a user's tier info")
@user_has_permission()
@app_commands.describe(player="The member to check")
async def tier(interaction: Interaction, player: Member):
    await update_tier_data(player)
    data = tier_data.get(str(player.id))
    if data:
        await interaction.response.send_message(
            f"{data['discord_name']} {data['username']} {data['tier']} {data['region']} {data['date']}"
        )
    else:
        await interaction.response.send_message("No tier data found.", ephemeral=True)

@tree.command(name="database", description="View full tier database")
@user_has_permission()
async def database(interaction: Interaction):
    # Refresh all users
    for member in interaction.guild.members:
        await update_tier_data(member)

    if not tier_data:
        await interaction.response.send_message("No tier data found.", ephemeral=True)
        return

    msg = "**Tier Database:**\n"
    for user_id, data in tier_data.items():
        msg += f"{data['discord_name']} {data['username']} {data['tier']}\n"

    # Send in chunks if long
    for chunk in [msg[i:i+1900] for i in range(0, len(msg), 1900)]:
        await interaction.channel.send(chunk)
    await interaction.response.send_message("✅ Database displayed.", ephemeral=True)

# --- Your existing ticket system code remains unchanged ---
# ... (I omitted ticket system here to focus on your request, but you should keep it as is)

# ... (Keep your ticket system code here as before)

keep_alive()
token = os.getenv("TOKEN")
bot.run(token)
