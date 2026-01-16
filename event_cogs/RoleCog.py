import disnake
from disnake.ext import commands
from disnake import SelectOption, TextInputStyle
from datetime import datetime

ROLE_REQUEST_CHANNEL_ID = 1389673049623625830
MODERATION_CHANNEL_ID = 1389673053503361115
ROLE_REMOVE_CHANNEL_ID = 1389673062764515461
MODERATION_REMOVE_CHANNEL_ID = 1389673060197597404
ROLE_MESSAGE_ID_FILE = "role.txt"
REMOVE_MESSAGE_ID_FILE = "remove.txt"

ALLOWED_ROLE_IDS = [
    1389672499498713241, 1389672501470171257, 1389672502988509327, 1389672504058052628,
    1389672506385764463, 1389672507564626022, 1389672509129101483, 1389672510374674634,
    1389672511448547529, 1389672513675464785, 1389672516758409236, 1389672518721470494,
    1389672520965161001
]


class RoleActionModal(disnake.ui.Modal):
    def __init__(self, role: disnake.Role, is_removal: bool):
        self.is_removal = is_removal
        self.role = role
        action = "снятия" if is_removal else "запроса"
        title = f"Запрос {action} роли: {role.name}"

        components = [
            disnake.ui.TextInput(
                label=f"Причина {action} роли",
                style=TextInputStyle.paragraph,
                custom_id="reason_input",
                placeholder=f"Укажите, почему вы хотите {'снять' if is_removal else 'получить'} эту роль",
                required=True,
                max_length=500,
            )
        ]

        super().__init__(title=title, components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        reason = interaction.text_values["reason_input"]

        embed = disnake.Embed(
            title=f"Новая заявка на {'снятие' if self.is_removal else 'выдачу'} роли",
            color=disnake.Color.orange() if self.is_removal else disnake.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Пользователь", value=interaction.user.mention, inline=False)
        embed.add_field(name="Роль", value=self.role.mention, inline=False)
        embed.add_field(name="Причина", value=reason, inline=False)
        embed.set_footer(text=f"ID пользователя: {interaction.user.id}")

        view = RoleModerationView(interaction.user, self.role, reason, self.is_removal)

        mod_channel = interaction.guild.get_channel(
            MODERATION_REMOVE_CHANNEL_ID if self.is_removal else MODERATION_CHANNEL_ID
        )
        if mod_channel:
            await mod_channel.send(embed=embed, view=view)
            await interaction.response.send_message("Заявка отправлена модераторам.", ephemeral=True)
        else:
            await interaction.response.send_message("Не удалось найти канал для заявок.", ephemeral=True)


class RejectReasonModal(disnake.ui.Modal):
    def __init__(self, requester: disnake.Member, role: disnake.Role, message: disnake.Message,
                 view: disnake.ui.View, is_removal: bool):
        self.requester = requester
        self.role = role
        self.message = message
        self.view = view
        self.is_removal = is_removal
        title = f"Отказ заявки на {'снятие' if is_removal else 'выдачу'} роли {role.name}"

        components = [
            disnake.ui.TextInput(
                label="Причина отказа",
                style=TextInputStyle.paragraph,
                custom_id="reject_reason",
                placeholder="Укажите причину отказа для пользователя",
                required=True,
                max_length=500,
            )
        ]
        super().__init__(title=title, components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        reason = interaction.text_values["reject_reason"]

        embed = self.message.embeds[0]
        embed.color = disnake.Color.red()
        embed.add_field(name="Статус заявки", value=f"❌ Отклонено модератором {interaction.author.mention}", inline=False)
        embed.add_field(name="Причина отказа", value=reason, inline=False)

        for item in self.view.children:
            item.disabled = True

        await self.message.edit(embed=embed, view=self.view)

        try:
            reject_embed = disnake.Embed(
                title="Заявка отклонена",
                description=f"Ваша заявка на {'снятие' if self.is_removal else 'получение'} роли {self.role.mention} была отклонена.",
                color=disnake.Color.red()
            )
            reject_embed.add_field(name="Причина отказа", value=reason)
            await self.requester.send(embed=reject_embed)
        except:
            pass

        await interaction.response.send_message("Отказ отправлен пользователю.", ephemeral=True)


class RoleModerationView(disnake.ui.View):
    def __init__(self, requester: disnake.Member, role: disnake.Role, reason: str, is_removal: bool):
        super().__init__(timeout=None)
        self.requester = requester
        self.role = role
        self.reason = reason
        self.is_removal = is_removal

    @disnake.ui.button(label="Одобрить", style=disnake.ButtonStyle.green)
    async def approve(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if not interaction.author.guild_permissions.manage_roles:
            await interaction.response.send_message("У вас нет прав для этого действия.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = disnake.Color.green()
        embed.add_field(name="Статус заявки", value=f"✅ Одобрено модератором {interaction.author.mention}", inline=False)
        embed.add_field(name="Причина", value=self.reason, inline=False)

        for item in self.children:
            item.disabled = True

        action_done = False
        if self.is_removal and self.role in self.requester.roles:
            await self.requester.remove_roles(self.role, reason="Снятие роли одобрено модератором")
            action_done = True
        elif not self.is_removal and self.role not in self.requester.roles:
            await self.requester.add_roles(self.role, reason="Выдача роли одобрена модератором")
            action_done = True

        try:
            dm_embed = disnake.Embed(
                title="Ваша заявка одобрена",
                description=(f"Ваша заявка на {'снятие' if self.is_removal else 'получение'} роли {self.role.mention} одобрена. "
                             f"Роль {'снята' if self.is_removal else 'выдана'}."),
                color=disnake.Color.green()
            )
            await self.requester.send(embed=dm_embed)
        except:
            pass

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("Заявка обработана.", ephemeral=True)

    @disnake.ui.button(label="Отклонить", style=disnake.ButtonStyle.red)
    async def reject(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if not interaction.author.guild_permissions.manage_roles:
            await interaction.response.send_message("У вас нет прав для этого действия.", ephemeral=True)
            return

        modal = RejectReasonModal(
            requester=self.requester,
            role=self.role,
            message=interaction.message,
            view=self,
            is_removal=self.is_removal
        )
        await interaction.response.send_modal(modal)


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.role_message = None
        self.remove_message = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.init_role_panel(ROLE_REQUEST_CHANNEL_ID, ROLE_MESSAGE_ID_FILE, False)
        await self.init_role_panel(ROLE_REMOVE_CHANNEL_ID, REMOVE_MESSAGE_ID_FILE, True)

    async def init_role_panel(self, channel_id: int, file_path: str, is_removal: bool):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            print(f"Канал с ID {channel_id} не найден.")
            return

        try:
            with open(file_path, "r") as f:
                msg_id = int(f.read().strip())
                message = await channel.fetch_message(msg_id)
                if is_removal:
                    self.remove_message = message
                else:
                    self.role_message = message
        except:
            embed = self.create_embed(is_removal)
            view = self.create_view(is_removal)
            message = await channel.send(embed=embed, view=view)
            with open(file_path, "w") as f:
                f.write(str(message.id))
            if is_removal:
                self.remove_message = message
            else:
                self.role_message = message

    def create_embed(self, is_removal: bool) -> disnake.Embed:
        action = "снятие" if is_removal else "запрос"
        embed = disnake.Embed(
            title=f"📢 {action.capitalize()} роли на сервере",
            description=(f"Чтобы {'снять' if is_removal else 'запросить'} роль, нажмите кнопку ниже и выберите нужную роль.\n"
                         f"После выбора укажите причину.\n"
                         f"Заявка будет отправлена модераторам для проверки."),
            color=disnake.Color.red() if is_removal else disnake.Color.blurple()
        )
        embed.set_footer(text="Роль будет обработана после одобрения модераторами.")
        return embed

    def create_view(self, is_removal: bool) -> disnake.ui.View:
        view = disnake.ui.View(timeout=None)
        button = disnake.ui.Button(
            label="Снять роль" if is_removal else "Запросить роль",
            style=disnake.ButtonStyle.danger if is_removal else disnake.ButtonStyle.primary,
            custom_id="remove_role" if is_removal else "request_role"
        )
        view.add_item(button)
        return view

    @commands.Cog.listener()
    async def on_interaction(self, interaction: disnake.MessageInteraction):
        custom_id = interaction.data.get("custom_id")
        if custom_id not in ("request_role", "remove_role"):
            return

        is_removal = custom_id == "remove_role"
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Эта команда работает только на сервере.", ephemeral=True)
            return

        roles = [
            role for role_id in ALLOWED_ROLE_IDS
            if (role := guild.get_role(role_id)) is not None
        ]

        if not roles:
            await interaction.response.send_message("Доступные роли не найдены.", ephemeral=True)
            return

        options = [
            SelectOption(label=role.name, value=str(role.id), description=f"{'Снять' if is_removal else 'Запросить'} роль {role.name}")
            for role in roles
        ]

        class RoleSelect(disnake.ui.Select):
            def __init__(self):
                super().__init__(
                    placeholder="Выберите роль",
                    min_values=1,
                    max_values=1,
                    options=options,
                    custom_id=f"role_select_{'remove' if is_removal else 'request'}"
                )

            async def callback(self, select_interaction: disnake.MessageInteraction):
                role_id = int(self.values[0])
                role = guild.get_role(role_id)
                if role is None:
                    await select_interaction.response.send_message("Роль не найдена.", ephemeral=True)
                    return
                modal = RoleActionModal(role, is_removal)
                await select_interaction.response.send_modal(modal)

        view = disnake.ui.View(timeout=None)
        view.add_item(RoleSelect())

        await interaction.response.send_message(
            content="Выберите роль из списка:",
            view=view,
            ephemeral=True
        )


def setup(bot):
    bot.add_cog(Roles(bot))
