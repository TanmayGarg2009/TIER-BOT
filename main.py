import discord
from discord import app_commands, Interaction, SelectOption
from discord.ext import commands
from discord.ui import View, Select

# Tier constants (used to check if user is LT3 or higher)
TIERS = ["LT5", "LT4", "LT3", "LT2", "LT1", "HT5", "HT4", "HT3", "HT2", "HT1"]
ADMIN_ROLE_NAME = "ヅAdmin"  # Target role for access
GUILD_ID = 1346134488547332217  # Replace with your actual server ID

# Function to get highest tier role from a member
def get_highest_tier(roles):
    tier_roles = [role.name for role in roles if role.name in TIERS]
    if not tier_roles:
        return None
    return sorted(tier_roles, key=lambda x: TIERS.index(x))[-1]

# Function to check if user has Admin or higher
def has_admin_or_higher(member: discord.Member):
    admin_role = discord.utils.get(member.guild.roles, name=ADMIN_ROLE_NAME)
    if not admin_role:
        return False
    return any(role.position >= admin_role.position for role in member.roles)

class TicketSelect(Select):
    def __init__(self, user: discord.Member):
        options = [
            SelectOption(label="Support", value="Support", description="General support."),
            SelectOption(label="Whitelist", value="Whitelist", description="Whitelist request."),
            SelectOption(label="Purge", value="Purge", description="Request a purge."),
        ]

        if get_highest_tier(user.roles) in TIERS[2:]:  # LT3 or higher
            options.append(SelectOption(label="High test", value="High test", description="High level test request."))

        super().__init__(
            placeholder="Choose a ticket type...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: Interaction):
        ticket_type = self.values[0]
        guild = interaction.guild
        user = interaction.user

        category = discord.utils.get(guild.categories, name=ticket_type)
        if not category:
            category = await guild.create_category(ticket_type)

        channel_name = f"{user.name}_{ticket_type}".replace(" ", "_").lower()
        existing_channel = discord.utils.get(category.channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"❌ You already have an open ticket: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }

        # Allow Admin and all roles above Admin
        for role in guild.roles:
            if role.name == ADMIN_ROLE_NAME or role.position >= discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME).position:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        await channel.send(f"<@&{discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME).id}> {user.mention}, welcome to your `{ticket_type}` ticket!")
        await interaction.response.send_message(f"🎟️ Ticket created: {channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(user))

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.tree.command(name="setup_ticket", description="Set up the ticket panel in this channel")
async def setup_ticket(interaction: Interaction):
    if not has_admin_or_higher(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this.", ephemeral=True)
        return

    view = TicketView(interaction.user)
    await interaction.response.send_message("📬 **Select a ticket option below to create your ticket:**", view=view)

@bot.tree.command(name="adduser", description="Add a user to this ticket channel")
@app_commands.describe(user="User to add")
async def add_user(interaction: Interaction, user: discord.Member):
    channel = interaction.channel
    if isinstance(channel, discord.TextChannel):
        await channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(f"✅ {user.mention} has been added to the ticket.", ephemeral=True)

@bot.tree.command(name="removeuser", description="Remove a user from this ticket channel")
@app_commands.describe(user="User to remove")
async def remove_user(interaction: Interaction, user: discord.Member):
    channel = interaction.channel
    if isinstance(channel, discord.TextChannel):
        await channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"✅ {user.mention} has been removed from the ticket.", ephemeral=True)

# Start the bot
bot.run(os.environ['TOKEN'])
