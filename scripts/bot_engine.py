import time
import logging
from .game_context import GameContext

logger = logging.getLogger(__name__)


class BotEngine:
    """
    Moteur d'exécution du Bot.
    Responsabilité : Recevoir une instruction de haut niveau (ex: "Prendre Zaapi")
    et piloter le GameContext pour la réaliser.
    """

    def __init__(self):
        # Le moteur possède le contexte de jeu (Souris, Clavier, Fenêtre, Navigation)
        self.ctx = GameContext()
        self.is_running = False

    def ensure_ready(self):
        """Vérifie que la fenêtre est liée et focus"""
        if not self.ctx.window.bound_handle:
            logger.warning("⚠️ Action annulée : Aucune fenêtre de jeu liée.")
            return False
        self.ctx.ensure_focus()
        return True

    def run_sequence(self, t_type, arg1, arg2, cmd):
        """
        Exécute une séquence de navigation complète.
        :param t_type: Type de macro ('zaapi', 'zaap', 'potion_zaapi', 'classic')
        :param arg1: Argument principal (Nom du Zaap/Zaapi)
        :param arg2: Contexte ou Ville (ex: 'Sufokia', 'potion_bonta')
        :param cmd: Commande console optionnelle (/travel x,y)
        """
        if not self.ensure_ready(): return

        self.is_running = True
        try:
            # Nettoyage de la commande /travel pour n'avoir que les coordonnées
            clean_cmd_pos = cmd.replace("/travel ", "").strip() if cmd else None

            # --- LOGIQUE DE DÉCISION ---

            # CAS 1 : Potion + Zaapi (Optimisation Bonta/Brakmar explicite)
            if t_type == "potion_zaapi":
                self._sequence_potion_zaapi(potion_type=arg2, zaapi_dest=arg1, final_travel=clean_cmd_pos)

            # CAS 2 : Zaapi Standard (Avec détection intelligente de ville)
            elif t_type == "zaapi":
                self._sequence_smart_zaapi(zaapi_dest=arg1, city_hint=arg2, final_travel=clean_cmd_pos)

            # CAS 3 : Zaap Classique
            elif t_type == "zaap":
                logger.info(f"✨ Macro Zaap -> {arg1}")
                self.ctx.navigation.zaap(arg1)
                if clean_cmd_pos:
                    time.sleep(2.0)
                    self.ctx.navigation.auto_travel(clean_cmd_pos)

            # CAS 4 : Potion Directe
            elif t_type == "potion_direct":
                self._use_potion_by_name(cmd)

            # CAS 5 : Marche à pied (/travel simple sans zaap)
            elif clean_cmd_pos:
                self.ctx.navigation.auto_travel(clean_cmd_pos)

        except Exception as e:
            logger.error(f"❌ Erreur Exécution Bot : {e}", exc_info=True)
        finally:
            self.is_running = False

    # --- SOUS-SEQUENCES (Pour garder le code propre) ---

    def _sequence_potion_zaapi(self, potion_type, zaapi_dest, final_travel):
        """Séquence Potion Bonta/Brakmar -> Zaapi"""
        if potion_type == "potion_bonta":
            self.ctx.navigation.use_bonta_potion()
            time.sleep(2.0)
            self.ctx.navigation.zaapi_from("Bonta")
        elif potion_type == "potion_brakmar":
            self.ctx.navigation.use_brakmar_potion()
            time.sleep(2.0)
            self.ctx.navigation.zaapi_from("Brakmar")

        # Interaction interface
        self.ctx.navigation.use_zaapi_interface(zaapi_dest)

        if final_travel:
            time.sleep(2.0)
            self.ctx.navigation.auto_travel(final_travel)

    def _sequence_smart_zaapi(self, zaapi_dest, city_hint, final_travel):
        """
        Gère le cas complexe : On doit prendre un Zaapi, mais dans quelle ville ?
        Logique Stricte :
        1. Si hint explicite (arg2) -> On prend cette ville.
        2. Si pas de hint mais une destination finale (/travel x,y) -> On calcule la ville la plus proche.
        3. Si ni l'un ni l'autre -> On ne fait RIEN ou on log une erreur (ou fallback Bonta mais on évite).

        Ensuite :
        - Si Ville == Bonta/Brakmar -> Potion.
        - Si Ville == Autre -> Zaap.
        """
        hub_city = None
        known_cities = ["Sufokia", "Frigost", "Brakmar", "Bonta"]

        # ÉTAPE 1 : Recherche explicite dans le hint (arg2)
        if city_hint:
            for city in known_cities:
                if city.lower() in city_hint.lower():
                    hub_city = city
                    break

        # ÉTAPE 2 : Calcul de proximité si pas de hint mais une destination finale
        if not hub_city and final_travel:
            try:
                # final_travel est sous forme "x,y"
                parts = final_travel.split(',')
                if len(parts) == 2:
                    tx, ty = int(parts[0]), int(parts[1])
                    # On utilise la méthode du NavigationManager pour trouver la ville
                    detected_city = self.ctx.navigation.find_closest_city((tx, ty))
                    if detected_city:
                        hub_city = detected_city
                        logger.info(f"📍 Ville la plus proche détectée : {hub_city} (pour cible {tx},{ty})")
            except ValueError:
                logger.warning(f"⚠️ Impossible de parser les coordonnées pour find_closest_city: {final_travel}")

        # ÉTAPE 3 : Fallback Ultime (Bonta) si échec total
        if not hub_city:
            hub_city = "Bonta"
            logger.warning("⚠️ Aucune ville détectée pour le Zaapi, fallback sur Bonta.")

        logger.info(f"✨ Séquence Zaapi via Hub : {hub_city} -> Dest: {zaapi_dest}")

        # ÉTAPE 4 : Exécution du voyage vers le Hub
        if hub_city == "Bonta":
            self.ctx.navigation.use_bonta_potion()
            time.sleep(2.5)  # Temps de tp
        elif hub_city == "Brakmar":
            self.ctx.navigation.use_brakmar_potion()
            time.sleep(2.5)
        else:
            # Cas Sufokia, Frigost, etc. -> On utilise le Zaap
            self.ctx.navigation.zaap(hub_city)
            time.sleep(4.0)  # Temps de chargement après Zaap

        # ÉTAPE 5 : Interaction Zaapi
        self.ctx.navigation.zaapi_from(hub_city)
        self.ctx.navigation.use_zaapi_interface(zaapi_dest)

        if final_travel:
            time.sleep(2.0)
            self.ctx.navigation.auto_travel(final_travel)

    def _use_potion_by_name(self, name):
        if name == "potion_bonta":
            self.ctx.navigation.use_bonta_potion()
        elif name == "potion_brakmar":
            self.ctx.navigation.use_brakmar_potion()