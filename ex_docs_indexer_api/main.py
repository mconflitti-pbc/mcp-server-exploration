from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl
from langchain.document_loaders import UnstructuredURLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
import chromadb
import joblib
import os
import uuid
from enum import Enum
from typing import Dict

class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class URLInput(BaseModel):
    url: HttpUrl

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    url: str
    error: str = None

app = FastAPI()
jobs: Dict[str, JobStatusResponse] = {}

SAVE_PATH = "chroma_backup.joblib"

# Initialize in-memory ChromaDB
client = chromadb.Client()
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(
    client=client,
    embedding_function=embeddings
)

def save_db():
    """Save ChromaDB state using joblib"""
    db_state = {
        "client": client._state,
        "collections": client.list_collections()
    }
    joblib.dump(db_state, SAVE_PATH)

def load_db():
    """Load ChromaDB state from joblib file"""
    if os.path.exists(SAVE_PATH):
        db_state = joblib.load(SAVE_PATH)
        client._state = db_state["client"]

async def process_url(job_id: str, url: str):
    try:
        jobs[job_id].status = JobStatus.PROCESSING

        loader = UnstructuredURLLoader(urls=[url])
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)

        db.add_documents(splits)
        save_db()

        jobs[job_id].status = JobStatus.COMPLETED
    except Exception as e:
        jobs[job_id].status = JobStatus.FAILED
        jobs[job_id].error = str(e)

@app.post("/process-url", response_model=JobStatusResponse)
async def create_process(url_input: URLInput, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobStatusResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        url=str(url_input.url)
    )

    background_tasks.add_task(process_url, job_id, str(url_input.url))
    return jobs[job_id]

@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
