import re
import logging

logger = logging.getLogger(__name__)


class GuideParser:
    """
    Analyse sémantique des étapes.
    STRICT : La destination est extraite UNIQUEMENT du texte (web_text).
    """

    # --- CONSTANTES ---
    TARGET_COLORS = ["rgb(98, 172, 255)", "#62ACFF", "#62acff"]
    BLACKLIST_CONTEXT = ["départ", "depuis", "partir", "commencer"]

    # Coordonnées déclenchant une potion spécifique (Priorité absolue - Mode Direct)
    SPECIAL_POTION_DESTINATIONS = {
        (-32, -57): "potion_bonta",
        (-25, 33): "potion_brakmar"
    }

    # Centres des villes pour déduction contextuelle
    CITY_CENTERS = {
        "Bonta": (-31, -56),
        "Brakmar": (-26, 37),
        # On garde les coords pour info, mais elles ne déclencheront pas de potion
        "Frigost": (-78, -41),
        "Sufokia": (13, 26)
    }

    # Seules ces villes ont une potion d'optimisation
    OPTIMIZED_CITIES = ["Bonta", "Brakmar"]

    CITY_POTION_COMMANDS = {
        "Bonta": "potion_bonta",
        "Brakmar": "potion_brakmar"
    }

    def parse_step(self, step_data: dict) -> dict:
        """
        Analyse une étape et retourne un dictionnaire d'actions structuré.
        """
        raw_html = step_data.get('web_text', '')
        clean_text = self._clean_html(raw_html)

        result = {
            "position": None,
            "travel_cmd": None,
            "macro_type": "classic",
            "macro_arg": None,
            "macro_arg2": None
        }

        # 1. Extraction Position (STRICTEMENT depuis le texte)
        result["position"] = self._extract_position(clean_text)

        if result["position"]:
            result["travel_cmd"] = f"/travel {result['position'][0]},{result['position'][1]}"

        # 2. Vérification Potion Directe (Cas Spécial sur position trouvée)
        if result["position"] and result["position"] in self.SPECIAL_POTION_DESTINATIONS:
            potion_cmd = self.SPECIAL_POTION_DESTINATIONS[result["position"]]
            result["travel_cmd"] = potion_cmd  # Sera traité comme raccourci clavier
            result["macro_type"] = "potion_direct"
            return result

        # 3. Analyse Séquentielle Zaap / Zaapi
        blue_items = self._get_blue_spans_raw(raw_html)
        final_zaap, final_zaapi = self._extract_transport_entities(blue_items)

        # 4. Déduction Ville
        inferred_city = self._infer_closest_city(result["position"])

        # --- ARBRE DE DÉCISION ---

        # CAS A : Optimisation Bonta/Brakmar UNIQUEMENT
        if final_zaapi and inferred_city in self.OPTIMIZED_CITIES:
            potion_cmd = self.CITY_POTION_COMMANDS.get(inferred_city)
            result["macro_type"] = "potion_zaapi"
            result["macro_arg"] = final_zaapi  # Nom du Zaapi
            result["macro_arg2"] = potion_cmd  # Potion à utiliser (bonta/brakmar)

        # CAS B : Zaapi standard (Frigost, Sufokia, etc.)
        elif final_zaapi:
            # Pas d'opti potion -> On utilisera la méthode H -> Zaap
            result["macro_type"] = "zaapi"
            result["macro_arg"] = final_zaapi

        # CAS C : Zaap Classique
        elif final_zaap:
            result["macro_type"] = "zaap"
            result["macro_arg"] = final_zaap

        return result

    def _extract_position(self, clean_text):
        matches = re.findall(r'\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]', clean_text)
        if matches:
            last = matches[-1]
            return (int(last[0]), int(last[1]))
        return None

    def _extract_transport_entities(self, blue_items):
        final_zaap = None
        final_zaapi = None
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
                if any(bad in context for bad in self.BLACKLIST_CONTEXT):
                    continue
                param = re.sub(r'zaapi?', '', text, flags=re.IGNORECASE).strip()
                if not param and i + 1 < len(blue_items):
                    param = blue_items[i + 1]['text']
                    skip_next = True
                if param:
                    potential_actions.append({"type": cmd_type, "name": param})

        for action in potential_actions:
            if action['type'] == 'zaap':
                final_zaap = action['name']
            elif action['type'] == 'zaapi':
                final_zaapi = action['name']

        return final_zaap, final_zaapi

    def _infer_closest_city(self, pos):
        if not pos: return None
        dest_x, dest_y = pos
        min_dist = float('inf')
        inferred_city = None

        for city, (cx, cy) in self.CITY_CENTERS.items():
            dist = (dest_x - cx) ** 2 + (dest_y - cy) ** 2
            if dist < min_dist:
                min_dist = dist
                inferred_city = city
        return inferred_city

    def _get_blue_spans_raw(self, html: str):
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

    def _clean_html(self, html):
        text = re.sub(r'<[^>]+>', ' ', html)
        return re.sub(r'\s+', ' ', text).strip()