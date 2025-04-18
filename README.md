# CARA ComplianceBot

CARA ComplianceBot is an intelligent, AI-driven chatbot for Governance, Risk, and Compliance (GRC). It simplifies frameworks like ISO 27001, NIST CSF, and SOC 2, enabling real-time policy assistance, risk workflows, and automated evidence gathering through a conversational interface.

## Features

- 24/7 Compliance Q&A (e.g., "What is Control A.12.1?")
- Risk & Control Workflows via chat
- Audit Readiness Checklists & Reminders
- Policy Navigation & Evidence Collection
- Micro-training modules & compliance awareness quizzes

## Specialized Modules

1. **ISO Bot** – Automates ISO 27001 FAQs, control help, and evidence collection
2. **RiskBot** – Conversational risk assessment wizard
3. **Compliance Coach** – Micro-training, reminders, and policy query support
4. **AuditBuddy** – Helps orgs get ready for audits by simulating Q&A or fetching documents
5. **Policy Navigator** – Helps users find and understand organizational policies
6. **Security Advisor** – Provides security best practices and guidance

## Setup Instructions

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   Create a `.env` file in the root directory with the following variables:
   ```
   DEEPSEEK_API_KEY=sk-a87b8094c11b4c429f030b9aa5d43832
   ```
4. Run the backend:
   ```
   uvicorn app.backend.main:app --reload
   ```
5. Run the frontend:
   ```
   streamlit run app/frontend/app.py
   ```

## Architecture

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: ChromaDB (Vector Database)
- **AI Model**: DeepSeek

## Authentication & API Access

### Default Credentials

The system comes with two pre-configured accounts:

- **Admin Account**:
  - Username: `admin`
  - Password: `admin`
  - Has full access to all features including the admin panel

- **Regular User Account**:
  - Username: `user`
  - Password: `password`
  - Has access to the chatbot features but not the admin panel

### API Authentication

The API uses OAuth2 with Password Bearer authentication:

1. **Obtaining an Access Token**:
   - Send a POST request to `/token` endpoint
   - Request Body (form data):
     ```
     username: your_username
     password: your_password
     ```
   - Response will include an `access_token` valid for 30 minutes

2. **Using the Access Token**:
   - Include the token in all authenticated API requests
   - Add an Authorization header:
     ```
     Authorization: Bearer your_access_token
     ```

3. **Swagger UI Access**:
   - Access the API documentation at http://localhost:8000/docs
   - Click "Authorize" button at the top right
   - Enter your credentials in the OAuth2 dialog
   - Select "Authorization header" for the client credentials location
   - No client_id or client_secret is needed for password flow

### Admin Panel Access

The admin panel allows administrators to:
- Manage users (view list, add new users)
- Add/edit compliance Q&A content
- Monitor user interactions
- Configure bot behavior

To access the admin panel:
1. Run both backend and frontend servers
2. Navigate to the admin interface at: http://localhost:8501/admin
3. Log in with admin credentials (username: `admin`, password: `admin`)
4. Only users with admin privileges can access this panel

Regular users who attempt to access the admin panel will receive an "Admin access required" error message.

## Admin Panel Features

### User Management

The "Manage Users" tab provides a complete interface to the user database:
- View all users currently in the database with status indicators
- Filter and search functionality for large user bases
- Add new users with validation (username, password, email, admin status)
- Database-focused interface shows only actual users in the system

### Q&A Content Management

The Q&A management system allows admins to:
- Add new question and answer pairs to the knowledge base
- Organize Q&A content by specialized modules
- View existing Q&A content from the database
- Add metadata to improve search and categorization

### System Configuration

The admin panel provides comprehensive system settings:
- API Configuration: Manage AI model settings, response parameters
- Database Maintenance: Backup database, clear history, maintain data integrity
- Security Settings: Configure authentication parameters, session management

## User Management (Admin Only)

Administrators can create new users with the following information:
- Username (required)
- Password (required)
- Full Name
- Email
- Admin Access (checkbox to grant admin privileges)

New users can immediately use their credentials to access the system based on their assigned privileges. 