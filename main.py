import disnake
from disnake.ext import commands
import asyncio
import os

intents = disnake.Intents.default()
intents.messages = True
intents.members = True
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.InteractionBot(intents=intents)

def load_all_cogs(directories):
    for directory in directories:
        for filename in os.listdir(directory):
            if filename.endswith(".py"):
                extension = f"{directory}.{filename[:-3]}"
                try:
                    bot.load_extension(extension)
                    print(f"Loaded {extension}")
                except Exception as e:
                    print(f"Failed to load {extension}. Error: {e}")

load_all_cogs(["cogs", "event_cogs"])

@bot.event
async def on_ready():
    print(f'Logged {bot.user} ({bot.user.id})')

try:
    bot.run('')
except disnake.errors.LoginFailure:
    print("Invalid token. Please check your bot token.")
except disnake.errors.DiscordServerError as e:
    print(f"Discord server error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
