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
@tree.command(name="givetier", description="Assign a tier role to a player", guild=discord.Object(id=YOUR_GUILD_ID))
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

@tree.command(name="removetier", description="Remove a tier role from a player", guild=discord.Object(id=YOUR_GUILD_ID))
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

@tree.command(name="tier", description="Check a user's tier info", guild=discord.Object(id=YOUR_GUILD_ID))
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

@tree.command(name="database", description="View full tier database", guild=discord.Object(id=YOUR_GUILD_ID))
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

# Ticket system

class TicketButtons(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Support", style=discord.ButtonStyle.blurple, custom_id="ticket_support"))
        self.add_item(Button(label="Whitelist", style=discord.ButtonStyle.green, custom_id="ticket_whitelist"))
        self.add_item(Button(label="Purge", style=discord.ButtonStyle.red, custom_id="ticket_purge"))
        # High Test only for LT3+
        high_test_button = Button(label="High Test", style=discord.ButtonStyle.gray, custom_id="ticket_hightest")
        self.add_item(high_test_button)

    async def interaction_check(self, interaction: Interaction) -> bool:
        lt3_index = TIERS.index("LT3")
        user_tiers = [role.name for role in interaction.user.roles if role.name in TIERS]
        user_highest = max((TIERS.index(t) for t in user_tiers), default=-1)
        high_test_button = next((btn for btn in self.children if btn.custom_id == "ticket_hightest"), None)
        if user_highest >= lt3_index:
            if high_test_button:
                high_test_button.disabled = False
        else:
            if high_test_button:
                high_test_button.disabled = True
        return True

@tree.command(name="setup_ticket", description="Setup the ticket system in this channel", guild=discord.Object(id=YOUR_GUILD_ID))
async def setup_ticket(interaction: Interaction):
    guild = interaction.guild
    # Create categories if not exist
    categories = {}
    for cat_name in ["Support", "Whitelist", "Purge", "High Test"]:
        category = discord.utils.get(guild.categories, name=cat_name)
        if category is None:
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
            category_name_map = {
                "support": "Support",
                "whitelist": "Whitelist",
                "purge": "Purge",
                "hightest": "High Test"
            }
            category_name = category_name_map.get(category_key)
            if not category_name:
                await interaction.response.send_message("❌ Invalid ticket category.", ephemeral=True)
                return

            guild = interaction.guild
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                category = await guild.create_category(category_name)

            # Check if user has LT3 or above role before allowing to create tickets in High Test
            if category_name == "High Test":
                lt3_index = TIERS.index("LT3")
                user_tiers = [role.name for role in interaction.user.roles if role.name in TIERS]
                user_highest = max((TIERS.index(t) for t in user_tiers), default=-1)
                if user_highest < lt3_index:
                    await interaction.response.send_message("❌ You need LT3 or higher role to open High Test tickets.", ephemeral=True)
                    return

            # Check if user already has an open ticket channel in this category
            existing_channel = discord.utils.find(
                lambda c: c.name == f"{interaction.user.name.lower()}-{category_name.lower()}" and c.category == category,
                guild.channels
            )
            if existing_channel:
                await interaction.response.send_message(f"❌ You already have an open ticket here: {existing_channel.mention}", ephemeral=True)
                return

            # Create the ticket channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            # Allow members with roles higher than bot to see and send in ticket channel
            bot_member = guild.get_member(bot.user.id)
            for member in guild.members:
                if member.top_role > bot_member.top_role:
                    overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            channel_name = f"{interaction.user.name.lower()}-{category_name.lower()}"
            channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            await channel.send(f"📩 Ticket created by {interaction.user.mention} for **{category_name}**.")

            await interaction.response.send_message(f"🎫 Your **{category_name}** ticket has been created: {channel.mention}", ephemeral=True)

# Ticket commands

@tree.command(name="close", description="Close this ticket", guild=discord.Object(id=YOUR_GUILD_ID))
async def close(interaction: Interaction):
    if isinstance(interaction.channel, discord.TextChannel):
        if interaction.channel.name.startswith(tuple(f"{name.lower()}-" for name in ["support", "whitelist", "purge", "high test"])):
            await interaction.response.send_message("🗑️ Closing ticket in 5 seconds...", ephemeral=True)
            await discord.utils.sleep_until(datetime.utcnow() + discord.utils.timedelta(seconds=5))
            try:
                await interaction.channel.delete()
            except Exception as e:
                await interaction.followup.send(f"Error deleting channel: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)

@tree.command(name="add_user", description="Add a user to this ticket", guild=discord.Object(id=YOUR_GUILD_ID))
@app_commands.describe(user="The user to add to the ticket")
async def add_user(interaction: Interaction, user: Member):
    if isinstance(interaction.channel, discord.TextChannel):
        if interaction.channel.name.startswith(tuple(f"{name.lower()}-" for name in ["support", "whitelist", "purge", "high test"])):
            perms = interaction.channel.permissions_for(interaction.user)
            if not perms.manage_channels:
                await interaction.response.send_message("❌ You don't have permission to add users.", ephemeral=True)
                return
            await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
            await interaction.response.send_message(f"✅ Added {user.mention} to this ticket.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)

@tree.command(name="remove_user", description="Remove a user from this ticket", guild=discord.Object(id=YOUR_GUILD_ID))
@app_commands.describe(user="The user to remove from the ticket")
async def remove_user(interaction: Interaction, user: Member):
    if isinstance(interaction.channel, discord.TextChannel):
        if interaction.channel.name.startswith(tuple(f"{name.lower()}-" for name in ["support", "whitelist", "purge", "high test"])):
            perms = interaction.channel.permissions_for(interaction.user)
            if not perms.manage_channels:
                await interaction.response.send_message("❌ You don't have permission to remove users.", ephemeral=True)
                return
            await interaction.channel.set_permissions(user, overwrite=None)
            await interaction.response.send_message(f"❌ Removed {user.mention} from this ticket.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)

keep_alive()
token = os.getenv("TOKEN")
bot.run(token)
