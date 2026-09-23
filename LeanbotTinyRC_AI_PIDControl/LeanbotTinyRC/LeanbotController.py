import asyncio
import time

import shutil
from typing import Any, Callable, Optional, Awaitable
import inspect

from leanbot_ble import LeanbotBLE
from logs import log

import leanbotTinyRC

import traceback
import logging

#####################################################################

class LeanbotController:
    """
    Thin wrapper around LeanbotBLE.

    Responsibilities:
        - Own one LeanbotBLE instance
        - Expose upload / bootloader operations
        - Expose firmware pipe operations
        - Expose upload progress
        - Provide a place for higher-level serial commands
    """

    def __init__(
        self,
        leanbotid: int,
        config: dict,
    ):
        self.config = config
        log(
            "CFG",
            f"LeanbotController config: {self.config!r}",
        )
        self.leanbotid = f"Leanbot {leanbotid} BLE"

        self.serialMessageFromLeanbotQueue: asyncio.Queue[str] = asyncio.Queue()
        self.serialMessageToLeanbotQueue: asyncio.Queue[str] = asyncio.Queue()
        self.serialLineBuffer: str = ""
        self.serialOpen:bool = True

        # ------------------------------------------------------------------
        # Serial BLE Message Handler
        # ------------------------------------------------------------------

        self.serialBLEHandlerTask: Optional[asyncio.Task] = None

        self.pendingSerialMessageWaiters: dict[
            str,
            list[asyncio.Future],
        ] = {}

        self.leanbot = LeanbotBLE(
            notify_callback=self.serial_notification_handler,
            name=self.leanbotid,
            adapter=self.config["LeanbotBLE"]["bluetoothAdapter"]
        )

        self.is_uploading = False

    # ======================================================================
    # BLE Serial
    # ======================================================================

    # ================== Serial from Leanbot ====================== #

    def serial_notification_handler(self, sender, data):
        try:
            if(not self.serialOpen):
                return

            text = data.decode(errors="replace")

            log("BLE RX", text)

            self.serialMessageFromLeanbotQueue.put_nowait(text)   # Put one raw serial notification into the queue.

        except Exception as error:
            log(
                "BLE RX",
                f"BLE Serial error: {error}",
            )

    async def getSerialMessageFromLeanbot(self) -> str:
        """
        Wait for and return one raw serial notification.
        """
        return await self.serialMessageFromLeanbotQueue.get()

    def clearSerialMessageFromLeanbotQueue(self) -> None:
        """
        Clear all pending serial messages from the queue.

        Messages are removed without waiting for new data.
        Each removed item is marked as done.
        """
        while True:
            try:
                self.serialMessageFromLeanbotQueue.get_nowait()
                self.serialMessageFromLeanbotQueue.task_done()
            except asyncio.QueueEmpty:
                break

    # ================== Serial To Leanbot ====================== #

    def forwardSerial(self, text: str):
        self.serialMessageToLeanbotQueue.put_nowait(text) 

    def clearSerialMessageToLeanbotQueue(self) -> None:
        while True:
            try:
                self.serialMessageToLeanbotQueue.get_nowait()
                self.serialMessageToLeanbotQueue.task_done()
            except asyncio.QueueEmpty:
                break


    async def forwardSerialHandler(self):
        while True:
            if self.serialMessageToLeanbotQueue.empty():
                await asyncio.sleep(0.001)
                continue

            # Chờ 20ms để gom thêm các message đến liên tiếp
            await asyncio.sleep(0.02)

            while not self.serialMessageToLeanbotQueue.empty():
                data = await self.serialMessageToLeanbotQueue.get()
                await self.send(data)
    
    # ================== Serial from Leanbot ====================== #

    def clearSerialState(self) -> None:
        self.clearSerialMessageFromLeanbotQueue()
        self.clearSerialMessageToLeanbotQueue()
        self.serialLineBuffer = ""

    def openSerial(self):
        self.serialOpen = True

    def closeSerial(self):
        self.serialOpen = False

    # def completeSerialMessage(self) -> None:
    #     self.serialMessageFromLeanbotQueue.task_done()

    # ======================================================================
    # Serial Line Reader
    # ======================================================================

    async def getSerialLine(self) -> str:
        """
        Wait for and return the next complete serial line.
        """

        while True:

            # --------------------------------------------------------------
            # If buffer already contains a complete line, return it first.
            # --------------------------------------------------------------

            if "\n" in self.serialLineBuffer:

                line, self.serialLineBuffer = \
                    self.serialLineBuffer.split("\n", 1)

                return line.rstrip("\r")

            # --------------------------------------------------------------
            # Otherwise wait for another BLE notification.
            # --------------------------------------------------------------

            text = await self.getSerialMessageFromLeanbot()

            self.serialLineBuffer += text

    # ======================================================================
    # Serial Line Reader
    # ======================================================================

    async def getSerialLine(self) -> str:
        """
        Wait for and return the next complete serial line.
        """

        while True:

            # --------------------------------------------------------------
            # If buffer already contains a complete line, return it first.
            # --------------------------------------------------------------

            if "\n" in self.serialLineBuffer:

                line, self.serialLineBuffer = \
                    self.serialLineBuffer.split("\n", 1)

                return line.rstrip("\r")

            # --------------------------------------------------------------
            # Otherwise wait for another BLE notification.
            # --------------------------------------------------------------

            text = await self.getSerialMessageFromLeanbot()

            self.serialLineBuffer += text

    # ======================================================================
    # Serial BLE Message Handler
    # ======================================================================

    async def _empty_serial_handler(
        self,
        line: str,
    ) -> None:
        pass

    def startSerialBLEHandler(
        self,
        handle_line: Callable[[str], Any] | None = None,
    ) -> None:
        """
        Start the background serial BLE message handler.

        The handler receives every complete serial line.

        Only this background task consumes the serial BLE queue.
        Serial message waiters are notified by the same dispatcher.
        """

        if handle_line is None:
            log(
                "BLE",
                "No serial BLE handler provided, using empty handler",
            )
            handle_line = self._empty_serial_handler

        if not callable(handle_line):
            raise TypeError("Serial BLE handler must be callable")

        if (
            self.serialBLEHandlerTask is not None
            and not self.serialBLEHandlerTask.done()
        ):
            raise RuntimeError(
                "Serial BLE handler task is already running"
            )

        async def handler_loop() -> None:
            try:
                while True:

                    # ------------------------------------------------------
                    # Read the next complete serial line.
                    # ------------------------------------------------------

                    line = await self.getSerialLine()

                    log(
                        "BLE",
                        f"Serial line: {line}",
                    )

                    # ------------------------------------------------------
                    # Notify all waiters waiting for this exact message.
                    # ------------------------------------------------------

                    self.notifySerialMessageWaiters(line)

                    # ------------------------------------------------------
                    # Forward the line to the registered handler.
                    # ------------------------------------------------------

                    result = handle_line(line)

                    if inspect.isawaitable(result):
                        await result

            except asyncio.CancelledError:
                log(
                    "BLE",
                    "Serial BLE handler task cancelled",
                )
                raise

            except Exception as error:
                log(
                    "BLE",
                    f"Serial BLE handler task stopped: {error}",
                )
                traceback.print_exc()
                raise

        self.serialBLEHandlerTask = asyncio.create_task(
            handler_loop()
        )

    async def killSerialBLEHandlerTask(self) -> None:
        """
        Cancel and clean up the serial BLE message handler task.

        The task is awaited to guarantee that it has actually terminated.
        """

        task = self.serialBLEHandlerTask

        if task is None:
            return

        self.serialBLEHandlerTask = None

        if not task.done():
            task.cancel()

        try:
            await asyncio.gather(
                task,
                return_exceptions=True,
            )

        finally:
            self.serialBLEHandlerTask = None

    # ======================================================================
    # Serial Message Waiting
    # ======================================================================

    async def waitSerialMessage(
        self,
        expected_message: str,
        timeout_s: Optional[float] = None,
    ) -> str:
        """
        Wait for the next serial message matching expected_message.

        This method does not consume the serial BLE queue.
        The serial BLE handler is responsible for notifying
        pending waiters when a message arrives.

        Args:
            expected_message:
                Exact serial line to wait for.

            timeout_s:
                Timeout in seconds.
                None means wait indefinitely.

        Returns:
            The received serial message.

        Raises:
            TimeoutError:
                If no matching message is received before timeout.

            RuntimeError:
                If the serial BLE message waiters are cleared
                while waiting.

            asyncio.CancelledError:
                If the caller cancels the waiting task.
        """

        loop = asyncio.get_running_loop()

        future: asyncio.Future[str] = loop.create_future()

        waiters = self.pendingSerialMessageWaiters.setdefault(
            expected_message,
            [],
        )

        waiters.append(
            future,
        )

        try:

            if timeout_s is None:

                return await asyncio.shield(
                    future,
                )

            return await asyncio.wait_for(
                asyncio.shield(future),
                timeout=timeout_s,
            )

        except asyncio.TimeoutError as error:

            current_waiters = self.pendingSerialMessageWaiters.get(
                expected_message,
            )

            if current_waiters is not None:

                try:
                    current_waiters.remove(
                        future,
                    )

                except ValueError:
                    pass

                if not current_waiters:

                    self.pendingSerialMessageWaiters.pop(
                        expected_message,
                        None,
                    )

            raise TimeoutError(
                "Timeout waiting for serial message: "
                f"{expected_message}"
            ) from error

        except asyncio.CancelledError:

            # The caller cancelled the task.
            # Remove this waiter from the pending list.

            current_waiters = self.pendingSerialMessageWaiters.get(
                expected_message,
            )

            if current_waiters is not None:

                try:
                    current_waiters.remove(
                        future,
                    )

                except ValueError:
                    pass

                if not current_waiters:

                    self.pendingSerialMessageWaiters.pop(
                        expected_message,
                        None,
                    )

            raise

    def notifySerialMessageWaiters(
        self,
        message: str,
    ) -> None:
        """
        Notify all pending waiters waiting for the received
        serial message.
        """

        waiters = self.pendingSerialMessageWaiters.get(
            message,
        )

        if not waiters:
            return

        pending = list(waiters)

        self.pendingSerialMessageWaiters.pop(
            message,
            None,
        )

        for future in pending:

            if not future.done():

                future.set_result(
                    message,
                )

    def rejectAllSerialMessageWaiters(
        self,
        reason: str,
    ) -> None:
        """
        Reject all pending serial message waiters.

        This is used when the serial session is terminated,
        so no Future can remain pending after the session is gone.
        """

        error = RuntimeError(
            reason,
        )

        pending = list(
            self.pendingSerialMessageWaiters.values()
        )

        self.pendingSerialMessageWaiters.clear()

        for waiters in pending:

            for future in waiters:

                if not future.done():

                    future.set_exception(
                        error,
                    )
    
    # ------------------------------------------------------------------
    # BLE
    # ------------------------------------------------------------------

    async def find(self, scan_timeout=5, retry_interval=3):
        return await self.leanbot.find_device_by_name(
            scan_timeout=scan_timeout,
            retry_interval=retry_interval,
        )

    async def connect(self):
        return await self.leanbot.connect()

    async def disconnect(self):
        await self.leanbot.disconnect()

    def is_connected(self):
        return self.leanbot.is_connected()

    async def reset(self):
        await self.disconnect()
        await self.find(retry_interval=0.1)
        await self.connect()
        await asyncio.sleep(1.5) # ensure escape bootloader

    # ------------------------------------------------------------------
    # Bootloader
    # ------------------------------------------------------------------

    # async def enterBootloader(self):
    #     await self.leanbot.uploader.attemptsEnterBootloader()

    # async def keepOnBootloader(self):
    #     await self.leanbot.uploader.keepOnBootloader()

    # async def escapeBootloader(self):
    #     await self.leanbot.uploader.escapeBootloader()

    # def isBootloaderMode(self):
    #     return self.leanbot.uploader.is_bootloader_mode

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def isUploading(self):
        return self.is_uploading

    async def upload(self):
        """
        Upload firmware and keep the device in bootloader afterwards.
        """

        if self.is_uploading:
            raise RuntimeError("Upload is already running")

        self.is_uploading = True
        try:
            await self.leanbot.uploader.upload2()
            return True

        finally:
            self.is_uploading = False
            await asyncio.sleep(1.5) # ensure escape bootloader

    # ------------------------------------------------------------------
    # Upload progress
    # ------------------------------------------------------------------

    def getUploadWriteProgress(self):
        return self.leanbot.uploader.getWriteProgress()

    def getUploadVerifyProgress(self):
        return self.leanbot.uploader.getVerifyProgress()
    
    # ------------------------------------------------------------------
    # Firmware pipe
    # ------------------------------------------------------------------

    def open_hex_pipe(self):
        self.leanbot.uploader.open_hex_pipe()

    def push_hex_pipe(self, seq, addr, data):
        self.leanbot.uploader.push_hex_pipe(
            seq=seq,
            addr=addr,
            data=data,
        )

    def close_hex_pipe(self, reason=None):
        self.leanbot.uploader.close_hex_pipe(reason)

    def abort_upload(self, reason=None):
        self.leanbot.uploader.abort(reason)

    # ------------------------------------------------------------------
    # Serial
    # ------------------------------------------------------------------

    async def send(self, data, response=True):
        """
        Low-level serial send.

        This is intentionally generic for now.
        Higher-level commands can be added later, e.g.:

            await controller.run(...)
            await controller.stop(...)
            await controller.reset(...)
        """

        await self.leanbot.send(
            data,
            response=response,
        )

    # ------------------------------------------------------------------
    # High-level commands
    # ------------------------------------------------------------------

    async def selectRunLeanbot(self):
        log('Controller', 'send RUN to leanbot => select run mission')
        await self.send("RUN\n")

    async def showLeanbotCodeTag(self):
        log('Controller', 'send SHOW to leanbot => show Leanbot code tag')
        await self.send("SHOW\n")

    async def selectControlLeanbotRC(self):

        # log('Controller', 'Reset Leanbot')
        # await self.reset()

        log('Controller', 'send RESETTING to leanbot => select manual control tinyRC')
        await self.send("RESETTING\n")

    async def manualControlLeanbotRC(self):
        log('Controller', 'Start manual control Leanbot')
        await leanbotTinyRC.manual_control(self)
    