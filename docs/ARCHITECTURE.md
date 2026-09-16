# Mi Ruta Pro — Architecture Diagrams

**Generated:** 2026-09-16 · **Branch:** `gdpr-relax` · **Scope:** whole repository (`wab/`, `route_optimizer/`, `database/`, deploy files)

These diagrams reflect the code as it stands on this branch, including the **implied-consent (GDPR-relax) flow** — there is no longer a blocking consent gate; sending an address list *is* the consent act.

---

## 0. High-level flow — WhatsApp route optimization request

The 10,000-foot view: what happens, component by component, when a driver sends an address list and gets an optimized route back. Detail (rate limits, GDPR branches, command routing) is stripped out here — see section 1 for the full pipeline.

```mermaid
flowchart LR
    U(["👤 Driver<br/>WhatsApp"])

    subgraph PROVIDER ["Messaging provider"]
        WAP["Meta Cloud API<br/>or Twilio Sandbox"]
    end

    subgraph EDGE ["Webhook edge"]
        FLASK["Flask webhook_server<br/>verify signature · dispatch"]
        ADAPT["Provider adapter<br/>normalise payload"]
    end

    subgraph APP ["Application core"]
        MP["MessageProcessor<br/>route request detected"]
        AP["AddressParser<br/>extract address list"]
        UM["usage_manager<br/>tier / quota gate"]
        RB["RouteOptimizerBridge<br/>call optimizer · format reply"]
    end

    subgraph CORE ["route_optimizer"]
        RO["Directions calls (×2)<br/>original + optimized order<br/>+ 30-day file cache"]
    end

    subgraph DATA ["Persistence"]
        PG[("PostgreSQL<br/>user, tier, usage counters")]
    end

    GMAPS[("🗺️ Google Maps<br/>Directions API")]

    MS["MessageSender<br/>pick free-form vs template"]

    U -->|"1. sends address list"| WAP
    WAP -->|"2. webhook POST"| FLASK
    FLASK -->|"3. parse"| ADAPT
    ADAPT -->|"4. normalised message"| MP
    MP -->|"5. parse addresses"| AP
    AP -->|"6. address list"| MP
    MP -->|"7. check quota"| UM
    UM <-->|"read/update tier & counters"| PG
    UM -->|"8. allowed"| MP
    MP -->|"9. optimize(addresses)"| RB
    RB -->|"10. request route"| RO
    RO <-->|"11. cache hit?"| RO
    RO -->|"12. Directions API calls"| GMAPS
    GMAPS -->|"13. distance, duration, order"| RO
    RO -->|"14. route data"| RB
    RB -->|"15. formatted reply<br/>(savings + Maps link)"| MP
    MP -->|"16. record usage"| UM
    MP -->|"17. send reply"| MS
    MS -->|"18. deliver"| ADAPT
    ADAPT -->|"19. provider API call"| WAP
    WAP -->|"20. optimized route"| U

    classDef person fill:#0b4f6c,stroke:#083b52,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff
    classDef store fill:#4b5563,stroke:#374151,color:#fff
    class U person
    class WAP,GMAPS ext
    class PG store
```

**The five hops that matter:**

1. **Provider → Webhook edge** — Meta (JSON, HMAC-SHA256) or Twilio (form POST, HMAC-SHA1); the adapter pattern means `MessageProcessor` never knows which one it's talking to.
2. **Webhook edge → Application core** — `MessageProcessor` routes to `AddressParser`, which decides this is a route request (not a command, not a greeting).
3. **Application core → Persistence** — `usage_manager` checks the driver's tier/quota against PostgreSQL *before* any Google Maps call is made, so a blocked user never costs API quota.
4. **Application core → `route_optimizer` → Google Maps** — the bridge calls the pure optimizer module twice (input order + Google-optimized order) so savings can be computed; both calls are cached locally for 30 days.
5. **Application core → Provider → Driver** — the formatted reply (stops, savings, Google Maps link) goes back out through the same adapter that received the request, so Meta and Twilio each get delivery formatted their own way (single message vs. two-part split).

---

## 1. Flow diagram — inbound message pipeline

Every inbound WhatsApp message travels this path. The dashed box is the only place where money, Google Maps quota and the route result are involved.

