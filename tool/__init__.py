from . import filesystem_tool, system_monitor_tool, web_search_tool
from .tools import monitor, ocr

tools = [
    *filesystem_tool.tools,
    *system_monitor_tool.tools,
    *web_search_tool.tools,
    *monitor.tools,
    *ocr.tools,
]
