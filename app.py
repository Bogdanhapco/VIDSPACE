"""
VIDSPACE - FULL TIKTOK CLONE
================================

SETUP INSTRUCTIONS:
1. Create MongoDB Atlas account (free): mongodb.com/atlas
2. Create Cloudinary account (free): cloudinary.com
3. Add to Streamlit secrets (.streamlit/secrets.toml):

[mongodb]
connection_string = "your_mongodb_connection_string"

[cloudinary]
cloud_name = "your_cloud_name"
api_key = "your_api_key"
api_secret = "your_api_secret"

For local testing, create .streamlit/secrets.toml in your project folder.
For Streamlit Cloud, add in Settings > Secrets.
"""

import streamlit as st
import json
from datetime import datetime, timedelta
import hashlib
import time
import io

# Try to import cloud libraries (will use fallback if not available)
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except:
    MONGO_AVAILABLE = False
    st.warning("⚠️ pymongo not installed. Using local storage. Run: pip install pymongo")

try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
except:
    CLOUDINARY_AVAILABLE = False
    st.warning("⚠️ cloudinary not installed. Using base64. Run: pip install cloudinary")

# App CSS
APP_CSS = """
<style>
    .stApp {
        background: linear-gradient(to bottom, #000000, #0d0d0d, #1a1a1a);
    }
    
    * {
        color: #ffffff !important;
    }
    
    .video-card {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        border-radius: 20px;
        padding: 20px;
        margin: 15px 0;
        border: 2px solid #ff0050;
        box-shadow: 0 0 20px rgba(255, 0, 80, 0.3);
    }
    
    .notification-badge {
        background: #ff0050;
        color: white;
        border-radius: 50%;
        padding: 2px 8px;
        font-size: 0.8em;
        font-weight: bold;
    }
    
    .chat-message-sent {
        background: linear-gradient(135deg, #ff0050, #ff3366);
        border-radius: 15px;
        padding: 10px 15px;
        margin: 5px 0;
        max-width: 70%;
        margin-left: auto;
    }
    
    .chat-message-received {
        background: linear-gradient(135deg, #2d2d2d, #404040);
        border-radius: 15px;
        padding: 10px 15px;
        margin: 5px 0;
        max-width: 70%;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""

# Database wrapper
class Database:
    def __init__(self):
        self.use_cloud = False
        self.db = None
        
        # Try to connect to MongoDB
        if MONGO_AVAILABLE and 'mongodb' in st.secrets:
            try:
                client = MongoClient(st.secrets['mongodb']['connection_string'])
                self.db = client['vidspace']
                # Test connection
                client.server_info()
                self.use_cloud = True
                st.success("✅ Connected to MongoDB Cloud!")
            except Exception as e:
                st.warning(f"⚠️ MongoDB connection failed: {e}. Using local storage.")
        
        # Fallback to local JSON storage
        if not self.use_cloud:
            import os
            os.makedirs("data", exist_ok=True)
    
    def _local_load(self, collection):
        try:
            with open(f"data/{collection}.json", 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _local_save(self, collection, data):
        with open(f"data/{collection}.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_all(self, collection):
        if self.use_cloud:
            items = list(self.db[collection].find({}, {'_id': 0}))
            return {item.get('id', item.get('username', str(i))): item for i, item in enumerate(items)}
        return self._local_load(collection)
    
    def get_one(self, collection, key, value):
        if self.use_cloud:
            return self.db[collection].find_one({key: value}, {'_id': 0})
        data = self._local_load(collection)
        for item in data.values():
            if item.get(key) == value:
                return item
        return None
    
    def insert(self, collection, doc):
        if self.use_cloud:
            self.db[collection].insert_one(doc)
        else:
            data = self._local_load(collection)
            key = doc.get('id', doc.get('username'))
            data[key] = doc
            self._local_save(collection, data)
    
    def update(self, collection, key, value, update_data):
        if self.use_cloud:
            self.db[collection].update_one({key: value}, {'$set': update_data})
        else:
            data = self._local_load(collection)
            for k, item in data.items():
                if item.get(key) == value:
                    data[k].update(update_data)
                    break
            self._local_save(collection, data)
    
    def delete(self, collection, key, value):
        if self.use_cloud:
            self.db[collection].delete_one({key: value})
        else:
            data = self._local_load(collection)
            data = {k: v for k, v in data.items() if v.get(key) != value}
            self._local_save(collection, data)

# Initialize DB
db = Database()

# Cloudinary setup
class MediaStorage:
    def __init__(self):
        self.use_cloud = False
        
        if CLOUDINARY_AVAILABLE and 'cloudinary' in st.secrets:
            try:
                cloudinary.config(
                    cloud_name=st.secrets['cloudinary']['cloud_name'],
                    api_key=st.secrets['cloudinary']['api_key'],
                    api_secret=st.secrets['cloudinary']['api_secret']
                )
                self.use_cloud = True
                st.success("✅ Connected to Cloudinary!")
            except Exception as e:
                st.warning(f"⚠️ Cloudinary setup failed: {e}")
    
    def upload_video(self, video_file, video_id):
        if self.use_cloud:
            try:
                result = cloudinary.uploader.upload(
                    video_file,
                    resource_type="video",
                    public_id=video_id,
                    folder="vidspace_videos"
                )
                return result['secure_url']
            except Exception as e:
                st.error(f"Upload failed: {e}")
                return None
        else:
            # Fallback: base64 encoding (local storage)
            import base64
            video_bytes = video_file.read()
            return base64.b64encode(video_bytes).decode()
    
    def upload_image(self, image_file, image_id):
        if self.use_cloud:
            try:
                result = cloudinary.uploader.upload(
                    image_file,
                    public_id=image_id,
                    folder="vidspace_images"
                )
                return result['secure_url']
            except Exception as e:
                st.error(f"Upload failed: {e}")
                return None
        else:
            import base64
            image_bytes = image_file.read()
            return base64.b64encode(image_bytes).decode()
    
    def get_video_player(self, video_data):
        if self.use_cloud and video_data.startswith('http'):
            return st.video(video_data)
        else:
            # Base64 video
            import base64
            try:
                video_bytes = base64.b64decode(video_data)
                return st.video(video_bytes)
            except:
                return st.error("Error loading video")
    
    def get_image(self, image_data):
        if self.use_cloud and image_data and image_data.startswith('http'):
            return st.image(image_data)
        elif image_data:
            import base64
            try:
                image_bytes = base64.b64decode(image_data)
                return st.image(image_bytes)
            except:
                return st.error("Error loading image")

media = MediaStorage()

# Helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_id(prefix):
    return f"{prefix}_{int(datetime.now().timestamp())}_{hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:8]}"

def time_ago(timestamp_str):
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        diff = now - timestamp
        
        if diff.seconds < 60:
            return "just now"
        elif diff.seconds < 3600:
            return f"{diff.seconds // 60}m ago"
        elif diff.seconds < 86400:
            return f"{diff.seconds // 3600}h ago"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return timestamp.strftime("%b %d")
    except:
        return "recently"

# Account management
def create_account(username, password):
    if db.get_one('accounts', 'username', username):
        return False, "Username already exists"
    
    account = {
        'username': username,
        'password': hash_password(password),
        'created': datetime.now().isoformat(),
        'bio': "",
        'profile_pic': None,
        'followers': [],
        'following': [],
        'notifications': []
    }
    
    db.insert('accounts', account)
    return True, "Account created!"

def login(username, password):
    account = db.get_one('accounts', 'username', username)
    if not account:
        return False, "Username not found"
    if account['password'] != hash_password(password):
        return False, "Incorrect password"
    return True, "Login successful!"

def add_notification(username, notification_text, link_type=None, link_id=None):
    """Add notification to user"""
    account = db.get_one('accounts', 'username', username)
    if account:
        notifications = account.get('notifications', [])
        notifications.append({
            'text': notification_text,
            'timestamp': datetime.now().isoformat(),
            'read': False,
            'link_type': link_type,
            'link_id': link_id
        })
        # Keep last 50 notifications
        notifications = notifications[-50:]
        db.update('accounts', 'username', username, {'notifications': notifications})

def get_unread_notifications_count(username):
    account = db.get_one('accounts', 'username', username)
    if account:
        return sum(1 for n in account.get('notifications', []) if not n.get('read', False))
    return 0

def mark_notifications_read(username):
    account = db.get_one('accounts', 'username', username)
    if account:
        notifications = account.get('notifications', [])
        for n in notifications:
            n['read'] = True
        db.update('accounts', 'username', username, {'notifications': notifications})

# Video management
def upload_video(username, video_file, caption, hashtags):
    video_id = create_id("vid")
    
    # Upload to cloud or encode as base64
    video_data = media.upload_video(video_file, video_id)
    
    if not video_data:
        return None
    
    video = {
        'id': video_id,
        'username': username,
        'caption': caption,
        'hashtags': hashtags,
        'video_data': video_data,
        'timestamp': datetime.now().isoformat(),
        'likes': 0,
        'views': 0,
        'comments': []
    }
    
    db.insert('videos', video)
    
    # Notify followers
    account = db.get_one('accounts', 'username', username)
    if account:
        for follower in account.get('followers', []):
            add_notification(follower, f"@{username} posted a new video!", 'video', video_id)
    
    return video_id

def get_feed_videos(username):
    videos = db.get_all('videos')
    video_list = list(videos.values())
    
    # Get following list
    account = db.get_one('accounts', 'username', username)
    following = account.get('following', []) if account else []
    
    # Following videos first
    following_vids = [v for v in video_list if v['username'] in following]
    
    # Then trending
    trending_vids = sorted(video_list, key=lambda x: x.get('likes', 0), reverse=True)
    
    # Combine
    feed = following_vids + [v for v in trending_vids if v not in following_vids]
    return feed

def toggle_like(username, video_id):
    # Get user's interactions
    interactions = db.get_one('interactions', 'username', username)
    if not interactions:
        interactions = {'username': username, 'likes': [], 'saved': []}
        db.insert('interactions', interactions)
    
    likes = interactions.get('likes', [])
    video = db.get_one('videos', 'id', video_id)
    
    if video:
        if video_id in likes:
            likes.remove(video_id)
            video['likes'] = max(0, video.get('likes', 0) - 1)
        else:
            likes.append(video_id)
            video['likes'] = video.get('likes', 0) + 1
            # Notify video owner
            if video['username'] != username:
                add_notification(video['username'], f"@{username} liked your video!", 'video', video_id)
        
        db.update('interactions', 'username', username, {'likes': likes})
        db.update('videos', 'id', video_id, {'likes': video['likes']})

def add_comment(video_id, username, text):
    video = db.get_one('videos', 'id', video_id)
    if video:
        comments = video.get('comments', [])
        comments.append({
            'username': username,
            'text': text,
            'timestamp': datetime.now().isoformat()
        })
        db.update('videos', 'id', video_id, {'comments': comments})
        
        # Notify video owner
        if video['username'] != username:
            add_notification(video['username'], f"@{username} commented on your video!", 'video', video_id)

# Chat/DM management
def send_message(sender, recipient, message_text, video_id=None):
    chat_id = "_".join(sorted([sender, recipient]))
    
    message = {
        'id': create_id("msg"),
        'chat_id': chat_id,
        'sender': sender,
        'recipient': recipient,
        'text': message_text,
        'video_id': video_id,
        'timestamp': datetime.now().isoformat(),
        'read': False
    }
    
    db.insert('messages', message)
    
    # Notify recipient
    add_notification(recipient, f"@{sender} sent you a message", 'chat', sender)

def get_chat_messages(user1, user2):
    chat_id = "_".join(sorted([user1, user2]))
    all_messages = db.get_all('messages')
    
    chat_messages = [m for m in all_messages.values() if m.get('chat_id') == chat_id]
    chat_messages.sort(key=lambda x: x['timestamp'])
    return chat_messages

def get_user_chats(username):
    """Get list of users you've chatted with"""
    all_messages = db.get_all('messages')
    
    chat_users = set()
    for msg in all_messages.values():
        if msg.get('sender') == username:
            chat_users.add(msg.get('recipient'))
        elif msg.get('recipient') == username:
            chat_users.add(msg.get('sender'))
    
    return list(chat_users)

