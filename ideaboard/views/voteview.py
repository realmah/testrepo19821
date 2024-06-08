import logging
from contextlib import suppress
from datetime import datetime

import discord
from redbot.core.bot import Red
from redbot.core.i18n import Translator

from ..abc import MixinMeta

log = logging.getLogger("red.vrt.ideaboard.views.voteview")
_ = Translator("IdeaBoard", __file__)


class VoteView(discord.ui.View):
    def __init__(
        self,
        cog: MixinMeta,
        guild: discord.Guild,
        suggestion_number: int,
        suggestion_id: str,
    ):
        super().__init__(timeout=None)
        self.cog: MixinMeta = cog
        self.bot: Red = cog.bot
        self.guild = guild
        self.suggestion_number = suggestion_number

        up, down = cog.db.get_conf(guild).get_emojis(cog.bot)
        self.upvote.emoji = up
        self.upvote.custom_id = f"upvote_{suggestion_id}"
        self.downvote.emoji = down
        self.downvote.custom_id = f"downvote_{suggestion_id}"

        self.update_labels()

    def update_labels(self):
        conf = self.cog.db.get_conf(self.guild)
        if not conf.show_vote_counts:
            return
        if suggestion := conf.suggestions.get(self.suggestion_number):
            if upvotes := len(suggestion.upvotes):
                self.upvote.label = str(upvotes)
            else:
                self.upvote.label = None

            if downvotes := len(suggestion.downvotes):
                self.downvote.label = str(downvotes)
            else:
                self.downvote.label = None

    async def check(self, interaction: discord.Interaction) -> bool:
        """Return True if the user can vote"""
        conf = self.cog.db.get_conf(self.guild)
        suggestion = conf.suggestions.get(self.suggestion_number)
        if not suggestion:
            txt = _("This suggestion no longer exists in the config!")
            return await interaction.response.send_message(txt, ephemeral=True)

        # Check voting requirements
        voter = self.guild.get_member(interaction.user.id)
        if not voter:
            # This should never happen
            return False

        # Check blacklists
        if voter.id in conf.user_blacklist:
            await interaction.response.send_message(_("You are blacklisted from voting."), ephemeral=True)
            return False
        if any(role.id in conf.role_blacklist for role in voter.roles):
            await interaction.response.send_message(_("You have a blacklisted role and cannot vote."), ephemeral=True)
            return False

        # If vote_roles isnt empty, make sure voter has one of the roles
        if conf.vote_roles and not any(role.id in conf.vote_roles for role in voter.roles):
            await interaction.response.send_message(_("You do not have the required roles to vote."), ephemeral=True)
            return False

        # Check account age
        if conf.min_account_age_to_vote:
            age = (datetime.now().astimezone() - voter.created_at).total_seconds() / 3600
            if age < conf.min_account_age_to_vote:
                await interaction.response.send_message(
                    _("Your account is too young to vote. You must wait {age} more hours.").format(
                        age=conf.min_account_age_to_vote - age
                    ),
                    ephemeral=True,
                )
                return False

        # Check join time
        if conf.min_join_time_to_vote:
            age = (datetime.now().astimezone() - voter.joined_at).total_seconds() / 3600
            if age < conf.min_join_time_to_vote:
                await interaction.response.send_message(
                    _("You must wait {age} more hours before you can vote.").format(
                        age=conf.min_join_time_to_vote - age
                    ),
                    ephemeral=True,
                )
                return False

        # Check LevelUp requirement
        if conf.min_level_to_vote and self.bot.get_cog("LevelUp"):
            try:
                levelup = self.bot.get_cog("LevelUp")
                if self.guild.id in levelup.data:
                    levelup.init_user(self.guild.id, str(interaction.user.id))
                    level = levelup.data[self.guild.id]["users"][str(interaction.user.id)]["level"]
                    if level < conf.min_level_to_vote:
                        await interaction.response.send_message(
                            _("You must be level {level} to vote.").format(level=conf.min_level_to_vote), ephemeral=True
                        )
                        return False
            except Exception as e:
                log.exception("Error checking LevelUp requirement", exc_info=e)

        # Check ArkTools requirement
        if conf.min_playtime_to_vote and self.bot.get_cog("ArkTools"):
            try:
                arktools = self.bot.get_cog("ArkTools")
                player = await arktools.db_utils.search_player_cached(self.guild, interaction.user)
                if not player:
                    prefixes = await self.bot.get_valid_prefixes()
                    prefix = prefixes[0]
                    txt = _("Your in-game profile must be registered in order to vote on suggestions.\n")
                    txt += _("Use the {} command to link your discord account.").format(f"`{prefix}register`")
                    await interaction.response.send_message(txt, ephemeral=True)
                    return False
                playtime_hours = player.total_playtime / 3600
                if playtime_hours < conf.min_playtime_to_vote:
                    await interaction.response.send_message(
                        _("You must have at least {hours} hours of playtime to vote.").format(
                            hours=conf.min_playtime_to_vote
                        ),
                        ephemeral=True,
                    )
                    return False
            except Exception as e:
                log.exception("Error checking ArkTools requirement", exc_info=e)

        return True

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def upvote(self, interaction: discord.Interaction, buttons: discord.ui.Button):
        if not await self.check(interaction):
            return
        with suppress(discord.NotFound):
            await interaction.response.defer()

        conf = self.cog.db.get_conf(self.guild)
        profile = conf.get_profile(interaction.user)
        suggestion = conf.suggestions[self.suggestion_number]
        uid = interaction.user.id
        if uid in suggestion.downvotes:
            txt = _("You have switched your downvote to an upvote.")
            suggestion.upvotes.append(uid)
            suggestion.downvotes.remove(uid)
            profile.upvotes += 1
            profile.downvotes -= 1
        elif uid in suggestion.upvotes:
            txt = _("You have removed your upvote.")
            suggestion.upvotes.remove(uid)
            profile.upvotes -= 1
        else:
            txt = _("You have upvoted this suggestion.")
            suggestion.upvotes.append(uid)
            profile.upvotes += 1

        await interaction.followup.send(txt, ephemeral=True)

        if conf.show_vote_counts:
            self.update_labels()
            await interaction.message.edit(view=self)

        await self.cog.save()

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def downvote(self, interaction: discord.Interaction, buttons: discord.ui.Button):
        if not await self.check(interaction):
            return
        with suppress(discord.NotFound):
            await interaction.response.defer()

        conf = self.cog.db.get_conf(self.guild)
        profile = conf.get_profile(interaction.user)
        suggestion = conf.suggestions[self.suggestion_number]
        uid = interaction.user.id
        if uid in suggestion.upvotes:
            txt = _("You have switched your upvote to a downvote.")
            suggestion.upvotes.remove(uid)
            suggestion.downvotes.append(uid)
            profile.upvotes -= 1
            profile.downvotes += 1
        elif uid in suggestion.downvotes:
            txt = _("You have removed your downvote.")
            suggestion.downvotes.remove(uid)
            profile.downvotes -= 1
        else:
            txt = _("You have downvoted this suggestion.")
            suggestion.downvotes.append(uid)
            profile.downvotes += 1

        await interaction.followup.send(txt, ephemeral=True)

        if conf.show_vote_counts:
            self.update_labels()
            await interaction.message.edit(view=self)

        await self.cog.save()
