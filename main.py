import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Select, button, Button
from discord.ui.select import SelectOption
from datetime import datetime
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.presences = False

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

ALLOWED_ROLE_NAME = "Admin"
ANNOUNCE_CHANNEL_ID = 1346137032933642351
TIERS = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT5", "HT4", "HT3", "HT2", "HT1"]
REGIONS = ["AS", "NA", "EU"]
DATA_FILE = "tier_data.json"
TIER_CHOICES = [app_commands.Choice(name=t, value=t) for t in TIERS]
REGION_CHOICES = [app_commands.Choice(name=r, value=r) for r in REGIONS]
TICKET_OPTIONS = [
    ("General Support", "general"),
    ("Appeal", "appeal"),
    ("Whitelist Request", "whitelist"),
    ("Partnership", "partnership"),
    ("Others", "others")
]

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

def has_allowed_role(interaction):
    return any(role.name == ALLOWED_ROLE_NAME for role in interaction.user.roles)

async def create_tier_roles_if_missing(guild):
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

# ---------------- Tier Commands ----------------

@tree.command(name="givetier", description="Assign a tier role to a player")
@app_commands.describe(player="The member", tier="Tier role", region="Region", username="Game username")
@app_commands.choices(tier=TIER_CHOICES, region=REGION_CHOICES)
async def givetier(interaction, player: discord.Member, tier: app_commands.Choice[str], region: app_commands.Choice[str], username: str):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role is None:
        return await interaction.response.send_message("❌ Role not found.", ephemeral=True)
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
    await interaction.response.send_message(f"✅ Assigned role '{tier.value}' to {player.mention}.", ephemeral=True)
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="Tier Assigned", color=discord.Color.green())
        embed.add_field(name="Discord Name", value=str(interaction.user))
        embed.add_field(name="Username", value=username)
        embed.add_field(name="Region", value=region.value)
        embed.add_field(name="Rank Earned", value=tier.value)
        embed.add_field(name="Date", value=datetime.now().strftime("%d/%m/%Y"))
        await channel.send(embed=embed)

@tree.command(name="removetier", description="Remove a tier role")
@app_commands.describe(player="The member", tier="Tier to remove")
@app_commands.choices(tier=TIER_CHOICES)
async def removetier(interaction, player: discord.Member, tier: app_commands.Choice[str]):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role is None or role not in player.roles:
        return await interaction.response.send_message(f"{player.mention} doesn't have the role.", ephemeral=True)
    await player.remove_roles(role)
    highest = get_highest_tier(player.roles)
    if highest:
        tier_data[str(player.id)]["tier"] = highest
    else:
        tier_data.pop(str(player.id), None)
    save_data(tier_data)
    await interaction.response.send_message(f"✅ Removed role '{tier.value}' from {player.mention}.", ephemeral=True)
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="Tier Removed", color=discord.Color.red())
        embed.add_field(name="Discord Name", value=str(interaction.user))
        embed.add_field(name="Username", value=str(player))
        embed.add_field(name="Rank Removed", value=tier.value)
        await channel.send(embed=embed)

@tree.command(name="tier", description="Check a player's tier")
@app_commands.describe(player="The player")
async def tier(interaction, player: discord.Member):
    info = tier_data.get(str(player.id))
    if not info:
        return await interaction.response.send_message("No tier data found.", ephemeral=True)
    response = f"{info['discord_name']}  {info['username']}  {info['tier']}  {info['region']}  {info['date']}"
    await interaction.response.send_message(response, ephemeral=True)

@tree.command(name="database", description="List all users with tier info")
async def database(interaction):
    await update_all_users_function()
    if not tier_data:
        return await interaction.response.send_message("Database is empty.", ephemeral=True)
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

# ---------------- Ticket System ----------------

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [SelectOption(label=name, value=value, description=f"Open a {name} ticket") for name, value in TICKET_OPTIONS]
        super().__init__(placeholder="Select a ticket type...", options=options)

    async def callback(self, interaction):
        category = discord.utils.get(interaction.guild.categories, name=self.values[0])
        if not category:
            category = await interaction.guild.create_category(self.values[0])
        name = f"{self.values[0]}_{interaction.user.name}"
        channel = await interaction.guild.create_text_channel(name, category=category)
        await channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"🎫 Ticket created: {channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

@tree.command(name="setup_ticket", description="Setup the ticket panel")
async def setup_ticket(interaction):
    embed = discord.Embed(title="Support Ticket", description="Select the type of support you need from the dropdown below.", color=discord.Color.blurple())
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket panel created.", ephemeral=True)

@tree.command(name="adduser", description="Add user to ticket")
@app_commands.describe(user="User to add")
async def adduser(interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"✅ {user.mention} added to this ticket.", ephemeral=True)

@tree.command(name="removeuser", description="Remove user from ticket")
@app_commands.describe(user="User to remove")
async def removeuser(interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"✅ {user.mention} removed from this ticket.", ephemeral=True)

@tree.command(name="close", description="Close the ticket")
async def close(interaction):
    await interaction.channel.delete()

keep_alive()
token = os.getenv("TOKEN")
if not token:
    raise Exception("No token found. Please set your bot token as an environment variable named 'TOKEN'.")
bot.run(token)