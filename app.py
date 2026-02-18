#!/usr/bin/env python3
"""Точка входа - запускает приложение с UI или в headless режиме"""

import sys


def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("AI ENTITIES - Ecosystem Simulation with NN Brain")
    print("=" * 60 + "\n")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--headless":
            # Headless mode
            print("Running in HEADLESS mode (no UI)\n")
            
            preset = sys.argv[2] if len(sys.argv) > 2 else "balanced"
            duration = float(sys.argv[3]) if len(sys.argv) > 3 else 16.0
            
            from headless import HeadlessSimulation
            sim = HeadlessSimulation(preset_name=preset, duration=duration)
            sim.run()
        
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage: python3 app.py [OPTIONS]")
            print()
            print("OPTIONS:")
            print("  (no args)           Run with Tkinter UI + Pygame visualization")
            print("  --headless PRESET DURATION")
            print("                      Run without UI")
            print("                      PRESET: balanced, herbivore_dominated, predator_dominant, scarce_resources")
            print("                      DURATION: simulation length in seconds (default: 16)")
            print("  --help, -h         Show this help message")
            print()
            print("Examples:")
            print("  python3 app.py                           # Normal mode with UI")
            print("  python3 app.py --headless balanced 10    # Headless, balanced, 10 seconds")
            print("  python3 app.py --headless predator_dominant 20  # Headless, predator mode, 20s")
        
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use 'python3 app.py --help' for usage information")
            sys.exit(1)
    
    else:
        # UI mode - может повторяться для нескольких симуляций
        from ui.application import SimulationApp
        
        while True:
            print("Running in UI mode (Tkinter + Pygame)\n")
            
            try:
                app = SimulationApp()
                app.run()
                
                # После закрытия окна спрашиваем, хочет ли пользователь снова
                print("\n" + "=" * 60)
                answer = input("Run another simulation? (y/n): ").lower()
                print("=" * 60 + "\n")
                
                if answer != 'y' and answer != 'yes':
                    print("Goodbye!")
                    break
            
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            
            except Exception as e:
                print(f"\nError: {e}")
                import traceback
                traceback.print_exc()
                
                print("\n" + "=" * 60)
                print("TROUBLESHOOTING:")
                print("=" * 60)
                print("If you get Tkinter errors, try running in headless mode:")
                print("  python3 app.py --headless balanced 10")
                print()
                break


if __name__ == "__main__":
    main()
