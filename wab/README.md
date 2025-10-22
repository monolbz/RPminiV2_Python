# WhatsApp Business Webhook Server

A Python-based webhook server for receiving and responding to WhatsApp Business messages. This server handles incoming messages from WhatsApp users and sends automated replies.

## Features

- **Webhook Verification**: Automatic verification of WhatsApp webhook requests
- **Message Reception**: Receives text, location, image, and document messages
- **Smart Reply System**: Automatically sends replies via WhatsApp Cloud API
- **24-Hour Window Tracking**: Tracks conversation windows to determine free-form vs template messaging
- **Security**: Webhook signature verification for secure communication
- **Template Support**: Handles pre-approved WhatsApp message templates
- **Logging**: Comprehensive logging for debugging and monitoring
- **Testing Tools**: Local testing scripts and sample payloads

## Architecture

```
wab/
├── app/                          # Core application
│   ├── webhook_server.py         # Flask server with webhook endpoints
│   ├── message_processor.py      # Processes incoming messages
│   └── message_sender.py         # Sends replies to WhatsApp
├── utils/                        # Utility modules
│   ├── logger.py                 # Logging configuration
│   ├── validators.py             # Webhook signature validation
│   ├── conversation_tracker.py   # 24h window tracking
│   └── template_manager.py       # Template management
├── config/                       # Configuration
│   ├── config.py                 # Configuration loader
│   └── templates.json            # WhatsApp templates
├── data/                         # Runtime data (gitignored)
│   └── sessions.json             # Active conversation sessions
├── examples/                     # Testing tools
│   ├── test_webhook.py           # Local testing script
│   └── sample_payload.json       # Sample WhatsApp payload
├── integration/                  # Future integration (Phase 2)
│   └── route_optimizer_bridge.py # Bridge to route planner
├── logs/                         # Log files (gitignored)
└── run_webhook.py                # Entry point script
```

## Prerequisites

1. **WhatsApp Business Account**
   - Meta Business Account
   - WhatsApp Business App in Meta Developer Portal
   - Phone number registered with WhatsApp Business API

2. **Python Environment**
   - Python 3.8 or higher
   - Virtual environment (recommended)

3. **Network Access**
   - Public URL for webhook (use ngrok for local testing)
   - HTTPS required by WhatsApp

## Setup Instructions

### 1. Get WhatsApp API Credentials

