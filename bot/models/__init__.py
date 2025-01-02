from typing import Union, Literal
from pydantic import BaseModel, Field

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
