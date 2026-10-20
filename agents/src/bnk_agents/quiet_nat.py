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


# When the hosted model fails (a 500 or an empty reply), NAT logs the same error from four places, the
# last with a 60-line traceback. The agent retries and usually recovers, so keep one plain line instead.
DUPLICATE_ERRORS = (
    "nat.builder.function",
    "nat.plugins.langchain.agent.react_agent.register",
    "nat.plugins.langchain.agent.react_agent.agent",
)
EMPTY_REPLY = "LLM output: ''"


class _OneLine(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.ERROR:
            return True
        if record.name in DUPLICATE_ERRORS:
            return False
        record.exc_info = None
        record.exc_text = None
        if EMPTY_REPLY in record.getMessage():
            record.msg = ("[AGENT] NVIDIA's model returned an empty reply. The agent will try again; "
                          "if the run stops, run labctl agents again.")
            record.args = ()
        return True


def main() -> int:
    for name in QUIET:
        logging.getLogger(name).addFilter(_Floor())
    for name in DUPLICATE_ERRORS + ("nat.plugins.langchain.agent.base",):
        logging.getLogger(name).addFilter(_OneLine())
    from nat.cli.main import run_cli
    return run_cli()


if __name__ == "__main__":
    sys.exit(main())
