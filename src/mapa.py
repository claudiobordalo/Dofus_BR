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
