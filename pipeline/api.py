"""파일 기반 job API 스켈레톤."""
from __future__ import annotations

from pathlib import Path
from threading import Lock

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from pipeline import config
from pipeline import jobs
from pipeline import main as pipeline_main

app = FastAPI(title="Dullizze Shorts API", version="0.1.0")
WORKER_LOCK = Lock()
DASHBOARD_PATH = config.ROOT / "web" / "dashboard.html"


class JobCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    tone: str | None = None
    template: str | None = None
    job_id: str | None = None
    auto_start: bool = True


def _job_dir_from_manifest(job: dict) -> Path:
    return config.ROOT / job["run_dir"]


def _set_queued(job: dict) -> dict:
    out_dir = _job_dir_from_manifest(job)
    job["status"] = "queued"
    job["step"] = "queued"
    job["error"] = None
    jobs.write_job(out_dir, job)
    return job


def _run_job(job_id: str, run_dir: str) -> None:
    out_dir = config.ROOT / run_dir
    with WORKER_LOCK:
        try:
            job = jobs.read_job_path(out_dir / "job.json")
            pipeline_main.run(
                job["topic"],
                tone=job.get("tone"),
                template=job.get("template"),
                job_id=job_id,
                out_dir=out_dir,
            )
        except Exception as e:  # noqa: BLE001 - background task failure must be recorded
            job_path = out_dir / "job.json"
            job = jobs.read_job_path(job_path) if job_path.exists() else {"job_id": job_id}
            job["status"] = "failed"
            job["step"] = job.get("step") or "background"
            job["error"] = {"step": job["step"], "message": str(e)}
            jobs.write_job(out_dir, job)


def _enqueue(job: dict, background_tasks: BackgroundTasks) -> dict:
    queued = _set_queued(job)
    background_tasks.add_task(_run_job, queued["job_id"], queued["run_dir"])
    return queued


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))


@app.post("/jobs", status_code=201)
def create_job(payload: JobCreate, background_tasks: BackgroundTasks) -> dict:
    topic = payload.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic은 비워둘 수 없습니다.")
    try:
        job = jobs.create_manifest(
            topic=topic,
            tone=payload.tone,
            template=payload.template,
            job_id=payload.job_id,
            overwrite=False,
        )
        if payload.auto_start:
            return _enqueue(job, background_tasks)
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@app.get("/jobs/{job_id}")
def get_job(job_id: str, run_date: str | None = Query(default=None, alias="date")) -> dict:
    try:
        return jobs.read_job(job_id, run_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/jobs/{job_id}/run")
def run_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    run_date: str | None = Query(default=None, alias="date"),
) -> dict:
    try:
        job = jobs.read_job(job_id, run_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if job.get("status") in {"queued", "running"}:
        raise HTTPException(status_code=409, detail=f"이미 실행 중입니다: {job['job_id']}")
    return _enqueue(job, background_tasks)


@app.get("/jobs/{job_id}/video")
def get_job_video(job_id: str, run_date: str | None = Query(default=None, alias="date")) -> FileResponse:
    try:
        out_dir = jobs.find_job_dir(job_id, run_date)
        job = jobs.read_job_path(out_dir / "job.json")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    video = job.get("artifacts", {}).get("video")
    if not video:
        raise HTTPException(status_code=404, detail="video artifact가 아직 없습니다.")

    video_path = (out_dir / video).resolve()
    if out_dir.resolve() not in video_path.parents or not video_path.exists():
        raise HTTPException(status_code=404, detail="video 파일을 찾을 수 없습니다.")
    return FileResponse(Path(video_path), media_type="video/mp4", filename=video_path.name)
