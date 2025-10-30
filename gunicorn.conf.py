# Gunicorn Configuration for WebPortal Production
import multiprocessing
import os
from pathlib import Path

# Server socket
bind = "127.0.0.1:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr  
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'webportal_gunicorn'

# Server mechanics
daemon = False
pidfile = None  # Let systemd handle PID
user = 'root'
group = 'root'
tmp_upload_dir = None

# SSL (if needed in future)
keyfile = None
certfile = None

# Application
pythonpath = '/opt/webportal-flask'
chdir = '/opt/webportal-flask'

# Server hooks
def when_ready(server):
    """Called just after the server is started."""
    server.log.info("WebPortal server is ready. Listening on: %s", server.address)

def worker_init(worker):
    """Called just after a worker has been forked."""
    worker.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info("Worker %s exited", worker.pid)

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker about to be forked (pid: %s)", worker.pid if worker else 'unknown')