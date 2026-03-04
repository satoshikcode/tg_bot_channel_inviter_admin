import asyncio
import os
import random
import sys

from dotenv import load_dotenv
from pyrogram import Client, enums, errors, types

load_dotenv()

BOT_USERNAME: str = os.getenv("BOT_USERNAME", "").lstrip("@")
SESSION_NAME: str = os.getenv("SESSION_NAME", "account_1")

if not BOT_USERNAME:
    print("[ОШИБКА] Переменная BOT_USERNAME не задана в .env")
    sys.exit(1)

API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
SYSTEM_VERSION = "Windows 10"
APP_VERSION = "6.6.2 x64"
LANG_CODE = "en"
SYSTEM_LANG_CODE = "en-US"
LANG_PACK = "tdesktop"

DEVICE_MODELS = [
    "Desktop",
    "PC",
    "Workstation",
    "ASUS ROG",
    "Dell XPS",
    "Lenovo ThinkPad",
    "Custom PC",
    "HP Pavilion",
    "MSI Gaming",
    "Acer Predator",
]

DEVICE_MODEL = random.choice(DEVICE_MODELS)

ADMIN_PRIVILEGES = types.ChatPrivileges(
    can_manage_chat=True,
    can_change_info=True,
    can_post_messages=True,
    can_edit_messages=True,
    can_delete_messages=True,
    can_invite_users=True,
    can_restrict_members=True,
    can_pin_messages=True,
    can_promote_members=True,
    can_manage_video_chats=True,
)


def log(msg: str) -> None:
    print(f"  {msg}")


async def safe_sleep() -> None:
    delay = random.uniform(5, 7)
    log(f"Пауза {delay:.1f} сек...")
    await asyncio.sleep(delay)


async def process_chat(
    client: Client,
    chat: types.Chat,
    bot_user: types.User,
    stats: dict,
) -> None:
    chat_title = chat.title or str(chat.id)

    try:
        await client.add_chat_members(chat.id, bot_user.id)
        log(f"Бот добавлен в '{chat_title}'")
    except errors.UserAlreadyParticipant:
        log(f"Бот уже в '{chat_title}'")
    except errors.FloodWait as e:
        wait = e.value + random.randint(5, 10)
        log(f"FloodWait при добавлении в '{chat_title}' -- ждём {wait} сек")
        await asyncio.sleep(wait)
        try:
            await client.add_chat_members(chat.id, bot_user.id)
            log(f"Бот добавлен в '{chat_title}' (повтор)")
        except Exception as ex:
            log(f"Не удалось добавить бота в '{chat_title}' после повтора: {ex}")
            stats["errors"] += 1
            return
    except errors.UserIsBot:
        pass
    except Exception as ex:
        if "USER_BOT" not in str(ex):
            log(f"Бот не добавлен в '{chat_title}': {ex}")

    try:
        await client.promote_chat_member(
            chat.id,
            bot_user.id,
            privileges=ADMIN_PRIVILEGES,
        )
        log(f"Бот назначен админом в '{chat_title}'")
        stats["success"] += 1
    except errors.FloodWait as e:
        wait = e.value + random.randint(5, 10)
        log(f"FloodWait при промоуте в '{chat_title}' -- ждём {wait} сек")
        await asyncio.sleep(wait)
        try:
            await client.promote_chat_member(
                chat.id,
                bot_user.id,
                privileges=ADMIN_PRIVILEGES,
            )
            log(f"Бот назначен админом в '{chat_title}' (повтор)")
            stats["success"] += 1
        except Exception as ex:
            log(f"Не удалось назначить админом в '{chat_title}' после повтора: {ex}")
            stats["errors"] += 1
    except Exception as ex:
        log(f"Не удалось назначить админом в '{chat_title}': {ex}")
        stats["errors"] += 1


async def main() -> None:
    app = Client(
        name=SESSION_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        device_model=DEVICE_MODEL,
        system_version=SYSTEM_VERSION,
        app_version=APP_VERSION,
        lang_code=LANG_CODE,
        system_lang_code=SYSTEM_LANG_CODE,
        lang_pack=LANG_PACK,
    )

    async with app:
        me = await app.get_me()
        print(f"Авторизован как: {me.first_name} (ID {me.id})\n")

        try:
            bot_user = await app.get_users(BOT_USERNAME)
        except Exception as e:
            print(f"Не удалось найти бота @{BOT_USERNAME}: {e}")
            return

        if not bot_user.is_bot:
            print(f"@{BOT_USERNAME} не является ботом!")
            return

        print(f"Целевой бот: @{bot_user.username} (ID {bot_user.id})\n")

        eligible_chats: list[types.Chat] = []

        print("Сканирование диалогов...\n")
        async for dialog in app.get_dialogs():
            chat = dialog.chat

            if chat.type not in (enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP):
                continue

            try:
                member = await app.get_chat_member(chat.id, me.id)
            except Exception:
                continue

            if member.status not in (
                enums.ChatMemberStatus.ADMINISTRATOR,
                enums.ChatMemberStatus.OWNER,
            ):
                continue

            if member.status == enums.ChatMemberStatus.OWNER:
                eligible_chats.append(chat)
                log(f"[Создатель] '{chat.title}'")
                continue

            if member.privileges and member.privileges.can_promote_members:
                eligible_chats.append(chat)
                log(f"[Админ]     '{chat.title}'")

        print(f"\nНайдено подходящих чатов: {len(eligible_chats)}\n")

        if not eligible_chats:
            print("Нет чатов, куда можно добавить бота. Завершение.")
            return

        stats = {"success": 0, "errors": 0}

        for i, chat in enumerate(eligible_chats, 1):
            print(f"\n[{i}/{len(eligible_chats)}] Обработка '{chat.title}'...")
            await process_chat(app, chat, bot_user, stats)

            if i < len(eligible_chats):
                await safe_sleep()

        print(f"\nУспешно: {stats['success']}, Ошибок: {stats['errors']}, Всего: {len(eligible_chats)}")


if __name__ == "__main__":
    asyncio.run(main())
