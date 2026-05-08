# -*- coding: utf-8 -*-
"""Model management routes.

Provides model metadata management and best model settings.
"""
import json
import os
import uuid
import threading
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db, Model, ModelFile
from backend.schemas import ModelCreate, ModelUpdate, ModelResponse, ModelExportRequest, ModelExportResponse, ModelFileResponse
from backend.websocket_manager import ws_manager

router = APIRouter()

# Model storage root directory (unified DATA_DIR)
_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
_DATA_DIR = os.environ.get("DATA_DIR", _DEFAULT_DATA_DIR)
MODEL_STORAGE_DIR = os.path.join(_DATA_DIR, "uploads", "models")


def _detect_format(file_path: str) -> str:
    """Detect model format by file extension."""
    suffix = os.path.splitext(file_path)[1].lower()
    format_map = {
        ".pt": "yolo_pt",
        ".pth": "pytorch",
        ".onnx": "onnx",
        ".xml": "openvino",
        ".engine": "tensorrt",
        ".plan": "tensorrt",
    }
    return format_map.get(suffix, "yolo_pt")


def _build_model_file_response(mf: ModelFile) -> ModelFileResponse:
    """Build ModelFileResponse."""
    return ModelFileResponse(
        id=mf.id,
        model_id=mf.model_id,
        format=mf.format,
        file_path=mf.file_path,
        file_size=mf.file_size,
        precision=mf.precision or "fp32",
        is_default=mf.is_default,
        created_at=mf.created_at,
    )


def _build_model_response(m: Model, db: Session = None) -> ModelResponse:
    """Build ModelResponse, helper function."""
    # Get file list from model_files table via direct query
    if db is not None:
        model_files = db.query(ModelFile).filter(ModelFile.model_id == m.id).all()
        files = [_build_model_file_response(mf) for mf in model_files]
        available_formats = [mf.format for mf in model_files]
    else:
        files = []
        available_formats = []

    return ModelResponse(
        id=m.id,
        name=m.name,
        version=m.version,
        pretrained_model=m.pretrained_model,
        file_path=m.file_path,
        format=m.format or "yolo_pt",
        device_preference=m.device_preference or "auto",
        precision=m.precision or "fp32",
        atlas_id=m.atlas_id,
        metrics=json.loads(m.metrics) if m.metrics else None,
        is_best=m.is_best,
        created_at=m.created_at,
        files=files,
        available_formats=available_formats,
        input_shape=m.input_shape,
    )


@router.get("", response_model=List[ModelResponse])
async def list_models(db: Session = Depends(get_db)):
    """Get model list."""
    models = db.query(Model).order_by(Model.created_at.desc()).all()
    return [_build_model_response(m, db) for m in models]


@router.post("", response_model=ModelResponse, status_code=201)
async def create_model(data: ModelCreate, db: Session = Depends(get_db)):
    """Create new model record."""
    # Check if name+version combination already exists
    existing = db.query(Model).filter(
        Model.name == data.name,
        Model.version == data.version
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Model '{data.name}' (version: {data.version or 'none'}) already exists")

    model = Model(
        name=data.name,
        version=data.version,
        pretrained_model=data.pretrained_model,
        file_path=data.file_path,
        atlas_id=data.atlas_id,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return _build_model_response(model, db)


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int, db: Session = Depends(get_db)):
    """Get model details."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    return _build_model_response(m, db)


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: int,
    data: ModelUpdate,
    db: Session = Depends(get_db)
):
    """Update model."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    if data.name is not None:
        m.name = data.name
    if data.version is not None:
        m.version = data.version
    if data.pretrained_model is not None:
        m.pretrained_model = data.pretrained_model
    if data.file_path is not None:
        m.file_path = data.file_path
    if data.metrics is not None:
        m.metrics = json.dumps(data.metrics)
    if data.available_formats is not None:
        m.available_formats = json.dumps(data.available_formats)
    if data.device_preference is not None:
        m.device_preference = data.device_preference
    if data.precision is not None:
        m.precision = data.precision
    if data.input_shape is not None:
        m.input_shape = data.input_shape

    db.commit()
    db.refresh(m)
    return _build_model_response(m, db)


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: int, db: Session = Depends(get_db)):
    """Delete model (cascade delete all format files)."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    # Delete all associated format files (direct query)
    model_files = db.query(ModelFile).filter(ModelFile.model_id == model_id).all()
    for mf in model_files:
        if os.path.exists(mf.file_path):
            try:
                os.remove(mf.file_path)
            except OSError:
                pass

    db.delete(m)
    db.commit()
    return None


@router.post("/{model_id}/set-best", response_model=ModelResponse)
async def set_best_model(model_id: int, db: Session = Depends(get_db)):
    """Set model as best model."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    # Cancel other best models
    db.query(Model).filter(Model.is_best == True).update({"is_best": False})

    m.is_best = True
    db.commit()
    db.refresh(m)
    return _build_model_response(m, db)


