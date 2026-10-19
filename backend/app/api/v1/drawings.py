"""Handwriting practice: save, list and delete the user's drawings of a word."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Entry, User
from app.schemas.drawing import DrawingCreateRequest, DrawingGalleryResponse, DrawingItem
from app.services import drawing_service
from app.services.version_service import get_user_version

router = APIRouter(prefix="/drawings", tags=["drawings"])


@router.get(
    "",
    response_model=list[DrawingItem],
    summary="List the authenticated user's drawings of one entry, newest first.",
)
def list_drawings(
    entry_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DrawingItem]:
    rows = drawing_service.list_for_entry(db, user_id=user.id, entry_id=entry_id)
    return [DrawingItem(**drawing_service.to_item(r)) for r in rows]


@router.get(
    "/gallery",
    response_model=DrawingGalleryResponse,
    summary="The user's drawings grouped by word (latest few per word), most recent word first.",
)
def drawings_gallery(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DrawingGalleryResponse:
    return DrawingGalleryResponse(
        **drawing_service.gallery(
            db, user_id=user.id, limit=limit, offset=offset, version=get_user_version(db, user.id)
        )
    )


@router.post(
    "",
    response_model=DrawingItem,
    status_code=status.HTTP_201_CREATED,
    summary="Save a handwriting drawing (PNG data URL) for an entry.",
)
def create_drawing(
    payload: DrawingCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DrawingItem:
    if db.get(Entry, payload.entry_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mot introuvable.")
    try:
        png, width, height = drawing_service.decode_png(payload.image)
    except drawing_service.InvalidDrawingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if drawing_service.count_for_user(db, user.id) >= drawing_service.MAX_DRAWINGS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Limite de {drawing_service.MAX_DRAWINGS_PER_USER} dessins atteinte : "
                "supprime d'anciens dessins depuis la page Compte."
            ),
        )
    row = drawing_service.save_drawing(
        db, user_id=user.id, entry_id=payload.entry_id, png=png, width=width, height=height
    )
    return DrawingItem(**drawing_service.to_item(row))


@router.delete(
    "/{drawing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one of the user's drawings.",
)
def remove_drawing(
    drawing_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if not drawing_service.delete_drawing(db, user_id=user.id, drawing_id=drawing_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dessin introuvable.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
