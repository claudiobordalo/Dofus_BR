from dataclasses import dataclass


APP_NAME = "Bot Dofus BR"
APP_VERSION = "1.0.0"

DEBUG = False

YOLO_MODEL = "meu_modelo.pt"


@dataclass(frozen=True)
class ScreenRegion:
    x1: int
    y1: int
    x2: int
    y2: int


MAP_CHANGE = {
    "right": ScreenRegion(1608, 546, 1872, 676),
    "left": ScreenRegion(280, 13, 315, 804),
    "bottom": ScreenRegion(1280, 927, 1535, 1079),
    "top": ScreenRegion(329, 1, 1583, 12),
}


MINIMAP_REGION = ScreenRegion(
    1778,
    958,
    1904,
    1065,
)


FARM_REGION = ScreenRegion(
    323,
    14,
    1596,
    922,
)


SCREEN_BLACK_THRESHOLD = 10

MAP_CHANGE_TIMEOUT = 3.5
MAP_CHANGE_INTERVAL = 0.2

CLICK_DURATION_MIN = 0.1
CLICK_DURATION_MAX = 0.2

MOUSE_DELAY_MIN = 0.02
MOUSE_DELAY_MAX = 0.05
