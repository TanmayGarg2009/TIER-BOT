import os
import json
import discord
from discord import app_commands, Interaction, Member, PermissionOverwrite
from discord.ext import commands
from discord.ui import View, Button
from keep_alive import keep_alive
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_typing = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ========== Your existing tier system (unchanged) ==========
TIERS = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT5", "HT4", "HT3", "HT2", "HT1"]
TIER_CHOICES = [app_commands.Choice(name=t, value=t) for t in TIERS]
REGION_CHOICES = [
    app_commands.Choice(name="AS", value="AS"),
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="EU", value="EU")
]

DATA_FILE = "tier_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

tier_data = load_data()

def get_highest_tier(roles):
    for tier in reversed(TIERS):  # HT1 > ... > LT5
        if any(role.name == tier for role in roles):
            return tier
    return None

async def update_tier_data(member: discord.Member):
    highest = get_highest_tier(member.roles)
    if highest:
        tier_data[str(member.id)] = {
            "discord_name": member.display_name,
            "username": tier_data.get(str(member.id), {}).get("username", "unknown"),
            "tier": highest,
            "region": tier_data.get(str(member.id), {}).get("region", "unknown"),
            "date": datetime.now().strftime("%d/%m/%Y")
        }
    else:
        if str(member.id) in tier_data:
            del tier_data[str(member.id)]
    save_data(tier_data)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot is ready. Logged in as {bot.user}")

@bot.event
async def on_member_update(before, after):
    await update_tier_data(after)

@tree.command(name="givetier", description="Assign a tier role to a player")
@app_commands.describe(player="The member to give the role to", username="In-game username", tier="Tier", region="Region")
@app_commands.choices(tier=TIER_CHOICES, region=REGION_CHOICES)
async def givetier(interaction: Interaction, player: Member, username: str, tier: app_commands.Choice[str], region: app_commands.Choice[str]):
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if not role:
        await interaction.response.send_message("Role not found.", ephemeral=True)
        return

    await player.add_roles(role)
    tier_data[str(player.id)] = {
        "discord_name": player.display_name,
        "username": username,
        "tier": tier.value,
        "region": region.value,
        "date": datetime.now().strftime("%d/%m/%Y")
    }
    save_data(tier_data)
    await interaction.response.send_message(f"✅ Assigned {tier.value} to {player.mention}", ephemeral=True)

@tree.command(name="removetier", description="Remove a tier role from a player")
@app_commands.describe(player="The member to remove the role from", tier="Tier")
@app_commands.choices(tier=TIER_CHOICES)
async def removetier(interaction: Interaction, player: Member, tier: app_commands.Choice[str]):
    role = discord.utils.get(interaction.guild.roles, name=tier.value)
    if not role:
        await interaction.response.send_message("Role not found.", ephemeral=True)
        return

    await player.remove_roles(role)
    await update_tier_data(player)
    await interaction.response.send_message(f"✅ Removed {tier.value} from {player.mention}", ephemeral=True)

@tree.command(name="tier", description="Check a user's tier info")
@app_commands.describe(player="The member to check")
async def tier(interaction: Interaction, player: Member):
    await update_tier_data(player)
    data = tier_data.get(str(player.id))
    if data:
        await interaction.response.send_message(
            f"{data['discord_name']} {data['username']} {data['tier']} {data['region']} {data['date']}"
        )
    else:
        await interaction.response.send_message("No tier data found.", ephemeral=True)

@tree.command(name="database", description="View full tier database")
async def database(interaction: Interaction):
    # Refresh all users
    for member in interaction.guild.members:
        await update_tier_data(member)

    if not tier_data:
        await interaction.response.send_message("No tier data found.", ephemeral=True)
        return

    msg = "**Tier Database:**\n"
    for user_id, data in tier_data.items():
        msg += f"{data['discord_name']} {data['username']} {data['tier']}\n"

    # Send in chunks if long
    for chunk in [msg[i:i+1900] for i in range(0, len(msg), 1900)]:
        await interaction.channel.send(chunk)
    await interaction.response.send_message("✅ Database displayed.", ephemeral=True)


# ====== Ticket system ======

TICKET_CATEGORIES = ["Support", "Whitelist", "Purge", "High test"]

