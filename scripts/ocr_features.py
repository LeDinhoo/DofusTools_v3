import cv2
import pytesseract
import time
import os
import numpy as np
import datetime


class OcrScripts:
    def __init__(self, logger_func):
        self.log = logger_func
        # Configuration Tesseract (Doit être le chemin local de l'utilisateur)
        try:
            # Note : Assurez-vous que ce chemin est correct pour l'utilisateur final.
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            self.log("OCR : Tesseract configuré.")
        except Exception as e:
            self.log(f"❌ OCR Erreur: Configuration Tesseract échouée. Veuillez vérifier le chemin. ({e})")

        # --- CONFIGURATION DU SAUVEGARDE ---
        self.save_dir = "ocr_screens"  # Nom du dossier de sauvegarde
        # -----------------------------

    # ---------------------
    # PREPROCESS (Amélioration pour petits textes via Redimensionnement)
    # ---------------------
    def _preprocess(self, img, threshold_value, scale_factor):
        """
        Applique un prétraitement avec mise à l'échelle pour améliorer
        la reconnaissance des petits caractères.
        """

        # 1. Mise à l'échelle (Upscaling)
        if scale_factor > 1.0:
            h, w = img.shape[:2]
            # Utiliser INTER_CUBIC pour une meilleure qualité d'interpolation
            img = cv2.resize(img, (int(w * scale_factor), int(h * scale_factor)), interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Seuil Binaire (Manuel)
        _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)

        return thresh

    # ---------------------
    # OCR
    # ---------------------
    def _ocr_text(self, img):
        """
        Lance l'OCR sur l'image en utilisant une whitelist et psm 6.
        """
        whitelist = " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'"
        config = f"--psm 6 -c tessedit_char_whitelist={whitelist}"
        text = pytesseract.image_to_string(img, config=config)
        return text

    # ---------------------
    # MÉTHODES APPELABLES
    # ---------------------
    def process_ocr_on_image(self, img_source, threshold_value=200, target_text="Lester", scale_factor=3.0):
        """
        Tente de reconnaître un texte cible dans une image source (fichier ou PIL.Image).
        """
        self.log(f"OCR : Début de la reconnaissance (Seuil: {threshold_value}, Cible: '{target_text}')")
        start_time = time.time()

        img = None
        if isinstance(img_source, str):
            # C'est un chemin de fichier
            if not os.path.exists(img_source):
                self.log(f"❌ OCR Erreur : Image introuvable au chemin '{img_source}'.")
                return
            img = cv2.imread(img_source)
            if img is None:
                self.log(f"❌ OCR Erreur : Impossible de lire le fichier '{img_source}'.")
                return
        else:
            # C'est un objet PIL.Image (venant de la capture)
            try:
                # Conversion PIL Image (RGB) vers OpenCV (BGR)
                img = cv2.cvtColor(np.array(img_source), cv2.COLOR_RGB2BGR)
            except Exception as e:
                self.log(f"❌ OCR Erreur : Problème de conversion Image PIL/NumPy. {e}")
                return

        try:
            # 1. Prétraitement simple AVEC FACTEUR D'ÉCHELLE
            processed = self._preprocess(img, threshold_value, scale_factor=scale_factor)

            # 2. Sauvegarde de l'image traitée
            if not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_target = "".join(c for c in target_text if c.isalnum() or c in ('_', '-'))
            filename = f"{timestamp}_T{threshold_value}_{safe_target}.png"
            full_path = os.path.join(self.save_dir, filename)

            cv2.imwrite(full_path, processed)
            self.log(f"💾 Image traitée sauvegardée : {full_path}")

            # 3. Lancement de l'OCR
            text = self._ocr_text(processed)
            cleaned = text.replace("\n", " ").strip()

            # 4. Affichage du résultat
            if target_text.lower() in cleaned.lower():
                self.log(f"✔️ OCR Succès : Texte cible '{target_text}' trouvé.")
            else:
                self.log(f"❌ OCR Échec : Texte cible '{target_text}' non trouvé. (Total: '{cleaned}')")

        except pytesseract.TesseractNotFoundError:
            self.log("❌ OCR Erreur: Tesseract n'est pas installé ou le chemin est incorrect.")
        except Exception as e:
            self.log(f"❌ OCR Erreur critique lors du traitement: {e}")
        finally:
            self.log(f"OCR : Terminé en {time.time() - start_time:.2f}s.")

    def run_ocr_for_key_Z(self, window_manager, keyboard_manager, threshold=200, target="Lester", scale_factor=1.0):
        """
        Séquence complète : Presser Z, Capturer, Relâcher Z, lancer l'OCR.
        """
        if not window_manager.bound_handle:
            self.log("❌ OCR Annulé : Aucune fenêtre du jeu n'est liée.")
            return

        self.log(f"OCR & Touche Z : Activation du panneau ('Z', 0x5A)...")

        try:
            if not window_manager.ensure_focus():
                self.log("❌ Séquence Annulée : Impossible de mettre la fenêtre en focus.")
                return

            # 1. Presser Z (0x5A)
            key_code_z = 0x5A
            keyboard_manager.send_key_action(key_code_z, is_down=True)
            time.sleep(0.05)

            # 2. Capture de la fenêtre
            img_pil = window_manager.capture_window()

            # 3. Fermer le panneau (presser Z à nouveau)
            keyboard_manager.send_key_action(key_code_z, is_down=False)

            if img_pil:
                # 4. Lancement de l'OCR sur l'objet image AVEC FACTEUR D'ÉCHELLE
                self.process_ocr_on_image(img_pil,
                                          threshold_value=threshold,
                                          target_text=target,
                                          scale_factor=scale_factor)
            else:
                self.log("❌ OCR Échec : Capture d'écran impossible.")

        except Exception as e:
            self.log(f"❌ Erreur critique lors de la séquence Z + OCR : {e}")