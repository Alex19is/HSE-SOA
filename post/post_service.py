# post_service.py
import grpc
from concurrent import futures
import time
import uuid
from datetime import datetime

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

import post_pb2
import post_pb2_grpc

class PostServiceServicer(post_pb2_grpc.PostServiceServicer):
    def __init__(self):
        self.posts = {}

    def CreatePost(self, request, context):
        post_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        post = post_pb2.Post(
            id=post_id,
            title=request.title,
            description=request.description,
            creator=request.creator,
            created_at=now,
            updated_at=now,
            is_private=request.is_private,
            tags=request.tags
        )
        self.posts[post_id] = post
        return post_pb2.PostResponse(post=post)

    def DeletePost(self, request, context):
        post = self.posts.get(request.id)
        if not post:
            return post_pb2.DeletePostResponse(error="Post not found")
        if post.creator != request.creator:
            return post_pb2.DeletePostResponse(error="Permission denied")
        del self.posts[request.id]
        return post_pb2.DeletePostResponse(message="Post deleted")

    def UpdatePost(self, request, context):
        post = self.posts.get(request.id)
        if not post:
            return post_pb2.PostResponse(error="Post not found")
        if post.creator != request.creator:
            return post_pb2.PostResponse(error="Permission denied")
        now = datetime.utcnow().isoformat()
        post.title = request.title or post.title
        post.description = request.description or post.description
        post.updated_at = now
        post.is_private = request.is_private
        post.tags[:] = request.tags
        self.posts[request.id] = post
        return post_pb2.PostResponse(post=post)

    def GetPost(self, request, context):
        post = self.posts.get(request.id)
        if not post:
            return post_pb2.PostResponse(error="Post not found")
        if post.is_private and post.creator != request.requester:
            return post_pb2.PostResponse(error="Access denied")
        return post_pb2.PostResponse(post=post)

    def ListPosts(self, request, context):
        posts = []
        for post in self.posts.values():
            if not post.is_private or post.creator == request.requester:
                posts.append(post)
        start = (request.page - 1) * request.size
        end = start + request.size
        return post_pb2.ListPostsResponse(posts=posts[start:end])

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    post_pb2_grpc.add_PostServiceServicer_to_server(PostServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Post gRPC service started on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
