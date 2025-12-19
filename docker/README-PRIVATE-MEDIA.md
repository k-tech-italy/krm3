# Private Media Files with Nginx X-Accel-Redirect

This document explains the private media file serving feature in KRM3, which uses nginx's X-Accel-Redirect to serve protected files efficiently with Django permission checks.

## Overview

The private media feature provides:
- **Access Control**: Files are only accessible to authorized users via Django permission checks
- **Performance**: Nginx handles actual file serving using zero-copy sendfile
- **Security**: Real file paths are never exposed to clients
- **Integration**: Uses django_simple_dms's built-in CRUD+Share permission system

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Client Request: /media-auth/123/                       │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Nginx (Port 80)                                        │
│  - Proxies /media-auth/* → Django (uWSGI:8000)          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Django (ProtectedDocumentView)                         │
│  1. Check user authentication                           │
│  2. Get Document by PK                                  │
│  3. Check permissions (accessible_by)                   │
│  4. Return X-Accel-Redirect: /protected-media/...       │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Nginx Internal Location: /protected-media/             │
│  - "internal" directive prevents direct access          │
│  - Serves file from PRIVATE_MEDIA_ROOT                  │
│  - Sets proper Content-Type headers                     │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Django Settings

The following settings are automatically configured via environment variables:

```python
# In src/krm3/config/__init__.py and settings.py
PRIVATE_MEDIA_ROOT = env('PRIVATE_MEDIA_ROOT')  # Default: ~private-media/
PRIVATE_MEDIA_URL = env('PRIVATE_MEDIA_URL')    # Default: /protected-media/
```

### Environment Variables

**Local Development:**
- `PRIVATE_MEDIA_ROOT`: `~private-media/` (in project root)
- `PRIVATE_MEDIA_URL`: `/protected-media/`

**Docker Container:**
- `KRM3_PRIVATE_MEDIA_ROOT`: `/data/private-media`
- `KRM3_PRIVATE_MEDIA_URL`: `/protected-media/`

**Production with Persistent Storage:**
```bash
docker run -p 80:80 \
  -v /var/lib/krm3/private-media:/data/private-media \
  -e KRM3_PRIVATE_MEDIA_ROOT="/data/private-media" \
  -e KRM3_DATABASE_URL="..." \
  krm3:latest
```

### Nginx Configuration

The nginx configuration is **automatically generated** from Django settings:

```bash
# Generate configuration
django-admin generate_nginx_config --output /etc/nginx/sites-enabled/krm3.conf

# The generated config includes:
location /protected-media/ {
    internal;  # Prevents direct access from clients
    alias /data/private-media/;
}
```

The `internal` directive ensures files can only be served via X-Accel-Redirect from Django.

## Components

### 1. PrivateMediaStorage Class

**File:** `src/krm3/core/storage.py`

Custom Django storage backend for private media files:

```python
from krm3.core.storage import PrivateMediaStorage

# Usage in models (future implementation)
class MyModel(models.Model):
    private_file = models.FileField(storage=PrivateMediaStorage())
```

### 2. ProtectedDocumentView

**File:** `src/krm3/web/views.py`

Class-based view that handles authorization and file serving:

```python
class ProtectedDocumentView(LoginRequiredMixin, TemplateView):
    """Serve protected documents via nginx X-Accel-Redirect."""

    def get(self, request, pk):
        # 1. Check authentication (via LoginRequiredMixin)
        # 2. Get document and verify permissions
        # 3. Return X-Accel-Redirect response
```

**URL Pattern:** `src/krm3/web/urls.py`
```python
path('media-auth/<int:pk>/', ProtectedDocumentView.as_view(), name='protected_media')
```

### 3. Permission System

Uses **django_simple_dms's built-in permission system**:

- **Document.admin**: Owner has full RUDS (Read, Update, Delete, Share) permissions
- **DocumentGrant.user**: Direct user permissions
- **DocumentGrant.group**: Permissions inherited from user's groups
- **Document.objects.accessible_by(user)**: QuerySet of accessible documents

## Usage

### Accessing Protected Documents

**In Templates:**
```html
<!-- Link to protected document -->
<a href="{% url 'protected_media' document.pk %}">
    Download {{ document.document.name }}
</a>
```

**In Python/API:**
```python
from django.urls import reverse

# Generate URL for protected document
url = reverse('protected_media', kwargs={'pk': document.pk})
# Example: /media-auth/123/
```

**Direct Request:**
```bash
# Client requests (must be authenticated)
GET /media-auth/123/

# If authorized, Django returns X-Accel-Redirect header
# Nginx then serves the file from /data/private-media/documents/...
```

### Permission Checks

The view automatically checks permissions using django_simple_dms:

```python
# User must be:
# 1. Authenticated
# 2. Document admin, OR
# 3. Have direct DocumentGrant, OR
# 4. Member of group with DocumentGrant

accessible_docs = Document.objects.accessible_by(request.user)
if not accessible_docs.filter(pk=doc.pk).exists():
    raise Http404('Document not found or access denied')
```

## Migration Strategy

### Option A: Protect Existing Documents

For existing documents in public media, you can protect them in-place:

```python
# The nginx configuration already supports this
# Just use the ProtectedDocumentView URL instead of direct media URLs
```

### Option B: Move to Private Storage

To move existing documents to private storage:

```python
# Management command (to be created if needed)
from pathlib import Path
import shutil
from django.conf import settings
from django_simple_dms.models import Document

for doc in Document.objects.all():
    old_path = Path(settings.MEDIA_ROOT) / doc.document.name
    new_path = Path(settings.PRIVATE_MEDIA_ROOT) / doc.document.name

    if old_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
```

### Option C: New Documents with Private Storage

For new documents, use the PrivateMediaStorage:

```python
# Create proxy model or extend existing models
from django_simple_dms.models import Document as BaseDMSDocument
from krm3.core.storage import PrivateMediaStorage

class ProtectedDocument(BaseDMSDocument):
    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        if not self.pk and hasattr(self, 'document'):
            self.document.storage = PrivateMediaStorage()
        super().save(*args, **kwargs)
```

## Testing

### Local Development

1. Create a test document:
```python
from django_simple_dms.models import Document
doc = Document.objects.create(...)
```

2. Access via protected URL:
```bash
curl -u user:pass http://localhost:8000/media-auth/1/
```

### Docker Container

1. Build and run:
```bash
docker build -t krm3:latest -f docker/Dockerfile .
docker run -p 80:80 -e KRM3_DATABASE_URL="..." krm3:latest
```

2. Verify nginx configuration:
```bash
docker exec <container> cat /etc/nginx/sites-enabled/krm3.conf
# Should show /protected-media/ with "internal" directive
```

3. Test file access:
```bash
# This should work (if authenticated and authorized)
curl -b cookies.txt http://localhost/media-auth/123/

# This should fail with 404 (internal location)
curl http://localhost/protected-media/documents/2025/01/19/file.pdf
```

## Security Considerations

### 1. Direct Access Prevention

The `internal` directive in nginx prevents direct access:
```nginx
location /protected-media/ {
    internal;  # Returns 404 if accessed directly
    alias /data/private-media/;
}
```

### 2. Authentication Required

The view uses `LoginRequiredMixin`, requiring authentication before any file access.

### 3. Permission Checks

Uses django_simple_dms's robust permission system with user/group grants.

### 4. Path Traversal Protection

- Django's FileField validates paths
- Nginx's internal location prevents path manipulation
- X-Accel-Redirect header sanitized by Django

### 5. File Path Exposure

Real file system paths are never exposed to clients - only logical document IDs are used in URLs.

## Performance Benefits

### Nginx Sendfile

Nginx uses efficient zero-copy sendfile() syscall:
- No data copying between kernel and user space
- Minimal CPU usage for file serving
- High throughput for large files

### Django Offloading

Django only handles:
- Authentication (session lookup)
- Permission checks (database query)
- Response headers (minimal processing)

Nginx handles:
- Actual file serving
- Content-Type detection
- Range requests (partial downloads)
- Gzip compression (if configured)

## Troubleshooting

### 404 Errors

**Issue:** Getting 404 when accessing `/media-auth/123/`

**Solutions:**
- Check user is authenticated
- Verify user has permission to document
- Check document exists: `Document.objects.get(pk=123)`

### Files Not Served

**Issue:** X-Accel-Redirect sent but file not served

**Solutions:**
```bash
# Check nginx error log
docker exec <container> tail -f /var/log/nginx/krm3_error.log

# Verify file exists
docker exec <container> ls -la /data/private-media/documents/...

# Check nginx config generated correctly
docker exec <container> cat /etc/nginx/sites-enabled/krm3.conf
```

### Permission Denied

**Issue:** User cannot access document they should have access to

**Solutions:**
```python
# Check document grants
from django_simple_dms.models import Document, DocumentGrant

doc = Document.objects.get(pk=123)
grants = DocumentGrant.objects.filter(document=doc)

# Check user's accessible documents
accessible = Document.objects.accessible_by(user)
print(doc in accessible)
```

## Future Enhancements

Potential improvements:
- [ ] Audit logging for file access
- [ ] Download counters
- [ ] Rate limiting per user
- [ ] Temporary signed URLs for external sharing
- [ ] Automatic file encryption at rest
- [ ] CDN integration with signed URLs
- [ ] File virus scanning before serving

## References

- [Nginx X-Accel Documentation](http://nginx.org/en/docs/http/ngx_http_core_module.html#internal)
- [Django Custom Storage Backends](https://docs.djangoproject.com/en/stable/howto/custom-file-storage/)
- [django_simple_dms Documentation](https://github.com/saxix/django-simple-dms)
