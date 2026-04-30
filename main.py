#!/usr/bin/env python
import os
import sys

# Add current directory to path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Redirect to the actual main in hecos/
if __name__ == "__main__":
    from hecos.main import main
    main()
