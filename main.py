import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

TOKEN = os.getenv("TOKEN") or "YOUR_TOKEN_HERE"
GUILD_ID = 1346134488547332217  # Replace with your server ID
TIER_LOG_CHANNEL_ID = 1346137032933642351  # Replace with your log channel ID

TIER_ROLES = ["HT1", "HT2", "HT3", "LT1", "LT2", "LT3", "LT4", "LT5"]
DATA_FILE = "tiers.json"

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_highest_tier(roles):
    tier_order = {role: i for i, role in enumerate(TIER_ROLES)}
    user_tiers = [r.name for r in roles if r.name in tier_order]
    if not user_tiers:
        return None
    return min(user_tiers, key=lambda r: tier_order[r])

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="givetier", description="Assign a tier role", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(discord_name="Their Discord name", username="Their in-game username", region="AS/NA/EU", tier="Tier to assign")
@app_commands.choices(
    region=[
        app_commands.Choice(name="Asia", value="AS"),
        app_commands.Choice(name="North America", value="NA"),
        app_commands.Choice(name="Europe", value="EU")
    ],
    tier=[app_commands.Choice(name=t, value=t) for t in TIER_ROLES]
)
async def givetier(interaction: discord.Interaction, discord_name: str, username: str, region: app_commands.Choice[str], tier: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=False)
    member = interaction.guild.get_member_named(discord_name)
    if not member:
        await interaction.followup.send("Member not found.")
        return
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if not role:
        await interaction.followup.send("Tier role not found.")
        return
    await member.add_roles(role)
    data = load_data()
    data[str(member.id)] = {
        "discord_name": discord_name,
        "username": username,
        "region": region.value,
        "tier": tier.value,
        "date": datetime.utcnow().strftime("%Y-%m-%d")
    }
    save_data(data)
    await interaction.followup.send(f"✅ {tier.value} given to {discord_name}")
    log_channel = bot.get_channel(TIER_LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"🎖️ {tier.value} assigned to {discord_name} ({username}) in region {region.value} on {data[str(member.id)]['date']}")

@bot.tree.command(name="removetier", description="Remove a specific tier", guild=discord.Object(id=GUILD_ID))
@app_commands.choices(
    tier=[app_commands.Choice(name=t, value=t) for t in TIER_ROLES]
)
async def removetier(interaction: discord.Interaction, member: discord.Member, tier: app_commands.Choice[str]):
    await member.remove_roles(discord.utils.get(interaction.guild.roles, name=tier.value))
    await interaction.response.send_message(f"❌ Removed {tier.value} from {member.display_name}", ephemeral=False)

@bot.tree.command(name="tier", description="Check a user's tier", guild=discord.Object(id=GUILD_ID))
async def tier(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer(ephemeral=True)
    member = member or interaction.user
    data = load_data()
    entry = data.get(str(member.id))
    if entry:
        msg = f"**Username:** {entry['username']}\n**Discord:** {entry['discord_name']}\n**Tier:** {entry['tier']}\n**Region:** {entry['region']}\n**Date:** {entry['date']}"
    else:
        msg = "No tier data found."
    await interaction.followup.send(msg)

@bot.tree.command(name="database", description="Show all tier assignments", guild=discord.Object(id=GUILD_ID))
async def database(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    msg = "\n".join([f"{v['discord_name']} | {v['username']} | {v['tier']}" for v in data.values()])
    await interaction.followup.send(msg or "No data yet.")

@bot.tree.command(name="setup_ticket", description="Setup ticket system", guild=discord.Object(id=GUILD_ID))
async def setup_ticket(interaction: discord.Interaction):
    await interaction.response.send_message("Ticket system setup", ephemeral=True)
    
    class TicketView(discord.ui.View):
        @discord.ui.select(placeholder="Choose ticket type", options=[
            discord.SelectOption(label="Support", value="support"),
            discord.SelectOption(label="Whitelist", value="whitelist"),
            discord.SelectOption(label="Purge", value="purge"),
            discord.SelectOption(label="High test", value="high_test", description="LT3 and above only")
        ])
        async def select_callback(self, interaction2: discord.Interaction, select: discord.ui.Select):
            ticket_type = select.values[0]
            member = interaction2.user
            if ticket_type == "high_test":
                has_permission = any(r.name in ["LT1", "LT2", "LT3", "HT1", "HT2", "HT3"] for r in member.roles)
                if not has_permission:
                    await interaction2.response.send_message("You need LT3 or higher to access this option.", ephemeral=True)
                    return
            category = discord.utils.get(interaction2.guild.categories, name=ticket_type)
            if not category:
                category = await interaction2.guild.create_category(ticket_type)
            channel_name = f"{member.name}_{ticket_type}"
            channel = await interaction2.guild.create_text_channel(channel_name, category=category)
            await channel.set_permissions(member, read_messages=True, send_messages=True)
            await channel.set_permissions(interaction2.guild.default_role, read_messages=False)
            await interaction2.response.send_message(f"Created ticket: {channel.mention}", ephemeral=True)
            await channel.send(f"@staff {member.mention} created a **{ticket_type}** ticket.")

    await interaction.channel.send("Create a ticket below:", view=TicketView())

@bot.tree.command(name="adduser", description="Add user to ticket", guild=discord.Object(id=GUILD_ID))
async def adduser(interaction: discord.Interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"✅ Added {user.display_name} to the ticket.")

@bot.tree.command(name="removeuser", description="Remove user from ticket", guild=discord.Object(id=GUILD_ID))
async def removeuser(interaction: discord.Interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"❌ Removed {user.display_name} from the ticket.")

@bot.tree.command(name="close", description="Close the ticket in 5 seconds", guild=discord.Object(id=GUILD_ID))
async def close(interaction: discord.Interaction):
    await interaction.response.send_message("⏳ Closing ticket in 5 seconds...")
    await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=5))
    await interaction.channel.delete()

bot.run(TOKEN)
