from __future__ import annotations

from aikit.jobqueue.arq_queue import ArqJobQueue


def test_registered_function_is_named_by_task_not_qualname():
    """Regression test: arq's `func()` names a job from `coroutine.__qualname__`
    when `name` is omitted, and a closure's qualname is always its def-site
    path (e.g. "ArqJobQueue.register.<locals>.wrapper") - never the task
    name. Caught in a live Docker run where the worker registered the
    wrapper under its qualname and every job then failed with
    "function 'execute_case' not found"."""
    queue = ArqJobQueue("redis://localhost:6379/0")

    async def handler(payload: dict) -> None:
        pass

    queue.register("execute_case", handler)

    [registered] = queue.functions
    assert registered.name == "execute_case"


def test_multiple_registrations_keep_distinct_names():
    queue = ArqJobQueue("redis://localhost:6379/0")

    async def handler_a(payload: dict) -> None:
        pass

    async def handler_b(payload: dict) -> None:
        pass

    queue.register("task_a", handler_a)
    queue.register("task_b", handler_b)

    names = {f.name for f in queue.functions}
    assert names == {"task_a", "task_b"}
