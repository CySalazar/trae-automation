"""Modulo per processamento e enhancement delle immagini.

Questo modulo fornisce funzionalità complete per:
- Cattura e gestione screenshot
- Enhancement delle immagini per migliorare l'OCR
- Conversioni tra formati immagine
- Gestione della cartella screenshot
"""

import os
import time
import numpy as np
from PIL import Image, ImageEnhance
import cv2
import pyautogui
from datetime import datetime

from config import (
    SCREENSHOTS_FOLDER, MAX_SCREENSHOTS_TO_KEEP,
    SCREENSHOT_FULLSCREEN_PATTERN, SCREENSHOT_ENHANCED_PATTERN,
    FILE_TIMESTAMP_FORMAT, SCREENSHOT_MAX_RETRIES,
    CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE,
    ADAPTIVE_THRESHOLD_MAX_VALUE, ADAPTIVE_THRESHOLD_BLOCK_SIZE, ADAPTIVE_THRESHOLD_C,
    GAUSSIAN_BLUR_KERNEL_SIZE, MORPHOLOGY_KERNEL_SIZE, MEDIAN_BLUR_KERNEL_SIZE,
    BILATERAL_FILTER_D, BILATERAL_FILTER_SIGMA_COLOR, BILATERAL_FILTER_SIGMA_SPACE,
    SHARPENING_KERNEL, MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT
)
from logger import log_message, log_error, log_debug, record_screenshot_error, record_enhancement_error

def manage_screenshots_folder():
    """Gestisce la cartella degli screenshot, creandola se necessario e pulendola."""
    try:
        # Crea la cartella se non esiste
        if not os.path.exists(SCREENSHOTS_FOLDER):
            os.makedirs(SCREENSHOTS_FOLDER)
            log_debug(f"Cartella '{SCREENSHOTS_FOLDER}' creata")
        
        # Pulisci vecchi screenshot se necessario
        cleanup_old_screenshots()
        
    except Exception as e:
        log_error(f"Errore gestione cartella screenshot: {e}")

def cleanup_old_screenshots():
    """Rimuove i vecchi screenshot mantenendo solo gli ultimi MAX_SCREENSHOTS_TO_KEEP."""
    try:
        if not os.path.exists(SCREENSHOTS_FOLDER):
            return
        
        # Ottieni tutti i file screenshot
        files = []
        for filename in os.listdir(SCREENSHOTS_FOLDER):
            if filename.endswith('.png'):
                filepath = os.path.join(SCREENSHOTS_FOLDER, filename)
                files.append((filepath, os.path.getmtime(filepath)))
        
        # Ordina per data di modifica (più recenti prima)
        files.sort(key=lambda x: x[1], reverse=True)
        
        # Rimuovi i file più vecchi
        if len(files) > MAX_SCREENSHOTS_TO_KEEP:
            files_to_remove = files[MAX_SCREENSHOTS_TO_KEEP:]
            for filepath, _ in files_to_remove:
                try:
                    os.remove(filepath)
                    log_debug(f"Screenshot rimosso: {os.path.basename(filepath)}")
                except Exception as e:
                    log_error(f"Errore rimozione screenshot {filepath}: {e}")
        
    except Exception as e:
        log_error(f"Errore pulizia screenshot: {e}")

def safe_screenshot():
    """Cattura uno screenshot con retry automatici in caso di errore.
    
    Returns:
        PIL.Image or None: Screenshot catturato o None se fallisce
    """
    for attempt in range(SCREENSHOT_MAX_RETRIES):
        try:
            log_debug(f"Tentativo screenshot #{attempt + 1}")
            screenshot = pyautogui.screenshot()
            
            if screenshot is None:
                raise Exception("Screenshot restituito None")
            
            # Verifica dimensioni minime
            if screenshot.width < MIN_IMAGE_WIDTH or screenshot.height < MIN_IMAGE_HEIGHT:
                raise Exception(f"Screenshot troppo piccolo: {screenshot.width}x{screenshot.height}")
            
            log_debug(f"Screenshot catturato con successo: {screenshot.width}x{screenshot.height}")
            return screenshot
            
        except Exception as e:
            log_error(f"Tentativo screenshot #{attempt + 1} fallito: {e}")
            if attempt < SCREENSHOT_MAX_RETRIES - 1:
                time.sleep(1)  # Attesa prima del retry
            else:
                record_screenshot_error()
                return None
    
    return None

