import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

ALLOWED_ROLE_NAME = "Admin"
ANNOUNCE_CHANNEL_ID = 1346137032933642351
TIERS = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT5", "HT4", "HT3", "HT2", "HT1"]
REGIONS = ["AS", "NA", "EU"]

TIER_CHOICES = [app_commands.Choice(name=tier, value=tier) for tier in TIERS]
REGION_CHOICES = [app_commands.Choice(name=region, value=region) for region in REGIONS]
TICKET_OPTIONS = [
    ("General support", "🛠️"),
    ("Appeal", "⚖️"),
    ("Whitelist request", "📜"),
    ("Partnership", "🤝"),
    ("Others", "❓"),
]

DATA_FILE = "tier_data.json"

def load_data():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

tier_data = load_data()

def get_highest_tier(roles):
    tier_ranks = {name: i for i, name in enumerate(TIERS)}
    user_tiers = [role.name for role in roles if role.name in tier_ranks]
    return max(user_tiers, key=lambda x: tier_ranks[x], default=None)

def has_allowed_role(interaction: discord.Interaction):
    return any(role.name == ALLOWED_ROLE_NAME for role in interaction.user.roles)

async def create_tier_roles_if_missing(guild: discord.Guild):
    existing_roles = [role.name for role in guild.roles]
    for tier in TIERS:
        if tier not in existing_roles:
            await guild.create_role(name=tier)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        await create_tier_roles_if_missing(guild)
        await tree.sync(guild=guild)
    update_all_users.start()
    print(f"✅ Logged in as {bot.user}")

@tree.command(name="givetier", description="Assign a tier role to a player")
@app_commands.describe(player="The member", tier="Tier", region="Region", username="Game username")
@app_commands.choices(tier=TIER_CHOICES, region=REGION_CHOICES)
async def givetier(interaction: discord.Interaction, player: discord.Member, tier: app_commands.Choice[str], region: app_commands.Choice[str], username: str):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role is None:
        await interaction.response.send_message("❌ Role not found.", ephemeral=True)
        return

    await player.add_roles(role)
    highest = get_highest_tier(player.roles)
    tier_data[str(player.id)] = {
        "discord_name": str(player),
        "username": username,
        "tier": highest,
        "region": region.value,
        "date": datetime.now().strftime("%d/%m/%Y")
    }
    save_data(tier_data)
    await interaction.response.send_message(f"✅ Assigned '{tier.value}' to {player.mention}.", ephemeral=True)

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="Tier Assigned", color=discord.Color.green())
        embed.add_field(name="Discord Name", value=str(interaction.user), inline=False)
        embed.add_field(name="Username", value=username, inline=False)
        embed.add_field(name="Region", value=region.value, inline=False)
        embed.add_field(name="Rank Earned", value=tier.value, inline=False)
        embed.add_field(name="Date", value=datetime.now().strftime("%d/%m/%Y"), inline=False)
        await channel.send(embed=embed)

@tree.command(name="removetier", description="Remove a tier role")
@app_commands.describe(player="The member", tier="Tier")
@app_commands.choices(tier=TIER_CHOICES)
async def removetier(interaction: discord.Interaction, player: discord.Member, tier: app_commands.Choice[str]):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role is None or role not in player.roles:
        await interaction.response.send_message(f"{player.mention} doesn't have that role.", ephemeral=True)
        return

    await player.remove_roles(role)
    highest = get_highest_tier(player.roles)

    if highest:
        tier_data[str(player.id)]["tier"] = highest
    else:
        tier_data.pop(str(player.id), None)
    save_data(tier_data)

    await interaction.response.send_message(f"✅ Removed '{tier.value}' from {player.mention}.", ephemeral=True)

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="Tier Removed", color=discord.Color.red())
        embed.add_field(name="Discord Name", value=str(interaction.user), inline=False)
        embed.add_field(name="Username", value=str(player), inline=False)
        embed.add_field(name="Rank Removed", value=tier.value, inline=False)
        await channel.send(embed=embed)

