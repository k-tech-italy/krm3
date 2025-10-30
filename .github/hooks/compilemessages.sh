#!/bin/sh
set -e # Exit immediately if a command exits with a non-zero status.

# Look for manage.py in the current directory and parent directories.
# Change into the directory where manage.py is found before running.
manage_py_path=$(find . -maxdepth 5 -type f -name 'manage.py' | head -n 1)

if [ -z "$manage_py_path" ]; then
    echo "Could not find manage.py to run compilemessages."
    exit 1
fi

base_dir=$(dirname "$manage_py_path")
echo "Found manage.py in '$base_dir'. Compiling messages..."

# Run compilemessages from the directory containing manage.py
(cd "$base_dir" && python manage.py compilemessages)
