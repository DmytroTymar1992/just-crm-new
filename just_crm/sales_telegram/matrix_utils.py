import asyncio
import aiohttp
from nio import AsyncClient, MatrixRoom, RoomMessageText, RoomMessageMedia
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MatrixTelegramClient:
    def __init__(self):
        self.client = AsyncClient(settings.MATRIX_SERVER)
        self.client.access_token = None
        self.room_alias_cache = {}

    async def login(self):
        logger.debug(f"Attempting login with {settings.MATRIX_ADMIN_USERNAME}")
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{settings.MATRIX_SERVER}/_matrix/client/r0/login"
                payload = {
                    "type": "m.login.password",
                    "identifier": {"type": "m.id.user", "user": settings.MATRIX_ADMIN_USERNAME},
                    "password": settings.MATRIX_ADMIN_PASSWORD
                }
                async with session.post(url, json=payload) as response:
                    data = await response.json()
                    if response.status == 200 and 'access_token' in data:
                        self.client.access_token = data['access_token']
                        self.client.user_id = settings.MATRIX_ADMIN_USERNAME
                        logger.info("Matrix login successful")
                    elif response.status == 429:
                        retry_after = data.get('retry_after_ms', 5000) / 1000
                        logger.warning(f"Rate limited, sleeping for {retry_after}s")
                        await asyncio.sleep(retry_after)
                        return await self.login()
                    else:
                        raise Exception(f"Login failed: {data}")
        except Exception as e:
            logger.error(f"Matrix login failed: {e}")
            raise

    async def get_room_alias(self, room_id):
        if room_id in self.room_alias_cache:
            return self.room_alias_cache[room_id]
        async with aiohttp.ClientSession() as session:
            url = f"{settings.MATRIX_SERVER}/_matrix/client/v3/rooms/{room_id}/aliases"
            headers = {"Authorization": f"Bearer {self.client.access_token}"}
            try:
                async with session.get(url, headers=headers) as response:
                    text = await response.text()
                    logger.debug(f"API response for {room_id}: {text}")
                    if response.status == 200:
                        data = await response.json()
                        aliases = data.get('aliases', [])
                        for alias in aliases:
                            if alias.startswith('#telegram_'):
                                chat_id = alias.split('_')[1].split(':')[0]
                                self.room_alias_cache[room_id] = chat_id
                                logger.info(f"Cached telegram_chat_id: {chat_id} for {room_id}")
                                return chat_id
                        logger.debug(f"No telegram alias for {room_id}: {aliases}")
                        return None
                    elif response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 10)) * 1000
                        logger.warning(f"Rate limited, sleeping for {retry_after}ms")
                        await asyncio.sleep(retry_after / 1000)
                        return await self.get_room_alias(room_id)
                    else:
                        logger.error(f"Failed to get aliases: {response.status} - {text}")
                        return None
            except Exception as e:
                logger.error(f"Error fetching aliases for {room_id}: {e}")
                return None

    async def start_listener(self, callback):
        async def on_message(room: MatrixRoom, event):
            logger.debug(f"Received event in room {room.room_id}: {event}")
            if event.sender != settings.MATRIX_ADMIN_USERNAME:
                message_id = event.event_id
                sender = event.sender
                telegram_chat_id = await self.get_room_alias(room.room_id)
                if not telegram_chat_id:
                    if sender.startswith("@telegram_"):
                        try:
                            telegram_chat_id = sender.split(":", 1)[0].split("_", 1)[1]
                            logger.info(
                                f"Fallback telegram_chat_id {telegram_chat_id} parsed from sender {sender}"
                            )
                        except Exception as parse_exc:
                            logger.error(
                                f"Failed to parse telegram_chat_id from sender {sender}: {parse_exc}"
                            )
                            return
                    else:
                        logger.error(
                            f"Could not determine telegram_chat_id for room {room.room_id}"
                        )
                        return
                logger.info(f"Processing message from {telegram_chat_id} (message_id: {message_id}, chat_id: {telegram_chat_id})")
                if isinstance(event, RoomMessageText):
                    await callback(telegram_chat_id, message_id, sender, {'text': event.body, 'files': []})
                elif isinstance(event, RoomMessageMedia):
                    msgtype = event.source['content'].get('msgtype', 'm.file')
                    file_type = {
                        'm.image': 'image',
                        'm.file': 'document',
                        'm.audio': 'voice',
                        'm.video': 'video'
                    }.get(msgtype, 'document')
                    await callback(telegram_chat_id, message_id, sender, {
                        'text': event.body or '',
                        'files': [{
                            'file_id': event.event_id,
                            'file_url': event.url,
                            'type': file_type
                        }]
                    })

        self.client.add_event_callback(on_message, (RoomMessageText, RoomMessageMedia))
        await self.login()
        logger.info("Starting Matrix sync")
        try:
            await self.client.sync_forever(timeout=30000)
        except Exception as e:
            logger.error(f"Error in sync_forever: {e}")
            raise