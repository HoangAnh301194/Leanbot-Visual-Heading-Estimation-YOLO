import asyncio

from logs import log
from readchar import readchar


def calc_run_lr(
    velocity: int,
    speed_l: int,
    speed_r: int,
) -> tuple[int, int]:

    left = velocity * speed_l // 4
    right = velocity * speed_r // 4

    return left, right


def read_char() -> str:
    return readchar()


def flush_keyboard(queue: asyncio.Queue) -> None:
    while True:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            break


async def keyboard_reader(
    queue: asyncio.Queue,
) -> None:

    while True:

        RC = await asyncio.to_thread(
            read_char
        )

        await queue.put(
            RC.lower()
        )


async def sendTinyRCCommand(controller, command):
    # Start waiting for END before sending the first command.
    end_task = asyncio.create_task(
        controller.waitSerialMessage(f"{command}/END", 30) # wait maximum 30ms
    )

    try:
        # Retry up to 3 times if START is not received.
        for i in range(3):
            log("tinyRC", f"Send command {command} try {i + 1}")

            await controller.send(
                f"{command}\n",
                response=False,
            )

            # Wait up to 300 ms for START.
            if await controller.waitSerialMessage(
                f"{command}/START",
                0.3,
            ):
                log("tinyRC", "Receive command START")

                # START received -> wait for END.
                await end_task

                log("tinyRC", "Receive command END")
                return True

            log("tinyRC", "START timeout")

        # START was not received after 3 attempts.
        log(
            "tinyRC",
            "START not received after 3 attempts, "
            "cancelling END waiter",
        )

        return False

    finally:
        # Clean up END waiter if it is still waiting.
        if not end_task.done():
            end_task.cancel()

        await asyncio.gather(
            end_task,
            return_exceptions=True,
        )


async def run_lr(
    controller,
    velocity: int,
    speed_l: int,
    speed_r: int,
) -> None:

    left, right = calc_run_lr(
        velocity,
        speed_l,
        speed_r,
    )

    command = f"r/{left}/{right}"

    log("TX", command.rstrip())

    await sendTinyRCCommand(controller, command)


async def run_fw_bw(
    controller,
    speed: int,
    duration: int,
) -> None:

    command = f"rfb/{speed}/{duration}"

    log("TX", command.rstrip())

    await sendTinyRCCommand(controller, command)

async def spin_steps(
    controller,
    speed: int,
    rotationSteps: int,
) -> None:

    command = f"spst/{speed}/{rotationSteps}"

    log("TX", command.rstrip())

    await sendTinyRCCommand(controller, command)

def get_config(controller) -> dict:
    try:
        return controller.config[
            "LeanbotTinyRC"
        ][
            "ManualControl"
        ]

    except KeyError as error:
        raise RuntimeError(
            "LeanbotTinyRC.ManualControl "
            "configuration is missing"
        ) from error


async def manual_control(controller) -> None:

    config = get_config(controller)

    velocity = int(
        config["Velocity"]
    )

    keymap = config["KeyMap"]

    end_key = str(
        config["ControlKey"]["End"]
    ).lower()

    if not controller.is_connected():
        raise RuntimeError(
            "Cannot start manual control: "
            "Leanbot is not connected"
        )

    log(
        "RC",
        f"Leanbot Tiny RC manual control started. "
        f"End RC: {end_key!r}",
    )

    keyboard_queue = asyncio.Queue()

    keyboard_task = asyncio.create_task(
        keyboard_reader(
            keyboard_queue
        )
    )

    try:

        while controller.is_connected():

            RC = await keyboard_queue.get()

            if RC == end_key:
                log(
                    "RC",
                    f"End RC {end_key!r} pressed",
                )
                break

            # if RC == "t":
            #     log(
            #         "RC",
            #         f"Test runFwBw(2000, 5000)",
            #     )

            #     await run_fw_bw(
            #         controller,
            #         2000,
            #         5000,
            #     )

            #     # Discard every key pressed while command was running.
            #     flush_keyboard(
            #         keyboard_queue
            #     )

            #     continue

            if RC not in keymap:
                continue

            command_config = keymap[RC]

            command_name = str(
                command_config["name"]
            )

            speed_l = int(
                command_config["speed_l"]
            )

            speed_r = int(
                command_config["speed_r"]
            )

            await run_lr(
                controller,
                velocity,
                speed_l,
                speed_r,
            )

            # Discard every key pressed while command was running.
            flush_keyboard(
                keyboard_queue
            )

            left, right = calc_run_lr(
                velocity,
                speed_l,
                speed_r,
            )

            log('RC KEY', f"[{RC.upper()}] {command_name:15} -> RunLR({left}, {right})")
            # print(
            #     f"[{RC.upper()}] "
            #     f"{command_name:15} "
            #     f"-> RunLR({left}, {right})",
            #     flush=True,
            # )

    finally:

        keyboard_task.cancel()

        await asyncio.gather(
            keyboard_task,
            return_exceptions=True,
        )

        if controller.is_connected():

            try:
                await run_lr(
                    controller,
                    velocity,
                    0,
                    0,
                )

            except Exception as error:
                log(
                    "RC",
                    f"Failed to stop Leanbot: "
                    f"{type(error).__name__}: {error}",
                )

    log(
        "RC",
        "Leanbot Tiny RC manual control ended",
    )