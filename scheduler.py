import atexit

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler

from fetcher import refresh_cache

_scheduler = None


def start_scheduler(app):
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler()

    def _on_job_error(event):
        if event.exception:
            app.logger.exception(
                "Scheduled job %s failed",
                event.job_id,
                exc_info=event.exception,
            )

    _scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)
    _scheduler.add_job(refresh_cache, "interval", days=1)
    _scheduler.start()

    atexit.register(lambda: _scheduler.shutdown(wait=False))

    return _scheduler
