"""
captura.py

Responsável exclusivamente pela captura da tela do jogo.
"""

from __future__ import annotations

import cv2
import mss

from utils import capturar_tela

class CapturaTela:
    """
    Centraliza toda a captura de tela utilizada pelo bot.
    """

    def __init__(self):

        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]

    def capturar(self):
        """
        Retorna a imagem capturada como numpy.ndarray.
        """

        return capturar_tela(
            self.sct,
            self.monitor,
        )

    def salvar_temporaria(
        self,
        caminho: str = "temp_screenshot.jpg",
    ) -> str:
        """
        Captura a tela e salva uma imagem temporária.
        """

        imagem = self.capturar()

        cv2.imwrite(
            caminho,
            imagem,
        )

        return caminho
