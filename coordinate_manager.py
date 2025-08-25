"""Modulo per gestione coordinate e click automatici.

Questo modulo fornisce funzionalità complete per:
- Validazione delle coordinate
- Esecuzione di click automatici con retry
- Gestione errori durante i click
- Validazione post-click
"""

import time
import pyautogui

from config import (
    CLICK_VALIDATION_TIMEOUT, MAX_RETRIES, RETRY_DELAY
)
from logger import (
    log_message, log_error, log_debug, log_coordinates_found,
    record_click_performed, record_click_error
)

def validate_coordinates(coordinates):
    """Valida che le coordinate siano utilizzabili per un click.
    
    Args:
        coordinates (tuple or list): Coordinate (x, y) da validare
        
    Returns:
        bool: True se le coordinate sono valide
    """
    try:
        if not coordinates:
            return False
        
        if not isinstance(coordinates, (tuple, list)):
            return False
        
        if len(coordinates) != 2:
            return False
        
        x, y = coordinates
        
        # Controlla che siano numeri
        if not all(isinstance(coord, (int, float)) for coord in [x, y]):
            return False
        
        # Controlla che siano positivi
        if x < 0 or y < 0:
            return False
        
        # Ottieni dimensioni schermo
        try:
            screen_width, screen_height = pyautogui.size()
            
            # Controlla che siano dentro i limiti dello schermo
            if x >= screen_width or y >= screen_height:
                log_error(f"Coordinate {coordinates} fuori dai limiti schermo {screen_width}x{screen_height}")
                return False
                
        except Exception as e:
            log_error(f"Errore ottenimento dimensioni schermo: {e}")
            # Continua comunque con validazione base
        
        return True
        
    except Exception as e:
        log_error(f"Errore validazione coordinate {coordinates}: {e}")
        return False

def safe_click(coordinates, validate_after_click=True):
    """Esegue un click sicuro con validazione e gestione errori.
    
    Args:
        coordinates (tuple): Coordinate (x, y) dove cliccare
        validate_after_click (bool): Se validare il click dopo l'esecuzione
        
    Returns:
        bool: True se il click è stato eseguito con successo
    """
    try:
        # Validazione coordinate
        if not validate_coordinates(coordinates):
            log_error(f"Coordinate non valide per click: {coordinates}")
            return False
        
        x, y = coordinates
        log_debug(f"Tentativo click alle coordinate ({x}, {y})")
        
        # Esegui il click
        try:
            pyautogui.click(x, y)
            log_debug(f"Click eseguito alle coordinate ({x}, {y})")
            
            # Validazione post-click se richiesta
            if validate_after_click:
                time.sleep(CLICK_VALIDATION_TIMEOUT)
                # Qui potresti aggiungere ulteriori validazioni se necessario
            
            record_click_performed()
            return True
            
        except pyautogui.FailSafeException as e:
            log_error(f"FailSafe attivato durante click: {e}")
            record_click_error()
            return False
            
        except Exception as e:
            log_error(f"Errore durante esecuzione click: {e}")
            record_click_error()
            return False
        
    except Exception as e:
        log_error(f"Errore critico durante safe_click: {e}")
        record_click_error()
        return False