@router.post("/{model_id}/upload", response_model=ModelResponse)
async def upload_model_file(
    model_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload model file."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    # Ensure upload directory exists
    os.makedirs(MODEL_STORAGE_DIR, exist_ok=True)

    # Save model file
    file_path = os.path.join(MODEL_STORAGE_DIR, f"model_{model_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Parse model ckpt, extract metrics metadata
    try:
        from ultralytics import YOLO
        detector = YOLO(file_path)
        ckpt = detector.ckpt
        # Safe extraction of fields
        def safe_get(d, *keys, default=None):
            for k in keys:
                if d is None:
                    return default
                if isinstance(d, dict):
                    d = d.get(k)
                elif isinstance(d, (list, tuple)):
                    d = d[k] if k < len(d) else None
                else:
                    d = getattr(d, k, None)
                if d is None:
                    return default
            return d

        names = safe_get(ckpt, "model", "names") or {}
        yaml_info = safe_get(ckpt, "model", "yaml") or {}
        nc = safe_get(yaml_info, "nc", default=len(names)) or len(names)
        train_metrics = safe_get(ckpt, "train_metrics") or {}

        categories = [{"id": int(k), "name": str(v)} for k, v in (names or {}).items()]

        parsed_metrics = {
            "num_classes": nc or 0,
            "categories": categories,
            "precision": train_metrics.get("metrics/precision(B)") if train_metrics else None,
            "recall": train_metrics.get("metrics/recall(B)") if train_metrics else None,
            "mAP50": train_metrics.get("metrics/mAP50(B)") if train_metrics else None,
            "mAP50-95": train_metrics.get("metrics/mAP50-95(B)") if train_metrics else None,
            "fitness": train_metrics.get("fitness") if train_metrics else None,
            "best_epoch": ckpt.get("epoch") if ckpt else None,
        }
        m.metrics = json.dumps(parsed_metrics)
    except Exception as e:
        # Parsing failure does not affect upload, just log
        import logging
        logging.getLogger(__name__).warning(f"Failed to parse model metadata: {e}")

    # Update model record
    m.file_path = file_path

    # Auto-detect format and create ModelFile record
    detected_format = _detect_format(file_path)

    # If this is the first file of this format, set as default
    existing_formats = [mf.format for mf in db.query(ModelFile).filter(ModelFile.model_id == m.id).all()]
    is_first_of_format = detected_format not in existing_formats
    is_default = is_first_of_format and len(existing_formats) == 0

    model_file = ModelFile(
        model_id=m.id,
        format=detected_format,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        precision="fp32",
        is_default=is_default,
    )
    db.add(model_file)

    # Update Model's format and available_formats compatible fields
    if not m.format:
        m.format = detected_format

    db.commit()
    db.refresh(m)

    return _build_model_response(m, db)


@router.get("/{model_id}/training-history")
async def get_model_training_history(model_id: int, db: Session = Depends(get_db)):
    """Get model's training history."""
    from backend.database import TrainingJob

    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    jobs = db.query(TrainingJob).filter(
        TrainingJob.model_id == model_id
    ).order_by(TrainingJob.started_at.desc()).all()

    results = []
    for job in jobs:
        results.append({
            "id": job.id,
            "status": job.status,
            "config": json.loads(job.config) if job.config else None,
            "current_step": job.current_step,
            "total_steps": job.total_steps,
            "metrics": json.loads(job.metrics) if job.metrics else None,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        })
    return results


@router.get("/{model_id}/download")
async def download_model(model_id: int, db: Session = Depends(get_db)):
    """Download model file."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    if not m.file_path or not os.path.exists(m.file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    filename = os.path.basename(m.file_path)
    return FileResponse(m.file_path, filename=filename)


@router.post("/{model_id}/export", response_model=dict)
async def export_model_async(
    model_id: int,
    data: ModelExportRequest,
    db: Session = Depends(get_db)
):
    """Export model to specified format (async with progress push).

    Args:
        model_id: Model ID
        data: Export request, including target format, half precision, etc.

    Returns:
        Export task ID, frontend can subscribe to progress via WebSocket
    """
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    if not m.file_path or not os.path.exists(m.file_path):
        raise HTTPException(status_code=400, detail="Model file not found")

    # Check if YOLO .pt model
    if m.format and m.format != "yolo_pt":
        raise HTTPException(status_code=400, detail="Only export from YOLO .pt format is supported")

    # Generate export task ID
    export_id = str(uuid.uuid4())[:8]

    # Start background export task
    thread = threading.Thread(
        target=_export_model_background,
        args=(model_id, export_id, data.target_format, data.half),
        daemon=True,
    )
    thread.start()

    return {
        "export_id": export_id,
        "status": "started",
        "message": "Export started",
    }


def _export_model_background(model_id: int, export_id: str, target_format: str, half: bool):
    """Background model export, push progress via WebSocket."""
    from backend.database import SessionLocal
    import asyncio

    db = SessionLocal()
    try:
        # Send start progress
        asyncio.run(ws_manager.send_export_update(export_id, {
            "status": "starting",
            "progress": 0,
            "message": "Preparing export...",
        }))

        m = db.query(Model).filter(Model.id == model_id).first()
        if not m:
            asyncio.run(ws_manager.send_export_update(export_id, {
                "status": "error",
                "progress": 0,
                "message": "Model not found",
            }))
            return

        # Send loading model progress
        asyncio.run(ws_manager.send_export_update(export_id, {
            "status": "loading",
            "progress": 20,
            "message": "Loading model...",
        }))

        # Check if format already exists and delete old file before creating new
        precision = "fp16" if half else "fp32"
        existing_file = db.query(ModelFile).filter(
            ModelFile.model_id == m.id,
            ModelFile.format == target_format
        ).first()

        if existing_file and os.path.exists(existing_file.file_path):
            try:
                os.remove(existing_file.file_path)
            except OSError:
                pass

        # Execute export (new file overwrites old at same path)
        try:
            from backend.core.export import export_model

            result = export_model(
                model_path=m.file_path,
                target_format=target_format,
                output_dir=MODEL_STORAGE_DIR,
                half=half,
            )

            # Send saving progress
            asyncio.run(ws_manager.send_export_update(export_id, {
                "status": "saving",
                "progress": 80,
                "message": "Saving file...",
            }))

            if existing_file:
                # Update record
                existing_file.file_path = result["output_path"]
                existing_file.file_size = result["file_size"]
                existing_file.precision = precision
            else:
                # Create new ModelFile record
                model_file = ModelFile(
                    model_id=m.id,
                    format=target_format,
                    file_path=result["output_path"],
                    file_size=result["file_size"],
                    precision=precision,
                    is_default=False,
                )
                db.add(model_file)

            # Update Model's available_formats compatible field
            model_files = db.query(ModelFile).filter(ModelFile.model_id == m.id).all()
            available_formats = [mf.format for mf in model_files]
            if target_format not in available_formats:
                available_formats.append(target_format)
            m.available_formats = json.dumps(available_formats)
            db.commit()

            # Send completion
            asyncio.run(ws_manager.send_export_update(export_id, {
                "status": "completed",
                "progress": 100,
                "message": "Export completed",
                "output_path": result["output_path"],
                "file_size": result["file_size"],
                "available_formats": available_formats,
                "target_format": target_format,
            }))

        except Exception as e:
            asyncio.run(ws_manager.send_export_update(export_id, {
                "status": "error",
                "progress": 0,
                "message": f"Export failed: {str(e)}",
            }))

    finally:
        db.close()


# Keep old sync export endpoint (compatible)
@router.post("/{model_id}/export/sync", response_model=ModelExportResponse)
async def export_model_sync(
    model_id: int,
    data: ModelExportRequest,
    db: Session = Depends(get_db)
):
    """Export model to specified format (sync, no progress push)."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    if not m.file_path or not os.path.exists(m.file_path):
        raise HTTPException(status_code=400, detail="Model file not found")

    # Check if YOLO .pt model
    if m.format and m.format != "yolo_pt":
        raise HTTPException(status_code=400, detail="Only export from YOLO .pt format is supported")

    # Check if format already exists and delete old file before creating new
    precision = "fp16" if data.half else "fp32"
    existing_file = db.query(ModelFile).filter(
        ModelFile.model_id == m.id,
        ModelFile.format == data.target_format
    ).first()

    if existing_file and os.path.exists(existing_file.file_path):
        try:
            os.remove(existing_file.file_path)
        except OSError:
            pass

    # Execute export (new file overwrites old at same path)
    try:
        from backend.core.export import export_model

        result = export_model(
            model_path=m.file_path,
            target_format=data.target_format,
            output_dir=MODEL_STORAGE_DIR,
            half=data.half,
        )

        if existing_file:
            # Update record
            existing_file.file_path = result["output_path"]
            existing_file.file_size = result["file_size"]
            existing_file.precision = precision
        else:
            # Create new ModelFile record
            model_file = ModelFile(
                model_id=m.id,
                format=data.target_format,
                file_path=result["output_path"],
                file_size=result["file_size"],
                precision=precision,
                is_default=False,
            )
            db.add(model_file)

        # Update Model's available_formats compatible field
        model_files = db.query(ModelFile).filter(ModelFile.model_id == m.id).all()
        available_formats = [mf.format for mf in model_files]
        if data.target_format not in available_formats:
            available_formats.append(data.target_format)
        m.available_formats = json.dumps(available_formats)
        db.commit()
        db.refresh(m)

        return ModelExportResponse(
            success=result["success"],
            output_path=result["output_path"],
            file_size=result["file_size"],
            available_formats=available_formats,
            target_format=data.target_format,
            half=data.half,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


# ============ ModelFile CRUD ============

@router.get("/{model_id}/files", response_model=List[ModelFileResponse])
async def list_model_files(model_id: int, db: Session = Depends(get_db)):
    """Get all format files associated with the model."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    model_files = db.query(ModelFile).filter(ModelFile.model_id == model_id).all()
    return [_build_model_file_response(mf) for mf in model_files]


@router.delete("/{model_id}/files/{file_id}", status_code=204)
async def delete_model_file(model_id: int, file_id: int, db: Session = Depends(get_db)):
    """Delete specific format file of the model."""
    mf = db.query(ModelFile).filter(
        ModelFile.id == file_id,
        ModelFile.model_id == model_id
    ).first()
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete physical file
    if os.path.exists(mf.file_path):
        try:
            os.remove(mf.file_path)
        except OSError:
            pass

    db.delete(mf)
    db.commit()
    return None


@router.post("/{model_id}/files/{file_id}/set-default", response_model=ModelResponse)
async def set_default_format(model_id: int, file_id: int, db: Session = Depends(get_db)):
    """Set default inference format for the model."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    mf = db.query(ModelFile).filter(
        ModelFile.id == file_id,
        ModelFile.model_id == model_id
    ).first()
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")

    # Cancel all is_default for this format (direct query)
    model_files = db.query(ModelFile).filter(ModelFile.model_id == model_id).all()
    for f in model_files:
        f.is_default = (f.id == file_id)

    # Update Model's format field
    m.format = mf.format
    db.commit()
    db.refresh(m)
    return _build_model_response(m, db)


@router.get("/{model_id}/files/{file_id}/download")
async def download_model_file(model_id: int, file_id: int, db: Session = Depends(get_db)):
    """Download specific format file of the model."""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    mf = db.query(ModelFile).filter(
        ModelFile.id == file_id,
        ModelFile.model_id == model_id
    ).first()
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(mf.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    filename = os.path.basename(mf.file_path)
    return FileResponse(mf.file_path, filename=filename)