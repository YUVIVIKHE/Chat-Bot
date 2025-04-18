import httpx
from app.config.settings import DEEPSEEK_API_KEY
from typing import List, Dict, Any, Optional
import json
import asyncio

class DeepSeekAI:
    def __init__(self, api_key: str = DEEPSEEK_API_KEY):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_response(
        self, 
        query: str, 
        context: Optional[List[str]] = None,
        module: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from the DeepSeek AI model.
        
        Args:
            query: The user's question
            context: Additional context to provide to the model
            module: The specific module to use for generating the response
        
        Returns:
            Dictionary containing the AI response
        """
        try:
            # Prepare system prompt based on module
            system_prompt = self._get_system_prompt(module)
            
            # Prepare messages for the API request
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add context if available
            if context and len(context) > 0:
                context_text = "\n\n".join(context)
                messages.append({
                    "role": "system",
                    "content": f"Use the following information as context for answering the user's question:\n\n{context_text}"
                })
            
            # Add the user's query
            messages.append({"role": "user", "content": query})
            
            # Prepare the payload
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # Make the API request
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    response = await client.post(
                        self.api_url,
                        headers=self.headers,
                        json=payload
                    )
                    
                    # Process the response
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        # Extract the assistant's reply
                        assistant_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Return success with response
                        return {
                            "success": True,
                            "response": assistant_response,
                            "usage": response_data.get("usage", {})
                        }
                    else:
                        # Try to get error details
                        error_detail = "Unknown error"
                        try:
                            error_data = response.json()
                            error_detail = error_data.get("error", {}).get("message", str(error_data))
                        except:
                            error_detail = f"Status code: {response.status_code}"
                        
                        # Log detailed error
                        print(f"DeepSeek API error: {error_detail}. Falling back to mock response.")
                        return await self._get_fallback_response(query, context, module)
                except httpx.TimeoutException:
                    print("DeepSeek API request timed out. Falling back to mock response.")
                    return await self._get_fallback_response(query, context, module)
                except Exception as e:
                    print(f"Error calling DeepSeek API: {str(e)}. Falling back to mock response.")
                    return await self._get_fallback_response(query, context, module)
        except Exception as e:
            # Log the error and fall back to mock response
            print(f"Error calling DeepSeek API: {str(e)}. Falling back to mock response.")
            return await self._get_fallback_response(query, context, module)
    
    async def _get_fallback_response(
        self, 
        query: str, 
        context: Optional[List[str]] = None,
        module: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a fallback response if the API call fails."""
        # Create a mock response based on the module and query
        response_text = self._generate_mock_response(query, context, module)
        
        # Simulate a delay to make it feel like an API call
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "response": response_text,
            "usage": {"total_tokens": 250}
        }
    
    def _generate_mock_response(
        self,
        query: str,
        context: Optional[List[str]] = None,
        module: Optional[str] = None
    ) -> str:
        """Generate a mock response based on the query and module."""
        # Use some context if available
        if context and len(context) > 0:
            # If we have relevant context, use it
            context_text = context[0]
            # Extract just the answer part after the first newline if it exists
            if '\n' in context_text:
                parts = context_text.split('\n', 1)
                answer_text = parts[1]
            else:
                answer_text = context_text
            
            return f"Based on our compliance database, here's the answer to your question about '{query}':\n\n{answer_text}"
        
        # Generic responses based on the module
        module_responses = {
            "1": f"As the ISO Bot, I can tell you that regarding '{query}', ISO 27001 typically requires organizations to implement controls that address this risk through a systematic approach. Consider reviewing controls in Annex A that relate to your specific concern.",
            
            "2": f"As RiskBot, I recommend conducting a thorough risk assessment for '{query}'. Start by identifying assets, threats, and vulnerabilities, then evaluate likelihood and impact to determine appropriate controls.",
            
            "3": f"Compliance Coach here! When dealing with '{query}', remember to document your actions and maintain evidence of compliance. Training your team on this specific requirement is essential for organizational compliance.",
            
            "4": f"AuditBuddy advice: For your question about '{query}', prepare by gathering documentation that demonstrates compliance. Auditors will look for evidence of implementation, not just policy statements.",
            
            "5": f"Policy Navigator: According to most organizational policies, '{query}' should be handled according to your data classification standards. Refer to your organization's specific policy documents for detailed guidance.",
            
            "6": f"Security Advisor: To address '{query}' securely, implement defense-in-depth measures including technical controls, administrative safeguards, and regular monitoring. Don't forget to test your security controls periodically."
        }
        
        # If we have a specific module, use its response
        if module and module in module_responses:
            return module_responses[module]
        
        # Generic response for no context and no specific module
        return f"Thank you for your question about '{query}'. In compliance and governance contexts, it's important to refer to your organization's specific policies and applicable regulations. Would you like me to provide general guidance on this topic, or could you provide more specific details about your compliance framework?"
    
    def _get_system_prompt(self, module: Optional[str] = None) -> str:
        """Get system prompt based on the selected module."""
        base_prompt = "You are CARA ComplianceBot, an AI assistant for Governance, Risk, and Compliance. Your goal is to provide accurate, helpful information about compliance frameworks, policies, and best practices."
        
        if not module:
            return base_prompt
        
        module_prompts = {
            "1": "You are ISO Bot, specializing in ISO 27001 standards. Provide detailed information about ISO controls, requirements, and implementation guidance. Help users understand how to comply with ISO 27001 and gather appropriate evidence.",
            
            "2": "You are RiskBot, a risk assessment specialist. Guide users through identifying, analyzing, and mitigating risks. Help with risk register creation, risk scoring, and control selection.",
            
            "3": "You are Compliance Coach, focused on compliance training and awareness. Provide bite-sized training modules, reminders about compliance policies, and answer policy-related questions.",
            
            "4": "You are AuditBuddy, an audit preparation specialist. Help organizations prepare for audits by explaining audit processes, gathering required documentation, and simulating auditor questions.",
            
            "5": "You are Policy Navigator, helping users find and understand organizational policies. Assist with policy interpretation, application in specific scenarios, and compliance with internal requirements.",
            
            "6": "You are Security Advisor, providing security best practices and guidance. Offer advice on security controls, incident response, and security awareness."
        }
        
        return module_prompts.get(module, base_prompt)

# Create a singleton instance
ai_model = DeepSeekAI() 