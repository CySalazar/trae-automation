"""Modulo per estrazione testo tramite OCR.

Questo modulo fornisce funzionalità complete per:
- Estrazione testo da immagini con multiple configurazioni OCR
- Validazione e processamento dei risultati OCR
- Gestione errori e retry per operazioni OCR
- Deduplicazione delle detection
"""

import re
import pytesseract
from PIL import Image

from config import (
    OCR_CONFIGS, MIN_CONFIDENCE_THRESHOLD,
    DEDUPLICATION_DISTANCE_THRESHOLD, FINAL_COORDINATES_TOLERANCE
)
from logger import (
    log_message, log_error, log_debug, log_enhancement_stats,
    record_ocr_error
)
from image_processing import validate_image

def extract_text_with_single_config(image, config):
    """Estrae testo da un'immagine usando una singola configurazione OCR.
    
    Args:
        image (PIL.Image): Immagine da processare
        config (str): Configurazione OCR da utilizzare
        
    Returns:
        dict or None: Dati OCR o None se fallisce
    """
    try:
        if not validate_image(image):
            return None
        
        # Esegui OCR con la configurazione specificata
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config=config
        )
        
        return data
        
    except Exception as e:
        log_error(f"Errore OCR con config '{config}': {e}")
        return None

def validate_ocr_data(data):
    """Valida i dati OCR restituiti da Tesseract.
    
    Args:
        data (dict): Dati OCR da validare
        
    Returns:
        bool: True se i dati sono validi
    """
    try:
        if not data or not isinstance(data, dict):
            return False
        
        # Controlla che ci siano le chiavi necessarie
        required_keys = ['text', 'left', 'top', 'width', 'height', 'conf']
        for key in required_keys:
            if key not in data:
                return False
            if not isinstance(data[key], list):
                return False
        
        # Controlla che tutte le liste abbiano la stessa lunghezza
        lengths = [len(data[key]) for key in required_keys]
        if not all(length == lengths[0] for length in lengths):
            return False
        
        return True
        
    except Exception:
        return False

