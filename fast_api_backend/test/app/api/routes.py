from fastapi import APIRouter
from pydantic import BaseModel
from app.nlp.parser import parse_question
from app.sparql.client import query_sparql

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str

@router.post("/ask")
async def ask_question(req: QuestionRequest):
    # NLP parse -> SPARQL
    sparql_query = parse_question(req.question)
    # Run SPARQL query
    answer = query_sparql(sparql_query)
    return {"question": req.question, "answer": answer}
