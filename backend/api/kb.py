"""
劳动合同纠纷智能问答系统 - 知识库管理接口（SQLite 版本）

本文件管理知识库文档的增删查改，上传的文档会参与问答系统的 BM25 检索。
"""
import os
import io
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from database import get_db
from models.schemas import DocumentInfo, DocumentListResponse, UploadResponse
from auth.decorators import get_current_user, require_admin

logger = logging.getLogger(__name__)

# 关闭 pdfminer 的 DEBUG 日志，避免大量调试输出拖慢处理速度
logging.getLogger('pdfminer').setLevel(logging.WARNING)
logging.getLogger('pdfplumber').setLevel(logging.WARNING)

router = APIRouter(prefix="/api/kb", tags=["知识库管理"])


@router.get("/documents", summary="获取文档列表")
def list_documents(
    keyword: str = Query("", description="搜索关键词（按标题模糊匹配）"),
    doc_type: str = Query("", description="文档类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=100, description="每页数量"),
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """获取知识库中的所有文档列表，支持按标题关键词和文档类型筛选"""
    cur = db.cursor()

    # 构建查询条件和参数
    where_clauses = []
    params = []

    if keyword:
        where_clauses.append("title LIKE ?")
        params.append(f"%{keyword}%")

    if doc_type:
        where_clauses.append("doc_type = ?")
        params.append(doc_type)

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # 查询总数
    count_sql = f"SELECT COUNT(*) AS count FROM documents{where_sql}"
    cur.execute(count_sql, params)
    total = cur.fetchone()["count"]

    # 查询分页数据
    offset = (page - 1) * pageSize
    query_sql = f"""
        SELECT id, title, doc_type, file_size, chunk_count, indexed, created_at
        FROM documents{where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    cur.execute(query_sql, params + [pageSize, offset])
    rows = cur.fetchall()
    cur.close()

    docs = []
    for row in rows:
        docs.append({
            "id": row["id"],
            "title": row["title"],
            "doc_type": row["doc_type"] or "未分类",
            "size": row["file_size"] or 0,
            "chunk_count": row["chunk_count"],
            "chunkCount": row["chunk_count"],
            "indexed": bool(row["indexed"]) if row["indexed"] is not None else False,
            "created_at": row["created_at"],
            "createdAt": row["created_at"]
        })
    return {"list": docs, "total": total}


@router.get("/documents/{document_id}", summary="获取文档详情（含全文内容）")
def get_document_detail(
    document_id: int,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """获取单个文档的详细信息，包括全文内容（用于预览）"""
    cur = db.cursor()
    cur.execute("""
        SELECT id, title, content, doc_type, file_size, chunk_count, indexed, created_at
        FROM documents WHERE id = ?
    """, (document_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        raise HTTPException(status_code=404, detail="文档不存在")

    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"] or "",
        "doc_type": row["doc_type"],
        "file_size": row["file_size"] or 0,
        "chunk_count": row["chunk_count"],
        "indexed": bool(row["indexed"]) if row["indexed"] is not None else False,
        "created_at": row["created_at"]
    }


@router.get("/stats", summary="获取知识库统计信息")
def get_kb_stats(db=Depends(get_db), user: dict = Depends(get_current_user)):
    """获取知识库统计信息：文档总数、已索引数、待索引数、总向量数"""
    cur = db.cursor()

    # 文档总数
    cur.execute("SELECT COUNT(*) AS count FROM documents")
    total_documents = cur.fetchone()["count"]

    # 已索引文档数（indexed=1 的才算已索引）
    cur.execute("SELECT COUNT(*) AS count FROM documents WHERE indexed = 1")
    indexed_count = cur.fetchone()["count"]

    # 待索引文档数
    cur.execute("SELECT COUNT(*) AS count FROM documents WHERE indexed = 0 OR indexed IS NULL")
    pending_count = cur.fetchone()["count"]

    # 总分块数（所有文档的 chunk_count 之和）
    cur.execute("SELECT COALESCE(SUM(chunk_count), 0) AS total FROM documents")
    total_chunks = cur.fetchone()["total"]

    # 按类型分类统计
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
        "indexed": indexed_count,
        "pending": pending_count,
        "totalChunks": total_chunks,
        "byCategory": by_category
    }


@router.post("/upload", response_model=UploadResponse, summary="上传文档到知识库")
async def upload_document(
    file: UploadFile = File(..., description="文档文件（.txt/.pdf/.docx/.md）"),
    title: str = Form(..., description="文档标题"),
    doc_type: str = Form("法律法规", description="文档类型"),
    db=Depends(get_db),
    user: dict = Depends(require_admin)
):
    """上传文档到知识库（仅管理员）。上传后文档自动参与问答系统的检索。"""
    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="文件为空，请选择有效的文件")

    file_ext = os.path.splitext(file.filename)[1].lower()

    # 根据文件类型解析文本内容
    text_content = ""
    if file_ext == ".txt" or file_ext == ".md":
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text_content = content.decode("gbk")
            except UnicodeDecodeError:
                try:
                    text_content = content.decode("gb2312")
                except UnicodeDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail="文件编码无法识别，请使用 UTF-8 编码的文本文件"
                    )
    elif file_ext == ".pdf":
        text_content = _extract_pdf_text(content)
    elif file_ext == ".docx":
        text_content = _extract_docx_text(content)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 {file_ext}，请上传 .txt、.pdf、.docx 或 .md 文件"
        )

    if not text_content or not text_content.strip():
        if file_ext == ".pdf":
            raise HTTPException(
                status_code=400,
                detail="PDF 无法提取文本内容，该文件可能是扫描件或图片型 PDF。请上传 .txt 格式的文本文件，或使用 OCR 工具将 PDF 转换为文本后再上传"
            )
        elif file_ext == ".docx":
            raise HTTPException(
                status_code=400,
                detail="DOCX 文档内容为空，请检查文件是否包含有效文本内容"
            )
        else:
            raise HTTPException(status_code=400, detail="文档内容为空，无法提取文本")

    # 文本分块
    chunks = chunk_text(text_content, chunk_size=500, overlap=50)

    # 保存文档到数据库，标记为已索引（因为 BM25 检索直接用文本，不需要额外建索引）
    cur = db.cursor()
    cur.execute(
        """INSERT INTO documents (title, content, doc_type, file_path, file_size, chunk_count, indexed, uploaded_by)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
        (title, text_content, doc_type, file.filename, file_size, len(chunks), user["user_id"])
    )
    doc_id = cur.lastrowid
    db.commit()
    cur.close()

    # 重新加载 RAG 管线，让新上传的文档立即参与问答检索
    try:
        from rag.pipeline import get_pipeline
        pipeline = get_pipeline()
        pipeline.reload()
        logger.info(f"文档上传后 RAG 管线已重新加载，文档ID={doc_id}")
    except Exception as e:
        logger.warning(f"RAG 管线重新加载失败: {e}")

    return UploadResponse(
        document_id=doc_id,
        title=title,
        chunk_count=len(chunks),
        message="文档上传成功"
    )


def _extract_pdf_text(content: bytes) -> str:
    """
    从 PDF 文件中提取文本内容
    策略：
    1. PyMuPDF 文本提取（快速，适用于有文字层的 PDF）
    2. 如果 PyMuPDF 提取为空，说明是扫描件，直接跳到 OCR
       （不再浪费时间尝试 pdfplumber/pdfminer，它们对扫描件同样无效）
    3. OCR 识别（针对扫描件/图片型 PDF）
    """
    text_content = ""

    # ========== 方法1：PyMuPDF 文本提取 ==========
    try:
        import pymupdf as fitz
        doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
        pages_text = []
        for page in doc:
            page_text = page.get_text()
            if page_text:
                pages_text.append(page_text)
        doc.close()
        text_content = "\n".join(pages_text)
        if text_content.strip():
            logger.info("PyMuPDF 成功提取 PDF 文本")
            return text_content
        else:
            logger.info("PyMuPDF 提取结果为空，该 PDF 可能是扫描件，直接跳到 OCR")
    except ImportError:
        logger.warning("PyMuPDF 未安装，跳过文本提取")
    except Exception as e:
        logger.warning(f"PyMuPDF 提取失败: {e}")

    # ========== 方法2：OCR 识别（针对扫描件/图片型 PDF）==========
    # 跳过 pdfplumber 和 pdfminer，因为对扫描件 PDF 无效且极慢
    logger.info("开始 OCR 识别...")
    text_content = _ocr_pdf(content)
    if text_content.strip():
        logger.info("OCR 成功识别 PDF 文本")
    else:
        logger.warning("OCR 也未能提取文本，该 PDF 可能完全是空白图片")

    return text_content


def _ocr_pdf(content: bytes) -> str:
    """
    使用 OCR 识别 PDF 中的文字
    适用于扫描件、图片型 PDF
    流程：PyMuPDF 渲染页面为图片 → pytesseract 识别中文

    Windows 环境下需要手动指定 Tesseract 路径和 tessdata 路径，
    请根据实际安装位置修改 _TESSERACT_PATH 和 _TESSDATA_PATH。
    """
    import os
    import platform

    # ========== Windows 路径配置 ==========
    # 修改为你电脑上 Tesseract 的实际安装路径
    _TESSERACT_PATH = r'D:\installsoftware\Tesseract-OCR\tesseract.exe'
    _TESSDATA_PATH = r'D:\installsoftware\Tesseract-OCR\tessdata'

    try:
        import pymupdf as fitz
        import pytesseract
        from PIL import Image
    except ImportError as e:
        logger.warning(f"OCR 所需库未安装: {e}")
        return ""

    # Windows 下手动指定 Tesseract 路径和 tessdata 路径
    if platform.system() == 'Windows':
        if os.path.exists(_TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = _TESSERACT_PATH
        if os.path.exists(_TESSDATA_PATH):
            os.environ['TESSDATA_PREFIX'] = _TESSDATA_PATH

    try:
        doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
        ocr_texts = []
        total_pages = len(doc)

        for page_num in range(total_pages):
            page = doc[page_num]
            # 渲染页面为图片，DPI=300 保证清晰度
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)

            # 转换为 PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # OCR 识别，同时识别中文和英文
            page_text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            if page_text.strip():
                ocr_texts.append(page_text.strip())

            logger.info(f"OCR 处理第 {page_num + 1}/{total_pages} 页完成")

        doc.close()
        return "\n".join(ocr_texts)

    except Exception as e:
        logger.error(f"OCR 处理失败: {e}")
        return ""


def _extract_docx_text(content: bytes) -> str:
    """
    从 DOCX 文件中提取文本内容
    """
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        # 同时提取表格中的文本
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text)
        return "\n".join(paragraphs)
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="服务器未安装 Word 解析库（python-docx），请联系管理员安装"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DOCX 解析失败: {str(e)}")


