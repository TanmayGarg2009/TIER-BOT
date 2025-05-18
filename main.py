import os
import json
import discord
from discord import app_commands, Interaction, Member
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

# Tier commands
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

# Ticket system integration

class TicketButtons(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Support", style=discord.ButtonStyle.blurple, custom_id="ticket_support"))
        self.add_item(Button(label="Whitelist", style=discord.ButtonStyle.green, custom_id="ticket_whitelist"))
        self.add_item(Button(label="Purge", style=discord.ButtonStyle.red, custom_id="ticket_purge"))
        self.add_item(Button(label="High Test", style=discord.ButtonStyle.gray, custom_id="ticket_hightest"))

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Enable/disable High Test button based on LT3+ role
        lt3_index = TIERS.index("LT3")
        user_tiers = [role.name for role in interaction.user.roles if role.name in TIERS]
        user_highest = max((TIERS.index(t) for t in user_tiers), default=-1)
        high_test_button = next((btn for btn in self.children if btn.custom_id == "ticket_hightest"), None)
        if high_test_button:
            high_test_button.disabled = user_highest < lt3_index
        return True

@tree.command(name="setup_ticket", description="Setup the ticket system in this channel")
async def setup_ticket(interaction: Interaction):
    # Only allow this command in your server
    if interaction.guild.id != 1346134488547332217:
        await interaction.response.send_message("This command can only be used in the main server.", ephemeral=True)
        return

    guild = interaction.guild

    # Create categories if not exist
    category_names = ["support", "whitelist", "purge", "high test"]
    categories = {}
    for cat_name in category_names:
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)
        categories[cat_name] = category

    view = TicketButtons()
    await interaction.channel.send("🎟 **Select a ticket category:**", view=view)
    await interaction.response.send_message("✅ Ticket system setup in this channel!", ephemeral=True)

@bot.event
async def on_interaction(interaction: Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("ticket_"):
            category_key = custom_id.replace("ticket_", "")

            # Check LT3+ role for High Test category
            if category_key == "hightest":
                lt3_index = TIERS.index("LT3")
                user_tiers = [role.name for role in interaction.user.roles if role.name in TIERS]
                user_highest = max((TIERS.index(t) for t in user_tiers), default=-1)
                if user_highest < lt3_index:
                    await interaction.response.send_message("❌ You need to have LT3 or higher to open this ticket.", ephemeral=True)
                    return

            # Find or create the category
            category_name_map = {
                "support": "support",
                "whitelist": "whitelist",
                "purge": "purge",
                "hightest": "high test"
            }
            cat_name = category_name_map.get(category_key)
            if not cat_name:
                await interaction.response.send_message("Unknown ticket category.", ephemeral=True)
                return

            guild = interaction.guild
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                category = await guild.create_category(cat_name)

            # Channel name format: discordname-category
            channel_name = f"{interaction.user.name}-{cat_name}".lower().replace(" ", "-")

            # Check if a ticket channel already exists with the same name
            existing_channel = discord.utils.get(category.channels, name=channel_name)
            if existing_channel:
                await interaction.response.send_message(f"You already have an open ticket in {existing_channel.mention}", ephemeral=True)
                return

            # Check if user has LT3 or above for all tickets except Purge and Whitelist? 
            # You asked only for High Test to require LT3, so no need here.

            # Create the channel in the category
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Also allow roles with LT3+ to view tickets
            lt3_index = TIERS.index("LT3")
            for role in guild.roles:
                if role.name in TIERS:
                    role_index = TIERS.index(role.name)
                    if role_index >= lt3_index:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            await channel.send(f"📩 Ticket created by {interaction.user.mention} for **{cat_name.capitalize()}**.")

            await interaction.response.send_message(f"🎫 Your **{cat_name.capitalize()}** ticket has been created: {channel.mention}", ephemeral=True)

# Ticket management commands

@tree.command(name="close", description="Close this ticket channel")
async def close(interaction: Interaction):
    if isinstance(interaction.channel, discord.TextChannel):
        # Only allow close in ticket categories
        if interaction.channel.category and interaction.channel.category.name.lower() in ["support", "whitelist", "purge", "high test"]:
            await interaction.response.send_message("Closing this ticket in 5 seconds...", ephemeral=True)
            await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=5))
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)
    else:
        await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)

@tree.command(name="add_user", description="Add a user to this ticket")
@app_commands.describe(user="The user to add to the ticket")
async def add_user(interaction: Interaction, user: Member):
    if isinstance(interaction.channel, discord.TextChannel):
        if interaction.channel.category and interaction.channel.category.name.lower() in ["support", "whitelist", "purge", "high test"]:
            await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
            await interaction.response.send_message(f"✅ Added {user.mention} to this ticket.", ephemeral=True)
        else:
            await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)
    else:
        await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)

@tree.command(name="remove_user", description="Remove a user from this ticket")
@app_commands.describe(user="The user to remove from the ticket")
async def remove_user(interaction: Interaction, user: Member):
    if isinstance(interaction.channel, discord.TextChannel):
        if interaction.channel.category and interaction.channel.category.name.lower() in ["support", "whitelist", "purge", "high test"]:
            await interaction.channel.set_permissions(user, overwrite=None)
            await interaction.response.send_message(f"❌ Removed {user.mention} from this ticket.", ephemeral=True)
        else:
            await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)
    else:
        await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)

keep_alive()
token = os.getenv("TOKEN")
bot.run(token)
