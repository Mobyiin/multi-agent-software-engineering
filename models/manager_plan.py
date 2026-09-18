from typing import Literal

from pydantic import BaseModel, Field


AgentName = Literal[
    "coding_agent",
    "testing_agent",
    "code_review_agent",
    "documentation_agent",
    "frontend_agent",
    ]


Complexity = Literal[
    "small",
    "medium",
    "large",
]


class TaskProposal(BaseModel):
    description: str = Field(min_length=1)
    assigned_agent: AgentName
    complexity: Complexity
    reason: str = Field(min_length=1)


class ManagerPlan(BaseModel):
    goal_summary: str = Field(min_length=1)
    tasks: list[TaskProposal]
    final_notes: str | None = None