from asgiref.local import Local

# This single object acts exactly like a thread-local but is fully async-safe
request_ctx = Local()
