# test_post_service.py
import uuid
import pytest
from datetime import datetime

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

import post_pb2
import post_pb2_grpc
from post_service import PostServiceServicer

class DummyContext:
    def set_code(self, code):
        self.code = code
    def set_details(self, details):
        self.details = details

@pytest.fixture
def service():
    return PostServiceServicer()

@pytest.fixture
def dummy_context():
    return DummyContext()

def test_create_post(service, dummy_context):
    req = post_pb2.CreatePostRequest(
        title="Test post",
        description="Test description",
        creator="user1",
        is_private=False,
        tags=["tag1", "tag2"]
    )
    response = service.CreatePost(req, dummy_context)
    assert response.error == ""
    assert response.post.title == "Test post"
    assert response.post.creator == "user1"
    assert response.post.id in service.posts

def test_delete_post_by_creator(service, dummy_context):
    req_create = post_pb2.CreatePostRequest(
        title="Delete post",
        description="To be deleted",
        creator="user1",
        is_private=False,
        tags=[]
    )
    response_create = service.CreatePost(req_create, dummy_context)
    post_id = response_create.post.id
    req_delete = post_pb2.DeletePostRequest(
        id=post_id,
        creator="user1"
    )
    response_delete = service.DeletePost(req_delete, dummy_context)
    assert response_delete.error == ""
    assert response_delete.message == "Post deleted"

    assert post_id not in service.posts

def test_delete_post_by_non_creator(service, dummy_context):
    req_create = post_pb2.CreatePostRequest(
        title="Delete post",
        description="To be deleted by wrong user",
        creator="user1",
        is_private=False,
        tags=[]
    )
    response_create = service.CreatePost(req_create, dummy_context)
    post_id = response_create.post.id

    req_delete = post_pb2.DeletePostRequest(
        id=post_id,
        creator="user2"
    )
    response_delete = service.DeletePost(req_delete, dummy_context)
    assert response_delete.error == "Permission denied"
    assert post_id in service.posts

def test_update_post(service, dummy_context):
    req_create = post_pb2.CreatePostRequest(
        title="Old title",
        description="Old description",
        creator="user1",
        is_private=False,
        tags=["old"]
    )
    response_create = service.CreatePost(req_create, dummy_context)
    post_id = response_create.post.id

    req_update = post_pb2.UpdatePostRequest(
        id=post_id,
        title="New title",
        description="New description",
        is_private=True,
        tags=["new"],
        creator="user1"
    )
    response_update = service.UpdatePost(req_update, dummy_context)
    assert response_update.error == ""
    assert response_update.post.title == "New title"
    assert response_update.post.is_private is True

    assert response_update.post.updated_at != response_update.post.created_at

def test_get_post_public(service, dummy_context):
    req_create = post_pb2.CreatePostRequest(
        title="Public post",
        description="Public description",
        creator="user1",
        is_private=False,
        tags=[]
    )
    response_create = service.CreatePost(req_create, dummy_context)
    post_id = response_create.post.id

    req_get = post_pb2.GetPostRequest(
        id=post_id,
        requester="user2"
    )
    response_get = service.GetPost(req_get, dummy_context)
    assert response_get.error == ""
    assert response_get.post.id == post_id

def test_get_post_private_by_owner(service, dummy_context):
    req_create = post_pb2.CreatePostRequest(
        title="Private post",
        description="Private description",
        creator="user1",
        is_private=True,
        tags=[]
    )
    response_create = service.CreatePost(req_create, dummy_context)
    post_id = response_create.post.id

    req_get = post_pb2.GetPostRequest(
        id=post_id,
        requester="user1"
    )
    response_get = service.GetPost(req_get, dummy_context)
    assert response_get.error == ""
    assert response_get.post.id == post_id

def test_get_post_private_by_non_owner(service, dummy_context):
    req_create = post_pb2.CreatePostRequest(
        title="Private post",
        description="Private description",
        creator="user1",
        is_private=True,
        tags=[]
    )
    response_create = service.CreatePost(req_create, dummy_context)
    post_id = response_create.post.id

    req_get = post_pb2.GetPostRequest(
        id=post_id,
        requester="user2"
    )
    response_get = service.GetPost(req_get, dummy_context)
    assert response_get.error == "Access denied"

def test_list_posts(service, dummy_context):

    service.posts.clear()

    req1 = post_pb2.CreatePostRequest(
        title="Post 1",
        description="Desc 1",
        creator="user1",
        is_private=False,
        tags=[]
    )
    req2 = post_pb2.CreatePostRequest(
        title="Post 2",
        description="Desc 2",
        creator="user1",
        is_private=True,
        tags=[]
    )
    req3 = post_pb2.CreatePostRequest(
        title="Post 3",
        description="Desc 3",
        creator="user2",
        is_private=False,
        tags=[]
    )
    service.CreatePost(req1, dummy_context)
    service.CreatePost(req2, dummy_context)
    service.CreatePost(req3, dummy_context)

    req_list = post_pb2.ListPostsRequest(
        page=1,
        size=10,
        requester="user1"
    )
    response_list = service.ListPosts(req_list, dummy_context)

    assert len(response_list.posts) == 3

    req_list2 = post_pb2.ListPostsRequest(
        page=1,
        size=10,
        requester="user2"
    )
    response_list2 = service.ListPosts(req_list2, dummy_context)
    assert len(response_list2.posts) == 2

