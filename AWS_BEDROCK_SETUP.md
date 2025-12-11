# AWS Bedrock Integration Setup Guide

This guide will help you integrate AWS Bedrock into your PayU Sensei application to replace or complement OpenAI for AI-powered features like MOM generation, email summarization, and Teams analysis.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [AWS Account Setup](#aws-account-setup)
- [Enable Bedrock Models](#enable-bedrock-models)
- [IAM Configuration](#iam-configuration)
- [Installation](#installation)
- [Code Integration](#code-integration)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Model Selection Guide](#model-selection-guide)
- [Cost Considerations](#cost-considerations)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

---

## Overview

AWS Bedrock is a fully managed service that provides access to foundation models from leading AI companies (Anthropic, Meta, Amazon, etc.) through a unified API. This integration allows you to:

- **Use multiple AI models** (Claude, Llama, Titan, etc.) without vendor lock-in
- **Reduce costs** compared to OpenAI for many use cases
- **Maintain data privacy** with AWS's security and compliance features
- **Scale automatically** with AWS infrastructure

### Supported Models

- **Anthropic Claude** (Claude 3 Opus, Sonnet, Haiku)
- **Meta Llama** (Llama 2, Llama 3)
- **Amazon Titan** (Titan Text, Titan Embeddings)
- **AI21 Labs Jurassic** (Jurassic-2 Ultra, Mid, Grande)
- **Cohere** (Command, Command Light, Embed)
- **Stability AI** (Stable Diffusion)

---

## Prerequisites

Before you begin, ensure you have:

1. **AWS Account** - An active AWS account with billing enabled
2. **AWS CLI** - Installed and configured (optional, but recommended)
3. **Python 3.9+** - Already installed for your backend
4. **AWS Access** - Permissions to:
   - Access AWS Bedrock
   - Create/configure IAM roles and policies
   - Enable model access in Bedrock

### Verify AWS CLI Installation

```bash
aws --version
# Should show: aws-cli/2.x.x

# Configure AWS credentials (if not already done)
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter your default region (e.g., us-east-1)
# Enter default output format (json)
```

---

## AWS Account Setup

### Step 1: Access AWS Bedrock Console

1. Log in to the [AWS Management Console](https://console.aws.amazon.com/)
2. Navigate to **AWS Bedrock** service
   - You can search for "Bedrock" in the search bar
   - Or go directly to: `https://console.aws.amazon.com/bedrock/`

### Step 2: Verify Region Availability

AWS Bedrock is available in specific regions. Ensure you're using one of these:

- **US East (N. Virginia)** - `us-east-1` ✅ Recommended
- **US West (Oregon)** - `us-west-2`
- **Asia Pacific (Tokyo)** - `ap-northeast-1`
- **Europe (Frankfurt)** - `eu-central-1`

**Note**: Model availability varies by region. Check the Bedrock console for available models in your region.

---

## Enable Bedrock Models

### Step 1: Request Model Access

1. In the AWS Bedrock console, click on **"Model access"** in the left sidebar
2. You'll see a list of available foundation models
3. For each model you want to use, click **"Request model access"**
4. Review and accept the terms of use
5. Wait for approval (usually instant for most models, but can take up to 24 hours)

### Step 2: Recommended Models to Enable

For this application, we recommend enabling:

**Primary Models:**
- ✅ **Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`) - Best balance of performance and cost
- ✅ **Claude 3 Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`) - Fastest and cheapest
- ✅ **Llama 3 70B** (`meta.llama3-70b-instruct-v1:0`) - Open-source alternative

**Optional Models:**
- **Claude 3 Opus** (`anthropic.claude-3-opus-20240229-v1:0`) - Most capable, higher cost
- **Titan Text G1** (`amazon.titan-text-express-v1`) - Amazon's model
- **Jurassic-2 Ultra** (`ai21.j2-ultra-v1`) - AI21 Labs model

### Step 3: Verify Model Access

After requesting access, verify models are available:

```bash
# Using AWS CLI
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?modelId==`anthropic.claude-3-sonnet-20240229-v1:0`]'

# Or check in the Bedrock console under "Model access"
```

---

## IAM Configuration

### Step 1: Create IAM User (Recommended for Development)

1. Go to **IAM Console** → **Users** → **Create user**
2. Enter username: `bedrock-service-user`
3. Select **"Provide user access to the AWS Management Console"** (optional)
4. Click **Next**

### Step 2: Attach Bedrock Policy

1. Click **"Add permissions"**
2. Select **"Attach policies directly"**
3. Search for and select: **`AmazonBedrockFullAccess`**
   - **Note**: For production, create a custom policy with least privilege (see below)

4. Click **Next** → **Create user**

### Step 3: Create Access Keys

1. Click on the newly created user
2. Go to **"Security credentials"** tab
3. Click **"Create access key"**
4. Select **"Application running outside AWS"** (for local development)
5. Click **"Next"** → **"Create access key"**
6. **IMPORTANT**: Copy both:
   - **Access Key ID**
   - **Secret Access Key** (shown only once!)

Save these credentials securely - you'll need them for environment variables.

### Step 4: Custom IAM Policy (Production Recommended)

For production, create a custom policy with minimal permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-70b-instruct-v1:0"
      ]
    }
  ]
}
```

**Steps to create custom policy:**
1. Go to **IAM** → **Policies** → **Create policy**
2. Click **JSON** tab
3. Paste the policy above (adjust region and model ARNs as needed)
4. Click **Next** → Name it: `BedrockInvokePolicy`
5. Click **Create policy**
6. Attach this policy to your IAM user/role instead of `AmazonBedrockFullAccess`

---

## Installation

### Step 1: Install AWS SDK for Python (boto3)

The AWS SDK for Python (boto3) is required to interact with Bedrock:

```bash
cd backend

# Activate virtual environment (if using one)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install boto3
pip install boto3

# Or add to requirements.txt
echo "boto3>=1.34.0" >> requirements.txt
pip install -r requirements.txt
```

### Step 2: Verify Installation

```bash
python -c "import boto3; print(boto3.__version__)"
# Should print: 1.34.0 or higher
```

---

## Code Integration

### Step 1: Update AI Service

We'll modify the `ai_service.py` to support both OpenAI and AWS Bedrock. Here's how to integrate:

**Option A: Replace OpenAI with Bedrock** (Recommended for cost savings)

**Option B: Support Both Providers** (Recommended for flexibility)

We'll implement Option B to allow switching between providers.

### Step 2: Create Bedrock Service Helper

Create a new file `backend/app/services/bedrock_service.py`:

```python
"""
AWS Bedrock service for AI-powered processing
"""
import os
import json
import boto3
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class BedrockService:
    """Service for AWS Bedrock AI processing"""
    
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        
        # Initialize Bedrock client
        try:
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=self.region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            print(f"Bedrock client initialized for region: {self.region}, model: {self.model_id}")
        except Exception as e:
            print(f"Error initializing Bedrock client: {e}")
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
            return response_body['content'][0]['text']
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise Exception(f"Bedrock API error ({error_code}): {error_message}")
    
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
            return response_body['generation']
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise Exception(f"Bedrock API error ({error_code}): {error_message}")
    
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
        if "claude" in self.model_id.lower():
            response = self._invoke_claude(prompt, system_prompt, temperature, max_tokens)
        elif "llama" in self.model_id.lower():
            response = self._invoke_llama(prompt, system_prompt, temperature, max_tokens)
        else:
            # Default to Claude format
            response = self._invoke_claude(prompt, system_prompt, temperature, max_tokens)
        
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
```

### Step 3: Update AI Service to Support Bedrock

Modify `backend/app/services/ai_service.py` to support both providers:

```python
# Add at the top
from app.services.bedrock_service import BedrockService

# Update __init__ method
def __init__(self):
    self.api_key = os.getenv("OPENAI_API_KEY")
    self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    self.use_bedrock = os.getenv("USE_BEDROCK", "false").lower() == "true"
    
    # Initialize clients
    self.client = OpenAI(api_key=self.api_key) if self.api_key and not self.use_bedrock else None
    self.bedrock_service = BedrockService() if self.use_bedrock else None
```

Then update each method to use Bedrock when enabled. Example for `generate_mom`:

```python
async def generate_mom(
    self,
    transcript: str,
    session_id: str,
    duration: Optional[str] = None
) -> Dict[str, Any]:
    """Generate Minutes of Meeting from transcript"""
    
    prompt = f"""Analyze the following meeting transcript and generate structured Minutes of Meeting (MOM).

Transcript:
{transcript}

Please provide:
1. A concise summary (2-3 paragraphs)
2. Key decisions made (list format)
3. Action items with owners and deadlines (if mentioned)
4. Key discussion points (bullet points)
5. List of attendees (if identifiable)

Format the response as JSON with the following structure:
{{
    "summary": "...",
    "decisions": [{{"decision": "...", "context": "..."}}],
    "action_items": [{{"task": "...", "owner": "...", "deadline": "...", "priority": "..."}}],
    "key_points": ["...", "..."],
    "attendees": ["...", "..."]
}}"""

    system_prompt = "You are an expert at analyzing meetings and generating structured minutes."

    try:
        if self.use_bedrock and self.bedrock_service:
            # Use Bedrock
            response_text = await self.bedrock_service.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            mom_data = json.loads(response_text)
        elif self.client:
            # Use OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            mom_data = json.loads(response.choices[0].message.content)
        else:
            # Fallback
            mom_data = self._generate_mom_fallback(transcript)
        
        mom_data["session_id"] = session_id
        mom_data["duration"] = duration
        return mom_data
    except Exception as e:
        print(f"Error generating MOM: {e}")
        mom_data = self._generate_mom_fallback(transcript)
        mom_data["session_id"] = session_id
        mom_data["duration"] = duration
        return mom_data
```

**Note**: Apply similar changes to all other methods (`generate_faqs`, `generate_email_draft`, `detect_risks`, etc.)

---

## Environment Variables

### Step 1: Update env.example

Add the following to `backend/env.example`:

```bash
# AWS Bedrock Configuration
# Set to "true" to use AWS Bedrock instead of OpenAI
USE_BEDROCK=false
# AWS Region for Bedrock (e.g., us-east-1, us-west-2)
AWS_REGION=us-east-1
# AWS Access Key ID (from IAM user)
AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
# AWS Secret Access Key (from IAM user)
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
# Bedrock Model ID to use
# Options:
#   - anthropic.claude-3-sonnet-20240229-v1:0 (recommended)
#   - anthropic.claude-3-haiku-20240307-v1:0 (fastest, cheapest)
#   - anthropic.claude-3-opus-20240229-v1:0 (most capable)
#   - meta.llama3-70b-instruct-v1:0 (open-source alternative)
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

### Step 2: Update Your .env File

Copy the new variables to your `.env` file and fill in your AWS credentials:

```bash
cd backend
cp env.example .env
# Edit .env and add your AWS credentials
```

**Example .env configuration:**

```bash
# Use Bedrock instead of OpenAI
USE_BEDROCK=true

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Bedrock Model
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Keep OpenAI as fallback (optional)
OPENAI_API_KEY=sk-your-key-here
```

### Step 3: Update Docker Compose (if using Docker)

Add environment variables to `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      # ... existing variables ...
      - USE_BEDROCK=${USE_BEDROCK:-false}
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:-anthropic.claude-3-sonnet-20240229-v1:0}
```

---

## Testing

### Step 1: Test Bedrock Connection

Create a test script `backend/test_bedrock.py`:

```python
"""Test Bedrock integration"""
import asyncio
import os
from dotenv import load_dotenv
from app.services.bedrock_service import BedrockService

load_dotenv()

async def test_bedrock():
    service = BedrockService()
    
    if not service.client:
        print("❌ Bedrock client not initialized. Check your AWS credentials.")
        return
    
    print("✅ Bedrock client initialized")
    
    # Test simple generation
    try:
        response = await service.generate_text(
            prompt="Write a haiku about AI.",
            system_prompt="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=100
        )
        print(f"\n✅ Test successful!")
        print(f"Response: {response}")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_bedrock())
```

Run the test:

```bash
cd backend
python test_bedrock.py
```

### Step 2: Test MOM Generation

1. Start your backend server:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Start a transcription session and generate MOM through the API:
   ```bash
   # Start transcription (if you have a session)
   curl -X POST http://localhost:8000/api/ai/summarize \
     -H "Content-Type: application/json" \
     -d '{"session_id": "your-session-id", "include_faqs": true}'
   ```

3. Check backend logs for Bedrock API calls

### Step 3: Verify Model Usage

Check AWS CloudWatch for Bedrock API usage:

1. Go to **CloudWatch Console** → **Metrics** → **Bedrock**
2. Look for `Invocations` and `InputTokens` metrics
3. Verify your API calls are being recorded

---

## Model Selection Guide

### Claude 3 Sonnet (Recommended)
- **Model ID**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Best for**: General-purpose tasks, MOM generation, email summarization
- **Cost**: ~$3 per 1M input tokens, $15 per 1M output tokens
- **Speed**: Fast
- **Quality**: Excellent

### Claude 3 Haiku
- **Model ID**: `anthropic.claude-3-haiku-20240307-v1:0`
- **Best for**: Simple tasks, quick responses, cost-sensitive applications
- **Cost**: ~$0.25 per 1M input tokens, $1.25 per 1M output tokens
- **Speed**: Very fast
- **Quality**: Good

### Claude 3 Opus
- **Model ID**: `anthropic.claude-3-opus-20240229-v1:0`
- **Best for**: Complex analysis, high-quality outputs
- **Cost**: ~$15 per 1M input tokens, $75 per 1M output tokens
- **Speed**: Slower
- **Quality**: Excellent

### Llama 3 70B
- **Model ID**: `meta.llama3-70b-instruct-v1:0`
- **Best for**: Open-source alternative, cost-effective
- **Cost**: ~$0.65 per 1M input tokens, $0.65 per 1M output tokens
- **Speed**: Moderate
- **Quality**: Very good

### Choosing the Right Model

| Use Case | Recommended Model | Reason |
|----------|------------------|--------|
| MOM Generation | Claude 3 Sonnet | Best balance of quality and cost |
| Email Summarization | Claude 3 Haiku | Fast and cost-effective for simple tasks |
| Risk Detection | Claude 3 Sonnet | Needs good reasoning |
| FAQ Generation | Claude 3 Haiku | Straightforward Q&A |
| Complex Analysis | Claude 3 Opus | Highest quality needed |

---

## Cost Considerations

### Pricing Comparison (Approximate)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|----------------------|
| Claude 3 Haiku | $0.25 | $1.25 |
| Claude 3 Sonnet | $3.00 | $15.00 |
| Claude 3 Opus | $15.00 | $75.00 |
| Llama 3 70B | $0.65 | $0.65 |
| GPT-4 Turbo | $10.00 | $30.00 |

### Cost Optimization Tips

1. **Use Haiku for simple tasks** - Email summarization, simple Q&A
2. **Use Sonnet for complex tasks** - MOM generation, risk detection
3. **Use Opus sparingly** - Only for most critical/complex analysis
4. **Monitor usage** - Set up AWS Cost Alerts
5. **Cache responses** - Cache similar queries when possible
6. **Optimize prompts** - Shorter prompts = lower costs

### Setting Up Cost Alerts

1. Go to **AWS Billing Console** → **Budgets**
2. Click **"Create budget"**
3. Select **"Cost budget"**
4. Set amount (e.g., $50/month)
5. Configure alerts at 80%, 100% thresholds
6. Add email notifications

---

## Troubleshooting

### Issue: "Bedrock client not initialized"

**Symptoms:**
```
Error: Bedrock client not initialized
```

**Solutions:**
1. Verify AWS credentials in `.env`:
   ```bash
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   ```
2. Check IAM user has Bedrock permissions
3. Verify region is correct and Bedrock is available there
4. Test AWS CLI access:
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

### Issue: "Model access denied"

**Symptoms:**
```
Error: AccessDeniedException: User does not have access to model
```

**Solutions:**
1. Go to Bedrock Console → **Model access**
2. Request access to the model you're trying to use
3. Wait for approval (usually instant)
4. Verify model ID is correct in `.env`

### Issue: "Invalid model ID"

**Symptoms:**
```
Error: ValidationException: Invalid model ID
```

**Solutions:**
1. Check model ID format in `.env`:
   ```
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
   ```
2. Verify model is available in your region
3. Check Bedrock console for available models

### Issue: "Rate limit exceeded"

**Symptoms:**
```
Error: ThrottlingException: Rate exceeded
```

**Solutions:**
1. Implement exponential backoff in your code
2. Reduce request frequency
3. Use faster models (Haiku) for high-volume tasks
4. Contact AWS Support to increase limits

### Issue: "JSON parsing error"

**Symptoms:**
```
Error: JSONDecodeError when parsing model response
```

**Solutions:**
1. Ensure `response_format={"type": "json_object"}` is set
2. Add explicit JSON formatting instructions in prompt
3. Implement JSON extraction/cleaning logic
4. Add fallback error handling

### Issue: "Region not available"

**Symptoms:**
```
Error: Bedrock is not available in this region
```

**Solutions:**
1. Use one of the supported regions:
   - `us-east-1` (N. Virginia) ✅
   - `us-west-2` (Oregon)
   - `ap-northeast-1` (Tokyo)
   - `eu-central-1` (Frankfurt)
2. Update `AWS_REGION` in `.env`

### Issue: "Slow response times"

**Symptoms:**
- API calls taking 10+ seconds

**Solutions:**
1. Use Claude 3 Haiku for faster responses
2. Reduce `max_tokens` parameter
3. Check AWS region latency (use closest region)
4. Consider using streaming responses for better UX

---

## Production Deployment

### Step 1: Use IAM Roles (Instead of Access Keys)

For production, use IAM roles instead of access keys:

1. **EC2/ECS**: Attach IAM role to instance/task
2. **Lambda**: Attach IAM role to function
3. **EKS**: Use IAM roles for service accounts (IRSA)

**Example IAM Role Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
      ]
    }
  ]
}
```

### Step 2: Update Code for IAM Roles

When using IAM roles, remove explicit credentials:

```python
# Production: Use IAM role (no credentials needed)
self.client = boto3.client(
    'bedrock-runtime',
    region_name=self.region
)

