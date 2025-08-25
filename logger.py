"""Modulo per gestione logging e statistiche del sistema.

Questo modulo fornisce funzionalità complete per:
- Logging strutturato con timestamp
- Monitoraggio statistiche di performance
- Report di stato del sistema
- Gestione errori e metriche
"""

import time
import os
from datetime import datetime
from config import (
    LOG_FILE, TIMESTAMP_FORMAT, LOG_SEPARATOR, SUB_SEPARATOR,
    STATUS_REPORT_FREQUENCY, MAX_SCAN_TIMES_HISTORY,
    get_initial_stats
)

# Statistiche globali del sistema
stats = get_initial_stats()

def log_message(message, level="INFO", include_separator=False):
    """Registra un messaggio nel file di log con timestamp.
    
    Args:
        message (str): Il messaggio da registrare
        level (str): Livello del log (INFO, ERROR, WARNING, DEBUG)
        include_separator (bool): Se includere un separatore prima del messaggio
    """
    try:
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Stampa su console
        print(log_entry)
        
        # Scrivi su file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if include_separator:
                f.write(f"\n{LOG_SEPARATOR}\n")
            f.write(log_entry + "\n")
            
    except Exception as e:
        # Fallback: stampa solo su console se il file non è accessibile
        print(f"[{datetime.now().strftime(TIMESTAMP_FORMAT)}] [ERROR] Errore logging: {e}")
        print(f"[{datetime.now().strftime(TIMESTAMP_FORMAT)}] [{level}] {message}")

def log_error(message, exception=None):
    """Registra un messaggio di errore con dettagli opzionali dell'eccezione.
    
    Args:
        message (str): Messaggio di errore
        exception (Exception, optional): Eccezione da includere nei dettagli
    """
    error_msg = message
    if exception:
        error_msg += f" - Dettagli: {str(exception)}"
    
    log_message(error_msg, "ERROR")
    
    # Aggiorna statistiche errori
    stats['total_errors'] += 1

def log_warning(message):
    """Registra un messaggio di warning.
    
    Args:
        message (str): Messaggio di warning
    """
    log_message(message, "WARNING")

def log_debug(message):
    """Registra un messaggio di debug.
    
    Args:
        message (str): Messaggio di debug
    """
    log_message(message, "DEBUG")

def log_startup_messages():
    """Registra i messaggi di avvio del sistema."""
    from config import STARTUP_MESSAGES
    
    log_message("", include_separator=True)
    log_message(STARTUP_MESSAGES['title'])
    log_message(STARTUP_MESSAGES['target'])
    log_message(STARTUP_MESSAGES['objective'])
    log_message(STARTUP_MESSAGES['mode'])
    log_message(STARTUP_MESSAGES['interval'])
    log_message(STARTUP_MESSAGES['interrupt'])
    log_message("", include_separator=True)

def update_scan_stats(scan_successful=True, scan_time=None):
    """Aggiorna le statistiche di scansione.
    
    Args:
        scan_successful (bool): Se la scansione è stata completata con successo
        scan_time (float, optional): Tempo impiegato per la scansione in secondi
    """
    stats['total_scans'] += 1
    
    if scan_successful:
        stats['successful_detections'] += 1
        stats['consecutive_failures'] = 0
    else:
        stats['failed_scans'] += 1
        stats['consecutive_failures'] += 1
        
        # Aggiorna il massimo di fallimenti consecutivi
        if stats['consecutive_failures'] > stats['max_consecutive_failures']:
            stats['max_consecutive_failures'] = stats['consecutive_failures']
    
    # Aggiorna metriche di performance se fornito il tempo
    if scan_time is not None:
        update_performance_stats(scan_time)

def update_performance_stats(scan_time):
    """Aggiorna le statistiche di performance con il tempo di scansione.
    
    Args:
        scan_time (float): Tempo di scansione in secondi
    """
    try:
        metrics = stats['performance_metrics']
        
        # Aggiungi il nuovo tempo alla lista
        metrics['scan_times'].append(scan_time)
        
        # Mantieni solo gli ultimi N tempi per efficienza
        if len(metrics['scan_times']) > MAX_SCAN_TIMES_HISTORY:
            metrics['scan_times'] = metrics['scan_times'][-MAX_SCAN_TIMES_HISTORY:]
        
        # Calcola statistiche
        if metrics['scan_times']:
            metrics['avg_scan_time'] = sum(metrics['scan_times']) / len(metrics['scan_times'])
            metrics['max_scan_time'] = max(metrics['max_scan_time'], scan_time)
            
            if metrics['min_scan_time'] == float('inf'):
                metrics['min_scan_time'] = scan_time
            else:
                metrics['min_scan_time'] = min(metrics['min_scan_time'], scan_time)
        
        log_debug(f"Tempo scansione: {scan_time:.2f}s (Media: {metrics['avg_scan_time']:.2f}s)")
        
    except Exception as e:
        log_error(f"Errore aggiornamento statistiche performance: {e}")

