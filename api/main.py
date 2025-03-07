from fastapi import FastAPI, Request
import requests

app = FastAPI()
main_service_url = "http://localhost:8000"

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def forward_request(request: Request, path_name: str):

    url = f"{main_service_url}/{path_name}"
    
    data = await request.body()
    
    response = requests.request(
        method=request.method,
        url=url,
        headers=request.headers,
        data=data
    )

    return response.content
