# WhatsApp mention keyword trigger

## Goal

Let a user bootstrap a conversation under `dmPolicy: "mention"` (or
`groupPolicy: "mention"`) by starting a message with a literal keyword such as
`@nanobot`. Today `_is_addressed_to_bot()` accepts only a genuine WhatsApp
@mention or a reply to Nanobot; one-to-one chats cannot produce a genuine
@mention, so a fresh direct message can never pass the policy.

## Configuration

Add `channels.whatsapp.mentionKeyword` (Python: `mention_keyword`):

- Type: string. Default: `"@nanobot"`.
- Empty string `""` disables the text trigger, restoring mention/reply-only
  behavior.

## Matching semantics

A message matches the keyword when its text — from `_message_text()`, which
covers plain text, extended text, and media captions — satisfies all of:

1. Starts with the keyword after any leading whitespace.
2. Comparison is case-insensitive (`@NanoBot` matches).
3. The keyword is followed by whitespace or end-of-message, so `@nanobots`
   does not match.

`_is_addressed_to_bot()` returns true for a genuine mention, a reply to
Nanobot, or a keyword match. It is used by both the DM and group `"mention"`
policies, so the keyword works in both chat kinds. Voice notes without
captions have no text and still require reply-to-bot.

## Prefix stripping

After text extraction, a matching keyword prefix is removed before the agent
sees the message: `@nanobot what's up` becomes `what's up`. Stripping applies
regardless of the active policy so behavior stays consistent when a policy is
switched back to `"open"`. A bare `@nanobot` with no media strips to empty
text and is dropped by the existing empty-message guard.

## Management and documentation

Expose `mentionKeyword` through the WhatsApp channel management manifest as a
string field with default `"@nanobot"`, add labels to the ten WebUI locale
files, and document the setting in the WhatsApp guide and Docker setup guide.

## Validation

Tests demonstrating:

1. Under `dmPolicy: "mention"`, a direct message starting with the keyword is
   accepted and the keyword is stripped from the delivered content.
2. Case-insensitive match and leading-whitespace tolerance.
3. `@nanobots …` and `hey @nanobot …` are still ignored.
4. `mentionKeyword: ""` restores mention/reply-only behavior.
5. Under `groupPolicy: "mention"`, a group message starting with the keyword
   is accepted.
6. Setup manifest exposes `mentionKeyword` as a string defaulting to
   `"@nanobot"`.

## Deployment

Deploy via the standard Pi pattern. The default activates without a config
change; set `mentionKeyword` explicitly in `/home/pi/.nanobot/config.json`
for visibility.
