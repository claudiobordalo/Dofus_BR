import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Tuple

import keyboard
from ultralytics import YOLO

from config import *

from src.detector import Detector
from src.mapa import GameMap
from src.utils import (
    get_coordinates,
    save_coordinates,
)

class BotInterface:

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("Bot Dofus")
        self.root.geometry("620x760")

        self.harvest_bot = None

        self.selected_classes = []

        self.selected_position = None

        self.available_classes = self.get_available_classes()

        self.create_widgets()

        keyboard.add_hotkey(
            "F8",
            self.toggle_pause
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_closing
        )

