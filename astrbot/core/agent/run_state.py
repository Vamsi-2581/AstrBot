"""Run outcome markers shared by the default agent and the work loop.

The agent stages and runner write these markers; the BTW work loop reads them.
They live outside the BTW package so the default runtime does not have to
import BTW to report that one of its runs failed or stopped.
"""

WORK_FAILED_EXTRA = "btw_work_failed"
THIRD_PARTY_RUNNER_ERROR_EXTRA_KEY = "_third_party_runner_error"


def mark_work_run_failed(event) -> None:
    """Record that a run failed, for work runs only.

    Chat runs keep their own error path, so the marker is written only when the
    event belongs to the work loop.

    Args:
        event: The event whose run ended in an error.
    """
    if event.get_extra("btw_loop") == "work":
        event.set_extra(WORK_FAILED_EXTRA, True)


def stop_requested(event) -> bool:
    """Return whether an event's run was asked to stop.

    Three signals mean the same thing, and no one of them covers every path:
    ``/task stop`` sets the event's own flag for a third-party runner and the
    agent stop request for a local one, and ``run_agent`` *clears* the stop
    request when it reports a user abort.  A reader that looks at only one of
    them reports a stopped run as completed.  They live here so every reader
    -- the work loop's status and the third-party stream -- cannot drift apart.

    Args:
        event: The event whose run may have been stopped.

    Returns:
        Whether the run was stopped by any of the three signals.
    """
    return (
        event.is_stopped()
        or bool(event.get_extra("agent_stop_requested"))
        or bool(event.get_extra("agent_user_aborted"))
    )
