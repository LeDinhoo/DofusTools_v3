import requests
import logging
import json

logger = logging.getLogger(__name__)


class NetworkFeatures:
    def __init__(self):
        # Utilisation d'une session pour garder les connexions actives (Keep-Alive)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python-Automation-Hub/3.0'
        })
        self.base_url = "https://ganymede-app.com"

    def fetch_guide_data(self, guide_id):
        """
        Télécharge le JSON d'un guide depuis Ganymede via requests.
        Retourne (data, error_message).
        """
        url = f"{self.base_url}/guides/{guide_id}/export"
        logger.info(f"Réseau : Téléchargement du guide {guide_id}...")

        try:
            # Timeout de 10s pour la connexion et la lecture
            response = self.session.get(url, timeout=10)

            # Lève une exception si le code HTTP est 4xx ou 5xx
            response.raise_for_status()

            try:
                data = response.json()
                logger.info(f"Réseau : Guide {guide_id} téléchargé avec succès.")
                return data, None
            except json.JSONDecodeError:
                err = "Le serveur a renvoyé des données invalides (pas du JSON)."
                logger.error(f"Réseau : {err}")
                return None, err

        except requests.exceptions.HTTPError as e:
            err = f"Erreur HTTP : {e.response.status_code} - {e.response.reason}"
            logger.error(f"Réseau : {err}")
            return None, err
        except requests.exceptions.ConnectionError:
            err = "Impossible de joindre le serveur (Problème de connexion)."
            logger.warning(f"Réseau : {err}")
            return None, err
        except requests.exceptions.Timeout:
            err = "Le serveur met trop de temps à répondre (Timeout)."
            logger.warning(f"Réseau : {err}")
            return None, err
        except Exception as e:
            err = f"Erreur inattendue : {str(e)}"
            logger.critical(f"Réseau : {err}")
            return None, err