def save_screenshot(screenshot, filename_pattern, **format_kwargs):
    """Salva uno screenshot con un nome file formattato.
    
    Args:
        screenshot (PIL.Image): Screenshot da salvare
        filename_pattern (str): Pattern del nome file con placeholder
        **format_kwargs: Argomenti per formattare il nome file
        
    Returns:
        str or None: Percorso del file salvato o None se fallisce
    """
    try:
        if screenshot is None:
            log_error("Tentativo di salvare screenshot None")
            return None
        
        # Aggiungi timestamp se non presente
        if 'timestamp' not in format_kwargs:
            format_kwargs['timestamp'] = datetime.now().strftime(FILE_TIMESTAMP_FORMAT)
        
        # Formatta il nome file
        filename = filename_pattern.format(**format_kwargs)
        filepath = os.path.join(SCREENSHOTS_FOLDER, filename)
        
        # Salva lo screenshot
        screenshot.save(filepath)
        log_debug(f"Screenshot salvato: {filename}")
        return filepath
        
    except Exception as e:
        log_error(f"Errore salvataggio screenshot: {e}")
        return None

def validate_image(image):
    """Valida che un'immagine sia utilizzabile.
    
    Args:
        image: Immagine da validare (PIL.Image o numpy.ndarray)
        
    Returns:
        bool: True se l'immagine è valida
    """
    try:
        if image is None:
            return False
        
        # Controlla PIL Image
        if isinstance(image, Image.Image):
            if image.width < MIN_IMAGE_WIDTH or image.height < MIN_IMAGE_HEIGHT:
                return False
            return True
        
        # Controlla numpy array
        if isinstance(image, np.ndarray):
            if len(image.shape) < 2:
                return False
            height, width = image.shape[:2]
            if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                return False
            return True
        
        return False
        
    except Exception:
        return False

def pil_to_cv2(pil_image):
    """Converte un'immagine PIL in formato OpenCV.
    
    Args:
        pil_image (PIL.Image): Immagine PIL da convertire
        
    Returns:
        numpy.ndarray or None: Immagine OpenCV o None se fallisce
    """
    try:
        if not validate_image(pil_image):
            return None
        
        # Converti in RGB se necessario
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Converti in numpy array
        cv2_image = np.array(pil_image)
        
        # OpenCV usa BGR, PIL usa RGB
        cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_RGB2BGR)
        
        return cv2_image
        
    except Exception as e:
        log_error(f"Errore conversione PIL->CV2: {e}")
        return None

def cv2_to_pil(cv2_image):
    """Converte un'immagine OpenCV in formato PIL.
    
    Args:
        cv2_image (numpy.ndarray): Immagine OpenCV da convertire
        
    Returns:
        PIL.Image or None: Immagine PIL o None se fallisce
    """
    try:
        if not validate_image(cv2_image):
            return None
        
        # OpenCV usa BGR, PIL usa RGB
        if len(cv2_image.shape) == 3:
            rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = cv2_image
        
        # Converti in PIL
        pil_image = Image.fromarray(rgb_image)
        
        return pil_image
        
    except Exception as e:
        log_error(f"Errore conversione CV2->PIL: {e}")
        return None

def enhance_with_clahe(image):
    """Applica CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image (numpy.ndarray): Immagine da processare
        
    Returns:
        numpy.ndarray or None: Immagine processata o None se fallisce
    """
    try:
        if not validate_image(image):
            return None
        
        # Converti in grayscale se necessario
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Applica CLAHE
        clahe = cv2.createCLAHE(
            clipLimit=CLAHE_CLIP_LIMIT,
            tileGridSize=CLAHE_TILE_GRID_SIZE
        )
        enhanced = clahe.apply(gray)
        
        return enhanced
        
    except Exception as e:
        log_error(f"Errore enhancement CLAHE: {e}")
        return None

def enhance_dark_on_light(image):
    """Enhancement per testo scuro su sfondo chiaro.
    
    Args:
        image (numpy.ndarray): Immagine da processare
        
    Returns:
        numpy.ndarray or None: Immagine processata o None se fallisce
    """
    try:
        if not validate_image(image):
            return None
        
        # Converti in grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Applica threshold adattivo
        enhanced = cv2.adaptiveThreshold(
            gray,
            ADAPTIVE_THRESHOLD_MAX_VALUE,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            ADAPTIVE_THRESHOLD_BLOCK_SIZE,
            ADAPTIVE_THRESHOLD_C
        )
        
        return enhanced
        
    except Exception as e:
        log_error(f"Errore enhancement dark-on-light: {e}")
        return None

def enhance_light_on_dark(image):
    """Enhancement per testo chiaro su sfondo scuro.
    
    Args:
        image (numpy.ndarray): Immagine da processare
        
    Returns:
        numpy.ndarray or None: Immagine processata o None se fallisce
    """
    try:
        if not validate_image(image):
            return None
        
        # Converti in grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Applica threshold adattivo invertito
        enhanced = cv2.adaptiveThreshold(
            gray,
            ADAPTIVE_THRESHOLD_MAX_VALUE,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            ADAPTIVE_THRESHOLD_BLOCK_SIZE,
            ADAPTIVE_THRESHOLD_C
        )
        
        return enhanced
        
    except Exception as e:
        log_error(f"Errore enhancement light-on-dark: {e}")
        return None