def click_with_retry(coordinates, max_retries=None, retry_delay=None):
    """Esegue un click con retry automatici in caso di fallimento.
    
    Args:
        coordinates (tuple): Coordinate (x, y) dove cliccare
        max_retries (int, optional): Numero massimo di retry
        retry_delay (float, optional): Delay tra i retry in secondi
        
    Returns:
        bool: True se il click è stato eseguito con successo
    """
    if max_retries is None:
        max_retries = MAX_RETRIES
    if retry_delay is None:
        retry_delay = RETRY_DELAY
    
    try:
        for attempt in range(max_retries + 1):  # +1 per includere il tentativo iniziale
            try:
                log_debug(f"Tentativo click #{attempt + 1}/{max_retries + 1}")
                
                if safe_click(coordinates, validate_after_click=True):
                    log_message(f"✅ Click eseguito con successo al tentativo #{attempt + 1}")
                    return True
                
                # Se non è l'ultimo tentativo, attendi prima del retry
                if attempt < max_retries:
                    log_debug(f"Click fallito, retry tra {retry_delay} secondi...")
                    time.sleep(retry_delay)
                
            except Exception as e:
                log_error(f"Errore durante tentativo click #{attempt + 1}: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue
        
        log_error(f"❌ Tutti i {max_retries + 1} tentativi di click falliti")
        return False
        
    except Exception as e:
        log_error(f"Errore critico durante click_with_retry: {e}")
        return False

def get_screen_dimensions():
    """Ottiene le dimensioni dello schermo.
    
    Returns:
        tuple: (width, height) o (0, 0) se fallisce
    """
    try:
        return pyautogui.size()
    except Exception as e:
        log_error(f"Errore ottenimento dimensioni schermo: {e}")
        return (0, 0)

def is_coordinate_on_screen(x, y):
    """Verifica se una coordinata è dentro i limiti dello schermo.
    
    Args:
        x (int): Coordinata X
        y (int): Coordinata Y
        
    Returns:
        bool: True se la coordinata è sullo schermo
    """
    try:
        screen_width, screen_height = get_screen_dimensions()
        if screen_width == 0 or screen_height == 0:
            return False
        
        return 0 <= x < screen_width and 0 <= y < screen_height
        
    except Exception as e:
        log_error(f"Errore verifica coordinata su schermo: {e}")
        return False

def filter_valid_coordinates(coordinates_list):
    """Filtra una lista di coordinate mantenendo solo quelle valide.
    
    Args:
        coordinates_list (list): Lista di coordinate da filtrare
        
    Returns:
        list: Lista di coordinate valide
    """
    valid_coordinates = []
    
    try:
        if not coordinates_list or not isinstance(coordinates_list, list):
            return valid_coordinates
        
        for coord in coordinates_list:
            try:
                if validate_coordinates(coord):
                    valid_coordinates.append(coord)
                    log_coordinates_found("target", coord)
                else:
                    log_debug(f"Coordinata non valida filtrata: {coord}")
            except Exception as e:
                log_error(f"Errore validazione coordinata {coord}: {e}")
                continue
        
        log_debug(f"Filtro coordinate: {len(valid_coordinates)}/{len(coordinates_list)} valide")
        return valid_coordinates
        
    except Exception as e:
        log_error(f"Errore critico durante filtro coordinate: {e}")
        return []

def select_best_coordinate(coordinates_list):
    """Seleziona la migliore coordinata da una lista.
    
    Args:
        coordinates_list (list): Lista di coordinate
        
    Returns:
        tuple or None: Migliore coordinata o None se nessuna valida
    """
    try:
        valid_coords = filter_valid_coordinates(coordinates_list)
        
        if not valid_coords:
            log_debug("Nessuna coordinata valida trovata")
            return None
        
        if len(valid_coords) == 1:
            log_debug(f"Una sola coordinata valida: {valid_coords[0]}")
            return valid_coords[0]
        
        # Se ci sono multiple coordinate, seleziona la prima (potrebbero essere tutte simili dopo deduplicazione)
        selected = valid_coords[0]
        log_debug(f"Selezionata coordinata: {selected} da {len(valid_coords)} opzioni")
        return selected
        
    except Exception as e:
        log_error(f"Errore selezione migliore coordinata: {e}")
        return None

def perform_automatic_click(coordinates_list):
    """Esegue un click automatico sulla migliore coordinata disponibile.
    
    Args:
        coordinates_list (list): Lista di coordinate candidate
        
    Returns:
        bool: True se il click è stato eseguito con successo
    """
    try:
        if not coordinates_list:
            log_debug("Nessuna coordinata fornita per click automatico")
            return False
        
        log_debug(f"Tentativo click automatico su {len(coordinates_list)} coordinate candidate")
        
        # Seleziona la migliore coordinata
        best_coord = select_best_coordinate(coordinates_list)
        if not best_coord:
            log_error("❌ Nessuna coordinata valida per click automatico")
            return False
        
        # Esegui il click con retry
        log_message(f"🖱️ Esecuzione click automatico alle coordinate {best_coord}")
        success = click_with_retry(best_coord)
        
        if success:
            log_message(f"✅ Click automatico eseguito con successo alle coordinate {best_coord}")
        else:
            log_error(f"❌ Click automatico fallito alle coordinate {best_coord}")
        
        return success
        
    except Exception as e:
        log_error(f"Errore critico durante click automatico: {e}")
        return False

def get_mouse_position():
    """Ottiene la posizione corrente del mouse.
    
    Returns:
        tuple: (x, y) posizione del mouse o (0, 0) se fallisce
    """
    try:
        return pyautogui.position()
    except Exception as e:
        log_error(f"Errore ottenimento posizione mouse: {e}")
        return (0, 0)

def move_mouse_to_coordinate(coordinates, duration=0.5):
    """Muove il mouse a una coordinata specifica.
    
    Args:
        coordinates (tuple): Coordinate (x, y) di destinazione
        duration (float): Durata del movimento in secondi
        
    Returns:
        bool: True se il movimento è stato eseguito con successo
    """
    try:
        if not validate_coordinates(coordinates):
            return False
        
        x, y = coordinates
        pyautogui.moveTo(x, y, duration=duration)
        log_debug(f"Mouse spostato alle coordinate ({x}, {y})")
        return True
        
    except Exception as e:
        log_error(f"Errore spostamento mouse: {e}")
        return False

def calculate_coordinate_center(coordinates_list):
    """Calcola il centro geometrico di una lista di coordinate.
    
    Args:
        coordinates_list (list): Lista di coordinate
        
    Returns:
        tuple or None: Coordinate del centro o None se fallisce
    """
    try:
        valid_coords = filter_valid_coordinates(coordinates_list)
        
        if not valid_coords:
            return None
        
        if len(valid_coords) == 1:
            return valid_coords[0]
        
        # Calcola il centro
        total_x = sum(coord[0] for coord in valid_coords)
        total_y = sum(coord[1] for coord in valid_coords)
        
        center_x = int(total_x / len(valid_coords))
        center_y = int(total_y / len(valid_coords))
        
        center = (center_x, center_y)
        
        # Valida il centro calcolato
        if validate_coordinates(center):
            log_debug(f"Centro calcolato: {center} da {len(valid_coords)} coordinate")
            return center
        else:
            log_error(f"Centro calcolato non valido: {center}")
            return None
        
    except Exception as e:
        log_error(f"Errore calcolo centro coordinate: {e}")
        return None