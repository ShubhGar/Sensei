"""
JIRA Integration for creating issues
"""
import os
import requests
import base64
import asyncio
import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from app.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class JiraIntegration:
    """Service for JIRA integration"""
    
    def __init__(self):
        self.jira_url = os.getenv("JIRA_URL", "").rstrip('/')
        self.jira_username = os.getenv("JIRA_USERNAME", "").strip()
        # Strip quotes if present (common in .env files)
        self.jira_api_token = os.getenv("JIRA_API_TOKEN", "").strip().strip('"').strip("'")
        # Note: Username case may matter - preserve original case from env
        
        if not self.jira_url or not self.jira_username or not self.jira_api_token:
            logger.warning("JIRA credentials not fully configured. JIRA integration may not work.")
            logger.warning(f"JIRA_URL: {'set' if self.jira_url else 'missing'}, JIRA_USERNAME: {'set' if self.jira_username else 'missing'}, JIRA_API_TOKEN: {'set' if self.jira_api_token else 'missing'}")
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
    
    def _format_description(self, description: str) -> Dict[str, Any]:
        """Format description text into JIRA ADF (Atlassian Document Format)
        
        Handles newlines, special characters, and converts plain text to ADF format
        """
        if not description:
            return {
                "type": "doc",
                "version": 1,
                "content": []
            }
        
        # Split by newlines and create paragraphs
        lines = description.split('\n')
        content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - add empty paragraph for spacing
                content.append({
                    "type": "paragraph",
                    "content": []
                })
            else:
                # Non-empty line - create paragraph with text
                content.append({
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": line
                        }
                    ]
                })
        
        # If no content after processing, add at least one paragraph
        if not content:
            content.append({
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description
                    }
                ]
            })
        
        return {
            "type": "doc",
            "version": 1,
            "content": content
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
        # Map common variations to standard JIRA priorities
        priority_map = {
            "Highest": "Highest",
            "High": "High",
            "Medium": "Medium",
            "Normal": "Medium",  # Map Normal to Medium
            "Low": "Low",
            "Lowest": "Lowest",
            "Urgent": "Highest",  # Map Urgent to Highest
            "Critical": "Highest",  # Map Critical to Highest
            "Important": "High",  # Map Important to High
            "urgent": "Highest",  # Case-insensitive
            "critical": "Highest",
            "important": "High"
        }
        
        # Build issue payload
        issue_data = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": summary[:255],  # JIRA summary max length
                "description": self._format_description(description),
                "issuetype": {
                    "name": issue_type
                }
            }
        }
        
        # Add priority if provided
        if priority:
            # Map priority to JIRA priority name (case-insensitive)
            priority_key = priority.strip() if isinstance(priority, str) else str(priority)
            # Try exact match first, then case-insensitive match
            jira_priority = priority_map.get(priority_key) or priority_map.get(priority_key.capitalize()) or priority_map.get(priority_key.lower().capitalize())
            if not jira_priority:
                # Default to Medium if not found, but log a warning
                logger.warning(f"Unknown priority '{priority}', defaulting to 'Medium'. Valid priorities: {list(priority_map.keys())}")
                jira_priority = "Medium"
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
                error_details = []
                if e.response.text:
                    try:
                        error_data = e.response.json()
                        error_messages = error_data.get('errorMessages', [])
                        errors = error_data.get('errors', {})
                        
                        if error_messages:
                            error_details.extend(error_messages)
                        if errors:
                            for field, msg in errors.items():
                                error_details.append(f"{field}: {msg}")
                        
                        if error_details:
                            error_msg = f"JIRA Error ({e.response.status_code}): {', '.join(error_details)}"
                        else:
                            error_msg = f"JIRA Error ({e.response.status_code}): {str(e.response.text[:500])}"
                    except:
                        error_msg = f"JIRA Error ({e.response.status_code}): {e.response.text[:500]}"
                
                # Provide helpful messages for common errors
                if e.response.status_code == 401:
                    if "permission" in error_msg.lower():
                        error_msg = f"Permission denied: You don't have permission to create issues in project '{project_key}'. Please check your JIRA permissions or try a different project."
                    else:
                        error_msg = "Authentication failed. Please check your JIRA credentials (JIRA_USERNAME and JIRA_API_TOKEN)."
                elif e.response.status_code == 404:
                    error_msg = f"Project '{project_key}' not found. Please verify the project key exists and you have access to it."
                elif e.response.status_code == 400:
                    # Enhanced 400 error message with more details
                    if error_details:
                        error_msg = f"Invalid request ({e.response.status_code}): {', '.join(error_details)}. Please check: project key '{project_key}', issue type '{issue_type}', priority '{priority}', and other fields."
                    else:
                        error_msg = f"Invalid request ({e.response.status_code}): {error_msg}. Common issues: invalid priority name (use Highest/High/Medium/Low/Lowest), issue type not available in project, or field validation errors."
                
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
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error fetching JIRA projects: {e.response.status_code}"
                if e.response.text:
                    try:
                        error_data = e.response.json()
                        error_messages = error_data.get('errorMessages', [])
                        if error_messages:
                            error_msg = f"JIRA Error ({e.response.status_code}): {', '.join(error_messages)}"
                    except:
                        error_msg = f"JIRA Error ({e.response.status_code}): {e.response.text[:200]}"
                
                # Provide helpful messages for common errors
                if e.response.status_code == 401:
                    error_msg = "JIRA authentication failed. Please check your JIRA_USERNAME and JIRA_API_TOKEN in .env file"
                elif e.response.status_code == 403:
                    error_msg = "JIRA access forbidden. Please check your JIRA permissions and API token"
                elif e.response.status_code == 404:
                    error_msg = f"JIRA API endpoint not found. Please verify JIRA_URL is correct: {self.jira_url}"
                
                raise ValueError(error_msg)
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Request error fetching JIRA projects: {str(e)}")
            except Exception as e:
                raise ValueError(f"Unexpected error fetching JIRA projects: {str(e)}")
        
        try:
            projects = await asyncio.to_thread(_get_projects_sync)
            if not projects:
                logger.warning("JIRA API returned empty projects list")
                return []
            return [{"key": p.get("key"), "name": p.get("name")} for p in projects]
        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            logger.error(f"Error fetching JIRA projects: {str(e)}", exc_info=True)
            raise ValueError(f"Error fetching JIRA projects: {str(e)}")
    
    async def get_assigned_issues(
        self,
        status: Optional[str] = None,
        max_results: int = 100
    ) -> list:
        """
        Get JIRA issues assigned to the current user
        
        Args:
            status: Filter by status (e.g., "In Progress", "To Do", "Done"). 
                   If None, returns all issues except "Done" by default
            max_results: Maximum number of issues to return (default: 100)
        
        Returns:
            List of issues with key fields
        """
        if not self.jira_url or not self.jira_username or not self.jira_api_token:
            raise ValueError("JIRA credentials not configured")
        
        # Build JQL query
        # Try to use specific assignee ID and project from JIRA_BOARD_URL if available
        jira_board_url = os.getenv("JIRA_BOARD_URL", "")
        assignee_id = None
        project_key = os.getenv("JIRA_PROJECT_KEY", "")  # Optional: filter by project (e.g., "MS")
        
        # Extract assignee ID and project from board URL if provided
        # Format examples:
        #   https://domain.atlassian.net/jira/software/c/projects/MS/boards/404?assignee=712020%3A30247fee-020e-4e67-ba74-40b5aec20ad0
        #   https://domain.atlassian.net/jira/software/c/projects/MS/boards/404/backlog?assignee=5ff44d42692b79011008616e
        if jira_board_url:
            import urllib.parse
            parsed_url = urllib.parse.urlparse(jira_board_url)
            
            # Extract assignee from query params (supports both account ID formats)
            if "assignee=" in jira_board_url:
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if "assignee" in query_params:
                    assignee_id = query_params["assignee"][0]
                    assignee_id = urllib.parse.unquote(assignee_id)
                    logger.info(f"Using assignee ID from JIRA_BOARD_URL: {assignee_id}")
            
            # Extract project from URL path (e.g., /projects/MS/boards/...)
            if "/projects/" in jira_board_url:
                parts = jira_board_url.split("/projects/")
                if len(parts) > 1:
                    project_from_url = parts[1].split("/")[0]
                    if project_from_url:
                        project_key = project_from_url
                        logger.info(f"Extracted project key from JIRA_BOARD_URL: {project_key}")
        
        # Build JQL query parts
        jql_parts = []
        
        # Add project filter if specified
        if project_key:
            jql_parts.append(f"project = {project_key}")
        
        # Add assignee filter
        # Use email/username from JIRA_USERNAME if assignee_id not available
        if assignee_id:
            # Use assignee ID directly (no accountId: prefix needed based on working curl test)
            # Format: assignee=5ff44d42692b79011008616e (simple, no quotes, no accountId: prefix)
            jql_parts.append(f"assignee={assignee_id}")
            logger.info(f"Using assignee ID from board URL: {assignee_id}")
        elif self.jira_username:
            # Use email/username for assignee filter (more reliable than currentUser())
            # JIRA requires quotes around email addresses (they contain @ which is a reserved character)
            # Escape the @ symbol or use quotes properly
            username_escaped = self.jira_username.replace('"', '\\"')  # Escape any quotes in username
            jql_parts.append(f"assignee in (\"{username_escaped}\")")
            logger.info(f"Using email/username for assignee filter: {self.jira_username}")
        else:
            jql_parts.append("assignee = currentUser()")
        
        # Exclude test-related issue types (Test Plan, Test Case, Test Set, Test Execution, Xray Test)
        # These are typically not actionable work items for daily task management
        jql_parts.append("issuetype NOT IN (\"Test Plan\", \"Test Case\", \"Test Set\", \"Test Execution\", \"Xray Test\")")
        
        # Combine JQL parts
        jql = " AND ".join(jql_parts)
        
        # Filter by status - exclude completed/closed/rejected issues by default
        # Only show active work states: To Do, In Progress, Code Review, etc.
        if status:
            # If specific status provided, use it
            jql += f" AND status = \"{status}\""
        else:
            # Default: exclude Done, Closed, Resolved, Released, Risk Accepted, Rejected (show only active work)
            jql += " AND status NOT IN (\"Done\", \"Closed\", \"Resolved\", \"Released\", \"Risk Accepted\", \"Rejected\")"
        
        logger.info(f"JQL Query: {jql}")
        
        # Order by priority (highest first) and updated date (most recent first)
        jql += " ORDER BY priority DESC, updated DESC"
        
        # Use the new /rest/api/3/search/jql endpoint (migrated from deprecated /rest/api/3/search)
        # See: https://developer.atlassian.com/changelog/#CHANGE-2046
        url = f"{self.jira_url}/rest/api/3/search/jql"
        headers = self._get_headers()
        
        # Build request body with JQL and fields
        # Format per JIRA API documentation: POST with JSON body
        # Note: /rest/api/3/search/jql does NOT support startAt parameter
        # Based on working curl test, the minimal format is just {"jql": "..."}
        # But we can include maxResults and fields for better results
        request_body = {
            "jql": jql
        }
        
        # Add optional parameters if needed
        if max_results:
            request_body["maxResults"] = max_results
        # Always include fields for better data
        request_body["fields"] = [
            "summary",
            "status",
            "priority",
            "assignee",
            "created",
            "updated",
            "duedate",
            "issuetype",
            "project",
            "description"
        ]
        
        def _get_issues_sync():
            try:
                # Use POST method to /rest/api/3/search/jql endpoint
                # This is the new endpoint that replaced the deprecated /rest/api/3/search
                logger.debug(f"JIRA API Request | URL: {url} | JQL: {jql[:100]}...")
                response = requests.post(url, headers=headers, json=request_body, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error fetching JIRA issues: {e.response.status_code}"
                if e.response.text:
                    try:
                        error_data = e.response.json()
                        error_messages = error_data.get('errorMessages', [])
                        if error_messages:
                            error_msg = f"JIRA Error ({e.response.status_code}): {', '.join(error_messages)}"
                    except:
                        error_msg = f"JIRA Error ({e.response.status_code}): {e.response.text[:200]}"
                
                if e.response.status_code == 401:
                    error_msg = "JIRA authentication failed. Please check your JIRA_USERNAME and JIRA_API_TOKEN"
                elif e.response.status_code == 403:
                    error_msg = "JIRA access forbidden. Please check your JIRA permissions"
                
                raise ValueError(error_msg)
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Request error fetching JIRA issues: {str(e)}")
            except Exception as e:
                raise ValueError(f"Unexpected error fetching JIRA issues: {str(e)}")
        
        try:
            result = await asyncio.to_thread(_get_issues_sync)
            issues = result.get("issues", [])
            
            # Process and format issues
            formatted_issues = []
            for issue in issues:
                fields = issue.get("fields", {})
                
                # Extract priority with numeric value for sorting
                priority = fields.get("priority")
                priority_name = priority.get("name") if priority else "Unprioritized"
                priority_id = priority.get("id") if priority else "0"
                
                # Calculate urgency score based on priority and due date
                urgency_score = self._calculate_urgency_score(
                    priority_name=priority_name,
                    due_date=fields.get("duedate"),
                    created_date=fields.get("created"),
                    updated_date=fields.get("updated")
                )
                
                # Extract description text from ADF format if present
                description = fields.get("description")
                description_text = ""
                if description:
                    if isinstance(description, dict) and description.get("type") == "doc":
                        # Extract text from ADF format
                        content = description.get("content", [])
                        text_parts = []
                        for block in content:
                            if block.get("type") == "paragraph":
                                para_content = block.get("content", [])
                                for item in para_content:
                                    if item.get("type") == "text":
                                        text_parts.append(item.get("text", ""))
                        description_text = "\n".join(text_parts)
                    elif isinstance(description, str):
                        description_text = description
                
                formatted_issue = {
                    "key": issue.get("key"),
                    "id": issue.get("id"),
                    "summary": fields.get("summary", ""),
                    "status": fields.get("status", {}).get("name", "Unknown"),
                    "priority": priority_name,
                    "priority_id": priority_id,
                    "issue_type": fields.get("issuetype", {}).get("name", "Task"),
                    "project": {
                        "key": fields.get("project", {}).get("key", ""),
                        "name": fields.get("project", {}).get("name", "")
                    },
                    "assignee": fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else None,
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                    "due_date": fields.get("duedate"),
                    "description": description_text,
                    "url": f"{self.jira_url}/browse/{issue.get('key')}",
                    "urgency_score": urgency_score
                }
                formatted_issues.append(formatted_issue)
            
            # Sort by urgency score (highest first), then by priority, then by updated date
            formatted_issues.sort(
                key=lambda x: (
                    -x["urgency_score"],  # Negative for descending order
                    self._priority_sort_value(x["priority"]),
                    x["updated"] or ""  # Most recent first
                ),
                reverse=False  # We want highest urgency first
            )
            
            logger.info(f"Fetched {len(formatted_issues)} JIRA issues assigned to {self.jira_username}")
            return formatted_issues
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error fetching JIRA issues: {str(e)}", exc_info=True)
            raise ValueError(f"Error fetching JIRA issues: {str(e)}")
    
    def _calculate_urgency_score(
        self,
        priority_name: str,
        due_date: Optional[str],
        created_date: Optional[str],
        updated_date: Optional[str]
    ) -> float:
        """
        Calculate urgency score based on priority and due date
        Higher score = more urgent
        
        Returns:
            Float score (0-100)
        """
        # Priority weight (0-50 points)
        priority_weights = {
            "Highest": 50,
            "High": 40,
            "Medium": 25,
            "Low": 10,
            "Lowest": 5,
            "Unprioritized": 0
        }
        priority_score = priority_weights.get(priority_name, 0)
        
        # Due date weight (0-50 points)
        due_date_score = 0
        if due_date:
            try:
                due = datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                now = datetime.datetime.now(due.tzinfo) if due.tzinfo else datetime.datetime.now()
                days_until_due = (due - now).days
                
                if days_until_due < 0:
                    # Overdue - maximum urgency
                    due_date_score = 50
                elif days_until_due == 0:
                    # Due today
                    due_date_score = 45
                elif days_until_due <= 1:
                    # Due tomorrow
                    due_date_score = 40
                elif days_until_due <= 3:
                    # Due in 3 days
                    due_date_score = 30
                elif days_until_due <= 7:
                    # Due in a week
                    due_date_score = 20
                elif days_until_due <= 14:
                    # Due in 2 weeks
                    due_date_score = 10
                else:
                    # More than 2 weeks away
                    due_date_score = 5
            except Exception as e:
                logger.warning(f"Error parsing due date {due_date}: {e}")
        
        return priority_score + due_date_score
    
    def _priority_sort_value(self, priority_name: str) -> int:
        """Get numeric value for priority sorting (lower = higher priority)"""
        priority_order = {
            "Highest": 1,
            "High": 2,
            "Medium": 3,
            "Low": 4,
            "Lowest": 5,
            "Unprioritized": 6
        }
        return priority_order.get(priority_name, 6)

