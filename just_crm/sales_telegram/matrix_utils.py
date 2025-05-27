import asyncio
import logging
import aiohttp

from nio import (
    AsyncClient,
    MatrixRoom,
    RoomMessageText,
    RoomMessageMedia,
    JoinedMembersError,  # уже був підключений
)
from django.conf import settings

logger = logging.getLogger(__name__)


class MatrixTelegramClient:
    def __init__(self):
        self.client = AsyncClient(settings.MATRIX_SERVER)
        self.client.access_token = None
        self.room_alias_cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Логін адміністратора (без змін)
    # ------------------------------------------------------------------
    async def login(self):
        logger.debug("Logging in as %s", settings.MATRIX_ADMIN_USERNAME)
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    f"{settings.MATRIX_SERVER}/_matrix/client/r0/login",
                    json={
                        "type": "m.login.password",
                        "identifier": {
                            "type": "m.id.user",
                            "user": settings.MATRIX_ADMIN_USERNAME,
                        },
                        "password": settings.MATRIX_ADMIN_PASSWORD,
                    },
                )
                data = await resp.json()
                if resp.status == 200 and "access_token" in data:
                    self.client.access_token = data["access_token"]
                    self.client.user_id = settings.MATRIX_ADMIN_USERNAME
                    logger.info("Matrix login OK")
                elif resp.status == 429:
                    retry = data.get("retry_after_ms", 5_000) / 1_000
                    logger.warning("Rate-limited, sleep %.1fs", retry)
                    await asyncio.sleep(retry)
                    return await self.login()
                else:
                    raise RuntimeError(f"Login failed: {data}")
        except Exception as exc:
            logger.exception("Matrix login error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # room_id → telegram_chat_id (без змін)
    # ------------------------------------------------------------------
    async def get_room_alias(self, room_id: str) -> str | None:
        if room_id in self.room_alias_cache:
            return self.room_alias_cache[room_id]

        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"{settings.MATRIX_SERVER}/_matrix/client/v3/rooms/{room_id}/aliases",
                headers={"Authorization": f"Bearer {self.client.access_token}"},
            )
            text = await resp.text()
            logger.debug("Alias API %s → %s", room_id, text)

            if resp.status == 200:
                for alias in (await resp.json()).get("aliases", []):
                    if alias.startswith("#telegram_"):
                        chat_id = alias.split("_", 1)[1].split(":", 1)[0]
                        self.room_alias_cache[room_id] = chat_id
                        logger.info("Cached chat_id %s for %s", chat_id, room_id)
                        return chat_id
                return None

            if resp.status == 429:
                retry = int(resp.headers.get("Retry-After", 10))
                logger.warning("Alias rate-limit, retry in %ss", retry)
                await asyncio.sleep(retry)
                return await self.get_room_alias(room_id)

            logger.error("Alias fetch failed %s: %s", resp.status, text)
            return None

    # ------------------------------------------------------------------
    # Головний слухач Matrix → callback()
    # ------------------------------------------------------------------
    async def start_listener(self, callback):
        async def on_message(room: MatrixRoom, event):
            logger.debug("Room %s event %s", room.room_id, event)

            matrix_event_id = event.event_id
            sender = event.sender

            # ① alias
            telegram_chat_id = await self.get_room_alias(room.room_id)

            # ② fallback із sender @telegram_<id>
            if not telegram_chat_id and sender.startswith("@telegram_"):
                try:
                    telegram_chat_id = sender.split(":", 1)[0].split("_", 1)[1]
                    self.room_alias_cache[room.room_id] = telegram_chat_id
                except Exception:
                    logger.error("Cannot parse chat_id for room %s", room.room_id)

            # ③ fallback із members, якщо ми (admin) ініціювали чат
            if not telegram_chat_id and sender == settings.MATRIX_ADMIN_USERNAME:
                members = await self.client.joined_members(room.room_id)
                if not isinstance(members, JoinedMembersError):
                    member_ids = (
                        members.members.keys()
                        if isinstance(members.members, dict)
                        else (m.user_id for m in members.members)
                    )
                    for uid in member_ids:
                        if uid.startswith("@telegram_"):
                            telegram_chat_id = uid.split(":", 1)[0].split("_", 1)[1]
                            self.room_alias_cache[room.room_id] = telegram_chat_id
                            break

            if not telegram_chat_id:
                logger.error("Unknown chat for room %s", room.room_id)
                return

            # ----------------------------------------------------------
            # RoomMessageText
            # ----------------------------------------------------------
            if isinstance(event, RoomMessageText):
                # --- CHANGE: витягаємо оригінальний message_id із мосту
                tgm_id = (
                    event.source["content"]
                    .get("fi.mau.telegram.source", {})
                    .get("id")
                )
                await callback(
                    telegram_chat_id,
                    matrix_event_id,
                    sender,
                    {"text": event.body, "files": [], "tgm_id": tgm_id},  # --- CHANGE
                )

            # ----------------------------------------------------------
            # RoomMessageMedia
            # ----------------------------------------------------------
            elif isinstance(event, RoomMessageMedia):
                msgtype = event.source["content"].get("msgtype", "m.file")
                file_type = {
                    "m.image": "image",
                    "m.file": "document",
                    "m.audio": "voice",
                    "m.video": "video",
                }.get(msgtype, "document")

                tgm_id = (
                    event.source["content"]
                    .get("fi.mau.telegram.source", {})
                    .get("id")
                )  # --- CHANGE

                await callback(
                    telegram_chat_id,
                    matrix_event_id,
                    sender,
                    {
                        "text": event.body or "",
                        "files": [
                            {
                                "file_id": event.event_id,
                                "file_url": event.url,
                                "type": file_type,
                            }
                        ],
                        "tgm_id": tgm_id,  # --- CHANGE
                    },
                )

        # підписуємося на text + media
        self.client.add_event_callback(on_message, (RoomMessageText, RoomMessageMedia))

        await self.login()
        logger.info("Matrix sync started")
        await self.client.sync_forever(timeout=30_000)
