import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from datetime import datetime

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Replace this with your actual server ID
GUILD_ID = 123456789012345678  # <-- UPDATE THIS
GUILD = discord.Object(id=GUILD_ID)

TIERS = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT5", "HT4", "HT3", "HT2", "HT1"]
tier_data = {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.tree.sync(guild=GUILD)
    print(f"✅ Slash commands synced to guild: {GUILD_ID}")

def save_data():
    with open("tier_data.json", "w") as f:
        json.dump(tier_data, f, indent=2)

def load_data():
    global tier_data
    if os.path.exists("tier_data.json"):
        with open("tier_data.json", "r") as f:
            tier_data = json.load(f)

# === Tier Commands ===

@bot.tree.command(name="givetier", description="Give a tier role", guild=GUILD)
@app_commands.describe(member="User", tier="Tier name", username="Minecraft IGN")
async def givetier(interaction: discord.Interaction, member: discord.Member, tier: str, username: str):
    if tier not in TIERS:
        await interaction.response.send_message("❌ Invalid tier", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=tier)
    if not role:
        role = await interaction.guild.create_role(name=tier)

    await member.add_roles(role)

    tier_data[str(member.id)] = {
        "discord_name": str(member),
        "username": username,
        "tier": tier,
        "date": datetime.now().strftime("%d/%m/%Y")
    }
    save_data()
    await interaction.response.send_message(f"✅ {member.mention} was given tier `{tier}`", ephemeral=True)

@bot.tree.command(name="tier", description="View a user's tier", guild=GUILD)
async def tier(interaction: discord.Interaction, member: discord.Member):
    data = tier_data.get(str(member.id))
    if not data:
        await interaction.response.send_message("User has no tier data.", ephemeral=True)
        return
    msg = f"{data['discord_name']} | {data['username']} | {data['tier']} | {data['date']}"
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="database", description="View all tier data", guild=GUILD)
async def database(interaction: discord.Interaction):
    if not tier_data:
        await interaction.response.send_message("Tier database is empty.", ephemeral=True)
        return
    msg = "**Tier List**\n" + "\n".join(
        f"{data['discord_name']} | {data['username']} | {data['tier']}"
        for data in tier_data.values()
    )
    await interaction.response.send_message(msg[:2000], ephemeral=True)

# === Ticket System ===

TICKET_OPTIONS = [
    ("Support", "support"),
    ("Whitelist", "whitelist"),
    ("Purge", "purge"),
    ("High Test", "hightest"),
    ("Other", "other")
]

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name, value=value) for name, value in TICKET_OPTIONS]
        super().__init__(placeholder="Choose a ticket type", options=options)

    async def callback(self, interaction: discord.Interaction):
        category_name = "Tickets"
        category = discord.utils.get(interaction.guild.categories, name=category_name)
        if not category:
            category = await interaction.guild.create_category(category_name)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
        }

        channel = await interaction.guild.create_text_channel(
            name=f"{self.values[0]}_{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        await interaction.response.send_message(f"🎫 Created ticket: {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketSelect())

@bot.tree.command(name="setup_ticket", description="Set up the ticket system", guild=GUILD)
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📨 Open a Ticket",
        description="Choose a category below to open a ticket.",
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Ticket system deployed!", ephemeral=True)

@bot.tree.command(name="close", description="Close this ticket", guild=GUILD)
async def close(interaction: discord.Interaction):
    await interaction.channel.delete()

@bot.tree.command(name="adduser", description="Add a user to this ticket", guild=GUILD)
async def adduser(interaction: discord.Interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"✅ {user.mention} added.")

@bot.tree.command(name="removeuser", description="Remove a user from this ticket", guild=GUILD)
async def removeuser(interaction: discord.Interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"✅ {user.mention} removed.")

# === Launch Bot ===

load_data()
bot.run(os.getenv("TOKEN"))
