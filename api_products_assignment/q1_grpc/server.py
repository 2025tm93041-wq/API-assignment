"""gRPC Task Manager server (in-memory store).

Usage:
    python server.py               # normal server on :50051
    python server.py --delay 2     # GetTask sleeps 2s (timeout demo)
"""
import argparse
import threading
import time
from concurrent import futures

import grpc
import task_pb2
import task_pb2_grpc

VALID_STATUSES = {"pending", "in_progress", "done"}


class TaskService(task_pb2_grpc.TaskServiceServicer):
    def __init__(self, get_delay=0.0):
        self._tasks = {}          # id -> Task
        self._next_id = 1         # incremental ID generator
        self._lock = threading.Lock()
        self._get_delay = get_delay

    # ---- helpers ---------------------------------------------------------
    def _validate_status(self, status, context):
        if status not in VALID_STATUSES:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}",
            )

    def _get_or_abort(self, task_id, context):
        task = self._tasks.get(task_id)
        if task is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Task {task_id} not found")
        return task

    # ---- 1. Create -------------------------------------------------------
    def CreateTask(self, request, context):
        if not request.title.strip():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "title must not be empty")
        status = request.status or "pending"
        self._validate_status(status, context)
        with self._lock:
            task = task_pb2.Task(id=self._next_id, title=request.title, status=status)
            self._tasks[task.id] = task
            self._next_id += 1
        print(f"[server] Created task {task.id}: {task.title} ({task.status})")
        return task

    # ---- 2. Get by ID ----------------------------------------------------
    def GetTask(self, request, context):
        if request.id < 1:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "id must be >= 1")
        if self._get_delay > 0:                       # simulate slow server
            print(f"[server] GetTask sleeping {self._get_delay}s ...")
            time.sleep(self._get_delay)
        with self._lock:
            return self._get_or_abort(request.id, context)

    # ---- 3. List all (server streaming) ----------------------------------
    def ListTasks(self, request, context):
        with self._lock:
            snapshot = list(self._tasks.values())
        for task in snapshot:
            yield task

    # ---- 4. Update status ------------------------------------------------
    def UpdateTaskStatus(self, request, context):
        self._validate_status(request.status, context)
        with self._lock:
            task = self._get_or_abort(request.id, context)
            task.status = request.status
            return task

    # ---- 5. Bidirectional streaming --------------------------------------
    def StreamTaskUpdates(self, request_iterator, context):
        for req in request_iterator:
            print(f"[server] stream update -> id={req.id}, status={req.status}")
            self._validate_status(req.status, context)
            with self._lock:
                task = self._get_or_abort(req.id, context)
                task.status = req.status
                updated = task_pb2.Task(id=task.id, title=task.title, status=task.status)
            yield updated


def serve(port=50051, delay=0.0):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    task_pb2_grpc.add_TaskServiceServicer_to_server(TaskService(delay), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[server] Task Manager listening on :{port} (GetTask delay={delay}s)")
    server.wait_for_termination()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=50051)
    p.add_argument("--delay", type=float, default=0.0, help="seconds GetTask sleeps")
    a = p.parse_args()
    serve(a.port, a.delay)
