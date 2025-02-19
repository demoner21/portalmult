from datetime import datetime
from fastapi import HTTPException

def validate_date_range(start_date: str, end_date: str):
    """
    Valida se a data de início é anterior ou igual à data de término.
    
    :param start_date: Data de início no formato YYYY-MM-DD
    :param end_date: Data de término no formato YYYY-MM-DD
    :raises HTTPException: Se a data de início for maior que a data de término
    """
    if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
        raise HTTPException(
            status_code=422,
            detail="A data de início não pode ser maior que a data de término"
        )