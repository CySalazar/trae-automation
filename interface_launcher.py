#!/usr/bin/env python3
"""
Interface Launcher - Main Entry Point for UI Selection

This module provides a unified entry point for launching different user interfaces:
- Graphical User Interface (GUI) with tkinter
- Command Line Interface (CLI) for terminal users
- Log Viewer Interface for log analysis
- Configuration Manager for system settings

Author: Matteo Sala
License: GNU GPL v3.0
"""

import sys
import os
import argparse
import threading
import time
from typing import Optional

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from gui_interface import SystemMonitorGUI
    GUI_AVAILABLE = True
except ImportError as e:
    print(f"GUI interface not available: {e}")
    GUI_AVAILABLE = False

try:
    from cli_interface import SystemMonitorCLI
    CLI_AVAILABLE = True
except ImportError as e:
    print(f"CLI interface not available: {e}")
    CLI_AVAILABLE = False

try:
    from log_viewer import LogViewer, LogViewerCLI
    LOG_VIEWER_AVAILABLE = True
except ImportError as e:
    print(f"Log viewer not available: {e}")
    LOG_VIEWER_AVAILABLE = False

try:
    from config_manager import ConfigurationManager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Configuration manager not available: {e}")
    CONFIG_MANAGER_AVAILABLE = False

try:
    from statistics_manager import StatisticsManager
    STATS_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Statistics manager not available: {e}")
    STATS_MANAGER_AVAILABLE = False

