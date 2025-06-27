from typing import Optional
from models.documents import ClientDocument

class DocumentRepository:
    def get_by_id(self, document_id: int) -> Optional[ClientDocument]:
        return ClientDocument.query.filter_by(id=document_id).first()