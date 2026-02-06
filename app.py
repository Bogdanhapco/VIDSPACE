import streamlit as st

# MUST BE FIRST - st.set_page_config
st.set_page_config(page_title="🎬 VidSpace", page_icon="🎬", layout="wide")

import json
from datetime import datetime
import hashlib
import time

try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except:
    MONGO_AVAILABLE = False

try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
except:
    CLOUDINARY_AVAILABLE = False

APP_CSS = """
<style>
.stApp{background:linear-gradient(to bottom,#000,#0d0d0d,#1a1a1a)}
*{color:#fff!important}
.video-card{background:linear-gradient(135deg,#1a1a1a 0%,#2d2d2d 100%);border-radius:20px;padding:20px;margin:15px 0;border:2px solid #ff0050;box-shadow:0 0 20px rgba(255,0,80,0.3)}
.chat-message-sent{background:linear-gradient(135deg,#ff0050,#ff3366);border-radius:15px;padding:10px 15px;margin:5px 0;max-width:70%;margin-left:auto}
.chat-message-received{background:linear-gradient(135deg,#2d2d2d,#404040);border-radius:15px;padding:10px 15px;margin:5px 0;max-width:70%}
#MainMenu{visibility:hidden}footer{visibility:hidden}
</style>
"""

class Database:
    def __init__(self):
        self.use_cloud=False
        self.db=None
        if MONGO_AVAILABLE and 'mongodb' in st.secrets:
            try:
                client=MongoClient(st.secrets['mongodb']['connection_string'],serverSelectionTimeoutMS=5000)
                self.db=client['vidspace']
                client.server_info()
                self.use_cloud=True
                st.success("✅ MongoDB Connected!")
            except Exception as e:
                st.warning(f"⚠️ MongoDB failed. Using local.")
        if not self.use_cloud:
            import os
            os.makedirs("data",exist_ok=True)
    
    def _local_load(self,collection):
        try:
            with open(f"data/{collection}.json",'r')as f:return json.load(f)
        except:return{}
    
    def _local_save(self,collection,data):
        with open(f"data/{collection}.json",'w')as f:json.dump(data,f,indent=2)
    
    def get_all(self,collection):
        if self.use_cloud:
            try:
                items=list(self.db[collection].find({},{'_id':0}))
                return{item.get('id',item.get('username',str(i))):item for i,item in enumerate(items)}
            except:return{}
        return self._local_load(collection)
    
    def get_one(self,collection,key,value):
        if self.use_cloud:
            try:return self.db[collection].find_one({key:value},{'_id':0})
            except:return None
        data=self._local_load(collection)
        for item in data.values():
            if item.get(key)==value:return item
        return None
    
    def insert(self,collection,doc):
        if self.use_cloud:
            try:self.db[collection].insert_one(doc)
            except:pass
        else:
            data=self._local_load(collection)
            key=doc.get('id',doc.get('username'))
            data[key]=doc
            self._local_save(collection,data)
    
    def update(self,collection,key,value,update_data):
        if self.use_cloud:
            try:self.db[collection].update_one({key:value},{'$set':update_data})
            except:pass
        else:
            data=self._local_load(collection)
            for k,item in data.items():
                if item.get(key)==value:
                    data[k].update(update_data)
                    break
            self._local_save(collection,data)
    
    def delete(self,collection,key,value):
        if self.use_cloud:
            try:self.db[collection].delete_one({key:value})
            except:pass
        else:
            data=self._local_load(collection)
            data={k:v for k,v in data.items()if v.get(key)!=value}
            self._local_save(collection,data)

db=Database()

class MediaStorage:
    def __init__(self):
        self.use_cloud=False
        if CLOUDINARY_AVAILABLE and 'cloudinary' in st.secrets:
            try:
                cloudinary.config(cloud_name=st.secrets['cloudinary']['cloud_name'],api_key=st.secrets['cloudinary']['api_key'],api_secret=st.secrets['cloudinary']['api_secret'])
                self.use_cloud=True
                st.success("✅ VIDSPACE Cloud Connected!")
            except:st.warning("⚠️ VIDSPACE Cloud failed")
    
    def upload_video(self,video_file,video_id):
        if self.use_cloud:
            try:
                result=cloudinary.uploader.upload(video_file,resource_type="video",public_id=video_id,folder="vidspace_videos")
                return result['secure_url']
            except:return None
        else:
            import base64
            return base64.b64encode(video_file.read()).decode()
    
    def get_video_player(self,video_data):
        if self.use_cloud and video_data and video_data.startswith('http'):
            return st.video(video_data)
        else:
            import base64
            try:return st.video(base64.b64decode(video_data))
            except:return st.error("Error loading video")

