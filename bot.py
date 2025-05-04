import discord
from discord.ext import commands
import os
from collections import defaultdict
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))
PUBLIC_LOG_CHANNEL_ID = int(os.getenv("PUBLIC_LOG_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_comms_data = defaultdict(lambda: {"minutes": 0, "offences": 0, "rule_breaks": []})

RULE_BREAKS = {
    "Fail RP": 180,
    "RDM": 180,
    "VDM": 180,
    "Gta Driving/Hot Repairing/DVing/Mid RP Scene": 60,
    "Abusing Bulletproof vehicles=Powergaming": 120,
    "Talking About Rules Without Staff": 120,
    "AFK Farming": 120,
    "Combat Logging": 120,
    "IRL Talk (Talking About Someone)": 120,
    "Breaking NLR": 120,
    "Power Gaming": 120,
    "Animation Exploitation": 120,
    "Scamming More Than 100K": 120,
    "Breaking Locked Agreement": 120,
    "Stream Sniping": 120,
    "Exploiting Comms Boat": 120,
    "Exploiting Farming": 120,
    "Harassment TOS (After a verbal warning)": 360,
    "ALL Twitch TOS (After a verbal warning)": 360,
    "NITRP": 360,
    "Mass Server Disrespect": 360,
    "LTAP": 360,
    "N word Hard R": 360,
    "F slur (homophobic)": 360,
    "IRL Threat": 360,
    "Forced ERP=TOS": 360,
    "Mass Tos": 360,
    "Hate Speech": 360,
    "Mocking Disability TOS": 360,
    "Initiation in Greenzone": 120,
    "Camping in Greenzone=powergaming": 120,
    "Q-Peaking (Blindfire in cover)": 60,
    "Outside Shooters No Announcement": 120,
    "Random Initiation On Police": 180,
    "Police Impersonation": 180,
    "Cop Baiting": 180,
    "Breaking Police Rules": 360,
    "LTAP FROM POLICE": 360,
    "NHS Impersonation": 180,
    "Initiation/Crimes against NHS": 180,
    "Breaking EMS Rules": 360,
    "Initiation in Staff Sit": 120,
    "Wasting Staff time (After a verbal warning)": 60,
    "Staff Disrespect (After a verbal warning)": 60,
    "RDM/VDM in Staff Sit": 180,
    "Selling Whitelisted Gangs": "PERM BAN",
    "Money/item duplication": "PERM BAN",
    "Selling Donor Cars": "PERM BAN",
    "Advertising Other Servers": "PERM BAN",
    "Giving Away/Selling NHS Equipment": "PERM BAN",
}

GROUP1 = list(RULE_BREAKS.items())[:25]
GROUP2 = list(RULE_BREAKS.items())[25:]

def build_leaderboard():
    sorted_data = sorted(user_comms_data.items(), key=lambda x: x[1]["minutes"], reverse=True)
    desc = ""
    for idx, (user_id, data) in enumerate(sorted_data, start=1):
        desc += f"**{idx}. <@{user_id}>** - {data['minutes']} minutes, {data['offences']} offences\n"
    return desc if desc else "No comms records yet."

class Group1Select(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=rule, description=f"{minutes} mins" if minutes != "PERM BAN" else "Permanent Ban")
            for rule, minutes in GROUP1
        ]
        super().__init__(placeholder="Group 1 Rules", min_values=0, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await handle_selection(self, interaction)

class Group2Select(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=rule, description=f"{minutes} mins" if minutes != "PERM BAN" else "Permanent Ban")
            for rule, minutes in GROUP2
        ]
        super().__init__(placeholder="Group 2 Rules", min_values=0, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await handle_selection(self, interaction)

async def handle_selection(select, interaction):
    selected = select.values
    if not selected:
        await interaction.response.send_message("❗ Please select a rule break.", ephemeral=True)
        return

    rule = selected[0]
    minutes = RULE_BREAKS.get(rule)

    if minutes == "PERM BAN":
        await interaction.response.send_message(f"🚫 **{rule}** is a permanent ban offence. No comms assigned.", ephemeral=True)
        return

    user_id = interaction.user.id
    user_data = user_comms_data[user_id]
    user_data["minutes"] += minutes
    user_data["offences"] += 1
    user_data["rule_breaks"].append(rule)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    await log_channel.send(f"🛑 **{interaction.user.mention}** received **{minutes} minutes** in comms for **{rule}**.")

    guild = interaction.guild
    member = guild.get_member(user_id)
    if member:
        thresholds = [
            (240, "Strike 1", "You have reached 4 hours (240+ minutes) of comms. This is your first strike."),
            (480, "Strike 2", "You have reached 8 hours (480+ minutes) of comms. This is your second strike."),
            (720, "Strike 3", "You have reached 12 hours (720+ minutes) of comms. You are flagged as a problem player."),
        ]
        for threshold, role_name, dm_message in thresholds:
            role = discord.utils.get(guild.roles, name=role_name)
            if user_data["minutes"] >= threshold and role and role not in member.roles:
                try:
                    await member.add_roles(role, reason="Automatic comms penalty")
                    await member.send(f"⚠️ {dm_message}")
                    public_log_channel = bot.get_channel(PUBLIC_LOG_CHANNEL_ID)
                    if public_log_channel:
                        await public_log_channel.send(
                            f"⚠️ {member.mention} has been given **{role_name}** for reaching {threshold}+ minutes in comms."
                        )
                except Exception as e:
                    print(f"Failed to assign role or DM: {e}")

    leaderboard_channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
    await leaderboard_channel.send(f"🏆 Updated Leaderboard:\n{build_leaderboard()}")

    await interaction.response.send_message("✅ Comms recorded.", ephemeral=True)

class CommsPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ Add Comms", style=discord.ButtonStyle.green, custom_id="add_comms")
    async def add_comms(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(Group1Select())
        view.add_item(Group2Select())
        await interaction.response.send_message("Select the rule break:", view=view, ephemeral=True)

    @discord.ui.button(label="🔁 Reset Comms Stats", style=discord.ButtonStyle.danger, custom_id="reset_comms")
    async def reset_comms(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ You do not have permission to reset.", ephemeral=True)
            return

        await interaction.response.send_message("Type `yes` within 10 seconds to confirm reset.", ephemeral=True)

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

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    await bot.tree.sync()
    panel_channel = bot.get_channel(PANEL_CHANNEL_ID)
    await panel_channel.purge(limit=5)
    await panel_channel.send("🛡️ **Comms Tracker Panel**", view=CommsPanel())

bot.run(TOKEN)
