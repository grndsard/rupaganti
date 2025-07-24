def send_first_welcome(chat_id, lang='en'):
    """Send the first welcome message with Start button"""
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(LANG[lang]['start_button'], callback_data="start_bot"))
        bot.send_message(chat_id, LANG[lang]['first_welcome'], reply_markup=markup)
    except Exception as e:
        logger.error(f"Error sending first welcome: {str(e)}")

def start_inactivity_timer(user_id, chat_id, lang='en'):
    """Start inactivity timer for a user"""
    # Update user's last activity time
    user_activity[user_id] = {
        'timestamp': time.time(),
        'chat_id': chat_id,
        'lang': lang,
        'reminder_sent': False,
        'timer': None
    }
    
    # Function to check inactivity
    def check_inactivity():
        if user_id not in user_activity:
            return
            
        current_time = time.time()
        last_activity = user_activity[user_id]['timestamp']
        elapsed = current_time - last_activity
        
        # If 2 minutes passed without activity and reminder not sent yet
        if elapsed > 120 and not user_activity[user_id]['reminder_sent']:
            # Send reminder
            try:
                bot.send_message(chat_id, LANG[lang]['inactivity_reminder'])
                user_activity[user_id]['reminder_sent'] = True
                
                # Schedule final check after 1 more minute
                timer = threading.Timer(60.0, check_inactivity)
                timer.daemon = True
                timer.start()
                user_activity[user_id]['timer'] = timer
            except:
                pass
        # If 3 minutes total passed (reminder sent 1 minute ago)
        elif elapsed > 180 and user_activity[user_id]['reminder_sent']:
            # Send session closed message
            try:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(LANG[lang]['start_button'], callback_data="start_bot"))
                bot.send_message(chat_id, LANG[lang]['inactivity_close'], reply_markup=markup)
                
                # Clean up user activity
                user_activity.pop(user_id, None)
            except:
                pass
        else:
            # Schedule next check
            timer = threading.Timer(30.0, check_inactivity)  # Check every 30 seconds
            timer.daemon = True
            timer.start()
            user_activity[user_id]['timer'] = timer
    
    # Start the inactivity timer
    timer = threading.Timer(30.0, check_inactivity)  # First check after 30 seconds
    timer.daemon = True
    timer.start()
    user_activity[user_id]['timer'] = timer

def update_user_activity(user_id):
    """Update user's last activity timestamp"""
    if user_id in user_activity:
        user_activity[user_id]['timestamp'] = time.time()
        user_activity[user_id]['reminder_sent'] = False