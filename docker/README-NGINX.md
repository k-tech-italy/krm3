# KRM3 Docker with Nginx Integration

This document explains the nginx integration in the KRM3 Docker container.

## Overview

The KRM3 Docker container now includes nginx as a reverse proxy that:
- Serves static files directly (better performance)
- Serves media files directly (better performance)
- Proxies Django application routes to uWSGI
- Serves the frontend SPA for all unmatched routes
- **Automatically detects Django routes** using a management command

## Architecture

```
┌─────────────────────────────────────────────┐
│  Docker Container (Port 80, 8000, 8443)     │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │  Nginx (Port 80)                     │   │
│  │  ┌────────────────────────────────┐  │   │
│  │  │ /static/*  → Static files      │  │   │
│  │  │ /media/*   → Media files       │  │   │
│  │  │ /admin/*   → Django (uWSGI)    │  │   │
│  │  │ /api/*     → Django (uWSGI)    │  │   │
│  │  │ /be/*      → Django (uWSGI)    │  │   │
│  │  │ /oauth/*   → Django (uWSGI)    │  │   │
│  │  │ /*         → Frontend SPA      │  │   │
│  │  └────────────────────────────────┘  │   │
│  └───────────────┬──────────────────────┘   │
│                  │                          │
│                  ▼                          │
│  ┌──────────────────────────────────────┐   │
│  │  uWSGI (Port 8000)                   │   │
│  │  Django Application                  │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  Managed by Circus Process Manager          │
└─────────────────────────────────────────────┘
```

## How It Works

### 1. Dynamic Route Detection and Templating

The Django management command `generate_nginx_config` automatically:
- Inspects Django's URL configuration
- Extracts first-level URL paths (e.g., `/admin/`, `/api/`, `/be/`)
- Filters out static assets (PWA files, static/media URLs)
- Exports Django configuration as shell environment variables

The nginx configuration is then generated from a template using `envsubst`:
- Template file: `/etc/nginx/sites-available/krm3.conf.template`
- Variables from Django: `DJANGO_ROUTES_PATTERN`, `STATIC_URL`, `MEDIA_URL`
- Variables from environment: `KRM3_STATIC_ROOT`, `KRM3_MEDIA_ROOT`
- Final config: `/etc/nginx/sites-enabled/krm3.conf`

### 2. Container Startup Sequence

When the container starts (`docker/etc/entrypoint.sh`):

1. **Setup Phase**:
   - Run database migrations
   - Collect static files
   - Create admin user
   - **Export Django config as environment variables**
   - **Generate nginx config from template using envsubst**
   - **Validate nginx configuration**

2. **Service Start**:
   - Circus starts nginx (priority 1) with the generated configuration
   - Circus starts uWSGI (priority 2)

### 3. Request Flow

**Static Files** (`/static/*`):
```
Request → Nginx → Serve from $KRM3_STATIC_ROOT
```

**Media Files** (`/media/*`):
```
Request → Nginx → Serve from $KRM3_MEDIA_ROOT
```

**Django Routes** (`/admin/*`, `/api/*`, `/be/*`, etc.):
```
Request → Nginx → uWSGI (localhost:8000) → Django
```

**Frontend Routes** (everything else):
```
Request → Nginx → Serve index.html from $KRM3_STATIC_ROOT
```

## Files Changed

### New Files

1. **`src/krm3/management/commands/generate_nginx_config.py`**
   - Django management command
   - Extracts URL patterns from Django configuration
   - Exports configuration as shell environment variables

2. **`docker/etc/nginx.conf`**
   - Main nginx configuration
   - Process management, gzip, logging, etc.

3. **`docker/etc/sites-available/krm3.conf.template`**
   - Nginx site configuration template
   - Uses `envsubst` variable substitution
   - Source of truth for nginx routing rules

### Modified Files

1. **`docker/Dockerfile`**
   - Added nginx and gettext-base (for envsubst) packages
   - Added nginx configuration files and template
   - Created required directories (`/etc/nginx/sites-available`, `/etc/nginx/sites-enabled`)
   - Set proper permissions
   - Exposed port 80 only (production ready)

2. **`docker/etc/entrypoint.sh`**
   - Added Django config export step
   - Added envsubst templating step
   - Added nginx configuration validation

3. **`docker/etc/circus.conf`**
   - Added nginx watcher
   - Updated uWSGI to listen on localhost:8000 (HTTP)
   - Set service priorities

## Usage

### Building the Image

```bash
docker build -t krm3:latest -f docker/Dockerfile .
```

### Running the Container

**Production mode with nginx (Port 80)**:
```bash
docker run -p 80:80 \
  -e KRM3_DATABASE_URL="..." \
  -e KRM3_SECRET_KEY="..." \
  -e KRM3_STATIC_ROOT="/tmp/static" \
  -e KRM3_MEDIA_ROOT="/tmp/media" \
  krm3:latest
```

