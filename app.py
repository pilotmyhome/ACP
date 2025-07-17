from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.future import select

app = FastAPI()

# Replace with your Supabase PostgreSQL URL
DATABASE_URL = "postgresql+asyncpg://postgres:[PASSWORD]@aws-0-us-east-2.pooler.supabase.com:6543/postgres"

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"
    post_id = Column(String, primary_key=True, index=True)
    like_count = Column(Integer, default=0)
    retweet_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, ForeignKey("posts.post_id"))
    user_id = Column(String)

class Retweet(Base):
    __tablename__ = "retweets"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, ForeignKey("posts.post_id"))
    user_id = Column(String)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, ForeignKey("posts.post_id"))
    text = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app.lifespan = lifespan

@app.get("/")
async def root():
    return {"message": "Backend is live - use /docs for API testing"}

class ToggleRequest(BaseModel):
    post_id: str
    user_id: str

class CommentRequest(BaseModel):
    post_id: str
    text: str

class ShareRequest(BaseModel):
    post_id: str

@app.post("/likes/toggle")
async def toggle_like(req: ToggleRequest):
    async with SessionLocal() as session:
        result = await session.execute(select(Like).filter_by(post_id=req.post_id, user_id=req.user_id))
        like = result.scalar_one_or_none()
        result = await session.execute(select(Post).filter_by(post_id=req.post_id))
        post = result.scalar_one_or_none()
        if not post:
            post = Post(post_id=req.post_id)
            session.add(post)
        if like:
            session.delete(like)
            post.like_count -= 1
        else:
            new_like = Like(post_id=req.post_id, user_id=req.user_id)
            session.add(new_like)
            post.like_count += 1
        session.add(post)
        await session.commit()
    return {"success": True}

@app.post("/retweets/toggle")
async def toggle_retweet(req: ToggleRequest):
    async with SessionLocal() as session:
        result = await session.execute(select(Retweet).filter_by(post_id=req.post_id, user_id=req.user_id))
        retweet = result.scalar_one_or_none()
        result = await session.execute(select(Post).filter_by(post_id=req.post_id))
        post = result.scalar_one_or_none()
        if not post:
            post = Post(post_id=req.post_id)
            session.add(post)
        if retweet:
            session.delete(retweet)
            post.retweet_count -= 1
        else:
            new_retweet = Retweet(post_id=req.post_id, user_id=req.user_id)
            session.add(new_retweet)
            post.retweet_count += 1
        session.add(post)
        await session.commit()
    return {"success": True}

@app.post("/comments")
async def submit_comment(req: CommentRequest):
    async with SessionLocal() as session:
        comment = Comment(post_id=req.post_id, text=req.text)
        session.add(comment)
        result = await session.execute(select(Post).filter_by(post_id=req.post_id))
        post = result.scalar_one_or_none()
        if not post:
            post = Post(post_id=req.post_id)
        post.comment_count += 1
        session.add(post)
        await session.commit()
    return {"success": True}

@app.get("/comments/{post_id}")
async def get_comments(post_id: str):
    async with SessionLocal() as session:
        result = await session.execute(select(Comment).filter_by(post_id=post_id).order_by(Comment.created_at))
        comments = result.scalars().all()
        return [c.text for c in comments]

@app.post("/shares")
async def share_post(req: ShareRequest):
    async with SessionLocal() as session:
        result = await session.execute(select(Post).filter_by(post_id=req.post_id))
        post = result.scalar_one_or_none()
        if not post:
            post = Post(post_id=req.post_id)
            session.add(post)
        post.share_count += 1
        session.add(post)
        await session.commit()
    return {"success": True}

@app.get("/stats/{post_id}")
async def get_stats(post_id: str):
    async with SessionLocal() as session:
        result = await session.execute(select(Post).filter_by(post_id=post_id))
        post = result.scalar_one_or_none()
        if not post:
            return {"like_count": 0, "retweet_count": 0, "comment_count": 0, "share_count": 0}
        return {
            "like_count": post.like_count,
            "retweet_count": post.retweet_count,
            "comment_count": post.comment_count,
            "share_count": post.share_count,
        }

@app.get("/likes/{post_id}/{user_id}")
async def is_liked(post_id: str, user_id: str):
    async with SessionLocal() as session:
        result = await session.execute(select(Like).filter_by(post_id=post_id, user_id=user_id))
        like = result.scalar_one_or_none()
        return {"is_liked": bool(like)}

@app.get("/retweets/{post_id}/{user_id}")
async def is_retweeted(post_id: str, user_id: str):
    async with SessionLocal() as session:
        result = await session.execute(select(Retweet).filter_by(post_id=post_id, user_id=user_id))
        retweet = result.scalar_one_or_none()
        return {"is_retweeted": bool(retweet)}