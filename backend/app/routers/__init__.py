"""Routers package"""
from app.routers.search import router as search_router
from app.routers.photo import router as photo_router
from app.routers.photo_import import router as import_router

__all__ = ['search_router', 'photo_router', 'import_router']