@tree.command(name="tier", description="Check a player's tier info")
@app_commands.describe(player="The member")
async def tier(interaction: discord.Interaction, player: discord.Member):
    info = tier_data.get(str(player.id))
    if not info:
        await interaction.response.send_message("No tier data found.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"{info['discord_name']}  {info['username']}  {info['tier']}  {info['region']}  {info['date']}",
        ephemeral=True
    )

@tree.command(name="database", description="List all users with tier info")
async def database(interaction: discord.Interaction):
    await update_all_users_function()
    if not tier_data:
        await interaction.response.send_message("Database is empty.", ephemeral=True)
        return

    message = "**Tier Database:**\n\n"
    for data in tier_data.values():
        message += f"{data['discord_name']} | {data['username']} | {data['tier']}\n"

    await interaction.response.send_message(message[:2000], ephemeral=True)

@tasks.loop(minutes=10)
async def update_all_users():
    await update_all_users_function()

async def update_all_users_function():
    for guild in bot.guilds:
        for member in guild.members:
            highest = get_highest_tier(member.roles)
            if highest:
                current = tier_data.get(str(member.id), {})
                tier_data[str(member.id)] = {
                    "discord_name": str(member),
                    "username": current.get("username", "Unknown"),
                    "tier": highest,
                    "region": current.get("region", "Unknown"),
                    "date": current.get("date", "Unknown")
                }
            elif str(member.id) in tier_data:
                tier_data.pop(str(member.id))
    save_data(tier_data)

# ⬇️ Ticket System Commands ⬇️
@tree.command(name="setup_ticket", description="Create a ticket panel")
async def setup_ticket(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

    view = discord.ui.View()
    select = discord.ui.Select(
        placeholder="Choose a ticket type...",
        options=[discord.SelectOption(label=name, emoji=emoji) for name, emoji in TICKET_OPTIONS]
    )

    async def callback(interact: discord.Interaction):
        choice = select.values[0]
        category = discord.utils.get(interaction.guild.categories, name=choice)
        if category is None:
            category = await interaction.guild.create_category(name=choice)

        channel_name = f"{choice.lower().replace(' ', '-')}_{interact.user.name.lower()}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interact.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
        await interact.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

    select.callback = callback
    view.add_item(select)

    embed = discord.Embed(title="📩 Open a Ticket", description="Choose a reason to open a ticket.", color=0x5865F2)
    embed.set_footer(text="Select an option below to create a ticket.")
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="adduser", description="Add a user to the ticket")
@app_commands.describe(user="User to add")
async def adduser(interaction: discord.Interaction, user: discord.Member):
    if isinstance(interaction.channel, discord.TextChannel):
        await interaction.channel.set_permissions(user, view_channel=True, send_messages=True)
        await interaction.response.send_message(f"✅ {user.mention} added to the ticket.", ephemeral=True)

@tree.command(name="removeuser", description="Remove a user from the ticket")
@app_commands.describe(user="User to remove")
async def removeuser(interaction: discord.Interaction, user: discord.Member):
    if isinstance(interaction.channel, discord.TextChannel):
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"❌ {user.mention} removed from the ticket.", ephemeral=True)

@tree.command(name="close", description="Close this ticket")
async def close(interaction: discord.Interaction):
    await interaction.response.send_message("🗑️ Ticket will be deleted in 5 seconds.", ephemeral=True)
    await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=5))
    await interaction.channel.delete()

@tree.command(name="sync", description="Force sync all slash commands (Admin only)")
async def sync(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
    await tree.sync(guild=interaction.guild)
    await interaction.response.send_message("✅ Slash commands synced!", ephemeral=True)

# Run bot
keep_alive()
token = os.getenv("TOKEN")
if not token:
    raise Exception("TOKEN not found in environment variables.")
bot.run(token)
