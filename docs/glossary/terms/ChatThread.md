---
description:  ""
template: term.html
terms:
  - glossary:
    - ChatThread
---

# ChatThread

A `ChatThread` is a conversation. There are two kinds:

- **Record thread**: a discussion attached to one business record. Each record has at most one thread, created the first time someone opens the chat on it. The record types that can have a thread are a fixed set in code (<glossary:Mission>, <glossary:Expense>, <glossary:DayEntry>, <glossary:TimesheetSubmission>); the Constance setting `CHAT_RECORD_CONTENT_TYPES` decides which of them are enabled. Deleting the record deletes its thread and messages.
- **Direct thread**: a private 1:1 conversation between two active users. Each pair of users has at most one direct thread.

## Who can read and post

- Record thread: anyone who can see the record (its owner, users with the `view_any_*` or `manage_any_*` permission for that record type, superusers). Posting a message does not modify the record, so read-only (`view_any_*`) access is enough to post. Access is checked on every request: losing access to the record means losing access to its thread.
- Direct thread: only the two users. Superusers cannot read other people's direct messages, neither in the API nor in the Django admin, which shows only who talks to whom and when.

Posting is allowed whatever the state of the record (closed timesheet, cancelled mission, ...). Nobody can post to a direct thread whose other user has been deactivated; the history stays readable.

## Messages

A message is plain text, up to 4000 characters. Only its author can delete it; deleted messages stay in the thread as placeholders without their text.

A user participates in a thread when they own the record (from the thread creation), open it or post in it. The inbox and the unread counts include only the threads a user participates in and can still access. Unread messages are the messages of other users, not deleted, newer than the last time the user marked the thread as read.

The chat module is enabled by the feature flag `CHAT_ENABLED`.
