import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import sqlite3
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree
TOKEN = os.getenv("TOKEN")
GUILD_ID = 1346134488547332217
TIER_ROLES = ["HT1", "LT1", "HT2", "LT2", "HT3", "LT3", "HT4", "LT4", "HT5", "LT5"]
REGIONS = ["AS", "NA", "EU"]
DB_FILE = "tier_data.db"

# -------------------- DATABASE SETUP -------------------- #

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS tiers (
            user_id TEXT PRIMARY KEY,
            discord_name TEXT,
            username TEXT,
            tier TEXT,
            date TEXT,
            region TEXT
        )''')
        conn.commit()

# -------------------- ROLE SYNC -------------------- #

def get_highest_tier(roles):
    tier_order = {tier: i for i, tier in enumerate(TIER_ROLES)}
    highest = None
    for role in roles:
        if role.name in tier_order:
            if highest is None or tier_order[role.name] < tier_order[highest]:
                highest = role.name
    return highest

def sync_roles_db(guild):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        for member in guild.members:
            highest = get_highest_tier(member.roles)
            if highest:
                cursor.execute("REPLACE INTO tiers (user_id, discord_name, username, tier, date, region) VALUES (?, ?, ?, ?, ?, ?)",
                               (str(member.id), member.display_name, member.name, highest, datetime.utcnow().strftime("%Y-%m-%d"), "Unknown"))
        conn.commit()

# -------------------- BOT EVENTS -------------------- #

@bot.event
async def on_ready():
    init_db()
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user}")

# -------------------- SLASH COMMANDS -------------------- #

@tree.command(name="givetier", description="Assign a tier to a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(discordname="The Discord display name",
                       username="Their Minecraft or other username",
                       region="Select region",
                       tier="Select tier")
@app_commands.choices(region=[app_commands.Choice(name=r, value=r) for r in REGIONS],
                      tier=[app_commands.Choice(name=t, value=t) for t in TIER_ROLES])
async def givetier(interaction: discord.Interaction, discordname: str, username: str, region: app_commands.Choice[str], tier: app_commands.Choice[str]):
    member = interaction.guild.get_member_named(discordname)
    if not member:
        await interaction.response.send_message("User not found.", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if not role:
        await interaction.response.send_message(f"Role '{tier.value}' not found.", ephemeral=True)
        return

    await member.add_roles(role)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO tiers (user_id, discord_name, username, tier, date, region) VALUES (?, ?, ?, ?, ?, ?)",
                       (str(member.id), discordname, username, tier.value, datetime.utcnow().strftime("%Y-%m-%d"), region.value))
        conn.commit()

    await interaction.response.send_message(f"Assigned {tier.value} to {discordname} ({username}) in region {region.value}.")

@tree.command(name="removetier", description="Remove a specific tier from a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(discordname="The Discord display name",
                       tier="Select tier to remove")
@app_commands.choices(tier=[app_commands.Choice(name=t, value=t) for t in TIER_ROLES])
async def removetier(interaction: discord.Interaction, discordname: str, tier: app_commands.Choice[str]):
    member = interaction.guild.get_member_named(discordname)
    if not member:
        await interaction.response.send_message("User not found.", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role in member.roles:
        await member.remove_roles(role)

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tier FROM tiers WHERE user_id = ?", (str(member.id),))
        row = cursor.fetchone()
        if row and row[0] == tier.value:
            cursor.execute("DELETE FROM tiers WHERE user_id = ?", (str(member.id),))
        conn.commit()

    await interaction.response.send_message(f"Removed {tier.value} from {discordname}.")

@tree.command(name="tier", description="View a user’s current tier", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(discordname="The Discord display name")
async def tier(interaction: discord.Interaction, discordname: str):
    sync_roles_db(interaction.guild)
    member = interaction.guild.get_member_named(discordname)
    if not member:
        await interaction.response.send_message("User not found.", ephemeral=True)
        return

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, discord_name, tier, date, region FROM tiers WHERE user_id = ?", (str(member.id),))
        data = cursor.fetchone()

    if data:
        msg = f"**Username:** {data[0]}\n**Discord Name:** {data[1]}\n**Tier:** {data[2]}\n**Date:** {data[3]}\n**Region:** {data[4]}"
    else:
        msg = "No tier data found."

    await interaction.response.send_message(msg, ephemeral=True)

@tree.command(name="database", description="List all users with their highest tier", guild=discord.Object(id=GUILD_ID))
async def database(interaction: discord.Interaction):
    sync_roles_db(interaction.guild)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT discord_name, username, tier FROM tiers")
        all_data = cursor.fetchall()
    if all_data:
        msg = "\n".join([f"{row[0]} | {row[1]} | {row[2]}" for row in all_data])
    else:
        msg = "No data found."
    await interaction.response.send_message(f"```\n{msg}```", ephemeral=True)

# -------------------- TICKET SYSTEM -------------------- #

@tree.command(name="setup_ticket", description="Setup a ticket system", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(ticketname="Ticket heading (category)")
async def setup_ticket(interaction: discord.Interaction, ticketname: str):
    category = discord.utils.get(interaction.guild.categories, name=ticketname)
    if category is None:
        category = await interaction.guild.create_category(ticketname)

    ticket_channel_name = f"{interaction.user.display_name}_{ticketname}".replace(" ", "-").lower()
    channel = discord.utils.get(interaction.guild.channels, name=ticket_channel_name)
    if channel is None:
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            discord.utils.get(interaction.guild.roles, name="staff"): discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(ticket_channel_name, category=category, overwrites=overwrites)
        await channel.send(f"<@&{discord.utils.get(interaction.guild.roles, name='staff').id}> <@{interaction.user.id}> Ticket created.")

    await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

bot.run(TOKEN)
