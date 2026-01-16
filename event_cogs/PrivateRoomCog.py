import disnake
from disnake.ext import commands
import json
import os

class VoiceManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.private_channels = {}
        self.manage_message_id = None
        self.category_id = 1389672709436346519
        self.create_private_channel_id = 1389673687057174648  
        self.streaming_users = set()  

        self.load_message_id()

    def load_message_id(self):
        if os.path.exists("manage_message_id.json"):
            with open("manage_message_id.json", "r") as f:
                data = json.load(f)
                self.manage_message_id = data.get("message_id")

    def save_message_id(self):
        with open("manage_message_id.json", "w") as f:
            json.dump({"message_id": self.manage_message_id}, f)

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(1389672051907756124)
        manage_channel = guild.get_channel(1389673100706320444)

        if self.manage_message_id:
            try:
                message = await manage_channel.fetch_message(self.manage_message_id)
                await message.edit(view=SettingsView(self))
            except disnake.NotFound:
                self.manage_message_id = None

        if not self.manage_message_id:
            embed = disnake.Embed(
                title="Панель управления приватными комнатами",
                description="Настройте свои приватные комнаты ниже.",
                color=disnake.Color.blurple()
            )
            embed.add_field(name=":busts_in_silhouette: Лимит участников", value="Измените лимит пользователей.", inline=False)
            embed.add_field(name=":pencil: Изменить название", value="Переименуйте вашу комнату.", inline=False)
            embed.add_field(name=":boot: Кикнуть участника", value="Удалите пользователя из вашей комнаты.", inline=False)
            embed.add_field(name=":no_entry_sign: Запретить доступ", value="Запретите доступ выбранным пользователям.", inline=False)
            embed.add_field(name=":white_check_mark: Разрешить доступ", value="Разрешите доступ ранее запрещенным пользователям.", inline=False)

            message = await manage_channel.send(embed=embed, view=SettingsView(self))
            self.manage_message_id = message.id
            self.save_message_id()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is not None and after.channel is None:
            private_channel = self.private_channels.get(member.id)
            if private_channel:
                if member.id not in self.streaming_users:
                    await self.delete_private_channel(private_channel, member)

        if after.channel is not None and after.channel.id == self.create_private_channel_id:
            await self.create_private_channel(member)

        private_channel = self.private_channels.get(member.id)
        if before.channel is not None and after.channel is not None and private_channel:
            if before.channel.id == private_channel.id:
                if len(private_channel.members) == 0 and member.id not in self.streaming_users:
                    await self.delete_private_channel(private_channel, member)

    async def create_private_channel(self, user):
        guild = user.guild

        old_private_channel = self.private_channels.get(user.id)
        if old_private_channel:
            await self.delete_private_channel(old_private_channel, user)

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(view_channel=True, connect=True, speak=True, stream=True,
                                                            use_voice_activation=True),
            user: disnake.PermissionOverwrite(view_channel=True, connect=True, speak=True, stream=True,
                                              use_voice_activation=True)
        }

        category = guild.get_channel(self.category_id)
        if category is None or category.type != disnake.ChannelType.category:
            return None

        try:
            private_channel = await guild.create_voice_channel(
                name=f"{user.display_name} комната",
                category=category,
                user_limit=2,
                overwrites=overwrites
            )
            self.private_channels[user.id] = private_channel

            await user.move_to(private_channel)

            return private_channel
        except disnake.HTTPException as e:
            return None

        try:
            private_channel = await guild.create_voice_channel(
                name=f"{user.display_name} комната",
                category=category,
                user_limit=2,
                overwrites=overwrites
            )
            self.private_channels[user.id] = private_channel

            await user.move_to(private_channel)
            return private_channel
        except disnake.HTTPException as e:
            return None

    async def delete_private_channel(self, private_channel, member):
        await private_channel.delete()
        del self.private_channels[member.id]

