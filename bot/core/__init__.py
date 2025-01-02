from typing import Dict, List, Union, Callable, Any
import os
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.function_calling.base import FunctionCallingAgent
from llama_index.core.tools import FunctionTool, ToolMetadata
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from tools import TherapyDocTools
from ..llms import MockLLM

class TherapyDocumentationBot:
    def __init__(self, test_mode=False):
        """Initialize the therapy documentation chatbot with llama-index"""
        self.tools = TherapyDocTools()
        self.test_mode = test_mode
        self.chat_history: List[ChatMessage] = []
        
        if self.test_mode:
            # Use mock LLM in test mode
            llm = MockLLM()
        else:
            # Use real OpenAI in production mode with new API
            llm = OpenAI(
                model="gpt-4",
                temperature=0,
                api_key=os.environ.get("OPENAI_API_KEY"),
                additional_kwargs={} # Ensure no extra kwargs are passed
            )
        
        # Convert tools to llama-index format
        self.llama_tools = []
        for tool_info in self.tools.get_tools():
            # Create a wrapper function that accepts kwargs
            def create_tool_func(tool_func):
                def wrapper(**kwargs) -> str:
                    try:
                        return tool_func(**kwargs)
                    except TypeError as e:
                        return f"Error: Invalid arguments - {str(e)}"
                return wrapper
            
            # Bind the function to a new wrapper
            bound_wrapper = create_tool_func(tool_info['func'])
            
            # Create tool metadata
            metadata = ToolMetadata(
                name=tool_info['name'],
                description=tool_info['description']
            )
            
            # Create function tool
            self.llama_tools.append(
                FunctionTool(
                    metadata=metadata,
                    fn=bound_wrapper
                )
            )
        
        # Create system prompt
        system_prompt = """You are a friendly and empathetic therapy documentation assistant. Your role is to have natural conversations 
        while helping document the client's experiences and progress. You maintain context from previous messages to provide more 
        personalized and contextually relevant responses.

        IMPORTANT RULES:
        1. Only document what the user explicitly shares. Do not make assumptions or infer information that wasn't directly stated.
        2. When the user declines to share information or says they don't want to talk about something, simply acknowledge their response naturally without trying to document anything.
        3. For simple acknowledgments or responses that don't require documentation (like "thanks", "okay", "bye", "no", "nah"), just respond naturally without using any tools.
        4. Never use dots (.) in tool names - use only the exact tool names as provided.

        You can document information in these categories and their sections:

        - journaling: Journaling
          Sections: 
          - 'Counting entries': Track number of journal entries
          - 'Cognitive therapy': Document therapy-related journaling
        
        - sleep: Sleep
          Sections:
          - 'Length of sleep': Track sleep duration
          - 'Schedule': Document sleep/wake times
          - 'Dreams': Record any dream experiences
        
        - physical: Physical Activity
          Sections:
          - 'Fitbit heart rate zones': Ask user to share their Fitbit heart rate data
          - 'Strength training': Document strength training activities
        
        - social: Social Engagement
          Sections:
          - 'In-person': Track face-to-face interactions
          - 'Text': Document text-based communications
          - 'VC': Record video call interactions
        
        - productivity: Productivity & Work
          Sections:
          - 'Cold Turkey': Ask user to share their Cold Turkey Blocker stats
          - 'iOS Screen Time': Ask user to share their iOS Screen Time data
        
        - spiritual: Spiritual Practice
          Sections:
          - 'Solo': Document individual spiritual practices
          - 'Group': Track group spiritual activities
        
        - self_care: Basic Self-Care
          Sections:
          - 'Meals hygiene meds': Track daily self-care routines
          - 'budget checklist medical appts': Document appointments and financial care

        IMPORTANT: Some sections require external data:
        1. 'Fitbit heart rate zones': Always ask user to share their Fitbit data
        2. 'Cold Turkey': Always ask user to share their Cold Turkey Blocker statistics
        3. 'iOS Screen Time': Always ask user to share their iOS Screen Time data

        For each category, you can use these tools:
        1. set_category_section_observations: Record observations for a specific section
        2. set_category_next_steps: Document next steps or action items discussed
        3. add_category_notes: Add additional notes

        Example of proper documentation:
        When user says: "I slept 8 hours last night, no dreams, went to bed at 10pm"
        Document in appropriate sections:
        {
            "category_id": "sleep",
            "section_name": "Length of sleep",
            "observations": "8 hours of sleep"
        }
        {
            "category_id": "sleep",
            "section_name": "Schedule",
            "observations": "Bedtime at 10pm"
        }
        {
            "category_id": "sleep",
            "section_name": "Dreams",
            "observations": "No dreams reported"
        }

        When user says: "Did my morning workout"
        Document strength training and ask about Fitbit data:
        {
            "category_id": "physical",
            "section_name": "Strength training",
            "observations": "Completed morning workout"
        }
        Response: "That's great! Could you share your Fitbit heart rate data from the workout? This helps us track your exercise intensity."

        When user says: "Had a therapy session and wrote about it"
        Document in sections:
        {
            "category_id": "journaling",
            "section_name": "Cognitive therapy",
            "observations": "Documented therapy session in journal"
        }

        IMPORTANT: Always use proper JSON formatting with commas between properties:
        CORRECT:
        {
            "category_id": "sleep",
            "section_name": "Length of sleep",
            "observations": "..."
        }
        
        INCORRECT:
        {
            "category_id": "sleep"
            "section_name": "Length of sleep"
            "observations": "..."
        }

        Behavior in different modes:

        In interactive mode:
        1. Be empathetic and professional in your responses
        2. Document only explicitly shared information
        3. Ask natural follow-up questions to gather more context
        4. Use the context provided in each interaction to maintain conversation flow

        In non-interactive mode (single message):
        1. Focus on documenting only what was explicitly shared
        2. Do not make assumptions or infer information
        3. DO NOT ask follow-up questions
        4. Keep responses brief and focused on confirming what was documented

        The context will include:
        - Previous conversation history (up to 5 messages)
        - Currently discussed category
        - Previously documented observations
        - Previously documented next steps
        - Any additional notes

        Remember:
        - Only document what is explicitly shared
        - Use exact tool names without dots
        - Respond naturally to simple acknowledgments without using tools
        """

        # Initialize the agent
        self.agent = FunctionCallingAgent.from_llm(
            tools=self.llama_tools,
            llm=llm,
            system_prompt=system_prompt,
            verbose=True
        )

    def start_documentation(self) -> Dict:
        """Start a new documentation session"""
        return {
            "response": "Hey! What's up? How have you been doing?"
        }

    def process_message(self, message: str) -> Dict[str, str]:
        """Process incoming user message"""
        if not message:
            return {
                "response": "I'm sorry, I didn't understand that. Could you tell me more?"
            }
        
        try:
            # Build context for the agent
            context = ""
            categories = self.tools.get_categories()
            
            # Add chat history to context
            if self.chat_history:
                context += "Previous conversation:\n"
                for msg in self.chat_history[-5:]:  # Keep last 5 messages for context
                    role = "User" if msg.role == MessageRole.USER else "Assistant"
                    context += f"{role}: {msg.content}\n"
            
            # Add current documentation state to context
            if self.tools.current_category:
                context += f"\nCurrently discussing: {self.tools.current_category}\n"
                if self.tools.current_category in self.tools.current_data:
                    data = self.tools.current_data[self.tools.current_category]
                    if data["observations"]:
                        context += f"What you've shared: {data['observations']}\n"
                    if data["next_steps"]:
                        context += f"Next steps we discussed: {data['next_steps']}\n"
                if self.tools.current_category in self.tools.notes:
                    context += f"Additional notes: {self.tools.notes[self.tools.current_category]}\n"
            
            print("\nDebug - process_message:")
            print(f"Input message: {message}")
            print(f"Context: {context}")
            
            try:
                # Combine context with user message
                full_message = f"Context:\n{context}\n\nUser message: {message}"
                
                # Let the agent handle the conversation
                response = self.agent.chat(full_message)
                
                print(f"Agent response: {response}")
                
                # Extract the response text
                response_text = str(response)
                
                # Update chat history
                self.chat_history.append(ChatMessage(role=MessageRole.USER, content=message))
                self.chat_history.append(ChatMessage(role=MessageRole.ASSISTANT, content=response_text))
                
                result = {"response": response_text}
                print(f"Final processed result: {result}")
                return result
                
            except Exception as e:
                print(f"Error in process_message: {str(e)}")
                print(f"Error type: {type(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                return {
                    "response": f"Error: {str(e)}"
                }
            
        except Exception as e:
            return {
                "response": f"I encountered an error: {str(e)}. Could you please try again?"
            }

    def get_current_data(self) -> Dict[str, Dict[str, str]]:
        """Get current documentation data"""
        return self.tools.current_data

    def get_notes(self) -> Dict[str, str]:
        """Get current notes"""
        return self.tools.notes

    def clear_data(self):
        """Clear all documentation data"""
        categories = self.tools.get_categories()
        for category in categories:
            self.tools.clear_category(category_id=category['id'])
