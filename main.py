import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="%", intents=intents)

TICKET_CHANNEL_ID = 1365339429539024946  # Where the Open Ticket button will be posted
TICKET_CATEGORY_ID = 1363040295943536700  # Ticket category ID
STAFF_ROLE_NAME = "Staff"  # Name of your staff role
TICKET_LOG_CHANNEL_ID = 1361974563952529583  # Ticket logs channel ID (replace!)
TRANSCRIPT_CHANNEL_ID = 1361975087124971693  # Ticket transcripts channel ID
COUNTER_FILE = "ticket_counter.txt"  # File to track ticket numbers


# 🔢 Generate systematic ticket numbers
def get_next_ticket_number():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("0")
    with open(COUNTER_FILE, "r+") as f:
        number = int(f.read().strip())
        number += 1
        f.seek(0)
        f.write(str(number))
        f.truncate()
    return f"{number:04}"


# 🎟️ Ticket Modal
class TicketModal(Modal):
    def __init__(self):
        super().__init__(title="🎟️ Open a Support Ticket")
        self.team_name = TextInput(label="💬 Team Name", required=True)
        self.issue = TextInput(label="🛠️ Describe the Issue", required=True, style=discord.TextStyle.paragraph)
        self.add_item(self.team_name)
        self.add_item(self.issue)

    async def callback(self, interaction: discord.Interaction):
        team_name = self.team_name.value
        issue = self.issue.value
        ticket_number = get_next_ticket_number()

        category = discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("❌ Ticket category not found.", ephemeral=True)
            return

        channel_name = f"{team_name.lower().replace(' ', '-')}-{ticket_number}"
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category
        )

        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            await ticket_channel.set_permissions(staff_role, read_messages=True, send_messages=True)
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title=f"📩 Ticket #{ticket_number} — {team_name}",
            description=(
                f"**👤 Opened by:** {interaction.user.mention}\n"
                f"**📝 Issue:**\n{issue}\n\n"
                f"📎 Please attach any **proof/screenshots** below."
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="🔔 Our staff will assist you shortly!")

        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=TicketActionView())
        await interaction.response.send_message(f"✅ Your ticket has been created: {ticket_channel.mention}", ephemeral=True)


# 🎫 Open Ticket Button
class OpenTicketButton(Button):
    def __init__(self):
        super().__init__(label="🎫 Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())


# 🔒 Close Ticket Button
class CloseTicketButton(Button):
    def __init__(self):
        super().__init__(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔒 Ticket locked! Staff will handle it soon.", ephemeral=True)
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.channel.edit(name=f"closed-{interaction.channel.name}")
        await interaction.channel.send(f"🔒 Ticket has been closed by {interaction.user.mention}. Please wait for further action.")


# 🗑️ Delete Ticket Button (with transcript saving)
class DeleteTicketButton(Button):
    def __init__(self):
        super().__init__(label="🗑️ Delete Ticket", style=discord.ButtonStyle.danger, custom_id="delete_ticket")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("🗑️ Saving transcript and deleting in 5 seconds...", ephemeral=True)

        transcript = ""
        async for message in interaction.channel.history(limit=None, oldest_first=True):
            if message.author.bot:
                continue
            transcript += f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author}: {message.content}\n"

        transcript_channel = bot.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_channel:
            file = discord.File(fp=discord.File.from_content(transcript.encode('utf-8'), filename=f"{interaction.channel.name}.txt"))
            await transcript_channel.send(content=f"📝 Transcript for {interaction.channel.name} (deleted by {interaction.user.mention}):", file=file)

        log_channel = bot.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🗑️ Ticket Deleted",
                description=f"Ticket {interaction.channel.name} was deleted by {interaction.user.mention}.",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

        await asyncio.sleep(5)
        await interaction.channel.delete()


# 🎯 Ticket Action View (Close + Delete)
class TicketActionView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton())
        self.add_item(DeleteTicketButton())


# 🌟 Ticket Button View (Open Ticket)
class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())


@bot.event
async def on_ready():
    print(f"✅ Bot is ready. Logged in as {bot.user}")
    bot.add_view(TicketButtonView())
    bot.add_view(TicketActionView())


@bot.command()
async def setup_ticket(ctx):
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Ticket channel not found.")
        return

    embed = discord.Embed(
        title="💡 Need Help?",
        description="Click the **🎫 Open Ticket** button below to get help from our staff!",
        color=discord.Color.green()
    )
    await channel.send(embed=embed, view=TicketButtonView())


bot.run(os.getenv("TOKEN"))
