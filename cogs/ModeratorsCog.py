import disnake
from disnake.ext import commands, tasks
import datetime
from zoneinfo import ZoneInfo
import sqlite3
import asyncio

ALLOWED_ROLE_IDS = {1389672224071614584, 1389672225833091254, 1389672227544502434, 1389672232061505707, 1389672233680638013, 1389672237002657945, 1389672246083326146, 1389672248411164833, 1389672268543819826, 1389672276995211475, 1389672351037259796, 1389672347249938593, 1389672345328947352, 1389672343235854541}

LOG_CHANNELS = {
    "mute": 1397307908978638848,
    "ban": 1397307963617710220,
    "kick": 1397307943044513882,
    "unmute": 1397307963617710220,
    "unban": 1394791416080634059
}

MSK = ZoneInfo("Europe/Moscow")


class ModeratorsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.conn = sqlite3.connect("moderation.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_bans (
                user_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                unban_at TEXT NOT NULL,
                reason TEXT
            )
        """)
        self.conn.commit()

        self.check_unbans.start()

    def cog_unload(self):
        self.check_unbans.cancel()
        self.conn.close()

    def has_permission(self, member: disnake.Member) -> bool:
        return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

    async def send_log(self, guild: disnake.Guild, action: str, embed: disnake.Embed):
        log_channel = guild.get_channel(LOG_CHANNELS.get(action))
        if log_channel:
            await log_channel.send(embed=embed)

    @commands.slash_command(description="Выдать мут пользователю.")
    async def mute(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member,
        time: int,
        reason: str
    ):
        if not self.has_permission(inter.author):
            await inter.response.send_message("Нет доступа.", ephemeral=True)
            return

        until = disnake.utils.utcnow() + datetime.timedelta(minutes=time)
        await member.timeout(until=until, reason=reason)

        dm_embed = disnake.Embed(
            title="🔇 Вы получили мут",
            description=f"**Модератор:** {inter.author.mention}\n**Время:** {time} минут\n**Причина:** {reason}",
            color=disnake.Color.orange()
        )
        dm_embed.set_footer(text="Обжалование возможно у администрации.")
        try:
            await member.send(embed=dm_embed)
        except:
            pass

        log_embed = disnake.Embed(
            title="🔇 Мут выдан",
            color=disnake.Color.orange(),
            timestamp=datetime.datetime.now(tz=MSK)
        )
        log_embed.add_field(name="Модератор", value=inter.author.mention)
        log_embed.add_field(name="Пользователь", value=member.mention)
        log_embed.add_field(name="Время", value=f"{time} минут")
        log_embed.add_field(name="Причина", value=reason)

        await self.send_log(inter.guild, "mute", log_embed)
        await inter.response.send_message(f"{member.mention} получил мут на {time} минут.", ephemeral=True)

    @commands.slash_command(description="Забанить пользователя.")
    async def ban(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member,
        reason: str,
        duration: int = commands.Param(default=None, description="Время в днях (опционально)")
    ):
        if not self.has_permission(inter.author):
            await inter.response.send_message("Нет доступа.", ephemeral=True)
            return

        dm_embed = disnake.Embed(
            title="⛔ Вы были забанены",
            description=f"**Модератор:** {inter.author.mention}\n**Причина:** {reason}" +
                        (f"\n**Срок:** {duration} дней" if duration else ""),
            color=disnake.Color.red()
        )
        dm_embed.set_footer(text="Обжалование возможно у администрации.")
        try:
            await member.send(embed=dm_embed)
        except:
            pass

        await inter.guild.ban(member, reason=reason, clean_history_duration=datetime.timedelta(days=0))

        log_embed = disnake.Embed(
            title="🔨 Пользователь забанен",
            color=disnake.Color.red(),
            timestamp=datetime.datetime.now(tz=MSK)
        )
        log_embed.add_field(name="Модератор", value=inter.author.mention)
        log_embed.add_field(name="Пользователь", value=member.mention)
        if duration:
            log_embed.add_field(name="Срок", value=f"{duration} дней")
        log_embed.add_field(name="Причина", value=reason)

        await self.send_log(inter.guild, "ban", log_embed)

        if duration:
            unban_at = datetime.datetime.utcnow() + datetime.timedelta(days=duration)
            self.cursor.execute(
                "INSERT OR REPLACE INTO temp_bans (user_id, guild_id, unban_at, reason) VALUES (?, ?, ?, ?)",
                (member.id, inter.guild.id, unban_at.isoformat(), reason)
            )
            self.conn.commit()

        await inter.response.send_message(f"{member.mention} забанен.", ephemeral=True)

    @commands.slash_command(description="Кикнуть пользователя.")
    async def kick(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member,
        reason: str
    ):
        if not self.has_permission(inter.author):
            await inter.response.send_message("Нет доступа.", ephemeral=True)
            return

        dm_embed = disnake.Embed(
            title="🚪 Вы были кикнуты",
            description=f"**Модератор:** {inter.author.mention}\n**Причина:** {reason}",
            color=disnake.Color.orange()
        )
        dm_embed.set_footer(text="Обжалование возможно у администрации.")
        try:
            await member.send(embed=dm_embed)
        except:
            pass

        await inter.guild.kick(member, reason=reason)

        log_embed = disnake.Embed(
            title="👢 Пользователь кикнут",
            color=disnake.Color.orange(),
            timestamp=datetime.datetime.now(tz=MSK)
        )
        log_embed.add_field(name="Модератор", value=inter.author.mention)
        log_embed.add_field(name="Пользователь", value=member.mention)
        log_embed.add_field(name="Причина", value=reason)

        await self.send_log(inter.guild, "kick", log_embed)
        await inter.response.send_message(f"{member.mention} кикнут.", ephemeral=True)

    @commands.slash_command(description="Снять мут с пользователя.")
    async def unmute(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member,
        reason: str
    ):
        if not self.has_permission(inter.author):
            await inter.response.send_message("Нет доступа.", ephemeral=True)
            return

        await member.timeout(duration=None, reason=reason)

        dm_embed = disnake.Embed(
            title="🔈 Мут снят",
            description=f"**Модератор:** {inter.author.mention}\n**Причина:** {reason}",
            color=disnake.Color.green()
        )
        dm_embed.set_footer(text="Пожалуйста, соблюдайте правила.")
        try:
            await member.send(embed=dm_embed)
        except:
            pass

        log_embed = disnake.Embed(
            title="🔈 Мут снят",
            color=disnake.Color.green(),
            timestamp=datetime.datetime.now(tz=MSK)
        )
        log_embed.add_field(name="Модератор", value=inter.author.mention)
        log_embed.add_field(name="Пользователь", value=member.mention)
        log_embed.add_field(name="Причина", value=reason)

        await self.send_log(inter.guild, "unmute", log_embed)
        await inter.response.send_message(f"Мут с {member.mention} снят.", ephemeral=True)

    @commands.slash_command(description="Разбанить пользователя по ID.")
    async def unban(
        self,
        inter: disnake.AppCmdInter,
        user_id: str,
        reason: str
    ):
        if not self.has_permission(inter.author):
            await inter.response.send_message("Нет доступа.", ephemeral=True)
            return

        try:
            user_id_int = int(user_id)
        except ValueError:
            await inter.response.send_message("Неверный формат ID пользователя.", ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(user_id_int)
        except:
            await inter.response.send_message("Пользователь с таким ID не найден.", ephemeral=True)
            return

        await inter.guild.unban(user, reason=reason)

        self.cursor.execute("DELETE FROM temp_bans WHERE user_id = ?", (user_id_int,))
        self.conn.commit()

        dm_embed = disnake.Embed(
            title="✅ Вы разбанены",
            description=f"**Модератор:** {inter.author.mention}\n**Причина:** {reason}",
            color=disnake.Color.green()
        )
        dm_embed.set_footer(text="Пожалуйста, соблюдайте правила.")
        try:
            await user.send(embed=dm_embed)
        except:
            pass

        log_embed = disnake.Embed(
            title="✅ Пользователь разбанен",
            color=disnake.Color.green(),
            timestamp=datetime.datetime.now(tz=MSK)
        )
        log_embed.add_field(name="Модератор", value=inter.author.mention)
        log_embed.add_field(name="Пользователь", value=f"<@{user_id_int}> (`{user_id_int}`)")
        log_embed.add_field(name="Причина", value=reason)

        await self.send_log(inter.guild, "unban", log_embed)
        await inter.response.send_message(f"Пользователь <@{user_id_int}> разбанен.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_unbans(self):
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        self.cursor.execute("SELECT user_id, guild_id, unban_at, reason FROM temp_bans")
        rows = self.cursor.fetchall()
        for user_id, guild_id, unban_at, reason in rows:
            if unban_at <= now:
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    continue
                try:
                    user = await self.bot.fetch_user(user_id)
                    await guild.unban(user, reason="Автоматический разбан по истечению срока")
                except Exception as e:
                    print(f"Ошибка при автоматическом разбане {user_id} в гильдии {guild_id}: {e}")
                    continue

                log_embed = disnake.Embed(
                    title="✅ Пользователь автоматически разбанен",
                    color=disnake.Color.green(),
                    timestamp=datetime.datetime.now(tz=MSK)
                )
                log_embed.add_field(name="Пользователь", value=f"<@{user_id}> (`{user_id}`)")
                log_embed.add_field(name="Причина", value="Истёк срок временного бана")

                if guild and guild.get_channel(LOG_CHANNELS.get("unban")):
                    await self.send_log(guild, "unban", log_embed)

                self.cursor.execute("DELETE FROM temp_bans WHERE user_id = ?", (user_id,))
                self.conn.commit()

    @check_unbans.before_loop
    async def before_check_unbans(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(ModeratorsCog(bot))
