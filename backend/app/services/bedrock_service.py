"""
AWS Bedrock service for AI-powered processing
"""
import os
import json
import asyncio
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from app.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)


class BedrockService:
    """Service for AWS Bedrock AI processing"""
    
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        
        # Initialize Bedrock client
        # Try explicit credentials first, then fall back to default credential chain
        try:
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            
            if aws_access_key and aws_secret_key:
                # Use explicit credentials from env
                self.client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
            else:
                # Use default credential chain (IAM role, env vars, ~/.aws/credentials, etc.)
                self.client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.region
                )
            logger.info(
                f"Bedrock client initialized | Region: {self.region} | Model: {self.model_id} | "
                f"Credentials: {'explicit' if aws_access_key and aws_secret_key else 'default chain'}"
            )
        except Exception as e:
            logger.error(
                f"Error initializing Bedrock client | Region: {self.region} | "
                f"Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            self.client = None
    
    def _invoke_claude(self, prompt: str, system_prompt: Optional[str] = None, 
                      temperature: float = 0.3, max_tokens: int = 4096) -> str:
        """Invoke Claude model via Bedrock"""
        if not self.client:
            raise Exception("Bedrock client not initialized")
        
        # Prepare messages
        messages = [{"role": "user", "content": prompt}]
        
        # Prepare request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Validate response structure
            if 'content' not in response_body:
                raise Exception(f"Invalid Bedrock response: missing 'content' field | Response: {response_body}")
            if not response_body['content'] or len(response_body['content']) == 0:
                raise Exception(f"Invalid Bedrock response: empty 'content' array | Response: {response_body}")
            if 'text' not in response_body['content'][0]:
                raise Exception(f"Invalid Bedrock response: missing 'text' field | Response: {response_body}")
            
            return response_body['content'][0]['text']
        except (KeyError, IndexError) as e:
            logger.error(
                f"Bedrock response parsing error | Model: {self.model_id} | "
                f"Error: {type(e).__name__}: {str(e)} | Operation: invoke_claude"
            )
            raise Exception(f"Failed to parse Bedrock response: {str(e)}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(
                f"Bedrock API error | Model: {self.model_id} | Code: {error_code} | "
                f"Message: {error_message} | Operation: invoke_claude"
            )
            raise Exception(f"Bedrock API error ({error_code}): {error_message}")
        except json.JSONDecodeError as e:
            logger.error(
                f"Bedrock JSON decode error | Model: {self.model_id} | "
                f"Error: {str(e)} | Operation: invoke_claude"
            )
            raise Exception(f"Failed to decode Bedrock response as JSON: {str(e)}")
    
    def _invoke_llama(self, prompt: str, system_prompt: Optional[str] = None,
                     temperature: float = 0.3, max_tokens: int = 4096) -> str:
        """Invoke Llama model via Bedrock"""
        if not self.client:
            raise Exception("Bedrock client not initialized")
        
        # Prepare prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = f"User: {prompt}\n\nAssistant:"
        
        body = {
            "prompt": full_prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Validate response structure
            if 'generation' not in response_body:
                raise Exception(f"Invalid Bedrock response: missing 'generation' field | Response: {response_body}")
            
            return response_body['generation']
        except (KeyError, IndexError) as e:
            logger.error(
                f"Bedrock response parsing error | Model: {self.model_id} | "
                f"Error: {type(e).__name__}: {str(e)} | Operation: invoke_llama"
            )
            raise Exception(f"Failed to parse Bedrock response: {str(e)}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(
                f"Bedrock API error | Model: {self.model_id} | Code: {error_code} | "
                f"Message: {error_message} | Operation: invoke_llama"
            )
            raise Exception(f"Bedrock API error ({error_code}): {error_message}")
        except json.JSONDecodeError as e:
            logger.error(
                f"Bedrock JSON decode error | Model: {self.model_id} | "
                f"Error: {str(e)} | Operation: invoke_llama"
            )
            raise Exception(f"Failed to decode Bedrock response as JSON: {str(e)}")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """Generate text using Bedrock model"""
        if not self.client:
            raise Exception("Bedrock client not initialized")
        
        # Determine model type and invoke accordingly
        # Run blocking boto3 calls in thread pool to avoid blocking event loop
        model_type = None
        if "claude" in self.model_id.lower():
            model_type = "claude"
            response = await asyncio.to_thread(
                self._invoke_claude, prompt, system_prompt, temperature, max_tokens
            )
        elif "llama" in self.model_id.lower():
            model_type = "llama"
            response = await asyncio.to_thread(
                self._invoke_llama, prompt, system_prompt, temperature, max_tokens
            )
        else:
            # Default to Claude format
            model_type = "claude (default)"
            response = await asyncio.to_thread(
                self._invoke_claude, prompt, system_prompt, temperature, max_tokens
            )
        
        logger.debug(
            f"Bedrock text generation | Model: {self.model_id} | Type: {model_type} | "
            f"Temperature: {temperature} | Max tokens: {max_tokens} | "
            f"Response length: {len(response)} chars"
        )
        
        # If JSON response format is requested, try to extract JSON
        if response_format and response_format.get("type") == "json_object":
            # Try to extract JSON from response
            try:
                # Look for JSON block in markdown or plain text
                if "```json" in response:
                    json_start = response.find("```json") + 7
                    json_end = response.find("```", json_start)
                    response = response[json_start:json_end].strip()
                elif "```" in response:
                    json_start = response.find("```") + 3
                    json_end = response.find("```", json_start)
                    response = response[json_start:json_end].strip()
                
                # Validate JSON
                json.loads(response)
            except (json.JSONDecodeError, ValueError):
                # If JSON extraction fails, return as-is (model should return valid JSON)
                pass
        
        return response

