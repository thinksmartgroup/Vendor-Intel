import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import difflib
import re

class WebInterfaceHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_modified = 0
        
    def on_modified(self, event):
        if event.src_path.endswith('web_interface.py'):
            # Debounce multiple events
            current_time = time.time()
            if current_time - self.last_modified < 1:
                return
            self.last_modified = current_time
            
            print(f"\n🔄 Detected changes in {event.src_path}")
            self.sync_debug_file()
    
    def sync_debug_file(self):
        try:
            # Read the original file
            with open('web_interface.py', 'r') as f:
                content = f.read()
            
            # Add debug logging
            debug_content = self.add_debug_logging(content)
            
            # Write to debug file
            with open('web_interface_debug.py', 'w') as f:
                f.write(debug_content)
            
            print("✅ Successfully synchronized web_interface_debug.py")
            
        except Exception as e:
            print(f"❌ Error syncing debug file: {str(e)}")
    
    def add_debug_logging(self, content):
        # Add logging import if not present
        if 'import logging' not in content:
            content = 'import logging\n' + content
        
        # Add logging configuration after imports
        logging_config = '''
# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
'''
        # Find the end of imports
        import_end = max(content.rfind('import '), content.rfind('from '))
        content = content[:import_end] + logging_config + content[import_end:]
        
        # Replace print statements with logging while preserving indentation
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'print(' in line:
                indent = len(line) - len(line.lstrip())
                spaces = ' ' * indent
                # Replace print with logger.debug while keeping the indentation
                lines[i] = re.sub(r'print\((.*?)\)', lambda m: f'{spaces}logger.debug({m.group(1)})', line)
        
        content = '\n'.join(lines)
        
        # Add logging for exceptions while preserving indentation
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'except' in line and 'as' in line:
                indent = len(line) - len(line.lstrip())
                spaces = ' ' * indent
                # Add error logging after the except line
                match = re.match(r'except\s+(\w+)\s+as\s+(\w+):', line)
                if match:
                    lines[i] = f"{line}\n{spaces}    logger.error(f\"Error: {{{match.group(2)}}}\", exc_info=True)"
        
        content = '\n'.join(lines)
        
        # Add debug=True to Flask app
        content = content.replace(
            'app.run(',
            'app.run(debug=True, '
        )
        
        return content

if __name__ == "__main__":
    print("🔍 Starting debug file sync watcher...")
    event_handler = WebInterfaceHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    
    try:
        # Do initial sync
        event_handler.sync_debug_file()
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n👋 Stopping debug file sync watcher...")
    observer.join() 