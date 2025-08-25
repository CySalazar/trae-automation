"""Modulo principale per la logica di scansione.

Questo modulo orchestra tutti i componenti del sistema per:
- Eseguire scansioni complete dello schermo
- Processare le immagini e estrarre il testo
- Cercare il messaggio target
- Eseguire click automatici quando necessario
"""

import time
from datetime import datetime

from config import (
    TARGET_PATTERN, TARGET_END_WORD, SCREENSHOT_FULLSCREEN_PATTERN,
    MAX_RETRIES, RETRY_DELAY, MAX_CONSECUTIVE_FAILURES, EXTENDED_WAIT_TIME
)
from logger import (
    log_message, log_error, log_debug, log_scan_start, log_scan_complete,
    log_enhancement_stats, update_scan_stats, update_performance_stats,
    record_successful_detection, should_log_status_report, log_system_status,
    reset_consecutive_failures, log_extended_wait_start, log_extended_wait_complete,
    get_stats_copy
)
from image_processing import (
    manage_screenshots_folder, safe_screenshot, save_screenshot,
    enhance_image_for_text_detection, save_enhanced_image
)
from ocr_engine import (
    extract_all_text_with_positions, deduplicate_detections,
    find_target_pattern_in_detections, deduplicate_coordinates
)
from coordinate_manager import perform_automatic_click

def scan_entire_screen_for_continue_message():
    """Esegue una scansione completa dello schermo per trovare il messaggio 'Continue'.
    
    Returns:
        list: Lista di coordinate trovate o lista vuota se non trovate/errore
    """
    try:
        log_debug("Inizio scansione completa dello schermo")
        
        # Gestisci cartella screenshot
        try:
            manage_screenshots_folder()
        except Exception as e:
            log_error(f"Errore gestione cartella screenshot: {e}")
            # Continua comunque
        
        # Cattura screenshot
        try:
            screenshot = safe_screenshot()
            if screenshot is None:
                log_error("Impossibile catturare screenshot")
                return []
        except Exception as e:
            log_error(f"Errore critico durante cattura screenshot: {e}")
            return []
        
        # Salva screenshot per debug
        try:
            save_screenshot(screenshot, SCREENSHOT_FULLSCREEN_PATTERN)
        except Exception as e:
            log_error(f"Errore salvataggio screenshot: {e}")
            # Continua comunque
        
        # Enhancement delle immagini
        try:
            enhanced_images = enhance_image_for_text_detection(screenshot)
            if not enhanced_images:
                log_error("Nessuna immagine enhanced generata")
                return []
        except Exception as e:
            log_error(f"Errore durante enhancement immagini: {e}")
            return []
        
        # Processa ogni immagine enhanced
        all_detections = []
        for method_name, enhanced_image in enhanced_images:
            try:
                log_debug(f"Processamento immagine enhanced: {method_name}")
                
                # Salva immagine enhanced per debug
                try:
                    save_enhanced_image(enhanced_image, method_name)
                except Exception as e:
                    log_error(f"Errore salvataggio immagine enhanced {method_name}: {e}")
                    # Continua comunque
                
                # Estrai testo
                try:
                    detections = extract_all_text_with_positions(enhanced_image)
                    if detections:
                        all_detections.extend(detections)
                        log_enhancement_stats(method_name, len(detections))
                    else:
                        log_debug(f"Nessuna detection per metodo {method_name}")
                except Exception as e:
                    log_error(f"Errore estrazione testo per {method_name}: {e}")
                    continue
                
            except Exception as e:
                log_error(f"Errore processamento metodo {method_name}: {e}")
                continue
        
        if not all_detections:
            log_debug("Nessuna detection trovata in tutte le immagini enhanced")
            return []
        
        # Deduplicazione detection
        try:
            unique_detections = deduplicate_detections(all_detections)
            log_debug(f"Detection dopo deduplicazione: {len(unique_detections)}")
        except Exception as e:
            log_error(f"Errore deduplicazione detection: {e}")
            unique_detections = all_detections  # Fallback
        
        # Log delle detection trovate (solo per debug)
        try:
            detected_words = [det['text'] for det in unique_detections[:10]]  # Prime 10
            if detected_words:
                log_debug(f"Parole rilevate (prime 10): {', '.join(detected_words)}")
        except Exception as e:
            log_error(f"Errore logging detection: {e}")
        
        # Cerca il pattern target
        try:
            coordinates = find_target_pattern_in_detections(
                unique_detections, TARGET_PATTERN, TARGET_END_WORD
            )
            log_debug(f"Coordinate trovate dal pattern: {len(coordinates)}")
        except Exception as e:
            log_error(f"Errore ricerca pattern target: {e}")
            return []
        
        # Deduplicazione finale delle coordinate
        try:
            final_coordinates = deduplicate_coordinates(coordinates)
            log_debug(f"Coordinate finali dopo deduplicazione: {len(final_coordinates)}")
            return final_coordinates
        except Exception as e:
            log_error(f"Errore deduplicazione coordinate finali: {e}")
            return coordinates if coordinates else []
        
    except Exception as e:
        log_error(f"Errore critico durante scansione schermo: {e}")
        return []