media=MediaStorage()

def hash_password(password):return hashlib.sha256(password.encode()).hexdigest()
def create_id(prefix):return f"{prefix}_{int(datetime.now().timestamp())}_{hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:8]}"
def time_ago(timestamp_str):
    try:
        timestamp=datetime.fromisoformat(timestamp_str)
        diff=datetime.now()-timestamp
        if diff.seconds<60:return "just now"
        elif diff.seconds<3600:return f"{diff.seconds//60}m ago"
        elif diff.seconds<86400:return f"{diff.seconds//3600}h ago"
        elif diff.days<7:return f"{diff.days}d ago"
        else:return timestamp.strftime("%b %d")
    except:return "recently"

def create_account(username,password):
    if db.get_one('accounts','username',username):return False,"Username exists"
    db.insert('accounts',{'username':username,'password':hash_password(password),'created':datetime.now().isoformat(),'bio':"",'profile_pic':None,'followers':[],'following':[],'notifications':[]})
    return True,"Account created!"

def login(username,password):
    account=db.get_one('accounts','username',username)
    if not account:return False,"Username not found"
    if account['password']!=hash_password(password):return False,"Incorrect password"
    return True,"Login successful!"

def add_notification(username,text):
    account=db.get_one('accounts','username',username)
    if account:
        notifs=account.get('notifications',[])
        notifs.append({'text':text,'timestamp':datetime.now().isoformat(),'read':False})
        db.update('accounts','username',username,{'notifications':notifs[-50:]})

def get_unread_notifications_count(username):
    account=db.get_one('accounts','username',username)
    return sum(1 for n in account.get('notifications',[])if not n.get('read',False))if account else 0

def mark_notifications_read(username):
    account=db.get_one('accounts','username',username)
    if account:
        notifs=account.get('notifications',[])
        for n in notifs:n['read']=True
        db.update('accounts','username',username,{'notifications':notifs})

def upload_video(username,video_file,caption,hashtags):
    video_id=create_id("vid")
    video_data=media.upload_video(video_file,video_id)
    if not video_data:return None
    db.insert('videos',{'id':video_id,'username':username,'caption':caption,'hashtags':hashtags,'video_data':video_data,'timestamp':datetime.now().isoformat(),'likes':0,'views':0,'comments':[]})
    account=db.get_one('accounts','username',username)
    if account:
        for follower in account.get('followers',[]):
            add_notification(follower,f"@{username} posted!")
    return video_id

def get_feed_videos(username):
    videos=list(db.get_all('videos').values())
    account=db.get_one('accounts','username',username)
    following=account.get('following',[])if account else[]
    following_vids=[v for v in videos if v['username']in following]
    trending=[v for v in sorted(videos,key=lambda x:x.get('likes',0),reverse=True)if v not in following_vids]
    return following_vids+trending

def toggle_like(username,video_id):
    interactions=db.get_one('interactions','username',username)
    if not interactions:
        interactions={'username':username,'likes':[]}
        db.insert('interactions',interactions)
    likes=interactions.get('likes',[])
    video=db.get_one('videos','id',video_id)
    if video:
        if video_id in likes:
            likes.remove(video_id)
            video['likes']=max(0,video.get('likes',0)-1)
        else:
            likes.append(video_id)
            video['likes']=video.get('likes',0)+1
            if video['username']!=username:add_notification(video['username'],f"@{username} liked your video!")
        db.update('interactions','username',username,{'likes':likes})
        db.update('videos','id',video_id,{'likes':video['likes']})

def add_comment(video_id,username,text):
    video=db.get_one('videos','id',video_id)
    if video:
        comments=video.get('comments',[])
        comments.append({'username':username,'text':text,'timestamp':datetime.now().isoformat()})
        db.update('videos','id',video_id,{'comments':comments})
        if video['username']!=username:add_notification(video['username'],f"@{username} commented!")

def increment_views(video_id):
    video=db.get_one('videos','id',video_id)
    if video:db.update('videos','id',video_id,{'views':video.get('views',0)+1})

