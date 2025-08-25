"""Configurazioni globali per il sistema di rilevamento automatico.

Questo modulo contiene tutte le configurazioni, costanti e impostazioni
globali utilizzate dal sistema di rilevamento automatico del messaggio 'Continue'.
"""

import time
import pytesseract
import pyautogui

# ============================================================================
# CONFIGURAZIONI TESSERACT
# ============================================================================

# Percorso dell'eseguibile Tesseract OCR
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ============================================================================
# CONFIGURAZIONI PYAUTOGUI
# ============================================================================

# Configurazioni di sicurezza per pyautogui
FAILSAFE_ENABLED = True    # Muovi mouse nell'angolo per interrompere
PAUSE_BETWEEN_ACTIONS = 0.5  # Pausa tra azioni per stabilità

# Applica configurazioni
pyautogui.FAILSAFE = FAILSAFE_ENABLED
pyautogui.PAUSE = PAUSE_BETWEEN_ACTIONS

# ============================================================================
# CONFIGURAZIONI RETRY E TIMEOUT
# ============================================================================

# Configurazioni per retry automatici
MAX_RETRIES = 3
RETRY_DELAY = 5  # secondi
CLICK_VALIDATION_TIMEOUT = 2  # secondi
SCREENSHOT_MAX_RETRIES = 3

# Configurazioni per gestione fallimenti consecutivi
MAX_CONSECUTIVE_FAILURES = 5
EXTENDED_WAIT_TIME = 300  # 5 minuti in secondi

# ============================================================================
# CONFIGURAZIONI SCANSIONE
# ============================================================================

# Intervallo tra scansioni
SCAN_INTERVAL = 120  # 2 minuti in secondi

# Frequenza report stato sistema
STATUS_REPORT_FREQUENCY = 10  # ogni N scansioni

# ============================================================================
# CONFIGURAZIONI OCR
# ============================================================================

# Configurazioni OCR per massimizzare il rilevamento
OCR_CONFIGS = [
    '--psm 6',   # Assume un singolo blocco di testo uniforme
    '--psm 8',   # Tratta l'immagine come una singola parola
    '--psm 7',   # Tratta l'immagine come una singola riga di testo
    '--psm 11',  # Trova il testo sparso
    '--psm 12',  # Trova il testo sparso con OSD
    '--psm 13'   # Riga grezza. Tratta l'immagine come una singola riga di testo
]

# Soglia minima di confidence per accettare una detection
MIN_CONFIDENCE_THRESHOLD = 15

# ============================================================================
# CONFIGURAZIONI DEDUPLICAZIONE
# ============================================================================

# Distanza minima tra detection per considerarle duplicate
DEDUPLICATION_DISTANCE_THRESHOLD = 20
FINAL_COORDINATES_TOLERANCE = 5

# ============================================================================
# CONFIGURAZIONI ENHANCEMENT IMMAGINI
# ============================================================================

# Parametri per CLAHE (Contrast Limited Adaptive Histogram Equalization)
CLAHE_CLIP_LIMIT = 3.0
CLAHE_TILE_GRID_SIZE = (8, 8)

# Parametri per threshold adattivo
ADAPTIVE_THRESHOLD_MAX_VALUE = 255
ADAPTIVE_THRESHOLD_BLOCK_SIZE = 11
ADAPTIVE_THRESHOLD_C = 2

# Parametri per filtri
GAUSSIAN_BLUR_KERNEL_SIZE = (5, 5)
MORPHOLOGY_KERNEL_SIZE = (2, 2)
MEDIAN_BLUR_KERNEL_SIZE = 3
BILATERAL_FILTER_D = 9
BILATERAL_FILTER_SIGMA_COLOR = 75
BILATERAL_FILTER_SIGMA_SPACE = 75

# Kernel per sharpening
SHARPENING_KERNEL = [[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]

# ============================================================================
# CONFIGURAZIONI GESTIONE SCREENSHOT
# ============================================================================

# Cartella per salvare gli screenshot
SCREENSHOTS_FOLDER = "screenshots"

# Numero massimo di screenshot da mantenere
MAX_SCREENSHOTS_TO_KEEP = 10

# Pattern per nomi file screenshot
SCREENSHOT_FULLSCREEN_PATTERN = "debug_fullscreen_{timestamp}.png"
SCREENSHOT_ENHANCED_PATTERN = "debug_enhanced_{method_name}_{timestamp}.png"

# ============================================================================
# CONFIGURAZIONI LOGGING
# ============================================================================

# File di log principale
LOG_FILE = "log.txt"

# Formato timestamp per log
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
FILE_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# ============================================================================
# CONFIGURAZIONI TARGET MESSAGE
# ============================================================================

# Messaggio target da cercare
TARGET_MESSAGE = "Model thinking limit reached, please enter 'Continue' to"

# Pattern regex per trovare il messaggio target
TARGET_PATTERN = r"Model\s+thinking\s+limit\s+reached.*?Continue.*?to"

# Parola finale di cui trovare le coordinate
TARGET_END_WORD = "to"

# ============================================================================
# CONFIGURAZIONI STATISTICHE
# ============================================================================

# Numero massimo di tempi di scansione da mantenere per calcolare la media
MAX_SCAN_TIMES_HISTORY = 100

# ============================================================================
# INIZIALIZZAZIONE STATISTICHE GLOBALI
# ============================================================================

def get_initial_stats():
    """Restituisce la struttura iniziale delle statistiche globali."""
    return {
        'total_scans': 0,
        'successful_detections': 0,
        'clicks_performed': 0,
        'failed_scans': 0,
        'consecutive_failures': 0,
        'max_consecutive_failures': 0,
        'total_errors': 0,
        'screenshot_errors': 0,
        'ocr_errors': 0,
        'click_errors': 0,
        'enhancement_errors': 0,
        'start_time': time.time(),
        'last_successful_detection': None,
        'last_click_time': None,
        'performance_metrics': {
            'avg_scan_time': 0,
            'scan_times': [],
            'max_scan_time': 0,
            'min_scan_time': float('inf')
        }
    }

# ============================================================================
# CONFIGURAZIONI DIMENSIONI MINIME
# ============================================================================

# Dimensioni minime per considerare un'immagine valida
MIN_IMAGE_WIDTH = 10
MIN_IMAGE_HEIGHT = 10

# ============================================================================
# MESSAGGI DI SISTEMA
# ============================================================================

# Messaggi di avvio
STARTUP_MESSAGES = {
    'title': "🚀 AVVIO SCANNER AUTOMATICO OGNI 2 MINUTI PER MESSAGGIO 'Continue'",
    'target': f"Target: '{TARGET_MESSAGE}'",
    'objective': f"Obiettivo: trovare coordinate della fine della parola '{TARGET_END_WORD}' e cliccare automaticamente",
    'mode': "Modalità: AUTOMATICA - Click automatico senza conferma",
    'interval': f"Intervallo: ogni 2 minuti ({SCAN_INTERVAL} secondi)",
    'interrupt': "Per interrompere: Ctrl+C"
}

# Separatori per log
LOG_SEPARATOR = "=" * 80
SUB_SEPARATOR = "-" * 40