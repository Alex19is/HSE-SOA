import grpc
import requests
from fastapi import FastAPI, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from google.protobuf.json_format import MessageToDict

import post_pb2
import post_pb2_grpc

app = FastAPI(title="Gateway API Service")

USER_SERVICE_URL = "http://localhost:8000"

POST_SERVICE_GRPC_ADDR = "localhost:50051"

channel = grpc.insecure_channel(POST_SERVICE_GRPC_ADDR)
grpc_stub = post_pb2_grpc.PostServiceStub(channel)

class PostCreate(BaseModel):
    title: str
    description: str
    is_private: bool = False
    tags: List[str] = []

class PostUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_private: Optional[bool] = None
    tags: Optional[List[str]] = None

class CommentCreate(BaseModel):
    text: str

# ------------------------------------------------------------------
# Proxy для user_service (прямое пересылание)
# ------------------------------------------------------------------
@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_users(request: Request, path: str):
    target_url = f"{USER_SERVICE_URL}/users/{path}"
    data = await request.body()
    response = requests.request(
        method=request.method,
        url=target_url,
        headers=request.headers,
        data=data
    )
    return response.content

@app.api_route("/token", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_token(request: Request):
    target_url = f"{USER_SERVICE_URL}/token"
    data = await request.body()
    response = requests.request(
        method=request.method,
        url=target_url,
        headers=request.headers,
        data=data
    )
    return response.content

# ------------------------------------------------------------------
# Dependency: проверка JWT и получение current_user из user_service
# ------------------------------------------------------------------

def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    user_me_url = f"{USER_SERVICE_URL}/users/me"
    headers = {"Authorization": token}
    resp = requests.get(user_me_url, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json())
    return resp.json()

# ------------------------------------------------------------------
# CRUD-эндпоинты для постов
# ------------------------------------------------------------------
@app.post("/posts", summary="Создание поста")
async def create_post(
    post: PostCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    username = current_user.get("login")
    if not username:
        raise HTTPException(status_code=400, detail="User login not found")

    grpc_request = post_pb2.CreatePostRequest(
        title=post.title,
        description=post.description,
        creator=username,
        is_private=post.is_private,
        tags=post.tags
    )
    grpc_response = grpc_stub.CreatePost(grpc_request)
    if grpc_response.error:
        raise HTTPException(status_code=400, detail=grpc_response.error)
    return MessageToDict(grpc_response.post)

@app.get("/posts/{post_id}", summary="Получение поста по ID")
async def get_post(
    post_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    username = current_user.get("login")
    grpc_request = post_pb2.GetPostRequest(
        id=post_id,
        requester=username
    )
    grpc_response = grpc_stub.GetPost(grpc_request)
    if grpc_response.error:
        raise HTTPException(status_code=400, detail=grpc_response.error)
    return MessageToDict(grpc_response.post)

@app.get("/posts", summary="Получение списка постов с пагинацией")
async def list_posts(
    request: Request,
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    size: int = 10
):
    username = current_user.get("login")
    grpc_request = post_pb2.ListPostsRequest(
        page=page,
        size=size,
        requester=username
    )
    grpc_response = grpc_stub.ListPosts(grpc_request)
    if grpc_response.error:
        raise HTTPException(status_code=400, detail=grpc_response.error)
    return [MessageToDict(p) for p in grpc_response.posts]

@app.put("/posts/{post_id}", summary="Обновление поста")
async def update_post(
    post_id: str,
    post: PostUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    username = current_user.get("login")
    grpc_request = post_pb2.UpdatePostRequest(
        id=post_id,
        title=post.title or "",
        description=post.description or "",
        is_private=post.is_private if post.is_private is not None else False,
        tags=post.tags or [],
        creator=username
    )
    grpc_response = grpc_stub.UpdatePost(grpc_request)
    if grpc_response.error:
        raise HTTPException(status_code=400, detail=grpc_response.error)
    return MessageToDict(grpc_response.post)

@app.delete("/posts/{post_id}", summary="Удаление поста")
async def delete_post(
    post_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    username = current_user.get("login")
    grpc_request = post_pb2.DeletePostRequest(
        id=post_id,
        creator=username
    )
    grpc_response = grpc_stub.DeletePost(grpc_request)
    if grpc_response.error:
        raise HTTPException(status_code=400, detail=grpc_response.error)
    return {"message": grpc_response.message}

@app.post("/posts/{post_id}/like", summary="Лайк поста")
async def like_post(
    post_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    username = current_user.get("login")
    grpc_request = post_pb2.LikePostRequest(
        post_id=post_id,
        user_login=username
    )
    grpc_response = grpc_stub.LikePost(grpc_request)
    if grpc_response.error:
        raise HTTPException(status_code=400, detail=grpc_response.error)
    return {
        "message": grpc_response.message,
        "total_likes": grpc_response.total_likes
    }

@app.post("/posts/{post_id}/comments", summary="Добавление комментария")
async def comment_post(
    post_id: str,
    comment: CommentCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    username = current_user.get("login")
    grpc_request = post_pb2.CommentPostRequest(
        post_id=post_id,
        user_login=username,
        text=comment.text
    )
    grpc_response = grpc_stub.CommentPost(grpc_request)
    if grpc_response.error:
        raise HTTPException(status_code=400, detail=grpc_response.error)
    return MessageToDict(grpc_response.comment)

@app.get("/posts/{post_id}/comments", summary="Получение списка комментариев с пагинацией")
async def list_comments(
    post_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    size: int = 10
):
    grpc_request = post_pb2.ListCommentsRequest(
        post_id=post_id,
        page=page,
        size=size
    )
    grpc_response = grpc_stub.ListComments(grpc_request)
    if grpc_response.error:
        raise HTTPException(status_code=400, detail=grpc_response.error)
    return [MessageToDict(c) for c in grpc_response.comments]