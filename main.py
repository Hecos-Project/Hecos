#!/usr/bin/env python
# Wrapper root per Zentra Package
import sys
import os

# Aggiunge la cartella zentra al path per compatibilità legacy se necessario
# Oppure semplicemente lancia il main del package
if __name__ == "__main__":
    from zentra.main import main
    main()