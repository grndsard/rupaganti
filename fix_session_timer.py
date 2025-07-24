def start_session_timer(chat_id, file_path, db_id, lang='en'):
    """Start countdown timer for session"""
    try:
        # Create countdown message with initial format (2:00)
        minutes = SESSION_TIMEOUT_SECONDS // 60
        seconds = SESSION_TIMEOUT_SECONDS % 60
        countdown_msg = bot.send_message(chat_id, LANG[lang]['countdown'].format(minutes, seconds))
        
        # Store session info
        active_sessions[chat_id] = {
            'file_path': file_path,
            'db_id': db_id,
            'countdown_msg_id': countdown_msg.message_id,
            'lang': lang,
            'start_time': time.time(),
            'timer': None
        }
        
        # Function to update countdown and check expiration
        def check_session():
            try:
                if chat_id not in active_sessions:
                    return
                
                elapsed = time.time() - active_sessions[chat_id]['start_time']
                remaining = max(0, SESSION_TIMEOUT_SECONDS - int(elapsed))
                
                # Always update the countdown for smooth animation
                
                if remaining <= 0:
                    # Session expired
                    session_info = active_sessions.pop(chat_id, None)
                    if session_info:
                        session_expired(chat_id, session_info['file_path'], session_info['db_id'], session_info['lang'])
                else:
                    # Update countdown and schedule next check - update every second for animation
                    update_countdown(chat_id, active_sessions[chat_id]['countdown_msg_id'], remaining, lang)
                    timer = threading.Timer(1.0, check_session)
                    timer.daemon = True
                    timer.start()
                    active_sessions[chat_id]['timer'] = timer
            except Exception as e:
                logger.error(f"Error in check_session: {str(e)}")
        
        # Start the timer
        timer = threading.Timer(1.0, check_session)
        timer.daemon = True
        timer.start()
        active_sessions[chat_id]['timer'] = timer
        
    except Exception as e:
        logger.error(f"Error starting session timer: {str(e)}")