import discord
from discord import Intents
import asyncio
import os
import tempfile
import uuid

serverID = 1111111111
TOKEN = "token"

intents = Intents.default()
intents.message_content = True

async def run_cmd(command):
    """Execute Windows commands asynchronously"""
    try:
        # Create process with Windows cmd.exe (Transfer to persistant chell in future)
        process = await asyncio.create_subprocess_shell(
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
            print(f"Online: {self.user}")

client = CmdClient()

@client.event
async def on_message(message):
    if message.author == client.user or not message.guild:
        return

    if message.guild.id != serverID:
        return

    content = message.content.strip()
    
    # Help command (will be worked on more in the future)
    if content.lower() == "--help":
        help_msg = ( 
            "```--Help:\n\n"
            "Any message will be executed as a Windows command\n"
            "Command list:\n"
            "  --help                   - Show this help\n"
            "```"
        )
        await message.channel.send(help_msg)
        return

    # Execute all other messages as commands
    try:
        print(f"Executing: {content}")
        result = await run_cmd(content)
        
        # Format output for Discord (If result length is over 1900 char uppload output.txt)
        if len(result) > 1900:
            bot_dir = os.path.dirname(os.path.abspath(__file__)) 
            temp_filename = f"temp_{uuid.uuid4().hex}.txt"
            temp_filepath = os.path.join(bot_dir, temp_filename)

            with open(temp_filepath, 'w', encoding='utf-8') as temp_file:
                    temp_file.write(result)

            await message.channel.send(file=discord.File(temp_filepath))
            os.remove(temp_filepath)
            print(f"Command executed successfully") #debug
        else:
            await message.channel.send(f"```> {content}\n\n{result}```")
            print(f"Command executed successfully") #debug
        
    except Exception as e:
        await message.channel.send(f"```Error: {str(e)}```")
        print(f"Command failed: {e}") #debug

# Start the bot
client.run(TOKEN)