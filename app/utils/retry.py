"""
Retry utility for handling API connection issues.
"""
import time
import requests
from requests.exceptions import RequestException
from typing import Callable, Any, Optional, Dict

def retry_request(
    method: str,
    url: str,
    max_retries: int = 2,
    retry_delay: float = 0.5,
    backoff_factor: float = 1.5,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    timeout: float = 5.0,
    error_callback: Optional[Callable] = None
) -> requests.Response:
    """
    Retry a requests API call with exponential backoff.
    
    Args:
        method: HTTP method (get, post, put, etc.)
        url: The URL to call
        max_retries: Maximum number of retries
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay with each retry
        headers: Request headers
        params: Query parameters
        data: Form data
        json: JSON data
        timeout: Request timeout in seconds
        error_callback: Function to call on error
        
    Returns:
        Response object
    
    Raises:
        RequestException: If all retries fail
    """
    method_func = getattr(requests, method.lower())
    delay = retry_delay
    last_exception = None
    
    session = requests.Session()
    
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