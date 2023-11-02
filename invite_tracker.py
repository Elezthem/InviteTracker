# Copyright: GregTCLTK 2018-2021.
# Contact Developer on https://discord.gg/fZPcqYu4EZ (ElezthemDev#2848 | 1148954109756579902)
# Cog by: Quill (quillfires)

import nextcord
import asyncio
import json
import time
import typing
import datetime
from nextcord.ext import commands
# from nextcord.ext.commands import has_permissions
from nextcord import Embed
import sqlite3

class invite_tracker(commands.Cog):
    """
    Keep track of your invites
    """
    def __init__(self, bot):
        self.bot = bot
        self.version = "1.0.0"

        # Подключение к базе данных
        self.conn = sqlite3.connect('invite_tracker.db')
        self.cursor = self.conn.cursor()

        # Создание таблицы при необходимости
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                guild_id INTEGER,
                user_id INTEGER,
                code TEXT,
                uses INTEGER,
                PRIMARY KEY (guild_id, user_id, code)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        ''')

        self.invites = {}


        # Загружаем инвайты
        bot.loop.create_task(self.load())

    def load_logs_channels(self):
        self.cursor.execute('''
            SELECT * FROM logs_channels
        ''')

        results = self.cursor.fetchall()

        logs_channels = {}

        for result in results:
            guild_id, channel_id = result
            logs_channels[guild_id] = str(channel_id)

        return logs_channels

    async def load(self):
        await self.bot.wait_until_ready()
        # Загружаем инвайты
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except:
                pass
        
        self.logs_channel = self.load_logs_channels()

    def find_invite_by_code(self, inv_list, code):
        for inv in inv_list:
            if inv.code == code:
                return inv

    @commands.Cog.listener()
    async def on_ready(self):
        # Загружаем инвайты после подключения бота
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except:
                pass
        

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = member.guild.id
        logs_channel = self.bot.get_channel(int(self.logs_channel.get(guild_id)))

        if logs_channel is not None:
            eme = Embed(description="Just joined the server", color=0x03d692, title=" ")
            eme.set_footer(text="ID: " + str(member.id))
            eme.timestamp = member.joined_at
            try:
                invs_before = self.invites.get(guild_id, [])
                invs_after = await member.guild.invites()
                self.invites[guild_id] = invs_after
                for invite in invs_before:
                    after_invite = self.find_invite_by_code(invs_after, invite.code)
                    if after_invite and invite.uses < after_invite.uses:
                        eme.add_field(name="Used invite",
                                    value=f"Inviter: {after_invite.inviter.mention} (`{after_invite.inviter}` | `{str(after_invite.inviter.id)}`)\nCode: `{after_invite.code}`\nUses: `{str(after_invite.uses)}`", inline=False)
            except Exception as e:
                print(f"Error: {e}")
            if len(eme.fields) > 0:
                await logs_channel.send(embed=eme)


        

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = member.guild.id
        logs_channel = self.bot.get_channel(int(self.logs_channel.get(guild_id)))

        if logs_channel is not None:
            eme = Embed(description="Just left the server", color=0xff0000, title=" ")
            eme.set_footer(text="ID: " + str(member.id))
            eme.timestamp = datetime.datetime.now()
            try:
                invs_before = self.invites[guild_id]
                invs_after = await member.guild.invites()
                self.invites[guild_id] = invs_after
                for invite in invs_before:
                    if invite.uses > self.find_invite_by_code(invs_after, invite.code).uses:
                        eme.add_field(name="Used invite",
                                    value=f"Inviter: {invite.inviter.mention} (`{invite.inviter}` | `{str(invite.inviter.id)}`)\nCode: `{invite.code}`\nUses: ` {str(invite.uses)} `", inline=False)
            except Exception as e:
                print(f"Error: {e}")
            await logs_channel.send(embed=eme)


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            self.invites[guild.id] = await guild.invites()
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            self.invites.pop(guild.id)
        except:
            pass
    
    @commands.command()
    async def my_invites(self, ctx):
        user_id = ctx.author.id
        guild_id = ctx.guild.id

        self.cursor.execute('''
            SELECT code, uses FROM invites WHERE user_id = ? AND guild_id = ?
        ''', (user_id, guild_id))

        results = self.cursor.fetchall()

        total_uses = 0

        if results:
            embed = nextcord.Embed(
                title='Your Invites',
                description='Here are your invites:',
                color=0x03d692
            )

            for result in results:
                code, uses = result
                total_uses += uses
                embed.add_field(name=code, value=f'Uses: {uses}', inline=False)

            embed.add_field(name="Total Invites", value=f'Total Uses: {total_uses}', inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send('You have no invites.')

    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_logs_channel(self, ctx, channel: nextcord.TextChannel):
        guild_id = ctx.guild.id
        channel_id = channel.id

        self.cursor.execute('''
            INSERT OR REPLACE INTO logs_channels (guild_id, channel_id)
            VALUES (?, ?)
        ''', (guild_id, channel_id))

        self.conn.commit()

        # Обновляем настройку канала в переменной self.logs_channel
        self.logs_channel[guild_id] = str(channel_id)

        await ctx.send(f'Канал для журнала установлен на {channel.mention}')





def setup(bot):
    bot.add_cog(invite_tracker(bot))
