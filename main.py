import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="%", intents=intents)

TICKET_CHANNEL_ID = 1365339429539024946
TICKET_CATEGORY_ID = 1363040295943536700
STAFF_ROLE_NAME = "Staff"
LOGS_CHANNEL_ID = 1361975087124971693

class TicketModal(Modal):
    def __init__(self):
        super().__init__(title="🎟️ Open a Ticket")
        self.team_name = TextInput(label="Team Name", placeholder="Enter your team name", required=True)
        self.issue = TextInput(label="Issue", placeholder="Describe your issue", required=True)
        self.add_item(self.team_name)
        self.add_item(self.issue)

    async def callback(self, interaction: discord.Interaction):
        raw_team_name = self.team_name.value.strip()
        issue = self.issue.value

        category = discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("❌ Ticket category not found. Please contact staff.", ephemeral=True)
            return

        # Create clean channel name
        team_name = raw_team_name.replace(" ", "-").lower()

        existing_channels = [channel.name for channel in category.text_channels]
        final_name = team_name
        count = 1

        while final_name in existing_channels:
            count += 1
            final_name = f"{team_name}-{count}"

        # Create the ticket channel under the category
        ticket_channel = await category.create_text_channel(name=final_name)

        # Set permissions
        await ticket_channel.set_permissions(interaction.guild.default_role, view_channel=False)
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            await ticket_channel.set_permissions(staff_role, view_channel=True, send_messages=True)
        await ticket_channel.set_permissions(interaction.user, view_channel=True, send_messages=True)

        # Create embed
        embed = discord.Embed(
            title=f"🎟️ Ticket for {raw_team_name}",
            description=f"**Issue:** {issue}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="📸 Proof Needed", value=f"{interaction.user.mention} please upload any required proof/screenshots here.", inline=False)
        embed.set_footer(text=f"Opened by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await ticket_channel.send(embed=embed, view=TicketManageButtons())

        # Send log to logs channel
        logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            await logs_channel.send(f"🆕 Ticket created by {interaction.user.mention}: {ticket_channel.mention}")

        # Confirm to user
        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

class TicketManageButtons(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton())
        self.add_item(DeleteTicketButton())

class CloseTicketButton(Button):
    def __init__(self):
        super().__init__(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.edit(name=f"closed-{interaction.channel.name}")
            await interaction.response.send_message("🔒 Ticket closed. You can now delete it if needed.", ephemeral=True)

class DeleteTicketButton(Button):
    def __init__(self):
        super().__init__(label="🗑️ Delete Ticket", style=discord.ButtonStyle.grey, custom_id="delete_ticket")

    async def callback(self, interaction: discord.Interaction):
        logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            await logs_channel.send(f"🗑️ Ticket {interaction.channel.name} deleted by {interaction.user.mention}.")
        await interaction.channel.delete()

class OpenTicketButton(Button):
    def __init__(self):
        super().__init__(label="🎟️ Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())

@bot.event
async def on_ready():
    print(f"✅ Bot is ready. Logged in as {bot.user}")
    bot.add_view(TicketButtonView())  # ✅ Now this works perfectly

@bot.command()
async def setup_ticket(ctx):
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Ticket channel not found.")
        return

    embed = discord.Embed(
        title="💬 Need Help?",
        description="Click the button below to open a support ticket with our team!",
        color=discord.Color.green()
    )
    await channel.send(embed=embed, view=TicketButtonView())
    await ctx.send("✅ Ticket system setup complete!")

bot.run(os.getenv("TOKEN"))
