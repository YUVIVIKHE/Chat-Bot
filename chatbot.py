import streamlit as st
import os
import base64
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Chat Bot",
    page_icon="💬",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .bot-message {
        background-color: #f5f5f5;
    }
    .file-upload {
        margin-top: 0.5rem;
        padding: 0.5rem;
        border-radius: 0.3rem;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
    }
    .audio-message {
        margin-top: 0.5rem;
        padding: 0.5rem;
        border-radius: 0.3rem;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
    }
    .interaction-panel {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Create uploads directory if it doesn't exist
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat title
st.title("💬 Chat Bot")
st.markdown("---")

# Display chat history
try:
    for message in st.session_state.messages:
        with st.container():
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">👤 You: {message["content"]}</div>', unsafe_allow_html=True)
                # Display file if present
                if "file" in message and message["file"]:
                    file_path = message["file"]
                    file_name = os.path.basename(file_path)
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                    
                    # Determine file type
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    if file_ext in ['.png', '.jpg', '.jpeg', '.gif']:
                        # Display image
                        st.image(file_content, caption=file_name)
                    elif file_ext in ['.pdf', '.txt', '.csv']:
                        # Create download link
                        b64 = base64.b64encode(file_content).decode()
                        href = f'<div class="file-upload">📎 Uploaded file: <a href="data:application/octet-stream;base64,{b64}" download="{file_name}">{file_name}</a></div>'
                        st.markdown(href, unsafe_allow_html=True)
                    elif file_ext in ['.mp3', '.wav', '.ogg']:
                        # Display audio
                        st.audio(file_content, format=f'audio/{file_ext[1:]}')
            else:
                st.markdown(f'<div class="chat-message bot-message">🤖 Bot: {message["content"]}</div>', unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error displaying messages: {e}")
    # Reset messages if there's an error
    st.session_state.messages = []

# Create tabs for different input methods
tab1, tab2, tab3 = st.tabs(["Text", "File Upload", "Audio Upload"])

with tab1:
    # Chat input
    user_input = st.text_input("Your message:", key="user_input", placeholder="Type your message here...")
    
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Simple bot response (you can replace this with more sophisticated logic)
        bot_response = f"I received your message: {user_input}"
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
        
        # Rerun the app to update the chat
        st.rerun()

with tab2:
    uploaded_file = st.file_uploader("Choose a file", type=["png", "jpg", "jpeg", "pdf", "txt", "csv"], key="file_uploader")
    file_message = st.text_input("Add a message with your file (optional):", key="file_message", placeholder="Type your message here...")
    
    if st.button("Send File", key="send_file"):
        if uploaded_file:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join("uploads", f"{timestamp}_{uploaded_file.name}")
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            # Create message
            message_content = file_message if file_message else f"Uploaded a file: {uploaded_file.name}"
            
            # Add to chat history
            st.session_state.messages.append({
                "role": "user", 
                "content": message_content,
                "file": file_path
            })
            
            # Bot response
            bot_response = f"I received your file: {uploaded_file.name}"
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            
            # Rerun the app to update the chat
            st.rerun()
        else:
            st.warning("Please upload a file first.")

with tab3:
    # Audio upload (simpler approach)
    audio_file = st.file_uploader("Upload an audio file", type=["mp3", "wav", "ogg"], key="audio_uploader")
    audio_message = st.text_input("Add a message with your audio (optional):", key="audio_message", placeholder="Type your message here...")
    
    if st.button("Send Audio", key="send_audio"):
        if audio_file:
            # Save the audio file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = os.path.join("uploads", f"{timestamp}_{audio_file.name}")
            with open(audio_path, "wb") as f:
                f.write(audio_file.getbuffer())
            
            # Create message content
            message_content = audio_message if audio_message else f"Sent an audio message: {audio_file.name}"
            
            # Add to chat history
            st.session_state.messages.append({
                "role": "user",
                "content": message_content,
                "file": audio_path  # Using file field for consistency
            })
            
            # Bot response
            bot_response = f"I received your audio file: {audio_file.name}"
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            
            # Rerun the app to update the chat
            st.rerun()
        else:
            st.warning("Please upload an audio file first.")

# Add a clear button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun() 