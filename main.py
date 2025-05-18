import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Select, Button
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
DATA_FILE = "tier_data.json"

REGIONS = ["AS", "NA", "EU"]
TIER_CHOICES = [app_commands.Choice(name=tier, value=tier) for tier in TIERS]
REGION_CHOICES = [app_commands.Choice(name=region, value=region) for region in REGIONS]
TICKET_OPTIONS = ["General Support", "Appeal", "Whitelist Request", "Partnership", "Others"]


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
    await tree.sync()
    update_all_users.start()
    print(f"✅ Logged in as {bot.user}")

# TIER SYSTEM COMMANDS OMITTED HERE FOR BREVITY - UNCHANGED
# ... keep your existing givetier, removetier, tier, database, update_all_users ...

# ------------------- TICKET SYSTEM -------------------
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=opt, description=f"Open a ticket for {opt.lower()}")
            for opt in TICKET_OPTIONS
        ]
        super().__init__(placeholder="Choose a ticket option...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category_name = self.values[0]
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        channel_name = f"{category_name.replace(' ', '').lower()}_{interaction.user.name}"
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role in guild.roles:
            if role.position > guild.me.top_role.position:
                continue
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        await channel.send(f"<@{interaction.user.id}> Ticket created for **{category_name}**.")
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

@tree.command(name="setup_ticket", description="Setup the ticket panel")
async def setup_ticket(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎟️ Create a Ticket",
        description="Select an option from the dropdown to open a ticket.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Support System")
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket panel created!", ephemeral=True)

@tree.command(name="adduser", description="Add a user to the ticket")
@app_commands.describe(user="User to add")
async def adduser(interaction: discord.Interaction, user: discord.Member):
    if not interaction.channel.name.startswith("general") and interaction.channel.category:
        await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"✅ {user.mention} added to the ticket.", ephemeral=True)
    else:
        await interaction.response.send_message("This command must be used in a ticket channel.", ephemeral=True)

@tree.command(name="removeuser", description="Remove a user from the ticket")
@app_commands.describe(user="User to remove")
async def removeuser(interaction: discord.Interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"✅ {user.mention} removed from the ticket.", ephemeral=True)

@tree.command(name="close", description="Close the ticket")
async def close(interaction: discord.Interaction):
    await interaction.channel.delete()

# ------------------- BACKGROUND UPDATER -------------------
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

# ------------------- START BOT -------------------
keep_alive()
token = os.getenv("TOKEN")
if not token:
    raise Exception("No token found. Please set your bot token as an environment variable named 'TOKEN'.")
bot.run(token)
