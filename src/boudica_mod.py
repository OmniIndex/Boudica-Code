"""
Boudica API Module - For use by other Python scripts

This module provides a reusable BoudicaClient class that can be imported and used
by other Python applications to interact with all Boudica API endpoints.

Extracted from src/slm_cgi_client.cpp

Example Usage:
    from boudica_mod import BoudicaClient, BoudicaConfig
    
    config = BoudicaConfig(
        base_url="http://localhost/api/boudica",
        user_id="user@example.com",
        api_key="your_api_key"
    )
    client = BoudicaClient(config)
    
    # Use the client
    response = client.chat("Hello, world!")
    models = client.models()
    agents = client.agents_list()
"""

import requests
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from urllib.parse import urljoin

__version__ = "1.0.0"
__all__ = [
    "BoudicaConfig",
    "BoudicaClient",
    "BoudicaError",
]


class BoudicaError(Exception):
    """Base exception for Boudica API errors"""
    pass


class BoudicaConnectionError(BoudicaError):
    """Connection error with Boudica API"""
    pass


class BoudicaAuthError(BoudicaError):
    """Authentication error with Boudica API"""
    pass


@dataclass
class BoudicaConfig:
    """Configuration for Boudica API client"""
    base_url: str = "http://localhost/api/boudica"
    api_key: Optional[str] = None
    user_id: Optional[str] = None
    timeout: int = 600
    verify_ssl: bool = True


