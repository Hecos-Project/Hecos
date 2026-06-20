"""
Module responsible for initializing the Hecos system and showing boot sequences.
"""
import sys
import time
from hecos.core.logging import logger
from hecos.core.system import module_loader, diagnostica
from hecos.core.i18n import translator
from hecos.ui import interface, graphics, ui_updater
from hecos.memory import brain_interface
from hecos.core.processing import processore

class SystemBootstrapper:
    """Handles the heavy lifting of system initialization."""
    
    def __init__(self, config_manager, state_manager):
        self.config_manager = config_manager
        self.state_manager = state_manager

    def initialize(self):
        """Inizializzazione di tutti i componenti."""
        from hecos.core.constants import ensure_directories
        ensure_directories()
        
        logger.init_logger(self.config_manager.config)
        
        # Initialize translator
        language = self.config_manager.config.get("language", "en")
        translator.init_translator(language)
        processore.configure(self.config_manager.config)
        logger.info("[APP] Hecos boot sequence initiated.")
        
        interface.setup_console()
        self.state_manager.system_status = translator.t("loading_memory")
        brain_interface.initialize_vault()
        brain_interface.maybe_clear_on_restart(self.config_manager.config)
        
        # IMPORTANT: pass current config to plugin loader
        self.state_manager.system_status = translator.t("loading_plugins")
        module_loader.update_capability_registry(self.config_manager.config)
        self.state_manager.system_status = translator.t("sync_plugins")
        module_loader.sync_plugin_config(self.config_manager)

        # MCP Bridge Bootstrap
        mcp_bridge = module_loader.get_plugin_module("MCP_BRIDGE")
        if mcp_bridge and hasattr(mcp_bridge, "on_load"):
            try:
                logger.info("[APP] Bootstrapping MCP Bridge...")
                mcp_bridge.on_load(self.config_manager.config)
            except Exception as _mcp_e:
                logger.error("APP", f"MCP Bridge bootstrap error: {_mcp_e}")
        
        # Inject state_manager into WebUI server after plugin load (for audio toggle routes)
        try:
            from modules.web_ui.server import set_state_manager
            set_state_manager(self.state_manager)
        except Exception as _e:
            logger.warning("APP", f"Could not inject state_manager into WebUI: {_e}")
        
        # Synchronize list of available personalities in config
        self.config_manager.sync_available_personalities()
        
        # Start KeyManager background health monitor
        try:
            from hecos.core.keys.key_manager import get_key_manager
            get_key_manager().start_background_monitor(interval_seconds=300) # Check every 5 mins
        except Exception as _km_e:
            logger.warning("APP", f"KeyManager monitor startup error: {_km_e}")
        
        config = self.config_manager.config
        self.state_manager.system_status = translator.t("diagnostics")
        diagnostica.run_initial_check(config)

        # Audio device auto-selection (Piper TTS output + Microphone input)
        try:
            from hecos.core.audio.device_manager import maybe_scan_on_startup
            self.state_manager.system_status = "Scanning audio devices..."
            maybe_scan_on_startup()
            logger.info("[APP] Audio device scan completed.")
        except Exception as _ae:
            logger.warning("APP", f"Audio device scan skipped: {_ae}")

        # Avvia il monitoraggio backend solo se il plugin è attivo
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")
        if dashboard_mod:
            ui_updater.start(self.config_manager, self.state_manager, dashboard_mod)
        else:
            logger.warning("APP", "DASHBOARD plugin disabled; hardware monitoring inactive.")

        # ── RAG Embedder Daemon — Avvio asincrono in background ────────────────
        # Il daemon (subprocess Python separato) viene avviato qui per iniziare
        # a caricare il modello ONNX prima che arrivi la prima richiesta.
        # Non è bloccante: il subprocess si avvia in background e segnala "ready"
        # quando ha finito di caricare. Le richieste RAG attendono automaticamente.
        try:
            rag_cfg = config.get("cognition", {}).get("rag", {})
            if rag_cfg.get("enabled", False):
                model_name = rag_cfg.get("embedder_model", "BAAI/bge-small-en-v1.5")
                self.state_manager.system_status = "Starting RAG embedder daemon..."
                from hecos.core.rag.embedder_daemon import get_daemon
                _daemon = get_daemon(model_name)
                _daemon.start()  # avvia il subprocess (non-blocking)
                logger.info("[APP] RAG embedder daemon subprocess avviato in background.")
        except Exception as _rag_boot_e:
            logger.warning("APP", f"RAG daemon start failed (non-fatal): {_rag_boot_e}")
        # ──────────────────────────────────────────────────────────────────────

    def show_boot_animation(self):
        """Shows boot animation inside the scrolling body area."""
        interface.move_to_body()
        sys.stdout.write(f"\n\033[96m[SYSTEM] {translator.t('boot_sync_msg')}\033[0m\n")
        for progress in range(0, 101, 5):
            bar = graphics.create_bar(progress, width=40, style="cyber")
            sys.stdout.write(f"\r{bar}")
            sys.stdout.flush()
            time.sleep(0.01)
        time.sleep(0.1)

    def show_welcome(self):
        """Shows welcome message."""
        self.state_manager.system_status = translator.t("speaking")
        
        # Show Web UI access links if active
        if module_loader.get_plugin_module("WEB_UI"):
            interface.show_web_access_info(self.config_manager.config)
            
        message = self.config_manager.config.get("behavior", {}).get("welcome_message", translator.t("system_ready"))
        interface.write_hecos(message)
        
        self.state_manager.system_processing = False
        self.state_manager.system_status = translator.t("ready")
        
        # Start the background UI updater
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")
        ui_updater.start(self.config_manager, self.state_manager, dashboard_mod)
        
        # Update just the status bar in place, avoid clearing the screen
        interface.update_status_bar_in_place(
            self.config_manager.config, 
            self.state_manager.voice_status, 
            self.state_manager.listening_status, 
            self.state_manager.system_status,
            ptt_status=self.state_manager.push_to_talk
        )