# Development: Use credentials from .env
if os.getenv("AWS_ACCESS_KEY_ID"):
    self.client = boto3.client(
        'bedrock-runtime',
        region_name=self.region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
else:
    # Use IAM role (production)
    self.client = boto3.client(
        'bedrock-runtime',
        region_name=self.region
    )
```

### Step 3: Enable Logging and Monitoring

1. **CloudWatch Logs**: Enable detailed logging
2. **CloudWatch Metrics**: Monitor API calls, errors, latency
3. **X-Ray**: Enable for distributed tracing (optional)

### Step 4: Implement Error Handling

Add robust error handling:

```python
try:
    response = await self.bedrock_service.generate_text(...)
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'ThrottlingException':
        # Implement retry with exponential backoff
        await asyncio.sleep(2 ** retry_count)
        # Retry...
    elif error_code == 'AccessDeniedException':
        # Log and alert
        logger.error("Bedrock access denied - check IAM permissions")
    else:
        # Fallback to OpenAI or return error
        raise
```

### Step 5: Security Best Practices

1. **Never commit credentials** - Use environment variables or secrets manager
2. **Use AWS Secrets Manager** - For production credentials
3. **Enable VPC endpoints** - For private Bedrock access (if in VPC)
4. **Implement rate limiting** - Prevent abuse
5. **Monitor costs** - Set up billing alerts

---

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Bedrock Model IDs Reference](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [boto3 Bedrock Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html)
- [Anthropic Claude Documentation](https://docs.anthropic.com/claude/docs)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

---

## Quick Reference

### Environment Variables Checklist

```bash
# Required for Bedrock
USE_BEDROCK=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

### Common Model IDs

```bash
# Claude Models
anthropic.claude-3-opus-20240229-v1:0      # Most capable
anthropic.claude-3-sonnet-20240229-v1:0    # Recommended
anthropic.claude-3-haiku-20240307-v1:0     # Fastest, cheapest

# Llama Models
meta.llama3-70b-instruct-v1:0              # Open-source

# Amazon Models
amazon.titan-text-express-v1                # Amazon's model
```

### Testing Commands

```bash
# Test Bedrock connection
python backend/test_bedrock.py

# Test via API
curl -X POST http://localhost:8000/api/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session"}'

# Check AWS CLI access
aws bedrock list-foundation-models --region us-east-1
```

---

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review AWS CloudWatch logs for detailed errors
3. Verify IAM permissions and model access
4. Check AWS Bedrock service status
5. Open an issue on GitHub with:
   - Error message
   - Region and model ID
   - Relevant logs (redact credentials)

---

**Last Updated**: 2024
**Version**: 1.0

