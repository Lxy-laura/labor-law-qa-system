"""
劳动合同纠纷智能问答系统 - 智能问答接口（SQLite 版本）
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from models.schemas import (
    QuestionRequest,
    FeedbackRequest,
    FeedbackResponse
)
from auth.decorators import get_current_user

router = APIRouter(prefix="/api/qa", tags=["智能问答"])

@router.post("/ask", summary="智能问答")
def ask_question(
    req: QuestionRequest,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """智能问答接口"""
    try:
        from rag.pipeline import get_pipeline

        pipeline = get_pipeline()
        result = pipeline.run(req.question, top_k=req.top_k)

        cur = db.cursor()
        cur.execute(
            """INSERT INTO chat_history (user_id, question, answer, citations, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (
                user["user_id"],
                req.question,
                result["answer"],
                json.dumps(result["citations"], ensure_ascii=False),
                result["confidence"]
            )
        )
        db.commit()
        cur.close()

        return {
            "answer": result["answer"],
            "citations": result["citations"],
            "cases": result.get("cases", []),
            "landing_services": result.get("landing_services", []),
            "confidence": result["confidence"],
            "expanded_query": result.get("expanded_query")
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"问答处理失败: {str(e)}")

@router.get("/conversations", summary="获取对话历史列表")
def get_conversations(
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    cur = db.cursor()
    cur.execute(
        """SELECT id, question, answer, confidence, created_at
           FROM chat_history WHERE user_id = ?
           ORDER BY created_at DESC LIMIT 50""",
        (user["user_id"],)
    )
    rows = cur.fetchall()
    cur.close()

    conversations = []
    for row in rows:
        conversations.append({
            "id": row["id"],
            "title": row["question"][:30] + ("..." if len(row["question"]) > 30 else ""),
            "question": row["question"],
            "answer": row["answer"],
            "confidence": row["confidence"],
            "created_at": row["created_at"]
        })
    return conversations

@router.delete("/conversations/{conv_id}", summary="删除对话记录")
def delete_conversation(
    conv_id: int,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    cur = db.cursor()
    cur.execute(
        "DELETE FROM chat_history WHERE id = ? AND user_id = ?",
        (conv_id, user["user_id"])
    )
    db.commit()
    cur.close()
    return {"message": "删除成功"}

@router.post("/feedback", response_model=FeedbackResponse, summary="提交问答反馈")
def submit_feedback(
    req: FeedbackRequest,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    cur = db.cursor()
    cur.execute(
        "SELECT id FROM chat_history WHERE id = ? AND user_id = ?",
        (req.chat_id, user["user_id"])
    )
    if not cur.fetchone():
        cur.close()
        raise HTTPException(status_code=404, detail="对话记录不存在或无权操作")
    cur.execute(
        """INSERT INTO feedback (user_id, chat_id, rating, comment)
           VALUES (?, ?, ?, ?)""",
        (user["user_id"], req.chat_id, req.rating, req.comment)
    )
    feedback_id = cur.lastrowid
    db.commit()
    cur.close()
    return FeedbackResponse(message="反馈提交成功", feedback_id=feedback_id)