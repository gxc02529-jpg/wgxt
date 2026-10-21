# -*- coding: utf-8 -*-
"""推荐 service 分层回归测试：使用 SQLite 内存库，不访问外部服务。"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.article import Article
from app.models.category import Category
from app.models.preference import UserPreference
from app.models.user import User
from app.services.recommendation_service import recommend_with_preferences


class RecommendationServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_explicit_category_preference_is_resolved_in_service_layer(self):
        user = User(username="reader", password_hash="hash", role="user", status="active")
        category = Category(name="科技", slug="tech", status="active")
        article = Article(
            title="科技新闻",
            author=user,
            status="published",
            view_count=10,
            like_count=0,
            favorite_count=0,
            share_count=0,
        )
        article.categories = [category]
        self.session.add_all([user, category, article])
        self.session.flush()
        self.session.add(UserPreference(user_id=user.id, category_id=category.id))
        self.session.commit()

        reason, items = recommend_with_preferences(self.session, user, limit=6)

        self.assertEqual(reason, "根据您的兴趣偏好推荐")
        self.assertEqual([item.id for item in items], [article.id])


if __name__ == "__main__":
    unittest.main()