def record_successful_detection():
    """Registra una detection di successo."""
    stats['last_successful_detection'] = time.time()
    log_message("✅ Detection del messaggio target completata con successo!")

def record_click_performed():
    """Registra un click eseguito."""
    stats['clicks_performed'] += 1
    stats['last_click_time'] = time.time()
    log_message(f"🖱️ Click automatico eseguito! (Totale: {stats['clicks_performed']})")

def record_click_error():
    """Registra un errore di click."""
    stats['click_errors'] += 1
    log_error("❌ Errore durante l'esecuzione del click automatico")

def record_screenshot_error():
    """Registra un errore di screenshot."""
    stats['screenshot_errors'] += 1
    log_error("📸 Errore durante la cattura dello screenshot")

def record_ocr_error():
    """Registra un errore OCR."""
    stats['ocr_errors'] += 1
    log_error("🔍 Errore durante l'estrazione del testo OCR")

def record_enhancement_error():
    """Registra un errore di enhancement immagine."""
    stats['enhancement_errors'] += 1
    log_error("🎨 Errore durante l'enhancement dell'immagine")

def get_uptime():
    """Calcola e restituisce l'uptime del sistema in secondi.
    
    Returns:
        float: Uptime in secondi
    """
    return time.time() - stats['start_time']

def format_uptime(uptime_seconds):
    """Formatta l'uptime in formato leggibile.
    
    Args:
        uptime_seconds (float): Uptime in secondi
        
    Returns:
        str: Uptime formattato (es. "2h 30m 45s")
    """
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def calculate_success_rate():
    """Calcola il tasso di successo delle scansioni.
    
    Returns:
        float: Tasso di successo in percentuale (0-100)
    """
    if stats['total_scans'] == 0:
        return 0.0
    return (stats['successful_detections'] / stats['total_scans']) * 100

def get_time_since_last_detection():
    """Calcola il tempo trascorso dall'ultima detection di successo.
    
    Returns:
        str: Tempo formattato o "Mai" se non ci sono state detection
    """
    if stats['last_successful_detection'] is None:
        return "Mai"
    
    time_diff = time.time() - stats['last_successful_detection']
    return format_uptime(time_diff)

def get_time_since_last_click():
    """Calcola il tempo trascorso dall'ultimo click.
    
    Returns:
        str: Tempo formattato o "Mai" se non ci sono stati click
    """
    if stats['last_click_time'] is None:
        return "Mai"
    
    time_diff = time.time() - stats['last_click_time']
    return format_uptime(time_diff)

def log_system_status():
    """Registra un report completo dello stato del sistema."""
    try:
        uptime = get_uptime()
        success_rate = calculate_success_rate()
        
        log_message("", include_separator=True)
        log_message("📊 REPORT STATO SISTEMA")
        log_message(f"⏱️ Uptime: {format_uptime(uptime)}")
        log_message(f"🔍 Scansioni totali: {stats['total_scans']}")
        log_message(f"✅ Detection riuscite: {stats['successful_detections']}")
        log_message(f"❌ Scansioni fallite: {stats['failed_scans']}")
        log_message(f"📈 Tasso di successo: {success_rate:.1f}%")
        log_message(f"🖱️ Click eseguiti: {stats['clicks_performed']}")
        log_message(f"🔄 Fallimenti consecutivi: {stats['consecutive_failures']}")
        log_message(f"📊 Max fallimenti consecutivi: {stats['max_consecutive_failures']}")
        
        # Statistiche errori
        log_message(f"🚨 Errori totali: {stats['total_errors']}")
        log_message(f"  📸 Errori screenshot: {stats['screenshot_errors']}")
        log_message(f"  🔍 Errori OCR: {stats['ocr_errors']}")
        log_message(f"  🖱️ Errori click: {stats['click_errors']}")
        log_message(f"  🎨 Errori enhancement: {stats['enhancement_errors']}")
        
        # Performance metrics
        metrics = stats['performance_metrics']
        if metrics['scan_times']:
            log_message(f"⚡ Performance scansioni:")
            log_message(f"  📊 Tempo medio: {metrics['avg_scan_time']:.2f}s")
            log_message(f"  ⚡ Tempo minimo: {metrics['min_scan_time']:.2f}s")
            log_message(f"  🐌 Tempo massimo: {metrics['max_scan_time']:.2f}s")
        
        # Tempi ultima attività
        log_message(f"🕐 Ultima detection: {get_time_since_last_detection()} fa")
        log_message(f"🕐 Ultimo click: {get_time_since_last_click()} fa")
        
        log_message("", include_separator=True)
        
    except Exception as e:
        log_error(f"Errore durante la generazione del report di stato: {e}")