def apply_noise_reduction(image):
    """Applica riduzione del rumore all'immagine.
    
    Args:
        image (numpy.ndarray): Immagine da processare
        
    Returns:
        numpy.ndarray or None: Immagine processata o None se fallisce
    """
    try:
        if not validate_image(image):
            return None
        
        # Applica filtro bilaterale per ridurre il rumore mantenendo i bordi
        if len(image.shape) == 3:
            denoised = cv2.bilateralFilter(
                image,
                BILATERAL_FILTER_D,
                BILATERAL_FILTER_SIGMA_COLOR,
                BILATERAL_FILTER_SIGMA_SPACE
            )
        else:
            # Per immagini grayscale, usa medianBlur
            denoised = cv2.medianBlur(image, MEDIAN_BLUR_KERNEL_SIZE)
        
        return denoised
        
    except Exception as e:
        log_error(f"Errore riduzione rumore: {e}")
        return None

def apply_sharpening(image):
    """Applica sharpening all'immagine.
    
    Args:
        image (numpy.ndarray): Immagine da processare
        
    Returns:
        numpy.ndarray or None: Immagine processata o None se fallisce
    """
    try:
        if not validate_image(image):
            return None
        
        # Crea kernel di sharpening
        kernel = np.array(SHARPENING_KERNEL, dtype=np.float32)
        
        # Applica il filtro
        sharpened = cv2.filter2D(image, -1, kernel)
        
        return sharpened
        
    except Exception as e:
        log_error(f"Errore sharpening: {e}")
        return None

def enhance_image_for_text_detection(screenshot):
    """Applica vari metodi di enhancement per migliorare la detection del testo.
    
    Args:
        screenshot (PIL.Image): Screenshot originale
        
    Returns:
        list: Lista di tuple (method_name, enhanced_image_pil) o lista vuota se fallisce
    """
    enhanced_images = []
    
    try:
        # Validazione input
        if not validate_image(screenshot):
            log_error("Screenshot non valido per enhancement")
            return []
        
        log_debug(f"Inizio enhancement immagine {screenshot.width}x{screenshot.height}")
        
        # Converti in formato OpenCV
        cv2_image = pil_to_cv2(screenshot)
        if cv2_image is None:
            log_error("Errore conversione screenshot per enhancement")
            return []
        
        # Metodi di enhancement
        enhancement_methods = [
            ('CLAHE', enhance_with_clahe),
            ('DARK_ON_LIGHT', enhance_dark_on_light),
            ('LIGHT_ON_DARK', enhance_light_on_dark)
        ]
        
        for method_name, enhance_func in enhancement_methods:
            try:
                log_debug(f"Applicando enhancement: {method_name}")
                
                # Applica enhancement
                enhanced_cv2 = enhance_func(cv2_image)
                if enhanced_cv2 is None:
                    log_error(f"Enhancement {method_name} ha restituito None")
                    continue
                
                # Applica post-processing opzionale
                try:
                    # Riduzione rumore
                    enhanced_cv2 = apply_noise_reduction(enhanced_cv2)
                    if enhanced_cv2 is None:
                        log_error(f"Riduzione rumore fallita per {method_name}")
                        continue
                    
                    # Sharpening
                    enhanced_cv2 = apply_sharpening(enhanced_cv2)
                    if enhanced_cv2 is None:
                        log_error(f"Sharpening fallito per {method_name}")
                        continue
                        
                except Exception as e:
                    log_error(f"Errore post-processing per {method_name}: {e}")
                    # Continua senza post-processing
                
                # Converti di nuovo in PIL
                enhanced_pil = cv2_to_pil(enhanced_cv2)
                if enhanced_pil is None:
                    log_error(f"Conversione PIL fallita per {method_name}")
                    continue
                
                enhanced_images.append((method_name, enhanced_pil))
                log_debug(f"Enhancement {method_name} completato con successo")
                
            except Exception as e:
                log_error(f"Errore durante enhancement {method_name}: {e}")
                record_enhancement_error()
                continue
        
        log_debug(f"Enhancement completato: {len(enhanced_images)} immagini generate")
        return enhanced_images
        
    except Exception as e:
        log_error(f"Errore critico durante enhancement: {e}")
        record_enhancement_error()
        return []

def save_enhanced_image(enhanced_image, method_name):
    """Salva un'immagine enhanced per debug.
    
    Args:
        enhanced_image (PIL.Image): Immagine enhanced da salvare
        method_name (str): Nome del metodo di enhancement
        
    Returns:
        str or None: Percorso del file salvato o None se fallisce
    """
    try:
        return save_screenshot(
            enhanced_image,
            SCREENSHOT_ENHANCED_PATTERN,
            method_name=method_name
        )
    except Exception as e:
        log_error(f"Errore salvataggio immagine enhanced {method_name}: {e}")
        return None