def perform_single_scan(scan_number):
    """Esegue una singola scansione completa.
    
    Args:
        scan_number (int): Numero della scansione
        
    Returns:
        tuple: (success, coordinates_found)
    """
    try:
        log_scan_start(scan_number)
        scan_start_time = time.time()
        
        # Esegui scansione
        coordinates = scan_entire_screen_for_continue_message()
        
        # Calcola tempo di scansione
        scan_time = time.time() - scan_start_time
        update_performance_stats(scan_time)
        
        # Determina se la scansione ha avuto successo
        success = len(coordinates) > 0
        
        # Log risultato
        log_scan_complete(scan_number, success, coordinates)
        
        # Aggiorna statistiche
        update_scan_stats(success, scan_time)
        
        if success:
            record_successful_detection()
        
        return success, coordinates
        
    except Exception as e:
        log_error(f"Errore durante scansione #{scan_number}: {e}")
        return False, []

def perform_scan_with_retry(scan_number, max_retries=None, retry_delay=None):
    """Esegue una scansione con retry automatici.
    
    Args:
        scan_number (int): Numero della scansione
        max_retries (int, optional): Numero massimo di retry
        retry_delay (float, optional): Delay tra i retry
        
    Returns:
        tuple: (success, coordinates_found)
    """
    if max_retries is None:
        max_retries = MAX_RETRIES
    if retry_delay is None:
        retry_delay = RETRY_DELAY
    
    try:
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    log_debug(f"Retry scansione #{scan_number}, tentativo {attempt + 1}/{max_retries + 1}")
                
                success, coordinates = perform_single_scan(scan_number)
                
                if success:
                    if attempt > 0:
                        log_message(f"✅ Scansione #{scan_number} riuscita al tentativo {attempt + 1}")
                    return True, coordinates
                
                # Se non è l'ultimo tentativo, attendi prima del retry
                if attempt < max_retries:
                    log_debug(f"Scansione fallita, retry tra {retry_delay} secondi...")
                    time.sleep(retry_delay)
                
            except Exception as e:
                log_error(f"Errore durante tentativo {attempt + 1} della scansione #{scan_number}: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue
        
        log_debug(f"Tutti i tentativi di scansione #{scan_number} falliti")
        return False, []
        
    except Exception as e:
        log_error(f"Errore critico durante scan_with_retry #{scan_number}: {e}")
        return False, []

def handle_scan_result(scan_number, success, coordinates):
    """Gestisce il risultato di una scansione.
    
    Args:
        scan_number (int): Numero della scansione
        success (bool): Se la scansione ha avuto successo
        coordinates (list): Coordinate trovate
        
    Returns:
        bool: True se è stato eseguito un click automatico
    """
    try:
        if success and coordinates:
            log_message(f"🎯 Messaggio target trovato nella scansione #{scan_number}!")
            
            # Esegui click automatico
            click_success = perform_automatic_click(coordinates)
            
            if click_success:
                log_message(f"✅ Click automatico eseguito con successo per scansione #{scan_number}")
                return True
            else:
                log_error(f"❌ Click automatico fallito per scansione #{scan_number}")
                return False
        else:
            log_debug(f"Messaggio target non trovato nella scansione #{scan_number}")
            return False
            
    except Exception as e:
        log_error(f"Errore gestione risultato scansione #{scan_number}: {e}")
        return False

def handle_consecutive_failures():
    """Gestisce i fallimenti consecutivi implementando attesa estesa.
    
    Returns:
        bool: True se è stata eseguita un'attesa estesa
    """
    try:
        stats = get_stats_copy()
        consecutive_failures = stats.get('consecutive_failures', 0)
        
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            log_extended_wait_start()
            
            # Attesa estesa
            try:
                time.sleep(EXTENDED_WAIT_TIME)
            except KeyboardInterrupt:
                log_message("⚠️ Interruzione durante attesa estesa")
                raise
            except Exception as e:
                log_error(f"Errore durante attesa estesa: {e}")
            
            log_extended_wait_complete()
            reset_consecutive_failures()
            return True
        
        return False
        
    except Exception as e:
        log_error(f"Errore gestione fallimenti consecutivi: {e}")
        return False

def should_perform_extended_wait():
    """Determina se dovrebbe essere eseguita un'attesa estesa.
    
    Returns:
        bool: True se dovrebbe essere eseguita un'attesa estesa
    """
    try:
        stats = get_stats_copy()
        consecutive_failures = stats.get('consecutive_failures', 0)
        return consecutive_failures >= MAX_CONSECUTIVE_FAILURES
    except Exception:
        return False

def log_scan_summary(scan_number, success, click_performed, scan_time=None):
    """Registra un riassunto della scansione.
    
    Args:
        scan_number (int): Numero della scansione
        success (bool): Se la scansione ha avuto successo
        click_performed (bool): Se è stato eseguito un click
        scan_time (float, optional): Tempo di scansione in secondi
    """
    try:
        status_icon = "✅" if success else "❌"
        click_icon = "🖱️" if click_performed else ""
        
        summary = f"{status_icon} Scansione #{scan_number}"
        
        if success:
            summary += " - Target trovato"
            if click_performed:
                summary += " - Click eseguito"
        else:
            summary += " - Target non trovato"
        
        if scan_time:
            summary += f" ({scan_time:.2f}s)"
        
        log_message(summary)
        
        # Log report di stato se necessario
        if should_log_status_report():
            log_system_status()
            
    except Exception as e:
        log_error(f"Errore logging riassunto scansione: {e}")

def get_next_scan_number():
    """Ottiene il numero della prossima scansione.
    
    Returns:
        int: Numero della prossima scansione
    """
    try:
        stats = get_stats_copy()
        return stats.get('total_scans', 0) + 1
    except Exception:
        return 1

def is_system_healthy():
    """Verifica se il sistema è in uno stato sano.
    
    Returns:
        bool: True se il sistema è sano
    """
    try:
        stats = get_stats_copy()
        
        # Controlla se ci sono troppi errori
        total_errors = stats.get('total_errors', 0)
        total_scans = stats.get('total_scans', 1)
        
        error_rate = total_errors / total_scans if total_scans > 0 else 0
        
        # Se il tasso di errore è superiore al 50%, considera il sistema non sano
        if error_rate > 0.5 and total_scans > 10:
            log_error(f"Sistema non sano: tasso errori {error_rate:.1%} su {total_scans} scansioni")
            return False
        
        return True
        
    except Exception as e:
        log_error(f"Errore verifica salute sistema: {e}")
        return True  # Assume sano in caso di errore

def log_scan_summary():
    """Registra un riassunto delle scansioni effettuate."""
    try:
        stats = get_stats_copy()
        total_scans = stats.get('total_scans', 0)
        successful_detections = stats.get('successful_detections', 0)
        total_clicks = stats.get('total_clicks', 0)
        
        if total_scans > 0:
            success_rate = (successful_detections / total_scans) * 100
            log_message(f"📊 Riassunto: {total_scans} scansioni, {successful_detections} detection ({success_rate:.1f}%), {total_clicks} click")
        
    except Exception as e:
        log_error(f"Errore durante log riassunto scansioni: {e}")