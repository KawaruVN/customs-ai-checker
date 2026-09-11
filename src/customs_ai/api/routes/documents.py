from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from customs_ai.ingestion.errors import IngestionError
from customs_ai.ingestion.models import UploadResponse
from customs_ai.ingestion.service import IngestionService
from customs_ai.logger import logger
from customs_ai.repositories.source_documents import SourceDocumentRepository

router = APIRouter(tags=["documents"])
repository = SourceDocumentRepository()
service = IngestionService(repository)


@router.post("/shipments/{shipment_id}/documents", response_model=UploadResponse)
async def upload_document(
    shipment_id: str,
    response: Response,
    file: UploadFile = File(...),
) -> UploadResponse:
    try:
        result, status_code = await service.ingest(shipment_id, file)
        response.status_code = status_code
        return result
    except IngestionError as exc:
        if exc.http_status >= 500:
            logger.error("Ingestion failed with code %s.", exc.code)
        else:
            logger.warning("Upload rejected with code %s.", exc.code)
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except Exception as exc:
        logger.error("Unhandled ingestion error.", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred.",
            },
        ) from exc
