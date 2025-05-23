import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
<<<<<<< HEAD
import datetime
import os

# --- Bot Setup ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# --- Database Setup ---
db = sqlite3.connect("tiers.db")
cursor = db.cursor()
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS tiers (
        user_id INTEGER PRIMARY KEY,
        discord_name TEXT,
        username TEXT,
        region TEXT,
        tier TEXT,
        assign_date TEXT
    )'''
)
db.commit()

# --- Config ---
tier_roles = ["HT1","HT2","HT3","HT4","HT5","LT1","LT2","LT3","LT4","LT5"]
region_choices = [app_commands.Choice(name="AS", value="AS"), app_commands.Choice(name="NA", value="NA"), app_commands.Choice(name="EU", value="EU")]
tier_choices = [app_commands.Choice(name=t, value=t) for t in tier_roles]
TIER_CHANNEL_ID = 1346137032933642351
GUILD_ID = 1346134488547332217
STAFF_ROLE_NAME = "staff"

# --- Helper Functions ---
def sync_roles(guild):
    for member in guild.members:
        roles = [r for r in member.roles if r.name in tier_roles]
        if roles:
            highest = sorted(roles, key=lambda r: tier_roles.index(r.name))[0].name
            cursor.execute(
                "REPLACE INTO tiers (user_id, discord_name, username, region, tier, assign_date) VALUES (?, ?, ?, ?, ?, ?)",
                (member.id, member.display_name, member.name, "Unknown", highest, str(datetime.date.today()))
            )
    db.commit()
=======
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
db = sqlite3.connect("tiers.db")
cursor = db.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS tiers (
    user_id INTEGER,
    discord_name TEXT,
    username TEXT,
    tier TEXT,
    region TEXT,
    date TEXT
)
""")
db.commit()

TIER_ROLES = ["HT1", "HT2", "HT3", "HT4", "HT5", "LT1", "LT2", "LT3", "LT4", "LT5"]
REGIONS = ["AS", "NA", "EU"]
TIER_CHANNEL = 1346137032933642351
STAFF_ROLE_NAME = "staff"
>>>>>>> 1a11f41 (git pull origin main.py)

# --- Sync on Ready ---
@bot.event
async def on_ready():
<<<<<<< HEAD
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user}")

# --- Tier Commands ---
@tree.command(name="givetier", description="Assign a tier role to a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Select a member", username="Enter username", region="Select region", tier="Select tier")
@app_commands.choices(region=region_choices, tier=tier_choices)
async def givetier(interaction: discord.Interaction, user: discord.Member, username: str, region: app_commands.Choice[str], tier: app_commands.Choice[str]):
    await sync_roles(interaction.guild)
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role:
        await user.add_roles(role)
    cursor.execute(
        "REPLACE INTO tiers (user_id, discord_name, username, region, tier, assign_date) VALUES (?, ?, ?, ?, ?, ?)",
        (user.id, user.display_name, username, region.value, tier.value, str(datetime.date.today()))
    )
    db.commit()
    # Public confirmation
    await interaction.response.send_message(f"Assigned {tier.value} to {user.display_name}")
    # Send summary to tier channel
    ch = interaction.guild.get_channel(TIER_CHANNEL_ID)
    if ch:
        await ch.send(
            f"{user.mention}\n" +
            f"Discord Name: {user.display_name}\n" +
            f"Username: {username}\n" +
            f"Region: {region.value}\n" +
            f"Tier Earned: {tier.value}\n" +
            f"Date: {str(datetime.date.today())}"
        )

@tree.command(name="removetier", description="Remove a tier role from a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Select a member", tier="Select tier to remove")
@app_commands.choices(tier=tier_choices)
async def removetier(interaction: discord.Interaction, user: discord.Member, tier: app_commands.Choice[str]):
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role in user.roles:
        await user.remove_roles(role)
    cursor.execute("SELECT tier FROM tiers WHERE user_id = ?", (user.id,))
    row = cursor.fetchone()
    if row and row[0] == tier.value:
        cursor.execute("DELETE FROM tiers WHERE user_id = ?", (user.id,))
        db.commit()
    await interaction.response.send_message(f"Removed {tier.value} from {user.display_name}")

@tree.command(name="tier", description="Show a user’s tier info", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Select a member")
async def tier(interaction: discord.Interaction, user: discord.Member):
    await sync_roles(interaction.guild)
    cursor.execute("SELECT username, discord_name, tier, assign_date, region FROM tiers WHERE user_id = ?", (user.id,))
    data = cursor.fetchone()
    if data:
        await interaction.response.send_message(
            f"Username: {data[0]}\n" +
            f"Discord Name: {data[1]}\n" +
            f"Tier: {data[2]}\n" +
            f"Date: {data[3]}\n" +
            f"Region: {data[4]}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("No tier data found.", ephemeral=True)

@tree.command(name="database", description="List all users’ tiers", guild=discord.Object(id=GUILD_ID))
=======
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)
    print(f"Bot is ready. Logged in as {bot.user}")

# Utility to get highest tier
def get_highest_tier(roles):
    role_order = {role: i for i, role in enumerate(TIER_ROLES)}
    highest = None
    for role in roles:
        if role.name in role_order:
            if highest is None or role_order[role.name] < role_order[highest.name]:
                highest = role
    return highest

@bot.tree.command(name="givetier")
@app_commands.describe(discordname="Pick a user", username="Enter their in-game username",
                       region="Pick a region", tier="Pick a tier")
@app_commands.choices(region=[app_commands.Choice(name=r, value=r) for r in REGIONS],
                      tier=[app_commands.Choice(name=t, value=t) for t in TIER_ROLES])
async def givetier(interaction: discord.Interaction,
                   discordname: discord.Member,
                   username: str,
                   region: app_commands.Choice[str],
                   tier: app_commands.Choice[str]):
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role:
        await discordname.add_roles(role)
        now = datetime.utcnow().strftime("%Y-%m-%d")
        cursor.execute("DELETE FROM tiers WHERE user_id = ?", (discordname.id,))
        cursor.execute("INSERT INTO tiers VALUES (?, ?, ?, ?, ?, ?)",
                       (discordname.id, discordname.name, username, tier.value, region.value, now))
        db.commit()

        channel = bot.get_channel(TIER_CHANNEL)
        await channel.send(f"{discordname.mention}\n{discordname.name}\n{username}\n{region.value}\n{tier.value}\n{now}")
        await interaction.response.send_message("Tier assigned.", ephemeral=False)
    else:
        await interaction.response.send_message("Tier role not found.", ephemeral=True)

@bot.tree.command(name="removetier")
@app_commands.describe(discordname="Select user", tier="Select tier to remove")
@app_commands.choices(tier=[app_commands.Choice(name=t, value=t) for t in TIER_ROLES])
async def removetier(interaction: discord.Interaction, discordname: discord.Member,
                     tier: app_commands.Choice[str]):
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if role:
        await discordname.remove_roles(role)
        cursor.execute("DELETE FROM tiers WHERE user_id = ? AND tier = ?", (discordname.id, tier.value))
        db.commit()
        await interaction.response.send_message(f"Removed {tier.value} from {discordname.name}", ephemeral=False)
    else:
        await interaction.response.send_message("Role not found.", ephemeral=True)

@bot.tree.command(name="tier")
@app_commands.describe(user="Check another user's tier")
async def tier(interaction: discord.Interaction, user: discord.Member = None):
    await sync_roles(interaction.guild)
    user = user or interaction.user
    cursor.execute("SELECT username, discord_name, tier, date, region FROM tiers WHERE user_id = ?", (user.id,))
    data = cursor.fetchone()
    if data:
        await interaction.response.send_message(
            f"{data[0]} {data[1]} {data[2]} {data[3]} {data[4]}", ephemeral=True)
    else:
        await interaction.response.send_message("No tier found.", ephemeral=True)

@bot.tree.command(name="database")
>>>>>>> 1a11f41 (git pull origin main.py)
async def database(interaction: discord.Interaction):
    await sync_roles(interaction.guild)
    cursor.execute("SELECT discord_name, username, tier FROM tiers")
    rows = cursor.fetchall()
<<<<<<< HEAD
    msg = "\n".join([f"{r[0]} | {r[1]} | {r[2]}" for r in rows]) or "No data."
    await interaction.response.send_message(msg, ephemeral=True)

# --- Ticket System ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support"),
            discord.SelectOption(label="Appeal"),
            discord.SelectOption(label="Whitelist Request"),
            discord.SelectOption(label="Partnership"),
            discord.SelectOption(label="Others")
        ]
        super().__init__(placeholder="Select ticket type...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        # Category
        cat = discord.utils.get(interaction.guild.categories, name=ticket_type)
        if not cat:
            cat = await interaction.guild.create_category(ticket_type)
        # Channel
        chan_name = f"{interaction.user.display_name}_{ticket_type.lower().replace(' ', '_')}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        staff = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        ch = await cat.create_text_channel(chan_name, overwrites=overwrites)
        await ch.send(f"{staff.mention if staff else ''} {interaction.user.mention}")
        await interaction.response.send_message(f"Ticket created: {ch.mention}", ephemeral=True)

@tree.command(name="setup_ticket", description="Deploy ticket panel", guild=discord.Object(id=GUILD_ID))
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 Create a Ticket", description="Select from the menu below.", color=discord.Color.blurple())
    view = TicketView()
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="adduser", description="Add a user to this ticket channel", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Select a member to add")
async def adduser(interaction: discord.Interaction, user: discord.Member):
    channel = interaction.channel
    await channel.set_permissions(user, view_channel=True, send_messages=True)
    await interaction.response.send_message(f"Added {user.mention} to the ticket.", ephemeral=True)

@tree.command(name="removeuser", description="Remove a user from this ticket channel", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Select a member to remove")
async def removeuser(interaction: discord.Interaction, user: discord.Member):
    channel = interaction.channel
    await channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"Removed {user.mention} from the ticket.", ephemeral=True)

@tree.command(name="close", description="Close the ticket channel", guild=discord.Object(id=GUILD_ID))
async def close(interaction: discord.Interaction):
    channel = interaction.channel
    await interaction.response.send_message("Closing ticket...", ephemeral=True)
    await channel.delete()

@tree.command(name="handle", description="Mark this ticket as being handled", guild=discord.Object(id=GUILD_ID))
async def handle(interaction: discord.Interaction):
    await interaction.response.send_message(f"{interaction.user.mention} is handling this ticket.")

=======
    if rows:
        formatted = "\n".join([f"{r[0]} {r[1]} {r[2]}" for r in rows])
        await interaction.response.send_message(f"{formatted}", ephemeral=True)
    else:
        await interaction.response.send_message("No data found.", ephemeral=True)

async def sync_roles(guild):
    for member in guild.members:
        highest = get_highest_tier(member.roles)
        if highest:
            cursor.execute("SELECT tier FROM tiers WHERE user_id = ?", (member.id,))
            result = cursor.fetchone()
            if not result or result[0] != highest.name:
                cursor.execute("DELETE FROM tiers WHERE user_id = ?", (member.id,))
                cursor.execute("INSERT INTO tiers VALUES (?, ?, ?, ?, ?, ?)",
                               (member.id, member.name, member.name, highest.name, "Unknown", datetime.utcnow().strftime("%Y-%m-%d")))
    db.commit()

# --- Ticket System ---
TICKET_CATEGORIES = ["Support", "Whitelist", "Purge", "High test"]

@bot.tree.command(name="setup_ticket")
async def setup_ticket(interaction: discord.Interaction):
    view = TicketDropdown()
    await interaction.response.send_message("Choose a ticket type:", view=view, ephemeral=True)

class TicketDropdown(discord.ui.View):
    @discord.ui.select(
        placeholder="Select ticket type",
        min_values=1,
        max_values=1,
        options=[discord.SelectOption(label=t) for t in TICKET_CATEGORIES]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        category_name = select.values[0]
        member = interaction.user
        guild = interaction.guild

        if category_name == "High test":
            has_required = any(role.name in TIER_ROLES[:6] for role in member.roles)
            if not has_required:
                return await interaction.response.send_message("LT3 or above required for High test.", ephemeral=True)

        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            category = await guild.create_category(category_name)

        channel_name = f"{member.name.lower()}_{category_name.replace(' ', '').lower()}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            discord.utils.get(guild.roles, name=STAFF_ROLE_NAME): discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        await channel.send(f"<@&{discord.utils.get(guild.roles, name=STAFF_ROLE_NAME).id}> {member.mention}")
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

@bot.tree.command(name="close")
async def close_ticket(interaction: discord.Interaction):
    if interaction.channel.name.startswith(interaction.user.name.lower()):
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("You can only close your own ticket.", ephemeral=True)

@bot.tree.command(name="adduser")
@app_commands.describe(user="User to add")
async def adduser(interaction: discord.Interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, view_channel=True, send_messages=True)
    await interaction.response.send_message(f"Added {user.mention} to the ticket.", ephemeral=False)

@bot.tree.command(name="removeuser")
@app_commands.describe(user="User to remove")
async def removeuser(interaction: discord.Interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"Removed {user.mention} from the ticket.", ephemeral=False)

@bot.tree.command(name="handle")
async def handle(interaction: discord.Interaction):
    await interaction.channel.send(f"{interaction.user.mention} is now handling this ticket.")
    await interaction.response.send_message("Marked as being handled.", ephemeral=True)

import os
>>>>>>> 1a11f41 (git pull origin main.py)
bot.run(os.getenv("TOKEN"))
