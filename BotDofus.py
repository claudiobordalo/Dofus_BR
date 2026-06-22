import json
import os
import sys
import time
import random
import threading
import logging
from typing import List, Tuple, Dict, Optional

import tkinter as tk
from tkinter import messagebox

import torch
import mss
import numpy as np
import cv2
from humancursor import SystemCursor
from ultralytics import YOLO

from config import *

class GameMap:
    def __init__(self, map_name: str):
        """
        Initialise une nouvelle instance de GameMap.
        
        Args:
            map_name (str): Nom de la carte (ex: "Incarnam", "Astrub")
        """
        self.map_name = map_name
        self.file_path = f"{map_name}_map.txt"
        self.map_data = self._load_map()
        self.visits = self._initialize_visits()
        
    def _load_map(self) -> Dict[str, any]:
        """
        Charge les données de la carte depuis le fichier.
        
        Returns:
            Dict[str, any]: Données de la carte ou dictionnaire vide si le fichier n'existe pas
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Fichier {self.file_path} introuvable, création d'un nouveau fichier...")
            return {}
        except Exception as e:
            print(f"Erreur lors du chargement de la carte : {e}")
            return {}

    def _initialize_visits(self) -> Dict[Tuple[int, int], int]:
        """
        Initialise le compteur de visites pour chaque position connue.
        
        Returns:
            Dict[Tuple[int, int], int]: Dictionnaire des visites
        """
        visits = {}
        for coord_str in self.map_data:
            try:
                x_str, y_str = coord_str.split(',')
                visits[(int(x_str), int(y_str))] = 0
            except Exception as e:
                print(f"Erreur lors de l'initialisation des visites pour {coord_str}: {e}")
        return visits

    def save(self) -> None:
        """Sauvegarde les données de la carte dans le fichier."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.map_data, f, indent=4, ensure_ascii=False)
            print(f"Carte {self.map_name} sauvegardée avec succès!")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la carte : {e}")

    def increment_visits(self, position: Tuple[int, int], visits) -> None:
        """
        Incrémente le compteur de visites pour une position donnée.
        
        Args:
            position (Tuple[int, int]): Position (x, y) sur la carte
        """
        self.visits[position] =  visits

    def update_resource(self, position: Tuple[int, int], resource_name: str, count: int) -> None:
        """
        Met à jour la quantité d'une ressource à une position donnée.
        
        Args:
            position (Tuple[int, int]): Position (x, y) sur la carte
            resource_name (str): Nom de la ressource
            count (int): Quantité de la ressource
        """
        key = f"{position[0]},{position[1]}"
        
        if key not in self.map_data:
            self.map_data[key] = {
                "accessible": {},
                resource_name: count
            }
            print(f"Création de la case {position} dans la mémoire.")
        else:
            current_count = self.map_data[key].get(resource_name, 0)
            self.map_data[key][resource_name] = max(count, current_count)
        
        print(f"Mise à jour de la case {position}: {self.map_data[key]}")

    def update_accessibility(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], 
                           is_accessible: bool) -> None:
        """
        Met à jour l'accessibilité entre deux positions.
        
        Args:
            from_pos (Tuple[int, int]): Position de départ
            to_pos (Tuple[int, int]): Position d'arrivée
            is_accessible (bool): True si le passage est possible
        """
        from_key = f"{from_pos[0]},{from_pos[1]}"
        to_key = f"{to_pos[0]},{to_pos[1]}"
        
        # Mise à jour de l'accessibilité pour la case de destination
        if to_key not in self.map_data:
            self.map_data[to_key] = {"accessible": {}}
        
        if "accessible" not in self.map_data[to_key]:
            self.map_data[to_key]["accessible"] = {}
            
        self.map_data[to_key]["accessible"][from_key] = is_accessible
        
        print(f"Accessibilité mise à jour: {to_key} -> {self.map_data[to_key]}")

    def get_possible_moves(self, current_pos: Tuple[int, int]) -> list:
        """
        Retourne les mouvements possibles depuis une position donnée.
        
        Args:
            current_pos (Tuple[int, int]): Position actuelle
        
        Returns:
            list: Liste des mouvements possibles [(new_x, new_y, visits_count, direction)]
        """
        directions = {
            "top": (0, -1),
            "bottom": (0, 1),
            "left": (-1, 0),
            "right": (1, 0)
        }
        
        current_key = f"{current_pos[0]},{current_pos[1]}"
        possible_moves = []
        
        for direction, (dx, dy) in directions.items():
            new_x, new_y = current_pos[0] + dx, current_pos[1] + dy
            new_key = f"{new_x},{new_y}"
            
            try:
                if new_key not in self.map_data or \
                "accessible" not in self.map_data[new_key] or \
                current_key not in self.map_data[new_key]["accessible"] or \
                self.map_data[new_key]["accessible"][current_key]:
                    count = self.visits.get((new_x, new_y), 0)
                    possible_moves.append((new_x, new_y, count, direction))
            except Exception:
                possible_moves.append((new_x, new_y, 0, direction))
                
        return possible_moves

    def get_resource_count(self, position: Tuple[int, int], resource_name: str) -> int:
        """
        Retourne la quantité d'une ressource à une position donnée.
        
        Args:
            position (Tuple[int, int]): Position sur la carte
            resource_name (str): Nom de la ressource
        
        Returns:
            int: Quantité de la ressource (0 si non trouvée)
        """
        key = f"{position[0]},{position[1]}"
        return self.map_data.get(key, {}).get(resource_name, 0)


