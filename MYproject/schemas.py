
from sqlmodel import JSON, Field, SQLModel, Column
from pydantic import BaseModel, EmailStr, ConfigDict
`   `

#Users Table
class User(SQLModel, table=True):
    id : int | None = Field(default=None, primary_key=True, index=True)
    username : str = Field(index=True, unique=True)
    email : str = Field(index=True, unique=True)
    hashed_password : str = Field()

class UserCreate(BaseModel):
    
    username: str
    email: EmailStr
    password: str
    
    model_config = ConfigDict(from_attributes=True)

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    
    model_config = ConfigDict(from_attributes=True)
    
    
#Quizzes Table
class Quizzes(SQLModel, table=True):
    id : int |None= Field( primary_key=True, index=True, default=None)
    user_id : int= Field( index=True, foreign_key="user.id")
    title : str = Field( index=True)
    description : str = Field()
    publisher : str = Field( index=True)
    short_code : str = Field( unique=True, index=True)
    
class QuestionCreate(BaseModel):
    
    question_text: str
    options: list[str]
    correct_option: str
    
    model_config = ConfigDict(from_attributes=True)

class QuizCreate(BaseModel):
    title: str
    description: str
    questions: list[QuestionCreate] 
    

class QuestionOut(BaseModel):
    id: int
    quiz_id: int
    question_text: str
    options: list[str]
    
    model_config = ConfigDict(from_attributes=True)

class QuizOut(BaseModel):
    id: int
    title: str
    description: str
    publisher: str
    short_code: str
    questions: list[QuestionOut] = []

    model_config = ConfigDict(from_attributes=True)
    
class Questions(SQLModel, table=True):
    id : int | None = Field (primary_key=True, index=True, default=None)
    quiz_id : int = Field( index=True, foreign_key="quizzes.id")
    question_text : str = Field(default=None)
    options : list[str] | None = Field(default=[], sa_column=Column(JSON))
    correct_option : str = Field()


class SubmitAnswers(BaseModel):
    answers: dict[int, str]
    
