import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# === CONFIG ===
ALLOWED_ROLE_NAME = "Admin"
ANNOUNCE_CHANNEL_ID = 1346137032933642351
GUILD_ID = 1340040522248622090  # <-- REPLACE with your server ID
GUILD = discord.Object(id=GUILD_ID)

TIERS = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT5", "HT4", "HT3", "HT2", "HT1"]
REGIONS = ["AS", "NA", "EU"]
DATA_FILE = "tier_data.json"

tier_data = {}

# === HELPERS ===

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

# === STARTUP ===

@bot.event
async def on_ready():
    global tier_data
    tier_data = load_data()
    for guild in bot.guilds:
        await create_tier_roles_if_missing(guild)
    await tree.sync(guild=GUILD)
    update_all_users.start()
    print(f"✅ Logged in as {bot.user}")

# === TIER SYSTEM ===

TIER_CHOICES = [app_commands.Choice(name=t, value=t) for t in TIERS]
REGION_CHOICES = [app_commands.Choice(name=r, value=r) for r in REGIONS]

@tree.command(name="givetier", description="Assign a tier role")
@app_commands.describe(player="Player", tier="Tier", region="Region", username="In-game name")
@app_commands.choices(tier=TIER_CHOICES, region=REGION_CHOICES)
async def givetier(interaction, player: discord.Member, tier: app_commands.Choice[str], region: app_commands.Choice[str], username: str):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    role = discord.utils.get(interaction.guild.roles, name=tier.value)
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

    await interaction.response.send_message(f"✅ Assigned {tier.value} to {player.mention}", ephemeral=True)

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="Tier Assigned", color=discord.Color.green())
        embed.add_field(name="Discord", value=str(interaction.user))
        embed.add_field(name="IGN", value=username)
        embed.add_field(name="Region", value=region.value)
        embed.add_field(name="Tier", value=tier.value)
        embed.add_field(name="Date", value=datetime.now().strftime("%d/%m/%Y"))
        await channel.send(embed=embed)

@tree.command(name="removetier", description="Remove a tier")
@app_commands.choices(tier=TIER_CHOICES)
async def removetier(interaction, player: discord.Member, tier: app_commands.Choice[str]):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    await player.remove_roles(role)

    highest = get_highest_tier(player.roles)
    if highest:
        tier_data[str(player.id)]["tier"] = highest
    else:
        tier_data.pop(str(player.id), None)
    save_data(tier_data)

    await interaction.response.send_message(f"✅ Removed {tier.value} from {player.mention}", ephemeral=True)

@tree.command(name="tier", description="Check player's tier")
async def tier(interaction, player: discord.Member):
    info = tier_data.get(str(player.id))
    if not info:
        return await interaction.response.send_message("No tier data.", ephemeral=True)

    msg = f"{info['discord_name']}  {info['username']}  {info['tier']}  {info['region']}  {info['date']}"
    await interaction.response.send_message(msg, ephemeral=True)

@tree.command(name="database", description="List all tier data")
async def database(interaction):
    await update_all_users_function()
    if not tier_data:
        return await interaction.response.send_message("Database is empty.", ephemeral=True)

    msg = "**Tier Database:**\n"
    for data in tier_data.values():
        msg += f"{data['discord_name']} | {data['username']} | {data['tier']}\n"
    await interaction.response.send_message(msg[:2000], ephemeral=True)

# === AUTO SYNC LOOP ===

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

# === TICKET SYSTEM ===

TICKET_OPTIONS = [
    ("General Support", "support"),
    ("Appeal", "appeal"),
    ("Whitelist Request", "whitelist"),
    ("Partnership", "partner"),
    ("Others", "others")
]

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name, value=value) for name, value in TICKET_OPTIONS]
        super().__init__(placeholder="Choose a ticket type", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category_name = self.values[0].capitalize()
        category = discord.utils.get(interaction.guild.categories, name=category_name)
        if not category:
            category = await interaction.guild.create_category(category_name)

        channel_name = f"{self.values[0]}_{interaction.user.name}".replace(" ", "-").lower()
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        channel = await interaction.guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        await interaction.response.send_message(f"✅ Created ticket: {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@tree.command(name="setup_ticket", description="Setup ticket panel")
async def setup_ticket(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    embed = discord.Embed(
        title="🎫 Create a Ticket",
        description="Select a category from the dropdown to open a ticket.",
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket panel created!", ephemeral=True)

@tree.command(name="adduser", description="Add user to ticket")
async def adduser(interaction: discord.Interaction, member: discord.Member):
    if interaction.channel.category and interaction.channel.category.name.lower() in [v for _, v in TICKET_OPTIONS]:
        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"✅ {member.mention} added to ticket.")
    else:
        await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)

@tree.command(name="removeuser", description="Remove user from ticket")
async def removeuser(interaction: discord.Interaction, member: discord.Member):
    await interaction.channel.set_permissions(member, overwrite=None)
    await interaction.response.send_message(f"✅ {member.mention} removed from ticket.")

@tree.command(name="close", description="Close the ticket")
async def close(interaction: discord.Interaction):
    await interaction.channel.delete()

# === RUN ===

token = os.getenv("TOKEN")
if not token:
    raise Exception("❌ TOKEN not set in environment.")
bot.run(token)
