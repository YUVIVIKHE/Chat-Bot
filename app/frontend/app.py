import streamlit as st
import requests
import json
from datetime import datetime
import time
from requests.exceptions import RequestException
import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Try to import retry function, or define a fallback version if import fails
try:
    from app.utils.retry import retry_request
except ImportError:
    # Fallback retry function if the import fails
    def retry_request(
        method, 
        url, 
        max_retries=3, 
        retry_delay=1.0, 
        backoff_factor=2.0, 
        headers=None, 
        params=None, 
        data=None, 
        json=None, 
        timeout=10.0, 
        error_callback=None
    ):
        """Fallback retry function if the import fails."""
        method_func = getattr(requests, method.lower())
        delay = retry_delay
        last_exception = None
        
        for retry in range(max_retries):
            try:
                response = method_func(
                    url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json,
                    timeout=timeout
                )
                return response
            except RequestException as e:
                last_exception = e
                if error_callback:
                    error_callback(e, retry, max_retries)
                
                # Only sleep if we're going to retry
                if retry < max_retries - 1:
                    time.sleep(delay)
                    delay *= backoff_factor
        
        # If we get here, all retries failed
        raise last_exception or RequestException("All retries failed")

# Set page configuration
st.set_page_config(
    page_title="CARA ComplianceBot",
    page_icon="🤖",
    layout="wide",
)

# API endpoint (change in production)
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_module" not in st.session_state:
    st.session_state.selected_module = None
if "api_error" not in st.session_state:
    st.session_state.api_error = None
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False
if "retry_count" not in st.session_state:
    st.session_state.retry_count = 0
if "last_query" not in st.session_state:
    st.session_state.last_query = None

# Get query parameters
query_params = st.experimental_get_query_params()
if "module" in query_params and query_params["module"]:
    module_id = query_params["module"][0]
    if module_id == "none":
        st.session_state.selected_module = None
    else:
        st.session_state.selected_module = module_id

# API error callback
def api_error_callback(exception, retry, max_retries):
    """Callback for API errors during retries."""
    st.session_state.api_error = f"API connection error (retry {retry+1}/{max_retries}): {str(exception)}"

# Custom CSS
st.markdown("""
<style>
.chat-message {
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.chat-message.user {
    background-color: #F0F2F6;
    border-left: 4px solid #4F8BF9;
}
.chat-message.assistant {
    background-color: #E8F0FE;
    border-left: 4px solid #34A853;
}
.chat-message .message-content {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
}
.chat-message .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
    margin-right: 1rem;
}
.chat-message .message {
    flex-grow: 1;
    line-height: 1.5;
}
.chat-message .timestamp {
    color: #888;
    font-size: 0.8rem;
    align-self: flex-end;
    margin-top: 0.5rem;
}
.source-badge {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 10px;
    font-size: 0.7rem;
    color: white;
    margin-right: 5px;
}
.source-database {
    background-color: #9C27B0;
}
.source-deepseek {
    background-color: #FF9800;
}
.stButton button {
    width: 100%;
}
.api-error {
    background-color: #FFDDDD;
    padding: 0.5rem;
    border-radius: 0.25rem;
    margin-bottom: 1rem;
}
.chat-container {
    padding: 1rem;
    background-color: #FFFFFF;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
}
.input-container {
    background-color: #FFFFFF;
    padding: 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.typing-indicator {
    display: flex;
    align-items: center;
    margin: 10px 0;
}
.typing-indicator .dot {
    height: 10px;
    width: 10px;
    margin-right: 5px;
    border-radius: 50%;
    background-color: #4F8BF9;
    animation: pulse 1.5s infinite;
}
.typing-indicator .dot:nth-child(2) {
    animation-delay: 0.2s;
}
.typing-indicator .dot:nth-child(3) {
    animation-delay: 0.4s;
}
@keyframes pulse {
    0%, 100% {
        transform: scale(1);
        opacity: 1;
    }
    50% {
        transform: scale(1.2);
        opacity: 0.5;
    }
}
</style>
""", unsafe_allow_html=True)

