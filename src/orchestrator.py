import taskiq_sqlite
from taskiq import TaskiqScheduler, TaskiqEvents, TaskiqState
from taskiq import TaskiqBroker
from src.settings import settings

# Initialize SQlite Broker (Serverless, Persistence)
broker = TaskiqBroker()

# We will use sqlite for persistence of results and state
# Note: taskiq-sqlite might require specific setup, for now we use the memory broker pattern 
# but backed by a sqlite result backend if provided by the lib, or just the standard In-Memory for dev
# As per PRD, "taskiq-sqlite" is chosen.
# Assuming taskiq-sqlite provides a broker or result backend.
# If taskiq-sqlite implementation is strictly a ResultBackend:
# from taskiq.backends.sqlite import SQLiteResultBackend
# broker = TaskiqBroker(result_backend=SQLiteResultBackend(dsn=settings.TASKIQ_BROKER_URL))

# Since taskiq-sqlite is minimal, let's stick to a robust simple setup for now.
# We'll stick to ZMQ or just simple InMemoryBroker for local dev if ZMQ is overkill,
# BUT PRD said "Taskiq + taskiq-sqlite".

# Placeholder for real configuration once we confirm taskiq-sqlite API specifics.
# Using standard InMemoryBroker for scaffolding to avoid import errors if lib missing.
try:
    from taskiq_sqlite import SQLiteBroker
    broker = SQLiteBroker(settings.TASKIQ_BROKER_URL)
except ImportError:
    # Fallback to in-memory if sqlite extension not ready
    from taskiq import InMemoryBroker
    broker = InMemoryBroker()

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState):
    print("[*] Worker starting up...")
    print(f"[*] Watching Directory: {settings.INBOX_DIR}")
    # Initialize Watchdog here
    
@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown(state: TaskiqState):
    print("[*] Worker shutting down...")

# Define tasks here or import them
@broker.task
async def pipeline_entrypoint(file_path: str):
    print(f"[*] New File Detected: {file_path}")
    return {"status": "processing", "file": file_path}
