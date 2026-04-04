#!/bin/bash
# ZENTRA PROCESS MANAGER

cd "$(dirname "$0")"

echo "Avvio Process Manager indipendente..."
python3 zentra_proc_manager.py

echo "Premi INVIO per uscire..."
read
