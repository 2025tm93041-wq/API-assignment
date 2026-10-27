"""gRPC Task Manager client.

    python client.py              # main flow (create x3, get #2, list, bidi updates)
    python client.py --errors     # error-case demo
    python client.py --timeout    # 1s-deadline demo (start server with --delay 2)
"""
import argparse

import grpc
import task_pb2
import task_pb2_grpc


def fmt(t):
    return f"Task(id={t.id}, title='{t.title}', status='{t.status}')"


def main_flow(stub):
    print("\n=== 1. Create three tasks ===")
    for title in ["Write report", "Review code", "Deploy service"]:
        print("Created:", fmt(stub.CreateTask(task_pb2.CreateTaskRequest(title=title))))

    print("\n=== 2. Fetch task #2 ===")
    print("Fetched:", fmt(stub.GetTask(task_pb2.GetTaskRequest(id=2))))

    print("\n=== 3. ListTasks (server streaming) ===")
    for t in stub.ListTasks(task_pb2.ListTasksRequest()):
        print("  ->", fmt(t))

    print("\n=== 4. StreamTaskUpdates (bidirectional) ===")
    updates = [(1, "in_progress"), (2, "done"), (3, "in_progress")]

    def gen():
        for tid, st in updates:
            print(f"  client sends: id={tid}, status={st}")
            yield task_pb2.UpdateTaskRequest(id=tid, status=st)

    for resp in stub.StreamTaskUpdates(gen()):
        print("  server replies:", fmt(resp))

    print("\n=== UpdateTaskStatus (unary) ===")
    print(fmt(stub.UpdateTaskStatus(task_pb2.UpdateTaskRequest(id=1, status="done"))))


def error_cases(stub):
    print("\n=== Error cases ===")
    cases = [
        ("GetTask id=0 (expect INVALID_ARGUMENT)", lambda: stub.GetTask(task_pb2.GetTaskRequest(id=0))),
        ("GetTask id=999 (expect NOT_FOUND)", lambda: stub.GetTask(task_pb2.GetTaskRequest(id=999))),
        ("UpdateTaskStatus status='blocked' (expect FAILED_PRECONDITION)",
         lambda: stub.UpdateTaskStatus(task_pb2.UpdateTaskRequest(id=1, status="blocked"))),
        ("CreateTask status='xyz' (expect FAILED_PRECONDITION)",
         lambda: stub.CreateTask(task_pb2.CreateTaskRequest(title="x", status="xyz"))),
    ]
    for label, call in cases:
        try:
            call()
            print(f"{label}: unexpected success")
        except grpc.RpcError as e:
            print(f"{label}\n   -> {e.code().name}: {e.details()}")


def get_with_deadline(stub, task_id=1, timeout=1.0):
    print(f"\n=== GetTask with {timeout}s deadline ===")
    try:
        t = stub.GetTask(task_pb2.GetTaskRequest(id=task_id), timeout=timeout)
        print("Received in time:", fmt(t))
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            print(f"Timeout handled gracefully: server did not respond within {timeout}s "
                  "(DEADLINE_EXCEEDED). Please retry later.")
        else:
            print(f"RPC failed: {e.code().name}: {e.details()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost:50051")
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--timeout", action="store_true")
    a = ap.parse_args()
    with grpc.insecure_channel(a.host) as ch:
        stub = task_pb2_grpc.TaskServiceStub(ch)
        if a.timeout:
            get_with_deadline(stub, 1, 1.0)
        elif a.errors:
            error_cases(stub)
        else:
            main_flow(stub)
