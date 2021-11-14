import json
import discord
from errors import GuildErrors
from discord.utils import get


class Guild_Manager:
    def __init__(self, guild: discord.guild):
        self.guild = guild
        with open("system.json", "r") as f:
            self.system = json.load(f)
            self.guilds = self.system["guilds"]

        try:
            self.guild_dict = self.guilds[str(self.guild.id)]
            self.set_attributes()
        except KeyError:
            self.add_guild()

    def set_attributes(self):
        self.authorized_roles = self.guild_dict["authorized_roles"] if hasattr(self, 'guild_dict') else []

    def to_dict(self):
        return {
            "authorized_roles": self.authorized_roles
        }

    def reload(self):
        with open("system.json", "r") as f:
            self.system = json.load(f)
            self.guilds = self.system["guilds"]
        try:
            self.guild_dict = self.guilds[str(self.guild.id)]
        except KeyError:
            pass

    def store(self):
        self.reload()
        self.guilds[self.guild.id] = self.to_dict()
        with open("system.json", "w") as f:
            json.dump(self.system, f, indent=4)
        self.reload()
        self.set_attributes()

    def add_guild(self):
        self.set_attributes()
        self.store()
        return self

    def del_guild(self):
        self.reload()
        self.set_attributes()
        try:
            self.reload()
            del self.guilds[str(self.guild.id)]
            with open("system.json", "w") as f:
                json.dump(self.system, f, indent=4)
        except KeyError:
            pass

    def add_auth_role(self, role: discord.Role):
        self.reload()
        self.set_attributes()
        if role.id not in self.authorized_roles:
            self.authorized_roles.append(role.id)
            self.store()
        else:
            raise GuildErrors.AuthRoleAlreadyAdded("This role is already in the list of authorized roles")

    def del_auth_role(self, role: discord.Role):
        self.reload()
        self.set_attributes()
        if role.id in self.authorized_roles:
            self.authorized_roles.remove(role.id)
            self.store()
        else:
            raise GuildErrors.AuthRoleNotInList("This role was not in the list.")

    def get_auth_roles(self):
        return self.authorized_roles

    @classmethod
    def get_all_guilds(self, client):
        with open("system.json", "r") as f:
            self.system = json.load(f)
            self.guilds = self.system["guilds"]

        guilds_ids = []
        for guild_id in self.guilds:
            guilds_ids.append(int(guild_id))

        return guilds_ids