class InterfaceLauncher:
    """Main launcher for different user interfaces"""
    
    def __init__(self):
        self.running_interfaces = []
        
    def show_main_menu(self):
        """Display the main interface selection menu"""
        print("\n" + "="*70)
        print("🚀 AUTO-DETECTION SYSTEM - INTERFACE LAUNCHER")
        print("="*70)
        print("\nAvailable Interfaces:")
        print()
        
        options = []
        
        if GUI_AVAILABLE:
            options.append(("1", "🖥️  Graphical User Interface (GUI)", "Launch the full-featured GUI with real-time monitoring"))
        else:
            print("❌ 1. Graphical User Interface (GUI) - Not Available")
            
        if CLI_AVAILABLE:
            options.append(("2", "💻 Command Line Interface (CLI)", "Launch the terminal-based interface"))
        else:
            print("❌ 2. Command Line Interface (CLI) - Not Available")
            
        if LOG_VIEWER_AVAILABLE:
            options.append(("3", "📋 Log Viewer", "Interactive log analysis and monitoring"))
        else:
            print("❌ 3. Log Viewer - Not Available")
            
        if CONFIG_MANAGER_AVAILABLE:
            options.append(("4", "⚙️  Configuration Manager", "Manage system configuration and parameters"))
        else:
            print("❌ 4. Configuration Manager - Not Available")
            
        if STATS_MANAGER_AVAILABLE:
            options.append(("5", "📊 Statistics Dashboard", "View detailed system statistics and performance"))
        else:
            print("❌ 5. Statistics Dashboard - Not Available")
            
        options.append(("6", "🔧 System Information", "Display system status and information"))
        options.append(("0", "❌ Exit", "Exit the launcher"))
        
        for option_num, title, description in options:
            print(f"{option_num}. {title}")
            print(f"   {description}")
            print()
            
        return options
        
    def launch_gui(self):
        """Launch the GUI interface"""
        if not GUI_AVAILABLE:
            print("❌ GUI interface is not available.")
            return
            
        print("🖥️  Launching Graphical User Interface...")
        try:
            app = SystemMonitorGUI()
            app.run()
        except Exception as e:
            print(f"❌ Error launching GUI: {e}")
            
    def launch_cli(self):
        """Launch the CLI interface"""
        if not CLI_AVAILABLE:
            print("❌ CLI interface is not available.")
            return
            
        print("💻 Launching Command Line Interface...")
        try:
            cli = SystemMonitorCLI()
            cli.run()
        except Exception as e:
            print(f"❌ Error launching CLI: {e}")
            
    def launch_log_viewer(self):
        """Launch the log viewer interface"""
        if not LOG_VIEWER_AVAILABLE:
            print("❌ Log viewer is not available.")
            return
            
        print("📋 Launching Log Viewer...")
        try:
            # Check for existing log files
            log_files = []
            potential_logs = ['log.txt', 'scanner.log', 'detection.log', 'system.log']
            
            for log_file in potential_logs:
                if os.path.exists(log_file):
                    log_files.append(log_file)
                    
            if not log_files:
                print("⚠️  No log files found. Creating default log viewer...")
                
            viewer = LogViewer(log_files)
            cli = LogViewerCLI(viewer)
            cli.run()
        except Exception as e:
            print(f"❌ Error launching log viewer: {e}")
            
    def launch_config_manager(self):
        """Launch the configuration manager"""
        if not CONFIG_MANAGER_AVAILABLE:
            print("❌ Configuration manager is not available.")
            return
            
        print("⚙️  Launching Configuration Manager...")
        try:
            config_mgr = ConfigurationManager()
            self.show_config_menu(config_mgr)
        except Exception as e:
            print(f"❌ Error launching configuration manager: {e}")
            
    def show_config_menu(self, config_mgr: 'ConfigurationManager'):
        """Show configuration management menu"""
        while True:
            print("\n" + "="*50)
            print("⚙️  CONFIGURATION MANAGER")
            print("="*50)
            print("\n1. View all parameters")
            print("2. View parameters by category")
            print("3. Update parameter")
            print("4. Reset parameter to default")
            print("5. Save configuration")
            print("6. Load configuration")
            print("7. Export configuration")
            print("0. Back to main menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.show_all_parameters(config_mgr)
            elif choice == '2':
                self.show_parameters_by_category(config_mgr)
            elif choice == '3':
                self.update_parameter(config_mgr)
            elif choice == '4':
                self.reset_parameter(config_mgr)
            elif choice == '5':
                config_mgr.save_configuration()
                print("✅ Configuration saved.")
            elif choice == '6':
                config_mgr.load_configuration()
                print("✅ Configuration loaded.")
            elif choice == '7':
                filename = input("Enter export filename (default: config_export.json): ").strip()
                if not filename:
                    filename = "config_export.json"
                config_mgr.export_configuration(filename)
                print(f"✅ Configuration exported to {filename}")
            else:
                print("❌ Invalid option.")
                
    def show_all_parameters(self, config_mgr: 'ConfigurationManager'):
        """Show all configuration parameters"""
        params = config_mgr.get_all_parameters()
        
        print("\n📋 ALL CONFIGURATION PARAMETERS")
        print("=" * 60)
        
        for name, param in params.items():
            print(f"\n{name}:")
            print(f"  Value: {param.value}")
            print(f"  Type: {param.data_type.__name__}")
            print(f"  Category: {param.category}")
            print(f"  Description: {param.description}")
            if param.min_value is not None:
                print(f"  Min: {param.min_value}")
            if param.max_value is not None:
                print(f"  Max: {param.max_value}")
            if param.allowed_values:
                print(f"  Allowed: {param.allowed_values}")
                
    def show_parameters_by_category(self, config_mgr: 'ConfigurationManager'):
        """Show parameters grouped by category"""
        categories = config_mgr.get_categories()
        
        print("\nAvailable categories:")
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category}")
            
        try:
            choice = int(input("\nSelect category: ")) - 1
            if 0 <= choice < len(categories):
                category = categories[choice]
                params = config_mgr.get_parameters_by_category(category)
                
                print(f"\n📋 PARAMETERS IN CATEGORY: {category.upper()}")
                print("=" * 50)
                
                for name, param in params.items():
                    print(f"\n{name}: {param.value}")
                    print(f"  {param.description}")
            else:
                print("❌ Invalid category selection.")
        except ValueError:
            print("❌ Invalid input.")
            
    def update_parameter(self, config_mgr: 'ConfigurationManager'):
        """Update a configuration parameter"""
        param_name = input("\nEnter parameter name: ").strip()
        
        if not config_mgr.has_parameter(param_name):
            print(f"❌ Parameter '{param_name}' not found.")
            return
            
        param = config_mgr.get_parameter(param_name)
        print(f"\nCurrent value: {param.value}")
        print(f"Type: {param.data_type.__name__}")
        print(f"Description: {param.description}")
        
        new_value = input("Enter new value: ").strip()
        
        try:
            success = config_mgr.update_parameter(param_name, new_value)
            if success:
                print(f"✅ Parameter '{param_name}' updated successfully.")
            else:
                print(f"❌ Failed to update parameter '{param_name}'.")
        except Exception as e:
            print(f"❌ Error updating parameter: {e}")
            
    def reset_parameter(self, config_mgr: 'ConfigurationManager'):
        """Reset a parameter to its default value"""
        param_name = input("\nEnter parameter name to reset: ").strip()
        
        try:
            success = config_mgr.reset_parameter(param_name)
            if success:
                print(f"✅ Parameter '{param_name}' reset to default value.")
            else:
                print(f"❌ Failed to reset parameter '{param_name}'.")
        except Exception as e:
            print(f"❌ Error resetting parameter: {e}")
            
    def launch_stats_dashboard(self):
        """Launch the statistics dashboard"""
        if not STATS_MANAGER_AVAILABLE:
            print("❌ Statistics manager is not available.")
            return
            
        print("📊 Launching Statistics Dashboard...")
        try:
            stats_mgr = StatisticsManager()
            self.show_stats_menu(stats_mgr)
        except Exception as e:
            print(f"❌ Error launching statistics dashboard: {e}")
            
    def show_stats_menu(self, stats_mgr: 'StatisticsManager'):
        """Show statistics dashboard menu"""
        while True:
            print("\n" + "="*50)
            print("📊 STATISTICS DASHBOARD")
            print("="*50)
            print("\n1. Current statistics")
            print("2. Performance metrics")
            print("3. System health")
            print("4. Export statistics")
            print("5. Reset statistics")
            print("0. Back to main menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.show_current_stats(stats_mgr)
            elif choice == '2':
                self.show_performance_metrics(stats_mgr)
            elif choice == '3':
                self.show_system_health(stats_mgr)
            elif choice == '4':
                self.export_statistics(stats_mgr)
            elif choice == '5':
                stats_mgr.reset_statistics()
                print("✅ Statistics reset.")
            else:
                print("❌ Invalid option.")
                
    def show_current_stats(self, stats_mgr: 'StatisticsManager'):
        """Show current statistics"""
        stats = stats_mgr.get_current_statistics()
        
        print("\n📊 CURRENT STATISTICS")
        print("=" * 40)
        
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"\n{key.replace('_', ' ').title()}:")
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key.replace('_', ' ').title()}: {sub_value}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
                
    def show_performance_metrics(self, stats_mgr: 'StatisticsManager'):
        """Show performance metrics"""
        metrics = stats_mgr.get_performance_summary()
        
        print("\n⚡ PERFORMANCE METRICS")
        print("=" * 40)
        
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"{key.replace('_', ' ').title()}: {value:.2f}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
                
    def show_system_health(self, stats_mgr: 'StatisticsManager'):
        """Show system health information"""
        health = stats_mgr.get_system_health()
        
        print("\n🏥 SYSTEM HEALTH")
        print("=" * 40)
        
        for key, value in health.items():
            if isinstance(value, dict):
                print(f"\n{key.replace('_', ' ').title()}:")
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key.replace('_', ' ').title()}: {sub_value}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
                
    def export_statistics(self, stats_mgr: 'StatisticsManager'):
        """Export statistics to file"""
        filename = input("Enter export filename (default: statistics_export.json): ").strip()
        if not filename:
            filename = "statistics_export.json"
            
        try:
            stats_mgr.export_statistics(filename)
            print(f"✅ Statistics exported to {filename}")
        except Exception as e:
            print(f"❌ Error exporting statistics: {e}")
            
    def show_system_info(self):
        """Show system information"""
        print("\n" + "="*50)
        print("🔧 SYSTEM INFORMATION")
        print("="*50)
        
        print(f"\nPython Version: {sys.version}")
        print(f"Platform: {sys.platform}")
        print(f"Current Directory: {os.getcwd()}")
        
        print("\nAvailable Modules:")
        print(f"  GUI Interface: {'✅ Available' if GUI_AVAILABLE else '❌ Not Available'}")
        print(f"  CLI Interface: {'✅ Available' if CLI_AVAILABLE else '❌ Not Available'}")
        print(f"  Log Viewer: {'✅ Available' if LOG_VIEWER_AVAILABLE else '❌ Not Available'}")
        print(f"  Config Manager: {'✅ Available' if CONFIG_MANAGER_AVAILABLE else '❌ Not Available'}")
        print(f"  Statistics Manager: {'✅ Available' if STATS_MANAGER_AVAILABLE else '❌ Not Available'}")
        
        # Check for log files
        print("\nLog Files:")
        log_files = ['log.txt', 'scanner.log', 'detection.log', 'system.log']
        for log_file in log_files:
            if os.path.exists(log_file):
                size = os.path.getsize(log_file)
                print(f"  {log_file}: {size} bytes")
            else:
                print(f"  {log_file}: Not found")
                
        # Check for config files
        print("\nConfiguration Files:")
        config_files = ['config.py', 'config.json', 'settings.json']
        for config_file in config_files:
            if os.path.exists(config_file):
                print(f"  {config_file}: ✅ Found")
            else:
                print(f"  {config_file}: ❌ Not found")
                
        input("\nPress Enter to continue...")
        
    def run(self):
        """Main launcher loop"""
        while True:
            try:
                options = self.show_main_menu()
                choice = input("\nSelect an option: ").strip()
                
                if choice == '0':
                    print("\n👋 Goodbye!")
                    break
                elif choice == '1' and GUI_AVAILABLE:
                    self.launch_gui()
                elif choice == '2' and CLI_AVAILABLE:
                    self.launch_cli()
                elif choice == '3' and LOG_VIEWER_AVAILABLE:
                    self.launch_log_viewer()
                elif choice == '4' and CONFIG_MANAGER_AVAILABLE:
                    self.launch_config_manager()
                elif choice == '5' and STATS_MANAGER_AVAILABLE:
                    self.launch_stats_dashboard()
                elif choice == '6':
                    self.show_system_info()
                else:
                    print("\n❌ Invalid option or interface not available.")
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(2)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Auto-Detection System Interface Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python interface_launcher.py              # Show main menu
  python interface_launcher.py --gui        # Launch GUI directly
  python interface_launcher.py --cli        # Launch CLI directly
  python interface_launcher.py --logs       # Launch log viewer
  python interface_launcher.py --config     # Launch config manager
  python interface_launcher.py --stats      # Launch statistics dashboard
        """
    )
    
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface directly')
    parser.add_argument('--cli', action='store_true', help='Launch CLI interface directly')
    parser.add_argument('--logs', action='store_true', help='Launch log viewer directly')
    parser.add_argument('--config', action='store_true', help='Launch configuration manager directly')
    parser.add_argument('--stats', action='store_true', help='Launch statistics dashboard directly')
    parser.add_argument('--info', action='store_true', help='Show system information and exit')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    launcher = InterfaceLauncher()
    
    # Handle direct launch options
    if args.gui:
        launcher.launch_gui()
        return
    elif args.cli:
        launcher.launch_cli()
        return
    elif args.logs:
        launcher.launch_log_viewer()
        return
    elif args.config:
        launcher.launch_config_manager()
        return
    elif args.stats:
        launcher.launch_stats_dashboard()
        return
    elif args.info:
        launcher.show_system_info()
        return
        
    # Show main menu
    launcher.run()

if __name__ == "__main__":
    main()