def send_message(sender,recipient,text,video_id=None):
    chat_id="_".join(sorted([sender,recipient]))
    db.insert('messages',{'id':create_id("msg"),'chat_id':chat_id,'sender':sender,'recipient':recipient,'text':text,'video_id':video_id,'timestamp':datetime.now().isoformat(),'read':False})
    add_notification(recipient,f"@{sender} sent a message")

def get_chat_messages(user1,user2):
    chat_id="_".join(sorted([user1,user2]))
    msgs=db.get_all('messages')
    chat_msgs=[m for m in msgs.values()if m.get('chat_id')==chat_id]
    chat_msgs.sort(key=lambda x:x['timestamp'])
    return chat_msgs

def get_user_chats(username):
    msgs=db.get_all('messages')
    users=set()
    for msg in msgs.values():
        if msg.get('sender')==username:users.add(msg.get('recipient'))
        elif msg.get('recipient')==username:users.add(msg.get('sender'))
    return list(users)

def get_unread_messages_count(username):
    msgs=db.get_all('messages')
    return sum(1 for m in msgs.values()if m.get('recipient')==username and not m.get('read',False))

def follow_user(follower,following):
    fa=db.get_one('accounts','username',follower)
    fb=db.get_one('accounts','username',following)
    if fa and fb:
        fl=fa.get('following',[])
        fo=fb.get('followers',[])
        if following not in fl:
            fl.append(following)
            fo.append(follower)
            db.update('accounts','username',follower,{'following':fl})
            db.update('accounts','username',following,{'followers':fo})
            add_notification(following,f"@{follower} followed you!")

def unfollow_user(follower,following):
    fa=db.get_one('accounts','username',follower)
    fb=db.get_one('accounts','username',following)
    if fa and fb:
        fl=fa.get('following',[])
        fo=fb.get('followers',[])
        if following in fl:
            fl.remove(following)
            fo.remove(follower)
            db.update('accounts','username',follower,{'following':fl})
            db.update('accounts','username',following,{'followers':fo})

