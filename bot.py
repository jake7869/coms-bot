import discord
from discord.ext import commands
import os
from collections import defaultdict
from datetime import datetime
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Data storage
user_comms_data = defaultdict(lambda: {"minutes": 0, "offences": 0, "rule_breaks": []})

# RULES from your punishment chart
RULE_BREAKS = {
    "NLR": 120,
    "Power Gaming": 120,
    "LTAP": 120,
    "Hot Mic": 20,
    "Trolling": 30,
    "VDM": 120,
    "Fail RP": 60,
    "Fear RP": 120,
    "Random Punching": 30,
    "RDM": 120,
    "Stealing Cars Not In RP": 30,
    "Breaking Character": 120,
    "Combat Logging": 120,
    "Combat Storing": 120,
    "Unrealistic Driving": 20,
    "Metagaming": 60,
    "Cop Baiting": 60,
    "Baiting Gang Members": 60,
    "Taser Spamming": 20,
    "Using Voice Changer to Troll": 30,
    "Sexual RP": "PERM BAN",
    "Homophobic/Racist/Discriminative Behaviour": "PERM BAN",
    "Using Slurs": "PERM BAN",
    "Bullying": "PERM BAN",
    "Stream Sniping": "PERM BAN",
    "Doxxing": "PERM BAN",
}

def build_leaderboard():
    sorted_data = sorted(user_comms_data.items(), key=lambda x: x[1]["minutes"], reverse=True)
    desc = ""
    for idx, (user_id, data) in enumerate(sorted_data, start=1):
        desc += f"**{idx}. <@{user_id}>** - {data['minutes']} minutes, {data['offences']} offences\n"
    return desc if desc else "No comms records yet."

class CommsPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ Add Comms", style=discord.ButtonStyle.green, custom_id="add_comms")
    async def add_comms(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddCommsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔁 Reset Comms Stats", style=discord.ButtonStyle.danger, custom_id="reset_comms")
    async def reset_comms(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("You do not have permission to reset.", ephemeral=True)
            return
        
        await interaction.response.send_message("Are you sure you want to reset? Type `yes` within 10 seconds.", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=10)
            if msg.content.lower() == "yes":
                backup = build_leaderboard()
                channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
                await channel.send(f"📋 **Backup before reset:**\n{backup}")
                user_comms_data.clear()
                await channel.send("✅ Leaderboard reset complete.")
            else:
                await interaction.followup.send("Reset cancelled.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("No confirmation received. Reset cancelled.", ephemeral=True)

class AddCommsModal(discord.ui.Modal, title="Add Comms"):
    rule_break = discord.ui.Select(
        placeholder="Select Rule Break",
        options=[discord.SelectOption(label=r) for r in RULE_BREAKS.keys()],
        custom_id="rule_break_select"
    )
    notes = discord.ui.TextInput(label="Notes (optional)", required=False, custom_id="notes")

    async def on_submit(self, interaction: discord.Interaction):
        rule = self.rule_break.values[0]
        minutes = RULE_BREAKS.get(rule, 0)

        if minutes == "PERM BAN":
            await interaction.response.send_message(f"🚫 **{rule}** is a permanent ban offence. No comms assigned.", ephemeral=True)
            return

        user_comms_data[interaction.user.id]["minutes"] += minutes
        user_comms_data[interaction.user.id]["offences"] += 1
        user_comms_data[interaction.user.id]["rule_breaks"].append(rule)

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        await log_channel.send(
            f"🛑 **{interaction.user.mention}** received **{minutes} minutes** in comms for **{rule}**.\n"
            f"📝 Notes: {self.notes.value if self.notes.value else 'No notes.'}"
        )

        leaderboard_channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
        await leaderboard_channel.send(f"🏆 Updated Leaderboard:\n{build_leaderboard()}")

        await interaction.response.send_message("✅ Comms recorded.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)")

    panel_channel = bot.get_channel(PANEL_CHANNEL_ID)
    await panel_channel.purge(limit=5)
    await panel_channel.send("🛡️ **Comms Tracker Panel**", view=CommsPanel())

bot.run(TOKEN)
