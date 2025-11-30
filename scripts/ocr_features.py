import cv2
import pytesseract
import time
import os
import shutil
import numpy as np
import datetime
import logging

logger = logging.getLogger(__name__)


class OcrScripts:
    def __init__(self):
        # Configuration dynamique de Tesseract
        self.tesseract_cmd = self._find_tesseract()

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            logger.info(f"OCR : Tesseract configuré sur {self.tesseract_cmd}")
        else:
            logger.error("❌ OCR Erreur: Tesseract introuvable dans le PATH ou les dossiers standards.")

        self.save_dir = "ocr_screens"

    def _find_tesseract(self):
        """Tente de localiser l'exécutable tesseract"""
        # 1. PATH système
        path = shutil.which("tesseract")
        if path: return path

        # 2. Chemins communs Windows
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")
        ]
        for p in common_paths:
            if os.path.exists(p): return p
        return None

    def _preprocess(self, img, threshold_value, scale_factor):
        if scale_factor > 1.0:
            h, w = img.shape[:2]
            img = cv2.resize(img, (int(w * scale_factor), int(h * scale_factor)), interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        return thresh

    def _ocr_text(self, img):
        whitelist = " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'"
        config = f"--psm 6 -c tessedit_char_whitelist={whitelist}"
        return pytesseract.image_to_string(img, config=config)

    def process_ocr_on_image(self, img_source, threshold_value=200, target_text="Lester", scale_factor=3.0):
        logger.info(f"OCR : Début de la reconnaissance (Seuil: {threshold_value}, Cible: '{target_text}')")
        start_time = time.time()

        img = None
        if isinstance(img_source, str):
            if not os.path.exists(img_source):
                logger.error(f"❌ OCR : Fichier introuvable '{img_source}'.")
                return
            img = cv2.imread(img_source)
        else:
            try:
                img = cv2.cvtColor(np.array(img_source), cv2.COLOR_RGB2BGR)
            except Exception as e:
                logger.error(f"❌ OCR : Conversion image échouée. {e}")
                return

        if img is None: return

        try:
            processed = self._preprocess(img, threshold_value, scale_factor=scale_factor)

            # Sauvegarde debug
            if not os.path.exists(self.save_dir): os.makedirs(self.save_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_target = "".join(c for c in target_text if c.isalnum() or c in ('_', '-'))
            filename = f"{timestamp}_T{threshold_value}_{safe_target}.png"
            cv2.imwrite(os.path.join(self.save_dir, filename), processed)

            text = self._ocr_text(processed)
            cleaned = text.replace("\n", " ").strip()

            if target_text.lower() in cleaned.lower():
                logger.info(f"✔️ OCR Succès : '{target_text}' trouvé.")
            else:
                logger.info(f"❌ OCR Échec. Trouvé : '{cleaned[:50]}...'")

        except Exception as e:
            logger.error(f"❌ OCR Exception : {e}")
        finally:
            logger.debug(f"OCR Terminé en {time.time() - start_time:.2f}s.")

    def run_ocr_for_key_Z(self, window_manager, keyboard_manager, threshold=200, target="Lester", scale_factor=1.0):
        if not window_manager.bound_handle:
            logger.warning("❌ OCR Annulé : Fenêtre non liée.")
            return

        logger.info("OCR Séquence 'Z'...")
        try:
            if not window_manager.ensure_focus(): return

            # Séquence
            keyboard_manager.send_key_action(0x5A, is_down=True)  # Z down
            time.sleep(0.05)
            img_pil = window_manager.capture_window()
            keyboard_manager.send_key_action(0x5A, is_down=False)  # Z up

            if img_pil:
                self.process_ocr_on_image(img_pil, threshold_value=threshold, target_text=target,
                                          scale_factor=scale_factor)
            else:
                logger.error("❌ OCR : Capture impossible.")

        except Exception as e:
            logger.critical(f"❌ Erreur Séquence OCR : {e}")