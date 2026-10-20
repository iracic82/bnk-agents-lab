"""Runs the NeMo Agent Toolkit CLI with the startup noise turned down, so the agent trace stands out.

NAT logs one line per MCP tool it registers. Run:ai's server offers about 40, and the agents can only
call the ones `include:` lists in the config, so those lines read as access the agents don't have. The
agents' own trace ([AGENT] blocks, tool calls, the approval prompt) is untouched.
"""
import logging
import sys
import warnings

# authlib warns that its jose module is deprecated when NAT imports it. Filters can't hold it back
# (authlib and pandas reset them to "always" on import), so drop it where warnings are printed. Set at
# import time, before anything can import NAT.
_show = warnings.showwarning


def _quiet_show(message, category, *args, **kwargs):
    if category.__name__ != "AuthlibDeprecationWarning":
        _show(message, category, *args, **kwargs)


warnings.showwarning = _quiet_show

# Loggers whose INFO lines are setup detail, not agent behaviour.
QUIET = (
    "nat.plugins.mcp.client.client_impl",
    "nat.plugins.mcp.client.client_base",
    "nat.builder.function_info",
    "nat.cli.commands.start",
    "nat.runtime.session",
    "mcp.client.streamable_http",
    "httpx",
)


class _Floor(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.WARNING and record.name != "nat.builder.function_info"


def main() -> int:
    for name in QUIET:
        logging.getLogger(name).addFilter(_Floor())
    from nat.cli.main import run_cli
    return run_cli()


if __name__ == "__main__":
    sys.exit(main())
