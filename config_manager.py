#!/usr/bin/env python3
"""
Dynamic Configuration Manager Module

This module provides dynamic configuration management for the automatic detection system.
It allows runtime modification of parameters, validation, persistence, and real-time
configuration updates without system restart.

Features:
- Runtime parameter modification
- Configuration validation
- Auto-save and persistence
- Configuration history and rollback
- Hot-reload capabilities
- Parameter constraints and validation
- Configuration profiles

Author: Matteo Sala
Version: 1.0.0
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from pathlib import Path
import copy

# Import static config for default values
try:
    import config as static_config
except ImportError:
    static_config = None

@dataclass
class ConfigParameter:
    """Configuration parameter with validation and metadata"""
    name: str
    value: Any
    default_value: Any
    description: str
    data_type: type
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None
    requires_restart: bool = False
    category: str = "general"
    validation_func: Optional[Callable] = None

@dataclass
class ConfigChange:
    """Record of a configuration change"""
    timestamp: float
    parameter_name: str
    old_value: Any
    new_value: Any
    user: str = "system"
    reason: str = ""

class ConfigurationManager:
    """Manages dynamic configuration for the detection system"""
    
    def __init__(self, config_file: str = "system_config.json", auto_save: bool = True):
        """
        Initialize the configuration manager
        
        Args:
            config_file: Path to configuration file
            auto_save: Whether to automatically save changes
        """
        self.config_file = Path(config_file)
        self.auto_save = auto_save
        self._lock = threading.RLock()
        
        # Configuration storage
        self.parameters: Dict[str, ConfigParameter] = {}
        self.change_history: List[ConfigChange] = []
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.current_profile = "default"
        
        # Change callbacks
        self.change_callbacks: Dict[str, List[Callable]] = {}
        
        # Initialize default parameters
        self._initialize_default_parameters()
        
        # Load existing configuration
        self.load_configuration()
        
        # Auto-save thread
        if auto_save:
            self.auto_save_thread = threading.Thread(target=self._auto_save_worker, daemon=True)
            self.auto_save_active = True
            self.auto_save_thread.start()
    
    def _initialize_default_parameters(self):
        """Initialize default system parameters"""
        # Scanning parameters
        scan_interval_default = getattr(static_config, 'SCAN_INTERVAL', 1.0) if static_config else 1.0
        self.register_parameter(
            "scan_interval", scan_interval_default, "Time between scans in seconds", float,
            min_value=0.1, max_value=60.0, category="scanning"
        )
        
        self.register_parameter(
            "max_scan_attempts", 3, "Maximum scan attempts before giving up", int,
            min_value=1, max_value=10, category="scanning"
        )
        
        self.register_parameter(
            "scan_timeout", 30.0, "Timeout for individual scans in seconds", float,
            min_value=5.0, max_value=300.0, category="scanning"
        )
        
        # OCR parameters
        ocr_confidence_default = getattr(static_config, 'MIN_CONFIDENCE_THRESHOLD', 0.7) if static_config else 0.7
        self.register_parameter(
            "ocr_confidence_threshold", ocr_confidence_default, "Minimum OCR confidence threshold", float,
            min_value=0.1, max_value=1.0, category="ocr"
        )
        
        ocr_language_default = getattr(static_config, 'OCR_LANGUAGE', 'eng') if static_config else 'eng'
        self.register_parameter(
            "ocr_language", ocr_language_default, "OCR language code", str,
            allowed_values=["eng", "ita", "fra", "deu", "spa"], category="ocr"
        )
        
        self.register_parameter(
            "ocr_psm_mode", 6, "Tesseract Page Segmentation Mode", int,
            min_value=0, max_value=13, category="ocr"
        )
        
        # Image processing parameters
        self.register_parameter(
            "image_scale_factor", 2.0, "Image scaling factor for better OCR", float,
            min_value=1.0, max_value=5.0, category="image_processing"
        )
        
        self.register_parameter(
            "gaussian_blur_kernel", 3, "Gaussian blur kernel size", int,
            min_value=1, max_value=15, category="image_processing"
        )
        
        self.register_parameter(
            "contrast_enhancement", True, "Enable contrast enhancement", bool,
            category="image_processing"
        )
        
        # Detection parameters
        target_message_default = getattr(static_config, 'TARGET_MESSAGE', 'Model thinking limit reached, please enter \'Continue\' to') if static_config else 'Continue'
        self.register_parameter(
            "target_message", target_message_default, "Target message to search for", str,
            category="detection"
        )
        
        target_end_word_default = getattr(static_config, 'TARGET_END_WORD', 'to') if static_config else 'to'
        self.register_parameter(
             "target_end_word", target_end_word_default, "Final word to find coordinates for", str,
             category="detection"
        )
        
        # Retry and timeout parameters
        max_retries_default = getattr(static_config, 'MAX_RETRIES', 3) if static_config else 3
        self.register_parameter(
            "max_retries", max_retries_default, "Maximum number of retry attempts", int,
            min_value=1, max_value=10, category="retry"
        )
        
        retry_delay_default = getattr(static_config, 'RETRY_DELAY', 1.0) if static_config else 1.0
        self.register_parameter(
            "retry_delay", retry_delay_default, "Delay between retry attempts in seconds", float,
            min_value=0.1, max_value=10.0, category="retry"
        )
        
        screenshot_timeout_default = getattr(static_config, 'SCREENSHOT_TIMEOUT', 5.0) if static_config else 5.0
        self.register_parameter(
            "screenshot_timeout", screenshot_timeout_default, "Screenshot operation timeout in seconds", float,
            min_value=1.0, max_value=30.0, category="timeout"
        )
        
        ocr_timeout_default = getattr(static_config, 'OCR_TIMEOUT', 10.0) if static_config else 10.0
        self.register_parameter(
            "ocr_timeout", ocr_timeout_default, "OCR operation timeout in seconds", float,
            min_value=1.0, max_value=60.0, category="timeout"
        )
        
        # Screenshot management
        screenshots_folder_default = getattr(static_config, 'SCREENSHOTS_FOLDER', 'screenshots') if static_config else 'screenshots'
        self.register_parameter(
            "screenshots_folder", screenshots_folder_default, "Folder to save screenshots", str,
            category="screenshots"
        )
        
        max_screenshots_default = getattr(static_config, 'MAX_SCREENSHOTS_TO_KEEP', 10) if static_config else 10
        self.register_parameter(
            "max_screenshots_to_keep", max_screenshots_default, "Maximum number of screenshots to keep", int,
            min_value=1, max_value=100, category="screenshots"
        )
        
        # Image enhancement parameters
        enable_enhancement_default = getattr(static_config, 'ENABLE_IMAGE_ENHANCEMENT', True) if static_config else True
        self.register_parameter(
            "enable_image_enhancement", enable_enhancement_default, "Enable image enhancement for better OCR", bool,
            category="enhancement"
        )
        
        contrast_factor_default = getattr(static_config, 'CONTRAST_FACTOR', 1.5) if static_config else 1.5
        self.register_parameter(
            "contrast_factor", contrast_factor_default, "Contrast enhancement factor", float,
            min_value=0.5, max_value=3.0, category="enhancement"
        )
        
        brightness_factor_default = getattr(static_config, 'BRIGHTNESS_FACTOR', 1.2) if static_config else 1.2
        self.register_parameter(
            "brightness_factor", brightness_factor_default, "Brightness enhancement factor", float,
            min_value=0.5, max_value=3.0, category="enhancement"
        )
        
        # Statistics parameters
        max_scan_times_history_default = getattr(static_config, 'MAX_SCAN_TIMES_HISTORY', 100) if static_config else 100
        self.register_parameter(
            "max_scan_times_history", max_scan_times_history_default, "Maximum number of scan times to keep for calculating average", int,
            min_value=10, max_value=1000, category="statistics"
        )
        
        self.register_parameter(
            "case_sensitive", False, "Case sensitive text matching", bool,
            category="detection"
        )
        
        self.register_parameter(
            "partial_match", True, "Allow partial text matching", bool,
            category="detection"
        )
        
        # Click parameters
        self.register_parameter(
            "click_delay", 0.1, "Delay before clicking in seconds", float,
            min_value=0.0, max_value=5.0, category="clicking"
        )
        
        self.register_parameter(
            "double_click_prevention", True, "Prevent accidental double clicks", bool,
            category="clicking"
        )
        
        self.register_parameter(
            "click_offset_x", 50, "X offset for click position", int,
            min_value=-50, max_value=50, category="clicking"
        )
        
        self.register_parameter(
            "click_offset_y", 0, "Y offset for click position", int,
            min_value=-50, max_value=50, category="clicking"
        )
        
        # Logging parameters
        self.register_parameter(
            "log_level", "INFO", "Logging level", str,
            allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            category="logging", requires_restart=True
        )
        
        self.register_parameter(
            "log_to_file", True, "Enable file logging", bool,
            category="logging"
        )
        
        self.register_parameter(
            "max_log_files", 10, "Maximum number of log files to keep", int,
            min_value=1, max_value=100, category="logging"
        )
        
        # Performance parameters
        self.register_parameter(
            "cpu_usage_limit", 80.0, "Maximum CPU usage percentage", float,
            min_value=10.0, max_value=100.0, category="performance"
        )
        
        self.register_parameter(
            "memory_usage_limit", 90.0, "Maximum memory usage percentage", float,
            min_value=10.0, max_value=100.0, category="performance"
        )
        
        self.register_parameter(
            "enable_performance_monitoring", True, "Enable performance monitoring", bool,
            category="performance"
        )
        
        # Safety parameters
        self.register_parameter(
            "failsafe_enabled", True, "Enable PyAutoGUI failsafe", bool,
            category="safety", requires_restart=True
        )
        
        self.register_parameter(
            "pause_duration", 0.1, "PyAutoGUI pause duration", float,
            min_value=0.0, max_value=2.0, category="safety"
        )
        
        self.register_parameter(
            "emergency_stop_key", "ctrl+shift+q", "Emergency stop key combination", str,
            category="safety"
        )
    
    def register_parameter(self, name: str, default_value: Any, description: str, 
                          data_type: type, min_value: Optional[Any] = None,
                          max_value: Optional[Any] = None, allowed_values: Optional[List[Any]] = None,
                          requires_restart: bool = False, category: str = "general",
                          validation_func: Optional[Callable] = None):
        """Register a new configuration parameter"""
        with self._lock:
            param = ConfigParameter(
                name=name,
                value=default_value,
                default_value=default_value,
                description=description,
                data_type=data_type,
                min_value=min_value,
                max_value=max_value,
                allowed_values=allowed_values,
                requires_restart=requires_restart,
                category=category,
                validation_func=validation_func
            )
            self.parameters[name] = param
    
    def get_parameter(self, name: str) -> Any:
        """Get parameter value"""
        with self._lock:
            if name not in self.parameters:
                raise KeyError(f"Parameter '{name}' not found")
            return self.parameters[name].value
    
    def set_parameter(self, name: str, value: Any, user: str = "system", reason: str = "") -> bool:
        """Set parameter value with validation"""
        with self._lock:
            if name not in self.parameters:
                raise KeyError(f"Parameter '{name}' not found")
            
            param = self.parameters[name]
            old_value = param.value
            
            # Validate the new value
            if not self._validate_parameter_value(param, value):
                return False
            
            # Update the parameter
            param.value = value
            
            # Record the change
            change = ConfigChange(
                timestamp=time.time(),
                parameter_name=name,
                old_value=old_value,
                new_value=value,
                user=user,
                reason=reason
            )
            self.change_history.append(change)
            
            # Trigger callbacks
            self._trigger_change_callbacks(name, old_value, value)
            
            # Auto-save if enabled
            if self.auto_save:
                self._save_configuration()
            
            return True
    
    def _validate_parameter_value(self, param: ConfigParameter, value: Any) -> bool:
        """Validate parameter value against constraints"""
        try:
            # Type validation
            if not isinstance(value, param.data_type):
                # Try to convert
                if param.data_type == bool and isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    value = param.data_type(value)
            
            # Range validation
            if param.min_value is not None and value < param.min_value:
                return False
            if param.max_value is not None and value > param.max_value:
                return False
            
            # Allowed values validation
            if param.allowed_values is not None and value not in param.allowed_values:
                return False
            
            # Custom validation function
            if param.validation_func is not None:
                return param.validation_func(value)
            
            return True
        except (ValueError, TypeError):
            return False
    
    def get_parameters_by_category(self, category: str) -> Dict[str, Any]:
        """Get all parameters in a specific category"""
        with self._lock:
            return {
                name: param.value for name, param in self.parameters.items()
                if param.category == category
            }
    
    def get_all_categories(self) -> List[str]:
        """Get list of all parameter categories"""
        with self._lock:
            return list(set(param.category for param in self.parameters.values()))
    
    def get_parameter_info(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a parameter"""
        with self._lock:
            if name not in self.parameters:
                raise KeyError(f"Parameter '{name}' not found")
            
            param = self.parameters[name]
            return {
                'name': param.name,
                'value': param.value,
                'default_value': param.default_value,
                'description': param.description,
                'data_type': param.data_type.__name__,
                'min_value': param.min_value,
                'max_value': param.max_value,
                'allowed_values': param.allowed_values,
                'requires_restart': param.requires_restart,
                'category': param.category
            }
    
    def reset_parameter(self, name: str, user: str = "system") -> bool:
        """Reset parameter to default value"""
        with self._lock:
            if name not in self.parameters:
                raise KeyError(f"Parameter '{name}' not found")
            
            param = self.parameters[name]
            return self.set_parameter(name, param.default_value, user, "Reset to default")
    
    def reset_category(self, category: str, user: str = "system") -> int:
        """Reset all parameters in a category to default values"""
        with self._lock:
            count = 0
            for name, param in self.parameters.items():
                if param.category == category:
                    if self.reset_parameter(name, user):
                        count += 1
            return count
    
    def save_profile(self, profile_name: str) -> bool:
        """Save current configuration as a profile"""
        with self._lock:
            try:
                self.profiles[profile_name] = {
                    name: param.value for name, param in self.parameters.items()
                }
                self._save_configuration()
                return True
            except Exception:
                return False
    
    def load_profile(self, profile_name: str, user: str = "system") -> bool:
        """Load a configuration profile"""
        with self._lock:
            if profile_name not in self.profiles:
                return False
            
            try:
                profile_config = self.profiles[profile_name]
                for name, value in profile_config.items():
                    if name in self.parameters:
                        self.set_parameter(name, value, user, f"Loaded from profile '{profile_name}'")
                
                self.current_profile = profile_name
                return True
            except Exception:
                return False
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete a configuration profile"""
        with self._lock:
            if profile_name in self.profiles:
                del self.profiles[profile_name]
                self._save_configuration()
                return True
            return False
    
    def get_profiles(self) -> List[str]:
        """Get list of available profiles"""
        with self._lock:
            return list(self.profiles.keys())
    
    def register_change_callback(self, parameter_name: str, callback: Callable):
        """Register a callback for parameter changes"""
        with self._lock:
            if parameter_name not in self.change_callbacks:
                self.change_callbacks[parameter_name] = []
            self.change_callbacks[parameter_name].append(callback)
    
    def _trigger_change_callbacks(self, parameter_name: str, old_value: Any, new_value: Any):
        """Trigger callbacks for parameter changes"""
        if parameter_name in self.change_callbacks:
            for callback in self.change_callbacks[parameter_name]:
                try:
                    callback(parameter_name, old_value, new_value)
                except Exception as e:
                    print(f"Error in change callback for {parameter_name}: {e}")
    
    def get_change_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent configuration changes"""
        with self._lock:
            return [asdict(change) for change in self.change_history[-limit:]]
    
    def export_configuration(self, filepath: str) -> bool:
        """Export current configuration to file"""
        with self._lock:
            try:
                config_data = {
                    'export_info': {
                        'timestamp': datetime.now().isoformat(),
                        'profile': self.current_profile
                    },
                    'parameters': {
                        name: {
                            'value': param.value,
                            'category': param.category,
                            'description': param.description
                        } for name, param in self.parameters.items()
                    },
                    'profiles': self.profiles,
                    'change_history': [asdict(change) for change in self.change_history[-50:]]
                }
                
                with open(filepath, 'w') as f:
                    json.dump(config_data, f, indent=2, default=str)
                return True
            except Exception:
                return False
    
    def import_configuration(self, filepath: str, user: str = "system") -> bool:
        """Import configuration from file"""
        with self._lock:
            try:
                with open(filepath, 'r') as f:
                    config_data = json.load(f)
                
                # Import parameters
                if 'parameters' in config_data:
                    for name, param_data in config_data['parameters'].items():
                        if name in self.parameters:
                            self.set_parameter(name, param_data['value'], user, "Imported from file")
                
                # Import profiles
                if 'profiles' in config_data:
                    self.profiles.update(config_data['profiles'])
                
                return True
            except Exception:
                return False
    
    def load_configuration(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Load parameters
                if 'parameters' in config_data:
                    for name, value in config_data['parameters'].items():
                        if name in self.parameters:
                            self.parameters[name].value = value
                
                # Load profiles
                if 'profiles' in config_data:
                    self.profiles = config_data['profiles']
                
                # Load current profile
                if 'current_profile' in config_data:
                    self.current_profile = config_data['current_profile']
                
            except Exception as e:
                print(f"Error loading configuration: {e}")
    
    def _save_configuration(self):
        """Save configuration to file"""
        try:
            config_data = {
                'parameters': {name: param.value for name, param in self.parameters.items()},
                'profiles': self.profiles,
                'current_profile': self.current_profile,
                'last_saved': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def _auto_save_worker(self):
        """Background worker for auto-saving configuration"""
        while self.auto_save_active:
            try:
                time.sleep(30)  # Save every 30 seconds
                if self.auto_save_active:
                    self._save_configuration()
            except Exception as e:
                print(f"Error in auto-save worker: {e}")
                time.sleep(60)  # Wait longer on error
    
    def stop_auto_save(self):
        """Stop auto-save worker"""
        self.auto_save_active = False
        if hasattr(self, 'auto_save_thread') and self.auto_save_thread.is_alive():
            self.auto_save_thread.join(timeout=5)
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'auto_save_active'):
            self.stop_auto_save()

# Global configuration manager instance
config_manager = ConfigurationManager()

def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance"""
    return config_manager

def get_config(parameter_name: str) -> Any:
    """Convenience function to get a configuration parameter"""
    return config_manager.get_parameter(parameter_name)

def set_config(parameter_name: str, value: Any, user: str = "system", reason: str = "") -> bool:
    """Convenience function to set a configuration parameter"""
    return config_manager.set_parameter(parameter_name, value, user, reason)