def has_lt3_or_above(member: discord.Member) -> bool:
    # Return True if member has LT3 or higher role
    if not member.guild:
        return False
    lt3_index = TIERS.index("LT3")
    member_tiers = [role.name for role in member.roles if role.name in TIERS]
    if not member_tiers:
        return False
    highest_index = max(TIERS.index(t) for t in member_tiers)
    return highest_index >= lt3_index

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        # Add buttons for all 4 categories
        self.add_item(Button(label="Support", style=discord.ButtonStyle.blurple, custom_id="ticket_support"))
        self.add_item(Button(label="Whitelist", style=discord.ButtonStyle.green, custom_id="ticket_whitelist"))
        self.add_item(Button(label="Purge", style=discord.ButtonStyle.red, custom_id="ticket_purge"))
        self.add_item(Button(label="High test", style=discord.ButtonStyle.gray, custom_id="ticket_hightest"))

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Disable High test button if user does not have LT3 or higher
        high_test_btn = discord.utils.get(self.children, custom_id="ticket_hightest")
        if high_test_btn:
            if has_lt3_or_above(interaction.user):
                high_test_btn.disabled = False
            else:
                high_test_btn.disabled = True
        return True

@tree.command(name="setup_ticket", description="Setup the ticket system in this channel")
async def setup_ticket(interaction: Interaction):
    guild = interaction.guild
    # Create categories if not exist
    for cat_name in TICKET_CATEGORIES:
        category = discord.utils.get(guild.categories, name=cat_name)
        if category is None:
            await guild.create_category(cat_name)

    view = TicketView()
    await interaction.channel.send("🎟 **Select a ticket category:**", view=view)
    await interaction.response.send_message("✅ Ticket system setup in this channel!", ephemeral=True)

@bot.event
async def on_interaction(interaction: Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("ticket_"):
            category_key = custom_id.replace("ticket_", "")
            if category_key == "hightest":
                category_key = "High test"
            else:
                # Capitalize first letter for category match
                category_key = category_key.capitalize()

            # Check user permission for High test tickets
            if category_key == "High test" and not has_lt3_or_above(interaction.user):
                await interaction.response.send_message("⚠️ You need LT3 or higher role to open High test tickets.", ephemeral=True)
                return

            guild = interaction.guild

            # Find or create category
            category = discord.utils.get(guild.categories, name=category_key)
            if category is None:
                category = await guild.create_category(category_key)

            # Format channel name: discordname-category (lowercase, spaces to dashes)
            base_name = f"{interaction.user.name}-{category_key}"
            channel_name = base_name.lower().replace(" ", "-")

            # Check if user already has an open ticket in that category (by channel name)
            existing_channel = discord.utils.get(category.channels, name=channel_name)
            if existing_channel:
                await interaction.response.send_message(f"❗ You already have an open ticket here: {existing_channel.mention}", ephemeral=True)
                return

            # Permissions:
            overwrites = {
                guild.default_role: PermissionOverwrite(read_messages=False),
                interaction.user: PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Add roles/users with top role above bot to see channel (staff)
            bot_member = guild.get_member(bot.user.id)
            for member in guild.members:
                if member.top_role > bot_member.top_role:
                    overwrites[member] = PermissionOverwrite(read_messages=True, send_messages=True)

            # Create text channel inside category
            ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

            await ticket_channel.send(f"📩 Ticket created by {interaction.user.mention} for **{category.name}**.")
            await interaction.response.send_message(f"🎫 Your **{category.name}** ticket has been created: {ticket_channel.mention}", ephemeral=True)

# Command to close the ticket (deletes channel)
@tree.command(name="close", description="Close the ticket (deletes the channel)")
async def close(interaction: Interaction):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("⚠️ This command can only be used inside a ticket channel.", ephemeral=True)
        return

    # Check if channel is inside one of the ticket categories
    if channel.category is None or channel.category.name not in TICKET_CATEGORIES:
        await interaction.response.send_message("⚠️ This command can only be used inside a ticket channel.", ephemeral=True)
        return

    try:
        await channel.delete()
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to close the ticket: {e}", ephemeral=True)
        return

# Command to add user to ticket channel
@tree.command(name="add_user", description="Add a user to this ticket")
@app_commands.describe(user="The user to add to the ticket")
async def add_user(interaction: Interaction, user: Member):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("⚠️ This command can only be used inside a ticket channel.", ephemeral=True)
        return

    if channel.category is None or channel.category.name not in TICKET_CATEGORIES:
        await interaction.response.send_message("⚠️ This command can only be used inside a ticket channel.", ephemeral=True)
        return

    await channel.set_permissions(user, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"✅ Added {user.mention} to this ticket.", ephemeral=True)

# Command to remove user from ticket channel
@tree.command(name="remove_user", description="Remove a user from this ticket")
@app_commands.describe(user="The user to remove from the ticket")
async def remove_user(interaction: Interaction, user: Member):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("⚠️ This command can only be used inside a ticket channel.", ephemeral=True)
        return

    if channel.category is None or channel.category.name not in TICKET_CATEGORIES:
        await interaction.response.send_message("⚠️ This command can only be used inside a ticket channel.", ephemeral=True)
        return

    await channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"❌ Removed {user.mention} from this ticket.", ephemeral=True)


keep_alive()
token = os.getenv("TOKEN")
bot.run(token)
