# Phone notifications (Wizard OS Android app, no Google push)

Notifications is the box's router for instant phone notifications. Nothing passes through Google (no FCM) or any
other third party: the Wizard OS Android app holds one connection to this box over the owner's Tailscale.

```
app on the box ──POST its inbox feed──▶ Notifications router ──one SSE stream over Tailscale──▶ Android app
   (uses: [notifications])                (routes: Chats · Badge ·                              (one channel per app,
                                            Morning report · Off)                                tap = that app's session)
```

## For apps: send your feed

Declare `uses: [notifications]` in `wizard.md`. The App Manager then puts the app on the link network
`wizard-link-<app>--notifications`, where Notifications answers as `notifications`. Whenever the app's inbox feed
changes (and once at start), POST the whole feed:

```
POST http://notifications:8080/notifications/api/app-feed
Content-Type: application/json

{"inbox": 1, "items": [{"key": "chat:abc", "title": "Carlos", "text": "See you at 5", "time": 1761893000,
  "priority": 3, "actions": [{"id": "reply", "label": "Reply", "input": true}, {"id": "read", "label": "Mark as read"}]}]}
→ 200 {"ok": true, "app": "<your id>", "events": <n>, "route": "chats|badge|daily|off"}
```

- The body is exactly the Wizard OS inbox feed (`GET /<app>/api/inbox`): one item per thing that needs the owner;
  an item leaves the feed when the owner handles it anywhere. Re-sending the same feed is free (it is diffed).
- The app is identified by the link network the request arrives on (Docker names it), never by the body. Requests
  through Tailscale Serve or from any other network get 403.
- Actions: `input` actions become an inline reply on the phone, plain actions a notification button; both are posted
  back by the phone to the app's own `POST /<app>/api/inbox/act` (`{key, action, text}`) as the owner. `ask` actions
  (agent) are not offered on the phone.

## Routing (the owner's choice, saved on the box)

`GET/POST /notifications/api/routes` (Settings › Notifications). Only **Chats** reaches the phone as a notification:

| Route | Phone |
|---|---|
| Chats | `notify` on new or newer activity (`alert: true`), quiet update when only the words change, `clear` when it leaves the feed |
| Badge (default for apps) | `count` only; no words are stored or sent |
| Morning report | not offered for apps (greyed out); nothing |
| Off | nothing |

Moving an app out of Chats sends `clear` for its notifications and forgets their words.

## For the phone: one stream, nothing lost

```
GET /notifications/api/phone              → {"phone": 1, "stream": "api/phone/stream", "events": "api/phone/events"}
GET /notifications/api/phone/stream?since=<last id>&sid=<server id>      (text/event-stream)
GET /notifications/api/phone/events?since=<last id>&sid=<server id>      (same catch-up as one JSON answer)
```

- First `hello {v, sid, latest}`; then either every event after `since`, or one `reset {items, counts}` snapshot when
  the phone has no cursor, the cursor is older than what is kept (7 days / 5000 events) or the store is new (`sid`
  changed). Then live events as they happen (`id:` = cursor), and `: ping` every 25 s.
- Readers come through Tailscale Serve with a user identity (`Tailscale-User-Login`), never from an app container.
  Set `PHONE_OWNER_LOGIN` to accept only the owner's login.
- Store: `/data/phone.sqlite3` (events, current Chats items, Badge counts).

## For the phone's own reader: a wake-up line

The Android app also reads Notifications' items itself (`GET /notifications/api/items`, per-app channels, its own
rules and watermark; wizard-ux issue 1567). On its own it reads every 30 s while it runs and every 15 minutes after
that, so a locked, dozing phone could see an item late. With the phone switch `wizard/phone-push` on, it keeps one
more connection open (wizard-ux issue 1618):

```
GET /notifications/api/phone/inbox        (text/event-stream)
event: hello   data: {"type":"hello","v":1}                         read once now
event: inbox   data: {"type":"inbox","id":"<item id>","time":<s>}   a new item: read once now
: ping                                                               every 50 s while quiet (PHONE_INBOX_PING_S)
```

- It follows ntfy's own live subscription of the inbox topics (`INBOX_TOPICS`), so an item is told the moment it is
  published; after the box loses ntfy for a moment it asks ntfy for everything since the last item it saw.
- It carries no words: the phone reads the item through `api/items` as before, so Off and quiet items stay off it.
- Same readers as the phone stream: through Tailscale Serve with a user identity, never another app's container.

Tests: `python -m unittest tests.test_phone` (diff rules, routes, catch-up, sender/reader identity, the real SSE
endpoint on a socket).