def should_log_status_report():
    """Determina se è il momento di registrare un report di stato.
    
    Returns:
        bool: True se dovrebbe essere registrato un report
    """
    return stats['total_scans'] > 0 and stats['total_scans'] % STATUS_REPORT_FREQUENCY == 0

def reset_consecutive_failures():
    """Resetta il contatore dei fallimenti consecutivi."""
    stats['consecutive_failures'] = 0
    log_message("🔄 Contatore fallimenti consecutivi resettato")

def get_stats_copy():
    """Restituisce una copia delle statistiche correnti.
    
    Returns:
        dict: Copia delle statistiche
    """
    return stats.copy()

def log_scan_start(scan_number):
    """Registra l'inizio di una nuova scansione.
    
    Args:
        scan_number (int): Numero della scansione
    """
    log_message(f"🔍 Avvio scansione #{scan_number}...")

def log_scan_complete(scan_number, found_target=False, coordinates=None):
    """Registra il completamento di una scansione.
    
    Args:
        scan_number (int): Numero della scansione
        found_target (bool): Se il target è stato trovato
        coordinates (tuple, optional): Coordinate trovate
    """
    if found_target and coordinates:
        log_message(f"✅ Scansione #{scan_number} completata - Target trovato alle coordinate {coordinates}")
    else:
        log_message(f"❌ Scansione #{scan_number} completata - Target non trovato")

def log_enhancement_stats(method_name, detections_count):
    """Registra le statistiche di enhancement per un metodo specifico.
    
    Args:
        method_name (str): Nome del metodo di enhancement
        detections_count (int): Numero di detection trovate
    """
    log_debug(f"Enhancement {method_name}: {detections_count} detection valide")

def log_coordinates_found(word, coordinates):
    """Registra il ritrovamento di coordinate per una parola.
    
    Args:
        word (str): Parola trovata
        coordinates (tuple): Coordinate (x, y)
    """
    log_message(f"🎯 Coordinate trovate per '{word}': {coordinates}")

def log_extended_wait_start():
    """Registra l'inizio di un'attesa estesa."""
    from config import EXTENDED_WAIT_TIME
    log_message(f"⏳ Troppi fallimenti consecutivi. Attesa estesa di {EXTENDED_WAIT_TIME//60} minuti...")

def log_extended_wait_complete():
    """Registra il completamento di un'attesa estesa."""
    log_message("✅ Attesa estesa completata. Ripresa scansioni normali.")

def setup_logging():
    """Inizializza il sistema di logging.
    
    Crea il file di log se non esiste e registra l'avvio del sistema.
    """
    try:
        # Crea la directory del log se non esiste
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Registra l'avvio del sistema
        log_message("🚀 Sistema di rilevamento automatico avviato", include_separator=True)
        log_message(f"📁 File di log: {LOG_FILE}")
        
    except Exception as e:
        print(f"Errore durante inizializzazione logging: {e}")

def log_system_startup():
    """Registra l'avvio del sistema con informazioni dettagliate."""
    log_message("🚀 Sistema di rilevamento automatico avviato", include_separator=True)
    log_message(f"📁 File di log: {LOG_FILE}")
    log_message(f"⏰ Avvio: {datetime.now().strftime(TIMESTAMP_FORMAT)}")

def log_system_shutdown():
    """Registra l'arresto del sistema."""
    uptime = get_uptime()
    log_message("🛑 Sistema di rilevamento automatico arrestato", include_separator=True)
    log_message(f"⏱️ Uptime totale: {format_uptime(uptime)}")
    log_message(f"🔍 Scansioni totali: {stats['total_scans']}")
    log_message(f"✅ Detection riuscite: {stats['successful_detections']}")

def log_scan_interval(scan_number, interval_minutes):
    """Registra l'intervallo di scansione."""
    log_message(f"⏰ Prossima scansione #{scan_number} tra {interval_minutes} minuti...")

def should_log_status_report():
    """Determina se è il momento di registrare un report di stato."""
    return stats['total_scans'] % STATUS_REPORT_FREQUENCY == 0

def get_stats_copy():
    """Restituisce una copia delle statistiche correnti."""
    return stats.copy()