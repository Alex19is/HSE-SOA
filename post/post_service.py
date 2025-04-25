import grpc
from concurrent import futures
import time
import uuid
from datetime import datetime
import os
import sys
import json
from kafka import KafkaProducer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../api')))
import post_pb2
import post_pb2_grpc

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

class PostServiceServicer(post_pb2_grpc.PostServiceServicer):
    def __init__(self):
        self.posts = {}                  
        self.likes = {}                  
        self.comments = {}               

    def _send_event(self, topic: str, event: dict):
        producer.send(topic, event)

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

        self.likes.pop(request.id, None)
        self.comments.pop(request.id, None)
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

        now = datetime.utcnow().isoformat()
        self._send_event('post_views', {
            'post_id': post.id,
            'user_login': request.requester,
            'timestamp': now
        })
        return post_pb2.PostResponse(post=post)

    def ListPosts(self, request, context):
        posts = []
        for post in self.posts.values():
            if not post.is_private or post.creator == request.requester:
                posts.append(post)
        start = (request.page - 1) * request.size
        end = start + request.size
        return post_pb2.ListPostsResponse(posts=posts[start:end])

    def LikePost(self, request, context):
        post = self.posts.get(request.post_id)
        if not post:
            return post_pb2.LikePostResponse(error="Post not found")
        likes_set = self.likes.setdefault(request.post_id, set())
        likes_set.add(request.user_login)
        now = datetime.utcnow().isoformat()
        self._send_event('post_likes', {
            'post_id': request.post_id,
            'user_login': request.user_login,
            'timestamp': now
        })
        return post_pb2.LikePostResponse(
            message="Like recorded",
            total_likes=len(likes_set)
        )

    def CommentPost(self, request, context):
        post = self.posts.get(request.post_id)
        if not post:
            return post_pb2.CommentPostResponse(error="Post not found")
        comment_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        comment = post_pb2.Comment(
            id=comment_id,
            post_id=request.post_id,
            user_login=request.user_login,
            text=request.text,
            created_at=now
        )
        self.comments.setdefault(request.post_id, []).append(comment)
        self._send_event('post_comments', {
            'post_id': request.post_id,
            'comment_id': comment_id,
            'user_login': request.user_login,
            'timestamp': now
        })
        return post_pb2.CommentPostResponse(comment=comment)

    def ListComments(self, request, context):
        all_comments = self.comments.get(request.post_id, [])
        if not all_comments:
            return post_pb2.ListCommentsResponse(comments=[])
        start = (request.page - 1) * request.size
        end = start + request.size
        return post_pb2.ListCommentsResponse(comments=all_comments[start:end])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    post_pb2_grpc.add_PostServiceServicer_to_server(PostServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Post gRPC service with Kafka started on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()