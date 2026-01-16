import disnake
from disnake import MessageInteraction
from disnake.ext import commands
from disnake.ui import View, Select, Button
import os
import asyncio

SUPPORT_CHANNEL_ID = 1389673043160469574
TICKET_CATEGORY_ID = 1389672666654441654
MOD_CHANNEL_ID = 1389673045416743103
OLD_TICKETS_CHANNEL_ID = 1396927008025612440
MOD_ROLE_ID = 1389672347249938593  

TICKET_MESSAGE_FILE = "ticket.txt"
MOD_MESSAGES_FILE = "tickets.txt"

class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        support_ch = self.bot.get_channel(SUPPORT_CHANNEL_ID)

        if not await self._restore_ticket_menu(support_ch):
            await self._send_ticket_menu(support_ch)

        await self._restore_mod_views()

    async def _restore_ticket_menu(self, support_ch) -> bool:
        if not os.path.exists(TICKET_MESSAGE_FILE):
            return False
        try:
            with open(TICKET_MESSAGE_FILE) as f:
                msg_id = int(f.read().strip())
            msg = await support_ch.fetch_message(msg_id)
            await msg.edit(view=self._ticket_menu_view())
            return True
        except Exception:
            return False

    async def _send_ticket_menu(self, support_ch):
        embed = disnake.Embed(
            title="📩  Техническая поддержка",
            description=("❓ В данном канале вы можете получить помощь как по Discord, так и по игровому серверу."

                         " Чтобы задать вопрос, выберите нужный вам пункт из предоставленного меню ниже."),
            color=disnake.Color.blurple())
        embed.set_image(
            url="https://media.discordapp.net/attachments/1396143206558597261/1396925101424775299/rich-tech-support.gif?ex=687fdb61&is=687e89e1&hm=a3ae409f24a61feabe53af1318b4e15acf2763b3abc56ababb5e5407d8ca9aaf&=&width=576&height=324")

        msg = await support_ch.send(embed=embed, view=self._ticket_menu_view())
        with open(TICKET_MESSAGE_FILE, "w") as f:
            f.write(str(msg.id))

    async def _restore_mod_views(self):
        if not os.path.exists(MOD_MESSAGES_FILE):
            return
        mod_ch = self.bot.get_channel(MOD_CHANNEL_ID)
        with open(MOD_MESSAGES_FILE) as f:
            for line in f:
                try:
                    msg_id = int(line.strip())
                    mod_msg = await mod_ch.fetch_message(msg_id)
                    ch_id, user_id = self._ids_from_footer(mod_msg)
                    if ch_id and user_id:
                        view = self._mod_buttons_view(ch_id, user_id)
                        await mod_msg.edit(view=view)
                except Exception:
                    continue

    def _ticket_menu_view(self):
        options = [
            disnake.SelectOption(label="Модерация Discord",
                                 description="Вопрос по Discord",
                                 value="discord"),
            disnake.SelectOption(label="Модерация игрового сервера",
                                 description="Вопрос по игровому серверу",
                                 value="game"),
            disnake.SelectOption(label="Обращение к Администрации магазина",
                                 description="Вопрос по магазину",
                                 value="store"),
        ]
        select = Select(placeholder="Выберите категорию вашего вопроса",
                        options=options,
                        custom_id="ticket_select")

        async def cb(inter: disnake.MessageInteraction):
            await self._create_ticket(inter, select.values[0])

        select.callback = cb

        view = View(timeout=None)
        view.add_item(select)
        return view

    async def _create_ticket(self, inter: disnake.MessageInteraction, category: str):
        guild = inter.guild

        if disnake.utils.get(guild.text_channels, name=f"ticket-{inter.user.id}"):
            await inter.response.send_message("У вас уже есть открытый тикет!", ephemeral=True)
            return

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(view_channel=False),
            inter.user: disnake.PermissionOverwrite(view_channel=True,
                                                    send_messages=True,
                                                    attach_files=True,
                                                    read_message_history=True)
        }
        cat = disnake.utils.get(guild.categories, id=TICKET_CATEGORY_ID)
        if cat is None:
            await inter.response.send_message("Категория для тикетов не найдена!", ephemeral=True)
            return

        channel = await guild.create_text_channel(
            name=f"ticket-{inter.user.id}",
            overwrites=overwrites,
            category=cat,
            topic=f"Тикет ▶ {inter.user} │ Категория: {category}")

        await channel.send(f"{inter.user.mention}, ваш тикет создан! Ожидайте ответа модератора.")

        embed = disnake.Embed(
            title="🆕  Новый тикет",
            description=(f"**Пользователь:** {inter.user.mention}\n"
                         f"**Категория:** {category}"),
            color=disnake.Color.green())
        embed.add_field(name="Взял тикет", value="—", inline=False)
        embed.add_field(name="Присоединились", value="—", inline=False)

        mod_ch = self.bot.get_channel(MOD_CHANNEL_ID)
        role_mention = f"<@&{MOD_ROLE_ID}>"
        mod_msg = await mod_ch.send(
            content=role_mention,
            embed=embed,
            view=self._mod_buttons_view(channel.id, inter.user.id)
        )

        with open(MOD_MESSAGES_FILE, "a", encoding="utf-8") as f:
            f.write(f"{mod_msg.id}\n")

        await inter.response.send_message(f"✅ Тикет создан: {channel.mention}", ephemeral=True)

    def _mod_buttons_view(self, channel_id: int, user_id: int):
        view = View(timeout=None)

        take_btn = Button(label="Взять тикет", style=disnake.ButtonStyle.secondary,
                          custom_id=f"take_{channel_id}_{user_id}")
        join_btn = Button(label="Присоединиться", style=disnake.ButtonStyle.secondary,
                          custom_id=f"join_{channel_id}_{user_id}")
        close_btn = Button(label="Закрыть тикет", style=disnake.ButtonStyle.secondary,
                           custom_id=f"close_{channel_id}_{user_id}")

        async def take_cb(inter: disnake.MessageInteraction):
            if not self._can_manage(inter):
                return await inter.response.send_message("Нет доступа.", ephemeral=True)

            ticket_ch = self.bot.get_channel(channel_id)
            mod_msg = inter.message
            embed = mod_msg.embeds[0]

            if embed.fields[0].value == "—":
                embed.set_field_at(0, name="Взял тикет", value=inter.user.mention, inline=False)
                await mod_msg.edit(embed=embed)
            await ticket_ch.set_permissions(
                inter.user, view_channel=True, send_messages=True,
                attach_files=True, read_message_history=True)

            take_btn.disabled = True
            await mod_msg.edit(view=view)
            await ticket_ch.send(f"<@{user_id}>, ваш тикет взял модератор {inter.user.mention}.")
            await inter.response.send_message("Вы взяли тикет.", ephemeral=True)

        async def join_cb(inter: disnake.MessageInteraction):
            if not self._can_manage(inter):
                return await inter.response.send_message("Нет доступа.", ephemeral=True)

            ticket_ch = self.bot.get_channel(channel_id)
            mod_msg = inter.message
            embed = mod_msg.embeds[0]

            joined = [] if embed.fields[1].value == "—" else embed.fields[1].value.split(", ")
            if inter.user.mention not in joined:
                joined.append(inter.user.mention)
                embed.set_field_at(1, name="Присоединились",
                                   value=", ".join(joined), inline=False)
                await mod_msg.edit(embed=embed)

            await ticket_ch.set_permissions(
                inter.user, view_channel=True, send_messages=True,
                attach_files=True, read_message_history=True)

            await inter.response.send_message("Вы присоединились к тикету.", ephemeral=True)

        async def close_cb(inter: MessageInteraction):
            if not self._can_manage(inter):
                return await inter.response.send_message("Нет доступа.", ephemeral=True)

            await inter.response.defer(ephemeral=True)  

            ticket_ch = self.bot.get_channel(channel_id)
            if ticket_ch is None:
                return await inter.followup.send("Тикет уже закрыт.", ephemeral=True)


            mod_msg = inter.message
            embed = mod_msg.embeds[0]
            taken_by = embed.fields[0].value
            joined_by = embed.fields[1].value
            closed_by = inter.user.mention
            author = self.bot.get_user(user_id)

            try:
                dm_embed = disnake.Embed(
                    title="🎫 Ваш тикет закрыт",
                    description=(f"**Взял:** {taken_by}\n"
                                 f"**Закрыл:** {closed_by}\n"
                                 f"**Другие модераторы:** {joined_by}"),

                    color=disnake.Color.red())
                await author.send(embed=dm_embed)
            except Exception:
                pass  

            transcript = await self._build_transcript(ticket_ch)

            old_ch = self.bot.get_channel(OLD_TICKETS_CHANNEL_ID)
            meta_embed = disnake.Embed(
                title="📁 Закрытый тикет",
                description=(f"**Пользователь:** {author.mention}\n"
                             f"**Категория:** "
                             f"{embed.description.split('Категория:** ')[1]}\n\n"
                             f"**Взял:** {taken_by}\n"
                             f"**Присоединились:** {joined_by}\n"
                             f"**Закрыл:** {closed_by}"),
                color=disnake.Color.dark_gray())
            await old_ch.send(embed=meta_embed)

            if transcript:
                log_embed = disnake.Embed(
                    title="💬 Переписка",
                    description=transcript,
                    color=disnake.Color.greyple())
                await old_ch.send(embed=log_embed)

            take_btn.disabled = True
            join_btn.disabled = True
            close_btn.disabled = True
            await mod_msg.edit(view=view)

            await ticket_ch.delete(reason=f"Closed by {inter.user}")

            await inter.followup.send("Тикет закрыт и архивирован.", ephemeral=True)  

        take_btn.callback = take_cb
        join_btn.callback = join_cb
        close_btn.callback = close_cb

        view.add_item(take_btn)
        view.add_item(join_btn)
        view.add_item(close_btn)
        return view

    @staticmethod
    def _can_manage(inter: disnake.MessageInteraction) -> bool:
        mod_role = disnake.utils.get(inter.guild.roles, id=MOD_ROLE_ID)
        return mod_role in inter.user.roles

    @staticmethod
    def _ids_from_footer(msg: disnake.Message):
        try:
            text = msg.embeds[0].footer.text
            parts = dict(p.split(":", 1) for p in text.split("|"))
            return int(parts["channel_id"]), int(parts["user_id"])
        except Exception:
            return None, None

    async def _build_transcript(self, channel: disnake.TextChannel) -> str:
        lines = []
        async for m in channel.history(limit=None, oldest_first=True):
            if m.content:
                lines.append(f"{m.author.mention}: {m.content}")
        if not lines:
            return ""

        text = "\n".join(lines)
        return text[:4090] + "…" if len(text) > 4096 else text


def setup(bot: commands.Bot):
    bot.add_cog(TicketSystem(bot))
