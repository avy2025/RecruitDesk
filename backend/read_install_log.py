
import codecs
import sys

try:
    # Try reading as UTF-16 LE (common for PowerShell redirection)
    with codecs.open("install_log.txt", "r", "utf-16") as f:
        content = f.read()
        print("Successfully read as UTF-16")
        print(content)
except Exception as e:
    print(f"Failed to read as UTF-16: {e}")
    try:
        # Try reading as default (cp1252 or utf-8)
        with open("install_log.txt", "r", errors='replace') as f:
            content = f.read()
            print("Successfully read as default/replace")
            print(content)
    except Exception as e2:
        print(f"Failed to read file: {e2}")
