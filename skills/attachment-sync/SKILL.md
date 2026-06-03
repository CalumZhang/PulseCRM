---
name: pulsecrm-attachment-sync
description: >
  Backfill file evidence (screenshots, recordings) onto tickets when the
  attachments live behind a private URL on the source platform that the tracker
  can't fetch directly. Use periodically to fill empty attachment fields on
  tickets that link back to a source message. Read-only except for adding the
  attachment; idempotent and safe. Generic and configurable.
---

# Attachment Sync

Some trackers can't ingest files whose URLs are private to the chat platform
(they require a bot token). When a triager files a ticket, the attachment field
is often left empty for that reason. This worker closes the gap: it finds tickets
missing attachments, walks back to the linked source message, and uploads the
eligible files.

## When to act

Run on a schedule (e.g. every few minutes) or on demand. For each ticket:

Process it **only when all hold**:
- the ticket's attachment field is currently **empty**, AND
- the ticket has a source link (the original message/thread), AND
- the file is an image or video, AND
- the file was uploaded by a real user (not a bot), AND
- the file is within a sane size cap and a sane time window of the report.

## Behavior

1. Read tickets missing attachments that have a source link.
2. Fetch the source message (and its thread) and collect eligible files.
3. Upload each file to the tracker's file API and attach it to the ticket.
4. Be **idempotent**: skip tickets that already have attachments; a per-file
   failure must not abort the others or the run.

## Rules

- **Only ever write the attachment field.** Never modify any other field, never
  delete anything.
- Skip silently when there's nothing eligible.
- Stay generic: source platform, tracker, size cap, and time window come from
  config; assume no specific product.

This pairs with the `attachment_sync` enricher adapter
(`../../src/pulsecrm/adapters/enrichers/attachment_sync.py`) for a code-based
implementation of the same job.
