@bot.message_handler(func=lambda message: message.content_type == 'text' and not message.text.startswith('/'))
def handle_first_message(message):
    """Handle any text message as first interaction"""
    try:
        user_id = message.from_user.id
        lang = get_user_lang(message.from_user.language_code)
        
        # Send first welcome message with Start button
        send_first_welcome(message.chat.id, lang)
        
        # Start inactivity timer
        start_inactivity_timer(user_id, message.chat.id, lang)
        
    except Exception as e:
        logger.error(f"Error in handle_first_message: {str(e)}")