```mermaid
flowchart TD
    START(["POST /webhook<br/>(Meta JSON or Twilio form)"]) --> GRL{"Global rate limit<br/>500/hour?"}
    GRL -- exceeded --> R429["429 Service unavailable"]
    GRL -- ok --> SIG{"Provider signature valid?<br/>X-Hub-Signature-256 / X-Twilio-Signature"}
    SIG -- no --> R403["403 Invalid signature"]
    SIG -- yes --> PARSE["provider.parse_incoming()<br/>→ normalised (message, value) tuples"]
    PARSE --> SPAWN["Spawn daemon thread per message<br/>return 200 immediately<br/>(Twilio 15s webhook timeout)"]
    SPAWN --> R200(["200 OK to provider"])

    SPAWN -.-> URL{"Per-user rate limit<br/>10/min?"}
    URL -- exceeded --> DROP1["Log + drop silently"]
    URL -- ok --> LOOP{"Loop detector<br/>3 identical msgs / 5 min?"}
    LOOP -- loop --> DROP2["Log + drop silently"]
    LOOP -- ok --> TRACK["ConversationTracker.update_conversation()<br/>upsert User + Session (24h window)<br/>assign tier if new user"]

    TRACK --> TYPE{"message type"}
    TYPE -- "image / location / document" --> PLACEHOLDER["'Not supported yet' reply"]
    TYPE -- "other" --> UNSUPPORTED["'Text only' reply"]
    TYPE -- "text" --> EMPTY{"Empty body?"}
    EMPTY -- yes --> EMPTYMSG["'Message is empty' reply"]

    EMPTY -- no --> GDPRCMD{"Is it a GDPR / billing<br/>command word?"}
    GDPRCMD -- no --> SURVEY{"Active NPS survey<br/>for this user?"}
    SURVEY -- yes --> SURVEYSTEP["FeedbackManager.handle_incoming()<br/>q1 → q2 → q3 / 'saltar'"]
    SURVEY -- no --> CMD
    GDPRCMD -- yes --> CMD{"Command router<br/>(exact match, lowercased)"}

    CMD -- "/ayuda /ejemplo /info" --> STATIC["Static help text"]
    CMD -- "/precios /pagos premium plus" --> BILLING["Stripe checkout links<br/>via StripeManager"]
    CMD -- "cancelar suscripción" --> CANCEL["stripe.Subscription.cancel()<br/>reply comes from Stripe webhook"]
    CMD -- "/privacidad /misdatos /exportar" --> GDPRREAD["Art. 15 / 20 — read + export consent record"]
    CMD -- "/eliminar /revocar" --> GDPRWRITE["Art. 17 / 7.3 — revoke consent,<br/>anonymize PII, cancel Stripe"]

    CMD -- "no command matched" --> APARSE["AddressParser.parse_addresses()"]
    APARSE --> APRESULT{"result"}
    APRESULT -- "(None, None)<br/>no address indicators" --> GREET{"Greeting or help keyword?"}
    GREET -- yes --> WELCOME["Welcome / help text"]
    GREET -- no --> FALLBACK["'I didn't understand' + command list"]
    APRESULT -- "(None, error)" --> PARSEERR["Format hint returned directly<br/>(short-circuit: no DB row yet,<br/>avoids misleading 'access check failed')"]

    APRESULT -- "(addresses, None)" --> CONSENT{"has_consent()?"}
    CONSENT -- no --> IMPLIED["save_consent(implied:first_address_list)<br/>creates User + Consent + tier<br/>→ privacy footnote flag"]
    CONSENT -- yes --> GATE
    IMPLIED --> GATE

    subgraph ROUTE ["Route request — the only metered path"]
        direction TB
        GATE{"usage_manager.check_route_allowed()"}
        GATE -- "blocked: no_credits / daily_limit /<br/>lifetime_exhausted / expired" --> BLOCKED["Tier-specific upsell message<br/>+ Stripe checkout link<br/>AuditLog: route_blocked"]
        GATE -- "allowed (or superuser bypass)" --> OPT["RouteOptimizerBridge.optimize_route()<br/>→ 2 Google Maps calls (original + optimized)<br/>via 30-day file cache"]
        OPT --> OK{"success?"}
        OK -- no --> ROUTEERR["Mapped error message<br/>(ZERO_RESULTS, NOT_FOUND, quota…)<br/>no usage recorded"]
        OK -- yes --> RECORD["record_route_used()<br/>counters + PPU credit debit<br/>AuditLog: route_requested"]
        RECORD --> TRIGGER{"3rd lifetime route?"}
        TRIGGER -- yes --> NPS["Create FeedbackSurvey,<br/>send Q1 after 5s in background thread"]
        TRIGGER -- no --> FORMAT
        NPS --> FORMAT{"provider"}
        FORMAT -- twilio --> TWOMSG["Message 1: stops + savings<br/>Message 2: Google Maps URL<br/>(1600-char guard, truncation)"]
        FORMAT -- meta --> ONEMSG["Single combined message"]
    end

    PLACEHOLDER --> SEND
    UNSUPPORTED --> SEND
    EMPTYMSG --> SEND
    SURVEYSTEP --> SEND
    STATIC --> SEND
    BILLING --> SEND
    GDPRREAD --> SEND
    GDPRWRITE --> SEND
    WELCOME --> SEND
    FALLBACK --> SEND
    PARSEERR --> SEND
    BLOCKED --> SEND
    ROUTEERR --> SEND
    TWOMSG --> SEND
    ONEMSG --> SEND

    SEND["MessageSender.send_reply()"] --> WINDOW{"provider"}
    WINDOW -- twilio --> TSEND["Always free-form<br/>(sandbox has no 24h window)"]
    WINDOW -- meta --> META24{"Within 24h window?"}
    META24 -- yes --> FREEFORM["Free-form text message"]
    META24 -- no --> TEMPLATE["Approved template ('hello_world')"]
    CANCEL --> NOREPLY(["No reply — Stripe webhook<br/>sends the confirmation"])
```

