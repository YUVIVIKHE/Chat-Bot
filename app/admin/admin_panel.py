import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
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
    page_title="CARA ComplianceBot - Admin Panel",
    page_icon="🔒",
    layout="wide",
)

# API endpoint (change in production)
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if "token" not in st.session_state:
    st.session_state.token = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "username" not in st.session_state:
    st.session_state.username = None
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Dashboard"
if "api_error" not in st.session_state:
    st.session_state.api_error = None
if "users_data" not in st.session_state:
    st.session_state.users_data = None

# Get query parameters
query_params = st.experimental_get_query_params()
if "tab" in query_params and query_params["tab"]:
    selected_tab = query_params["tab"][0]
    if selected_tab in ["Dashboard", "Manage Users", "Manage Q&A", "Chat Logs", "System Settings"]:
        st.session_state.current_tab = selected_tab

# API error callback
def api_error_callback(exception, retry, max_retries):
    """Callback for API errors during retries."""
    st.session_state.api_error = f"API connection error (retry {retry+1}/{max_retries}): {str(exception)}"

def log_api_error(operation: str, exception: Exception):
    """Log API errors with operation context."""
    st.session_state.api_error = f"API error during {operation}: {str(exception)}"

# Custom CSS for error display and improved UI
st.markdown("""
<style>
.api-error {
    background-color: #FFDDDD;
    padding: 0.5rem;
    border-radius: 0.25rem;
    margin-bottom: 1rem;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    white-space: pre-wrap;
    background-color: #F0F2F6;
    border-radius: 4px 4px 0 0;
    gap: 1px;
    padding-top: 10px;
    padding-bottom: 10px;
}
.stTabs [aria-selected="true"] {
    background-color: #4F8BF9 !important;
    color: white !important;
}
.dashboard-card {
    background-color: #ffffff;
    border-radius: 5px;
    padding: 1.5rem;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
}
.status-card {
    padding: 1rem;
    border-radius: 5px;
    margin-bottom: 0.5rem;
}
.status-online {
    background-color: #D5F5E3;
    border-left: 5px solid #2ECC71;
}
.status-offline {
    background-color: #FADBD8;
    border-left: 5px solid #E74C3C;
}
.status-warning {
    background-color: #FEF9E7;
    border-left: 5px solid #F1C40F;
}
.user-table th {
    background-color: #4F8BF9;
    color: white;
    padding: 8px 12px;
}
.user-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #ddd;
}
.user-table tr:nth-child(even) {
    background-color: #f8f9fa;
}
.user-table tr:hover {
    background-color: #eef1f5;
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

# Header
st.title("CARA ComplianceBot - Admin Panel")

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x150.png?text=CARA", width=150)
    st.markdown("### Admin Controls")
    
    if st.session_state.token:
        st.write(f"Logged in as: **{st.session_state.username}**")
        tabs = [
            "Dashboard",
            "Manage Users",
            "Manage Q&A",
            "Chat Logs",
            "System Settings"
        ]
        
        # Use dropdown instead of radio to minimize state changes
        selected_tab = st.selectbox(
            "Navigation",
            tabs,
            index=tabs.index(st.session_state.current_tab)
        )
        
        # Only update if changed
        if selected_tab != st.session_state.current_tab:
            st.session_state.current_tab = selected_tab
            # Update query params instead of rerun
            st.experimental_set_query_params(tab=selected_tab)
        
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.is_admin = False
            st.session_state.username = None
            # Clear query params on logout
            st.experimental_set_query_params()
    else:
        st.info("Please log in to access admin features")

# Login form
if not st.session_state.token:
    st.subheader("Admin Login")
    
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
                    max_retries=5,
                    retry_delay=1,
                    backoff_factor=2,
                    timeout=30,
                    error_callback=lambda e: log_api_error("login", e)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data["access_token"]
                    
                    # Get user info
                    try:
                        user_response = retry_request(
                            method="get",
                            url=f"{API_BASE_URL}/users/me",
                            headers={"Authorization": f"Bearer {st.session_state.token}"},
                            max_retries=5,
                            retry_delay=1,
                            backoff_factor=2,
                            timeout=30,
                            error_callback=lambda e: log_api_error("user info", e)
                        )
                        
                        if user_response.status_code == 200:
                            user_data = user_response.json()
                            st.session_state.is_admin = user_data.get("is_admin", False)
                            st.session_state.username = user_data.get("username")
                            
                            if not st.session_state.is_admin:
                                st.error("You don't have admin privileges.")
                                st.session_state.token = None
                                st.session_state.username = None
                            else:
                                st.success("Login successful!")
                                # Use one-time rerun here for login
                                time.sleep(1)
                                st.experimental_rerun()
                    except Exception as e:
                        st.session_state.api_error = f"Error connecting to server: {str(e)}"
                        st.session_state.token = None
                else:
                    st.error("Invalid username or password.")
            except Exception as e:
                st.session_state.api_error = f"Error connecting to server: {str(e)}"
elif not st.session_state.is_admin:
    # User is logged in but not an admin
    st.error("Admin access required.")
else:
    # Admin is logged in, show selected tab
    
    # Dashboard Tab
    if st.session_state.current_tab == "Dashboard":
        st.header("Dashboard")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.subheader("System Status")
            
            # Function to check system status
            def get_system_status():
                status = {
                    "api_server": {"status": "offline", "details": ""},
                    "database": {"status": "unknown", "details": ""},
                    "last_backup": {"timestamp": "", "status": "unknown"}
                }
                
                # Check API status
                try:
                    api_status = retry_request(
                        method="get",
                        url=f"{API_BASE_URL}/docs",
                        max_retries=5,
                        retry_delay=1,
                        backoff_factor=2,
                        timeout=30,
                        error_callback=lambda e: log_api_error("API status", e)
                    )
                    if api_status.status_code == 200:
                        status["api_server"]["status"] = "online"
                        status["api_server"]["details"] = "API server responding normally"
                    else:
                        status["api_server"]["status"] = "error"
                        status["api_server"]["details"] = f"Error: HTTP {api_status.status_code}"
                except Exception as e:
                    status["api_server"]["status"] = "offline"
                    status["api_server"]["details"] = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
                
                # Check database status through an API call
                try:
                    modules_response = retry_request(
                        method="get",
                        url=f"{API_BASE_URL}/modules",
                        max_retries=5,
                        retry_delay=1,
                        backoff_factor=2,
                        timeout=30,
                        error_callback=lambda e: log_api_error("database status", e)
                    )
                    if modules_response.status_code == 200:
                        status["database"]["status"] = "online"
                        modules_data = modules_response.json()
                        module_count = len(modules_data) if isinstance(modules_data, dict) else 0
                        status["database"]["details"] = f"Connected - {module_count} modules loaded"
                    else:
                        status["database"]["status"] = "error"
                        status["database"]["details"] = f"Error: HTTP {modules_response.status_code}"
                except Exception as e:
                    status["database"]["status"] = "offline"
                    status["database"]["details"] = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
                
                # Get last backup info - this would come from a real API in production
                # For now, use placeholder data
                last_backup_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
                status["last_backup"]["timestamp"] = last_backup_date
                status["last_backup"]["status"] = "success"
                
                return status
            
            # Get status data
            system_status = get_system_status()
            
            # Display statuses with improved visuals
            # API Server status
            status_class = ""
            status_icon = ""
            if system_status["api_server"]["status"] == "online":
                status_class = "status-online"
                status_icon = "✅"
            elif system_status["api_server"]["status"] == "error":
                status_class = "status-warning"
                status_icon = "⚠️"
            else:
                status_class = "status-offline"
                status_icon = "❌"
                
            st.markdown(f'''
            <div class="status-card {status_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{status_icon} API Server:</strong> {system_status["api_server"]["status"].title()}
                    </div>
                    <div style="font-size: 0.8rem;">
                        {system_status["api_server"]["details"]}
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Database status
            status_class = ""
            status_icon = ""
            if system_status["database"]["status"] == "online":
                status_class = "status-online"
                status_icon = "✅"
            elif system_status["database"]["status"] == "error":
                status_class = "status-warning"
                status_icon = "⚠️"
            else:
                status_class = "status-warning"
                status_icon = "⚠️"
                
            st.markdown(f'''
            <div class="status-card {status_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{status_icon} Database:</strong> {system_status["database"]["status"].title()}
                    </div>
                    <div style="font-size: 0.8rem;">
                        {system_status["database"]["details"]}
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Last backup status
            backup_icon = "ℹ️"
            if system_status["last_backup"]["status"] == "success":
                backup_icon = "🔄"
                
            st.markdown(f'''
            <div class="status-card status-online">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{backup_icon} Last Backup:</strong> {system_status["last_backup"]["timestamp"]}
                    </div>
                    <div>
                        <button class="backup-button" onclick="alert('Backup initiated');" 
                            style="background-color: #4F8BF9; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                            Backup Now
                        </button>
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Add a refresh button for statuses
            if st.button("🔄 Refresh Status"):
                st.experimental_rerun()
                
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.subheader("Activity")
            
            # Function to fetch real-time metrics
            def get_dashboard_metrics():
                try:
                    # This would connect to an API endpoint to fetch real metrics in a real implementation
                    # For now, return placeholder data
                    return {
                        "total_users": {"value": 25, "delta": 3},
                        "queries_today": {"value": 142, "delta": 28},
                        "active_sessions": {"value": 7, "delta": -2}
                    }
                except Exception:
                    # Return default values if we can't get real data
                    return {
                        "total_users": {"value": 0, "delta": 0},
                        "queries_today": {"value": 0, "delta": 0},
                        "active_sessions": {"value": 0, "delta": 0}
                    }
            
            # Get metrics
            metrics = get_dashboard_metrics()
            
            # Custom CSS for the metrics display
            st.markdown("""
            <style>
            .metric-container {
                display: flex;
                flex-direction: column;
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: #f8f9fa;
                margin-bottom: 1rem;
                border-left: 4px solid #4F8BF9;
            }
            .metric-value {
                font-size: 2.5rem;
                font-weight: bold;
                margin: 0;
                color: #333;
            }
            .metric-label {
                font-size: 1rem;
                color: #666;
                margin-bottom: 0.5rem;
            }
            .metric-delta {
                font-size: 1rem;
                margin-top: 0.25rem;
            }
            .metric-delta-positive {
                color: #2ECC71;
            }
            .metric-delta-negative {
                color: #E74C3C;
            }
            .metric-delta-neutral {
                color: #7F8C8D;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Display metrics in a grid
            metric_cols = st.columns(3)
            
            # Total Users metric
            with metric_cols[0]:
                delta_class = "metric-delta-positive" if metrics["total_users"]["delta"] >= 0 else "metric-delta-negative"
                delta_symbol = "+" if metrics["total_users"]["delta"] > 0 else ""
                
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-label">Total Users</div>
                    <div class="metric-value">{metrics["total_users"]["value"]}</div>
                    <div class="metric-delta {delta_class}">{delta_symbol}{metrics["total_users"]["delta"]}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Queries Today metric
            with metric_cols[1]:
                delta_class = "metric-delta-positive" if metrics["queries_today"]["delta"] >= 0 else "metric-delta-negative"
                delta_symbol = "+" if metrics["queries_today"]["delta"] > 0 else ""
                
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-label">Queries Today</div>
                    <div class="metric-value">{metrics["queries_today"]["value"]}</div>
                    <div class="metric-delta {delta_class}">{delta_symbol}{metrics["queries_today"]["delta"]}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Active Sessions metric
            with metric_cols[2]:
                delta_class = "metric-delta-positive" if metrics["active_sessions"]["delta"] >= 0 else "metric-delta-negative"
                delta_symbol = "+" if metrics["active_sessions"]["delta"] > 0 else ""
                
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-label">Active Sessions</div>
                    <div class="metric-value">{metrics["active_sessions"]["value"]}</div>
                    <div class="metric-delta {delta_class}">{delta_symbol}{metrics["active_sessions"]["delta"]}</div>
                </div>
                """, unsafe_allow_html=True)
                
            # Refresh button for metrics
            if st.button("🔄 Refresh Metrics"):
                st.experimental_rerun()
                
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("Recent Activity")
        
        # Function to fetch recent activity data
        def get_recent_activity():
            try:
                # This would connect to an API endpoint to fetch real activity in a real implementation
                # For now, return placeholder data that looks realistic
                current_date = datetime.now().strftime("%Y-%m-%d")
                current_time = datetime.now()
                
                # Create timestamps that look realistic (within last hour)
                timestamps = []
                for i in range(8):
                    random_minutes = 5 * i
                    activity_time = current_time - timedelta(minutes=random_minutes)
                    timestamps.append(activity_time.strftime("%H:%M:%S"))
                
                return {
                    "timestamp": [f"{current_date} {t}" for t in timestamps],
                    "user": ["admin", "user123", "user456", "admin", "user789", "user123", "admin", "user456"],
                    "action": ["Updated User", "Login", "Query", "Added Q&A", "Query", "Logout", "Configuration", "Query"],
                    "details": [
                        "Updated user permissions for user789",
                        "Login from 192.168.1.103",
                        "Query about ISO 27001 control A.8.2.3",
                        "Added 2 new Q&A entries to ISO Bot module",
                        "Query about NIST CSF requirements",
                        "Session timeout after 30 minutes",
                        "Updated API configuration settings",
                        "Query about SOC 2 compliance evidence"
                    ],
                    "module": ["Admin", "Auth", "ISO Bot", "Admin", "RiskBot", "Auth", "Admin", "AuditBuddy"]
                }
            except Exception:
                # Return empty data if we can't get real data
                return {
                    "timestamp": [],
                    "user": [],
                    "action": [],
                    "details": [],
                    "module": []
                }
        
        # Get activity data
        activity_data = get_recent_activity()
        
        # Create DataFrame
        if activity_data["timestamp"]:
            df = pd.DataFrame(activity_data)
            
            # Apply styling to the dataframe
            st.markdown("""
            <style>
            .recent-activity {
                margin-top: 1rem;
            }
            .recent-activity-table {
                width: 100%;
                border-collapse: collapse;
            }
            .recent-activity-table th {
                background-color: #4F8BF9;
                color: white;
                padding: 8px 12px;
                text-align: left;
            }
            .recent-activity-table td {
                padding: 8px 12px;
                border-bottom: 1px solid #ddd;
            }
            .recent-activity-table tr:nth-child(even) {
                background-color: #f8f9fa;
            }
            .recent-activity-table tr:hover {
                background-color: #eef1f5;
            }
            .module-badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
                color: white;
            }
            .module-admin {
                background-color: #3498DB;
            }
            .module-auth {
                background-color: #9B59B6;
            }
            .module-iso {
                background-color: #2ECC71;
            }
            .module-risk {
                background-color: #F39C12;
            }
            .module-audit {
                background-color: #E74C3C;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Create and display a custom HTML table
            html_table = '<div class="recent-activity"><table class="recent-activity-table"><thead><tr>'
            
            # Add table headers
            headers = ["Time", "User", "Action", "Module", "Details"]
            for header in headers:
                html_table += f'<th>{header}</th>'
            
            html_table += '</tr></thead><tbody>'
            
            # Add table rows
            for i in range(len(df)):
                html_table += '<tr>'
                
                # Format timestamp to show only time
                timestamp = df['timestamp'][i].split(' ')[1]
                html_table += f'<td>{timestamp}</td>'
                
                # User column
                html_table += f'<td>{df["user"][i]}</td>'
                
                # Action column
                html_table += f'<td>{df["action"][i]}</td>'
                
                # Module column with colored badge
                module = df["module"][i]
                module_class = ""
                if "Admin" in module:
                    module_class = "module-admin"
                elif "Auth" in module:
                    module_class = "module-auth"
                elif "ISO" in module:
                    module_class = "module-iso"
                elif "Risk" in module:
                    module_class = "module-risk"
                elif "Audit" in module:
                    module_class = "module-audit"
                
                html_table += f'<td><span class="module-badge {module_class}">{module}</span></td>'
                
                # Details column
                html_table += f'<td>{df["details"][i]}</td>'
                
                html_table += '</tr>'
            
            html_table += '</tbody></table></div>'
            
            # Display the HTML table
            st.markdown(html_table, unsafe_allow_html=True)
            
            # Add a refresh button
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("🔄 Refresh Activity"):
                    st.experimental_rerun()
            with col2:
                st.markdown('<div style="text-align: right;">Showing most recent 8 activities</div>', unsafe_allow_html=True)
        else:
            st.info("No recent activity data available.")
            
            if st.button("🔄 Refresh Activity Data"):
                st.experimental_rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Manage Users Tab
    elif st.session_state.current_tab == "Manage Users":
        st.header("Manage Users")
        
        user_tabs = st.tabs(["📋 User List", "➕ Add New User"])
        
        with user_tabs[0]:
            st.subheader("Users in Database")
            # Get users from API
            try:
                if st.session_state.users_data is None or st.button("🔄 Refresh User List"):
                    with st.spinner("Loading users from database..."):
                        response = retry_request(
                            method="get",
                            url=f"{API_BASE_URL}/admin/users",
                            headers={"Authorization": f"Bearer {st.session_state.token}"},
                            max_retries=5,
                            retry_delay=1,
                            backoff_factor=2,
                            timeout=30,
                            error_callback=lambda e: log_api_error("fetch users", e)
                        )
                        
                        if response.status_code == 200:
                            users = response.json()
                            st.session_state.users_data = users
                        else:
                            st.error(f"Failed to retrieve users: {response.status_code}")
                            st.session_state.users_data = None
            
                if st.session_state.users_data:
                    users_df = pd.DataFrame(st.session_state.users_data)
                    
                    # Add status indicators and format the dataframe
                    if not users_df.empty:
                        # Format columns for display
                        display_cols = ['username', 'full_name', 'email', 'is_admin', 'disabled']
                        
                        # Ensure all required columns exist
                        for col in display_cols:
                            if col not in users_df.columns:
                                users_df[col] = None
                        
                        # Rename columns for better display
                        users_df = users_df[display_cols]
                        users_df.columns = ['Username', 'Full Name', 'Email', 'Admin', 'Disabled']
                        
                        # Convert boolean columns to readable format
                        users_df['Admin'] = users_df['Admin'].apply(lambda x: '✅' if x else '❌')
                        users_df['Disabled'] = users_df['Disabled'].apply(lambda x: '❌ Active' if not x else '⚠️ Disabled')
                        
                        # Display as an HTML table with custom styling
                        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                        st.write(f"**Total Users: {len(users_df)}**")
                        st.dataframe(users_df, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("No users found in the database.")
                else:
                    st.info("No user data available. Please refresh the user list.")
            except Exception as e:
                st.session_state.api_error = f"Error connecting to server: {str(e)}"
        
        with user_tabs[1]:
            st.subheader("Add New User to Database")
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            with st.form("add_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username*")
                    new_password = st.text_input("Password*", type="password")
                    new_confirm_password = st.text_input("Confirm Password*", type="password")
                with col2:
                    new_fullname = st.text_input("Full Name")
                    new_email = st.text_input("Email")
                    new_is_admin = st.checkbox("Grant Admin Access")
                
                st.markdown("**Required fields*")
                submit_new_user = st.form_submit_button("Add User")
                
                if submit_new_user:
                    if not new_username or not new_password:
                        st.error("Username and password are required.")
                    elif new_password != new_confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            with st.spinner("Adding new user to database..."):
                                response = retry_request(
                                    method="post",
                                    url=f"{API_BASE_URL}/admin/users",
                                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                                    json={
                                        "username": new_username,
                                        "password": new_password,
                                        "full_name": new_fullname,
                                        "email": new_email,
                                        "is_admin": new_is_admin
                                    },
                                    max_retries=5,
                                    retry_delay=1,
                                    backoff_factor=2,
                                    timeout=30,
                                    error_callback=lambda e: log_api_error("add user", e)
                                )
                                
                                if response.status_code == 201:
                                    st.success(f"User {new_username} created successfully!")
                                    # Clear cached user data to force refresh
                                    st.session_state.users_data = None
                                else:
                                    st.error(f"Failed to create user: {response.text}")
                        except Exception as e:
                            st.session_state.api_error = f"Error connecting to server: {str(e)}"
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Manage Q&A Tab
    elif st.session_state.current_tab == "Manage Q&A":
        st.header("Manage Q&A Content")
        
        # Get modules
        try:
            modules_response = retry_request(
                method="get",
                url=f"{API_BASE_URL}/modules",
                max_retries=5,
                retry_delay=1,
                backoff_factor=2,
                timeout=30,
                error_callback=lambda e: log_api_error("fetch modules", e)
            )
            modules = modules_response.json() if modules_response.status_code == 200 else {}
        except:
            modules = {}
        
        qa_tabs = st.tabs(["➕ Add New Q&A", "📊 View Q&A Database"])
        
        with qa_tabs[0]:
            st.subheader("Add New Q&A Pair to Database")
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            
            if not modules:
                st.warning("No modules available. Please check the API connection.")
            else:
                with st.form("add_qa_form"):
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        module_id = st.selectbox(
                            "Select Module*", 
                            options=list(modules.keys()),
                            format_func=lambda x: f"{modules[x]['name']} - {modules[x]['description']}" if x in modules else x
                        )
                    
                    with col2:
                        st.write("Module Description:")
                        if module_id in modules:
                            st.info(modules[module_id]['description'])
                        else:
                            st.info("Please select a module")
                    
                    question = st.text_area("Question*", height=100, 
                                          placeholder="Enter the question that users might ask...")
                    
                    answer = st.text_area("Answer*", height=200,
                                        placeholder="Enter the detailed answer to the question...")
                    
                    metadata = st.text_area("Metadata (JSON)", value="{}", height=100,
                                          help="Additional metadata in JSON format (e.g., related standards, categories)",
                                          placeholder='{"standard": "ISO 27001", "category": "Access Control", "tags": ["security", "compliance"]}')
                    
                    st.markdown("**Required fields*")
                    submit_qa = st.form_submit_button("Add Q&A Pair to Database")
                    
                    if submit_qa:
                        if not question or not answer or not module_id:
                            st.error("Question, answer and module are required.")
                        else:
                            try:
                                # Parse metadata
                                try:
                                    metadata_dict = json.loads(metadata)
                                except json.JSONDecodeError:
                                    st.error("Invalid JSON in metadata field.")
                                    metadata_dict = {}
                                
                                with st.spinner("Adding Q&A pair to database..."):
                                    response = retry_request(
                                        method="post",
                                        url=f"{API_BASE_URL}/admin/qa",
                                        headers={"Authorization": f"Bearer {st.session_state.token}"},
                                        json={
                                            "question": question,
                                            "answer": answer,
                                            "module": module_id,
                                            "metadata": metadata_dict
                                        },
                                        max_retries=5,
                                        retry_delay=1,
                                        backoff_factor=2,
                                        timeout=30,
                                        error_callback=lambda e: log_api_error("add QA pair", e)
                                    )
                                    
                                    if response.status_code == 201:
                                        st.success("Q&A pair added successfully to the database!")
                                    else:
                                        st.error(f"Failed to add Q&A pair: {response.text}")
                            except Exception as e:
                                st.session_state.api_error = f"Error connecting to server: {str(e)}"
            st.markdown('</div>', unsafe_allow_html=True)
        
        with qa_tabs[1]:
            st.subheader("Q&A Database Content")
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            
            # Module filter for viewing Q&A pairs
            if modules:
                all_option = "All Modules"
                module_options = [all_option] + [f"{modules[m]['name']}" for m in modules]
                selected_module = st.selectbox("Filter by Module", options=module_options)
                
                # This would connect to an API endpoint to fetch the Q&A pairs
                # For now, just display a placeholder
                if st.button("🔄 Load Q&A Content"):
                    with st.spinner("Loading Q&A data from database..."):
                        time.sleep(1)  # Simulate API call
                        
                        if selected_module == all_option:
                            st.success("Loaded all Q&A content")
                        else:
                            st.success(f"Loaded Q&A content for {selected_module}")
                        
                        # Placeholder data
                        qa_data = {
                            "Module": ["ISO Bot", "ISO Bot", "RiskBot"],
                            "Question": [
                                "What is ISO 27001?", 
                                "How do I implement control A.8.1.1?", 
                                "What is a risk assessment?"
                            ],
                            "Answer": [
                                "ISO 27001 is an international standard for information security...",
                                "Control A.8.1.1 requires an inventory of assets. To implement...",
                                "A risk assessment is a systematic process of identifying..."
                            ],
                            "Last Updated": ["2023-10-05", "2023-10-12", "2023-11-01"]
                        }
                        
                        qa_df = pd.DataFrame(qa_data)
                        st.dataframe(qa_df, use_container_width=True)
            else:
                st.warning("No modules available. Please check the API connection.")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat Logs Tab
    elif st.session_state.current_tab == "Chat Logs":
        st.header("Chat Logs")
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.info("This feature will show user chat history from the database.")
        
        # Search and filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            st.selectbox("Filter by User", ["All Users", "user123", "user456", "user789"])
        with col2:
            st.selectbox("Filter by Module", ["All Modules", "ISO Bot", "RiskBot", "AuditBuddy"])
        with col3:
            st.date_input("Date Range", value=datetime.now())
        
        if st.button("🔍 Search Logs"):
            # Placeholder for chat logs - in a real implementation, fetch from API
            logs_data = {
                "Timestamp": ["2023-11-01 09:15", "2023-11-01 09:10", "2023-11-01 09:05"],
                "User": ["user123", "user456", "user789"],
                "Module": ["ISO Bot", "RiskBot", "AuditBuddy"],
                "Query": ["What is control A.8.1.1?", "How do I conduct a risk assessment?", "What documents do I need for SOC 2?"],
                "Response Length": [450, 623, 789]
            }
            st.dataframe(pd.DataFrame(logs_data), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # System Settings Tab
    elif st.session_state.current_tab == "System Settings":
        st.header("System Settings")
        
        settings_tabs = st.tabs(["⚙️ API Configuration", "🗄️ Database Maintenance", "🔐 Security Settings"])
        
        with settings_tabs[0]:
            st.subheader("API Configuration")
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            with st.form("api_settings"):
                col1, col2 = st.columns(2)
                
                with col1:
                    api_key = st.text_input("DeepSeek API Key", value="sk-***********", type="password",
                                          help="API key for the DeepSeek language model")
                    max_tokens = st.slider("Max Response Tokens", min_value=100, max_value=2000, value=1024,
                                         help="Maximum number of tokens in generated responses")
                
                with col2:
                    temperature = st.slider("Response Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1,
                                          help="Controls randomness of responses (0=deterministic, 1=creative)")
                    timeout = st.number_input("API Timeout (seconds)", min_value=1, max_value=60, value=10,
                                            help="Maximum time to wait for API response")
                
                save_api = st.form_submit_button("💾 Save API Settings")
                if save_api:
                    with st.spinner("Saving API settings to database..."):
                        time.sleep(1)  # Simulate API call
                        st.success("API settings saved successfully!")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with settings_tabs[1]:
            st.subheader("Database Maintenance")
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Backup")
                backup_options = st.radio("Backup Options", ["Full Backup", "Q&A Data Only", "User Data Only"])
                backup_button = st.button("💾 Create Backup")
                if backup_button:
                    with st.spinner(f"Creating {backup_options.lower()}..."):
                        time.sleep(2)  # Simulate operation
                        st.success(f"{backup_options} created successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            with col2:
                st.markdown("### Maintenance")
                st.warning("⚠️ These operations cannot be undone!")
                maintenance_option = st.selectbox("Select Operation", ["Clear Chat History", "Reset Q&A Database", "Purge Inactive Users"])
                confirm = st.checkbox("I understand this action cannot be undone")
                
                if st.button("Execute Maintenance") and confirm:
                    with st.spinner(f"Executing {maintenance_option}..."):
                        time.sleep(2)  # Simulate operation
                        st.success(f"{maintenance_option} completed successfully")
            st.markdown('</div>', unsafe_allow_html=True)
            
            with settings_tabs[2]:
                st.subheader("Security Settings")
                st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                with st.form("security_settings"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### Authentication")
                        session_timeout = st.slider("Session Timeout (minutes)", min_value=5, max_value=120, value=30,
                                                 help="Time after which an inactive session will expire")
                        password_expiry = st.number_input("Password Expiration (days)", min_value=0, max_value=365, value=90,
                                                      help="Number of days after which passwords expire (0=never)")
                    
                    with col2:
                        st.markdown("### Access Control")
                        failed_attempts = st.number_input("Max Failed Login Attempts", min_value=1, max_value=10, value=5,
                                                     help="Number of failed login attempts before account is locked")
                        st.checkbox("Enforce 2FA for Admin Users", value=True,
                                  help="Require two-factor authentication for administrative access")
                    
                    save_security = st.form_submit_button("🔒 Save Security Settings")
                    if save_security:
                        with st.spinner("Updating security settings..."):
                            time.sleep(1)  # Simulate API call
                            st.success("Security settings updated successfully!")
                st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    # This allows running the admin panel directly
    pass 