from typing import Dict, Optional, List, Union, Literal, Any
from langchain.chat_models import ChatOpenAI
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish, BaseMessage
from langchain.base_language import BaseLanguageModel
from langchain.chains import LLMChain
from tools import TherapyDocTools
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
import json
import os

class MockLLM(BaseLanguageModel):
    """Mock LLM for testing"""
    def predict(self, text: str, **kwargs) -> str:
        return """thoughts: The user mentioned sleep and energy levels
action: set_category_observations
action_input:
    category_id: sleep
    observations: Reports feeling energetic after energy drink but still thirsty
response: I understand you're feeling energetic from the energy drink. How's your overall sleep pattern been lately? Sometimes thirst can be related to sleep quality."""

    async def apredict(self, text: str, **kwargs) -> str:
        return self.predict(text, **kwargs)

    def predict_messages(self, messages: List[BaseMessage], **kwargs) -> BaseMessage:
        return BaseMessage(content=self.predict(str(messages)))

    async def apredict_messages(self, messages: List[BaseMessage], **kwargs) -> BaseMessage:
        return self.predict_messages(messages, **kwargs)

    def invoke(self, input: Union[str, List[BaseMessage]], **kwargs) -> Any:
        if isinstance(input, str):
            return self.predict(input, **kwargs)
        else:
            return self.predict_messages(input, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "mock"

class CategoryObservation(BaseModel):
    """A model for documenting observations in a category"""
    category_id: str = Field(description="The ID of the category (e.g., 'sleep', 'productivity')")
    observations: str = Field(description="The observations to document")

class CategoryNextSteps(BaseModel):
    """A model for documenting next steps in a category"""
    category_id: str = Field(description="The ID of the category (e.g., 'sleep', 'productivity')")
    next_steps: str = Field(description="The next steps to document")

class CategoryNotes(BaseModel):
    """A model for adding notes to a category"""
    category_id: str = Field(description="The ID of the category (e.g., 'sleep', 'productivity')")
    notes: str = Field(description="The notes to add")

class TherapyResponse(BaseModel):
    """A model for the chatbot's response"""
    thoughts: str = Field(description="Your thoughts about how to respond and what to document")
    action: Literal["set_category_observations", "set_category_next_steps", "add_category_notes"] = Field(description="The action to take")
    action_input: Union[CategoryObservation, CategoryNextSteps, CategoryNotes] = Field(description="The input for the action")
    response: str = Field(description="Your empathetic response to the user")

class TherapyPromptTemplate(StringPromptTemplate):
    """Custom prompt template for therapy documentation agent"""
    template: str
    input_variables: List[str]

    def format(self, **kwargs) -> str:
        """Format the prompt template"""
        kwargs.setdefault('agent_scratchpad', '')
        kwargs.setdefault('format_instructions', '')  # Add default for format_instructions
        
        # First replace the example JSON with a placeholder
        template_with_placeholder = self.template.replace(
            '{\n            "thoughts"',
            'EXAMPLE_START'
        ).replace(
            '        }',
            'EXAMPLE_END'
        )
        
        # Escape any curly braces in format_instructions
        if 'format_instructions' in kwargs:
            kwargs['format_instructions'] = kwargs['format_instructions'].replace('{', '{{').replace('}', '}}')
        
        # Format the template
        formatted = template_with_placeholder.format(**kwargs)
        
        # Put the example JSON back
        return formatted.replace(
            'EXAMPLE_START',
            '{\n            "thoughts"'
        ).replace(
            'EXAMPLE_END',
            '        }'
        )

class TherapyAgentOutputParser(AgentOutputParser):
    """Custom output parser that handles YAML-like format"""
    def __init__(self):
        super().__init__()

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        # For simple responses, just return them directly
        if not any(action in text.lower() for action in ["set_category_observations", "set_category_next_steps", "add_category_notes"]):
            return AgentFinish(
                return_values={"output": text},
                log=text
            )
        
        try:
            # Convert YAML-like format to JSON
            lines = text.strip().split('\n')
            json_dict = {}
            current_key = None
            current_dict = None
            
            for line in lines:
                # Count leading spaces to determine nesting level
                leading_spaces = len(line) - len(line.lstrip())
                line = line.strip()
                if not line:
                    continue
                
                # Split line into key and value
                parts = line.split(':', 1)
                if len(parts) != 2:
                    continue
                    
                key, value = parts[0].strip(), parts[1].strip()
                
                if leading_spaces == 0:  # Top-level key
                    if value:  # Key with direct value
                        json_dict[key] = value
                    else:  # Key with nested values
                        json_dict[key] = {}
                        current_key = key
                        current_dict = json_dict[key]
                elif leading_spaces >= 4:  # Nested key
                    if current_dict is not None:
                        current_dict[key] = value
                
            print(f"Parsed JSON dict: {json_dict}")  # Debug print
            
            # Extract the required fields from the parsed YAML-like format
            action = json_dict.get('action')
            action_input = json_dict.get('action_input', {})
            category_id = action_input.get('category_id')
            
            # Build the tool input based on the action type
            tool_input = None
            if action == "set_category_observations":
                observations = action_input.get('observations', '')
                if category_id and observations:
                    tool_input = f"{category_id} {observations}"
            elif action == "set_category_next_steps":
                next_steps = action_input.get('next_steps', '')
                if category_id and next_steps:
                    tool_input = f"{category_id} {next_steps}"
            elif action == "add_category_notes":
                notes = action_input.get('notes', '')
                if category_id and notes:
                    tool_input = f"{category_id} {notes}"
            
            if not tool_input:
                print(f"Failed to build tool input from action_input: {action_input}")
                return AgentFinish(
                    return_values={"output": json_dict.get('response', text)},
                    log=text
                )
            
            # Return an AgentAction with the parsed information
            return AgentAction(
                tool=action,
                tool_input=tool_input,
                log=text
            )
        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            print(f"Text being parsed: {text}")
            # If parsing fails, return the text as a response
            return AgentFinish(
                return_values={"output": text},
                log=text
            )

class TherapyDocumentationBot:
    def __init__(self, test_mode=False):
        """Initialize the therapy documentation chatbot with llama-index and langchain"""
        self.tools = TherapyDocTools()
        self.test_mode = test_mode or not os.getenv('OPENAI_API_KEY')
        
        if self.test_mode:
            # Use mock LLM in test mode
            llm = MockLLM()
        else:
            # Use real OpenAI in production mode
            llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mi")
        
        # Convert tools to langchain format
        self.langchain_tools = [
            Tool(
                name=tool.name,
                func=tool.func,
                description=tool.description
            )
            for tool in self.tools.get_tools()
        ]
        
        # Initialize agent
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self._create_agent(llm),
            tools=self.langchain_tools,
            verbose=True,
            return_intermediate_steps=True
        )

    def _create_agent(self, llm):
        """Create a LangChain agent with custom prompt template"""
        output_parser = TherapyAgentOutputParser()

        template = """You are a friendly and empathetic therapy documentation assistant. Your goal is to have natural conversations while helping document the user's experiences.

        Current context:
        {context}

        Available documentation tools:
        {tools}

        User message: {input}

        First, think about how to respond empathetically to the user's message. Then, if you notice any information that should be documented, use the appropriate tool.

        Available Categories:
        - sleep: Sleep (Fitbit data / Dreaming)
        - productivity: Productivity & Work
        - journaling: Journaling
        - physical: Physical Activity
        - meditation: Meditation
        - spiritual: Spiritual Practice
        - self_care: Basic Self-Care

        {format_instructions}

        Example Response Format:
        thoughts: The user mentioned sleep issues due to work stress. I should document both aspects.
        action: set_category_observations
        action_input:
            category_id: sleep
            observations: Having trouble sleeping, lying awake at night due to work stress
        response: I hear you - it's really tough when work stress follows you to bed. Have you noticed if there are certain times when the worrying tends to be worse? Sometimes tracking our patterns can help us find ways to manage them better.

        Begin:
        {agent_scratchpad}"""
        
        # Create custom format instructions for YAML-like format
        format_instructions = """The output should be formatted as follows:
        thoughts: [your thoughts about how to respond]
        action: [one of: set_category_observations, set_category_next_steps, add_category_notes]
        action_input:
            category_id: [category ID]
            observations/next_steps/notes: [content based on action type]
        response: [your empathetic response to the user]"""
        
        # Replace format_instructions in template
        template = template.replace("{format_instructions}", format_instructions)
        
        prompt = TherapyPromptTemplate(
            template=template,
            input_variables=["context", "tools", "input", "agent_scratchpad"]
        )
        
        llm_chain = LLMChain(llm=llm, prompt=prompt)
        
        return LLMSingleActionAgent(
            llm_chain=llm_chain,
            output_parser=output_parser,
            stop=["\nObservation:"],
            allowed_tools=[tool.name for tool in self.langchain_tools]
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
            print(f"Tools: {self.langchain_tools}")
            
            try:
                # Let the agent handle the conversation naturally
                response = self.agent_executor(
                    {
                        "input": message,
                        "context": context,
                        "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in self.langchain_tools]),
                        "agent_scratchpad": ""
                    }
                )
                print(f"Agent executor response: {response}")
                
                # Extract the response from the agent's output
                if isinstance(response, str):
                    result = {"response": response}
                else:
                    # Try to get response from return_values attribute first
                    if hasattr(response, 'return_values') and isinstance(response.return_values, dict):
                        response_text = response.return_values.get("output")
                        if response_text:
                            result = {"response": response_text}
                            return result
                    
                    # Then try dict-style access for return_values
                    if isinstance(response, dict) and "return_values" in response:
                        response_text = response["return_values"].get("output")
                        if response_text:
                            result = {"response": response_text}
                            return result
                    
                    # Fall back to output or response keys
                    if isinstance(response, dict):
                        response_text = response.get("output") or response.get("response")
                        if response_text:
                            result = {"response": response_text}
                            return result
                    
                    # Last resort: convert to string
                    result = {"response": str(response)}
                    
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
            self.tools.clear_category(category)
