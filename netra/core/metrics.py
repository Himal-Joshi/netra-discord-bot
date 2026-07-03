from prometheus_client import start_http_server, Counter, Gauge, Summary
import time

# Metrics
COMMANDS_EXECUTED = Counter('netra_commands_executed_total', 'Total number of commands executed', ['command_name', 'guild_id'])
COMMAND_ERRORS = Counter('netra_command_errors_total', 'Total number of command errors', ['command_name', 'error_type'])
GUILD_COUNT = Gauge('netra_guild_count', 'Total number of guilds the bot is in')
LATENCY = Gauge('netra_latency_seconds', 'Bot latency in seconds')

COMMAND_EXECUTION_TIME = Summary('netra_command_execution_seconds', 'Time spent processing command', ['command_name'])

def start_metrics_server(port: int = 8001):
    start_http_server(port)
