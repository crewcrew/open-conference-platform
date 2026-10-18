import os

bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
worker_class = "sync"
timeout = 60
graceful_timeout = 30
accesslog = None  # URLs include private booking/ticket tokens; log aggregate metrics at the proxy.
errorlog = "-"
capture_output = True
# Only trust forwarded headers on an isolated private app network behind your proxy.
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")
