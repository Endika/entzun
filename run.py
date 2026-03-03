import sys
import tkinter as tk
from tkinter import messagebox

import speech_recognition as sr

from entzun.ui.app import EntzunApp, logger


def main() -> None:
    logger.info("=== Entzun application ===")
    logger.info("Python: %s", sys.version)
    logger.info("Available microphones: %s", sr.Microphone.list_microphone_names())

    try:
        root = tk.Tk()
        EntzunApp(root)
        logger.info("Starting UI")
        root.mainloop()
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        messagebox.showerror("Fatal error", f"Error starting application:\n{exc}")
        sys.exit(1)
    finally:
        logger.info("=== Application closed ===")


if __name__ == "__main__":
    main()
