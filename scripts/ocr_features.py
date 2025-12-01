import cv2
import pytesseract
import time
import os
import shutil
import numpy as np
import datetime
import logging
import sys
from difflib import SequenceMatcher
from PIL import ImageGrab
import re

logger = logging.getLogger(__name__)


class OcrScripts:
    def __init__(self):
        self.save_dir = "ocr_screens"
        self.default_zone = (431, 20, 1703, 1216)

        # Configuration automatique de Tesseract
        self.tesseract_cmd = self._find_tesseract()
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            logger.info(f"OCR : Tesseract configuré sur -> {self.tesseract_cmd}")
        else:
            logger.critical("❌ OCR ERREUR : Tesseract introuvable ! Veuillez l'installer ou vérifier le chemin.")

    def _find_tesseract(self):
        """Cherche l'exécutable Tesseract dans les dossiers communs ou le PATH."""
        # 1. Vérifier si dans le PATH système
        path = shutil.which("tesseract")
        if path: return path

        # 2. Vérifier les chemins d'installation standards Windows
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
            # Ajout : Vérifier dans un dossier 'bin' local au projet (pour la portabilité)
            os.path.join(os.getcwd(), "bin", "tesseract", "tesseract.exe")
        ]

        for p in common_paths:
            if os.path.exists(p): return p

        return None

    def _preprocess(self, img, threshold_value, scale_factor):
        if img is None or img.size == 0:
            return None

        # Redimensionnement pour mieux voir les petits textes
        if scale_factor > 1.0:
            h, w = img.shape[:2]
            img = cv2.resize(img, (int(w * scale_factor), int(h * scale_factor)), interpolation=cv2.INTER_CUBIC)

        # Conversion niveau de gris
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Binarisation (Noir et Blanc pur)
        _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        return thresh

    def _fuzzy_match(self, target, text, min_ratio=0.85):  # Ratio un peu plus permissif
        if not target or not text: return False

        # Comparaison simple
        if target.lower() in text.lower(): return True

        # Comparaison floue (Levenshtein)
        return SequenceMatcher(None, target.lower(), text.lower()).ratio() >= min_ratio

    def run_ocr_for_key_Z(self, window_manager, keyboard_manager, threshold=150, target="Lester", scale_factor=3.0,
                          zone_rect=None, grayscale=True):
        """
        Séquence complète : Focus fenêtre -> Appui 'Z' -> Screenshot -> Relache 'Z' -> Analyse OCR
        """
        if not window_manager.bound_handle:
            logger.warning("OCR : Aucune fenêtre de jeu liée.")
            return None, None

        try:
            if not window_manager.ensure_focus():
                return None, None

            # Simulation appui 'Z' pour afficher les noms
            keyboard_manager.send_key_action(0x5A, is_down=True)
            time.sleep(0.15)  # Petite pause pour laisser le jeu afficher les labels

            # Calcul de la zone de capture
            bbox = None
            abs_x, abs_y = 0, 0

            if zone_rect:
                x, y, w, h = zone_rect
                if w > 0 and h > 0:
                    bbox = (x, y, x + w, y + h)
                    abs_x, abs_y = x, y
            else:
                rect = window_manager.get_window_rect()
                if rect:
                    bbox = rect
                    abs_x, abs_y = rect[0], rect[1]

            # Capture d'écran
            img_pil = ImageGrab.grab(bbox=bbox) if bbox else None

            # Relachement 'Z'
            keyboard_manager.send_key_action(0x5A, is_down=False)

            if not img_pil:
                logger.error("Capture d'écran échouée (bbox invalide ?)")
                return None, None

            # Traitement OCR
            return self._process_image(img_pil, threshold, target, scale_factor, abs_x, abs_y)

        except Exception as e:
            logger.critical(f"❌ Erreur Séquence OCR : {e}", exc_info=True)
            # Sécurité : on s'assure que Z est relaché en cas de crash
            keyboard_manager.send_key_action(0x5A, is_down=False)

        return None, None

    def _process_image(self, img_pil, threshold, target, scale, offset_x, offset_y):
        """Sous-fonction interne pour traiter l'image"""
        try:
            # Conversion PIL -> CV2
            img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            processed = self._preprocess(img, threshold, scale)

            # Debug : Sauvegarde de l'image vue par le robot
            if not os.path.exists(self.save_dir): os.makedirs(self.save_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%H%M%S")
            debug_path = os.path.join(self.save_dir, f"OCR_{timestamp}_{target}.png")
            cv2.imwrite(debug_path, processed)

            # Analyse Tesseract
            # psm 11 = Sparse text (texte épars) : idéal pour les noms au dessus des monstres
            config = "--psm 11"
            data = pytesseract.image_to_data(processed, config=config, output_type=pytesseract.Output.DICT)

            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if not text: continue

                if self._fuzzy_match(target, text):
                    # Coordonnées sur l'image zoomée
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]

                    # Conversion vers coordonnées écran réelles
                    real_x = int((x + w // 2) / scale) + offset_x
                    real_y = int((y + h // 2) / scale) + offset_y

                    return (real_x, real_y), debug_path

            return None, debug_path

        except Exception as e:
            logger.error(f"Erreur traitement image: {e}")
            return None, None