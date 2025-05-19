# This script is a complete rewrite of the Discord bot based on your specifications.
# Key Features:
# - Slash commands with updated parameters.
# - Automatic syncing of tier roles with the database.
# - Ticket system with improved visual appearance.
# - Properly scoped command responses (ephemeral or public).
# - Date tracking for tier assignment.

import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
from datetime import datetime
import os

TOKEN = os.environ['TOKEN']
intents = discord.Intents.all()
client = commands.Bot(command_prefix="!", intents=intents)
tree = client.tree

# Set up database
conn = sqlite3.connect("tiers.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS tiers (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    discordname TEXT,
    region TEXT,
    tier TEXT,
    date TEXT
)''')
conn.commit()

TIER_ROLES = ["HT1", "LT1", "HT2", "LT2", "HT3", "LT3", "HT4", "LT4", "HT5", "LT5"]

def get_highest_tier(roles):
    for tier in TIER_ROLES:
        if any(role.name == tier for role in roles):
            return tier
    return None

async def sync_roles_with_db(guild):
    for member in guild.members:
        tier = get_highest_tier(member.roles)
        if tier:
            now = datetime.utcnow().strftime("%Y-%m-%d")
            c.execute("INSERT OR REPLACE INTO tiers (user_id, username, discordname, region, tier, date) VALUES (?, ?, ?, ?, ?, ?)",
                      (str(member.id), member.name, str(member), "N/A", tier, now))
    conn.commit()

@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}!')

@tree.command(name="givetier", description="Assign a tier role")
@app_commands.describe(discordname="The member's Discord name", username="The member's username", region="Region (AS/NA/EU)", tier="Tier (HT1 to LT5)")
async def givetier(interaction: discord.Interaction, discordname: str, username: str, region: str, tier: str):
    member = discord.utils.get(interaction.guild.members, name=discordname)
    if not member:
        await interaction.response.send_message("Member not found.", ephemeral=True)
        return
    role = discord.utils.get(interaction.guild.roles, name=tier)
    if not role:
        await interaction.response.send_message("Tier role not found.", ephemeral=True)
        return
    await member.add_roles(role)
    now = datetime.utcnow().strftime("%Y-%m-%d")
    c.execute("INSERT OR REPLACE INTO tiers (user_id, username, discordname, region, tier, date) VALUES (?, ?, ?, ?, ?, ?)",
              (str(member.id), username, discordname, region, tier, now))
    conn.commit()
    await interaction.response.send_message(f"Gave {tier} to {discordname}", ephemeral=False)

@tree.command(name="removetier", description="Remove all tier roles from a user")
@app_commands.describe(discordname="The member's Discord name")
async def removetier(interaction: discord.Interaction, discordname: str):
    member = discord.utils.get(interaction.guild.members, name=discordname)
    if not member:
        await interaction.response.send_message("Member not found.", ephemeral=True)
        return
    removed = []
    for tier in TIER_ROLES:
        role = discord.utils.get(interaction.guild.roles, name=tier)
        if role in member.roles:
            await member.remove_roles(role)
            removed.append(role.name)
    c.execute("DELETE FROM tiers WHERE user_id = ?", (str(member.id),))
    conn.commit()
    await interaction.response.send_message(f"Removed tier roles {', '.join(removed)} from {discordname}", ephemeral=False)

@tree.command(name="tier", description="Show tier info")
@app_commands.describe(discordname="The member's Discord name")
async def tier(interaction: discord.Interaction, discordname: str):
    await sync_roles_with_db(interaction.guild)
    member = discord.utils.get(interaction.guild.members, name=discordname)
    if not member:
        await interaction.response.send_message("Member not found.", ephemeral=True)
        return
    c.execute("SELECT username, discordname, tier, date, region FROM tiers WHERE user_id = ?", (str(member.id),))
    row = c.fetchone()
    if row:
        await interaction.response.send_message(f"**Username:** {row[0]}\n**Discord Name:** {row[1]}\n**Tier:** {row[2]}\n**Date:** {row[3]}\n**Region:** {row[4]}", ephemeral=True)
    else:
        await interaction.response.send_message("No tier info found for this user.", ephemeral=True)

@tree.command(name="database", description="List all user tiers")
async def database(interaction: discord.Interaction):
    await sync_roles_with_db(interaction.guild)
    c.execute("SELECT username, discordname, tier FROM tiers")
    rows = c.fetchall()
    if not rows:
        await interaction.response.send_message("No data found.", ephemeral=True)
        return
    msg = "**Tier Database**\n"
    for row in rows:
        msg += f"**Username:** {row[0]} | **Discord:** {row[1]} | **Tier:** {row[2]}\n"
    await interaction.response.send_message(msg, ephemeral=True)

# -------- Ticket System -------- #

@tree.command(name="setup_ticket", description="Setup a ticket system in this channel")
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 Create a Ticket", description="Click a button below to open a ticket.", color=0x00ffcc)
    view = TicketView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Ticket system deployed!", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Support", style=discord.ButtonStyle.primary, custom_id="support"))
        self.add_item(discord.ui.Button(label="Whitelist", style=discord.ButtonStyle.success, custom_id="whitelist"))
        self.add_item(discord.ui.Button(label="Purge", style=discord.ButtonStyle.danger, custom_id="purge"))
        self.add_item(discord.ui.Button(label="High Test", style=discord.ButtonStyle.secondary, custom_id="hightest"))

@client.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        label = interaction.data['custom_id']
        channel = await interaction.guild.create_text_channel(f"{label}-{interaction.user.name}", overwrites={
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }, category=None)
        await channel.send(f"Ticket created for {label}. Please wait for a staff member.")
        await interaction.response.send_message(f"Created {label} ticket: {channel.mention}", ephemeral=True)

client.run(TOKEN)
