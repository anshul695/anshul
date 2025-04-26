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

TICKET_CHANNEL_ID = 1365339429539024946  # Replace with your ticket channel ID
TICKET_CATEGORY_ID = 1363040295943536700  # Replace with your ticket category ID
STAFF_ROLE_NAME = "Staff"  # Replace with your staff role name
LOGS_CHANNEL_ID = 1361975087124971693  # Replace with your logs channel ID
TRANSCRIPTS_CHANNEL_ID = 1361975087124971693  # Permanent transcripts channel

# Global variable to track ticket ID (persistent across restarts)
ticket_counter = 1


def get_ticket_id():
    global ticket_counter
    ticket_id = f"Op-{ticket_counter:04d}"
    ticket_counter += 1
    return ticket_id


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

        ticket_id = get_ticket_id()
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"{ticket_id}",
            category=category
        )

        # Set permissions for the new ticket channel
        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            await ticket_channel.set_permissions(staff_role, read_messages=True)
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

        # Embed for the ticket
        embed = discord.Embed(
            title=f"Ticket {ticket_id} for {team_name}",
            description=f"**Issue**: {issue}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Opened by {interaction.user}")
        embed.add_field(name="⚠️ Action Required", value="Please provide proof of your issue within this ticket.", inline=False)

        # Send embed and prompt for proof
        ticket_message = await ticket_channel.send(embed=embed)

        # Log ticket creation in the logs channel
        logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            await logs_channel.send(f"Ticket {ticket_id} created by {interaction.user} in {ticket_channel.mention}")

        # Respond to the user with confirmation
        await interaction.response.send_message(f"✅ Your ticket {ticket_id} has been created! Please provide proof in {ticket_channel.mention}.", ephemeral=True)

        # Add Close and Delete buttons
        await self.add_ticket_buttons(ticket_channel, ticket_id)

    async def add_ticket_buttons(self, ticket_channel, ticket_id):
        close_button = Button(label="Close Ticket", style=discord.ButtonStyle.red)
        delete_button = Button(label="Delete Ticket", style=discord.ButtonStyle.grey)

        async def close_callback(interaction):
            await ticket_channel.delete()
            await interaction.response.send_message("Ticket closed.", ephemeral=True)

        async def delete_callback(interaction):
            await ticket_channel.delete()
            logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
            if logs_channel:
                await logs_channel.send(f"Ticket {ticket_id} was deleted by {interaction.user}.")
            await interaction.response.send_message("Ticket deleted.", ephemeral=True)

        close_button.callback = close_callback
        delete_button.callback = delete_callback

        view = View()
        view.add_item(close_button)
        view.add_item(delete_button)
        await ticket_channel.send("Ticket is now being processed. You may close or delete it using the buttons below.", view=view)


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