class BoudicaClient:
    """
    Client for interacting with Boudica API endpoints.
    
    This is the main class to use for accessing all Boudica API functionality.
    """
    
    def __init__(self, config: BoudicaConfig = None):
        """
        Initialize the Boudica API client
        
        Args:
            config: BoudicaConfig instance. If None, uses default configuration.
        
        Raises:
            BoudicaError: If configuration is invalid
        """
        self.config = config or BoudicaConfig()
        self.session = requests.Session()
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request to the Boudica API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            **kwargs: Additional arguments to pass to requests
        
        Returns:
            Response JSON as dictionary
        
        Raises:
            BoudicaConnectionError: If connection fails
            BoudicaAuthError: If authentication fails
        """
        # Ensure base_url ends with / for proper urljoin behavior
        base = self.config.base_url.rstrip('/') + '/'
        url = urljoin(base, endpoint.lstrip('/'))
        headers = kwargs.pop('headers', {})
        headers['Content-Type'] = 'application/json'
        
        # Add user_id to params if configured
        if not params:
            params = {}
        if self.config.user_id and 'user_id' not in params:
            params['user_id'] = self.config.user_id
        if self.config.api_key and 'api_key' not in params:
            params['api_key'] = self.config.api_key
        
        try:
            response = self.session.request(
                method, url, json=data, params=params,
                headers=headers, timeout=self.config.timeout,
                verify=self.config.verify_ssl, **kwargs
            )
            
            # Handle authentication errors
            if response.status_code == 401:
                raise BoudicaAuthError(f"Authentication failed: {response.text}")
            
            response.raise_for_status()
            return response.json() if response.text else {"status": "ok"}
            
        except requests.exceptions.Timeout:
            raise BoudicaConnectionError(f"Request timeout after {self.config.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise BoudicaConnectionError(f"Failed to connect to {url}: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise BoudicaConnectionError(f"Request failed: {str(e)}")
    
    # ─── Core Chat & Generation Endpoints ───────────────────────────────────
    
    def chat(self, message: str, user_id: Optional[str] = None,
            model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Send a chat message to the model
        
        Args:
            message: The user's message/prompt
            user_id: User identifier (optional, uses config if not provided)
            model: Model to use (optional)
            **kwargs: Additional parameters (e.g., max_tokens, temperature)
        
        Returns:
            Response dict with model's reply
        
        Example:
            response = client.chat("What is the capital of France?")
            print(response)
        """
        data = {"message": message}
        if model:
            data["model"] = model
        data.update(kwargs)
        params = {"user_id": user_id or self.config.user_id}
        return self._request("POST", "/chat", data=data, params=params)
    
    def generate(self, prompt: str, max_tokens: Optional[int] = None,
                temperature: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate text continuation from prompt
        
        Args:
            prompt: The prompt to continue from
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional parameters
        
        Returns:
            Generated text response
        
        Example:
            response = client.generate("Once upon a time", max_tokens=100)
            print(response)
        """
        data = {"prompt": prompt}
        if max_tokens:
            data["max_tokens"] = max_tokens
        if temperature is not None:
            data["temperature"] = temperature
        data.update(kwargs)
        
        params = {"user_id": self.config.user_id}
        return self._request("POST", "/generate", data=data, params=params)
    
    # ─── System Information Endpoints ───────────────────────────────────────
    
    def health(self) -> Dict[str, Any]:
        """
        Health check endpoint - no authentication required
        
        Returns:
            Health status information
        
        Example:
            status = client.health()
            print(status)
        """
        params = {"user_id": self.config.user_id} if self.config.user_id else None
        return self._request("GET", "/health", params=params)
    
    def models(self) -> Dict[str, Any]:
        """
        List available models
        
        Returns:
            List of available models and their configurations
        
        Example:
            models = client.models()
            for model in models.get('models', []):
                print(model['name'])
        """
        params = {"user_id": self.config.user_id} if self.config.user_id else None
        return self._request("GET", "/models", params=params)
    
    # ─── User Management Endpoints ───────────────────────────────────────────
    
    def user_settings(self, user_id: Optional[str] = None,
                     settings: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get or update user settings
        
        Args:
            user_id: User identifier (optional)
            settings: Settings dict to update (optional, GET if not provided)
        
        Returns:
            User settings or update confirmation
        
        Example:
            # Get settings
            settings = client.user_settings()
            
            # Update settings
            result = client.user_settings(settings={"theme": "dark"})
        """
        method = "POST" if settings else "GET"
        params = {"user_id": user_id or self.config.user_id}
        return self._request(method, "/user_settings", data=settings, params=params)
    
    def users_list(self) -> Dict[str, Any]:
        """
        List all users
        
        Returns:
            List of users in the system
        
        Example:
            users = client.users_list()
            print(len(users.get('users', [])))
        """
        params = {"user_id": self.config.user_id} if self.config.user_id else None
        return self._request("GET", "/users", params=params)
    
    # ─── Message Management Endpoints ────────────────────────────────────────
    
    def messages(self, action: Optional[str] = None,
                message_id: Optional[str] = None,
                **kwargs) -> Dict[str, Any]:
        """
        List or manage messages
        
        Args:
            action: Message action (e.g., 'list', 'get', 'delete')
            message_id: ID of specific message
            **kwargs: Additional parameters
        
        Returns:
            Messages or action result
        
        Example:
            messages = client.messages(action='list')
            message = client.messages(action='get', message_id='123')
        """
        data = {}
        if action:
            data["action"] = action
        if message_id:
            data["message_id"] = message_id
        data.update(kwargs)
        
        params = {"user_id": self.config.user_id} if self.config.user_id else None
        method = "POST" if data else "GET"
        return self._request(method, "/messages", data=data if method == "POST" else None, params=params)
    
    # ─── Shared Chat Endpoints ──────────────────────────────────────────────
    
    def shared_chats(self, action: Optional[str] = None,
                    chat_id: Optional[str] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        List or manage shared chats
        
        Args:
            action: Action (e.g., 'list', 'get', 'share', 'unshare')
            chat_id: ID of specific chat
            **kwargs: Additional parameters
        
        Returns:
            Shared chats or action result
        
        Example:
            chats = client.shared_chats(action='list')
            result = client.shared_chats(action='share', chat_id='123')
        """
        data = {}
        if action:
            data["action"] = action
        if chat_id:
            data["chat_id"] = chat_id
        data.update(kwargs)
        
        params = {"user_id": self.config.user_id} if self.config.user_id else None
        method = "POST" if data else "GET"
        return self._request(method, "/shared_chats", data=data if method == "POST" else None, params=params)
    
    # ─── OAuth Integration Endpoints ────────────────────────────────────────
    
    def oauth_start(self, service: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start OAuth flow for a service
        
        Args:
            service: OAuth service name (e.g., 'sharepoint', 'slack', 'gdrive')
            user_id: User identifier
        
        Returns:
            Authorization URL to redirect user to
        
        Example:
            result = client.oauth_start(service='slack')
            auth_url = result['auth_url']
            # Redirect user to auth_url
        """
        params = {
            "service": service,
            "user_id": user_id or self.config.user_id
        }
        return self._request("GET", "/oauth/start", params=params)
    
    def oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle OAuth callback with authorization code
        
        Args:
            code: Authorization code from provider
            state: CSRF state parameter
        
        Returns:
            HTML page or JSON response with result
        
        Example:
            result = client.oauth_callback(code='auth_code_123', state='state_xyz')
        """
        params = {"code": code, "state": state}
        return self._request("GET", "/oauth/callback", params=params)
    
    def oauth_status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get OAuth connection status for a user
        
        Args:
            user_id: User identifier
        
        Returns:
            List of connected services and available apps
        
        Example:
            status = client.oauth_status()
            print(status['connected'])  # List of connected services
        """
        params = {"user_id": user_id or self.config.user_id}
        return self._request("GET", "/oauth/status", params=params)
    
    def oauth_disconnect(self, service: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Disconnect an OAuth service for a user
        
        Args:
            service: Service name to disconnect
            user_id: User identifier
        
        Returns:
            Disconnection confirmation
        
        Example:
            result = client.oauth_disconnect(service='slack')
        """
        data = {
            "service": service,
            "user_id": user_id or self.config.user_id
        }
        params = {"user_id": user_id or self.config.user_id} if (user_id or self.config.user_id) else None
        return self._request("POST", "/oauth/disconnect", data=data, params=params)
    
    # ─── OAuth Admin Management Endpoints ────────────────────────────────────
    
    def oauth_admin(self, action: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Admin OAuth management endpoint
        
        Actions:
            - 'list_connections': List all user tokens (admin view)
            - 'disconnect': Force disconnect a user (requires user_id, service_name)
            - 'register': Register OAuth app (requires service_name, client_id, etc.)
            - 'list': List registered apps (legacy GET)
        
        Args:
            action: Admin action
            **kwargs: Action-specific parameters
        
        Returns:
            Admin action result
        
        Example:
            # List connections
            conns = client.oauth_admin(action='list_connections')
            
            # Disconnect user
            result = client.oauth_admin(
                action='disconnect',
                user_id='user@example.com',
                service_name='slack'
            )
        """
        data = kwargs.copy()
        if action:
            data["action"] = action
        
        params = {"user_id": self.config.user_id} if self.config.user_id else None
        method = "POST" if action == "disconnect" else "GET"
        
        if method == "GET":
            if not params:
                params = {}
            if action:
                params["action"] = action
            return self._request("GET", "/oauth/admin", params=params)
        else:
            return self._request("POST", "/oauth/admin", data=data, params=params)
    
    def oauth_app_list(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        List registered OAuth app credentials
        
        Args:
            user_id: User/admin identifier
        
        Returns:
            List of registered OAuth apps for the domain
        
        Example:
            apps = client.oauth_app_list()
            for app in apps.get('apps', []):
                print(app['service_name'])
        """
        params = {"user_id": user_id or self.config.user_id}
        return self._request("GET", "/oauth/app/list", params=params)
    
    def oauth_app_register(self, service_name: str, provider: str,
                          client_id: str, client_secret: str,
                          auth_url: str, token_url: str,
                          scope: str, extra_params: Optional[str] = None) -> Dict[str, Any]:
        """
        Register/update an OAuth app credential
        
        Args:
            service_name: Name of the service
            provider: OAuth provider (e.g., 'linkedin', 'github')
            client_id: OAuth client ID
            client_secret: OAuth client secret
            auth_url: Authorization endpoint URL
            token_url: Token endpoint URL
            scope: OAuth scopes required
            extra_params: Additional parameters as JSON
        
        Returns:
            Registration confirmation
        
        Example:
            result = client.oauth_app_register(
                service_name='my_service',
                provider='github',
                client_id='abc123',
                client_secret='secret',
                auth_url='https://github.com/login/oauth/authorize',
                token_url='https://github.com/login/oauth/access_token',
                scope='user:email'
            )
        """
        data = {
            "service_name": service_name,
            "provider": provider,
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_url": auth_url,
            "token_url": token_url,
            "scope": scope
        }
        if extra_params:
            data["extra_params"] = extra_params
        
        params = {"user_id": self.config.user_id} if self.config.user_id else None
        return self._request("POST", "/oauth/app/register", data=data, params=params)
    
    def oauth_app_delete(self, service_name: str) -> Dict[str, Any]:
        """
        Delete an OAuth app credential
        
        Args:
            service_name: Name of the service to delete
        
        Returns:
            Deletion confirmation
        
        Example:
            result = client.oauth_app_delete(service_name='my_service')
        """
        data = {"service_name": service_name}
        params = {"user_id": self.config.user_id} if self.config.user_id else None
        return self._request("POST", "/oauth/app/delete", data=data, params=params)
    
    # ─── Agent Management Endpoints ──────────────────────────────────────────
    
    def agents_list(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        List available agents visible to the user
        
        Args:
            user_id: User identifier
        
        Returns:
            List of available agents (shared + user's private agents)
        
        Example:
            agents = client.agents_list()
            for agent in agents.get('agents', []):
                print(agent['display_name'])
        """
        params = {"user_id": user_id or self.config.user_id}
        return self._request("GET", "/agents/list", params=params)
    
    def agents_user_save(self, agent_name: str, display_name: str,
                        description: str, steps: List[Dict[str, str]],
                        agent_id: int = 0) -> Dict[str, Any]:
        """
        Save a private agent owned by the user
        
        Args:
            agent_name: Internal agent identifier
            display_name: User-friendly display name
            description: Agent description
            steps: List of agent steps
                Each step should have: step_index, description, service,
                query_template, depends_on (optional), loop_over (optional)
            agent_id: 0 for new, >0 for edit
        
        Returns:
            Agent save confirmation with agent_id
        
        Example:
            steps = [
                {
                    "step_index": 1,
                    "description": "Search knowledge base",
                    "service": "search",
                    "query_template": "Find docs about {{input}}"
                }
            ]
            result = client.agents_user_save(
                agent_name='my_agent',
                display_name='My Custom Agent',
                description='Does something useful',
                steps=steps
            )
        """
        data = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "display_name": display_name,
            "description": description,
            "steps": steps
        }
        params = {"user_id": self.config.user_id}
        return self._request("POST", "/agents/user/save", data=data, params=params)
    
    def agents_user_delete(self, agent_id: int) -> Dict[str, Any]:
        """
        Delete a private agent owned by the user
        
        Args:
            agent_id: ID of the agent to delete
        
        Returns:
            Deletion confirmation
        
        Example:
            result = client.agents_user_delete(agent_id=123)
        """
        data = {"agent_id": agent_id}
        params = {"user_id": self.config.user_id}
        return self._request("POST", "/agents/user/delete", data=data, params=params)


def create_client(base_url: str = "http://localhost/api/boudica",
                 api_key: Optional[str] = None,
                 user_id: Optional[str] = None) -> BoudicaClient:
    """
    Convenience function to create a configured BoudicaClient
    
    Args:
        base_url: Base URL for the Boudica API
        api_key: Optional API key for authentication
        user_id: User identifier
    
    Returns:
        Configured BoudicaClient instance
    
    Example:
        client = create_client(user_id='user@example.com')
        response = client.chat("Hello!")
    """
    config = BoudicaConfig(
        base_url=base_url,
        api_key=api_key,
        user_id=user_id
    )
    return BoudicaClient(config)
