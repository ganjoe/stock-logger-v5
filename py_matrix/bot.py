"""
py_matrix/bot.py
Async Matrix Bot that bridges Matrix messages to the PTABridge.
Listens on a single room and forwards messages to Gemini PTA.
"""
import asyncio
import time
from nio import AsyncClient, MatrixRoom, RoomMessageText, LoginResponse
from .config import MatrixConfig


class MatrixBot:
    """
    Thin adapter: Matrix Room <-> PTABridge.
    Only listens on one configured room. A dispatcher upstream 
    ensures only selected messages reach this bot.
    """

    def __init__(self, config: MatrixConfig, pta_bridge):
        self.config = config
        self.bridge = pta_bridge
        self.client = AsyncClient(config.homeserver, config.user_id)
        self._start_time = time.time()

    async def login(self) -> bool:
        """Logs in with user/password. Returns True on success."""
        response = await self.client.login(self.config.password)
        if isinstance(response, LoginResponse):
            print(f"[Matrix] ✅ Logged in as {self.config.user_id}")
            return True
        else:
            print(f"[Matrix] ❌ Login failed: {response}")
            return False

    async def _on_message(self, room: MatrixRoom, event: RoomMessageText):
        """Callback for incoming messages."""
        # 1. Ignore messages from wrong room
        if room.room_id != self.config.room_id:
            return

        # 2. Ignore own messages (loop prevention)
        if event.sender == self.config.user_id:
            return

        # 3. Ignore old messages from before bot startup (initial sync)
        if event.server_timestamp / 1000 < self._start_time:
            return

        user_msg = event.body.strip()
        if not user_msg:
            return

        print(f"[Matrix] 📩 {event.sender}: {user_msg}")

        try:
            # 4. Forward to PTA Bridge (synchronous call in async context)
            response = await asyncio.to_thread(self.bridge.chat, user_msg)

            # 5. Send response back to room
            await self.client.room_send(
                room_id=self.config.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": response,
                },
            )
            print(f"[Matrix] 📤 Response sent ({len(response)} chars)")

        except Exception as e:
            error_msg = f"❌ PTA Error: {str(e)}"
            print(f"[Matrix] {error_msg}")
            await self.client.room_send(
                room_id=self.config.room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": error_msg},
            )

    async def run(self):
        """Main loop: login, register callback, sync forever."""
        success = await self.login()
        if not success:
            return

        # Register message callback
        self.client.add_event_callback(self._on_message, RoomMessageText)

        print(f"[Matrix] 👂 Listening on room {self.config.room_id}")
        print(f"[Matrix] 🚀 Bot is running. Press Ctrl+C to stop.")

        # Sync forever (blocks)
        try:
            await self.client.sync_forever(timeout=30000, full_state=True)
        except KeyboardInterrupt:
            print("[Matrix] 🛑 Shutting down...")
        finally:
            await self.client.close()
            print("[Matrix] 🔌 Disconnected.")
