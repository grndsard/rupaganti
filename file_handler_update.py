@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_file(message):
    try:
        # Cancel any existing session for this user
        user_id = message.from_user.id
        if user_id in active_sessions:
            try:
                active_sessions[user_id]['timer'].cancel()
            except:
                pass
            active_sessions.pop(user_id, None)
            
        # Update user activity
        update_user_activity(user_id)