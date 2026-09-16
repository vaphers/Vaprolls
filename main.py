import sys
import webbrowser
import threading
import time
from cli import main_cli

def print_banner():
    banner = """
+----------------------------------------------+
|         SEO Auditor v1.0                     |
|         Local SEO Analysis Tool              |
+----------------------------------------------+
"""
    try:
        print(banner)
    except Exception:
        pass

def open_browser(url: str):
    time.sleep(1.5)
    webbrowser.open(url)

def main():
    args = sys.argv[1:]
    
    # Check if CLI is explicitly requested or if the first argument matches a CLI command
    if '--cli' in args or 'audit' in args or 'list' in args or 'report' in args or 'compare' in args:
        if '--cli' in args:
            args.remove('--cli')
        main_cli(args)
    else:
        print_banner()
        try:
            import uvicorn
            import importlib.util
            
            # Fall back to CLI if the web dashboard doesn't exist yet
            if not importlib.util.find_spec("web.app"):
                print("Web dashboard not found. Fallback to CLI.")
                print("Use 'python main.py audit <url>' to run an audit.")
                sys.exit(0)
                
            print("Starting FastAPI web dashboard on http://localhost:8000 ...")
            threading.Thread(target=open_browser, args=("http://localhost:8000",), daemon=True).start()
            uvicorn.run('web.app:app', host='0.0.0.0', port=8000, reload=False)
        except ImportError as e:
            print(f"Failed to start web dashboard: {e}")
            print("Please ensure uvicorn and fastapi are installed.")
            print("Fallback to CLI: use 'python main.py audit <url>'")
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            try:
                from web.app import cleanup_all_crawl_data
                cleanup_all_crawl_data()
            except Exception:
                pass

if __name__ == "__main__":
    main()
