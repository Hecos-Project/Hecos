"""
MODULE: Logical Processor Package - Hecos v2.5
DESCRIPTION: Re-exports facade symbols from processore.py and tool_dispatcher.py.
"""
from hecos.core.processing.processore import (
    current_config,
    configure,
    process_exchange,
    clean_final_output,
)
from hecos.core.processing.tool_dispatcher import (
    extract_and_execute_tools,
    TAG_MAPPING,
    BLACKLIST,
)
