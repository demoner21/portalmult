from fastapi import Depends, FastAPI
from security import get_current_user, TokenData

app = FastAPI()

@app.get("/protected")
async def protected_route(current_user: TokenData = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.email}!"}