**Key invariants visible above**

- Usage is recorded **only** after a successful optimization — errors and bad addresses never cost the user a route or a credit.
- Parse errors short-circuit *before* `check_route_allowed`, because a brand-new user has no DB row yet (commit `0fe309b`).
- GDPR and billing command words bypass the survey interceptor, so a user mid-survey can still revoke or delete.

---

## 2. C4 component diagram — Level 3, inside the webhook container

One deployable container (Gunicorn, 1 worker, Railway) holds all components. Boundaries below are Python packages.

```mermaid
flowchart TB
    %% ---------- People & external systems ----------
    USER(["👤 Delivery driver<br/><i>Person</i><br/>Sends address lists over WhatsApp"])

    subgraph EXT ["External systems"]
        direction LR
        WA["WhatsApp<br/><i>Meta Cloud API</i><br/>graph.facebook.com/v18.0"]
        TW["WhatsApp<br/><i>Twilio Sandbox</i><br/>twilio.rest.Client"]
        GM["Google Maps<br/><i>Directions API</i><br/>waypoint optimization"]
        ST["Stripe<br/><i>Checkout + Billing</i><br/>PPU / Premium / Plus"]
    end

    subgraph DATASTORES ["Data stores"]
        direction LR
        PG[("PostgreSQL<br/><i>Railway</i><br/>users · consents · sessions<br/>audit_logs · feedback_surveys")]
        FSCACHE[("Local filesystem<br/><i>.cache/*.json</i><br/>30-day Directions cache")]
        LOGS[("Rotating log files<br/><i>wab/logs/</i>")]
    end

    %% ---------- The container ----------
    subgraph CONTAINER ["Container: Mi Ruta Pro webhook app — Python 3.11 · Flask + Gunicorn (1 worker) · Railway"]
        direction TB

        subgraph EDGE ["wab/app · HTTP edge"]
            FLASK["webhook_server<br/><i>Flask app</i><br/>GET/POST /webhook · /health · /<br/>/internal/stripe/webhook<br/>/payment/success · /payment/cancel<br/>ProxyFix · thread per message"]
        end

        subgraph LIM ["wab/utils · protection"]
            RL["RateLimiter<br/><i>in-memory</i><br/>10 msg/min per user"]
            LD["MessageLoopDetector<br/><i>in-memory</i><br/>3 identical / 5 min"]
            GRL["GlobalRateLimiter<br/><i>in-memory</i><br/>500 msg/hour"]
            CLEAN["cleanup thread<br/><i>daemon, hourly</i>"]
        end

        subgraph PROV ["wab/providers · adapter pattern"]
            FACTORY["get_provider()<br/><i>factory</i><br/>reads MESSAGING_PROVIDER"]
            META["MetaAdapter<br/>JSON · HMAC-SHA256 · GET challenge"]
            TWIL["TwilioAdapter<br/>form POST · HMAC-SHA1 · BSUID support"]
        end

        subgraph CORE ["wab/app · orchestration"]
            MP["MessageProcessor<br/><i>God class, ~860 lines</i><br/>command router · GDPR handlers<br/>route orchestration"]
            MS["MessageSender<br/>free-form vs template decision"]
            AP["AddressParser<br/>line / numbered formats<br/>ES road types · ZIP · dedupe · round trip"]
            UM["usage_manager<br/>tier config · route gate<br/>counters · superuser bypass"]
            CM["ConsentManager<br/><i>DB-backed</i><br/>Art. 7 / 15 / 17 / 20"]
            FM["FeedbackManager<br/>NPS survey state machine (q1→q3)"]
            SM["StripeManager<br/><i>sole Stripe boundary</i><br/>checkout · webhook dispatch"]
        end

        subgraph SUP ["wab/utils + wab/config + wab/templates"]
            CT["ConversationTracker<br/><i>DB-backed</i><br/>24h window · Session upsert"]
            CFG["Config / constants<br/>env vars · emails · URLs"]
            TPL["templates<br/>privacy policy · consent copy"]
            LOG["logger<br/>rotating file + console"]
        end

        subgraph BRIDGE ["wab/integration"]
            RB["RouteOptimizerBridge<br/><i>singleton</i><br/>calls optimizer · formats for WhatsApp<br/>1600-char splitting · fallback if worse"]
        end

        subgraph RO ["route_optimizer · pure logic, no WhatsApp knowledge"]
            ROAPI["api<br/>get_route_with_waypoints()<br/>optimize_route() — 2 calls"]
            ROCACHE["cache<br/>MD5 key · 30-day expiry"]
            ROUTIL["utils<br/>fuel cost · duration · Maps URL"]
            ROCLI["main / input_handler<br/><i>CLI path only</i>"]
        end

        subgraph DB ["database · persistence"]
            DBM["DatabaseManager<br/>pool 10+20 · pre-ping · recycle 1h<br/>get_session() context manager"]
            MODELS["ORM models<br/>User · Consent · Session<br/>AuditLog · FeedbackSurvey"]
        end
    end

    %% ---------- Relationships ----------
    USER -->|"messages"| WA
    USER -->|"messages"| TW
    USER -->|"pays"| ST
    WA -->|"webhook POST"| FLASK
    TW -->|"webhook POST"| FLASK
    ST -->|"checkout.session.completed<br/>invoice.paid · dispute.created"| FLASK

    FLASK --> GRL
    FLASK --> RL
    FLASK --> LD
    CLEAN -.->|"prunes hourly"| RL
    CLEAN -.->|"prunes hourly"| LD
    FLASK --> FACTORY
    FACTORY --> META
    FACTORY --> TWIL
    FLASK -->|"verify + parse"| META
    FLASK -->|"verify + parse"| TWIL
    FLASK -->|"process_message()"| MP
    FLASK -->|"send_reply()"| MS
    FLASK -->|"handle_webhook_event()"| SM

    MP --> AP
    MP --> CT
    MP --> CM
    MP --> UM
    MP --> FM
    MP --> SM
    MP --> RB
    MP --> TPL
    MP --> CFG
    MP -->|"Twilio: sends part 1 itself"| MS
    FM -->|"Q1 after 5s, background thread"| MS
    SM -->|"payment confirmations"| MS
    CM -->|"assign_default_tier()"| UM
    CT -->|"assign_default_tier()"| UM
    UM -->|"upsell links"| SM

    MS --> META
    MS --> TWIL
    META -->|"HTTPS"| WA
    TWIL -->|"HTTPS"| TW

    RB --> ROAPI
    RB --> ROUTIL
    ROAPI --> ROCACHE
    ROAPI -->|"HTTPS GET ×2"| GM
    ROCACHE <-->|"read/write JSON"| FSCACHE
    ROCLI --> ROAPI

    CM --> DBM
    CT --> DBM
    UM --> DBM
    FM --> DBM
    SM --> DBM
    MP --> DBM
    DBM --> MODELS
    DBM <-->|"SQLAlchemy / psycopg2"| PG
    SM <-->|"REST"| ST
    LOG --> LOGS

    classDef person fill:#0b4f6c,stroke:#083b52,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff
    classDef store fill:#4b5563,stroke:#374151,color:#fff
    class USER person
    class WA,TW,GM,ST ext
    class PG,FSCACHE,LOGS store
```

