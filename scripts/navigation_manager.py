import time
import logging

logger = logging.getLogger(__name__)


class NavigationManager:
    def __init__(self, context):
        self.ctx = context  # Accès au GameContext (keyboard, mouse, window)

        # --- CONFIGURATION ---

        # Coordonnées des centres villes (pour find_closest_city)
        self.CITY_CENTERS = {
            "Bonta": (-31, -56),
            "Brakmar": (-26, 37),
            "Frigost": (-78, -41),
            "Sufokia": (13, 26)
        }

        # Coordonnées des objets Zaapi interactifs (post-potion/zaap)
        self.ZAAPI_INTERACT_COORDS = {
            "Bonta": (790, 448),
            "Brakmar": (1216, 405),
            "Sufokia": (589, 908),
            "Frigost": (1039, 173)
        }

        # --- TIMINGS DE MARCHE (CRUCIAL) ---
        # Temps d'attente après avoir cliqué sur le Zaapi, le temps que le perso marche et que l'interface s'ouvre.
        self.ZAAPI_WALK_TIMINGS = {
            "Bonta": 1.2,  # Potion -> Atelier
            "Brakmar": 1.8,  # Potion -> Atelier
            "Sufokia": 2.0,  # Zaap -> Atelier
            "Frigost": 1.5  # Zaap -> Atelier
        }

    # --- MÉTHODES DE BASE ---

    def auto_travel(self, position_str):
        """Ouvre le chat, écrit /travel x,y et valide."""
        if not position_str: return
        logger.info(f"🚀 Auto-Travel vers : {position_str}")
        self.ctx.keyboard.press_space()
        time.sleep(0.1)
        self.ctx.keyboard.send_text(f"/travel {position_str}")
        time.sleep(0.1)
        self.ctx.keyboard.press_enter()
        time.sleep(0.3)
        self.ctx.keyboard.press_enter()

    def use_bonta_potion(self):
        """Raccourci Potion Bonta (touche '-')"""
        logger.info("🧪 Potion Bonta")
        for _ in range(3):
            self.ctx.keyboard.press_key(0xBD)  # VK_OEM_MINUS
            time.sleep(0.15)

    def use_brakmar_potion(self):
        """Raccourci Potion Brakmar (touche '=')"""
        logger.info("🧪 Potion Brakmar")
        for _ in range(3):
            self.ctx.keyboard.press_key(0xBB)  # VK_OEM_PLUS
            time.sleep(0.15)

    def go_to_havre_sac(self):
        """Entre dans le Havre-Sac (touche 'H')"""
        logger.info("🏠 Go Havre-Sac")
        self.ctx.keyboard.press_key(0x48)  # Touche H
        time.sleep(1.7)

        # --- GESTION ZAAP ---

    def zaap(self, zaap_name):
        """Séquence complète Zaap depuis le Havre-Sac."""
        logger.info(f"⚡ Zaap vers : {zaap_name}")
        self.go_to_havre_sac()

        self.ctx.mouse.click_at(719, 497)  # Clic Zaap HS
        time.sleep(0.3)

        self.ctx.keyboard.send_text(zaap_name)
        time.sleep(0.3)
        self.ctx.keyboard.press_enter()

    # --- GESTION ZAAPI ---

    def zaapi_from(self, city):
        """
        Clique sur l'élément interactif Zaapi.
        Utilise le dictionnaire ZAAPI_WALK_TIMINGS pour gérer les délais spécifiques.
        """
        coords = self.ZAAPI_INTERACT_COORDS.get(city)
        if coords:
            logger.info(f"📍 Clic Zaapi physique à {city} {coords}")
            self.ctx.mouse.click_at(*coords)

            # Récupération du délai spécifique ou 2.0s par défaut
            delay = self.ZAAPI_WALK_TIMINGS.get(city, 2.0)
            logger.info(f"⏳ Marche vers Zaapi ({city}) : {delay}s...")
            time.sleep(delay)
        else:
            logger.warning(f"⚠️ Pas de coordonnées Zaapi connues pour : {city}")

    def use_zaapi_interface(self, zaapi_name):
        """
        Gère l'interface Zaapi UNE FOIS OUVERTE.
        """
        if not zaapi_name: return
        logger.info(f"⚙️ Interface Zaapi -> Recherche : {zaapi_name}")

        name_lower = zaapi_name.lower()

        # 1. Filtres Catégories
        if "atelier" in name_lower:
            self.ctx.mouse.click_at(1111, 468)
        elif "hôtel" in name_lower or "hotel" in name_lower:
            self.ctx.mouse.click_at(1286, 468)
        else:
            self.ctx.mouse.click_at(1456, 468)  # Divers

        time.sleep(0.3)

        # 2. Clic Recherche (Loupe)
        self.ctx.mouse.click_at(1008, 529)
        time.sleep(0.2)

        # 3. Saisie et Validation
        self.ctx.keyboard.send_text(zaapi_name)
        time.sleep(0.3)
        self.ctx.keyboard.press_enter()

    # --- UTILITAIRE ---

    def find_closest_city(self, next_pos_tuple):
        """Trouve la ville la plus proche des coordonnées cibles."""
        if not next_pos_tuple: return None
        target_x, target_y = next_pos_tuple
        min_dist = float('inf')
        closest_city = None

        for city, (cx, cy) in self.CITY_CENTERS.items():
            dist = (target_x - cx) ** 2 + (target_y - cy) ** 2
            if dist < min_dist:
                min_dist = dist
                closest_city = city
        return closest_city