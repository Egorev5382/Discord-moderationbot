import disnake
from disnake.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    MOD_ROLE_IDS = {
        1389672347249938593,
        1389672348264955954,
        1389672345328947352,
        1389672343235854541,
        1389672337074421953,
        1389672351037259796
    }

    ALLOWED_ROLE_IDS = {
        1389672224071614584,
        1389672225833091254,
        1389672227544502434,
        1389672230287446169,
        1389672232061505707,
        1389672246083326146,
        1389672248411164833,
        1389672268543819826,
    }

    def has_allowed_role(self, member: disnake.Member) -> bool:
        """Проверка есть ли у пользователя одна из разрешённых ролей"""
        return any(role.id in self.ALLOWED_ROLE_IDS for role in member.roles)

    @commands.slash_command(description="Снять модераторские роли с пользователя")
    async def unmod(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(name="пользователь", description="Кого размодерировать")
    ):
        if not self.has_allowed_role(inter.author):
            await inter.response.send_message("Нет доступа.", ephemeral=True)
            return

        removed_roles = []

        for role_id in self.MOD_ROLE_IDS:
            role = inter.guild.get_role(role_id)
            if role and role in member.roles:
                try:
                    await member.remove_roles(role, reason=f"Удалено через /unmod от {inter.author}")
                    removed_roles.append(role.name)
                except disnake.Forbidden:
                    await inter.response.send_message(
                        f"❌ Нет прав для снятия роли {role.mention}", ephemeral=True
                    )
                    return
                except Exception as e:
                    await inter.response.send_message(
                        f"⚠️ Ошибка при снятии роли: {e}", ephemeral=True
                    )
                    return

        if removed_roles:
            await inter.response.send_message(
                f"✅ У пользователя {member.mention} сняты роли: {', '.join(removed_roles)}", ephemeral=True
            )
        else:
            await inter.response.send_message(
                f"ℹ️ У пользователя {member.mention} нет указанных ролей.", ephemeral=True
            )

def setup(bot):
    bot.add_cog(Moderation(bot))
