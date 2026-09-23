from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

import yaml

from logs import (
    logs_init,
    logs_shutdown,
    set_log_file,
    log,
)

from LeanbotController import (
    LeanbotController,
)


# =========================================================================
# CLI
# =========================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "leanbot service.\n\n"
            "This program initializes a leanbot, connects it to "
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--leanbot",
        type=int,
        required=True,
        help=(
            "leanbot ID.\n\n"
            "Example:\n"
            "  --leanbot 123456"
        ),
    )

    parser.add_argument(
        "--saveLog",
        type=int,
        default=0,
        help=(
            "Save log file to log/leanbot<Leanbot ID>.txt.\n"
            "Default: 0\n\n"
            "Example:\n"
            "  --saveLog 1"
        ),
    )

    parser.add_argument(
        "--configFile",
        type=str,
        default=None,
        help=(
            "Path to the configuration file.\n"
            "Mandatory requirement, if omitted, throw error.\n\n"
            "Example:\n"
            "  --configFile ./config/config.yaml"
        ),
    )

    return parser.parse_args()


# =========================================================================
# Load config
# =========================================================================


def load_config(config_file: str | Path) -> dict:
    """
    Load the YAML configuration file.
    """

    config_path = Path(config_file).resolve()

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    config["_config_dir"] = config_path.parent

    return config


# =========================================================================
# MAIN
# =========================================================================


async def main() -> None:
    args = parse_args()

    if args.configFile is None:
        log(
            "SYS",
            "Error: --configFile argument is required.",
        )
        return

    # ---------------------------------------------------------------------
    # Initialize logger
    # ---------------------------------------------------------------------

    await logs_init()

    log_file = None

    if args.saveLog:
        log_dir = Path("log")
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"leanbot{args.leanbot}.txt"

        set_log_file(str(log_file))

    leanbot: LeanbotController | None = None

    try:
        log(
            "SYS",
            "=== Starting leanbot ===",
        )

        log(
            "SYS",
            f"leanbot ID: {args.leanbot}",
        )

        if args.saveLog:
            log(
                "SYS",
                f"Log file: {log_file}",
            )
        else:
            log(
                "SYS",
                "Log file: disabled",
            )

        # -----------------------------------------------------------------
        # Load from config file
        # -----------------------------------------------------------------

        config = load_config(args.configFile)

        log(
            "SYS",
            f"load from {args.configFile}: \n {config}",
        )

        # -----------------------------------------------------------------
        # Create leanbot
        # -----------------------------------------------------------------

        log(
            "SYS",
            "Initializing BLE Leanbot...",
        )

        leanbot = LeanbotController(
            args.leanbot,
            config["LeanbotController"],
        )

        leanbot.clearSerialState()
        leanbot.openSerial()
        leanbot.startSerialBLEHandler()  # forward all serial message to web

        # -----------------------------------------------------------------
        # Initialize BLE Leanbot
        # -----------------------------------------------------------------

        log(
            "SYS",
            "Connect leanbot...",
        )

        await leanbot.find()
        await leanbot.connect()

        log(
            "SYS",
            "Press Ctrl+C to stop",
        )

        await leanbot.manualControlLeanbotRC()

    except asyncio.CancelledError:
        log(
            "SYS",
            "leanbot task cancelled",
        )

    except KeyboardInterrupt:
        log(
            "SYS",
            "Ctrl+C received. Stopping...",
        )

    except Exception as error:
        log(
            "SYS",
            f"Unexpected error: {error}",
        )

    finally:
        # -----------------------------------------------------------------
        # Cleanup leanbot
        # -----------------------------------------------------------------

        log(
            "SYS",
            "=== Shutting down leanbot ===",
        )

        log(
            "SYS",
            "=== leanbot stopped ===",
        )

        try:
            if leanbot is not None:
                leanbot.clearSerialState()
                leanbot.closeSerial()
                await leanbot.killSerialBLEHandlerTask()
                await leanbot.disconnect()

            await logs_shutdown()

        except Exception as error:
            log(
                "SHUTDOWN",
                f"Serial cleanup error: {error}",
            )

        finally:
            os._exit(0)


# =========================================================================
# ENTRY POINT
# =========================================================================


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass