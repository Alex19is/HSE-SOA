import uuid
import pytest
from datetime import datetime

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

import post_pb2
import post_pb2_grpc
from post_service import PostServiceServicer

from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_kafka_producer():
    with patch("post_service.KafkaProducer") as mock:
        yield mock

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
    created = service.CreatePost(req_create, dummy_context)
    post_id = created.post.id

    req_delete = post_pb2.DeletePostRequest(
        id=post_id,
        creator="user1"
    )
    deleted = service.DeletePost(req_delete, dummy_context)
    assert deleted.error == ""
    assert deleted.message == "Post deleted"
    assert post_id not in service.posts


def test_delete_post_by_non_creator(service, dummy_context):
    created = service.CreatePost(post_pb2.CreatePostRequest(
        title="Private",
        description="Desc",
        creator="user1",
        is_private=False,
        tags=[]
    ), dummy_context)
    post_id = created.post.id

    wrong = service.DeletePost(post_pb2.DeletePostRequest(
        id=post_id,
        creator="user2"
    ), dummy_context)
    assert wrong.error == "Permission denied"
    assert post_id in service.posts


def test_update_post(service, dummy_context):
    created = service.CreatePost(post_pb2.CreatePostRequest(
        title="Old",
        description="Old desc",
        creator="user1",
        is_private=False,
        tags=["old"]
    ), dummy_context)
    post_id = created.post.id
    update_req = post_pb2.UpdatePostRequest(
        id=post_id,
        title="New",
        description="New desc",
        is_private=True,
        tags=["new"],
        creator="user1"
    )
    updated = service.UpdatePost(update_req, dummy_context)
    assert updated.error == ""
    assert updated.post.title == "New"
    assert updated.post.is_private is True
    assert updated.post.updated_at != updated.post.created_at


def test_get_post_public_and_private(service, dummy_context):
    pub = service.CreatePost(post_pb2.CreatePostRequest(
        title="Pub",
        description="D",
        creator="user1",
        is_private=False,
        tags=[]
    ), dummy_context)
    priv = service.CreatePost(post_pb2.CreatePostRequest(
        title="Priv",
        description="D",
        creator="user1",
        is_private=True,
        tags=[]
    ), dummy_context)

    res_pub = service.GetPost(post_pb2.GetPostRequest(
        id=pub.post.id,
        requester="user2"
    ), dummy_context)
    assert res_pub.error == ""

    res_own = service.GetPost(post_pb2.GetPostRequest(
        id=priv.post.id,
        requester="user1"
    ), dummy_context)
    assert res_own.error == ""

    res_no = service.GetPost(post_pb2.GetPostRequest(
        id=priv.post.id,
        requester="user2"
    ), dummy_context)
    assert res_no.error == "Access denied"


def test_list_posts(service, dummy_context):
    service.posts.clear()

    service.CreatePost(post_pb2.CreatePostRequest(
        title="P1", description="D1", creator="u1", is_private=False, tags=[]
    ), dummy_context)
    service.CreatePost(post_pb2.CreatePostRequest(
        title="P2", description="D2", creator="u1", is_private=True, tags=[]
    ), dummy_context)
    service.CreatePost(post_pb2.CreatePostRequest(
        title="P3", description="D3", creator="u2", is_private=False, tags=[]
    ), dummy_context)

    list1 = service.ListPosts(post_pb2.ListPostsRequest(page=1, size=10, requester="u1"), dummy_context)
    assert len(list1.posts) == 3

    list2 = service.ListPosts(post_pb2.ListPostsRequest(page=1, size=10, requester="u2"), dummy_context)
    assert len(list2.posts) == 2

def test_like_post(service, dummy_context):

    created = service.CreatePost(post_pb2.CreatePostRequest(
        title="LikeTest", description="D", creator="u1", is_private=False, tags=[]
    ), dummy_context)
    pid = created.post.id

    like1 = service.LikePost(post_pb2.LikePostRequest(post_id=pid, user_login="u2"), dummy_context)
    assert like1.error == ""
    assert like1.total_likes == 1

    like2 = service.LikePost(post_pb2.LikePostRequest(post_id=pid, user_login="u2"), dummy_context)
    assert like2.total_likes == 1

    like3 = service.LikePost(post_pb2.LikePostRequest(post_id=pid, user_login="u3"), dummy_context)
    assert like3.total_likes == 2


def test_comment_post_and_list(service, dummy_context):

    created = service.CreatePost(post_pb2.CreatePostRequest(
        title="CommTest", description="D", creator="u1", is_private=False, tags=[]
    ), dummy_context)
    pid = created.post.id

    c1 = service.CommentPost(post_pb2.CommentPostRequest(post_id=pid, user_login="u2", text="C1"), dummy_context)
    c2 = service.CommentPost(post_pb2.CommentPostRequest(post_id=pid, user_login="u3", text="C2"), dummy_context)
    assert c1.error == ""
    assert c1.comment.text == "C1"
 
    assert len(service.comments[pid]) == 2

    list_page1 = service.ListComments(post_pb2.ListCommentsRequest(post_id=pid, page=1, size=1), dummy_context)
    assert len(list_page1.comments) == 1

    list_page2 = service.ListComments(post_pb2.ListCommentsRequest(post_id=pid, page=2, size=1), dummy_context)
    assert len(list_page2.comments) == 1

    list_page3 = service.ListComments(post_pb2.ListCommentsRequest(post_id=pid, page=3, size=1), dummy_context)
    assert len(list_page3.comments) == 0