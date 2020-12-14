import discord
from discord.ext import commands

import asyncio

import datetime
import traceback
import os
import json
import sys
import humanize
import os
import codecs
import pathlib

from .utils import formats

def get_lines_of_code():
    total = 0
    file_amount = 0
    for path, subdirs, files in os.walk("."):
        if "venv" in subdirs:
            subdirs.remove("venv")
        if "env" in subdirs:
            subdirs.remove("env")
        for name in files:
            if name.endswith(".py"):
                file_amount += 1
                with codecs.open(
                    "./" + str(pathlib.PurePath(path, name)), "r", "utf-8"
                ) as f:
                    for i, l in enumerate(f):
                        total += 1

    return f"I have {total:,} lines of code, spread across {file_amount:,} files"

class RoboCoderHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        em = discord.Embed(title=f"{bot.user.name} Help", description=f"Help for Robo Coder Bot. Use `{ctx.prefix}help [command]` or `{ctx.prefix}help [Category]` for more specific help.\n", color=0x96c8da)
        msg = ""
        for name, cog in sorted(bot.cogs.items()):
            if not getattr(cog, "hidden", False):
                msg += f"\n{getattr(cog, 'emoji', '')} {cog.qualified_name}"
        em.add_field(name="Categories", value=msg)
        em.set_footer(text=bot.user.name, icon_url=bot.user.avatar_url)
        await ctx.send(embed=em)

    async def send_cog_help(self, cog):
        ctx = self.context
        bot = ctx.bot

        em = discord.Embed(title=f"{getattr(cog, 'emoji', '')} {cog.qualified_name}", description="\n", color=0x96c8da)
        commands = await self.filter_commands(cog.walk_commands())
        for command in commands:
            if not command.hidden:
                em.description += f"\n`{self.get_command_signature(command)}` {'-' if command.description else ''} {command.description}"

        em.description += "\n\nKey: `<required> [optional]`. **Remove <> and [] when using the command**."
        em.set_footer(text=bot.user.name, icon_url=bot.user.avatar_url)

        await ctx.send(embed=em)

    async def send_command_help(self, command):
        ctx = self.context
        bot = ctx.bot

        em = discord.Embed(title=f"{command.name} {command.signature}", description=command.description or "", color=0x96c8da)
        if command.aliases:
            em.description += f"\nAliases: {', '.join(command.aliases)}"
        em.description += "\n\nKey: `<required> [optional]`. **Remove <> and [] when using the command**."
        em.set_footer(text=bot.user.name, icon_url=bot.user.avatar_url)

        await ctx.send(embed=em)

    async def send_group_help(self, group):
        ctx = self.context
        bot = ctx.bot

        em = discord.Embed(title=f"{group.name} {group.signature}", description=group.description or "", color=0x96c8da)
        if group.aliases:
            em.description += f"\nAliases: {', '.join(group.aliases)} \n"

        commands = await self.filter_commands(group.commands)
        for command in group.walk_commands():
            em.description += f"\n`{self.get_command_signature(command)}` {'-' if command.description else ''} {command.description}"

        em.description += "\n\nKey: `<required> [optional]`. **Remove <> and [] when using the command**."
        em.set_footer(text=bot.user.name, icon_url=bot.user.avatar_url)

        await ctx.send(embed=em)

