import cv2
import pytesseract
import time
import os
import shutil
import numpy as np
import datetime
import logging
from difflib import SequenceMatcher
from PIL import ImageGrab
import re

logger = logging.getLogger(__name__)


class OcrScripts:
    def __init__(self):
        self.tesseract_cmd = self._find_tesseract()
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            logger.info(f"OCR : Tesseract configuré sur {self.tesseract_cmd}")
        else:
            logger.error("❌ OCR Erreur: Tesseract introuvable.")
        self.save_dir = "ocr_screens"
        self.default_zone = (431, 20, 1703, 1216)

    def _find_tesseract(self):
        path = shutil.which("tesseract")
        if path: return path
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")
        ]
        for p in common_paths:
            if os.path.exists(p): return p
        return None

    def _preprocess(self, img, threshold_value, scale_factor):
        if img is None or img.size == 0:
            return None
        if scale_factor > 1.0:
            h, w = img.shape[:2]
            img = cv2.resize(img, (int(w * scale_factor), int(h * scale_factor)), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        return thresh

    def _clean_text_for_comparison(self, text):
        if not text: return ""
        return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

    def _fuzzy_match(self, target, text, min_ratio=0.95):
        if not target or not text: return False

        # 1. Comparaison standard
        if SequenceMatcher(None, target.lower(), text.lower()).ratio() >= min_ratio: return True

        # 2. Comparaison "Nettoyée" (Ignore espaces/symboles)
        clean_target = self._clean_text_for_comparison(target)
        clean_text = self._clean_text_for_comparison(text)

        if clean_target and clean_text:
            if clean_target in clean_text: return True
            if SequenceMatcher(None, clean_target, clean_text).ratio() >= min_ratio: return True

        return False

    def _run_tesseract(self, img, psm_mode):
        whitelist = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-éèàçùêëïîôö.:' "
        config = f"--psm {psm_mode} -c tessedit_char_whitelist={whitelist}"
        try:
            return pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)
        except Exception as e:
            logger.error(f"Erreur Tesseract (Mode {psm_mode}): {e}")
            return None

    def process_ocr_on_image(self, img_source, threshold_value=150, target_text="Lester", scale_factor=3.0,
                             grayscale=True, binarize=False):
        logger.info(f"OCR Basique : Recherche de '{target_text}' (Zoom: x{scale_factor}, Seuil: {threshold_value})")

        img = None
        if isinstance(img_source, str):
            if not os.path.exists(img_source): return None, None
            img = cv2.imread(img_source)
        else:
            try:
                img = cv2.cvtColor(np.array(img_source), cv2.COLOR_RGB2BGR)
            except:
                return None, None

        if img is None: return None, None

        found_coords = None
        debug_path = None

        try:
            processed = self._preprocess(img, threshold_value, scale_factor)

            if not os.path.exists(self.save_dir): os.makedirs(self.save_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_target = "".join(c for c in target_text if c.isalnum())
            debug_path = os.path.join(self.save_dir,
                                      f"{timestamp}_Basic_x{scale_factor}_T{threshold_value}_{safe_target}.png")
            cv2.imwrite(debug_path, processed)

            data = self._run_tesseract(processed, 11)
            found_coords = self._analyze_ocr_data(data, target_text, scale_factor)

            if not found_coords:
                data_fallback = self._run_tesseract(processed, 3)
                found_coords = self._analyze_ocr_data(data_fallback, target_text, scale_factor)

            if not found_coords:
                raw_words = []
                if data and 'text' in data:
                    raw_words += [t for t in data['text'] if t.strip()]
                full_text_debug = " | ".join(raw_words) if raw_words else "(RIEN DÉTECTÉ)"
                logger.warning(f"❌ Échec. Tesseract a vu : [{full_text_debug}]")

        except Exception as e:
            logger.error(f"❌ OCR Exception : {e}")

        return found_coords, debug_path

    def _analyze_ocr_data(self, data, target_text, scale_factor):
        if not data or 'text' not in data: return None
        n_boxes = len(data['text'])

        # --- NOUVEAU : Reconstitution de la phrase entière ---
        # On crée une liste de mots valides avec leurs indices
        valid_words = []
        for i in range(n_boxes):
            word = data['text'][i].strip()
            if word:
                valid_words.append({'text': word, 'index': i})

        # On reconstruit le texte complet (avec espaces)
        full_text = " ".join([w['text'] for w in valid_words])

        # Si le texte complet contient la cible (en mode fuzzy/clean)
        # On doit maintenant trouver OÙ c'est.
        # Pour simplifier, si on trouve dans le bloc entier, on renvoie le centre du PREMIER mot qui match un morceau de la cible
        # C'est une approximation acceptable.

        # 1. Test mot à mot (comme avant, pour la précision si un mot seul suffit)
        for w in valid_words:
            if self._fuzzy_match(target_text, w['text'], 0.75):
                logger.info(f"✔️ OCR Trouvé (Mot unique): '{w['text']}'")
                i = w['index']
                return self._get_center(data, i, scale_factor)

        # 2. Test global (si la cible est en plusieurs mots "Capitaine Relcora")
        if self._fuzzy_match(target_text, full_text, 0.75):
            logger.info(f"✔️ OCR Trouvé (Phrase complète): '{full_text}'")
            # On essaie de trouver le premier mot de la cible dans la liste pour donner une coordonnée
            # On prend le premier mot de target_text (ex: "Capitaine")
            first_target_word = target_text.split()[0]

            for w in valid_words:
                # On cherche un mot qui ressemble au début de la cible
                if self._fuzzy_match(first_target_word, w['text'], 0.75):
                    return self._get_center(data, w['index'], scale_factor)

            # Si on ne trouve pas le début précis mais que la phrase match, on renvoie le centre du tout premier mot détecté
            if valid_words:
                return self._get_center(data, valid_words[0]['index'], scale_factor)

        return None

    def _get_center(self, data, i, scale_factor):
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        return (int((x + w // 2) / scale_factor), int((y + h // 2) / scale_factor))

    def run_ocr_for_key_Z(self, window_manager, keyboard_manager, threshold=150, target="Lester", scale_factor=3.0,
                          zone_rect=None, grayscale=True):
        if not window_manager.bound_handle: return None, None
        try:
            if not window_manager.ensure_focus(): return None, None

            keyboard_manager.send_key_action(0x5A, is_down=True)
            time.sleep(0.1)

            img_pil = None
            abs_x_offset = 0
            abs_y_offset = 0

            bbox = None
            if zone_rect:
                x, y, w, h = zone_rect
                if w > 0 and h > 0:
                    bbox = (x, y, x + w, y + h)
                    abs_x_offset = x
                    abs_y_offset = y
            else:
                if self.default_zone:
                    bbox = self.default_zone
                    abs_x_offset = bbox[0]
                    abs_y_offset = bbox[1]
                else:
                    rect = window_manager.get_window_rect()
                    if rect:
                        bbox = rect
                        abs_x_offset = rect[0]
                        abs_y_offset = rect[1]

            if bbox:
                img_pil = ImageGrab.grab(bbox=bbox)

            keyboard_manager.send_key_action(0x5A, is_down=False)

            if img_pil:
                rel_coords, debug_path = self.process_ocr_on_image(
                    img_pil,
                    threshold_value=threshold,
                    target_text=target,
                    scale_factor=scale_factor
                )

                abs_coords = None
                if rel_coords:
                    abs_coords = (abs_x_offset + rel_coords[0], abs_y_offset + rel_coords[1])

                return abs_coords, debug_path
            else:
                logger.error("Capture d'écran échouée")

        except Exception as e:
            logger.critical(f"❌ Erreur Séquence OCR : {e}")
        return None, None

    def run_ocr_on_zone(self, zone_rect, threshold=150, target="Lester", scale_factor=3.0):
        pass