def get_unread_messages_count(username):
    all_messages = db.get_all('messages')
    return sum(1 for m in all_messages.values() 
               if m.get('recipient') == username and not m.get('read', False))

# Follow/unfollow
def follow_user(follower, following):
    follower_acc = db.get_one('accounts', 'username', follower)
    following_acc = db.get_one('accounts', 'username', following)
    
    if follower_acc and following_acc:
        following_list = follower_acc.get('following', [])
        followers_list = following_acc.get('followers', [])
        
        if following not in following_list:
            following_list.append(following)
            followers_list.append(follower)
            
            db.update('accounts', 'username', follower, {'following': following_list})
            db.update('accounts', 'username', following, {'followers': followers_list})
            
            # Notify
            add_notification(following, f"@{follower} started following you!", 'profile', follower)

def unfollow_user(follower, following):
    follower_acc = db.get_one('accounts', 'username', follower)
    following_acc = db.get_one('accounts', 'username', following)
    
    if follower_acc and following_acc:
        following_list = follower_acc.get('following', [])
        followers_list = following_acc.get('followers', [])
        
        if following in following_list:
            following_list.remove(following)
            followers_list.remove(follower)
            
            db.update('accounts', 'username', follower, {'following': following_list})
            db.update('accounts', 'username', following, {'followers': followers_list})

