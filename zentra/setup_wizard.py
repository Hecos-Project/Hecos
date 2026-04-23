#!/usr/bin/env python
# proxy for the refactored setup module
try:
    from zentra.setup.main import main
except ImportError:
    # fallback to local import if called from within zentra/
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from zentra.setup.main import main

if __name__ == "__main__":
    main()
