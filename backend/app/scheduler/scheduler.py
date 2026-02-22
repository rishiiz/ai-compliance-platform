"""APScheduler setup and lifecycle."""

from apscheduler.schedulers.background import BackgroundScheduler

from app.scheduler.jobs import run_compliance_scan

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler | None:
    """Return the global scheduler instance, or None if not started."""
    return _scheduler


def start_scheduler() -> None:
    """Create and start the background scheduler with the compliance scan job."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(run_compliance_scan, "interval", hours=24, id="compliance_scan")
    _scheduler.start()


def stop_scheduler() -> None:
    """Shut down the scheduler and wait for running jobs to finish."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=True)
    _scheduler = None
