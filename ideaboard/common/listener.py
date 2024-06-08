import logging

import discord
from redbot.core import commands

from ..abc import MixinMeta

log = logging.getLogger("red.vrt.ideaboard.listeners")


class AssistantListener(MixinMeta):
    @commands.Cog.listener()
    async def on_assistant_cog_add(self, cog: commands.Cog):
        schema = {
            "name": "get_user_suggestion_stats",
            "description": (
                "Get statistics about the suggestions the user you are speaking to has made.\n"
                "This command will fetch total upvotes, downvotes, wins, losses, and more for suggestions the user may have made in the community.\n"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }
        await cog.register_function(self.qualified_name, schema)

    async def get_user_suggestion_stats(self, user: discord.Member, *args, **kwargs):
        """Get the number of suggestions a user has submitted"""
        conf = self.db.get_conf(user.guild)
        profile = conf.get_profile(user)
        txt = (
            f"Suggestion Stats for {user.display_name}\n"
            f"Total suggestions that the user made: {profile.suggestions_made}\n"
            f"Suggestions user made that were approved: {profile.suggestions_approved}\n"
            f"Suggestions user made that were denied: {profile.suggestions_denied}\n"
            f"Total upvotes: {profile.upvotes}\n"
            f"Total downvotes: {profile.downvotes}\n"
            f"Suggestions user voted on that won in their favor: {profile.wins}\n"
            f"Suggestions user voted on that did not go in their favor: {profile.losses}\n"
        )
        return txt
