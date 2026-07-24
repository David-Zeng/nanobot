# WhatsApp direct-message mention policy

## Goal

Allow a WhatsApp deployment to opt into conversational direct messages: an
unsolicited direct message is ignored, while an explicit WhatsApp mention or a
reply to one of Nanobot's messages is handled.

## Configuration

Add `channels.whatsapp.dmPolicy` with these values:

- `"open"` — current behavior; handle permitted direct messages. This remains
  the default for backward compatibility.
- `"mention"` — handle a permitted direct message only when it explicitly
  mentions Nanobot or replies to Nanobot's message.

The existing `groupPolicy` remains unchanged. Its `"mention"` behavior
continues to accept an explicit mention or a reply to Nanobot.

## Runtime behavior

After identifying whether a WhatsApp event is a group message, the channel
applies the corresponding policy before message processing, media download,
read receipts, or agent invocation:

- Group messages use `groupPolicy`.
- Direct messages use `dmPolicy`.
- In either mention policy, `_is_addressed_to_bot()` is the predicate. It
  returns true for an explicit WhatsApp mention or a reply-to-bot context.

Authorization through `allowFrom` is preserved and remains a separate check.

## Management and documentation

Expose `dmPolicy` through the WhatsApp channel management manifest as an enum
with `"open"` as its default. Document the setting in the WhatsApp guide and
channel configuration reference.

## Validation

Add tests demonstrating that:

1. A permitted direct message is ignored under `dmPolicy: "mention"` when it
   has neither a bot mention nor reply context.
2. A permitted direct message is accepted under that policy when it mentions
   Nanobot.
3. A permitted direct message is accepted under that policy when it replies to
   Nanobot.
4. The default `dmPolicy: "open"` retains current direct-message behavior.

## Deployment

After the code is merged and deployed, set the Pi configuration to:

```json
{
  "channels": {
    "whatsapp": {
      "dmPolicy": "mention"
    }
  }
}
```

Then recreate the gateway and verify the health endpoint and effective
non-secret WhatsApp configuration.