def process_single_detection(i, data):
    """Processa una singola detection OCR.
    
    Args:
        i (int): Indice della detection
        data (dict): Dati OCR completi
        
    Returns:
        dict or None: Detection processata o None se non valida
    """
    try:
        text = data['text'][i].strip()
        confidence = data['conf'][i]
        left = data['left'][i]
        top = data['top'][i]
        width = data['width'][i]
        height = data['height'][i]
        
        # Validazione base
        if not text or confidence < MIN_CONFIDENCE_THRESHOLD:
            return None
        
        # Validazione coordinate
        if not all(isinstance(val, (int, float)) for val in [left, top, width, height]):
            return None
        
        if left < 0 or top < 0 or width <= 0 or height <= 0:
            return None
        
        # Calcola coordinate del centro
        center_x = int(left + width // 2)
        center_y = int(top + height // 2)
        
        return {
            'text': text,
            'confidence': float(confidence),
            'left': int(left),
            'top': int(top),
            'width': int(width),
            'height': int(height),
            'center_x': center_x,
            'center_y': center_y
        }
        
    except Exception as e:
        log_error(f"Errore processamento detection {i}: {e}")
        return None

def extract_all_text_with_positions(image):
    """Estrae tutto il testo con posizioni da un'immagine usando multiple configurazioni OCR.
    
    Args:
        image (PIL.Image): Immagine da processare
        
    Returns:
        list: Lista di detection valide
    """
    all_detections = []
    
    try:
        # Validazione input
        if not validate_image(image):
            log_error("Immagine non valida per estrazione testo")
            return []
        
        log_debug(f"Inizio estrazione testo da immagine {image.width}x{image.height}")
        
        # Prova tutte le configurazioni OCR
        for config in OCR_CONFIGS:
            try:
                log_debug(f"Tentativo OCR con config: {config}")
                
                # Estrai dati OCR
                data = extract_text_with_single_config(image, config)
                if not validate_ocr_data(data):
                    log_debug(f"Dati OCR non validi per config: {config}")
                    continue
                
                # Processa ogni detection
                valid_detections = 0
                for i in range(len(data['text'])):
                    try:
                        detection = process_single_detection(i, data)
                        if detection:
                            all_detections.append(detection)
                            valid_detections += 1
                    except Exception as e:
                        log_error(f"Errore processamento detection {i} con config {config}: {e}")
                        continue
                
                log_debug(f"Config {config}: {valid_detections} detection valide")
                
            except Exception as e:
                log_error(f"Errore OCR con configurazione {config}: {e}")
                record_ocr_error()
                continue
        
        log_debug(f"Estrazione testo completata: {len(all_detections)} detection totali")
        return all_detections
        
    except Exception as e:
        log_error(f"Errore critico durante estrazione testo: {e}")
        record_ocr_error()
        return []

def calculate_distance(det1, det2):
    """Calcola la distanza euclidea tra due detection.
    
    Args:
        det1 (dict): Prima detection
        det2 (dict): Seconda detection
        
    Returns:
        float: Distanza euclidea
    """
    try:
        dx = det1['center_x'] - det2['center_x']
        dy = det1['center_y'] - det2['center_y']
        return (dx * dx + dy * dy) ** 0.5
    except Exception:
        return float('inf')

def deduplicate_detections(detections):
    """Rimuove detection duplicate basandosi sulla distanza e confidence.
    
    Args:
        detections (list): Lista di detection da deduplicare
        
    Returns:
        list: Lista di detection deduplicate
    """
    try:
        # Validazione input
        if not detections or not isinstance(detections, list):
            log_debug("Lista detection vuota o non valida")
            return []
        
        log_debug(f"Inizio deduplicazione di {len(detections)} detection")
        
        # Filtra detection non valide
        valid_detections = []
        for det in detections:
            try:
                if not isinstance(det, dict):
                    continue
                
                required_fields = ['text', 'confidence', 'center_x', 'center_y']
                if not all(field in det for field in required_fields):
                    continue
                
                # Validazione valori
                if not det['text'] or det['text'].isspace():
                    continue
                
                if not isinstance(det['confidence'], (int, float)) or det['confidence'] < 0:
                    continue
                
                if not all(isinstance(det[field], (int, float)) for field in ['center_x', 'center_y']):
                    continue
                
                if det['center_x'] < 0 or det['center_y'] < 0:
                    continue
                
                valid_detections.append(det)
                
            except Exception as e:
                log_error(f"Errore validazione detection: {e}")
                continue
        
        if not valid_detections:
            log_debug("Nessuna detection valida dopo filtro")
            return []
        
        log_debug(f"Detection valide dopo filtro: {len(valid_detections)}")
        
        # Ordina per confidence (più alta prima)
        try:
            valid_detections.sort(key=lambda x: x['confidence'], reverse=True)
        except Exception as e:
            log_error(f"Errore ordinamento detection: {e}")
            return valid_detections  # Restituisci senza ordinamento
        
        # Deduplicazione
        deduplicated = []
        for current in valid_detections:
            try:
                is_duplicate = False
                
                for existing in deduplicated:
                    try:
                        # Controlla se il testo è identico
                        if current['text'].lower() == existing['text'].lower():
                            distance = calculate_distance(current, existing)
                            if distance < DEDUPLICATION_DISTANCE_THRESHOLD:
                                is_duplicate = True
                                break
                    except Exception as e:
                        log_error(f"Errore confronto detection: {e}")
                        continue
                
                if not is_duplicate:
                    deduplicated.append(current)
                    
            except Exception as e:
                log_error(f"Errore durante deduplicazione: {e}")
                continue
        
        log_debug(f"Deduplicazione completata: {len(deduplicated)} detection uniche")
        return deduplicated
        
    except Exception as e:
        log_error(f"Errore critico durante deduplicazione: {e}")
        # Fallback: restituisci le detection originali
        return detections if isinstance(detections, list) else []

def find_target_pattern_in_detections(detections, target_pattern, target_end_word):
    """Cerca il pattern target nelle detection e trova le coordinate della parola finale.
    
    Args:
        detections (list): Lista di detection
        target_pattern (str): Pattern regex da cercare
        target_end_word (str): Parola finale di cui trovare le coordinate
        
    Returns:
        list: Lista di coordinate (x, y) trovate
    """
    coordinates = []
    
    try:
        if not detections:
            return coordinates
        
        log_debug(f"Ricerca pattern '{target_pattern}' in {len(detections)} detection")
        
        # Crea una stringa con tutto il testo rilevato
        all_text_parts = []
        text_to_detection = {}  # Mappa posizione nel testo -> detection
        
        current_pos = 0
        for det in detections:
            try:
                text = det['text']
                all_text_parts.append(text)
                
                # Mappa ogni carattere alla sua detection
                for i in range(len(text)):
                    text_to_detection[current_pos + i] = det
                
                current_pos += len(text) + 1  # +1 per lo spazio
                all_text_parts.append(' ')  # Aggiungi spazio tra detection
                
            except Exception as e:
                log_error(f"Errore processamento detection per pattern: {e}")
                continue
        
        full_text = ''.join(all_text_parts)
        log_debug(f"Testo completo per ricerca: '{full_text[:100]}...'")
        
        # Cerca il pattern
        try:
            pattern_matches = list(re.finditer(target_pattern, full_text, re.IGNORECASE))
            log_debug(f"Trovati {len(pattern_matches)} match del pattern")
            
            for match in pattern_matches:
                try:
                    # Trova tutte le occorrenze della parola target nel match
                    match_text = match.group()
                    word_pattern = r'\b' + re.escape(target_end_word) + r'\b'
                    word_matches = list(re.finditer(word_pattern, match_text, re.IGNORECASE))
                    
                    for word_match in word_matches:
                        try:
                            # Calcola la posizione assoluta della parola
                            word_start_pos = match.start() + word_match.start()
                            word_end_pos = match.start() + word_match.end() - 1
                            
                            # Trova la detection corrispondente alla fine della parola
                            if word_end_pos in text_to_detection:
                                det = text_to_detection[word_end_pos]
                                coord = (det['center_x'], det['center_y'])
                                coordinates.append(coord)
                                log_debug(f"Coordinate trovate per '{target_end_word}': {coord}")
                            
                        except Exception as e:
                            log_error(f"Errore estrazione coordinate parola: {e}")
                            continue
                            
                except Exception as e:
                    log_error(f"Errore processamento match pattern: {e}")
                    continue
                    
        except Exception as e:
            log_error(f"Errore ricerca pattern regex: {e}")
        
        log_debug(f"Ricerca pattern completata: {len(coordinates)} coordinate trovate")
        return coordinates
        
    except Exception as e:
        log_error(f"Errore critico durante ricerca pattern: {e}")
        return []

def deduplicate_coordinates(coordinates, tolerance=None):
    """Deduplicazione finale delle coordinate trovate.
    
    Args:
        coordinates (list): Lista di coordinate (x, y)
        tolerance (int, optional): Tolleranza per considerare coordinate duplicate
        
    Returns:
        list: Lista di coordinate deduplicate
    """
    if tolerance is None:
        tolerance = FINAL_COORDINATES_TOLERANCE
    
    try:
        if not coordinates:
            return []
        
        log_debug(f"Deduplicazione {len(coordinates)} coordinate con tolleranza {tolerance}")
        
        deduplicated = []
        for coord in coordinates:
            try:
                if not isinstance(coord, (tuple, list)) or len(coord) != 2:
                    continue
                
                x, y = coord
                if not all(isinstance(val, (int, float)) for val in [x, y]):
                    continue
                
                is_duplicate = False
                for existing_coord in deduplicated:
                    try:
                        ex_x, ex_y = existing_coord
                        distance = ((x - ex_x) ** 2 + (y - ex_y) ** 2) ** 0.5
                        if distance <= tolerance:
                            is_duplicate = True
                            break
                    except Exception:
                        continue
                
                if not is_duplicate:
                    deduplicated.append((int(x), int(y)))
                    
            except Exception as e:
                log_error(f"Errore deduplicazione coordinata {coord}: {e}")
                continue
        
        log_debug(f"Deduplicazione coordinate completata: {len(deduplicated)} coordinate uniche")
        return deduplicated
        
    except Exception as e:
        log_error(f"Errore critico deduplicazione coordinate: {e}")
        return coordinates if isinstance(coordinates, list) else []