def main():
    st.markdown(APP_CSS,unsafe_allow_html=True)
    if 'username'not in st.session_state:st.session_state.username=None
    if 'page'not in st.session_state:st.session_state.page="feed"
    
    if not st.session_state.username:
        st.markdown("<h1 style='text-align:center;color:#ff0050;font-size:4.5em'>🎬 VidSpace</h1><p style='text-align:center;font-size:1.5em'>Create. Share. Connect.</p>",unsafe_allow_html=True)
        col1,col2,col3=st.columns([1,2,1])
        with col2:
            tab1,tab2=st.tabs(["Login","Sign Up"])
            with tab1:
                u=st.text_input("Username",key="lu")
                p=st.text_input("Password",type="password",key="lp")
                if st.button("Login 🚀",use_container_width=True):
                    if u and p:
                        s,m=login(u,p)
                        if s:st.session_state.username=u;st.rerun()
                        else:st.error(m)
            with tab2:
                u=st.text_input("Username",key="ru")
                p=st.text_input("Password",type="password",key="rp")
                p2=st.text_input("Confirm",type="password",key="rp2")
                if st.button("Create Account ✨",use_container_width=True):
                    if u and p and p2:
                        if p!=p2:st.error("Passwords don't match!")
                        elif len(p)<4:st.error("Password too short!")
                        else:
                            s,m=create_account(u,p)
                            if s:st.success(m)
                            else:st.error(m)
        return
    
    nc=get_unread_notifications_count(st.session_state.username)
    mc=get_unread_messages_count(st.session_state.username)
    st.markdown("<h1 style='text-align:center;color:#ff0050;font-size:3.5em'>🎬 VidSpace</h1>",unsafe_allow_html=True)
    
    col1,col2,col3,col4,col5,col6=st.columns(6)
    with col1:
        if st.button("🏠 Feed",use_container_width=True):st.session_state.page="feed";st.rerun()
    with col2:
        if st.button(f"🔔{f' ({nc})'if nc>0 else''}",use_container_width=True):st.session_state.page="notif";st.rerun()
    with col3:
        if st.button(f"💬{f' ({mc})'if mc>0 else''}",use_container_width=True):st.session_state.page="messages";st.rerun()
    with col4:
        if st.button("➕ Upload",use_container_width=True):st.session_state.page="upload";st.rerun()
    with col5:
        if st.button("👤 Profile",use_container_width=True):st.session_state.page="profile";st.rerun()
    with col6:
        if st.button("🚪 Logout",use_container_width=True):st.session_state.username=None;st.rerun()
    
    st.divider()
    
    if st.session_state.page=="feed":
        st.markdown("<h2 style='color:#ff0050'>🏠 For You</h2>",unsafe_allow_html=True)
        videos=get_feed_videos(st.session_state.username)
        if not videos:st.info("No videos yet!");return
        for v in videos:
            increment_views(v['id'])
            col1,col2=st.columns([3,1])
            with col1:
                st.markdown(f"<div class='video-card'><h3 style='color:#ff0050;margin:0'>@{v['username']}</h3><p style='margin:5px 0'>{v['caption']}</p><p style='color:#888;font-size:0.9em;margin:0'>{v['hashtags']}</p></div>",unsafe_allow_html=True)
                media.get_video_player(v['video_data'])
            with col2:
                st.markdown(f"**👁️ {v['views']}**")
                i=db.get_one('interactions','username',st.session_state.username)
                liked=v['id']in(i.get('likes',[])if i else[])
                if st.button(f"{'❤️'if liked else'🤍'} {v['likes']}",key=f"l{v['id']}",use_container_width=True):toggle_like(st.session_state.username,v['id']);st.rerun()
                if st.button("📤 Send",key=f"s{v['id']}",use_container_width=True):st.session_state.send_video_id=v['id'];st.session_state.page="messages";st.rerun()
                st.markdown(f"**💬 {len(v.get('comments',[]))}**")
                with st.expander("Comments"):
                    for c in v.get('comments',[]):
                        st.markdown(f"<div style='background:#2a2a2a;padding:8px;border-radius:8px;margin:5px 0'><strong style='color:#ff0050'>@{c['username']}</strong><br>{c['text']}<br><span style='color:#888;font-size:0.8em'>{time_ago(c['timestamp'])}</span></div>",unsafe_allow_html=True)
                    ct=st.text_input("Comment",key=f"c{v['id']}",placeholder="Add...")
                    if st.button("Post",key=f"p{v['id']}"):
                        if ct:add_comment(v['id'],st.session_state.username,ct);st.rerun()
            st.divider()
    
    elif st.session_state.page=="notif":
        st.markdown("<h2 style='color:#ff0050'>🔔 Notifications</h2>",unsafe_allow_html=True)
        mark_notifications_read(st.session_state.username)
        a=db.get_one('accounts','username',st.session_state.username)
        notifs=a.get('notifications',[])[::-1]if a else[]
        if not notifs:st.info("No notifications!");return
        for n in notifs:
            st.markdown(f"<div style='background:#1a1a1a;padding:15px;border-radius:10px;margin:10px 0;border-left:4px solid #ff0050'><p style='margin:0'>{n['text']}</p><p style='color:#888;font-size:0.85em;margin:5px 0 0 0'>{time_ago(n['timestamp'])}</p></div>",unsafe_allow_html=True)
    
    elif st.session_state.page=="messages":
        st.markdown("<h2 style='color:#ff0050'>💬 Messages</h2>",unsafe_allow_html=True)
        sv=st.session_state.get('send_video_id')
        cu=get_user_chats(st.session_state.username)
        if not cu and not sv:
            st.info("No messages!")
            st.markdown("**Start chat:**")
            accs=db.get_all('accounts')
            for u in accs.keys():
                if u!=st.session_state.username:
                    if st.button(f"💬 @{u}",key=f"nc{u}"):st.session_state.chat_with=u;st.rerun()
            return
        col1,col2=st.columns([1,3])
        with col1:
            st.markdown("**Chats:**")
            for u in cu:
                if st.button(f"@{u}",key=f"ch{u}",use_container_width=True):
                    st.session_state.chat_with=u
                    if 'send_video_id'in st.session_state:del st.session_state.send_video_id
                    st.rerun()
        with col2:
            cc=st.session_state.get('chat_with')
            if sv:
                st.markdown("**Send video to:**")
                accs=db.get_all('accounts')
                for u in accs.keys():
                    if u!=st.session_state.username:
                        if st.button(f"Send to @{u}",key=f"st{u}"):
                            send_message(st.session_state.username,u,"Sent you a video! 🎬",video_id=sv)
                            st.success(f"Sent!")
                            del st.session_state.send_video_id
                            st.session_state.chat_with=u
                            time.sleep(1)
                            st.rerun()
                return
            if not cc:st.info("Select chat");return
            st.markdown(f"<h3>Chat with @{cc}</h3>",unsafe_allow_html=True)
            msgs=get_chat_messages(st.session_state.username,cc)
            for m in msgs:
                is_sent=m['sender']==st.session_state.username
                css='chat-message-sent'if is_sent else'chat-message-received'
                st.markdown(f"<div class='{css}'><p style='margin:0'>{m['text']}</p><p style='font-size:0.75em;margin:5px 0 0 0;opacity:0.8'>{time_ago(m['timestamp'])}</p></div>",unsafe_allow_html=True)
                if m.get('video_id'):
                    vv=db.get_one('videos','id',m['video_id'])
                    if vv:
                        with st.expander("📹 Shared video"):
                            media.get_video_player(vv['video_data'])
                            st.markdown(f"**@{vv['username']}:** {vv['caption']}")
            st.divider()
            with st.form(key="mf",clear_on_submit=True):
                col1,col2=st.columns([4,1])
                with col1:mt=st.text_input("Message",placeholder="Type...",label_visibility="collapsed")
                with col2:sb=st.form_submit_button("Send",use_container_width=True)
                if sb and mt:send_message(st.session_state.username,cc,mt);st.rerun()
    
    elif st.session_state.page=="upload":
        st.markdown("<h2 style='color:#ff0050'>➕ Upload</h2>",unsafe_allow_html=True)
        col1,col2,col3=st.columns([1,2,1])
        with col2:
            vf=st.file_uploader("Video",type=['mp4','mov','avi','webm'])
            cap=st.text_area("Caption",max_chars=500)
            ht=st.text_input("Hashtags",placeholder="#trending")
            if st.button("🚀 Upload",use_container_width=True):
                if vf and cap:
                    with st.spinner("Uploading..."):
                        vid_id=upload_video(st.session_state.username,vf,cap,ht)
                        if vid_id:st.success("Uploaded!");time.sleep(1);st.session_state.page="profile";st.rerun()
                        else:st.error("Failed!")
                else:st.error("Add video & caption!")
    
    elif st.session_state.page=="profile":
        u=st.session_state.username
        a=db.get_one('accounts','username',u)
        vids=[v for v in db.get_all('videos').values()if v['username']==u]
        st.markdown(f"<div style='text-align:center;background:linear-gradient(135deg,#ff0050,#ff3366);padding:30px;border-radius:15px;margin-bottom:20px'><h1 style='margin:0'>@{u}</h1><p style='margin:10px 0 0 0'>{a.get('bio','No bio')}</p></div>",unsafe_allow_html=True)
        col1,col2,col3=st.columns(3)
        with col1:st.markdown(f"<div style='text-align:center;background:#1a1a1a;padding:20px;border-radius:10px'><h2 style='color:#ff0050;margin:0'>{len(vids)}</h2><p style='margin:5px 0 0 0'>Videos</p></div>",unsafe_allow_html=True)
        with col2:st.markdown(f"<div style='text-align:center;background:#1a1a1a;padding:20px;border-radius:10px'><h2 style='color:#ff0050;margin:0'>{len(a.get('followers',[]))}</h2><p style='margin:5px 0 0 0'>Followers</p></div>",unsafe_allow_html=True)
        with col3:st.markdown(f"<div style='text-align:center;background:#1a1a1a;padding:20px;border-radius:10px'><h2 style='color:#ff0050;margin:0'>{len(a.get('following',[]))}</h2><p style='margin:5px 0 0 0'>Following</p></div>",unsafe_allow_html=True)
        st.divider()
        with st.expander("✏️ Edit"):
            nb=st.text_area("Bio",value=a.get('bio',''),max_chars=200)
            if st.button("Save"):db.update('accounts','username',u,{'bio':nb});st.success("Updated!");st.rerun()
        st.divider()
        st.markdown("<h3 style='color:#ff0050'>Your Videos</h3>",unsafe_allow_html=True)
        if vids:
            for v in vids:
                col1,col2=st.columns([4,1])
                with col1:st.markdown(f"<div style='background:#1a1a1a;padding:15px;border-radius:10px'><p style='margin:0'><strong>{v['caption']}</strong></p><p style='color:#888;font-size:0.9em;margin:5px 0 0 0'>❤️ {v['likes']} | 👁️ {v['views']} | 💬 {len(v.get('comments',[]))}</p></div>",unsafe_allow_html=True)
                with col2:
                    if st.button("🗑️",key=f"d{v['id']}"):db.delete('videos','id',v['id']);st.success("Deleted!");st.rerun()
        else:st.info("No videos!")

if __name__=="__main__":main()