# Main app
def main():
    st.set_page_config(page_title="🎬 VidSpace", page_icon="🎬", layout="wide")
    st.markdown(APP_CSS, unsafe_allow_html=True)
    
    # Session state
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'page' not in st.session_state:
        st.session_state.page = "feed"
    
    # Login screen
    if not st.session_state.username:
        show_login_page()
        return
    
    # Get notification count
    notif_count = get_unread_notifications_count(st.session_state.username)
    msg_count = get_unread_messages_count(st.session_state.username)
    
    # Header
    st.markdown("""
        <h1 style='text-align: center; color: #ff0050; font-size: 3.5em; margin-bottom: 0;'>
            🎬 VidSpace
        </h1>
    """, unsafe_allow_html=True)
    
    # Navigation
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if st.button("🏠 Feed", use_container_width=True):
            st.session_state.page = "feed"
            st.rerun()
    
    with col2:
        notif_badge = f" ({notif_count})" if notif_count > 0 else ""
        if st.button(f"🔔 Notifications{notif_badge}", use_container_width=True):
            st.session_state.page = "notifications"
            st.rerun()
    
    with col3:
        msg_badge = f" ({msg_count})" if msg_count > 0 else ""
        if st.button(f"💬 Messages{msg_badge}", use_container_width=True):
            st.session_state.page = "messages"
            st.rerun()
    
    with col4:
        if st.button("➕ Upload", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()
    
    with col5:
        if st.button("👤 Profile", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()
    
    with col6:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.username = None
            st.rerun()
    
    st.divider()
    
    # Pages
    if st.session_state.page == "feed":
        show_feed_page()
    elif st.session_state.page == "notifications":
        show_notifications_page()
    elif st.session_state.page == "messages":
        show_messages_page()
    elif st.session_state.page == "upload":
        show_upload_page()
    elif st.session_state.page == "profile":
        show_profile_page()

def show_login_page():
    st.markdown("""
        <h1 style='text-align: center; color: #ff0050; font-size: 4.5em;'>
            🎬 VidSpace
        </h1>
        <p style='text-align: center; font-size: 1.5em; margin-top: -10px;'>
            Create. Share. Connect.
        </p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Login 🚀", use_container_width=True):
                if username and password:
                    success, msg = login(username, password)
                    if success:
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error(msg)
        
        with tab2:
            username = st.text_input("Username", key="reg_user")
            password = st.text_input("Password", type="password", key="reg_pass")
            password2 = st.text_input("Confirm", type="password", key="reg_pass2")
            
            if st.button("Create Account ✨", use_container_width=True):
                if username and password and password2:
                    if password != password2:
                        st.error("Passwords don't match!")
                    elif len(password) < 4:
                        st.error("Password too short!")
                    else:
                        success, msg = create_account(username, password)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)

def show_feed_page():
    st.markdown("<h2 style='color: #ff0050;'>🏠 For You</h2>", unsafe_allow_html=True)
    
    videos = get_feed_videos(st.session_state.username)
    
    if not videos:
        st.info("No videos yet! Be the first to upload! 📹")
        return
    
    for video in videos:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"""
                <div class='video-card'>
                    <h3 style='color: #ff0050; margin: 0;'>@{video['username']}</h3>
                    <p style='margin: 5px 0;'>{video['caption']}</p>
                    <p style='color: #888; font-size: 0.9em; margin: 0;'>{video['hashtags']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            media.get_video_player(video['video_data'])
        
        with col2:
            st.markdown(f"**👁️ {video['views']}**")
            
            # Like
            interactions = db.get_one('interactions', 'username', st.session_state.username)
            is_liked = video['id'] in (interactions.get('likes', []) if interactions else [])
            like_emoji = "❤️" if is_liked else "🤍"
            
            if st.button(f"{like_emoji} {video['likes']}", key=f"like_{video['id']}", use_container_width=True):
                toggle_like(st.session_state.username, video['id'])
                st.rerun()
            
            # Send to friend
            if st.button("📤 Send", key=f"send_{video['id']}", use_container_width=True):
                st.session_state.send_video_id = video['id']
                st.session_state.page = "messages"
                st.rerun()
            
            # Comments
            st.markdown(f"**💬 {len(video.get('comments', []))}**")
            
            with st.expander("Comments"):
                for comment in video.get('comments', []):
                    st.markdown(f"""
                        <div style='background: #2a2a2a; padding: 8px; border-radius: 8px; margin: 5px 0;'>
                            <strong style='color: #ff0050;'>@{comment['username']}</strong><br>
                            {comment['text']}<br>
                            <span style='color: #888; font-size: 0.8em;'>{time_ago(comment['timestamp'])}</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                comment_text = st.text_input("Comment", key=f"cmt_{video['id']}", placeholder="Add comment...")
                if st.button("Post", key=f"post_{video['id']}"):
                    if comment_text:
                        add_comment(video['id'], st.session_state.username, comment_text)
                        st.rerun()
        
        st.divider()

def show_notifications_page():
    st.markdown("<h2 style='color: #ff0050;'>🔔 Notifications</h2>", unsafe_allow_html=True)
    
    # Mark as read
    mark_notifications_read(st.session_state.username)
    
    account = db.get_one('accounts', 'username', st.session_state.username)
    notifications = account.get('notifications', [])[::-1]  # Newest first
    
    if not notifications:
        st.info("No notifications yet!")
        return
    
    for notif in notifications:
        st.markdown(f"""
            <div style='background: #1a1a1a; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #ff0050;'>
                <p style='margin: 0;'>{notif['text']}</p>
                <p style='color: #888; font-size: 0.85em; margin: 5px 0 0 0;'>{time_ago(notif['timestamp'])}</p>
            </div>
        """, unsafe_allow_html=True)

def show_messages_page():
    st.markdown("<h2 style='color: #ff0050;'>💬 Messages</h2>", unsafe_allow_html=True)
    
    # Check if sending a video
    send_video = st.session_state.get('send_video_id')
    
    # Get chat list
    chat_users = get_user_chats(st.session_state.username)
    
    if not chat_users and not send_video:
        st.info("No messages yet! Start a conversation!")
        
        # Show all users to start chat
        st.markdown("**Start a new chat:**")
        accounts = db.get_all('accounts')
        for username in accounts.keys():
            if username != st.session_state.username:
                if st.button(f"💬 Chat with @{username}", key=f"newchat_{username}"):
                    st.session_state.chat_with = username
                    st.rerun()
        return
    
    # Sidebar: chat list
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("**Chats:**")
        for user in chat_users:
            if st.button(f"@{user}", key=f"chat_{user}", use_container_width=True):
                st.session_state.chat_with = user
                if 'send_video_id' in st.session_state:
                    del st.session_state.send_video_id
                st.rerun()
    
    with col2:
        current_chat = st.session_state.get('chat_with')
        
        if send_video:
            st.markdown("**Send video to:**")
            accounts = db.get_all('accounts')
            for username in accounts.keys():
                if username != st.session_state.username:
                    if st.button(f"Send to @{username}", key=f"sendto_{username}"):
                        send_message(
                            st.session_state.username,
                            username,
                            "Sent you a video! 🎬",
                            video_id=send_video
                        )
                        st.success(f"Sent to @{username}!")
                        del st.session_state.send_video_id
                        st.session_state.chat_with = username
                        time.sleep(1)
                        st.rerun()
            return
        
        if not current_chat:
            st.info("Select a chat")
            return
        
        # Show chat
        st.markdown(f"<h3>Chat with @{current_chat}</h3>", unsafe_allow_html=True)
        
        messages = get_chat_messages(st.session_state.username, current_chat)
        
        # Display messages
        for msg in messages:
            is_sent = msg['sender'] == st.session_state.username
            css_class = "chat-message-sent" if is_sent else "chat-message-received"
            
            msg_html = f"""
                <div class='{css_class}'>
                    <p style='margin: 0;'>{msg['text']}</p>
                    <p style='font-size: 0.75em; margin: 5px 0 0 0; opacity: 0.8;'>{time_ago(msg['timestamp'])}</p>
                </div>
            """
            st.markdown(msg_html, unsafe_allow_html=True)
            
            # Show video if included
            if msg.get('video_id'):
                video = db.get_one('videos', 'id', msg['video_id'])
                if video:
                    with st.expander("📹 Shared video"):
                        media.get_video_player(video['video_data'])
                        st.markdown(f"**@{video['username']}:** {video['caption']}")
        
        # Send message
        st.divider()
        with st.form(key="message_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                msg_text = st.text_input("Message", placeholder="Type a message...", label_visibility="collapsed")
            with col2:
                send_btn = st.form_submit_button("Send 📤", use_container_width=True)
            
            if send_btn and msg_text:
                send_message(st.session_state.username, current_chat, msg_text)
                st.rerun()

def show_upload_page():
    st.markdown("<h2 style='color: #ff0050;'>➕ Upload Video</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        video_file = st.file_uploader("Choose video", type=['mp4', 'mov', 'avi', 'webm'])
        caption = st.text_area("Caption", max_chars=500, placeholder="Describe your video...")
        hashtags = st.text_input("Hashtags", placeholder="#trending #viral #fyp")
        
        if st.button("🚀 Upload Video", use_container_width=True):
            if video_file and caption:
                with st.spinner("Uploading to cloud..."):
                    video_id = upload_video(st.session_state.username, video_file, caption, hashtags)
                    if video_id:
                        st.success("Video uploaded! 🎉")
                        time.sleep(1)
                        st.session_state.page = "profile"
                        st.rerun()
                    else:
                        st.error("Upload failed!")
            else:
                st.error("Please add video and caption!")

def show_profile_page():
    username = st.session_state.username
    account = db.get_one('accounts', 'username', username)
    
    # Get user's videos
    all_videos = db.get_all('videos')
    user_videos = [v for v in all_videos.values() if v['username'] == username]
    
    # Header
    st.markdown(f"""
        <div style='text-align: center; background: linear-gradient(135deg, #ff0050, #ff3366); padding: 30px; border-radius: 15px; margin-bottom: 20px;'>
            <h1 style='margin: 0;'>@{username}</h1>
            <p style='margin: 10px 0 0 0;'>{account.get('bio', 'No bio yet')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div style='text-align: center; background: #1a1a1a; padding: 20px; border-radius: 10px;'>
                <h2 style='color: #ff0050; margin: 0;'>{len(user_videos)}</h2>
                <p style='margin: 5px 0 0 0;'>Videos</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style='text-align: center; background: #1a1a1a; padding: 20px; border-radius: 10px;'>
                <h2 style='color: #ff0050; margin: 0;'>{len(account.get('followers', []))}</h2>
                <p style='margin: 5px 0 0 0;'>Followers</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div style='text-align: center; background: #1a1a1a; padding: 20px; border-radius: 10px;'>
                <h2 style='color: #ff0050; margin: 0;'>{len(account.get('following', []))}</h2>
                <p style='margin: 5px 0 0 0;'>Following</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Edit bio
    with st.expander("✏️ Edit Profile"):
        new_bio = st.text_area("Bio", value=account.get('bio', ''), max_chars=200)
        if st.button("Save Bio"):
            db.update('accounts', 'username', username, {'bio': new_bio})
            st.success("Bio updated!")
            st.rerun()
    
    st.divider()
    
    # Videos
    st.markdown("<h3 style='color: #ff0050;'>Your Videos</h3>", unsafe_allow_html=True)
    
    if user_videos:
        for video in user_videos:
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"""
                    <div style='background: #1a1a1a; padding: 15px; border-radius: 10px;'>
                        <p style='margin: 0;'><strong>{video['caption']}</strong></p>
                        <p style='color: #888; font-size: 0.9em; margin: 5px 0 0 0;'>
                            ❤️ {video['likes']} | 👁️ {video['views']} | 💬 {len(video.get('comments', []))}
                        </p>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("🗑️", key=f"del_{video['id']}"):
                    db.delete('videos', 'id', video['id'])
                    st.success("Deleted!")
                    st.rerun()
    else:
        st.info("No videos yet!")

if __name__ == "__main__":
    main()