**Notes**

- `route_optimizer/` has **no** dependency on `wab/` — the bridge is the only seam. The CLI (`run_optimizer.py`) uses the same core.
- Rate-limiter state is **per process and in memory**: it resets on deploy and would not be shared if the worker count ever rose above 1.
- The legacy JSON implementations (`wab/app/consent_manager.py`, `wab/utils/conversation_tracker.py`, `wab/utils/encryption.py`) are **not wired into the running app** — only their `_db` counterparts are. They remain reachable from `wab/scripts/` migration tools.

---

## 3. Sequence diagram — first route request (implied consent, Twilio)

The heaviest path in the system: new user, no DB row, sends addresses, gets a two-part reply.

```mermaid
sequenceDiagram
    autonumber
    actor U as Driver
    participant TW as Twilio
    participant F as webhook_server<br/>(Flask)
    participant A as TwilioAdapter
    participant L as Rate limiters
    participant T as ConversationTracker
    participant P as MessageProcessor
    participant FM as FeedbackManager
    participant AP as AddressParser
    participant C as ConsentManager
    participant UM as usage_manager
    participant RB as RouteOptimizerBridge
    participant GM as Google Maps API
    participant DB as PostgreSQL
    participant S as MessageSender

    U->>TW: "Calle Mayor 1, Madrid⏎Gran Vía 50, Madrid⏎…"
    TW->>F: POST /webhook (form-encoded, X-Twilio-Signature)

    F->>L: global check_limit() — 500/h
    L-->>F: allowed
    F->>A: verify_post_signature(request)
    A-->>F: true (HMAC-SHA1 over ProxyFix URL)
    F->>A: parse_incoming(request)
    A-->>F: [(message, value)] — phone or BSUID identifier
    F-)F: spawn daemon thread
    F-->>TW: 200 OK

    Note over F,S: everything below runs in the background thread

    F->>L: user check_limit(from) — 10/min
    L-->>F: allowed
    F->>L: check_loop(from, text) — 3 in 5 min
    L-->>F: not a loop
    F->>P: process_message(message, value)

    P->>T: update_conversation(from, bsuid)
    T->>DB: SELECT user by phone/bsuid
    DB-->>T: none
    T->>DB: INSERT users + assign_default_tier() (btester|free)
    T->>DB: INSERT sessions (24h) + audit 'session_started'
    T->>DB: INSERT audit 'tier_assigned'

    P->>FM: handle_incoming(from, text) — survey intercept
    FM->>DB: SELECT active feedback_surveys
    DB-->>FM: none
    FM-->>P: None (not a survey answer)

    Note over P: no command word matched
    P->>AP: parse_addresses(text)
    AP-->>P: (["Calle Mayor 1…", "Gran Vía 50…"], None)

    P->>C: has_consent(from)
    C->>DB: SELECT latest consent
    DB-->>C: none
    C-->>P: false
    P->>C: save_consent(implied:first_address_list)
    C->>DB: INSERT consents + audit 'consent_given'
    C-->>P: true → privacy footnote flag

    P->>UM: check_route_allowed(from)
    UM->>DB: SELECT user, reset daily counter if new UTC day
    Note right of UM: tier expiry · lifetime cap ·<br/>daily cap · PPU credits
    UM-->>P: (true, "")

    P->>RB: optimize_route(addresses)
    RB->>GM: GET /directions (input order)
    GM-->>RB: legs → distance_m, duration_s
    RB->>GM: GET /directions (optimize:true)
    GM-->>RB: legs + waypoint_order
    Note right of RB: both responses cached<br/>to .cache/ for 30 days
    RB-->>P: {success, original_route, optimized_route}

    P->>UM: record_route_used(from)
    UM->>DB: UPDATE counters, debit PPU credit if applicable
    UM->>DB: INSERT audit 'route_requested'

    P->>FM: trigger_survey_after_route(from)
    alt routes_used_lifetime == 3 and no prior survey
        FM->>DB: INSERT feedback_surveys (status='sent')
        FM-)S: background thread, sleep 5s, send Q1
    else otherwise
        FM-->>P: false
    end

    P->>RB: format_route_result_parts(result)
    RB-->>P: (summary ≤1550 chars, maps_url)
    Note right of P: fallback to original route<br/>if "optimized" is longer
    P->>S: send_reply(summary + privacy footnote)
    S->>A: send()
    A->>TW: messages.create()
    TW-->>U: ✅ Ruta calculada! · stops · savings · 🔒 footnote
    P-->>F: response(maps_url)
    F->>S: send_reply(maps_url)
    S->>A: send()
    A->>TW: messages.create()
    TW-->>U: 📍 Google Maps link
    opt 3rd route
        TW-->>U: NPS survey Q1 (≈5s later)
    end
```

