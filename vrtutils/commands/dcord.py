import datetime
import json
import math
import string
import typing as t
import unicodedata

import discord
from redbot.core import commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import pagify, text_to_file

from ..abc import MixinMeta
from ..common.dpymenu import DEFAULT_CONTROLS, confirm, menu


class Dcord(MixinMeta):
    @commands.command()
    @commands.is_owner()
    async def findguildbyid(self, ctx, guild_id: int):
        """Find a guild by ID"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            try:
                guild = await self.bot.fetch_guild(guild_id)
            except discord.Forbidden:
                guild = None
        if not guild:
            return await ctx.send("Could not find that guild")
        await ctx.send(f"That ID belongs to the guild `{guild.name}`")

    @commands.command()
    async def getuser(self, ctx, *, user_id: t.Union[int, discord.User]):
        """Find a user by ID"""
        if isinstance(user_id, int):
            try:
                member = await self.bot.get_or_fetch_user(int(user_id))
            except discord.NotFound:
                return await ctx.send(f"I could not find any users with the ID `{user_id}`")
        else:
            try:
                member = await self.bot.get_or_fetch_user(user_id.id)
            except discord.NotFound:
                return await ctx.send(f"I could not find any users with the ID `{user_id.id}`")
        since_created = f"<t:{int(member.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:R>"
        user_created = f"<t:{int(member.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:D>"
        created_on = f"Joined Discord on {user_created}\n({since_created})"
        embed = discord.Embed(
            title=f"{member.name} - {member.id}",
            description=created_on,
            color=await ctx.embed_color(),
        )
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True)
    async def usersjson(self, ctx: commands.Context):
        """Get a json file containing all non-bot usernames/ID's in this guild"""
        members = {str(member.id): member.name for member in ctx.guild.members if not member.bot}
        file = text_to_file(json.dumps(members))
        await ctx.send("Here are all usernames and their ID's for this guild", file=file)

    @commands.command()
    @commands.guild_only()
    async def oldestchannels(self, ctx, amount: int = 10):
        """See which channel is the oldest"""
        async with ctx.typing():
            channels = [c for c in ctx.guild.channels if not isinstance(c, discord.CategoryChannel)]
            c_sort = sorted(channels, key=lambda x: x.created_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {c.mention} "
                    f"created <t:{int(c.created_at.timestamp())}:f> (<t:{int(c.created_at.timestamp())}:R>)"
                    for i, c in enumerate(c_sort[:amount])
                ]
            )
            for p in pagify(txt, page_length=4000):
                em = discord.Embed(description=p, color=ctx.author.color)
                await ctx.send(embed=em)

    @commands.command(aliases=["oldestusers"])
    @commands.guild_only()
    async def oldestmembers(
        self,
        ctx,
        amount: t.Optional[int] = 10,
        include_bots: t.Optional[bool] = False,
    ):
        """
        See which users have been in the server the longest

        **Arguments**
        `amount:` how many members to display
        `include_bots:` (True/False) whether to include bots
        """
        async with ctx.typing():
            if include_bots:
                members = [m for m in ctx.guild.members]
            else:
                members = [m for m in ctx.guild.members if not m.bot]
            m_sort = sorted(members, key=lambda x: x.joined_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {m} "
                    f"joined <t:{int(m.joined_at.timestamp())}:f> (<t:{int(m.joined_at.timestamp())}:R>)"
                    for i, m in enumerate(m_sort[:amount])
                ]
            )

        embeds = [discord.Embed(description=p, color=ctx.author.color) for p in pagify(txt, page_length=2000)]
        pages = len(embeds)
        for idx, i in enumerate(embeds):
            i.set_footer(text=f"Page {idx + 1}/{pages}")
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command()
    @commands.guild_only()
    async def oldestaccounts(
        self,
        ctx,
        amount: t.Optional[int] = 10,
        include_bots: t.Optional[bool] = False,
    ):
        """
        See which users have the oldest Discord accounts

        **Arguments**
        `amount:` how many members to display
        `include_bots:` (True/False) whether to include bots
        """
        async with ctx.typing():
            if include_bots:
                members = [m for m in ctx.guild.members]
            else:
                members = [m for m in ctx.guild.members if not m.bot]
            m_sort = sorted(members, key=lambda x: x.created_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {m} "
                    f"created <t:{int(m.created_at.timestamp())}:f> (<t:{int(m.created_at.timestamp())}:R>)"
                    for i, m in enumerate(m_sort[:amount])
                ]
            )

        embeds = [discord.Embed(description=p, color=ctx.author.color) for p in pagify(txt, page_length=2000)]
        pages = len(embeds)
        for idx, i in enumerate(embeds):
            i.set_footer(text=f"Page {idx + 1}/{pages}")
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command()
    @commands.guild_only()
    async def rolemembers(self, ctx, role: discord.Role):
        """View all members that have a specific role"""
        members = []
        async for member in AsyncIter(ctx.guild.members, steps=500, delay=0.001):
            if role.id in [r.id for r in member.roles]:
                members.append(member)

        if not members:
            return await ctx.send(f"There are no members with the {role.mention} role")

        members = sorted(members, key=lambda x: x.name)
        start = 0
        stop = 10
        pages = math.ceil(len(members) / 10)
        embeds = []
        for p in range(pages):
            if stop > len(members):
                stop = len(members)

            page = ""
            for i in range(start, stop, 1):
                member = members[i]
                page += f"{member.name} - `{member.id}`\n"
            em = discord.Embed(
                title=f"Members with role {role.name}",
                description=page,
                color=ctx.author.color,
            )
            em.set_footer(text=f"Page {p + 1}/{pages}")
            embeds.append(em)
            start += 10
            stop += 10

        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command()
    @commands.guildowner()
    @commands.guild_only()
    async def wipevcs(self, ctx: commands.Context):
        """
        Clear all voice channels from a server
        """
        msg = await ctx.send("Are you sure you want to clear **ALL** Voice Channels from this server?")
        yes = await confirm(ctx, msg)
        if yes is None:
            return
        if not yes:
            return await msg.edit(content="Not deleting all VC's")
        perm = ctx.guild.me.guild_permissions.manage_channels
        if not perm:
            return await msg.edit(content="I dont have perms to manage channels")
        deleted = 0
        for chan in ctx.guild.channels:
            if isinstance(chan, discord.TextChannel):
                continue
            try:
                await chan.delete()
                deleted += 1
            except Exception:
                pass
        if deleted:
            await msg.edit(content=f"Deleted {deleted} VCs!")
        else:
            await msg.edit(content="No VCs to delete!")

    @commands.command()
    @commands.guildowner()
    @commands.guild_only()
    async def wipethreads(self, ctx: commands.Context):
        """
        Clear all threads from a server
        """
        msg = await ctx.send("Are you sure you want to clear **ALL** threads from this server?")
        yes = await confirm(ctx, msg)
        if yes is None:
            return
        if not yes:
            return await msg.edit(content="Not deleting all threads")
        perm = ctx.guild.me.guild_permissions.manage_threads
        if not perm:
            return await msg.edit(content="I dont have perms to manage threads")
        deleted = 0
        for thread in ctx.guild.threads:
            await thread.delete()
            deleted += 1
        if deleted:
            await msg.edit(content=f"Deleted {deleted} threads!")
        else:
            await msg.edit(content="No threads to delete!")

    @commands.command(name="emojidata")
    @commands.bot_has_permissions(embed_links=True)
    async def emoji_info(self, ctx: commands.Context, emoji: t.Union[discord.Emoji, discord.PartialEmoji, str]):
        """Get info about an emoji"""

        def _url():
            emoji_unicode = []
            for char in emoji:
                char = hex(ord(char))[2:]
                emoji_unicode.append(char)
            if "200d" not in emoji_unicode:
                emoji_unicode = list(filter(lambda c: c != "fe0f", emoji_unicode))
            emoji_unicode = "-".join(emoji_unicode)
            return f"https://twemoji.maxcdn.com/v/latest/72x72/{emoji_unicode}.png"

        unescapable = string.ascii_letters + string.digits
        embed = discord.Embed(color=ctx.author.color)
        if isinstance(emoji, str):
            if emoji.startswith("http"):
                return await ctx.send("This is not an emoji!")

            fail = "Unable to get emoji name"
            txt = "\n".join(map(lambda x: unicodedata.name(x, fail), emoji)) + "\n\n"
            unicode = ", ".join(f"\\{i}" if i not in unescapable else i for i in emoji)
            category = ", ".join(unicodedata.category(c) for c in emoji)
            txt += f"`Unicode:   `{unicode}\n"
            txt += f"`Category:  `{category}\n"
            embed.set_image(url=_url())
        else:
            txt = emoji.name + "\n\n"
            txt += f"`ID:        `{emoji.id}\n"
            txt += f"`Animated:  `{emoji.animated}\n"
            txt += f"`Created:   `<t:{int(emoji.created_at.timestamp())}:F>\n"
            embed.set_image(url=emoji.url)

        if isinstance(emoji, discord.PartialEmoji):
            txt += f"`Custom:    `{emoji.is_custom_emoji()}\n"
        elif isinstance(emoji, discord.Emoji):
            txt += f"`Managed:   `{emoji.managed}\n"
            txt += f"`Server:    `{emoji.guild}\n"
            txt += f"`Available: `{emoji.available}\n"
            txt += f"`BotCanUse: `{emoji.is_usable()}\n"
            if emoji.roles:
                mentions = ", ".join([i.mention for i in emoji.roles])
                embed.add_field(name="Roles", value=mentions)

        embed.description = txt
        await ctx.send(embed=embed)
