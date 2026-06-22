class Detector:

    def __init__(self, model):
        self.model = model

    def process_detections(self, img_path: str) -> List[Tuple[int, int]]:
        """Processa as detecções do YOLO e retorna os recursos encontrados."""
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
                    
                    if class_name in selected_classes:
                        x1, y1, x2, y2 = box.tolist()
                        center_x = int((x1 + x2) / 2 + random.gauss(0, (x2 - x1) * 0.1))
                        center_y = int((y1 + y2) / 2 + random.gauss(0, (y2 - y1) * 0.1))

                        # Vérification que le point est bien dans l'espace de farm (c'est à dire pas sur les côtés)
                        if is_point_in_farm(center_x, center_y):
                            detections.append((class_name, center_x, center_y))
        
        # Mise à jour des ressources dans la carte
        return detections, class_counts
