import os
import re
import sys
import json
from scripts.parser_features import ParserScripts

# --- CONFIGURATION ---
GUIDE_PATH = "guides/516.json"
TARGET_STEP_INDEX = 49

# Couleurs cibles (Bleu Ganymède)
TARGET_COLORS = ["rgb(98, 172, 255)", "#62ACFF", "#62acff"]

# Contexte à ignorer
BLACKLIST_CONTEXT = ["départ", "depuis", "partir", "commencer"]

# 1. Coordonnées Spéciales -> Commande Directe
# Si la destination finale est exactement l'une de ces coordonnées, on utilise la potion.
SPECIAL_POTION_DESTINATIONS = {
    (-32, -57): "potion_bonta",
    (-25, 33): "potion_brakmar"
}

# 2. Centres des villes pour déduction (Calcul de distance)
CITY_CENTERS = {
    "Bonta": (-31, -56),
    "Frigost": (-78, -41),
    "Brakmar": (-26, 37),
    "Sufokia": (13, 26)
}

# Mapping Ville -> Commande Potion (pour le combo Potion + Zaapi)
CITY_POTION_COMMANDS = {
    "Bonta": "potion_bonta",
    "Brakmar": "potion_brakmar",
    "Frigost": "potion_frigost",  # A vérifier si tu as cette commande
    "Sufokia": "potion_sufokia"  # A vérifier si tu as cette commande
}


def clean_html_markup(html_content):
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_blue_spans_raw(html_content):
    items = []
    span_pattern = re.compile(r'<span[^>]*style="([^"]*)"[^>]*>(.*?)</span>', re.IGNORECASE | re.DOTALL)

    for match in span_pattern.finditer(html_content):
        style_attr = match.group(1).lower()
        content = match.group(2).strip()
        start_pos = match.start()

        if not any(c.lower() in style_attr for c in TARGET_COLORS):
            continue

        clean_text = re.sub(r'<[^>]+>', '', content).strip()
        if not clean_text: continue

        context = html_content[max(0, start_pos - 50): start_pos].lower()

        items.append({
            "text": clean_text,
            "context": context
        })
    return items


