from pydantic import BaseModel


class AdvisingMeetingPlan(BaseModel):
    discuss_first: str
    faculty_questions: list[str]
    student_actions: list[str]
    parent_involvement_needed: bool
    parent_involvement_reason: str


class RecommendationResponse(BaseModel):
    academic: list[str]
    career: list[str]
    learning_pathways: list[str]
    meeting_plan: AdvisingMeetingPlan
