import pyautogui
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
import datetime
import os
import re
import time
import glob
from typing import List, Tuple, Dict

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def log_message(message, log_file="log.txt"):
    """Scrive messaggi nel file di log con timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

def manage_screenshots_folder():
    """Crea la cartella screenshots e mantiene solo le ultime 10 immagini"""
    screenshots_dir = "screenshots"
    
    # Crea la cartella se non esiste
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        log_message(f"📁 Cartella '{screenshots_dir}' creata")
    
    # Trova tutti i file di screenshot esistenti
    screenshot_patterns = [
        os.path.join(screenshots_dir, "debug_fullscreen_*.png"),
        os.path.join(screenshots_dir, "debug_enhanced_*.png")
    ]
    
    all_screenshots = []
    for pattern in screenshot_patterns:
        all_screenshots.extend(glob.glob(pattern))
    
    # Ordina per data di modifica (più recenti per ultimi)
    all_screenshots.sort(key=lambda x: os.path.getmtime(x))
    
    # Se ci sono più di 10 screenshot, elimina i più vecchi
    if len(all_screenshots) > 10:
        files_to_delete = all_screenshots[:-10]  # Tutti tranne gli ultimi 10
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                log_message(f"🗑️  Screenshot vecchio eliminato: {os.path.basename(file_path)}")
            except Exception as e:
                log_message(f"⚠️  Errore eliminando {os.path.basename(file_path)}: {e}")
        
        log_message(f"📊 Mantenuti {len(all_screenshots) - len(files_to_delete)} screenshot più recenti")
    
    return screenshots_dir

def enhance_image_for_text_detection(image):
    """
    Applica multiple tecniche di enhancement per migliorare la detection del testo UI
    Restituisce una lista di immagini processate con tecniche diverse
    """
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    
    img_np = np.array(image)
    
    # Converti in scala di grigi se necessario
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    
    enhanced_images = []
    
    # Versione 1: Contrasto adattivo con CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced_1 = clahe.apply(gray)
    enhanced_images.append(('clahe', enhanced_1))
    
    # Versione 2: Threshold adattivo per testo scuro su chiaro
    thresh_dark_on_light = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                cv2.THRESH_BINARY, 11, 2)
    enhanced_images.append(('dark_on_light', thresh_dark_on_light))
    
    # Versione 3: Threshold adattivo per testo chiaro su scuro
    thresh_light_on_dark = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                cv2.THRESH_BINARY_INV, 11, 2)
    enhanced_images.append(('light_on_dark', thresh_light_on_dark))
    
    # Versione 4: Originale con leggero denoising
    denoised = cv2.medianBlur(gray, 3)
    enhanced_images.append(('denoised_original', denoised))
    
    return enhanced_images

def extract_all_text_with_positions(image, method_name="unknown"):
    """
    Estrae tutto il testo dall'immagine con posizioni precise usando configurazioni OCR multiple
    """
    all_detections = []
    
    # Multiple configurazioni OCR per catturare diversi tipi di layout di testo
    ocr_configs = [
        ('psm_6', r'--oem 3 --psm 6'),  # Blocco uniforme di testo
        ('psm_7', r'--oem 3 --psm 7'),  # Singola linea di testo  
        ('psm_8', r'--oem 3 --psm 8'),  # Singola parola
        ('psm_11', r'--oem 3 --psm 11'), # Testo sparso
        ('psm_13', r'--oem 3 --psm 13')  # Singola linea raw, ordine di lettura
    ]
    
    for config_name, config_string in ocr_configs:
        try:
            # Usa pytesseract per ottenere dati strutturati con posizioni
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, 
                                           config=config_string, lang='eng')
            
            # Processa ogni elemento di testo rilevato
            for i in range(len(data['text'])):
                text = str(data['text'][i]).strip()
                confidence = int(data['conf'][i])
                
                # Filtra testo vuoto e confidence troppo bassa
                if text and confidence > 15:  # Soglia di confidence relativamente permissiva
                    detection = {
                        'text': text,
                        'left': int(data['left'][i]),
                        'top': int(data['top'][i]),
                        'width': int(data['width'][i]),
                        'height': int(data['height'][i]),
                        'confidence': confidence,
                        'right': int(data['left'][i]) + int(data['width'][i]),
                        'bottom': int(data['top'][i]) + int(data['height'][i]),
                        'method': method_name,
                        'ocr_config': config_name
                    }
                    all_detections.append(detection)
                    
        except Exception as e:
            log_message(f"Errore con configurazione OCR {config_name} su {method_name}: {e}")
            continue
    
    return all_detections

def find_target_message_pattern(text_detections: List[Dict]) -> List[Tuple[int, int]]:
    """
    Cerca il pattern esatto 'Model thinking limit reached, please enter 'Continue' to'
    e restituisce le coordinate della fine della parola 'to' per ogni occorrenza trovata
    """
    target_coordinates = []
    
    # Pattern da cercare - usiamo regex flessibili per variazioni di punteggiatura/spaziatura
    target_patterns = [
        r"model\s+thinking\s+limit\s+reached.*?please\s+enter.*?continue.*?to\b",
        r"thinking\s+limit\s+reached.*?enter.*?continue.*?to\b",
        r"limit\s+reached.*?please.*?continue.*?to\b"
    ]
    
    # Ordina le detection per posizione (dall'alto a sinistra verso il basso a destra)
    sorted_detections = sorted(text_detections, key=lambda x: (x['top'], x['left']))
    
    # Costruisce il testo completo con mappatura delle posizioni
    full_text_parts = []
    word_positions = {}  # Mappa parola -> lista di posizioni possibili
    
    for detection in sorted_detections:
        word = detection['text'].lower().strip('.,!?;:"\'')
        full_text_parts.append(word)
        
        # Memorizza tutte le posizioni di ogni parola (potrebbero esserci duplicati)
        if word not in word_positions:
            word_positions[word] = []
        word_positions[word].append(detection)
    
    # Crea il testo continuo per il pattern matching
    full_text = ' '.join(full_text_parts)
    log_message(f"Testo completo ricostruito: {full_text}")
    
    # Cerca ogni pattern target
    for pattern_idx, pattern in enumerate(target_patterns):
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        
        for match in matches:
            log_message(f"✅ PATTERN {pattern_idx+1} TROVATO: '{match.group()}'")
            log_message(f"   Posizione nel testo: {match.start()}-{match.end()}")
            
            # Ora dobbiamo trovare la specifica parola "to" che fa parte di questo match
            # Cerchiamo le parole "to" che sono vicine temporalmente/spazialmente al resto del pattern
            
            # Estratte le parole chiave del match per localizzare la regione
            match_text = match.group().lower()
            
            if 'to' in match_text:
                # Trova tutte le occorrenze di "to" nelle detection
                to_candidates = word_positions.get('to', [])
                
                for to_detection in to_candidates:
                    # Verifica che questo "to" sia effettivamente parte del messaggio target
                    # controllando che ci siano parole chiave del pattern nelle vicinanze
                    
                    nearby_words = []
                    to_area = {
                        'left': to_detection['left'] - 200,   # Area di ricerca intorno al "to"
                        'right': to_detection['right'] + 200,
                        'top': to_detection['top'] - 50,
                        'bottom': to_detection['bottom'] + 50
                    }
                    
                    # Cerca parole chiave nell'area vicina al "to"
                    for detection in sorted_detections:
                        if (to_area['left'] <= detection['left'] <= to_area['right'] and
                            to_area['top'] <= detection['top'] <= to_area['bottom']):
                            nearby_words.append(detection['text'].lower())
                    
                    nearby_text = ' '.join(nearby_words)
                    
                    # Verifica che ci siano abbastanza parole chiave nelle vicinanze
                    key_words = ['model', 'thinking', 'limit', 'reached', 'please', 'enter', 'continue']
                    found_key_words = sum(1 for word in key_words if word in nearby_text)
                    
                    if found_key_words >= 4:  # Almeno 4 parole chiave devono essere presenti
                        # Calcola coordinate della fine della parola "to"
                        x = to_detection['left']
                        x_final = x + 60
                        to_center_y = to_detection['top'] + to_detection['height'] // 2
                        
                        log_message(f"✅ VALIDO 'to' trovato a: ({x_final}, {to_center_y})")
                        log_message(f"   Parole chiave nelle vicinanze: {found_key_words}/7")
                        log_message(f"   Contesto: {nearby_text[:100]}...")
                        
                        target_coordinates.append((x_final, to_center_y))
    
    return target_coordinates

def deduplicate_final_coordinates(coordinates: List[Tuple[int, int]], tolerance: int = 5) -> List[Tuple[int, int]]:
    """
    Rimuove coordinate duplicate che sono troppo vicine tra loro.
    Due coordinate sono considerate duplicate se distano meno di 'tolerance' pixel.
    Mantiene la coordinata che rappresenta la media delle posizioni duplicate.
    """
    if not coordinates:
        return coordinates
    
    log_message(f"Deduplicazione coordinate con tolleranza {tolerance} pixel...")
    
    deduplicated = []
    used_indices = set()
    
    for i, (x1, y1) in enumerate(coordinates):
        if i in used_indices:
            continue
            
        # Trova tutte le coordinate simili a questa
        cluster = [(x1, y1)]
        cluster_indices = {i}
        
        for j, (x2, y2) in enumerate(coordinates):
            if j <= i or j in used_indices:
                continue
                
            # Calcola distanza euclidea
            distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            
            if distance <= tolerance:
                cluster.append((x2, y2))
                cluster_indices.add(j)
                used_indices.add(j)
        
        used_indices.update(cluster_indices)
        
        # Calcola coordinate media del cluster
        avg_x = int(sum(x for x, y in cluster) / len(cluster))
        avg_y = int(sum(y for x, y in cluster) / len(cluster))
        
        deduplicated.append((avg_x, avg_y))
        
        if len(cluster) > 1:
            log_message(f"Cluster di {len(cluster)} coordinate simili:")
            for x, y in cluster:
                log_message(f"  ({x}, {y})")
            log_message(f"  -> Coordinata media: ({avg_x}, {avg_y})")
    
    log_message(f"Coordinate prima deduplicazione: {len(coordinates)}")
    log_message(f"Coordinate dopo deduplicazione: {len(deduplicated)}")
    
    return deduplicated

def scan_entire_screen_for_continue_message() -> List[Tuple[int, int]]:
    """
    Scansiona l'intero schermo alla ricerca del messaggio target
    Restituisce lista delle coordinate (x,y) della fine di ogni 'to' trovato
    """
    log_message("="*80)
    log_message("INIZIO SCANSIONE COMPLETA SCHERMO")
    log_message("="*80)
    
    # Gestisci cartella screenshots e pulizia
    screenshots_dir = manage_screenshots_folder()
    
    # Screenshot dell'intero schermo
    log_message("Cattura screenshot schermo completo...")
    screenshot = pyautogui.screenshot()
    
    # Salva screenshot per debug nella cartella screenshots
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    debug_filename = os.path.join(screenshots_dir, f"debug_fullscreen_{timestamp}.png")
    screenshot.save(debug_filename)
    log_message(f"Screenshot salvato: {debug_filename}")
    
    width, height = screenshot.size
    log_message(f"Dimensioni schermo: {width} x {height} pixels")
    
    # Applica diverse tecniche di enhancement
    log_message("Applicazione tecniche di enhancement dell'immagine...")
    enhanced_versions = enhance_image_for_text_detection(screenshot)
    
    all_text_detections = []
    
    # Analizza ogni versione enhanced dell'immagine
    for method_name, enhanced_image in enhanced_versions:
        log_message(f"\n--- ANALISI METODO: {method_name.upper()} ---")
        
        # Salva versione enhanced per debug nella cartella screenshots
        enhanced_filename = os.path.join(screenshots_dir, f"debug_enhanced_{method_name}_{timestamp}.png")
        if isinstance(enhanced_image, np.ndarray):
            cv2.imwrite(enhanced_filename, enhanced_image)
        else:
            enhanced_image.save(enhanced_filename)
        
        # Estrai tutto il testo con posizioni
        detections = extract_all_text_with_positions(enhanced_image, method_name)
        log_message(f"Rilevate {len(detections)} parole con {method_name}")
        
        # Aggiungi tutte le detection alla lista completa
        all_text_detections.extend(detections)
    
    # Rimuovi duplicati basati su posizione simile
    log_message(f"\nTotale detection prima deduplicazione: {len(all_text_detections)}")
    
    # Deduplicazione: se due detection hanno posizione molto simile, tieni quella con confidence maggiore
    deduplicated_detections = []
    for detection in all_text_detections:
        is_duplicate = False
        for existing in deduplicated_detections:
            # Considera duplicato se è nella stessa area approssimativa
            if (abs(detection['left'] - existing['left']) < 10 and 
                abs(detection['top'] - existing['top']) < 10 and
                detection['text'].lower() == existing['text'].lower()):
                is_duplicate = True
                # Se la nuova detection ha confidence maggiore, sostituisci
                if detection['confidence'] > existing['confidence']:
                    deduplicated_detections.remove(existing)
                    deduplicated_detections.append(detection)
                break
        
        if not is_duplicate:
            deduplicated_detections.append(detection)
    
    log_message(f"Detection dopo deduplicazione: {len(deduplicated_detections)}")
    
    # Log di tutte le parole rilevate per debug
    log_message("\n--- TUTTE LE PAROLE RILEVATE ---")
    for detection in sorted(deduplicated_detections, key=lambda x: (x['top'], x['left']))[:50]:  # Primi 50 per non intasare il log
        log_message(f"'{detection['text']}' @ ({detection['left']},{detection['top']}) "
                   f"conf:{detection['confidence']} [{detection['method']}-{detection['ocr_config']}]")
    
    if len(deduplicated_detections) > 50:
        log_message(f"... e altre {len(deduplicated_detections) - 50} parole")
    
    # Cerca il pattern target nelle detection
    log_message(f"\n--- RICERCA PATTERN TARGET ---")
    raw_target_coordinates = find_target_message_pattern(deduplicated_detections)
    
    # Applica deduplicazione finale alle coordinate trovate
    log_message(f"\n--- DEDUPLICAZIONE FINALE COORDINATE ---")
    target_coordinates = deduplicate_final_coordinates(raw_target_coordinates, tolerance=5)
    
    if target_coordinates:
        log_message(f"\n✅ TROVATE {len(target_coordinates)} OCCORRENZE UNICHE DEL MESSAGGIO TARGET!")
        for i, (x, y) in enumerate(target_coordinates):
            log_message(f"   Occorrenza {i+1}: coordinate fine 'to' = ({x}, {y})")
    else:
        log_message(f"\n❌ NESSUNA OCCORRENZA DEL MESSAGGIO TARGET TROVATA")
        log_message("Il messaggio 'Model thinking limit reached, please enter 'Continue' to' non è presente sullo schermo")
    
    return target_coordinates

# Esecuzione principale
if __name__ == "__main__":
    # Pulisci log precedente
    if os.path.exists("log.txt"):
        os.remove("log.txt")
    
    log_message("🚀 AVVIO SCANNER AUTOMATICO OGNI 2 MINUTI PER MESSAGGIO 'Continue'")
    log_message("Target: 'Model thinking limit reached, please enter 'Continue' to'")
    log_message("Obiettivo: trovare coordinate della fine della parola 'to' e cliccare automaticamente")
    log_message("Modalità: AUTOMATICA - Click automatico senza conferma")
    log_message("Intervallo: ogni 2 minuti (120 secondi)")
    log_message("Per interrompere: Ctrl+C")
    
    scan_count = 0
    
    try:
        while True:
            scan_count += 1
            log_message(f"\n" + "="*80)
            log_message(f"SCANSIONE #{scan_count} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log_message("="*80)
            
            coordinates_list = scan_entire_screen_for_continue_message()
            
            log_message("\n" + "="*80)
            log_message("RISULTATI FINALI")
            log_message("="*80)
            
            if coordinates_list:
                log_message(f"✅ TROVATE {len(coordinates_list)} OCCORRENZE:")
                for i, (x, y) in enumerate(coordinates_list):
                    log_message(f"   {i+1}. Coordinate fine 'to': ({x}, {y})")
                
                # Click automatico sulla prima coordinata trovata
                if len(coordinates_list) >= 1:
                    x, y = coordinates_list[0]
                    log_message(f"\n🎯 CLICK AUTOMATICO su ({x}, {y})")
                    pyautogui.click(x, y)
                    log_message("✅ Click eseguito automaticamente!")
                    
                    if len(coordinates_list) > 1:
                        log_message(f"ℹ️  Altre {len(coordinates_list)-1} occorrenze ignorate (click solo sulla prima)")
            else:
                log_message("❌ NESSUN MESSAGGIO TARGET TROVATO SULLO SCHERMO")
                log_message("Il messaggio potrebbe non essere presente, o potrebbe non essere visibile/leggibile dall'OCR")
            
            log_message(f"\n⏰ Prossima scansione tra 2 minuti... (Scansione #{scan_count+1})")
            log_message("💡 Premi Ctrl+C per interrompere")
            
            # Attendi 2 minuti (120 secondi)
            time.sleep(120)
            
    except KeyboardInterrupt:
        log_message("\n\n🛑 INTERRUZIONE MANUALE RICEVUTA (Ctrl+C)")
        log_message(f"📊 Totale scansioni eseguite: {scan_count}")
        log_message("🏁 SCANNER AUTOMATICO TERMINATO")