class HarvestBot:
    def __init__(self, map_name: str, selected_classes: List[str], 
                 initial_position: Tuple[int, int], pod_available: int,
                  restriction_zone: Dict[str, int]):
        """
        Initialise le bot de récolte.
        """
        self.game_map = GameMap(map_name)
        self.selected_classes = selected_classes
        self.current_position = initial_position
        self.pod_available = pod_available
        self.restriction_zone = restriction_zone
        self.is_running = False
        self.is_paused = False
        
        # Définition des régions d'écran pour le changement de map
        self.screen_regions = MAP_CHANGE
        
        # Chargement du modèle YOLO
        self.model = YOLO(YOLO_MODEL)
        if torch.cuda.is_available():
            self.model.to("cuda")
    
    def start(self, running_indication: tk.Label, coord_indication: tk.Label) -> None:
        """
        Démarre le bot dans un état initial propre.
        """
        self.is_running = True
        self.gui_elements = {
            'running_indication': running_indication,
            'coord_indication': coord_indication
        }
        self.run_harvest()
    
    def stop(self) -> None:
        """
        Arrête le bot et sauvegarde l'état de la carte.
        """
        self.is_running = False
        self.gui_elements['running_indication'].config(text="⭕ Bot offline")
        self.game_map.save()
        print("[Bot] Arrêt du bot et sauvegarde des données.")

    def toggle_pause(self):
        """Pausa ou continua o bot."""

        self.is_paused = not self.is_paused

        if self.is_paused:
            self.gui_elements['running_indication'].config(
                text="🟡 Bot pausado"
            )
            print("[Bot] Pausado.")

        else:
            self.gui_elements['running_indication'].config(
                text="🟢 Bot executando"
            )
            print("[Bot] Continuando...")
    
    def human_like_click(self, x: int, y: int, click_duration: float = 0.2) -> None:
        """Simule un clic humain aux coordonnées spécifiées."""
        cursor = SystemCursor()
        time.sleep(random.uniform(0.01, 0.05))
        cursor.click_on([x, y], click_duration=random.uniform(0.1, click_duration))

    def human_like_movement(self, x: int, y: int) -> None:
        """Simule un mouvement de souris naturel."""
        cursor = SystemCursor()
        cursor.move_to([x, y])
        time.sleep(random.uniform(0.02, 0.05))

    def focus_on_game(self) -> None:
        """Met le focus sur la fenêtre du jeu."""
        screen_minimap = (1778, 958, 1904, 1065)
        pixel_x = random.randint(screen_minimap[0], screen_minimap[2])
        pixel_y = random.randint(screen_minimap[1], screen_minimap[3])
        
        self.human_like_movement(pixel_x, pixel_y)
        self.human_like_click(pixel_x, pixel_y)

    def capture_screen(self, sct, monitor) -> np.ndarray:
        """Capture l'écran et retourne l'image en format BGR."""
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def is_screen_black(self, threshold=10) -> bool:
        """Vérifie si le centre de l'écran est noir."""
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = self.capture_screen(sct, monitor)
        h, w, _ = img.shape
        center_crop = img[h//3:2*h//3, w//3:2*w//3]
        return np.mean(center_crop) < threshold

    def detect_map_change(self, seconds: float = 3.5, interval: float = 0.2) -> bool:
        """Détecte un changement de map."""
        black_screen = False
        
        for _ in range(int(seconds/interval)):
            time.sleep(interval)
            if self.is_screen_black():
                black_screen = True
                break
        
        if not black_screen:
            return False
        
        while True:
            time.sleep(interval)
            if not self.is_screen_black():
                return True

    def monitor_monster_attack(self, stop_event: threading.Event, 
                             check_interval: float = 0.1) -> None:
        """Surveille les attaques de monstres."""
        while not stop_event.is_set():
            if self.is_screen_black():
                print("Monstre détecté !")
                stop_event.set()
            time.sleep(check_interval)

    def change_map(self, visits: int) -> Tuple[int, int]:
        """Gère le changement de map."""
        self.game_map.increment_visits(self.current_position, visits)
        possible_moves = self.game_map.get_possible_moves(self.current_position)
        
        if not possible_moves:
            self.sound_alert("Aucune map accessible")
            return self.current_position
        
        # Filtrer les mouvements qui restent dans la zone de restriction
        filtered_moves = [
            move for move in possible_moves 
            if (self.restriction_zone['x1'] <= move[0] <= self.restriction_zone['x2'] and
                self.restriction_zone['y1'] <= move[1] <= self.restriction_zone['y2'])
        ]

        if not filtered_moves:
            self.sound_alert("Aucune map accessible dans la zone de restriction")
            return self.current_position

        random.shuffle(possible_moves)
        
        
        while filtered_moves and self.is_running:
            min_visits = min(move[2] for move in filtered_moves)
            best_moves = [move for move in filtered_moves if move[2] == min_visits]
            new_x, new_y, _, chosen_direction = random.choice(best_moves)
            
            region = self.screen_regions[chosen_direction]
            click_x = random.randint(region[0], region[2])
            click_y = random.randint(region[1], region[3])
            
            self.human_like_movement(click_x, click_y)
            self.human_like_click(click_x, click_y)
            
            if self.detect_map_change():
                time.sleep(0.7)
                self.game_map.update_accessibility(self.current_position, 
                                                (new_x, new_y), True)
                return (new_x, new_y)
            
            self.game_map.update_accessibility(self.current_position, 
                                            (new_x, new_y), False)
            filtered_moves.remove((new_x, new_y, min_visits, chosen_direction))
        
        self.sound_alert("Impossible de changer de map")
        return self.current_position

    def process_detections(self, img_path: str) -> List[Tuple[int, int]]:
        """Traite les détections YOLO et retourne les coordonnées des ressources."""
        results = self.model(img_path, imgsz=640, save=True, show=False)
        detections = []
        class_counts = {}

        def is_point_in_farm(x: int, y: int) -> bool:
            """Vérifie si un point est dans la région d'exclusion définie."""
            x1, y1 = 323, 14  # Coin supérieur gauche
            x2, y2 = 1596, 922  # Coin inférieur droit
            
            return x1 <= x <= x2 and y1 <= y <= y2

        
        for result in results:
            if result.boxes is not None:
                for box, cls in zip(result.boxes.xyxy, result.boxes.cls):
                    class_name = self.model.names[int(cls)]
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
                    
                    if class_name in self.selected_classes:
                        x1, y1, x2, y2 = box.tolist()
                        center_x = int((x1 + x2) / 2 + random.gauss(0, (x2 - x1) * 0.1))
                        center_y = int((y1 + y2) / 2 + random.gauss(0, (y2 - y1) * 0.1))

                        # Vérification que le point est bien dans l'espace de farm (c'est à dire pas sur les côtés)
                        if is_point_in_farm(center_x, center_y):
                            detections.append((center_x, center_y))
                            self.add_to_inventory(class_name)
        
        # Mise à jour des ressources dans la carte
        for class_name, count in class_counts.items():
            self.game_map.update_resource(self.current_position, class_name, count)
            
        return detections

    def run_harvest(self) -> None:
        """Exécute la boucle principale du bot."""

        # Initialisation de mss dans le thread actuel (celui de run_harvest)
        sct = mss.mss()
        monitor = sct.monitors[1]

        self.gui_elements['running_indication'].config(text="✅ Bot running in Harvest Mode")
        self.focus_on_game()
        
        iteration = 0
        while self.is_running:
            iteration += 1
            print(f"\n[Bot] Début de l'itération #{iteration}")
            
            # Capture et analyse de l'écran
            print("test")
            keyboard.press('y')
            print("test validé")
            time.sleep(0.2)
            img = self.capture_screen(sct, monitor)
            temp_img_path = "temp_screenshot.jpg"
            cv2.imwrite(temp_img_path, img)
            keyboard.release('y')
            
            # Traitement des détections
            detections = self.process_detections(temp_img_path)
            
            if detections:
                self.human_like_click(*detections[0])

                stop_monster_event = threading.Event()
                monitor_thread = threading.Thread(
                    target=self.monitor_monster_attack,
                    args=(stop_monster_event,)
                )
                monitor_thread.start()
                
                # Clic sur les ressources
                for idx, (x, y) in enumerate(detections[1:], start=2):
                    if stop_monster_event.is_set():
                        print("[Bot Harvest] Interruption levée par le thread de détection d'écran noir !")
                        self.monster_detected()
                        stop_monster_event.clear()


                    self.human_like_movement(x, y)
                    self.human_like_click(x, y)
                    time.sleep(0.2)
                
                time.sleep(8)

                if stop_monster_event.is_set():
                    print("[Bot Harvest] Interruption levée par le thread de détection d'écran noir !")
                    self.monster_detected()
                
                print("detecte plus les monstres")
                stop_monster_event.set()
                monitor_thread.join()
                time.sleep(0.1)
                

            if self.is_inventory_full():
                self.sound_alert("INVENTORY FULL")

            # Changement de map
            self.current_position = self.change_map(iteration)
            self.gui_elements['coord_indication'].config(
                text=f"({self.current_position[0]}, {self.current_position[1]})"
            )

    def is_inventory_full(self) -> bool:
        """Vérifie si l'inventaire est plein (estimation haute)"""
        return self.pod_available <= 0

    def add_to_inventory(self, ressource):
        """
        Met à jour les pods restant avec l'item collecté
        """
        bois = [ "Bombu", "Chataigner", "Chene", "Erable", "Frene", "If", "Merisier",
         "Noisetier", "Noyer", "Tremble", "Oliviolet", "Ebene", "Charme", "Bambou", 
         "Pin", "Bambou_sombre", "Kalyptus", "Orme","Bambou_sacre", "Aquajou"]

        if  ressource == "monstre":
            self.pod_available = self.pod_available - 250

        elif ressource in bois:
            self.pod_available = self.pod_available - 5 * random.randint(1,15)
            
        else:
            self.pod_available = self.pod_available - 1 * random.randint(1,15)


    def monster_detected(self):
        """Logique de pause et d'information au joueur qu'un monstre nous a attaqué"""
        self.sound_alert("Monstre détecté")

        self.gui_elements['running_indication'].config(text=f"🟡 Appuyer sur Entrée qaund le combat est terminé pour reprendre le farm")
        keyboard.wait('enter')
        self.gui_elements['running_indication'].config(text="✅ Bot running in Harvest Mode")

        self.add_to_inventory("monstre")


    def sound_alert(self, message) -> None:
        """
        Affiche une boîte de dialogue d'erreur et joue un son d'alarme 
        jusqu'à ce que l'utilisateur appuie sur Entrée
        """
        
        self.gui_elements['running_indication'].config(text=f"⭕ Appuyer sur Entrée pour arréter le son\n {message} ")
        # Créer un événement pour arrêter le thread du son
        stop_event = threading.Event()

        # Créer et démarrer le thread pour le son
        sound_thread = threading.Thread(
            target=self._play_sound_loop,
            args=(stop_event,)
        )
        sound_thread.start()

        print(f"\n\n[ALERT] {message}")
        print("Appuyez sur Entrée pour arrêter l'alarme...")
        
        keyboard.wait('enter')

        # Arrêter le thread du son
        stop_event.set()
        sound_thread.join()

    def _play_sound_loop(self, stop_event):
        """
        Fonction qui joue le son en boucle jusqu'à l'appui sur Entrée
        """
        while not stop_event.is_set():
            winsound.Beep(1000, 500)  # 1000 Hz pendant 500 ms
            time.sleep(0.5)

class BotInterface:
    def __init__(self):
        """Initialise l'interface graphique du bot."""
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("470x900")
        self.root.resizable(True, True)
        
        self.bot = None
        self.setup_gui()
        
    def setup_gui(self) -> None:
        """Configure les éléments de l'interface."""
        # Configuration des classes
        classes = self.get_available_classes()
        self.class_vars = []

        tk.Label(
            self.root,
            text="Recursos para coletar",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=5)

        for original_name, display_name in classes:
            var = tk.StringVar()
            self.class_vars.append(var)

            tk.Checkbutton(
                self.root,
                text=display_name,
                variable=var,
                onvalue=original_name,
                offvalue=""
            ).pack(anchor="w")
        
        # Configuration de la position
        position_frame = tk.Frame(self.root)
        position_frame.pack(pady=5)
        tk.Label(position_frame, text="X:").pack(side=tk.LEFT)
        self.x_entry = tk.Entry(position_frame, width=5)
        self.x_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(position_frame, text="Y:").pack(side=tk.LEFT)
        self.y_entry = tk.Entry(position_frame, width=5)
        self.y_entry.pack(side=tk.LEFT, padx=5)
        
        # Sélection de la carte
        tk.Label(
            self.root,
            text="Mapa",
            font=("Segoe UI", 10, "bold")
        ).pack()
        self.map_var = tk.StringVar(value="Incarnam")
        tk.OptionMenu(self.root, self.map_var, "Incarnam", "Astrub").pack()

        # Configuration de la zone de restriction
        tk.Label(
            self.root,
            text="Área permitida para o bot",
            font=("Segoe UI", 10, "bold")
        ).pack(pady=5)
        restriction_frame1 = tk.Frame(self.root)
        restriction_frame1.pack(pady=5)
        tk.Label(restriction_frame1, text="Canto superior esquerdo - X:").pack(side=tk.LEFT)
        self.restrict_x1_entry = tk.Entry(restriction_frame1, width=5)
        self.restrict_x1_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(restriction_frame1, text="Y:").pack(side=tk.LEFT)
        self.restrict_y1_entry = tk.Entry(restriction_frame1, width=5)
        self.restrict_y1_entry.pack(side=tk.LEFT, padx=5)

        restriction_frame2 = tk.Frame(self.root)
        restriction_frame2.pack(pady=5)
        tk.Label(restriction_frame2, text="Canto inferior direito - X:").pack(side=tk.LEFT)
        self.restrict_x2_entry = tk.Entry(restriction_frame2, width=5)
        self.restrict_x2_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(restriction_frame2, text="Y:").pack(side=tk.LEFT)
        self.restrict_y2_entry = tk.Entry(restriction_frame2, width=5)
        self.restrict_y2_entry.pack(side=tk.LEFT, padx=5)
        
        # Configuration des pods
        pod_frame = tk.Frame(self.root)
        pod_frame.pack(pady=5)
        tk.Label(pod_frame, text="Pods usados:").pack(side=tk.LEFT)
        self.pod_used_var = tk.Entry(pod_frame, width=5)
        self.pod_used_var.pack(side=tk.LEFT, padx=5)
        tk.Label(pod_frame, text="Pod max:").pack(side=tk.LEFT)
        self.pod_max_var = tk.Entry(pod_frame, width=5)
        self.pod_max_var.pack(side=tk.LEFT, padx=5)
        
        # ---------------- BOTÕES ----------------

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        self.start_button = tk.Button(
            button_frame,
            text="▶ Iniciar",
            width=12,
            command=self.start_bot
        )
        self.start_button.grid(row=0, column=0, padx=3)

        self.pause_button = tk.Button(
            button_frame,
            text="⏸ Pausar",
            width=12,
            state="disabled"
        )
        self.pause_button.grid(row=0, column=1, padx=3)

        self.stop_button = tk.Button(
            button_frame,
            text="⏹ Parar",
            width=12,
            command=self.stop_bot,
            state="disabled"
        )
        self.stop_button.grid(row=0, column=2, padx=3)

        # ---------------- STATUS ----------------

        self.running_indication = tk.Label(
            self.root,
            text="⚪ Bot parado",
            font=("Segoe UI", 10, "bold")
        )
        self.running_indication.pack(pady=10)

        self.coord_indication = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 10)
        )
        self.coord_indication.pack()

        # Atalho antigo
        keyboard.add_hotkey('*', self.stop_bot)
    
    def get_available_classes(self):
        """Retorna os recursos disponíveis e seus nomes em português."""

        model = YOLO("my_model.pt")

        traducoes = {
            "Ble": "Trigo",
            "Bombu": "Bombu",
            "Chataigner": "Castanheiro",
            "Chene": "Carvalho",
            "Eau": "Água (Pesca)",
            "Erable": "Bordo",
            "Frene": "Freixo",
            "If": "Teixo",
            "Menthe": "Hortelã",
            "Merisier": "Cerejeira",
            "Noisetier": "Aveleira",
            "Noyer": "Nogueira",
            "Ortie": "Urtiga",
            "Sauge": "Sálvia",
            "Trefle": "Trevo"
        }

        return [
            (nome_original, traducoes.get(nome_original, nome_original))
            for nome_original in model.names.values()
        ]
    
    def validate_inputs(self) -> Tuple[bool, str]:
        """Valide les entrées de l'utilisateur."""
        selected_classes = [var.get() for var in self.class_vars if var.get()]
        if not selected_classes:
            return False, "Sélectionnez au moins une classe."
            
        try:
            x_pos = int(self.x_entry.get())
            y_pos = int(self.y_entry.get())
            x1 = int(self.restrict_x1_entry.get())
            y1 = int(self.restrict_y1_entry.get())
            x2 = int(self.restrict_x2_entry.get())
            y2 = int(self.restrict_y2_entry.get())
            pod_max = int(self.pod_max_var.get())
            pod_used = int(self.pod_used_var.get())
                
        except ValueError:
            return False, "Les coordonnées et pods doivent être des nombres entiers."
            
        if x1 >= x2 or y1 >= y2:
            return False, "Les coordonnées de la zone de restriction sont invalides."

        if pod_used >= pod_max:
            return False, "Les pods sont pleins."
            
        return True, ""
    
    def start_bot(self) -> None:
        """Démarre le bot avec la configuration actuelle."""
        valid, error_message = self.validate_inputs()
        if not valid:
            messagebox.showerror("Erreur", error_message)
            return
            
        selected_classes = [var.get() for var in self.class_vars if var.get()]
        initial_position = (int(self.x_entry.get()), int(self.y_entry.get()))
        pod_available = int(self.pod_max_var.get()) - int(self.pod_used_var.get())

        restriction_zone = {
            'x1': int(self.restrict_x1_entry.get()),
            'y1': int(self.restrict_y1_entry.get()),
            'x2': int(self.restrict_x2_entry.get()),
            'y2': int(self.restrict_y2_entry.get())
        }
        
        self.bot = HarvestBot(
            map_name=self.map_var.get(),
            selected_classes=selected_classes,
            initial_position=initial_position,
            pod_available=pod_available,
            restriction_zone=restriction_zone
        )
        
        bot_thread = threading.Thread(
            target=self.bot.start,
            args=(self.running_indication, self.coord_indication),
            daemon=True
        )
        bot_thread.start()


    def stop_bot(self) -> None:
        """Arrête le bot et met à jour l'indication."""
        if self.bot:
            self.bot.stop()
            self.running_indication.config(text="⭕ Bot offline")
            messagebox.showinfo("Info", "Bot arrêté.")



if __name__ == "__main__":
    interface = BotInterface()
    interface.root.mainloop()
