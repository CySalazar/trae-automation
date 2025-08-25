#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic Detection and Click System for "Continue" Messages

This script automatically scans the screen for specific text patterns and performs
automatic clicks when the target message is detected. It's designed to be robust,
with comprehensive error handling, retry mechanisms, and performance monitoring.

Features:
- Automatic screen scanning with configurable intervals
- Multiple image enhancement techniques for better OCR accuracy
- Robust error handling and retry mechanisms
- Performance monitoring and statistics
- Safe coordinate validation and click operations
- Comprehensive logging system
- Modular architecture with separated responsibilities

Usage:
    python detect.py

The script will run continuously, scanning for the target message every 2 minutes
and automatically clicking when found.
"""

import sys
import time
import signal
from datetime import datetime

# Import modular components
try:
    from config import (
        SCAN_INTERVAL, TARGET_PATTERN, TARGET_END_WORD,
        MAX_CONSECUTIVE_FAILURES, EXTENDED_WAIT_TIME
    )
    from logger import (
        setup_logging, log_message, log_error, log_debug,
        log_system_startup, log_system_shutdown, log_scan_interval,
        should_log_status_report, log_system_status, get_stats_copy
    )
    from scanner import (
        perform_scan_with_retry, handle_scan_result, handle_consecutive_failures,
        get_next_scan_number, is_system_healthy, log_scan_summary
    )
except ImportError as e:
    print(f"Error importing modular components: {e}")
    print("Please ensure all required modules are in the same directory:")
    print("- config.py")
    print("- logger.py")
    print("- image_processing.py")
    print("- ocr_engine.py")
    print("- coordinate_manager.py")
    print("- scanner.py")
    sys.exit(1)

# Third-party imports for safety configuration
try:
    import pyautogui
except ImportError as e:
    print(f"Error importing pyautogui: {e}")
    print("Please install required packages: pip install pyautogui")
    sys.exit(1)

# Configure pyautogui safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# ============================================================================
# SIGNAL HANDLERS
# ============================================================================

def signal_handler(signum, frame):
    """Gestisce i segnali di interruzione per shutdown pulito."""
    try:
        log_message("\n\n🛑 INTERRUZIONE RICEVUTA")
        log_system_status()
        log_system_shutdown()
        sys.exit(0)
    except Exception as e:
        print(f"Errore durante shutdown: {e}")
        sys.exit(1)

# ============================================================================
# MAIN SCANNING LOOP
# ============================================================================

def run_continuous_scanner():
    """Esegue il loop principale di scansione continua."""
    try:
        log_system_startup()
        log_message(f"🎯 Target: '{TARGET_PATTERN}'")
        log_message(f"🔍 Parola finale: '{TARGET_END_WORD}'")
        log_message("🤖 Modalità: AUTOMATICA - Click automatico senza conferma")
        log_message("💡 Per interrompere: Ctrl+C")
        log_message("\n" + "="*80)
        
        while True:
            try:
                # Verifica salute del sistema
                if not is_system_healthy():
                    log_error("Sistema non sano, continuazione con cautela...")
                
                # Ottieni numero scansione
                scan_number = get_next_scan_number()
                
                # Esegui scansione con retry
                scan_start_time = time.time()
                success, coordinates = perform_scan_with_retry(scan_number)
                scan_time = time.time() - scan_start_time
                
                # Gestisci risultato scansione
                click_performed = False
                if success:
                    click_performed = handle_scan_result(scan_number, success, coordinates)
                
                # Log riassunto scansione
                log_scan_summary(scan_number, success, click_performed, scan_time)
                
                # Gestisci fallimenti consecutivi
                if not success:
                    extended_wait_performed = handle_consecutive_failures()
                    if extended_wait_performed:
                        continue  # Salta l'attesa normale se è stata fatta attesa estesa
                
                # Log report di stato periodico
                if should_log_status_report():
                    log_system_status()
                
                # Attesa prima della prossima scansione
                try:
                    next_scan_number = get_next_scan_number()
                    log_message(f"\n⏰ Prossima scansione #{next_scan_number} tra {SCAN_INTERVAL//60} minuti...")
                    log_message("💡 Premi Ctrl+C per interrompere")
                    time.sleep(SCAN_INTERVAL)
                except KeyboardInterrupt:
                    raise  # Rilancia per gestione nel blocco esterno
                except Exception as e:
                    log_error(f"Errore durante attesa: {e}")
                    time.sleep(10)  # Attesa ridotta in caso di errore
                
            except KeyboardInterrupt:
                raise  # Rilancia per gestione nel blocco esterno
            except Exception as e:
                log_error(f"Errore nel loop principale: {e}")
                time.sleep(5)  # Breve pausa prima di continuare
                continue
                
    except KeyboardInterrupt:
        log_message("\n\n🛑 INTERRUZIONE MANUALE RICEVUTA (Ctrl+C)")
        log_system_status()
        log_system_shutdown()
    except pyautogui.FailSafeException:
        log_message("\n\n🛑 FAILSAFE ATTIVATO - Mouse mosso nell'angolo")
        log_system_status()
        log_system_shutdown()
    except Exception as e:
        log_error(f"\n\n❌ ERRORE CRITICO NON GESTITO: {e}")
        log_system_status()
        log_message("🏁 SCANNER AUTOMATICO TERMINATO A CAUSA DI ERRORE CRITICO")
        sys.exit(1)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_system_requirements():
    """Valida che tutti i requisiti del sistema siano soddisfatti."""
    try:
        # Test import di tutti i moduli
        from config import TESSERACT_CMD
        from image_processing import safe_screenshot
        from ocr_engine import extract_all_text_with_positions
        from coordinate_manager import validate_coordinates
        
        # Test Tesseract
        import os
        if not os.path.exists(TESSERACT_CMD):
            log_error(f"Tesseract non trovato in: {TESSERACT_CMD}")
            return False
        
        # Test screenshot
        test_screenshot = safe_screenshot()
        if test_screenshot is None:
            log_error("Impossibile catturare screenshot di test")
            return False
        
        log_message("✅ Tutti i requisiti del sistema sono soddisfatti")
        return True
        
    except Exception as e:
        log_error(f"Errore validazione requisiti sistema: {e}")
        return False

def cleanup_on_exit():
    """Pulizia risorse prima dell'uscita."""
    try:
        log_debug("Pulizia risorse in corso...")
        # Eventuali operazioni di pulizia possono essere aggiunte qui
        log_debug("Pulizia completata")
    except Exception as e:
        log_error(f"Errore durante pulizia: {e}")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Punto di ingresso principale dell'applicazione."""
    try:
        # Setup logging
        setup_logging()
        
        # Registra signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Valida requisiti sistema
        if not validate_system_requirements():
            log_error("Validazione requisiti sistema fallita")
            sys.exit(1)
        
        # Avvia scanner continuo
        run_continuous_scanner()
        
    except Exception as e:
        print(f"Errore critico durante avvio: {e}")
        sys.exit(1)
    finally:
        cleanup_on_exit()

if __name__ == "__main__":
    main()