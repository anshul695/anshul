import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import random
import asyncio
import os
from dotenv import load_dotenv

# Load token from .env file
load_dotenv()

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="%", intents=intents)

# Channel ID for the Open Ticket button
TICKET_CHANNEL_ID = 1365339429539024946  # Replace with your actual channel ID
STAFF_ROLE_NAME = 'Staff'  # Replace with your actual staff role name
TICKET_CATEGORY_ID = 1363040295943536700  # Replace with the category ID you want tickets to be created in

# Persistent view to keep the button alive
class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())


class OpenTicketButton(Button):
    def __init__(self):
        super().__init__(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")

    async def callback(self, interaction):
        modal = TicketModal()
        await interaction.response.send_modal(modal)


# Modal to collect ticket information
class TicketModal(Modal):
    def __init__(self):
        super().__init__(title="Open Ticket")

        self.team_name = TextInput(label="Team Name", required=True)
        self.issue = TextInput(label="Issue", required=True)

        self.add_item(self.team_name)
        self.add_item(self.issue)



    async def callback(self, interaction: discord.Interaction):
        # Create private ticket channel
        team_name = self.team_name.value
        issue = self.issue.value
        

        category = discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORY_ID)
        ticket_channel = await interaction.guild.create_text_channel(
            f"{team_name}-{random.randint(1000, 9999)}", category=category
        )

        # Rename ticket to the team name
        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        await ticket_channel.set_permissions(staff_role, read_messages=True)

        # Send embed with ticket info
        embed = discord.Embed(
    title=f"Ticket for {team_name}",
    description=f"**Issue**: {issue}",
    color=discord.Color.blue()
)

        embed.set_footer(text=f"Ticket opened by {interaction.user}")
        await ticket_channel.send(embed=embed)

        # Respond to the user
        await interaction.response.send_message(f"Your ticket has been created! Please provide your screenshot in {ticket_channel.mention}.", ephemeral=True)

        # Add a close button when staff responds
        await self.add_close_button(ticket_channel)

    async def add_close_button(self, ticket_channel):
        # Close button for staff
        close_button = Button(label="Close Ticket", style=discord.ButtonStyle.red)

        async def close_callback(interaction):
            # When the close button is clicked, close the ticket
            await ticket_channel.delete()
            await interaction.response.send_message("Ticket closed.", ephemeral=True)

        close_button.callback = close_callback

        view = View()
        view.add_item(close_button)
        await ticket_channel.send("Ticket is now being processed.", view=view)

# Event to register the view when bot is ready
@bot.event
async def on_ready():
    bot.add_view(TicketButtonView())  # Register the view when bot is ready
    print(f"Logged in as {bot.user}")

# Command to setup the ticket system
@bot.command()
async def setup_ticket(ctx):
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    embed = discord.Embed(
        title="Create a Ticket",
        description="Click the button below to open a ticket and get assistance.",
        color=discord.Color.green()
    )
    await channel.send(embed=embed, view=TicketButtonView())

# Running the bot using token from .env
bot.run(os.getenv("TOKEN"))
