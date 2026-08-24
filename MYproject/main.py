
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from jwt.exceptions import InvalidTokenError
import schemas


from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi.middleware.cors import CORSMiddleware




from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

sqlite_file_name = "database.db"
engine = create_engine(f"sqlite:///{sqlite_file_name}", connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(engine)

def get_session(): 
    with Session(engine) as session:
        yield session


    
class Token(BaseModel):
    access_token: str
    token_type: str 
class TokenData(BaseModel):
    username: str | None = None 
    
password_hasher = PasswordHash.recommended()
dummyhash = password_hasher.hash("dummy_password")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencies 


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse("static/index.html")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return password_hasher.hash(password)

def generate_short_code(length: int = 8) -> str:
    return uuid4().hex[:length]

def authenticate_user(session: Session, username: str, password: str) -> schemas.User | None:
    user = session.exec(select(schemas.User).where(schemas.User.username == username)).first()
    if not user:
        verify_password(password, dummyhash)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt  


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: Session = Depends(get_session)) -> schemas.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = session.exec(select(schemas.User).where(schemas.User.username == token_data.username)).first()
    if user is None:
        raise credentials_exception
    return user 

@app.post("/register", response_model=schemas.UserOut)
async def register_user(user: schemas.UserCreate, session: Session = Depends(get_session)):
    existing_user = session.exec(select(schemas.User).where( or_(schemas.User.username == user.username, schemas.User.email == user.email))).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = schemas.User(username=user.username, email=user.email, hashed_password=hashed_password)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@app.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")





@app.post("/quizzes", response_model=schemas.QuizOut, status_code=status.HTTP_201_CREATED)
async def create_quiz(quiz: schemas.QuizCreate, current_user: schemas.User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not quiz.questions:
        raise HTTPException(status_code=400, detail="Quiz must have at least one question")
    for q in quiz.questions:
        if not q.options or len(q.options) < 2:
            raise HTTPException(status_code=400, detail="Each question must have at least two options")
    for q in quiz.questions:
        if not q.correct_option or q.correct_option not in q.options:
            raise HTTPException(status_code=400, detail="Each question must have a valid correct option")

    short_code = generate_short_code()
    db_quiz = schemas.Quizzes(user_id=current_user.id, title=quiz.title, description=quiz.description, publisher=current_user.username, short_code=short_code)
    session.add(db_quiz)
    session.flush()  # assigns db_quiz.id without committing the transaction

    for q in quiz.questions:
        db_question = schemas.Questions(quiz_id=db_quiz.id, question_text=q.question_text, options=q.options, correct_option=q.correct_option)
        session.add(db_question)

    session.commit()
    session.refresh(db_quiz)
    return db_quiz

@app.get("/quizzes", response_model=list[schemas.QuizOut])
async def get_quizzes(current_user: schemas.User = Depends(get_current_user), session: Session = Depends(get_session)):
    quizzes = session.exec(select(schemas.Quizzes).where(schemas.Quizzes.user_id == current_user.id)).all()
    
    return quizzes

@app.get("/quizzes/{quiz_id}", response_model=schemas.QuizOut)
async def get_quiz(quiz_id: int, current_user: schemas.User = Depends(get_current_user), session: Session = Depends(get_session)):
    quiz = session.exec(select(schemas.Quizzes).where(schemas.Quizzes.id == quiz_id, schemas.Quizzes.user_id == current_user.id)).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = session.exec(select(schemas.Questions).where(schemas.Questions.quiz_id == quiz.id)).all()
    quiz_out = schemas.QuizOut.model_validate(quiz)
    quiz_out.questions = [schemas.QuestionOut.model_validate(q) for q in questions]
    return quiz_out
    

@app.delete("/quizzes/delete/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(quiz_id: int, current_user: schemas.User = Depends(get_current_user), session: Session = Depends(get_session)):
    quiz = session.exec(select(schemas.Quizzes).where(schemas.Quizzes.id == quiz_id, schemas.Quizzes.user_id == current_user.id)).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = session.exec(select(schemas.Questions).where(schemas.Questions.quiz_id == quiz.id)).all()
    for question in questions:
        session.delete(question)
    session.delete(quiz)
    session.commit()
    return None



@app.get("/quizzes/public/{short_code}")
async def get_quiz_by_short_code(short_code: str, session: Session = Depends(get_session)):
    quiz = session.exec(select(schemas.Quizzes).where(schemas.Quizzes.short_code == short_code)).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = session.exec(select(schemas.Questions).where(schemas.Questions.quiz_id == quiz.id)).all()
    return {
    "quiz": schemas.QuizOut.model_validate(quiz),
    "questions": [schemas.QuestionOut.model_validate(q) for q in questions],
    }

@app.post("/quizzes/public/{short_code}/submit")
async def submit_quiz(short_code: str, answers: schemas.SubmitAnswers, session: Session = Depends(get_session)):
    quiz = session.exec(select(schemas.Quizzes).where(schemas.Quizzes.short_code == short_code)).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = session.exec(select(schemas.Questions).where(schemas.Questions.quiz_id == quiz.id)).all()
    score = 0
    for question in questions:
        if answers.answers.get(question.id) == question.correct_option:
            score += 1
    return {"score": score, "total_questions": len(questions)}

