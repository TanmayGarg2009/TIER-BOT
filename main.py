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
intents.presences = False

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Constants
ALLOWED_ROLE_NAME = "Admin"
ANNOUNCE_CHANNEL_ID = 1346137032933642351
TIERS = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT5", "HT4", "HT3", "HT2", "HT1"]
DATA_FILE = "tier_data.json"
REGIONS = ["AS", "NA", "EU"]
TIER_CHOICES = [app_commands.Choice(name=tier, value=tier) for tier in TIERS]
REGION_CHOICES = [app_commands.Choice(name=region, value=region) for region in REGIONS]


# Data Management
def load_data():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


tier_data = load_data()


# Role Utility Functions
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


# Bot Events
@bot.event
async def on_ready():
    for guild in bot.guilds:
        await create_tier_roles_if_missing(guild)
    await tree.sync()
    update_all_users.start()
    print(f"✅ Logged in as {bot.user}")


# Ticket System
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="Support", style=discord.ButtonStyle.primary, custom_id="ticket_support"))
        self.add_item(discord.ui.Button(label="Whitelist", style=discord.ButtonStyle.success, custom_id="ticket_whitelist"))
        self.add_item(discord.ui.Button(label="Purge", style=discord.ButtonStyle.danger, custom_id="ticket_purge"))
        self.add_item(discord.ui.Button(label="High Test", style=discord.ButtonStyle.secondary, custom_id="ticket_high_test"))

    @discord.ui.button(label="High Test", style=discord.ButtonStyle.secondary, custom_id="ticket_high_test")
    async def high_test_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.name in TIERS[:3] for role in interaction.user.roles):  # Checks if user has LT3+
            await interaction.response.send_message("❌ You don't have permission to access this.", ephemeral=True)
            return
        await interaction.response.send_message("✅ High Test ticket created!", ephemeral=True)


@tree.command(name="setup_ticket", description="Setup a ticket system in this channel")
async def setup_ticket(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    embed = discord.Embed(title="Ticket System", color=discord.Color.blue())
    embed.description = (
        "Select a ticket type below:\n"
        "1️⃣ **Support** - General help\n"
        "2️⃣ **Whitelist** - Apply for whitelist\n"
        "3️⃣ **Purge** - Request data purge\n"
        "4️⃣ **High Test** - Advanced testing (Visible to LT3+)"
    )

    view = TicketView()
    await interaction.response.send_message(embed=embed, view=view)


# Tier Management Commands
@tree.command(name="givetier", description="Assign a tier role to a player")
@app_commands.describe(
    player="The member to give the role to",
    tier="The tier role to assign",
    region="Select the region",
    username="Enter their in-game username"
)
@app_commands.choices(tier=TIER_CHOICES, region=REGION_CHOICES)
async def givetier(
    interaction: discord.Interaction,
    player: discord.Member,
    tier: app_commands.Choice[str],
    region: app_commands.Choice[str],
    username: str
):
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

    await interaction.response.send_message(
        f"✅ Assigned role '{tier.value}' to {player.mention}.", ephemeral=True
    )


# Automatic User Update Task
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


keep_alive()
token = os.getenv("TOKEN")
if not token:
    raise Exception("No token found. Please set your bot token as an environment variable named 'TOKEN'.")

bot.run(token)