def analyze_step(step_data, index):
    step_id = step_data.get('id')
    print("=" * 80)
    print(f"🔬 ANALYSE ÉTAPE #{index} (ID : {step_id})")
    print("=" * 80)

    raw_html = step_data.get('web_text', '')

    # --- 1. RÉCUPÉRATION POSITION ---
    final_pos = None
    clean_text = clean_html_markup(raw_html)
    coords_matches = re.findall(r'\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]', clean_text)
    if coords_matches:
        last = coords_matches[-1]
        final_pos = (int(last[0]), int(last[1]))
        print(f"📍 POSITION DÉTECTÉE : [{final_pos[0]}, {final_pos[1]}]")
    else:
        print(f"📍 POSITION DÉTECTÉE : Aucune")

    # --- 2. VÉRIFICATION PRIORITAIRE : POTION DIRECTE ---
    # Si la destination est EXACTEMENT une case de potion, on s'arrête là.
    if final_pos and final_pos in SPECIAL_POTION_DESTINATIONS:
        cmd = SPECIAL_POTION_DESTINATIONS[final_pos]
        print("-" * 80)
        print(f"⚡ CAS SPÉCIAL DÉTECTÉ (Coordonnées {final_pos})")
        print(f"🚀 COMMANDE FINALE : {cmd}")
        print("=" * 80)
        return  # On sort, pas besoin d'analyser Zaap/Zaapi si on y va en potion directe

    # --- 3. ANALYSE ZAAP / ZAAPI ---
    print("\n🔍 Analyse Séquentielle (Zaap/Zaapi) :")
    raw_spans = get_blue_spans_raw(raw_html)
    potential_actions = []
    skip_next = False

    for i, item in enumerate(raw_spans):
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
            is_ignored = any(bad in context for bad in BLACKLIST_CONTEXT)

            param_candidate = re.sub(r'zaapi?', '', text, flags=re.IGNORECASE).strip()
            if not param_candidate and i + 1 < len(raw_spans):
                param_candidate = raw_spans[i + 1]['text']
                skip_next = True

            if param_candidate and not is_ignored:
                potential_actions.append({"cmd": cmd_type, "arg": param_candidate})
                print(f"   - Trouvé : {cmd_type} -> {param_candidate}")

    # Récupération des dernières actions valides
    final_zaap = None
    final_zaapi = None
    for action in potential_actions:
        if action['cmd'] == 'zaap':
            final_zaap = action['arg']
        elif action['cmd'] == 'zaapi':
            final_zaapi = action['arg']

    print("-" * 80)

    # --- 4. DÉDUCTION & GÉNÉRATION COMMANDES ---

    # Calcul systématique de la ville la plus proche (pour décision)
    inferred_city = None
    if final_pos:
        dest_x, dest_y = final_pos
        min_dist = float('inf')
        for city, (cx, cy) in CITY_CENTERS.items():
            dist = (dest_x - cx) ** 2 + (dest_y - cy) ** 2
            if dist < min_dist:
                min_dist = dist
                inferred_city = city

    # CAS A : Optimisation BONTA / BRAKMAR
    # Si Zaapi présent + Ville est Bonta/Brakmar -> ON FORCE LA POTION (On ignore le Zaap)
    if final_zaapi and inferred_city in ["Bonta", "Brakmar"]:
        print(f"⚡ OPTIMISATION {inferred_city.upper()} : Remplacement Zaap par Potion.")
        potion_cmd = CITY_POTION_COMMANDS.get(inferred_city, "potion_unknown")
        print(f"🚀 COMMANDE 1 : {potion_cmd}")
        print(f"🚀 COMMANDE 2 : zaapi")
        print(f"📦 PARAMÈTRE 2: \"{final_zaapi}\"")

    # CAS B : Zaapi sans Zaap (Pour Sufokia/Frigost... ou si Bonta/Brakmar a échappé au cas A)
    # Le guide ne donne pas de Zaap, on déduit la ville et on prend la potion.
    elif final_zaapi and not final_zaap:
        print("🤔 Zaapi sans Zaap détecté -> Déduction Potion...")
        if inferred_city:
            potion_cmd = CITY_POTION_COMMANDS.get(inferred_city, "potion_unknown")
            print(f"   -> Ville la plus proche : {inferred_city}")
            print(f"🚀 COMMANDE 1 : {potion_cmd}")
            print(f"🚀 COMMANDE 2 : zaapi")
            print(f"📦 PARAMÈTRE 2: \"{final_zaapi}\"")
        else:
            print("⚠️ Impossible de déduire la ville (Pas de coords proches connues).")

    # CAS C : Comportement Standard (Zaap explicite + Zaapi optionnel)
    # C'est ici que passent Frigost et Sufokia s'il y a un Zaap dans le guide.
    elif final_zaap:
        print(f"🚀 COMMANDE FINALE : zaap")
        print(f"📦 PARAMÈTRE       : \"{final_zaap}\"")
        if final_zaapi:
            print(f"🚀 SUIVI DE        : zaapi")
            print(f"📦 PARAMÈTRE       : \"{final_zaapi}\"")

    # CAS D : Zaapi seul mais ville inconnue
    elif final_zaapi:
        print(f"🚀 COMMANDE FINALE : zaapi")
        print(f"📦 PARAMÈTRE       : \"{final_zaapi}\"")

    else:
        print("⚪ Aucune commande de transport détectée (Marche à pied ?).")

    print("=" * 80)


def main():
    parser = ParserScripts()
    if not os.path.exists(GUIDE_PATH):
        print(f"❌ Fichier {GUIDE_PATH} introuvable.")
        return

    data = parser.load_file(GUIDE_PATH)
    if not data: return

    steps = parser.get_steps_list(data)
    if 0 <= TARGET_STEP_INDEX < len(steps):
        analyze_step(steps[TARGET_STEP_INDEX], TARGET_STEP_INDEX)
    else:
        print(f"⚠️ Index {TARGET_STEP_INDEX} invalide.")


if __name__ == "__main__":
    main()