from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID

from core.deps import CurrentUser, DB, Pages
from models.core import Document, DocumentCategory, DocumentRevision

router = APIRouter()


class DocumentCreate(BaseModel):
    project_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    doc_number: Optional[str] = None
    title: str
    title_ar: Optional[str] = None
    description: Optional[str] = None
    file_url: str
    file_size: Optional[int] = None
    file_mime: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    category_id: Optional[UUID] = None


class NewRevision(BaseModel):
    file_url: str
    file_size: Optional[int] = None
    change_summary: Optional[str] = None


def _to_dict(d: Document) -> dict:
    return {
        "id": str(d.id),
        "project_id": str(d.project_id) if d.project_id else None,
        "category_id": str(d.category_id) if d.category_id else None,
        "doc_number": d.doc_number,
        "title": d.title,
        "title_ar": d.title_ar,
        "file_url": d.file_url,
        "version": d.version,
        "revision": d.revision,
        "status": d.status,
        "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
    }


@router.get("/")
async def list_documents(
    current_user: CurrentUser, db: DB, pages: Pages,
    project_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    search: Optional[str] = None,
):
    query = select(Document)
    if project_id:
        query = query.where(Document.project_id == project_id)
    if category_id:
        query = query.where(Document.category_id == category_id)
    if search:
        query = query.where(or_(
            Document.title.ilike(f"%{search}%"),
            Document.title_ar.ilike(f"%{search}%"),
            Document.doc_number.ilike(f"%{search}%"),
        ))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Document.uploaded_at.desc()).offset(pages.offset).limit(pages.size)
    result = await db.execute(query)

    return {"total": total, "page": pages.page, "size": pages.size,
            "items": [_to_dict(d) for d in result.scalars().all()]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_document(body: DocumentCreate, current_user: CurrentUser, db: DB):
    doc = Document(uploaded_by=current_user.id, **body.model_dump(exclude_none=True))
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return _to_dict(doc)


@router.get("/{document_id}")
async def get_document(document_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    rev_result = await db.execute(
        select(DocumentRevision).where(DocumentRevision.document_id == document_id)
        .order_by(DocumentRevision.uploaded_at.desc())
    )
    data = _to_dict(doc)
    data["revisions"] = [
        {"version": r.version, "revision": r.revision, "file_url": r.file_url,
         "change_summary": r.change_summary, "uploaded_at": r.uploaded_at.isoformat()}
        for r in rev_result.scalars().all()
    ]
    return data


@router.put("/{document_id}")
async def update_document(document_id: UUID, body: DocumentUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    await db.commit()
    return _to_dict(doc)


@router.post("/{document_id}/approve")
async def approve_document(document_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = "approved"
    doc.approved_by = current_user.id
    doc.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(doc.id), "status": "approved"}


@router.post("/{document_id}/revisions", status_code=201)
async def add_revision(document_id: UUID, body: NewRevision, current_user: CurrentUser, db: DB):
    """Upload a new revision — bumps revision letter and archives the old file_url."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Archive current as a revision record
    archive = DocumentRevision(
        document_id=doc.id, version=doc.version, revision=doc.revision,
        file_url=doc.file_url, file_size=doc.file_size,
        change_summary="Previous version", uploaded_by=doc.uploaded_by,
    )
    db.add(archive)

    # Bump revision letter (A -> B -> C...)
    next_rev = chr(ord(doc.revision[0]) + 1) if doc.revision and doc.revision[0].isalpha() else "B"
    doc.revision = next_rev
    doc.file_url = body.file_url
    doc.file_size = body.file_size
    doc.status = "under_review"

    await db.commit()
    return {"id": str(doc.id), "new_revision": next_rev}


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()


@router.get("/categories/list")
async def list_categories(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(DocumentCategory).where(DocumentCategory.company_id == current_user.company_id)
    )
    return [
        {"id": str(c.id), "name": c.name, "name_ar": c.name_ar, "code": c.code}
        for c in result.scalars().all()
    ]
