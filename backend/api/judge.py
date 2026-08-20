"""
劳动合同纠纷智能问答系统 - 合同研判接口（SQLite 版本）
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from models.schemas import JudgeRequest, JudgeResponse
from auth.decorators import get_current_user

router = APIRouter(prefix="/api/judge", tags=["合同研判"])


@router.post("/analyze", response_model=JudgeResponse, summary="合同条款研判")
def analyze_contract(
    req: JudgeRequest,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """合同研判接口"""
    try:
        from judge.analyzer import get_analyzer

        # 执行合同研判
        analyzer = get_analyzer()
        result = analyzer.analyze(req.contract_text)

        # 保存研判记录到数据库
        cur = db.cursor()
        cur.execute(
            """INSERT INTO judge_records (user_id, contract_text, analysis_result)
               VALUES (?, ?, ?)""",
            (
                user["user_id"],
                req.contract_text,
                json.dumps(result, ensure_ascii=False)
            )
        )
        db.commit()
        cur.close()

        return JudgeResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"研判处理失败: {str(e)}")
