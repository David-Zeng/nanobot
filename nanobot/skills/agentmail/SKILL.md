---
name: agentmail
description: "Send and receive email programmatically using the AgentMail CLI. Use for reading inboxes, sending messages, replying to threads, and managing drafts."
metadata: {"nanobot":{"emoji":"📧","requires":{"bins":["agentmail"],"env":["AGENTMAIL_API_KEY"]}}}
---

# AgentMail Skill

Use the `agentmail` CLI to send and receive email. The binary is at `/usr/local/bin/agentmail` and `AGENTMAIL_API_KEY` is pre-configured in the environment.

## Your Inboxes

| Inbox ID | Email | Purpose |
|----------|-------|---------|
| `david-3609@agentmail.to` | david-3609@agentmail.to | kids-school |
| `davidzzz-2687@agentmail.to` | davidzzz-2687@agentmail.to | ZR |

## List Messages

```bash
agentmail inboxes:messages list --inbox-id david-3609@agentmail.to --format json
```

Response fields per message: `message_id`, `thread_id`, `from`, `to`, `subject`, `preview`, `labels`, `timestamp`, `attachments`.

## Read a Full Message

The `get` subcommand (not `retrieve`) fetches full body. Message IDs containing `<`, `@`, `>` must be URL-encoded:

```bash
# URL-encode the message_id: < → %3C, @ → %40, > → %3E
agentmail inboxes:messages get \
  --inbox-id david-3609@agentmail.to \
  --message-id "%3Cmessage-id%40domain.com%3E" \
  --format json
```

Full response fields: `message_id`, `thread_id`, `from`, `to`, `subject`, `labels`, `timestamp`, `preview`, `text`, `html`, `extracted_text`, `extracted_html`, `attachments`, `in_reply_to`, `references`, `headers`, `smtp_id`, `size`.

Use `extracted_text` for clean readable body (strips HTML). Fall back to `text` if empty.

Python snippet to URL-encode a message ID:
```python
import urllib.parse
encoded_id = urllib.parse.quote(message_id, safe='')
```

## Threads

```bash
# List threads
agentmail inboxes:threads list --inbox-id david-3609@agentmail.to --format json

# Get a full thread (all messages in context)
agentmail inboxes:threads get --inbox-id david-3609@agentmail.to --thread-id <thread_id> --format json
```

## Send Email

```bash
# Send a new email
agentmail inboxes:messages send \
  --inbox-id david-3609@agentmail.to \
  --to "recipient@example.com" \
  --subject "Hello" \
  --text "Message body"

# Reply to a message
agentmail inboxes:messages reply \
  --inbox-id david-3609@agentmail.to \
  --message-id "%3Cmessage-id%40domain.com%3E" \
  --text "Reply body"

# Forward a message
agentmail inboxes:messages forward \
  --inbox-id david-3609@agentmail.to \
  --message-id "%3Cmessage-id%40domain.com%3E" \
  --to "someone@example.com"
```

## Drafts

```bash
# Create a draft
agentmail inboxes:drafts create \
  --inbox-id david-3609@agentmail.to \
  --to "recipient@example.com" \
  --subject "Draft subject" \
  --text "Draft body"

# Send a draft
agentmail inboxes:drafts send --inbox-id david-3609@agentmail.to --draft-id <draft_id>
```

## Workflow Tips

- Always use `--format json` when extracting fields from output.
- `message_id` values like `<foo@bar.com>` must be URL-encoded before passing as a flag.
- Use `extracted_text` for the clean email body; fall back to `text` if empty.
- Use threads (`inboxes:threads get`) for multi-turn conversations to get full context.
- Draft first if the user wants to review before sending.
