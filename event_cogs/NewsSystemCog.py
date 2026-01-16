import disnake
from disnake.ext import commands
from disnake.ui import View, Button
from datetime import datetime

NEWS_EDITOR_ROLE_ID = 1389672358045941831

ALLOWED_CHANNEL_IDS = [1389673026672398546, 1389673030782816380, 1389673038999453907]

AUTHOR_ICON_URL = "https://media.discordapp.net/attachments/1396143206558597261/1396925548193648651/U1weM7Jr9GBcKRATzPf0pHipbtPtMepiEwYH_VNBt5RiI_R8jFjknsoIn0jHjfPXvxCpW9N0IHEOOqEHGQDUNnXU.jpg?ex=687fdbcc&is=687e8a4c&hm=2d56b47f3b58fdb0213233911ffb59da570f949615deeb9880d9b513ad69aa9d&=&format=webp&width=975&height=975"

class NewsView(View):
    def __init__(self, embed: disnake.Embed, author: disnake.User, target_channel_id: int):
        super().__init__(timeout=None)
        self.embed = embed
        self.author = author
        self.target_channel_id = target_channel_id

    @disnake.ui.button(label="Выложить", style=disnake.ButtonStyle.success)
    async def publish(self, button: Button, inter: disnake.MessageInteraction):
        if inter.user.id != self.author.id:
            await inter.response.send_message("Вы не можете публиковать чужую новость.", ephemeral=True)
            return

        channel = inter.bot.get_channel(self.target_channel_id)
        if not channel:
            await inter.response.send_message("Ошибка: канал не найден.", ephemeral=True)
            return

        await channel.send(content="@everyone", embed=self.embed)
        await inter.response.send_message("Новость опубликована.", ephemeral=True)

    @disnake.ui.button(label="Заново", style=disnake.ButtonStyle.danger)
    async def restart(self, button: Button, inter: disnake.MessageInteraction):
        if inter.user.id != self.author.id:
            await inter.response.send_message("Вы не можете сбрасывать чужую новость.", ephemeral=True)
            return
        await inter.response.send_message("Начинаем заново. Введите команду `/news` ещё раз.", ephemeral=True)


class NewsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="news", description="Создать embed новость")
    async def news(
        self,
        inter: disnake.ApplicationCommandInteraction,
        target_channel: disnake.TextChannel = commands.Param(name="канал", description="Куда опубликовать новость"),
    ):
        role = disnake.utils.get(inter.guild.roles, id=NEWS_EDITOR_ROLE_ID)
        if role not in inter.author.roles:
            await inter.response.send_message("Нет доступа.", ephemeral=True)
            return

        if target_channel.id not in ALLOWED_CHANNEL_IDS:
            await inter.response.send_message("Выбранный канал не разрешён для публикации новостей.", ephemeral=True)
            return

        await inter.response.send_modal(
            title="Создание новости",
            custom_id=f"news_modal:{target_channel.id}",
            components=[
                disnake.ui.TextInput(
                    label="Заголовок", custom_id="title",
                    style=disnake.TextInputStyle.short, max_length=256
                ),
                disnake.ui.TextInput(
                    label="Текст новости", custom_id="description",
                    style=disnake.TextInputStyle.paragraph, max_length=2048
                ),
                disnake.ui.TextInput(
                    label="Цвет (#RRGGBB)", custom_id="color",
                    style=disnake.TextInputStyle.short, required=False
                ),
                disnake.ui.TextInput(
                    label="Ссылка на изображение", custom_id="image",
                    style=disnake.TextInputStyle.short, required=False
                ),
            ]
        )

    @commands.Cog.listener()
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        if not inter.custom_id.startswith("news_modal:"):
            return

        try:
            target_channel_id = int(inter.custom_id.split(":")[1])
        except (IndexError, ValueError):
            await inter.response.send_message("Ошибка: не удалось определить канал.", ephemeral=True)
            return

        target_channel = inter.guild.get_channel(target_channel_id)
        if not target_channel or target_channel.id not in ALLOWED_CHANNEL_IDS:
            await inter.response.send_message("Канал недействителен или не разрешён.", ephemeral=True)
            return

        title = inter.text_values["title"]
        description = inter.text_values["description"]
        color_hex = inter.text_values.get("color", "#2F3136") or "#2F3136"
        image_url = inter.text_values.get("image", "")

        try:
            color = disnake.Color(int(color_hex.replace("#", ""), 16))
        except ValueError:
            color = disnake.Color.default()

        embed = disnake.Embed(title=title, description=description, color=color)
        embed.set_author(name="Gtech Mobail News System", icon_url=AUTHOR_ICON_URL)

        if image_url:
            embed.set_image(url=image_url)

        time = datetime.now().strftime("%d.%m.%Y %H:%M")
        embed.set_footer(text=f"Редактор новости: {inter.author} | {time}")

        view = NewsView(embed, inter.author, target_channel_id)
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)


def setup(bot):
    bot.add_cog(NewsCog(bot))
