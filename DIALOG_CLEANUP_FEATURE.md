# Dialog Cleanup Feature

## Overview
Implemented functionality to clear the entire dialog (chat history) when users run the `/stop` command, leaving only the final unsubscribe message.

## Features
- **Complete Dialog Cleanup**: All bot messages are deleted when user runs `/stop`
- **Last Message Preservation**: The final unsubscribe message remains visible
- **Automatic Message Tracking**: Bot automatically tracks all sent messages for cleanup
- **Language Support**: Works for both Russian and English versions

## Implementation Details

### Files Modified
1. **`bot/storage.py`**:
   - Added `BotMessage` dataclass for storing message metadata
   - Added methods: `add_bot_message()`, `get_user_bot_messages()`, `clear_user_bot_messages()`
   - Automatic cleanup keeps only last 50 messages per user

2. **`bot/handlers.py`**:
   - Modified `_handle_stop()` to clear dialog before sending final message
   - Added `_clear_user_dialog()` method for message deletion
   - Added helper methods: `_send_and_store_message()`, `_reply_and_store_message()`
   - Enhanced message tracking for key user interactions

3. **`bot/scheduler.py`**:
   - Updated `_send_message_with_retry()` to store message IDs
   - Automatic tracking of daily principle messages and images

## Usage
When a user runs `/stop` command:
1. User's `/stop` command message is deleted
2. All previously stored bot messages are deleted
3. Bot message storage for user is cleared
4. User is unsubscribed from the service
5. Final unsubscribe message is sent (not stored for deletion)

## Example Flow
```
User: /start
Bot: 🕊️ Welcome to Yoga Principles Bot! [STORED]
Bot: Please choose your language [STORED] 
User: Selects Russian
Bot: ✅ Language set! [STORED]
Bot: Step 1/3: Timezone [STORED]
...setup continues...
Bot: 🎉 Setup Complete! [STORED]
Bot: Daily principle message [STORED]
Bot: Another principle message [STORED]

User: /stop
[All stored bot messages deleted]
Bot: 😔 Вы отписались от рассылки принципов йоги. [NOT STORED - remains visible]
```

## Technical Notes
- Messages older than 48 hours cannot be deleted (Telegram API limitation)
- Bot can only delete its own messages in private chats
- Error handling ensures graceful degradation if deletion fails
- Storage automatically limits to 50 messages per user to prevent file growth
- Message types are tracked: "welcome", "principle", "menu", "setup_complete", etc.

## Benefits
- **Clean User Experience**: Users see only the final message after unsubscribing
- **Privacy**: Previous interactions are cleaned up
- **Storage Efficiency**: Old message IDs are automatically cleaned up
- **Reliable**: Works even if some messages fail to delete 