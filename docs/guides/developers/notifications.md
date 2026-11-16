---
title: Notifications
---

# Notifications

KRM3 uses dedicated notification classes to keep event payload construction out of views.

Each notification extends `Notification` and implements `__call__`:

```python
HolidayNotification()(resource, dates)
```

## Registry

Available notifications are declared in `NOTIFICATIONS`:

```python
NOTIFICATIONS = {
    'holidays': HolidayNotification,
}
```

## Adding a notification

To add a notification:

1. Create a `Notification` subclass.
2. Build and dispatch the event through `EventDispatcher`.
3. Add the class to `NOTIFICATIONS`.
4. Add the relevant tests.

## Listing notifications

List the registered notifications with:

```console
$ ./manage.py list_notifications
Available notifications:
- holidays: HolidayNotification
```

The command only reads the local registry and does not synchronize configuration with Bitcaster.

## Bitcaster event mapping

KRM3 dispatches notifications through `bitcaster-django`. Each registered local notification that is sent must have
an `EventConfig` row mapping its local name to an event slug in the configured Bitcaster application. The mapping can
be managed from the Django admin.

For example:

| Local name | Remote event slug |
|---|---|
| `holidays` | `holidays` |
| `timesheet_pending` | `timesheet_pending` |
