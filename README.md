This project was originally created by me as a tool to bypass organizational restrictions on locked-down school computers by enabling remote access control.  (Shoutout to my schools IT teacher for allowing me to make stuff like this instead of studying for my exams)

Over time, it developed further as a side project, evolving into a low-level experimental malware framework.

# How it works:
When executed, the program requests elevated privileges. This is the only required user interaction on the host machine.

After elevation, the program spoofs the process ID of the `svchost.exe`service and embeds a Discord bot within its child processes. The Discord bot functions as a command-and-control interface, receiving commands from a specified Discord channel, executing them on the system, and returning the output back to the channel.

This technique enables the bot to exchange commands and responses while avoiding most common network or firewall interruptions. (Proof of Concept tested on a IT focused school enviroment)

# Current Goals:
1. Establish persistance (as admin)
2. Hide proccess in proccess tree (Done)
3. Toolkit access through discord.

# Disclaimer:
This software is provided strictly for educational and research purposes. Use it only on systems that you own or on systems where you have been given explicit permission to run security tests. Any unauthorized use against systems you do not own is illegal and unethical.

I do not take any responsibility or accept any liability for how this tool is used. By choosing to download, run, or modify this project, you agree that you are solely responsible for your actions. Misuse of this software could result in legal consequences, and you assume all risks associated with its use.
