import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
<<<<<<< HEAD
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
=======
import datetime
import os
>>>>>>> 91ebadc (git push origin main)

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
>>>>>>> 1a11f41 (git pull origin main.py)

<<<<<<< HEAD
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
=======
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

# --- Sync on Ready ---
@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user}")
>>>>>>> 91ebadc (git push origin main)

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

<<<<<<< HEAD
@bot.tree.command(name="database")
>>>>>>> 1a11f41 (git pull origin main.py)
=======
@tree.command(name="database", description="List all users’ tiers", guild=discord.Object(id=GUILD_ID))
>>>>>>> 91ebadc (git push origin main)
async def database(interaction: discord.Interaction):
    await sync_roles(interaction.guild)
    cursor.execute("SELECT discord_name, username, tier FROM tiers")
    rows = cursor.fetchall()
<<<<<<< HEAD
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
=======
    msg = "\n".join([f"{r[0]} | {r[1]} | {r[2]}" for r in rows]) or "No data."
    await interaction.response.send_message(msg, ephemeral=True)
>>>>>>> 91ebadc (git push origin main)

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

<<<<<<< HEAD
import os
>>>>>>> 1a11f41 (git pull origin main.py)
=======
>>>>>>> 91ebadc (git push origin main)
bot.run(os.getenv("TOKEN"))
