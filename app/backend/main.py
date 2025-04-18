from fastapi import FastAPI, Depends, HTTPException, status, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
import asyncio
import hashlib
import time

from app.auth.auth import (
    Token, User, authenticate_user, create_access_token,
    get_current_active_user, get_current_admin_user, fake_users_db, get_password_hash
)
from app.models.ai_model import ai_model
from app.database.chroma_db import chroma_db
from app.config.settings import ACCESS_TOKEN_EXPIRE_MINUTES, BOT_MODULES

# Initialize FastAPI app
app = FastAPI(title="CARA ComplianceBot API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for pending responses to prevent duplicate processing
active_requests = {}
# In-memory cache for background task results
background_task_results = {}

# Pydantic models
class QueryRequest(BaseModel):
    query: str
    module: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    module: Optional[str] = None
    source: Optional[str] = "deepseek"  # Default source is DeepSeek
    task_id: Optional[str] = None  # Task ID for long-running tasks

class ChatHistory(BaseModel):
    user_id: str
    query: str
    response: str
    module: Optional[str] = None
    timestamp: datetime

class AdminQAPair(BaseModel):
    question: str
    answer: str
    module: str
    metadata: Dict[str, Any] = {}

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: bool = False

# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Chat routes
@app.post("/chat", response_model=QueryResponse)
async def chat_with_bot(
    query_request: QueryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    # Generate a unique request ID based on user, query and module
    request_hash = _generate_request_hash(current_user.username, query_request.query, query_request.module)
    
    # Check if this request is already being processed
    if request_hash in active_requests:
        # Check if the previous request has completed
        cached_result = active_requests[request_hash]
        if cached_result.get("completed", False):
            # Remove old requests after 5 minutes to prevent memory leaks
            if (datetime.now() - cached_result.get("timestamp", datetime.now())).total_seconds() > 300:
                del active_requests[request_hash]
            else:
                return cached_result["response"]
    
    # First check if this exact query exists in our user_queries collection
    existing_query = await run_in_threadpool(lambda: check_existing_query(query_request.query, query_request.module))
    
    if existing_query:
        # We found a matching query, return the stored response
        response_data = {
            "response": existing_query["response"],
            "module": query_request.module,
            "source": "database"  # Indicate the response came from the database
        }
        # Cache this response
        active_requests[request_hash] = {
            "response": response_data,
            "completed": True,
            "timestamp": datetime.now()
        }
        return response_data
    
    # Check if we need to use a background task
    # For potentially long-running requests, use a background task
    # Generate a unique task ID
    task_id = f"task_{int(time.time() * 1000)}_{hash(request_hash)}"
    
    try:
        # If we get here, this is a new query - search for relevant context
        context = []
        if query_request.module:
            collection_name = get_collection_name_for_module(query_request.module)
            results = await run_in_threadpool(lambda: chroma_db.query_collection(collection_name, query_request.query, n_results=3))
            if results and 'documents' in results and results['documents']:
                context = results['documents'][0]
        
        # Start the background task
        background_tasks.add_task(
            generate_ai_response_task,
            task_id=task_id,
            query=query_request.query,
            context=context,
            module=query_request.module,
            username=current_user.username
        )
        
        # Return a placeholder response
        return {
            "response": "I'm processing your question. Please wait a moment...",
            "module": query_request.module,
            "source": "processing",
            "task_id": task_id
        }
    except Exception as e:
        # Log the error and re-raise
        print(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# New endpoint to check background task status
@app.get("/task_status/{task_id}", response_model=Optional[QueryResponse])
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    if task_id in background_task_results:
        result = background_task_results[task_id]
        if result.get("completed", False):
            # Task is complete, return the result
            response = {
                "response": result["response"],
                "module": result["module"],
                "source": result["source"]
            }
            # Clean up old tasks after 5 minutes
            if (datetime.now() - result.get("timestamp", datetime.now())).total_seconds() > 300:
                del background_task_results[task_id]
            return response
        else:
            # Task is still running
            return {
                "response": "Still processing your request...",
                "module": None,
                "source": "processing",
                "task_id": task_id
            }
    else:
        # Task not found
        raise HTTPException(status_code=404, detail="Task not found")

@app.get("/modules", response_model=Dict[str, Dict[str, str]])
async def get_bot_modules():
    return BOT_MODULES

# Admin routes
@app.post("/admin/qa", status_code=status.HTTP_201_CREATED)
async def add_qa_pair(
    qa_pair: AdminQAPair,
    current_user: User = Depends(get_current_admin_user)
):
    collection_name = get_collection_name_for_module(qa_pair.module)
    document = qa_pair.question + "\n" + qa_pair.answer
    chroma_db.add_documents(
        collection_name=collection_name,
        documents=[document],
        metadatas=[qa_pair.metadata],
        ids=[f"qa_{datetime.now().timestamp()}"]
    )
    return {"status": "success", "message": "QA pair added successfully"}

@app.post("/admin/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_admin_user)
):
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    hashed_password = get_password_hash(user.password)
    fake_users_db[user.username] = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": hashed_password,
        "disabled": False,
        "is_admin": user.is_admin
    }
    
    return {"status": "success", "username": user.username}

@app.get("/admin/users", response_model=List[User])
async def list_users(current_user: User = Depends(get_current_admin_user)):
    users = []
    for username, user_data in fake_users_db.items():
        user_dict = user_data.copy()
        user_dict.pop("hashed_password")
        users.append(User(**user_dict))
    return users

# Helper functions
def get_collection_name_for_module(module: str) -> str:
    """Get the collection name for a specific module."""
    module_collection_map = {
        "1": "iso_bot",
        "2": "risk_bot",
        "3": "compliance_coach",
        "4": "audit_buddy",
        "5": "policy_navigator",
        "6": "security_advisor"
    }
    return module_collection_map.get(module, "qa_pairs")

def store_chat_history(user_id: str, query: str, response: str, module: Optional[str] = None, source: str = "deepseek"):
    """
    Store chat history in ChromaDB.
    
    Args:
        user_id: The user ID
        query: The user's question
        response: The bot's response
        module: The module the question was for
        source: Where the answer came from (database or deepseek)
    """
    metadata = {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "module": module,
        "source": source
    }
    
    chroma_db.add_documents(
        collection_name="user_queries",
        documents=[query + "\n" + response],
        metadatas=[metadata],
        ids=[f"chat_{datetime.now().timestamp()}"]
    )

def check_existing_query(query: str, module: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Check if a nearly identical query exists in the database.
    
    Args:
        query: The user's question
        module: The module the question is for
        
    Returns:
        Dictionary with the response if found, None otherwise
    """
    try:
        # Search in user_queries collection with high similarity threshold
        results = chroma_db.query_collection(
            collection_name="user_queries",
            query_text=query,
            n_results=1
        )
        
        if not results or not results['documents'] or not results['documents'][0]:
            return None
            
        # Check if this is a highly similar match (could add more sophisticated matching here)
        similarity_score = results.get('distances', [[0]])[0][0] if 'distances' in results else 1.0
        
        # If similarity is high enough, consider it a match
        # ChromaDB returns distance, not similarity, so smaller is better (0 is exact match)
        if similarity_score < 0.25:  # This threshold can be adjusted
            document = results['documents'][0][0]
            # Parse stored document - format is "query\nresponse"
            parts = document.split('\n', 1)
            
            # Only return if we have the response part
            if len(parts) > 1:
                response = parts[1]
                
                # Additional check: if module specified, verify the module matches
                if module:
                    metadata = results['metadatas'][0][0] if 'metadatas' in results and results['metadatas'][0] else {}
                    stored_module = metadata.get('module')
                    
                    # If modules don't match, don't reuse the answer
                    if stored_module and stored_module != module:
                        return None
                
                return {
                    "response": response,
                    "query": parts[0]
                }
    
    except Exception as e:
        # Log the error but continue (don't break the bot over a matching issue)
        print(f"Error checking existing query: {str(e)}")
    
    return None

def _generate_request_hash(username: str, query: str, module: Optional[str] = None) -> str:
    """Generate a unique hash for a request to use for caching/deduplication."""
    # Combine all parameters that make this request unique
    request_string = f"{username}:{query}:{module or 'none'}"
    # Create a hash
    return hashlib.md5(request_string.encode()).hexdigest()

# Background task for generating AI responses
async def generate_ai_response_task(
    task_id: str,
    query: str,
    context: List[Any],
    module: Optional[str],
    username: str
):
    try:
        # Set a timeout for the DeepSeek API call
        try:
            # Generate response using DeepSeek AI model for new queries
            response = await asyncio.wait_for(
                ai_model.generate_response(
                    query=query,
                    context=context,
                    module=module
                ),
                timeout=60.0  # 60 second timeout
            )
        except asyncio.TimeoutError:
            # If the API call times out, use the fallback response
            response = {
                "success": True,
                "response": f"I apologize for the delay in responding to your question about '{query}'. Our AI service is experiencing high load at the moment. Please try again in a few moments, or consider rephrasing your question to be more specific.",
                "usage": {"total_tokens": 50}
            }
            
        # Store the query and response once we have it
        if response.get("success", False):
            await run_in_threadpool(lambda: store_chat_history(
                user_id=username, 
                query=query, 
                response=response["response"], 
                module=module,
                source="deepseek"
            ))
            
            # Store the result
            background_task_results[task_id] = {
                "response": response["response"],
                "module": module,
                "source": "deepseek",
                "completed": True,
                "timestamp": datetime.now()
            }
        else:
            # Store the error
            background_task_results[task_id] = {
                "response": "Failed to generate response",
                "module": module,
                "source": "error",
                "completed": True,
                "timestamp": datetime.now()
            }
    except Exception as e:
        # Store the error
        background_task_results[task_id] = {
            "response": f"Error processing request: {str(e)}",
            "module": module,
            "source": "error",
            "completed": True,
            "timestamp": datetime.now()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 