### 3b. Sequence — Stripe payment and tier activation

```mermaid
sequenceDiagram
    autonumber
    actor U as Driver
    participant TW as WhatsApp provider
    participant F as webhook_server
    participant P as MessageProcessor
    participant SM as StripeManager
    participant ST as Stripe
    participant DB as PostgreSQL
    participant S as MessageSender

    U->>TW: "premium"
    TW->>F: POST /webhook
    F->>P: process_message()
    P->>DB: SELECT user (tier, subscription, expiry)
    alt already on this tier with active subscription
        P-->>S: "Ya tienes el plan activo hasta dd/mm/yyyy"
    else needs checkout
        P->>SM: get_checkout_link_message(user, 'premium')
        SM->>DB: SELECT / UPDATE stripe_customer_id
        SM->>ST: Customer.create (if new) + checkout.Session.create<br/>mode=subscription · locale=es · automatic_tax
        ST-->>SM: session.url
        SM->>DB: UPDATE pending_tier, checkout_created_at
        SM-->>P: formatted link + IVA/pro-rata disclaimer
        P-->>S: checkout link
    end
    S-->>U: Stripe Checkout URL

    U->>ST: completes payment
    ST-->>U: redirect → GET /payment/success (static HTML page)
    ST->>F: POST /internal/stripe/webhook (Stripe-Signature, raw body)
    F->>SM: handle_webhook_event(payload, sig)
    SM->>ST: Webhook.construct_event() — verify signature

    alt checkout.session.completed
        SM->>DB: find user by client_reference_id
        alt tier == 'ppu'
            Note right of SM: idempotency — skip if audit row<br/>already has this stripe_session_id
            SM->>DB: +1 ppu_credit (top-up keeps an active plan intact)
        else premium / plus
            SM->>ST: cancel previous subscription if switching
            SM->>DB: activate tier, +30 days, reset routes_used_today
        end
        SM->>DB: INSERT audit 'payment_completed'
        SM->>S: payment confirmation message
    else invoice.paid
        SM->>ST: Subscription.retrieve → current_period_end
        SM->>DB: extend tier_expires_at + audit 'tier_upgraded'
    else invoice.payment_failed
        SM->>DB: audit 'payment_initiated' (reason=payment_failed)
        SM->>S: "No hemos podido cobrar tu suscripción"
    else customer.subscription.deleted
        SM->>DB: downgrade to 'ppu', clear subscription fields<br/>audit 'subscription_cancelled'
        SM->>S: "Tu suscripción ha sido cancelada"
    else charge.dispute.created
        SM->>ST: Charge.retrieve → customer
        SM->>DB: tier → 'free', clear Stripe fields, audit 'access_suspended'
        SM->>S: "Tu acceso ha sido suspendido"
    end
    F-->>ST: 200 {"status":"ok"}
    S-->>U: WhatsApp confirmation
```

