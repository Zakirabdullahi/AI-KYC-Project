import traceback
import sys

try:
    import main
    print("Import successful!")
except Exception as e:
    with open('error.log', 'w') as f:
        f.write(traceback.format_exc())
        print("Wrote error to error.log")
