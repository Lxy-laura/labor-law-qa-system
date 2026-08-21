"""
劳动合同纠纷智能问答系统 - 智能问答接口（SQLite 版本）
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from models.schemas import (
    QuestionRequest,
    FeedbackRequest,
    FeedbackResponse
)
from auth.decorators import get_current_user, require_admin

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

        # 执行 RAG 管线
        pipeline = get_pipeline()
        result = pipeline.run(req.question, top_k=req.top_k)

        # 保存对话历史到数据库
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
        chat_id = cur.lastrowid
        db.commit()
        cur.close()

        # 直接返回 dict，不使用 response_model
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
    """获取当前用户的对话历史列表"""
    cur = db.cursor()
    cur.execute(
        """SELECT id, question, answer, confidence, is_favorited, created_at
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
            "is_favorited": bool(row["is_favorited"]) if "is_favorited" in row.keys() else False,
            "created_at": row["created_at"]
        })

    return conversations

@router.get("/conversations/{conv_id}", summary="获取单个对话详情")
def get_conversation_detail(
    conv_id: int,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """获取指定对话的详细信息"""
    cur = db.cursor()
    cur.execute(
        """SELECT id, question, answer, citations, confidence, is_favorited, created_at
           FROM chat_history WHERE id = ? AND user_id = ?""",
        (conv_id, user["user_id"])
    )
    row = cur.fetchone()
    cur.close()

    if not row:
        raise HTTPException(status_code=404, detail="对话记录不存在或无权访问")

    # 解析引用来源
    citations = json.loads(row["citations"]) if row["citations"] else []

    # 归一化旧数据：如果 relevance > 1，说明是旧的 BM25 原始分数，需要归一化到 0-1
    if citations:
        max_rel = max(c.get("relevance", 0) for c in citations)
        if max_rel > 1:
            for c in citations:
                raw = c.get("relevance", 0)
                c["relevance"] = round(raw / max_rel, 4) if max_rel > 0 else 0

    return {
        "id": row["id"],
        "question": row["question"],
        "answer": row["answer"],
        "citations": citations,
        "confidence": row["confidence"],
        "is_favorited": bool(row["is_favorited"]) if "is_favorited" in row.keys() else False,
        "created_at": row["created_at"]
    }

@router.delete("/conversations/{conv_id}", summary="删除对话记录")
def delete_conversation(
    conv_id: int,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """删除指定的对话记录"""
    cur = db.cursor()
    cur.execute(
        "DELETE FROM chat_history WHERE id = ? AND user_id = ?",
        (conv_id, user["user_id"])
    )
    db.commit()
    cur.close()
    return {"message": "删除成功"}

@router.post("/conversations/{conv_id}/regenerate", summary="重新生成回答")
def regenerate_answer(
    conv_id: int,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """用当前已配置的 API Key 重新生成历史对话的回答"""
    cur = db.cursor()

    # 查找对话记录
    cur.execute(
        "SELECT id, question FROM chat_history WHERE id = ? AND user_id = ?",
        (conv_id, user["user_id"])
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        raise HTTPException(status_code=404, detail="对话记录不存在或无权操作")

    question = row["question"]

    # 重新执行 RAG 管线（使用当前已配置的 API Key）
    try:
        from rag.pipeline import get_pipeline
        pipeline = get_pipeline()
        result = pipeline.run(question, top_k=5)
    except Exception as e:
        cur.close()
        raise HTTPException(status_code=500, detail=f"重新生成失败: {str(e)}")

    # 更新数据库中的回答
    cur.execute(
        """UPDATE chat_history
           SET answer = ?, citations = ?, confidence = ?
           WHERE id = ?""",
        (
            result["answer"],
            json.dumps(result["citations"], ensure_ascii=False),
            result["confidence"],
            conv_id
        )
    )
    db.commit()
    cur.close()

    return {
        "id": conv_id,
        "question": question,
        "answer": result["answer"],
        "citations": result["citations"],
        "cases": result.get("cases", []),
        "landing_services": result.get("landing_services", []),
        "confidence": result["confidence"],
        "message": "回答已重新生成"
    }

@router.post("/conversations/{conv_id}/favorite", summary="切换收藏状态")
def toggle_favorite(
    conv_id: int,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """收藏或取消收藏对话记录"""
    cur = db.cursor()

    # 验证对话记录存在且属于当前用户
    cur.execute(
        "SELECT id, is_favorited FROM chat_history WHERE id = ? AND user_id = ?",
        (conv_id, user["user_id"])
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        raise HTTPException(status_code=404, detail="对话记录不存在或无权操作")

    # 切换收藏状态
    current = bool(row["is_favorited"]) if "is_favorited" in row.keys() else False
    new_state = 0 if current else 1

    cur.execute(
        "UPDATE chat_history SET is_favorited = ? WHERE id = ?",
        (new_state, conv_id)
    )
    db.commit()
    cur.close()

    return {"message": "已收藏" if new_state else "已取消收藏", "is_favorited": bool(new_state)}

@router.get("/favorites", summary="获取收藏列表")
def get_favorites(
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """获取当前用户收藏的对话列表"""
    cur = db.cursor()
    cur.execute(
        """SELECT id, question, answer, confidence, created_at
           FROM chat_history WHERE user_id = ? AND is_favorited = 1
           ORDER BY created_at DESC""",
        (user["user_id"],)
    )
    rows = cur.fetchall()
    cur.close()

    favorites = []
    for row in rows:
        favorites.append({
            "id": row["id"],
            "question": row["question"],
            "answer": row["answer"],
            "confidence": row["confidence"],
            "is_favorited": True,
            "created_at": row["created_at"]
        })

    return favorites

@router.post("/feedback", response_model=FeedbackResponse, summary="提交问答反馈")
def submit_feedback(
    req: FeedbackRequest,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """提交对问答回答的反馈"""
    cur = db.cursor()

    # 验证对话记录是否存在且属于当前用户
    cur.execute(
        "SELECT id FROM chat_history WHERE id = ? AND user_id = ?",
        (req.chat_id, user["user_id"])
    )
    if not cur.fetchone():
        cur.close()
        raise HTTPException(status_code=404, detail="对话记录不存在或无权操作")

    # 保存反馈
    cur.execute(
        """INSERT INTO feedback (user_id, chat_id, rating, comment)
           VALUES (?, ?, ?, ?)""",
        (user["user_id"], req.chat_id, req.rating, req.comment)
    )
    feedback_id = cur.lastrowid
    db.commit()
    cur.close()

    return FeedbackResponse(message="反馈提交成功", feedback_id=feedback_id)

@router.get("/feedback", summary="获取反馈列表（管理员）")
def get_feedback_list(
    rating: int = Query(None, ge=1, le=5, description="按评分筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db=Depends(get_db),
    user: dict = Depends(require_admin)
):
    """获取所有用户的反馈列表（仅管理员）"""
    cur = db.cursor()

    # 构建查询条件
    where_clause = ""
    params = []
    if rating:
        where_clause = "WHERE f.rating = ?"
        params.append(rating)

    # 获取总数
    cur.execute(f"SELECT COUNT(*) as total FROM feedback f {where_clause}", params)
    total = cur.fetchone()["total"]

    # 获取反馈列表（关联对话历史和用户信息）
    offset = (page - 1) * page_size
    cur.execute(
        f"""SELECT f.id, f.rating, f.comment, f.created_at,
                  ch.question, ch.answer,
                  u.username
           FROM feedback f
           LEFT JOIN chat_history ch ON f.chat_id = ch.id
           LEFT JOIN users u ON f.user_id = u.id
           {where_clause}
           ORDER BY f.created_at DESC
           LIMIT ? OFFSET ?""",
        params + [page_size, offset]
    )
    rows = cur.fetchall()

    # 获取评分统计
    cur.execute(
        """SELECT rating, COUNT(*) as count FROM feedback GROUP BY rating"""
    )
    stats_rows = cur.fetchall()
    stats = {}
    for srow in stats_rows:
        stats[str(srow["rating"])] = srow["count"]

    cur.close()

    feedback_list = []
    for row in rows:
        feedback_list.append({
            "id": row["id"],
            "rating": row["rating"],
            "comment": row["comment"],
            "question": row["question"] if row["question"] else "",
            "answer": row["answer"][:100] + "..." if row["answer"] and len(row["answer"]) > 100 else (row["answer"] or ""),
            "username": row["username"] if row["username"] else "匿名用户",
            "created_at": row["created_at"]
        })

    return {
        "list": feedback_list,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "stats": stats
    }