@router.post("/documents/{document_id}/reindex", summary="重建文档索引")
def reindex_document(
    document_id: int,
    db=Depends(get_db),
    user: dict = Depends(require_admin)
):
    """重建指定文档的索引（仅管理员）。重新分块并标记为已索引。"""
    cur = db.cursor()

    # 1. 查文档是否存在，并取出 content
    cur.execute("SELECT id, title, content FROM documents WHERE id = ?", (document_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        raise HTTPException(status_code=404, detail="文档不存在")

    text_content = row["content"] or ""

    # 2. 重新分块
    chunks = chunk_text(text_content, chunk_size=500, overlap=50)

    # 3. 更新 chunk_count 和 indexed 状态
    cur.execute(
        "UPDATE documents SET chunk_count = ?, indexed = 1 WHERE id = ?",
        (len(chunks), document_id)
    )
    db.commit()
    cur.close()

    # 4. 重新加载 RAG 管线
    try:
        from rag.pipeline import get_pipeline
        pipeline = get_pipeline()
        pipeline.reload()
        logger.info(f"文档重建索引后 RAG 管线已重新加载，文档ID={document_id}")
    except Exception as e:
        logger.warning(f"RAG 管线重新加载失败: {e}")

    return {
        "message": "索引重建成功",
        "document_id": document_id,
        "chunk_count": len(chunks)
    }


@router.delete("/documents/{document_id}", summary="删除知识库文档")
def delete_document(
    document_id: int,
    db=Depends(get_db),
    user: dict = Depends(require_admin)
):
    """删除知识库中的指定文档（仅管理员）。删除后 RAG 管线会重新加载。"""
    cur = db.cursor()

    cur.execute("SELECT id FROM documents WHERE id = ?", (document_id,))
    if not cur.fetchone():
        cur.close()
        raise HTTPException(status_code=404, detail="文档不存在")

    cur.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    db.commit()
    cur.close()

    # 重新加载 RAG 管线，让删除的文档从检索中移除
    try:
        from rag.pipeline import get_pipeline
        pipeline = get_pipeline()
        pipeline.reload()
        logger.info(f"文档删除后 RAG 管线已重新加载，文档ID={document_id}")
    except Exception as e:
        logger.warning(f"RAG 管线重新加载失败: {e}")

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
