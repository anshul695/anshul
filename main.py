import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import random
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="%", intents=intents)

TICKET_CHANNEL_ID = 1365339429539024946  # Replace with your button embed channel
TICKET_CATEGORY_ID = 1363040295943536700  # Replace with your ticket category ID
STAFF_ROLE_NAME = "Staff"  # Replace with your staff role name


class TicketModal(Modal):
    def __init__(self):
        super().__init__(title="Open Ticket")
        self.team_name = TextInput(label="Team Name", required=True)
        self.issue = TextInput(label="Issue", required=True)
        self.add_item(self.team_name)
        self.add_item(self.issue)

    async def callback(self, interaction: discord.Interaction):
        team_name = self.team_name.value
        issue = self.issue.value

        category = discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("Ticket category not found.", ephemeral=True)
            return

        ticket_channel = await interaction.guild.create_text_channel(
            name=f"{team_name}-{random.randint(1000, 9999)}",
            category=category
        )

        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            await ticket_channel.set_permissions(staff_role, read_messages=True)
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title=f"Ticket for {team_name}",
            description=f"**Issue**: {issue}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Opened by {interaction.user}")

        await ticket_channel.send(embed=embed)

        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)


class OpenTicketButton(Button):
    def __init__(self):
        super().__init__(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())


class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())


@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")
    bot.add_view(TicketButtonView())


@bot.command()
async def setup_ticket(ctx):
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Ticket channel not found.")
        return

    embed = discord.Embed(
        title="Need Help?",
        description="Click the button below to open a ticket.",
        color=discord.Color.green()
    )
    await channel.send(embed=embed, view=TicketButtonView())


bot.run(os.getenv("TOKEN"))