---

## Data lifecycle (GDPR), for reference

| Table | Retention | Cleanup |
|---|---|---|
| `users` | soft-deleted / anonymized on Art. 17 request | `User.anonymize()` — 14-digit placeholder, PII and Stripe fields cleared |
| `consents` | 3 years (Art. 7 burden of proof) | `cleanup_expired_data()` PG function |
| `sessions` | 24h window, deleted at 48h | `cleanup_expired_data()` PG function |
| `audit_logs` | 90 days, `user_id` set NULL on delete | `cleanup_expired_data()` PG function |
| addresses | never persisted — in memory for the request only | n/a |
| `.cache/*.json` | 30 days, contains address strings | expiry check on read |

> `cleanup_expired_data()` is exposed through `DatabaseManager.execute_cleanup()` but is **not** scheduled from inside the app — it needs an external cron/Railway job.

---

## Deployment topology

| | |
|---|---|
| Production | Railway · NIXPACKS · `gunicorn wab.app.webhook_server:app --workers 1 --timeout 120` |
| Local dev | `python wab/run_webhook.py` + `ngrok http 5000` |
| CLI | `python run_optimizer.py ["addr" …]` — reads `input.txt`, bypasses the whole `wab/` stack |
| Runtime | Python 3.11.7 · Flask 3.0 · SQLAlchemy 2.0 · stripe 11.4 · twilio 9.10 |
| Provider switch | `MESSAGING_PROVIDER=meta\|twilio` — no code change |