class Meta(commands.Cog):
    """Everything about the bot itself."""

    def __init__(self, bot):
        self.bot = bot
        self.emoji = ":gear:"

        self._original_help_command = bot.help_command
        bot.help_command = RoboCoderHelpCommand()
        bot.help_command.cog = self

        if os.path.exists("prefixes.json"):
            with open("prefixes.json", "r") as f:
                self.bot.guild_prefixes = json.load(f)
        else:
            self.bot.guild_prefixes = {}

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command can not be used in DMs")
        elif isinstance(error, commands.errors.BotMissingPermissions):
            perms_text = "\n".join([f"- {perm.replace('_', ' ').capitalize()}" for perm in error.missing_perms])
            await ctx.send(f":x: I am missing some permissions:\n {perms_text}") 
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f":x: You are missing a argument: `{error.param}`")
        elif isinstance(error, commands.errors.BadArgument) or isinstance(error, commands.errors.BadUnionArgument):
            await ctx.send(f":x: {error}")
        elif isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send(f":x: {error}")
        elif isinstance(error, ommands.errors.CommandOnCooldown):
            await ctx.send(f"You are on cooldown. Try again in {formats.plural(int(error.retry_after)):second}")
        elif isinstance(error, commands.errors.CheckFailure):
            return
        elif isinstance(error, commands.errors.CommandNotFound):
            return

        if isinstance(error, commands.CommandInvokeError):
            if isinstance(error, commands.errors.CheckFailure):
                return
            elif isinstance(error, commands.errors.CommandNotFound):
                return

            em = discord.Embed(title=":warning: Error", description="", color=discord.Color.gold(), timestamp=datetime.datetime.utcnow())
            em.description += f"\nCommand: `{ctx.command}`"
            em.description += f"\nLink: [Jump]({ctx.message.jump_url})"
            em.description += f"\n\n```py\n{error}```\n"

            await self.bot.console.send(embed=em)

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx):
        await ctx.send("prefixes: " + ", ".join(self.bot.guild_prefixes[str(ctx.guild.id)]))

    @commands.command(name="hello", aliases=["hi"])
    async def hi(self, ctx):
        await ctx.send(f":wave: Hello, I am Robo Coder!\nTo get more info use {ctx.prefix}help")

    @prefix.command(name="add", description="add a prefix")
    @commands.has_permissions(manage_guild=True)
    async def add(self, ctx, *, arg):
        self.bot.guild_prefixes[str(ctx.guild.id)].append(arg)
        with open("prefixes.json", "w") as f:
            json.dump(self.bot.guild_prefixes, f)
        await ctx.send("Added prefix: " + arg)
    
    @prefix.command(name="remove", description="remove prefix")
    @commands.has_permissions(manage_guild=True)
    async def remove(self, ctx, *, arg):
        if arg in self.bot.guild_prefixes[str(ctx.guild.id)]:
            self.bot.guild_prefixes[str(ctx.guild.id)].remove(arg)
            await ctx.send("Removed prefix: " + arg)
        else:
            await ctx.send(f"That prefix does not exist. Try '{ctx.prefix}prefixes' to get a list of prefixes")

        with open("prefixes.json", "w") as f:
            json.dump(self.bot.guild_prefixes, f)

    @prefix.command(name="prefixes", description="veiw a list of prefixes")
    @commands.guild_only()
    async def prefixes(self, ctx):
        server_prefixes = self.bot.guild_prefixes
        await ctx.send("prefixes: " + ", ".join(server_prefixes))        

    @commands.command(name="ping", description="Check my latency")
    async def ping(self, ctx):
        await ctx.send(f"My latency is {int(self.bot.latency*1000)}ms")

    @commands.group(name="uptime", description="Get the uptime", aliases=["up"], invoke_without_command=True)
    async def uptime(self, ctx):
        uptime = datetime.datetime.utcnow()-self.bot.startup_time
        await ctx.send(f"I started up {humanize.naturaldelta(uptime)} ago")
    
    @commands.command(name="invite", description="Get a invite to add me to your server")
    async def invite(self, ctx):
        perms  = discord.Permissions.none()
        perms.manage_messages = True
        perms.kick_members = True
        perms.ban_members = True
        perms.manage_channels = True
        perms.manage_roles = True
        perms.manage_webhooks = True
        invite = discord.utils.oauth_url(self.bot.user.id, permissions=perms, guild=None, redirect_uri=None)
        await ctx.send(f"<{invite}>")

    @commands.command(name="code", description="Find out what I'm made of")
    async def code(self, ctx):
        code = get_lines_of_code()
        await ctx.send(code)

def setup(bot):
    bot.add_cog(Meta(bot))
