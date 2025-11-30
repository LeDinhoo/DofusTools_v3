import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

class NetworkFeatures:
    def __init__(self):
        # Plus de dépendance logger_func
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python-Automation-Hub'

    def fetch_guide_data(self, guide_id):
        """
        Télécharge le JSON d'un guide depuis Ganymede.
        Retourne (data, error_message).
        """
        url = f"https://ganymede-app.com/guides/{guide_id}/export"
        logger.info(f"Réseau : Téléchargement du guide {guide_id}...")

        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
            # Timeout de 10s pour éviter de geler l'app trop longtemps si le serveur rame
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    try:
                        raw_data = response.read().decode('utf-8')
                        data = json.loads(raw_data)
                        logger.info(f"Réseau : Guide {guide_id} téléchargé avec succès.")
                        return data, None
                    except json.JSONDecodeError:
                        err = "Le serveur a renvoyé des données invalides (pas du JSON)."
                        logger.error(f"Réseau : {err}")
                        return None, err
                else:
                    err = f"Erreur serveur (Code: {response.status})"
                    logger.error(f"Réseau : {err}")
                    return None, err

        except urllib.error.URLError as e:
            err = f"Impossible de joindre le serveur ({e.reason})"
            logger.warning(f"Réseau : {err}")
            return None, err
        except Exception as e:
            err = f"Erreur inattendue : {str(e)}"
            logger.critical(f"Réseau : {err}")
            return None, err