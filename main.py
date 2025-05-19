import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import os
import sqlite3
import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

db = sqlite3.connect("tier_bot.db")
cursor = db.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS tiers (
    user_id TEXT PRIMARY KEY,
    discord_name TEXT,
    username TEXT,
    tier TEXT,
    date_assigned TEXT
)
''')
db.commit()

TIER_ROLES = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT1"]

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    try:
        synced = await tree.sync(guild=discord.Object(id=1346134488547332217))
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

async def update_user_highest_tier(member):
    user_roles = [role.name for role in member.roles if role.name in TIER_ROLES]
    if not user_roles:
        cursor.execute("DELETE FROM tiers WHERE user_id = ?", (str(member.id),))
        db.commit()
        return
    highest_tier = max(user_roles, key=lambda r: TIER_ROLES.index(r))
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute("REPLACE INTO tiers (user_id, discord_name, username, tier, date_assigned) VALUES (?, ?, ?, ?, ?)",
                   (str(member.id), member.display_name, member.name, highest_tier, now))
    db.commit()

@bot.event
async def on_member_update(before, after):
    before_roles = set(before.roles)
    after_roles = set(after.roles)
    tier_changed = any(role.name in TIER_ROLES for role in before_roles ^ after_roles)
    if tier_changed:
        await update_user_highest_tier(after)

@tree.command(name="givetier", description="Assign a tier role to a user.", guild=discord.Object(id=1346134488547332217))
@app_commands.describe(member="User to assign the role to", tier="Tier role to assign")
async def givetier(interaction: discord.Interaction, member: discord.Member, tier: str):
    if tier not in TIER_ROLES:
        await interaction.response.send_message("Invalid tier.", ephemeral=True)
        return
    role = discord.utils.get(interaction.guild.roles, name=tier)
    if not role:
        await interaction.response.send_message(f"Role {tier} not found.", ephemeral=True)
        return
    await member.add_roles(role)
    await update_user_highest_tier(member)
    await interaction.response.send_message(f"{tier} given to {member.mention}")

@tree.command(name="removetier", description="Remove a tier role from a user.", guild=discord.Object(id=1346134488547332217))
@app_commands.describe(member="User to remove the role from", tier="Tier role to remove")
async def removetier(interaction: discord.Interaction, member: discord.Member, tier: str):
    role = discord.utils.get(interaction.guild.roles, name=tier)
    if role in member.roles:
        await member.remove_roles(role)
        await update_user_highest_tier(member)
        await interaction.response.send_message(f"{tier} removed from {member.mention}")
    else:
        await interaction.response.send_message(f"{member.mention} does not have {tier}", ephemeral=True)

@tree.command(name="tier", description="Check a user's highest tier.", guild=discord.Object(id=1346134488547332217))
@app_commands.describe(member="User to check")
async def tier(interaction: discord.Interaction, member: discord.Member):
    cursor.execute("SELECT * FROM tiers WHERE user_id = ?", (str(member.id),))
    row = cursor.fetchone()
    if row:
        await interaction.response.send_message(f"**Name:** {row[1]}\n**Username:** {row[2]}\n**Tier:** {row[3]}\n**Date Assigned:** {row[4]}")
    else:
        await interaction.response.send_message(f"No tier data for {member.display_name}")

@tree.command(name="database", description="List all users and their highest tier.", guild=discord.Object(id=1346134488547332217))
async def database_cmd(interaction: discord.Interaction):
    cursor.execute("SELECT discord_name, username, tier FROM tiers")
    rows = cursor.fetchall()
    if rows:
        msg = "\n".join([f"{row[0]} | {row[1]} | {row[2]}" for row in rows])
        await interaction.response.send_message(f"**Database:**\n```{msg}```")
    else:
        await interaction.response.send_message("Database is empty.")

# Ticket system
class TicketSelect(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(ui.Select(
            placeholder="Choose a ticket type...",
            options=[
                discord.SelectOption(label="Support", value="support"),
                discord.SelectOption(label="Whitelist", value="whitelist"),
                discord.SelectOption(label="Purge", value="purge"),
                discord.SelectOption(label="High Test", value="high_test", description="LT3+ only")
            ],
            custom_id="ticket_type_select"
        ))

    @ui.select(custom_id="ticket_type_select")
    async def select_callback(self, interaction: discord.Interaction, select):
        selected = select.values[0]
        allowed_roles = TIER_ROLES[:3]  # LT3, LT2, LT1, HT1

        if selected == "high_test" and not any(role.name in allowed_roles for role in interaction.user.roles):
            await interaction.response.send_message("You must have LT3 or higher to access High Test.", ephemeral=True)
            return

        thread = await interaction.channel.create_thread(name=f"{selected}-{interaction.user.name}", type=discord.ChannelType.private_thread)
        await thread.add_user(interaction.user)
        await thread.send(f"Welcome <@{interaction.user.id}>! This is your **{selected}** ticket.")
        await interaction.response.send_message(f"Ticket created: {thread.mention}", ephemeral=True)

@tree.command(name="setup_ticket", description="Setup the ticket panel.", guild=discord.Object(id=1346134488547332217))
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 Ticket Support", description="Please select a ticket type below.", color=discord.Color.blurple())
    await interaction.channel.send(embed=embed, view=TicketSelect())
    await interaction.response.send_message("Ticket panel set up.", ephemeral=True)

@tree.command(name="adduser", description="Add user to ticket thread.", guild=discord.Object(id=1346134488547332217))
async def adduser(interaction: discord.Interaction, member: discord.Member):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.channel.add_user(member)
        await interaction.response.send_message(f"Added {member.mention} to thread.", ephemeral=True)
    else:
        await interaction.response.send_message("Not a thread.", ephemeral=True)

@tree.command(name="removeuser", description="Remove user from ticket thread.", guild=discord.Object(id=1346134488547332217))
async def removeuser(interaction: discord.Interaction, member: discord.Member):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.channel.remove_user(member)
        await interaction.response.send_message(f"Removed {member.mention} from thread.", ephemeral=True)
    else:
        await interaction.response.send_message("Not a thread.", ephemeral=True)

@tree.command(name="close", description="Close the ticket thread.", guild=discord.Object(id=1346134488547332217))
async def close(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.channel.send("This ticket is now closed.")
        await interaction.channel.edit(archived=True, locked=True)
        await interaction.response.send_message("Ticket closed.", ephemeral=True)
    else:
        await interaction.response.send_message("Not a thread.", ephemeral=True)

bot.run(os.getenv("TOKEN"))
