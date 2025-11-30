import urllib.request
import json


class NetworkFeatures:
    def __init__(self, logger_func):
        self.log = logger_func
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python-Automation-Hub'

    def fetch_guide_data(self, guide_id):
        """
        Télécharge le JSON d'un guide depuis Ganymede.
        Retourne (data, error_message).
        """
        url = f"https://ganymede-app.com/guides/{guide_id}/export"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
            # Timeout de 10s pour éviter de geler l'app trop longtemps si le serveur rame
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    try:
                        raw_data = response.read().decode('utf-8')
                        data = json.loads(raw_data)
                        return data, None
                    except json.JSONDecodeError:
                        return None, "Le serveur a renvoyé des données invalides (pas du JSON)."
                else:
                    return None, f"Erreur serveur (Code: {response.status})"

        except urllib.error.URLError as e:
            return None, f"Impossible de joindre le serveur ({e.reason})"
        except Exception as e:
            return None, f"Erreur inattendue : {str(e)}"