import random
import time

import cv2
import mss
import numpy as np

from humancursor import SystemCursor

from src.config import (
    MINIMAP_REGION,
    SCREEN_BLACK_THRESHOLD,
    MAP_CHANGE_TIMEOUT,
    MAP_CHANGE_INTERVAL,
)


def mover_mouse_humano(x: int, y: int) -> None:
    cursor = SystemCursor()
    cursor.move_to([x, y])
    time.sleep(random.uniform(0.02, 0.05))


def clique_humano(x: int, y: int, duracao: float = 0.2) -> None:
    cursor = SystemCursor()
    time.sleep(random.uniform(0.01, 0.05))
    cursor.click_on(
        [x, y],
        click_duration=random.uniform(0.1, duracao),
    )


def focar_jogo() -> None:
    x = random.randint(MINIMAP_REGION.x1, MINIMAP_REGION.x2)
    y = random.randint(MINIMAP_REGION.y1, MINIMAP_REGION.y2)

    mover_mouse_humano(x, y)
    clique_humano(x, y)


def capturar_tela(sct, monitor):
    screenshot = sct.grab(monitor)
    img = np.array(screenshot)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def tela_preta(threshold=SCREEN_BLACK_THRESHOLD):
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = capturar_tela(sct, monitor)

    h, w, _ = img.shape
    centro = img[h // 3:2 * h // 3, w // 3:2 * w // 3]

    return np.mean(centro) < threshold


def detectar_troca_mapa(
    segundos=MAP_CHANGE_TIMEOUT,
    intervalo=MAP_CHANGE_INTERVAL,
):
    tela_ficou_preta = False

    for _ in range(int(segundos / intervalo)):
        time.sleep(intervalo)

        if tela_preta():
            tela_ficou_preta = True
            break

    if not tela_ficou_preta:
        return False

    while True:
        time.sleep(intervalo)

        if not tela_preta():
            return True