**Development mode (Direct uWSGI on Port 8000)**:
```bash
docker run -p 8000:8000 \
  -e KRM3_DATABASE_URL="..." \
  -e KRM3_SECRET_KEY="..." \
  krm3:latest run
```

Access Points:
- **Nginx (Production)**: http://localhost:80
- **Direct Django (Development)**: http://localhost:8000

### Regenerating Nginx Configuration

If you add new Django URL patterns, the nginx configuration will be automatically regenerated on container restart. You can also manually regenerate it:

```bash
# Inside the container

# 1. Export Django config variables
NGINX_ENV_FILE=$(django-admin generate_nginx_config --verbose)

# 2. Source the variables
source "${NGINX_ENV_FILE}"

# 3. Generate config from template
envsubst < /etc/nginx/sites-available/krm3.conf.template > /etc/nginx/sites-enabled/krm3.conf

# 4. Clean up temp file
rm -f "${NGINX_ENV_FILE}"

# 5. Validate and reload nginx
nginx -t && nginx -s reload
```

### Testing Configuration Locally

```bash
# Dry-run (print shell script to stdout without writing)
django-admin generate_nginx_config --dry-run

# With verbose output (shows detected routes)
django-admin generate_nginx_config --dry-run --verbose

# Generate to a specific file
django-admin generate_nginx_config --output /tmp/my_env.sh --verbose
```

## Configuration

### Environment Variables

The nginx configuration uses these environment variables:

- `KRM3_STATIC_ROOT`: Path to static files (default: `/tmp/static`)
- `KRM3_MEDIA_ROOT`: Path to media files (default: `/tmp/media`)
- `STATIC_URL`: Django static URL prefix (from settings)
- `MEDIA_URL`: Django media URL prefix (from settings)

### Customizing Nginx

To customize nginx behavior, edit:
- **`docker/etc/nginx.conf`**: Main nginx settings (global configuration)
- **`docker/etc/sites-available/krm3.conf.template`**: Site-specific configuration template
- **`src/krm3/management/commands/generate_nginx_config.py`**: Route detection logic

**Benefit of Template Approach:**
- All nginx configuration is in version-controlled template files
- No need to modify Python code to change nginx settings
- Easy to review nginx changes in Git diffs
- Standard `envsubst` pattern familiar to DevOps teams

## Troubleshooting

### Check nginx logs

```bash
docker exec <container-id> tail -f /var/log/nginx/krm3_access.log
docker exec <container-id> tail -f /var/log/nginx/krm3_error.log
```

### Check if nginx is running

```bash
docker exec <container-id> circusctl status
```

### Test nginx configuration

```bash
docker exec <container-id> nginx -t
```

### Reload nginx

```bash
docker exec <container-id> nginx -s reload
```

## Benefits

1. **Performance**: Static files served directly by nginx (no Django overhead)
2. **Automatic**: Routes detected automatically from Django configuration
3. **Maintainable**: Nginx config in version-controlled templates, not generated code
4. **Production-Ready**: Gzip compression, proper caching headers, optimized settings, port 80 only
5. **Secure**: Uses `envsubst` for templating, avoiding shell injection risks
6. **Standard**: Follows common Docker/nginx patterns familiar to DevOps teams

## Technical Details

### Why localhost:8000?

uWSGI now listens on `127.0.0.1:8000` instead of `0.0.0.0:8000` because:
- Nginx proxies to it internally
- External access goes through nginx on port 80
- Direct access to uWSGI still possible via exposed port 8000

### Why Circus Priority?

Nginx starts before uWSGI (priority 1 vs 2) to ensure:
- Nginx is ready to accept requests
- uWSGI can start and bind to port 8000
- Clean startup sequence

### Route Detection and Templating Logic

The `generate_nginx_config` command:
1. Gets Django's URL resolver
2. Recursively extracts first-level paths from URL patterns
3. Filters out:
   - Empty paths
   - Static/media URL paths
   - PWA files (manifest.json, serviceworker.js, offline)
   - Regex artifacts (paths starting with dots)
4. Escapes special nginx regex characters
5. Exports as shell variables:
   - `DJANGO_ROUTES_PATTERN`: Regex pattern for nginx location block
   - `STATIC_URL`: Static files URL prefix
   - `MEDIA_URL`: Media files URL prefix

Then `envsubst` reads the template and substitutes:
- `${DJANGO_ROUTES_PATTERN}` → Django route regex
- `${STATIC_URL}` → Static URL from Django settings
- `${MEDIA_URL}` → Media URL from Django settings
- `${KRM3_STATIC_ROOT}` → Static root from environment
- `${KRM3_MEDIA_ROOT}` → Media root from environment

## Future Enhancements

Possible improvements:
- HTTPS support with Let's Encrypt
- Rate limiting for API endpoints
- Custom error pages
- CDN integration
- Health check endpoints
