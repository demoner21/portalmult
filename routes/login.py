from fastapi.responses import RedirectResponse

@app.get("/login")
async def login():
    return RedirectResponse(
        url=f"{KEYCLOAK_URL}/protocol/openid-connect/auth?client_id={CLIENT_ID}&response_type=code&redirect_uri=http://localhost:3000/callback"
    )

@app.get("/callback")
async def callback(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{KEYCLOAK_URL}/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": "http://localhost:3000/callback",
            },
        )
        response.raise_for_status()
        token_data = response.json()
        return {"access_token": token_data["access_token"]}