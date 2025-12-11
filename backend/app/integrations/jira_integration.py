"""
JIRA Integration for creating issues
"""
import os
import requests
import base64
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from app.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class JiraIntegration:
    """Service for JIRA integration"""
    
    def __init__(self):
        self.jira_url = os.getenv("JIRA_URL", "").rstrip('/')
        self.jira_username = os.getenv("JIRA_USERNAME", "")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN", "")
        
        if not self.jira_url or not self.jira_username or not self.jira_api_token:
            logger.warning("JIRA credentials not fully configured. JIRA integration may not work.")
        else:
            logger.info(f"JIRA integration initialized | URL: {self.jira_url} | User: {self.jira_username}")
    
    def _get_auth_header(self) -> str:
        """Generate Basic Auth header for JIRA API"""
        credentials = f"{self.jira_username}:{self.jira_api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for JIRA API requests"""
        return {
            "Authorization": self._get_auth_header(),
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        labels: Optional[list] = None,
        assignee: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a JIRA issue
        
        Args:
            project_key: JIRA project key (e.g., "PROJ")
            summary: Issue summary/title
            description: Issue description
            issue_type: Issue type (Task, Bug, Story, Epic, Subtask)
            priority: Priority (Highest, High, Medium, Low, Lowest)
            labels: List of labels
            assignee: Assignee username/account ID
        
        Returns:
            Dict with created issue information
        """
        if not self.jira_url or not self.jira_username or not self.jira_api_token:
            raise ValueError("JIRA credentials not configured. Please set JIRA_URL, JIRA_USERNAME, and JIRA_API_TOKEN in .env file")
        
        # Map priority names to JIRA priority names
        # JIRA typically uses: Highest, High, Medium, Low, Lowest
        # "Normal" is not a standard JIRA priority, so we'll map it to Medium
        priority_map = {
            "Highest": "Highest",
            "High": "High",
            "Medium": "Medium",
            "Normal": "Medium",  # Map Normal to Medium
            "Low": "Low",
            "Lowest": "Lowest"
        }
        
        # Build issue payload
        issue_data = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": summary[:255],  # JIRA summary max length
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": issue_type
                }
            }
        }
        
        # Add priority if provided
        if priority:
            # Map priority to JIRA priority name
            jira_priority = priority_map.get(priority, "Medium")  # Default to Medium if not found
            issue_data["fields"]["priority"] = {
                "name": jira_priority
            }
        
        # Add labels if provided
        if labels and len(labels) > 0:
            issue_data["fields"]["labels"] = labels
        
        # Add assignee if provided
        if assignee:
            issue_data["fields"]["assignee"] = {
                "name": assignee
            }
        
        # Make API request (run in thread pool to avoid blocking)
        url = f"{self.jira_url}/rest/api/3/issue"
        headers = self._get_headers()
        
        def _create_issue_sync():
            try:
                response = requests.post(url, json=issue_data, headers=headers, timeout=30)
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error creating JIRA issue: {e.response.status_code}"
                if e.response.text:
                    try:
                        error_data = e.response.json()
                        error_messages = error_data.get('errorMessages', [])
                        if error_messages:
                            error_msg = f"JIRA Error ({e.response.status_code}): {', '.join(error_messages)}"
                        else:
                            error_msg = f"JIRA Error ({e.response.status_code}): {str(e.response.text[:200])}"
                    except:
                        error_msg = f"JIRA Error ({e.response.status_code}): {e.response.text[:200]}"
                
                # Provide helpful messages for common errors
                if e.response.status_code == 401:
                    if "permission" in error_msg.lower():
                        error_msg = f"Permission denied: You don't have permission to create issues in project '{project_key}'. Please check your JIRA permissions or try a different project."
                    else:
                        error_msg = "Authentication failed. Please check your JIRA credentials (JIRA_USERNAME and JIRA_API_TOKEN)."
                elif e.response.status_code == 404:
                    error_msg = f"Project '{project_key}' not found. Please verify the project key exists and you have access to it."
                elif e.response.status_code == 400:
                    error_msg = f"Invalid request: {error_msg}. Please check the project key, issue type, and other fields."
                
                return {"success": False, "error": error_msg}
            except requests.exceptions.RequestException as e:
                return {"success": False, "error": f"Request error creating JIRA issue: {str(e)}"}
            except Exception as e:
                return {"success": False, "error": f"Unexpected error creating JIRA issue: {str(e)}"}
        
        try:
            result = await asyncio.to_thread(_create_issue_sync)
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            data = result.get("data")
            issue_key = data.get("key")
            issue_id = data.get("id")
            issue_url = f"{self.jira_url}/browse/{issue_key}"
            
            logger.info(f"Successfully created JIRA issue | Key: {issue_key} | ID: {issue_id}")
            
            return {
                "success": True,
                "issue_key": issue_key,
                "issue_id": issue_id,
                "issue_url": issue_url,
                "message": f"JIRA issue {issue_key} created successfully"
            }
        except ValueError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error creating JIRA issue: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
    
    async def get_projects(self) -> list:
        """Get list of accessible JIRA projects"""
        if not self.jira_url or not self.jira_username or not self.jira_api_token:
            raise ValueError("JIRA credentials not configured")
        
        url = f"{self.jira_url}/rest/api/3/project"
        headers = self._get_headers()
        
        def _get_projects_sync():
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        
        try:
            projects = await asyncio.to_thread(_get_projects_sync)
            return [{"key": p.get("key"), "name": p.get("name")} for p in projects]
        except Exception as e:
            logger.error(f"Error fetching JIRA projects: {str(e)}", exc_info=True)
            raise ValueError(f"Error fetching JIRA projects: {str(e)}")