#### A. Create Meta App
1. Go to [Meta Developer Portal](https://developers.facebook.com/)
2. Create a new app (Business type)
3. Add "WhatsApp" product to your app

#### B. Get Required Credentials

**Verify Token** (you create this):
- Create a random string (e.g., "my_secure_token_12345")
- You'll use this when setting up the webhook in Meta portal

**Access Token**:
1. Go to App Dashboard > WhatsApp > API Setup
2. Copy the temporary access token (starts with "EAAG...")
3. For production, generate a permanent token

**Phone Number ID**:
1. Go to App Dashboard > WhatsApp > API Setup
2. Find "Phone number ID" (numerical ID like "123456789012345")

**Business Account ID**:
1. Go to App Dashboard > WhatsApp > Getting Started
2. Find "WhatsApp Business Account ID"

**App Secret**:
1. Go to App Dashboard > Settings > Basic
2. Click "Show" next to "App Secret"
3. Copy the secret (for webhook signature verification)

### 2. Configure Environment Variables

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your WhatsApp credentials:

```env
# WhatsApp Business API Configuration
WHATSAPP_VERIFY_TOKEN=my_secure_token_12345
WHATSAPP_ACCESS_TOKEN=EAAG...your_access_token
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321098765
WHATSAPP_APP_SECRET=your_app_secret_here

# Server Configuration
WEBHOOK_PORT=5000
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### 3. Install Dependencies

Make sure your virtual environment is activated:

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

### 4. Set Up Webhook URL

#### For Local Testing (using ngrok):

1. **Install ngrok**: Download from [ngrok.com](https://ngrok.com/)

2. **Start the webhook server**:
   ```bash
   python wab/run_webhook.py
   ```

3. **In a new terminal, start ngrok**:
   ```bash
   ngrok http 5000
   ```

4. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

#### Configure Webhook in Meta Portal:

1. Go to App Dashboard > WhatsApp > Configuration
2. Click "Edit" next to "Webhook"
3. Enter your webhook URL: `https://abc123.ngrok.io/webhook`
4. Enter your verify token (from `.env`)
5. Click "Verify and Save"
6. Subscribe to webhook fields:
   - ✅ messages
   - ✅ message_status (optional)

### 5. Test the Webhook

#### Option A: Send a Test Message from WhatsApp

1. Send a message to your WhatsApp Business number
2. Check the webhook server logs for incoming message
3. You should receive an automated reply

#### Option B: Use Local Test Script

```bash
# Test the webhook server locally
python wab/examples/test_webhook.py
```

This will test:
- Webhook verification endpoint
- Message receiving endpoint
- Health check endpoint

## Usage

### Starting the Server

**Basic usage:**
```bash
python wab/run_webhook.py
```

**Custom port:**
```bash
python wab/run_webhook.py --port 8000
```

**Debug mode:**
```bash
python wab/run_webhook.py --debug
```

**Custom host:**
```bash
python wab/run_webhook.py --host 0.0.0.0 --port 5000
```

### Webhook Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | GET | Webhook verification (Meta calls this) |
| `/webhook` | POST | Receive messages from WhatsApp |
| `/health` | GET | Health check endpoint |
| `/` | GET | Server information |

### Example Interaction

**User sends:**
```
Hello!
```

**Bot replies:**
```
Hello Test User! 👋

I'm your Route Optimizer assistant. I can help you plan efficient delivery routes in Madrid.

To get started, send me your addresses and I'll optimize your route!
```

## WhatsApp Messaging Rules

### 24-Hour Conversation Window

WhatsApp has strict messaging policies:

**Within 24 hours** (User messages you first):
- ✅ Send free-form text messages
- ✅ No template required
- ✅ Cost: FREE (first 1,000/month) then ~€0.0164/conversation

**Outside 24 hours** (No recent user message):
- ❌ Cannot send free-form messages
- ✅ Must use pre-approved templates only
- ✅ Cost: ~€0.0164/conversation (no free tier)

### Message Templates

Templates must be created and approved in Meta Business Manager before use.

**Current templates** (see [templates.json](config/templates.json)):
- `hello_world` - Default greeting (pre-approved by WhatsApp)
- `route_notification` - For route ready notifications (needs approval)
- `route_error` - For error notifications (needs approval)

**To create new templates**:
1. Go to Meta Business Manager
2. Navigate to WhatsApp Manager > Message Templates
3. Click "Create Template"
4. Design your template with placeholders
5. Submit for approval (takes 1-3 days)
6. Add to `wab/config/templates.json`

## Message Types Supported

| Type | Status | Description |
|------|--------|-------------|
| Text | ✅ Supported | Text messages with auto-replies |
| Location | ✅ Supported | Location coordinates (placeholder) |
| Image | ✅ Supported | Images (placeholder) |
| Document | ✅ Supported | Documents (placeholder) |
| Audio | ⏳ Planned | Audio messages |
| Video | ⏳ Planned | Video messages |

## Conversation Tracking

The server tracks active conversations to determine messaging strategy:

**Session Storage**: [wab/data/sessions.json](data/sessions.json)
- Stores last message timestamp per phone number
- Automatically cleaned up after 48 hours
- Determines if free-form or template required

**Tracking Logic**:
```python
# User messages you → 24h window starts
# You can reply freely for 24 hours
# After 24h → must use templates
# User messages again → window resets
```

## Security

### Webhook Signature Verification

All incoming webhooks are verified using HMAC-SHA256:

```python
# Automatically verified in webhook_server.py
signature = request.headers.get('X-Hub-Signature-256')
verify_webhook_signature(payload, signature, app_secret)
```

**Important**: Set `WHATSAPP_APP_SECRET` in `.env` for production!

### Best Practices

1. ✅ Keep `.env` file secret (never commit)
2. ✅ Use HTTPS for webhook URL (required by WhatsApp)
3. ✅ Enable signature verification in production
4. ✅ Rotate access tokens periodically
5. ✅ Monitor logs for suspicious activity

## Logging

Logs are stored in `wab/logs/` directory:

**Log Files**: `webhook_YYYYMMDD.log`
- Daily log rotation
- Detailed logging with timestamps
- Includes request/response data

**Log Levels**:
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical failures

**Change log level** in `.env`:
```env
LOG_LEVEL=DEBUG  # For development
LOG_LEVEL=INFO   # For production
```

## Troubleshooting

### Webhook Verification Failed

**Problem**: Meta portal shows "Verification failed"

**Solutions**:
1. Check `WHATSAPP_VERIFY_TOKEN` in `.env` matches portal
2. Ensure server is running and accessible
3. Check webhook URL is correct (include `/webhook`)
4. Verify HTTPS is working (ngrok provides HTTPS)

### Messages Not Received

**Problem**: Sending messages to WhatsApp number but webhook not triggered

**Solutions**:
1. Check webhook subscriptions in Meta portal (messages field)
2. Verify webhook URL is still valid (ngrok URLs expire)
3. Check server logs for errors
4. Test health endpoint: `curl http://localhost:5000/health`

### Cannot Send Messages

**Problem**: Receiving messages but cannot send replies

**Solutions**:
1. Verify `WHATSAPP_ACCESS_TOKEN` is valid
2. Check `WHATSAPP_PHONE_NUMBER_ID` is correct
3. Ensure within 24-hour window OR using templates
4. Check API rate limits (not exceeded)
5. Review error messages in logs

### Invalid Signature Error

**Problem**: "Invalid webhook signature" in logs

**Solutions**:
1. Set correct `WHATSAPP_APP_SECRET` in `.env`
2. Get app secret from Meta portal: Settings > Basic
3. For testing, temporarily disable verification (not recommended)

## Testing

### Local Testing (Without WhatsApp)

Run the test script to verify webhook functionality:

```bash
python wab/examples/test_webhook.py
```

This tests:
- ✅ Health check endpoint
- ✅ Webhook verification
- ✅ Message processing

### Testing with WhatsApp

1. **Add test number**: In Meta portal, add test phone numbers
2. **Send message**: Send a message from test WhatsApp to your business number
3. **Check logs**: Monitor `wab/logs/` for incoming webhook
4. **Verify reply**: Check if automated reply is received

### ngrok Tips

**Persistent URLs** (paid ngrok):
```bash
ngrok http 5000 --domain=your-static-domain.ngrok.io
```

**Monitor requests**:
- Open ngrok web interface: `http://localhost:4040`
- View all webhook requests in real-time

## Integration with Route Optimizer (Phase 2)

Currently in Phase 1: Core webhook functionality only.

**Phase 2 will add**:
- Parse addresses from WhatsApp messages
- Call route optimizer automatically
- Send optimized route back to user
- Share Google Maps links via WhatsApp

Integration bridge: [wab/integration/route_optimizer_bridge.py](integration/route_optimizer_bridge.py)

## Cost Estimation

Based on WhatsApp pricing (Spain):

| Usage | Monthly Conversations | Cost |
|-------|----------------------|------|
| Development | 0-100 | **€0.00** (free tier) |
| Small business | 1,000 | **€0.00** (free tier) |
| Medium business | 5,000 | **€65.60** (4,000 paid) |
| Large business | 10,000 | **€147.60** (9,000 paid) |

**Cost optimization**:
- Encourage users to initiate conversations
- Keep conversations within 24h window
- Use templates only when necessary

## Development

### Project Structure

```python
# Main webhook server
wab/app/webhook_server.py       # Flask routes and endpoints

# Message handling
wab/app/message_processor.py    # Process incoming messages
wab/app/message_sender.py       # Send replies to WhatsApp

# Utilities
wab/utils/logger.py              # Logging setup
wab/utils/validators.py          # Validation functions
wab/utils/conversation_tracker.py # Session tracking
wab/utils/template_manager.py   # Template handling

# Configuration
wab/config/config.py             # Config loader
wab/config/templates.json        # Template definitions
```

### Adding New Message Handlers

Edit [message_processor.py](app/message_processor.py):

```python
def _process_text_message(self, message, from_number, phone_number_id, display_name):
    message_body = message.get('text', {}).get('body', '').strip()

    # Add your custom logic
    if 'keyword' in message_body.lower():
        reply_text = "Your custom response"
        return self._create_response(from_number, phone_number_id, reply_text)
```

### Adding New Templates

1. Create template in Meta Business Manager
2. Wait for approval
3. Add to `wab/config/templates.json`:

```json
{
  "your_template": {
    "name": "your_template",
    "language": "en",
    "variables_count": 2,
    "description": "Your template description"
  }
}
```

## Support & Resources

- **WhatsApp Business API Docs**: https://developers.facebook.com/docs/whatsapp
- **Meta Developer Portal**: https://developers.facebook.com/
- **Flask Documentation**: https://flask.palletsprojects.com/
- **ngrok Documentation**: https://ngrok.com/docs

## License

This project is part of the Madrid Route Optimizer and uses the same MIT License.

## Author

Created by [@monolbz](https://github.com/monolbz)

## Next Steps

1. ✅ Complete Phase 1: Core webhook functionality (DONE)
2. ⏳ Phase 2: Integrate with route optimizer
3. ⏳ Add more message types (audio, video)
4. ⏳ Create additional message templates
5. ⏳ Add database for conversation history
6. ⏳ Implement user preferences
7. ⏳ Add multi-language support
