import discord
from discord import app_commands
from discord.ext import commands
import time
from typing import Optional

from core.bot import Netra
from core.i18n import i18n

class Utility(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        # Assuming we have a guild or default to 'en'
        locale = "en"
        response = i18n.get(locale, "ping-response", latency=latency)
        await interaction.response.send_message(response)

    @app_commands.command(name="serverinfo", description="Get information about the server")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            
        embed = discord.Embed(title=f"Server Info: {guild.name}", color=discord.Color.blue())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown")
        embed.add_field(name="Members", value=str(guild.member_count))
        embed.add_field(name="Roles", value=str(len(guild.roles)))
        embed.add_field(name="Channels", value=str(len(guild.channels)))
        embed.set_footer(text=f"ID: {guild.id} | Created at: {guild.created_at.strftime('%Y-%m-%d')}")
        await interaction.response.send_message(embed=embed)



    @app_commands.command(name="userinfo", description="Get information about a user")
    async def userinfo(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        color = getattr(target, 'color', discord.Color.default())
        embed = discord.Embed(title=f"User Info: {target.name}", color=color)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="ID", value=str(target.id))
        
        joined_at = getattr(target, 'joined_at', None)
        embed.add_field(name="Joined At", value=joined_at.strftime('%Y-%m-%d') if joined_at else "N/A")
        
        roles = getattr(target, 'roles', [])
        if len(roles) > 1:
            embed.add_field(name="Roles", value=", ".join([role.mention for role in roles[1:10]]) + ("..." if len(roles) > 10 else ""))
        else:
            embed.add_field(name="Roles", value="None")
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite", description="Get the bot's invite link to add it to another server")
    async def invite(self, interaction: discord.Interaction):
        if not self.bot.user:
            return await interaction.response.send_message("Bot is not ready yet.", ephemeral=True)
            
        permissions = discord.Permissions(permissions=8) # Administrator permissions, or customize as needed
        invite_url = discord.utils.oauth_url(self.bot.user.id, permissions=permissions, scopes=("bot", "applications.commands"))
        
        embed = discord.Embed(
            title="Invite Netra", 
            description=f"Click [here]({invite_url}) to invite the bot to your server!", 
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="Get a list of commands and how to use them")
    async def help_command(self, interaction: discord.Interaction, command_name: Optional[str] = None):
        if command_name:
            found_cmd = None
            for cmd in self.bot.tree.walk_commands():
                if cmd.name == command_name and isinstance(cmd, app_commands.Command):
                    found_cmd = cmd
                    break
            
            if not found_cmd:
                await interaction.response.send_message(f"Command `{command_name}` not found.", ephemeral=True)
                return
            
            embed = discord.Embed(title=f"Help: /{found_cmd.name}", description=found_cmd.description or "No description provided.", color=discord.Color.blue())
            
            params_info = []
            example_cmd = f"/{found_cmd.name}"
            
            for param in found_cmd.parameters:
                req = "Required" if param.required else "Optional"
                
                # Determine type name and realistic example value
                type_name = "Text"
                example_val = '"value"'
                
                if param.type == discord.AppCommandOptionType.user:
                    type_name = "User"
                    example_val = "@User"
                elif param.type == discord.AppCommandOptionType.channel:
                    type_name = "Channel"
                    example_val = "#channel"
                elif param.type == discord.AppCommandOptionType.role:
                    type_name = "Role"
                    example_val = "@Role"
                elif param.type == discord.AppCommandOptionType.integer:
                    type_name = "Integer Number"
                    example_val = "5"
                elif param.type == discord.AppCommandOptionType.number:
                    type_name = "Decimal Number"
                    example_val = "3.5"
                elif param.type == discord.AppCommandOptionType.boolean:
                    type_name = "True/False"
                    example_val = "True"
                elif param.type == discord.AppCommandOptionType.string:
                    type_name = "Text"
                    if "time" in param.name.lower():
                        example_val = '"10m"'
                    elif "reason" in param.name.lower() or "message" in param.name.lower():
                        example_val = '"Hello there!"'
                    else:
                        example_val = '"some text"'
                
                params_info.append(f"**{param.name}** ({type_name}, {req}): {param.description}")
                
                if param.required:
                    example_cmd += f" {param.name}:{example_val}"
                else:
                    example_cmd += f" [{param.name}:{example_val}]"
            
            if params_info:
                embed.add_field(name="Parameters", value="\n".join(params_info), inline=False)
            
            embed.add_field(name="Example", value=f"`{example_cmd}`", inline=False)
            
            embed.set_footer(text="Tip: Use these parameters when typing the command in Discord.")
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="Netra Bot Help",
                description="Use `/help command_name:<name>` to get detailed information on how to use specific commands.\n\n*Note: Admin commands are natively hidden from the Discord `/` auto-complete menu for regular users.*",
                color=discord.Color.blue()
            )
            
            user_cmds = []
            admin_cmds = []
            
            for cmd in self.bot.tree.walk_commands():
                if isinstance(cmd, app_commands.Command):
                    is_admin = False
                    
                    # Check if command has default_permissions set to something restricting
                    if getattr(cmd, 'default_permissions', None) is not None and getattr(cmd.default_permissions, 'value', 0) != 0:
                        is_admin = True
                        
                    # Check close-ticket and setticket-moderator manually since they rely on DB-based roles or might not be caught
                    if cmd.name in ("close-ticket", "setticket-moderator", "setup-tickets"):
                        is_admin = True

                    cmd_text = f"**`/{cmd.name}`** - {cmd.description}"
                    if is_admin:
                        admin_cmds.append(cmd_text)
                    else:
                        user_cmds.append(cmd_text)
            
            if user_cmds:
                embed.add_field(name="👥 User Commands", value="\n".join(user_cmds), inline=False)
            if admin_cmds:
                embed.add_field(name="🛡️ Admin & Moderator Commands", value="\n".join(admin_cmds), inline=False)
                
            await interaction.response.send_message(embed=embed)

async def setup(bot: Netra):
    await bot.add_cog(Utility(bot))
