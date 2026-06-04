from celery_tasks.tasks import ping
r = ping.delay()
print('Task queued, id=', r.id)