class SettingsView(disnake.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    def get_private_channel(self, user):
        return self.cog.private_channels.get(user.id)

    @disnake.ui.button(style=disnake.ButtonStyle.secondary, emoji="👥")
    async def change_limit(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        private_channel = self.get_private_channel(interaction.user)
        if private_channel is None:
            await interaction.response.send_message("У вас нет активного приватного канала.", ephemeral=True)
            return

        modal = ChangeLimitModal(private_channel)
        await interaction.response.send_modal(modal)

    @disnake.ui.button(style=disnake.ButtonStyle.secondary, emoji="✏️")
    async def change_name(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        private_channel = self.get_private_channel(interaction.user)
        if private_channel is None:
            await interaction.response.send_message("У вас нет активного приватного канала.", ephemeral=True)
            return

        modal = ChangeNameModal(private_channel)
        await interaction.response.send_modal(modal)

    @disnake.ui.button(style=disnake.ButtonStyle.secondary, emoji="👢")
    async def kick_member(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        private_channel = self.get_private_channel(interaction.user)
        if private_channel is None:
            await interaction.response.send_message("У вас нет активного приватного канала.", ephemeral=True)
            return

        modal = IDInputModal(private_channel, "kick", example="Нажмите ПКМ по человеку -> скопировать ID")
        await interaction.response.send_modal(modal)

    @disnake.ui.button(style=disnake.ButtonStyle.secondary, emoji="🚫")
    async def ban_member(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        private_channel = self.get_private_channel(interaction.user)
        if private_channel is None:
            await interaction.response.send_message("У вас нет активного приватного канала.", ephemeral=True)
            return

        modal = IDInputModal(private_channel, "ban", example="Нажмите ПКМ по человеку -> скопировать ID")
        await interaction.response.send_modal(modal)

    @disnake.ui.button(style=disnake.ButtonStyle.secondary, emoji="✅")
    async def allow_member(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        private_channel = self.get_private_channel(interaction.user)
        if private_channel is None:
            await interaction.response.send_message("У вас нет активного приватного канала.", ephemeral=True)
            return

        modal = IDInputModal(private_channel, "allow", example="Нажмите ПКМ по человеку -> скопировать ID")
        await interaction.response.send_modal(modal)

class IDInputModal(disnake.ui.Modal):
    def __init__(self, private_channel, action, example=""):
        self.private_channel = private_channel
        self.action = action
        components = [
            disnake.ui.TextInput(
                label="Введите ID пользователя",
                placeholder=example,
                custom_id="user_id_input",
                style=disnake.TextInputStyle.short,
                max_length=20
            )
        ]
        super().__init__(title="Введите ID для выполнения действия", custom_id=f"{action}_modal", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        user_id = interaction.text_values["user_id_input"]
        guild = interaction.guild
        user = guild.get_member(int(user_id))

        if user is None:
            await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
            return

        if self.action == "kick":
            await user.move_to(None)
            await interaction.response.send_message(f"Пользователь {user.display_name} кикнут.", ephemeral=True)
        elif self.action == "ban":
            await self.private_channel.set_permissions(user, connect=False, view_channel=True)

            if user.voice and user.voice.channel == self.private_channel:
                await user.move_to(None)

            await interaction.response.send_message(
                f"Доступ для пользователя {user.display_name} запрещен.",
                ephemeral=True
            )

        elif self.action == "allow":
            await self.private_channel.set_permissions(user, view_channel=True)
            await interaction.response.send_message(f"Доступ для пользователя {user.display_name} разрешен.", ephemeral=True)

class ChangeLimitModal(disnake.ui.Modal):
    def __init__(self, private_channel):
        self.private_channel = private_channel
        components = [
            disnake.ui.TextInput(
                label="Введите новый лимит участников",
                placeholder="От 1 до 99",
                custom_id="new_limit_input",
                style=disnake.TextInputStyle.short,
                max_length=2
            )
        ]
        super().__init__(title="Изменение лимита участников", custom_id="change_limit_modal", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        new_limit = interaction.text_values["new_limit_input"]
        if not new_limit.isdigit() or not (1 <= int(new_limit) <= 99):
            await interaction.response.send_message("Лимит должен быть числом от 1 до 99.", ephemeral=True)
            return

        await self.private_channel.edit(user_limit=int(new_limit))
        await interaction.response.send_message(f"Лимит участников канала изменен на {new_limit}.", ephemeral=True)

class ChangeNameModal(disnake.ui.Modal):
    def __init__(self, private_channel):
        self.private_channel = private_channel
        components = [
            disnake.ui.TextInput(
                label="Введите новое имя канала",
                placeholder="Имя канала",
                custom_id="new_name_input",
                style=disnake.TextInputStyle.short,
                max_length=100
            )
        ]
        super().__init__(title="Изменение названия канала", custom_id="change_name_modal", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        new_name = interaction.text_values["new_name_input"]
        await self.private_channel.edit(name=new_name)
        await interaction.response.send_message(f"Имя канала изменено на {new_name}.", ephemeral=True)

def setup(bot):
    bot.add_cog(VoiceManager(bot))
