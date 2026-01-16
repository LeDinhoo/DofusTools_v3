import re
import logging

logger = logging.getLogger(__name__)


class GuideParser:
    """
    Classe responsable de l'analyse sémantique des étapes de guides (Ganymède).
    Elle extrait :
    1. La position destination [x,y]
    2. Les commandes de transport (Zaap, Zaapi, Potion) avec optimisation.
    3. Les entités interactives (PNJ, Monstres).
    """

    # --- CONSTANTES DE PARSING ---

    # Couleurs indiquant une instruction interactive (Bleu Ganymède)
    TARGET_COLORS = ["rgb(98, 172, 255)", "#62ACFF", "#62acff"]

    # Mots-clés de contexte à ignorer (Indiquent un point de départ et non une destination)
    BLACKLIST_CONTEXT = ["départ", "depuis", "partir", "commencer"]

    # Coordonnées exactes déclenchant une potion spécifique (Priorité absolue)
    SPECIAL_POTION_DESTINATIONS = {
        (-32, -57): "potion_bonta",
        (-25, 33): "potion_brakmar"
    }

    # Centres des villes pour déduction contextuelle (si Zaapi sans Zaap)
    CITY_CENTERS = {
        "Bonta": (-31, -56),
        "Frigost": (-78, -41),
        "Brakmar": (-26, 37),
        "Sufokia": (13, 26)
    }

    # Commandes de potion associées aux villes
    CITY_POTION_COMMANDS = {
        "Bonta": "potion_bonta",
        "Brakmar": "potion_brakmar",
        "Frigost": "potion_frigost",
        "Sufokia": "potion_sufokia"
    }

    def parse_step(self, step_data: dict) -> dict:
        """
        Analyse une étape brute (dict JSON) et retourne les actions structurées.
        """
        raw_html = step_data.get('web_text', '')

        # Structure de résultat par défaut
        result = {
            "position": None,  # Tuple (x, y)
            "travel": None,  # Dict action (voir ci-dessous)
            "targets": {  # Entités pour l'OCR / Interaction
                "npcs": [],
                "monsters": [],
                "items": []
            }
        }

        # 1. Extraction Position
        result["position"] = self._extract_position(raw_html, step_data)

        # 2. Vérification Potion Directe (Cas Spécial)
        if result["position"] in self.SPECIAL_POTION_DESTINATIONS:
            result["travel"] = {
                "type": "potion",
                "command": self.SPECIAL_POTION_DESTINATIONS[result["position"]]
            }
            # On s'arrête là pour le voyage (pas besoin de chercher Zaap)
            self._extract_entities(raw_html, result)  # On récupère quand même les PNJ
            return result

        # 3. Analyse Zaap / Zaapi
        result["travel"] = self._analyze_travel_logic(raw_html, result["position"])

        # 4. Extraction Entités (PNJ, Monstres...)
        self._extract_entities(raw_html, result)

        return result

    def _extract_position(self, html: str, step_data: dict):
        """Récupère la DERNIÈRE position [x,y] du texte, sinon fallback sur le JSON."""
        # Nettoyage
        text = re.sub(r'<[^>]+>', ' ', html)
        clean_text = re.sub(r'\s+', ' ', text).strip()

        # Regex [x,y]
        matches = re.findall(r'\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]', clean_text)
        if matches:
            last = matches[-1]
            return (int(last[0]), int(last[1]))

        # Fallback JSON
        jx, jy = step_data.get('pos_x'), step_data.get('pos_y')
        if jx is not None and jy is not None and (jx != 0 or jy != 0):
            return (jx, jy)

        return None

    def _analyze_travel_logic(self, html: str, dest_pos: tuple):
        """Logique complexe de déduction du transport (Zaap, Zaapi, Potion, Optimisation)."""

        # 1. Extraction séquentielle brute des spans bleus
        blue_items = self._get_blue_spans_raw(html)

        # 2. Filtrage et identification Zaap/Zaapi
        potential_actions = []
        skip_next = False

        for i, item in enumerate(blue_items):
            if skip_next:
                skip_next = False
                continue

            text = item['text']
            context = item['context']
            lower_text = text.lower()

            cmd_type = None
            if "zaapi" in lower_text:
                cmd_type = "zaapi"
            elif "zaap" in lower_text:
                cmd_type = "zaap"

            if cmd_type:
                # Ignorer si contexte de départ ("Depuis le Zaap...")
                if any(bad in context for bad in self.BLACKLIST_CONTEXT):
                    continue

                # Chercher le nom (Paramètre)
                # Soit dans le texte même ("Zaap Village")
                param = re.sub(r'zaapi?', '', text, flags=re.IGNORECASE).strip()

                # Soit dans le span suivant ("Zaap" ... "Village")
                if not param and i + 1 < len(blue_items):
                    param = blue_items[i + 1]['text']
                    skip_next = True

                if param:
                    potential_actions.append({"type": cmd_type, "name": param})

        # 3. Consolidation (Dernier Zaap / Dernier Zaapi valides)
        final_zaap = None
        final_zaapi = None
        for action in potential_actions:
            if action['type'] == 'zaap':
                final_zaap = action['name']
            elif action['type'] == 'zaapi':
                final_zaapi = action['name']

        # 4. Déduction et Optimisation

        # Calcul ville proche (si coords dispo)
        inferred_city = None
        if dest_pos:
            dx, dy = dest_pos
            min_dist = float('inf')
            for city, (cx, cy) in self.CITY_CENTERS.items():
                dist = (dx - cx) ** 2 + (dy - cy) ** 2
                if dist < min_dist:
                    min_dist = dist
                    inferred_city = city

        # --- ARBRE DE DÉCISION ---

        # CAS A : Optimisation Bonta/Brakmar (Zaapi présent + Ville Bonta/Brakmar)
        # On remplace le Zaap par la Potion de cité
        if final_zaapi and inferred_city in ["Bonta", "Brakmar"]:
            return {
                "type": "potion_zaapi",
                "potion_cmd": self.CITY_POTION_COMMANDS.get(inferred_city),
                "zaapi_name": final_zaapi,
                "reason": f"Optimisation {inferred_city}"
            }

        # CAS B : Zaapi sans Zaap (Frigost, Sufokia, etc.)
        # On déduit la ville et on prend la potion
        if final_zaapi and not final_zaap:
            if inferred_city:
                return {
                    "type": "potion_zaapi",
                    "potion_cmd": self.CITY_POTION_COMMANDS.get(inferred_city),
                    "zaapi_name": final_zaapi,
                    "reason": "Zaapi sans Zaap (Déduction)"
                }
            else:
                # Fallback : on retourne juste le Zaapi (l'utilisateur devra se débrouiller pour y aller)
                return {"type": "zaapi", "name": final_zaapi}

        # CAS C : Zaap Classique (+ Zaapi optionnel)
        if final_zaap:
            if final_zaapi:
                return {
                    "type": "zaap_zaapi",
                    "zaap_name": final_zaap,
                    "zaapi_name": final_zaapi
                }
            else:
                return {
                    "type": "zaap",
                    "name": final_zaap
                }

        # CAS D : Zaapi seul non résolu (rare)
        if final_zaapi:
            return {"type": "zaapi", "name": final_zaapi}

        return None  # Aucun transport détecté

    def _get_blue_spans_raw(self, html: str):
        """Extrait les spans de couleur cible avec leur contexte (50 chars avant)."""
        items = []
        span_pattern = re.compile(r'<span[^>]*style="([^"]*)"[^>]*>(.*?)</span>', re.IGNORECASE | re.DOTALL)

        for match in span_pattern.finditer(html):
            style_attr = match.group(1).lower()
            content = match.group(2).strip()
            start_pos = match.start()

            if not any(c.lower() in style_attr for c in self.TARGET_COLORS):
                continue

            clean_text = re.sub(r'<[^>]+>', '', content).strip()
            if not clean_text: continue

            context = html[max(0, start_pos - 50): start_pos].lower()
            items.append({"text": clean_text, "context": context})

        return items

    def _extract_entities(self, html: str, result_dict: dict):
        """Extrait PNJ, Monstres et Items via classes CSS."""

        def get_content(cls):
            raw = re.findall(rf'class="[^"]*{cls}[^"]*"[^>]*>(.*?)</span>', html)
            return [re.sub(r'<[^>]+>', '', r).strip() for r in raw]

        result_dict["targets"]["npcs"] = get_content("tag-npc")
        result_dict["targets"]["monsters"] = get_content("tag-monster")
        result_dict["targets"]["items"] = get_content("tag-item")