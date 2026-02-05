import streamlit as st
import json
import os
from datetime import datetime
import hashlib
import base64
import time

# Files
ACCOUNTS_FILE = "accounts.json"
VIDEOS_FILE = "videos.json"
INTERACTIONS_FILE = "interactions.json"
SESSIONS_FILE = "sessions.json"
VIDEOS_DIR = "uploaded_videos"

# Create directories
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Space/Dark theme CSS
APP_CSS = """
<style>
    .stApp {
        background: linear-gradient(to bottom, #000000, #1a1a1a, #0a0a0a);
    }
    
    .stMarkdown, p, label {
        color: #ffffff !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    ::-webkit-scrollbar-thumb {
        background: #ff0050;
        border-radius: 4px;
    }
    
    /* TikTok style buttons */
    .video-actions {
        position: fixed;
        right: 20px;
        bottom: 100px;
        z-index: 1000;
    }
</style>
"""

def init_files():
    for file in [ACCOUNTS_FILE, VIDEOS_FILE, INTERACTIONS_FILE, SESSIONS_FILE]:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump({}, f)

# Session management
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_file(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_file(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def create_session(username):
    sessions = load_file(SESSIONS_FILE)
    session_id = hashlib.sha256(f"{username}{datetime.now()}".encode()).hexdigest()
    sessions[session_id] = {
        'username': username,
        'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_file(SESSIONS_FILE, sessions)
    return session_id

def get_session(session_id):
    sessions = load_file(SESSIONS_FILE)
    session = sessions.get(session_id)
    return session['username'] if session else None

def delete_session(session_id):
    sessions = load_file(SESSIONS_FILE)
    if session_id in sessions:
        del sessions[session_id]
        save_file(SESSIONS_FILE, sessions)

# Account management
def create_account(username, password):
    accounts = load_file(ACCOUNTS_FILE)
    if username in accounts:
        return False, "Username already exists"
    
    accounts[username] = {
        'password': hash_password(password),
        'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'bio': "",
        'followers': [],
        'following': []
    }
    save_file(ACCOUNTS_FILE, accounts)
    return True, "Account created!"

def login(username, password):
    accounts = load_file(ACCOUNTS_FILE)
    if username not in accounts:
        return False, "Username not found", None
    if accounts[username]['password'] != hash_password(password):
        return False, "Incorrect password", None
    
    session_id = create_session(username)
    return True, "Login successful!", session_id

def get_user_profile(username):
    accounts = load_file(ACCOUNTS_FILE)
    return accounts.get(username, {})

def update_bio(username, bio):
    accounts = load_file(ACCOUNTS_FILE)
    if username in accounts:
        accounts[username]['bio'] = bio
        save_file(ACCOUNTS_FILE, accounts)

def follow_user(follower, following):
    accounts = load_file(ACCOUNTS_FILE)
    
    if follower in accounts and following in accounts:
        if following not in accounts[follower]['following']:
            accounts[follower]['following'].append(following)
            accounts[following]['followers'].append(follower)
            save_file(ACCOUNTS_FILE, accounts)
            return True
    return False

def unfollow_user(follower, following):
    accounts = load_file(ACCOUNTS_FILE)
    
    if follower in accounts and following in accounts:
        if following in accounts[follower]['following']:
            accounts[follower]['following'].remove(following)
            accounts[following]['followers'].remove(follower)
            save_file(ACCOUNTS_FILE, accounts)
            return True
    return False

# Video management
def upload_video(username, video_file, caption, hashtags):
    videos = load_file(VIDEOS_FILE)
    
    # Generate unique video ID
    video_id = f"vid_{int(datetime.now().timestamp())}_{username}"
    
    # Save video file
    video_path = os.path.join(VIDEOS_DIR, f"{video_id}.mp4")
    with open(video_path, 'wb') as f:
        f.write(video_file.read())
    
    # Save video metadata
    videos[video_id] = {
        'id': video_id,
        'username': username,
        'caption': caption,
        'hashtags': hashtags,
        'video_path': video_path,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'likes': 0,
        'views': 0,
        'comments': []
    }
    
    save_file(VIDEOS_FILE, videos)
    return video_id

def get_all_videos():
    """Get all videos sorted by timestamp (newest first)"""
    videos = load_file(VIDEOS_FILE)
    video_list = list(videos.values())
    video_list.sort(key=lambda x: x['timestamp'], reverse=True)
    return video_list

def get_user_videos(username):
    """Get videos by specific user"""
    videos = load_file(VIDEOS_FILE)
    user_videos = [v for v in videos.values() if v['username'] == username]
    user_videos.sort(key=lambda x: x['timestamp'], reverse=True)
    return user_videos

def get_trending_videos():
    """Get videos sorted by likes"""
    videos = load_file(VIDEOS_FILE)
    video_list = list(videos.values())
    video_list.sort(key=lambda x: x['likes'], reverse=True)
    return video_list[:50]  # Top 50

def get_for_you_videos(username):
    """Algorithm: videos from followed users + trending"""
    profile = get_user_profile(username)
    following = profile.get('following', [])
    
    videos = load_file(VIDEOS_FILE)
    
    # Videos from people you follow
    following_videos = [v for v in videos.values() if v['username'] in following]
    
    # Trending videos
    trending = get_trending_videos()
    
    # Mix them together
    all_videos = following_videos + [v for v in trending if v not in following_videos]
    
    return all_videos[:100]  # Limit to 100

def increment_views(video_id):
    videos = load_file(VIDEOS_FILE)
    if video_id in videos:
        videos[video_id]['views'] += 1
        save_file(VIDEOS_FILE, videos)

def add_comment(video_id, username, comment_text):
    videos = load_file(VIDEOS_FILE)
    if video_id in videos:
        videos[video_id]['comments'].append({
            'username': username,
            'text': comment_text,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_file(VIDEOS_FILE, videos)

# Interactions (likes)
def load_interactions():
    return load_file(INTERACTIONS_FILE)

def has_liked(username, video_id):
    interactions = load_interactions()
    user_likes = interactions.get(username, {}).get('likes', [])
    return video_id in user_likes

def toggle_like(username, video_id):
    interactions = load_interactions()
    videos = load_file(VIDEOS_FILE)
    
    if username not in interactions:
        interactions[username] = {'likes': []}
    
    if video_id in interactions[username]['likes']:
        # Unlike
        interactions[username]['likes'].remove(video_id)
        if video_id in videos:
            videos[video_id]['likes'] -= 1
    else:
        # Like
        interactions[username]['likes'].append(video_id)
        if video_id in videos:
            videos[video_id]['likes'] += 1
    
    save_file(INTERACTIONS_FILE, interactions)
    save_file(VIDEOS_FILE, videos)

# Main app
def main():
    st.set_page_config(page_title="🎬 VidSpace", page_icon="🎬", layout="wide")
    st.markdown(APP_CSS, unsafe_allow_html=True)
    
    init_files()
    
    # Session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "feed"
    if 'video_index' not in st.session_state:
        st.session_state.video_index = 0
    
    # Check session
    logged_in = False
    if st.session_state.session_id:
        username = get_session(st.session_state.session_id)
        if username:
            st.session_state.username = username
            logged_in = True
    
    # Login screen
    if not logged_in:
        st.markdown("""
            <h1 style='text-align: center; color: #ff0050; font-size: 4em;'>
                🎬 VidSpace
            </h1>
            <p style='text-align: center; color: #ffffff; font-size: 1.3em;'>
                Create. Share. Go Viral.
            </p>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            tab1, tab2 = st.tabs(["Login", "Sign Up"])
            
            with tab1:
                login_user = st.text_input("Username", key="login_user")
                login_pass = st.text_input("Password", type="password", key="login_pass")
                
                if st.button("Login 🚀", use_container_width=True):
                    if login_user and login_pass:
                        success, msg, session = login(login_user, login_pass)
                        if success:
                            st.session_state.session_id = session
                            st.session_state.username = login_user
                            st.rerun()
                        else:
                            st.error(msg)
            
            with tab2:
                reg_user = st.text_input("Username", key="reg_user")
                reg_pass = st.text_input("Password", type="password", key="reg_pass")
                reg_pass2 = st.text_input("Confirm Password", type="password", key="reg_pass2")
                
                if st.button("Create Account ✨", use_container_width=True):
                    if reg_user and reg_pass and reg_pass2:
                        if reg_pass != reg_pass2:
                            st.error("Passwords don't match!")
                        elif len(reg_pass) < 4:
                            st.error("Password too short!")
                        else:
                            success, msg = create_account(reg_user, reg_pass)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
        return
    
    # Navigation
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if st.button("🏠 For You", use_container_width=True):
            st.session_state.current_page = "feed"
            st.session_state.video_index = 0
            st.rerun()
    
    with col2:
        if st.button("🔥 Trending", use_container_width=True):
            st.session_state.current_page = "trending"
            st.session_state.video_index = 0
            st.rerun()
    
    with col3:
        if st.button("➕ Upload", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()
    
    with col4:
        if st.button("👤 Profile", use_container_width=True):
            st.session_state.current_page = "profile"
            st.rerun()
    
    with col5:
        if st.button("🔍 Explore", use_container_width=True):
            st.session_state.current_page = "explore"
            st.rerun()
    
    with col6:
        if st.button("🚪 Logout", use_container_width=True):
            delete_session(st.session_state.session_id)
            st.session_state.session_id = None
            st.rerun()
    
    st.divider()
    
    # Pages
    if st.session_state.current_page == "feed":
        show_feed(st.session_state.username, get_for_you_videos(st.session_state.username))
    
    elif st.session_state.current_page == "trending":
        show_feed(st.session_state.username, get_trending_videos())
    
    elif st.session_state.current_page == "upload":
        show_upload_page(st.session_state.username)
    
    elif st.session_state.current_page == "profile":
        show_profile_page(st.session_state.username)
    
    elif st.session_state.current_page == "explore":
        show_explore_page(st.session_state.username)

def show_feed(username, videos):
    """TikTok-style vertical feed"""
    
    if not videos:
        st.markdown("""
            <div style='text-align: center; padding: 100px;'>
                <h2 style='color: #ff0050;'>No videos yet! 📹</h2>
                <p style='color: #ffffff;'>Upload the first video or follow some users!</p>
            </div>
        """, unsafe_allow_html=True)
        return
    
    # Navigation
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("⬆️ Previous", use_container_width=True):
            if st.session_state.video_index > 0:
                st.session_state.video_index -= 1
                st.rerun()
    
    with col2:
        st.markdown(f"""
            <p style='text-align: center; color: #ffffff;'>
                Video {st.session_state.video_index + 1} of {len(videos)}
            </p>
        """, unsafe_allow_html=True)
    
    with col3:
        if st.button("⬇️ Next", use_container_width=True):
            if st.session_state.video_index < len(videos) - 1:
                st.session_state.video_index += 1
                st.rerun()
    
    # Current video
    video = videos[st.session_state.video_index]
    video_id = video['id']
    
    # Increment views
    increment_views(video_id)
    
    # Video display
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"""
            <div style='background: #1a1a1a; padding: 20px; border-radius: 10px;'>
                <h3 style='color: #ff0050;'>@{video['username']}</h3>
                <p style='color: #ffffff;'>{video['caption']}</p>
                <p style='color: #888888;'>{video['hashtags']}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Video player
        if os.path.exists(video['video_path']):
            with open(video['video_path'], 'rb') as f:
                video_bytes = f.read()
                st.video(video_bytes)
        else:
            st.error("Video file not found")
    
    with col2:
        # Actions
        st.markdown(f"<h4 style='color: #ffffff;'>👁️ {video['views']} views</h4>", unsafe_allow_html=True)
        
        # Like button
        is_liked = has_liked(username, video_id)
        like_emoji = "❤️" if is_liked else "🤍"
        
        if st.button(f"{like_emoji} {video['likes']}", key=f"like_{video_id}", use_container_width=True):
            toggle_like(username, video_id)
            st.rerun()
        
        # Follow button
        if video['username'] != username:
            profile = get_user_profile(username)
            is_following = video['username'] in profile.get('following', [])
            
            if is_following:
                if st.button("✅ Following", key=f"unfollow_{video_id}", use_container_width=True):
                    unfollow_user(username, video['username'])
                    st.rerun()
            else:
                if st.button("➕ Follow", key=f"follow_{video_id}", use_container_width=True):
                    follow_user(username, video['username'])
                    st.rerun()
        
        # Comments
        st.markdown(f"<h4 style='color: #ffffff;'>💬 {len(video['comments'])} comments</h4>", unsafe_allow_html=True)
        
        with st.expander("View Comments"):
            for comment in video['comments']:
                st.markdown(f"""
                    <div style='background: #2a2a2a; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                        <strong style='color: #ff0050;'>@{comment['username']}</strong><br>
                        <span style='color: #ffffff;'>{comment['text']}</span>
                    </div>
                """, unsafe_allow_html=True)
        
        # Add comment
        with st.form(key=f"comment_form_{video_id}"):
            comment_text = st.text_input("Add comment", label_visibility="collapsed", placeholder="Add a comment...")
            if st.form_submit_button("💬 Comment", use_container_width=True):
                if comment_text:
                    add_comment(video_id, username, comment_text)
                    st.rerun()

def show_upload_page(username):
    st.markdown("<h2 style='color: #ff0050;'>📹 Upload Video</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        video_file = st.file_uploader("Choose a video file", type=['mp4', 'mov', 'avi'])
        caption = st.text_area("Caption", max_chars=500, placeholder="What's this video about?")
        hashtags = st.text_input("Hashtags", placeholder="#fyp #viral #trending")
        
        if st.button("🚀 Upload Video", use_container_width=True):
            if video_file and caption:
                with st.spinner("Uploading..."):
                    video_id = upload_video(username, video_file, caption, hashtags)
                    st.success("Video uploaded! 🎉")
                    time.sleep(1)
                    st.session_state.current_page = "profile"
                    st.rerun()
            else:
                st.error("Please add video and caption!")

def show_profile_page(username):
    profile = get_user_profile(username)
    user_videos = get_user_videos(username)
    
    st.markdown(f"""
        <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #ff0050, #ff6b9d); border-radius: 10px;'>
            <h1 style='color: #ffffff;'>@{username}</h1>
            <p style='color: #ffffff; font-size: 1.2em;'>{profile.get('bio', 'No bio yet')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div style='text-align: center; padding: 20px; background: #1a1a1a; border-radius: 10px;'>
                <h2 style='color: #ff0050;'>{len(user_videos)}</h2>
                <p style='color: #ffffff;'>Videos</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style='text-align: center; padding: 20px; background: #1a1a1a; border-radius: 10px;'>
                <h2 style='color: #ff0050;'>{len(profile.get('followers', []))}</h2>
                <p style='color: #ffffff;'>Followers</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div style='text-align: center; padding: 20px; background: #1a1a1a; border-radius: 10px;'>
                <h2 style='color: #ff0050;'>{len(profile.get('following', []))}</h2>
                <p style='color: #ffffff;'>Following</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Edit bio
    with st.expander("✏️ Edit Bio"):
        new_bio = st.text_area("Bio", value=profile.get('bio', ''), max_chars=200)
        if st.button("Save Bio"):
            update_bio(username, new_bio)
            st.success("Bio updated!")
            st.rerun()
    
    st.divider()
    
    # User's videos
    st.markdown("<h3 style='color: #ff0050;'>Your Videos</h3>", unsafe_allow_html=True)
    
    if user_videos:
        cols = st.columns(3)
        for idx, video in enumerate(user_videos):
            with cols[idx % 3]:
                st.markdown(f"""
                    <div style='background: #1a1a1a; padding: 10px; border-radius: 10px; margin: 5px;'>
                        <p style='color: #ffffff;'><strong>{video['caption'][:30]}...</strong></p>
                        <p style='color: #888888;'>❤️ {video['likes']} 👁️ {video['views']}</p>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No videos yet. Upload your first video!")

def show_explore_page(username):
    st.markdown("<h2 style='color: #ff0050;'>🔍 Explore Users</h2>", unsafe_allow_html=True)
    
    accounts = load_file(ACCOUNTS_FILE)
    my_profile = get_user_profile(username)
    my_following = my_profile.get('following', [])
    
    for user, data in accounts.items():
        if user == username:
            continue
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            user_videos = get_user_videos(user)
            st.markdown(f"""
                <div style='background: #1a1a1a; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                    <h3 style='color: #ff0050;'>@{user}</h3>
                    <p style='color: #ffffff;'>{data.get('bio', 'No bio')}</p>
                    <p style='color: #888888;'>
                        📹 {len(user_videos)} videos | 
                        👥 {len(data.get('followers', []))} followers
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            is_following = user in my_following
            
            if is_following:
                if st.button("Unfollow", key=f"unfollow_{user}", use_container_width=True):
                    unfollow_user(username, user)
                    st.rerun()
            else:
                if st.button("Follow", key=f"follow_{user}", use_container_width=True):
                    follow_user(username, user)
                    st.rerun()

if __name__ == "__main__":
    main()
