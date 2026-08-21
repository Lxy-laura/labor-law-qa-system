"""
劳动合同纠纷智能问答系统 - 知识库管理接口（SQLite 版本）
"""
import os
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from database import get_db
from models.schemas import DocumentInfo, DocumentListResponse, UploadResponse
from auth.decorators import get_current_user, require_admin

router = APIRouter(prefix="/api/kb", tags=["知识库管理"])


@router.get("/documents", response_model=DocumentListResponse, summary="获取文档列表")
def list_documents(db=Depends(get_db), user: dict = Depends(get_current_user)):
    """获取知识库中的所有文档列表"""
    cur = db.cursor()
    cur.execute("""
        SELECT id, title, doc_type, chunk_count, created_at
        FROM documents
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()

    docs = []
    for row in rows:
        docs.append(DocumentInfo(
            id=row["id"],
            title=row["title"],
            doc_type=row["doc_type"],
            chunk_count=row["chunk_count"],
            created_at=row["created_at"]
        ))
    return DocumentListResponse(documents=docs, total=len(docs))
@router.get("/stats", summary="获取知识库统计信息")
def get_kb_stats(db=Depends(get_db), user: dict = Depends(get_current_user)):
    """获取知识库统计信息：文档总数、分类统计"""
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM documents")
    total_documents = cur.fetchone()["count"]

    cur.execute("""
        SELECT doc_type, COUNT(*) AS count
        FROM documents
        GROUP BY doc_type
    """)
    by_category = {}
    for row in cur.fetchall():
        by_category[row["doc_type"] or "未分类"] = row["count"]

    cur.close()

    return {
        "totalDocuments": total_documents,
        "byCategory": by_category
    }

@router.post("/upload", response_model=UploadResponse, summary="上传文档到知识库")
async def upload_document(
    file: UploadFile = File(..., description="文档文件（.txt/.pdf/.docx）"),
    title: str = Form(..., description="文档标题"),
    doc_type: str = Form("法律法规", description="文档类型"),
    db=Depends(get_db),
    user: dict = Depends(require_admin)
):
    """上传文档到知识库（仅管理员）"""
    # 读取文件内容
    content = await file.read()
    file_ext = os.path.splitext(file.filename)[1].lower()

    # 根据文件类型解析文本内容
    text_content = ""
    if file_ext == ".txt":
        text_content = content.decode("utf-8")
    elif file_ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
            text_content = "\n".join([page.get_text() for page in doc])
            doc.close()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF 解析失败: {str(e)}")
    elif file_ext == ".docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            text_content = "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"DOCX 解析失败: {str(e)}")
    else:
        raise HTTPException(
            status_code=400,
            detail="不支持的文件格式，请上传 .txt、.pdf 或 .docx 文件"
        )

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="文档内容为空")

    # 文本分块
    chunks = chunk_text(text_content, chunk_size=500, overlap=50)

    # 保存文档元数据到数据库
    cur = db.cursor()
    cur.execute(
        """INSERT INTO documents (title, content, doc_type, file_path, chunk_count, uploaded_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (title, text_content, doc_type, file.filename, len(chunks), user["user_id"])
    )
    doc_id = cur.lastrowid
    db.commit()
    cur.close()

    # 向量化分块并存入 Milvus（失败不影响文档保存）
    try:
        from rag.embedder import get_embedder
        from rag.retriever import get_retriever

        embedder = get_embedder()
        retriever = get_retriever()

        embeddings = embedder.encode(chunks)
        retriever.insert_documents(chunks, embeddings, doc_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"向 Milvus 插入文档向量失败: {e}")

    return UploadResponse(
        document_id=doc_id,
        title=title,
        chunk_count=len(chunks),
        message="文档上传成功"
    )


@router.delete("/documents/{document_id}", summary="删除知识库文档")
def delete_document(
    document_id: int,
    db=Depends(get_db),
    user: dict = Depends(require_admin)
):
    """删除知识库中的指定文档（仅管理员）"""
    cur = db.cursor()

    cur.execute("SELECT id FROM documents WHERE id = ?", (document_id,))
    if not cur.fetchone():
        cur.close()
        raise HTTPException(status_code=404, detail="文档不存在")

    cur.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    db.commit()
    cur.close()

    return {"message": "文档删除成功", "document_id": document_id}


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """将长文本切分为重叠的块"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks
