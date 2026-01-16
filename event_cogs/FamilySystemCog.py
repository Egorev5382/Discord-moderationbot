import disnake
from disnake.ext import commands
from disnake import Option, OptionType, ButtonStyle
from disnake.ui import View, Button
import sqlite3
import datetime

FAMILY_TEXT_CATEGORY_ID = 1389672753904353352
FAMILY_VOICE_CATEGORY_ID = 1389672758681534576

class FamilyInviteView(View):
    def __init__(self, bot, family_role, inviter, invitee):
        super().__init__(timeout=60)
        self.bot = bot
        self.family_role = family_role
        self.inviter = inviter
        self.invitee = invitee
        self.responded = False

    @disnake.ui.button(label="Принять", style=ButtonStyle.green)
    async def accept(self, button: Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.invitee.id:
            await inter.response.send_message("Это приглашение не для вас.", ephemeral=True)
            return
        if self.responded:
            await inter.response.send_message("Вы уже ответили на приглашение.", ephemeral=True)
            return
        self.responded = True
        await self.invitee.add_roles(self.family_role)
        await inter.response.edit_message(content=f"Вы приняли приглашение в семью **{self.family_role.name}**!", view=None)
        try:
            await self.inviter.send(f"{self.invitee.mention} принял приглашение в семью **{self.family_role.name}**.")
        except:
            pass
        self.stop()

    @disnake.ui.button(label="Отклонить", style=ButtonStyle.red)
    async def decline(self, button: Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.invitee.id:
            await inter.response.send_message("Это приглашение не для вас.", ephemeral=True)
            return
        if self.responded:
            await inter.response.send_message("Вы уже ответили на приглашение.", ephemeral=True)
            return
        self.responded = True
        await inter.response.edit_message(content=f"Вы отклонили приглашение в семью **{self.family_role.name}**.", view=None)
        try:
            await self.inviter.send(f"{self.invitee.mention} отклонил приглашение в семью **{self.family_role.name}**.")
        except:
            pass
        self.stop()

class FamilySystemCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("db.sqlite3")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS families (
                family_name TEXT,
                role_id INTEGER,
                leader_id INTEGER,
                text_channel_id INTEGER,
                voice_channel_id INTEGER,
                created_at TEXT
            )
        """)
        self.db.commit()

        self.ALLOWED_ROLE_IDS = [
            1389672345328947352,
            1389672343235854541,
            1389672268543819826,
            1389672248411164833,
            1389672246083326146,
            1389672232061505707,
            1389672230287446169,
            1389672227544502434,
            1389672225833091254,
            1389672224071614584
        ]

    @commands.slash_command(name="familycreate", description="Создать семью")
    async def familycreate(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name=Option(
            name="name",
            description="Название семьи",
            required=True
        ),
        color=Option(
            name="color",
            description="Цвет в HEX формате (например, #ff5733)",
            required=True
        )
    ):
        await inter.response.defer(ephemeral=True)

        if not any(role.id in self.ALLOWED_ROLE_IDS for role in inter.author.roles):
            await inter.send("Нет доступа.", ephemeral=True)
            return

        if not name or not color:
            await inter.send("Заполните все поля.", ephemeral=True)
            return

        self.cursor.execute("SELECT * FROM families WHERE leader_id = ?", (inter.author.id,))
        existing_family = self.cursor.fetchone()
        if existing_family:
            await inter.send("У вас уже есть семья, для удаления обратитесь к администрации.", ephemeral=True)
            return

        if not color.startswith("#") or len(color) != 7:
            await inter.send("Цвет должен быть в формате HEX. Пример: `#ff5733`", ephemeral=True)
            return

        try:
            rgb_color = disnake.Color(int(color[1:], 16))
        except ValueError:
            await inter.send("Ошибка: некорректный HEX-цвет.", ephemeral=True)
            return

        guild = inter.guild

        role = await guild.create_role(
            name=name,
            color=rgb_color,
            mentionable=True,
            reason="Создание семьи"
        )

        await inter.author.add_roles(role)

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            role: disnake.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        text_channel = await guild.create_text_channel(
            name=f"{name.lower()}-чат",
            category=guild.get_channel(FAMILY_TEXT_CATEGORY_ID),
            overwrites=overwrites
        )

        voice_channel = await guild.create_voice_channel(
            name=f"{name.lower()}-войс",
            category=guild.get_channel(FAMILY_VOICE_CATEGORY_ID),
            overwrites=overwrites
        )

        self.cursor.execute("""
            INSERT INTO families (family_name, role_id, leader_id, text_channel_id, voice_channel_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name, role.id, inter.author.id, text_channel.id, voice_channel.id,
            datetime.datetime.utcnow().isoformat()
        ))
        self.db.commit()

        await inter.send(f"Семья **{name}** успешно создана!", ephemeral=True)

    @commands.slash_command(name="familyinvite", description="Пригласить пользователя в семью")
    async def familyinvite(
        self,
        inter: disnake.ApplicationCommandInteraction,
        family_role: disnake.Role = Option(
            name="family_role",
            description="Роль семьи",
            type=OptionType.role,
            required=True
        ),
        member: disnake.Member = Option(
            name="member",
            description="Кого пригласить",
            type=OptionType.user,
            required=True
        )
    ):
        await inter.response.defer(ephemeral=True)

        if not any(role.id in self.ALLOWED_ROLE_IDS for role in inter.author.roles):
            await inter.send("Нет доступа.", ephemeral=True)
            return

        if not family_role or not member:
            await inter.send("Заполните все поля.", ephemeral=True)
            return

        self.cursor.execute("SELECT leader_id FROM families WHERE role_id = ?", (family_role.id,))
        result = self.cursor.fetchone()

        if not result:
            await inter.send("Семья с этой ролью не найдена в базе данных.", ephemeral=True)
            return

        leader_id = result[0]
        if inter.author.id != leader_id:
            await inter.send("Вы не глава этой семьи и не можете приглашать участников.", ephemeral=True)
            return

        if member.bot:
            await inter.send("Нельзя приглашать ботов.", ephemeral=True)
            return

        if member == inter.author:
            await inter.send("Вы не можете пригласить себя.", ephemeral=True)
            return

        if family_role in member.roles:
            await inter.send(f"{member.mention} уже состоит в семье **{family_role.name}**.", ephemeral=True)
            return

        view = FamilyInviteView(self.bot, family_role, inter.author, member)
        try:
            await member.send(
                f"Вас приглашают в семью **{family_role.name}** на сервере **{inter.guild.name}** от {inter.author.mention}. Примите или отклоните приглашение.",
                view=view
            )
            await inter.send(f"Приглашение отправлено {member.mention}.", ephemeral=True)
        except disnake.Forbidden:
            await inter.send(f"Не удалось отправить приглашение пользователю {member.mention}. Возможно, у него закрыты личные сообщения.", ephemeral=True)

def setup(bot):
    bot.add_cog(FamilySystemCog(bot))