# Display API error if any
if st.session_state.api_error:
    st.markdown(f"""
    <div class="api-error">
        <strong>Error:</strong> {st.session_state.api_error}
        <br/>Please check if the backend server is running.
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Clear Error"):
        st.session_state.api_error = None
        st.experimental_rerun()

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x150.png?text=CARA", width=150)
    st.title("CARA ComplianceBot")
    
    if st.session_state.token:
        st.write(f"Welcome, **{st.session_state.username}**!")
        
        # Get modules
        try:
            modules_response = retry_request(
                method="get", 
                url=f"{API_BASE_URL}/modules",
                max_retries=3,
                error_callback=api_error_callback
            )
            
            if modules_response.status_code == 200:
                modules = modules_response.json()
                
                st.subheader("Choose a Bot")
                
                # Display module selection using a selectbox instead of buttons
                module_options = [("none", "General ComplianceBot")]
                for module_id, module_info in modules.items():
                    module_options.append((module_id, module_info["name"]))
                
                # Find current selection index
                current_module_id = st.session_state.selected_module if st.session_state.selected_module else "none"
                selected_index = 0
                for i, (mod_id, _) in enumerate(module_options):
                    if mod_id == current_module_id:
                        selected_index = i
                        break
                
                # Display selectbox
                selected_module_name = st.selectbox(
                    "Select a bot",
                    options=[name for _, name in module_options],
                    index=selected_index
                )
                
                # Find the selected module ID
                selected_module_id = "none"
                for mod_id, name in module_options:
                    if name == selected_module_name:
                        selected_module_id = mod_id
                        break
                
                # Update if changed
                if (selected_module_id == "none" and st.session_state.selected_module is not None) or \
                   (selected_module_id != "none" and st.session_state.selected_module != selected_module_id):
                    if selected_module_id == "none":
                        st.session_state.selected_module = None
                    else:
                        st.session_state.selected_module = selected_module_id
                    # Update query parameters instead of rerunning the app
                    st.experimental_set_query_params(module=selected_module_id)
            else:
                st.error("Failed to load modules")
        except Exception as e:
            st.session_state.api_error = f"Error connecting to server: {str(e)}"
        
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.username = None
            st.session_state.chat_history = []
            st.session_state.selected_module = None
            # Clear query params on logout
            st.experimental_set_query_params()
    else:
        st.info("Please log in to use CARA ComplianceBot")
    
    st.markdown("---")
    st.markdown("© 2023 CARA ComplianceBot")
    
    # Admin link
    if st.session_state.token:
        try:
            user_response = retry_request(
                method="get",
                url=f"{API_BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                max_retries=2,
                error_callback=api_error_callback
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                if user_data.get("is_admin", False):
                    st.markdown("---")
                    if st.button("Admin Panel"):
                        # Open admin panel in new tab using direct link instead of rerunning
                        st.markdown(
                            f'<script>window.open("http://localhost:8501", "_blank");</script>',
                            unsafe_allow_html=True
                        )
        except Exception:
            pass  # Already handled by error_callback

# Main content
if not st.session_state.token:
    # Login/Registration section
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.header("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                try:
                    response = retry_request(
                        method="post",
                        url=f"{API_BASE_URL}/token",
                        data={"username": username, "password": password},
                        max_retries=3,
                        error_callback=api_error_callback
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.username = username
                        st.success("Login successful!")
                        time.sleep(1)
                        st.experimental_rerun()
                    else:
                        st.error("Invalid username or password.")
                except Exception as e:
                    st.session_state.api_error = f"Error connecting to server: {str(e)}"
    
    with col2:
        st.header("Welcome to CARA ComplianceBot")
        st.markdown("""
        CARA ComplianceBot is your intelligent, AI-driven chatbot for Governance, Risk, 
        and Compliance (GRC). Get real-time policy assistance, risk workflows, and 
        automated evidence gathering — all through a conversational interface.
        
        **Discover how CARA ComplianceBot can help your organization:**
        
        * 24/7 Compliance Q&A
        * Risk & Control Workflows
        * Audit Readiness Checks
        * Policy Navigation
        * Compliance Awareness
        
        Login to start exploring compliance made simple!
        """)

else:
    # Chat interface
    st.header("CARA ComplianceBot Chat")
    
    # Show selected module name if any
    if st.session_state.selected_module:
        try:
            modules_response = retry_request(
                method="get",
                url=f"{API_BASE_URL}/modules",
                max_retries=2,
                error_callback=api_error_callback
            )
            
            if modules_response.status_code == 200:
                modules = modules_response.json()
                module_info = modules.get(st.session_state.selected_module, {})
                if module_info:
                    st.subheader(f"Currently chatting with: {module_info['name']}")
                    st.markdown(f"*{module_info['description']}*")
        except Exception:
            pass  # Already handled by error_callback
    
    # Display chat history
    chat_container = st.container()
    
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        if not st.session_state.chat_history:
            st.markdown("""
            <div style="text-align: center; padding: 2rem; color: #888;">
                <h3>Start a conversation with CARA ComplianceBot</h3>
                <p>Ask me anything about compliance, risk management, or security!</p>
            </div>
            """, unsafe_allow_html=True)
        
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                with st.container():
                    st.markdown(f"""
                    <div class="chat-message user">
                        <div class="message-content">
                            <img src="https://via.placeholder.com/40/4F8BF9/FFFFFF?text=U" class="avatar" />
                            <div class="message">{chat["content"]}</div>
                        </div>
                        <div class="timestamp">{chat["timestamp"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                with st.container():
                    # Add source badge if available
                    source_html = ""
                    if "source" in chat:
                        badge_class = f"source-{chat['source']}" if chat['source'] in ["database", "deepseek"] else ""
                        source_label = "From Database" if chat['source'] == "database" else "From DeepSeek AI"
                        source_html = f'<span class="source-badge {badge_class}">{source_label}</span>'
                    
                    st.markdown(f"""
                    <div class="chat-message assistant">
                        <div class="message-content">
                            <img src="https://via.placeholder.com/40/34A853/FFFFFF?text=C" class="avatar" />
                            <div class="message">
                                {source_html}
                                {chat["content"]}
                            </div>
                        </div>
                        <div class="timestamp">{chat["timestamp"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Show loading indicator if request is in progress
        if st.session_state.is_loading:
            st.markdown("""
            <div class="chat-message assistant">
                <div class="message-content">
                    <img src="https://via.placeholder.com/40/34A853/FFFFFF?text=C" class="avatar" />
                    <div class="message">
                        <div class="typing-indicator">
                            <div class="dot"></div>
                            <div class="dot"></div>
                            <div class="dot"></div>
                        </div>
                        <div style="font-size: 0.8rem; color: #888; margin-top: 0.5rem;">
                            Thinking... This may take a moment for complex questions.
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add a cancel button for long-running requests
            if st.button("Cancel Request"):
                st.session_state.is_loading = False
                st.session_state.api_error = None
                st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Input area
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    
    # Create columns for the dropdown and input
    col1, col2 = st.columns([1, 4])
    
    # Get modules for dropdown
    with col1:
        try:
            modules_response = retry_request(
                method="get",
                url=f"{API_BASE_URL}/modules",
                max_retries=2,
                error_callback=api_error_callback
            )
            
            if modules_response.status_code == 200:
                modules = modules_response.json()
                
                # Create options list with None option first
                options = [("", "All Modules")]
                for module_id, module_info in modules.items():
                    options.append((module_id, module_info["name"]))
                
                # Extract just the module IDs and names for the selectbox
                module_ids = [opt[0] for opt in options]
                module_names = [opt[1] for opt in options]
                
                # Create selectbox with the current module selected
                selected_index = module_ids.index(st.session_state.selected_module) if st.session_state.selected_module in module_ids else 0
                selected_module_name = st.selectbox(
                    "Bot Module",
                    options=module_names,
                    index=selected_index
                )
                
                # Find the module ID that corresponds to the selected name
                selected_index = module_names.index(selected_module_name)
                st.session_state.selected_module = module_ids[selected_index]
                
        except Exception:
            st.error("Error loading modules")
            st.session_state.selected_module = None
    
    with col2:
        # Input form
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input("Ask your compliance question:", placeholder="e.g., What are the key requirements of ISO 27001?")
            col_a, col_b = st.columns([4, 1])
            with col_b:
                submit_button = st.form_submit_button("📤 Send", disabled=st.session_state.is_loading)
            
            if submit_button and user_input:
                # Set loading state
                st.session_state.is_loading = True
                st.session_state.last_query = {
                    "text": user_input,
                    "module": st.session_state.selected_module
                }
                st.session_state.retry_count = 0
                
                # Add user message to chat history
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": timestamp
                })
                
                st.experimental_rerun()
    
    # Process API calls outside the form to allow rerunning
    if st.session_state.is_loading and st.session_state.last_query:
        try:
            response = retry_request(
                method="post",
                url=f"{API_BASE_URL}/chat",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                json={
                    "query": st.session_state.last_query["text"],
                    "module": st.session_state.last_query["module"]
                },
                max_retries=3,  # Increased from 2 to 3
                timeout=30.0,   # Increased from 10.0 to 30.0 seconds
                retry_delay=1.0, # Increased from 0.5 to 1.0
                backoff_factor=2.0, # Added explicit backoff factor
                error_callback=api_error_callback
            )
            
            if response.status_code == 200:
                data = response.json()
                # Add assistant response to chat history with source
                source = data.get("source", "deepseek")  # Default to deepseek if not specified
                
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": data["response"],
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "source": source
                })
                # Reset loading state and last query
                st.session_state.is_loading = False
                st.session_state.last_query = None
            else:
                error_msg = f"Error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                
                # Check if we should retry
                st.session_state.retry_count += 1
                if st.session_state.retry_count <= 2:  # Allow up to 2 automatic retries
                    time.sleep(2)  # Wait before retrying
                    st.experimental_rerun()  # Try again
                else:
                    # Too many retries, show error
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"I'm sorry, I encountered an error: {error_msg}",
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    st.session_state.is_loading = False
                    st.session_state.last_query = None
        except Exception as e:
            error_message = str(e)
            
            # Check for timeout errors and provide a more user-friendly message
            if "timeout" in error_message.lower():
                error_message = "The server took too long to respond. This may happen with complex queries. Please try again with a simpler question or try again later."
                
                # Check if we should retry
                st.session_state.retry_count += 1
                if st.session_state.retry_count <= 1:  # Allow 1 automatic retry for timeouts
                    time.sleep(2)  # Wait before retrying
                    st.experimental_rerun()  # Try again
                else:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": error_message,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    st.session_state.api_error = f"Error connecting to server: {error_message}"
                    st.session_state.is_loading = False
                    st.session_state.last_query = None
            else:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"I'm sorry, I encountered an error: {error_message}",
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                st.session_state.api_error = f"Error connecting to server: {error_message}"
                st.session_state.is_loading = False
                st.session_state.last_query = None
    
    # Clear chat button
    if len(st.session_state.chat_history) > 0:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.experimental_rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    # This allows running the Streamlit app directly
    pass