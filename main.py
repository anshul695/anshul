import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os
from dotenv import load_dotenv
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_webserver():
    app.run(host='0.0.0.0', port=8080)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="%", intents=intents)

TICKET_CHANNEL_ID = 1365339429539024946  # Channel to post the "Open Ticket" button
TICKET_CATEGORY_ID = 1363040295943536700  # Category where tickets will be created
STAFF_ROLE_NAME = "Staff"  # Name of your staff role
LOGS_CHANNEL_ID = 1361974563952529583  # Ticket activity (opened/closed)
TRANSCRIPTS_CHANNEL_ID = 1361975087124971693  # Ticket transcripts (saved chat)

# --- Ticket Modal ---
class TicketModal(Modal, title="🎟️ Open a Ticket"):
    team_name = TextInput(label="Team Name", placeholder="Enter your team name", required=True)
    issue = TextInput(label="Issue", placeholder="Describe your issue", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        raw_team_name = self.team_name.value.strip()
        team_name_base = raw_team_name.replace(" ", "-").lower()
        issue_text = self.issue.value.strip()

        category = discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("❌ Ticket category not found.", ephemeral=True)
            return

        # Create a unique channel name always
        existing_names = [c.name for c in category.channels]
        final_name = team_name_base
        counter = 1
        while final_name in existing_names:
            counter += 1
            final_name = f"{team_name_base}-{counter}"

        ticket_channel = await interaction.guild.create_text_channel(
            name=final_name,
            category=category
        )

        # Set permissions
        await ticket_channel.set_permissions(interaction.guild.default_role, view_channel=False)
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            await ticket_channel.set_permissions(staff_role, view_channel=True, send_messages=True, read_message_history=True)
        await ticket_channel.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)

        # Send ticket info
        embed = discord.Embed(
            title=f"🎟️ Ticket for {raw_team_name}",
            description=f"**Issue:** {issue_text}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="📸 Proof Needed", value=f"{interaction.user.mention} Please upload any required proof below!", inline=False)
        embed.set_footer(text=f"Opened by {interaction.user}", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)

        await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed, view=TicketManageButtons())

        # Log ticket creation
        logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            await logs_channel.send(f"🆕 Ticket created by {interaction.user.mention} ➔ {ticket_channel.mention}")

        # Confirm to user
        await interaction.response.send_message(f"✅ Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

# --- Ticket Manage Buttons ---
# --- Ticket Management Buttons (Close/Delete) ---
class TicketManageButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.secondary, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("🔒 Ticket closed. Only staff can now respond.", ephemeral=True)

        # Log ticket closure
        logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            await logs_channel.send(f"🔒 {interaction.user.mention} closed the ticket `{interaction.channel.name}`.")

    @discord.ui.button(label="🗑️ Delete Ticket", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🗑️ Deleting ticket and saving transcript...", ephemeral=True)

        # Save messages from the ticket channel
        messages = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            messages.append(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author}: {msg.content}")

        transcript_text = "\n".join(messages) if messages else "No messages."

        filename = f"transcript-{interaction.channel.name}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        # Send the transcript
        transcripts_channel = bot.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if transcripts_channel:
            await transcripts_channel.send(
                content=f"📝 Transcript for {interaction.channel.name}:",
                file=discord.File(filename)
            )

        # Log deletion
        logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            await logs_channel.send(f"🗑️ {interaction.user.mention} deleted the ticket `{interaction.channel.name}`.")

        os.remove(filename)
        await interaction.channel.delete()

# --- Open Ticket Button ---
class OpenTicketButton(Button):
    def __init__(self):
        super().__init__(label="🎟️ Open Ticket", style=discord.ButtonStyle.success, custom_id="open_ticket")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())

# --- Ticket Button View ---
class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())

# --- Bot Events ---
@bot.event
async def on_ready():
    print(f"✅ Bot is ready. Logged in as {bot.user}")
    bot.add_view(TicketButtonView())

# --- Setup Command ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Ticket channel not found.")
        return

    embed = discord.Embed(
        title="Need Help?",
        description="🎟️ Click the button below to open a ticket with our staff!",
        color=discord.Color.green()
    )
    await channel.send(embed=embed, view=TicketButtonView())
    await ctx.send("✅ Ticket system setup complete!")

@setup_ticket.error
async def setup_ticket_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need Administrator permissions to use this command.")

if __name__ == "__main__":
    threading.Thread(target=run_webserver).start()
    bot.run(os.getenv("TOKEN"))

# --- Run Bot ---
bot.run(os.getenv("TOKEN"))
