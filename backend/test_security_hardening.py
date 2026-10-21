# -*- coding: utf-8 -*-
"""生产安全加固回归测试：不连接数据库、不访问外部服务。"""
import unittest

from app.config import Settings, validate_runtime_settings
from app.models.article import Article
from app.services.html_sanitizer import sanitize_article_html


class ArticleHTMLSanitizerTests(unittest.TestCase):
    def test_removes_dangerous_nodes_attributes_and_protocols(self):
        raw = (
            '<p onclick="steal()">正文<script>alert(1)</script></p>'
            '<iframe src="https://evil.example"></iframe>'
            '<img src="javascript:alert(1)" onerror="steal()" alt="图">'
            '<a href="javascript:alert(1)" target="_blank">链接</a>'
            '<svg onload="steal()"><circle /></svg>'
        )

        cleaned = sanitize_article_html(raw)

        self.assertIn("<p>正文</p>", cleaned)
        self.assertNotIn("script", cleaned.casefold())
        self.assertNotIn("iframe", cleaned.casefold())
        self.assertNotIn("svg", cleaned.casefold())
        self.assertNotIn("onclick", cleaned.casefold())
        self.assertNotIn("onerror", cleaned.casefold())
        self.assertNotIn("javascript:", cleaned.casefold())

    def test_preserves_editor_structure_and_safe_urls(self):
        raw = (
            '<h2>标题</h2><p style="text-align:center">正文<br>'
            '<strong>重点</strong><a href="https://example.com/a" target="_blank">来源</a>'
            '<img src="/static/a.png" alt="封面" width="640"></p>'
            '<table><tbody><tr><td colspan="2">数据</td></tr></tbody></table>'
        )

        cleaned = sanitize_article_html(raw)

        self.assertIn("<h2>标题</h2>", cleaned)
        self.assertIn("<strong>重点</strong>", cleaned)
        self.assertIn('href="https://example.com/a"', cleaned)
        self.assertIn('rel="noopener noreferrer"', cleaned)
        self.assertIn('src="/static/a.png"', cleaned)
        self.assertIn('colspan="2"', cleaned)
        self.assertNotIn("style=", cleaned)

    def test_historical_article_is_sanitized_when_serialized(self):
        article = Article(
            id=1,
            title="历史稿件",
            author_id=1,
            content='<p>正文<img src="x" onerror="steal()"></p><script>steal()</script>',
            status="published",
        )
        article.categories = []
        article.channels = []

        payload = article.to_dict(include_content=True)

        self.assertEqual(payload["content"], '<p>正文<img src="x"></p>')
        self.assertNotIn("script", payload["content"])
        self.assertNotIn("onerror", payload["content"])


class ProductionSettingsTests(unittest.TestCase):
    @staticmethod
    def make_settings(**overrides):
        values = {
            "APP_ENV": "production",
            "DB_PASSWORD": "strong-database-password",
            "SECRET_KEY": "a-secure-random-secret-key-with-more-than-32-chars",
            "CORS_ORIGINS": "https://news.example.com",
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    def test_secure_production_settings_are_accepted(self):
        validate_runtime_settings(self.make_settings())

    def test_default_database_password_is_rejected_in_production(self):
        for password in ("password!", "   "):
            with self.subTest(password=password), self.assertRaisesRegex(RuntimeError, "数据库密码"):
                validate_runtime_settings(self.make_settings(DB_PASSWORD=password))

    def test_default_or_short_secret_is_rejected_in_production(self):
        for secret in ("wengaofabu-dev-secret-change-me", "too-short"):
            with self.subTest(secret=secret), self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
                validate_runtime_settings(self.make_settings(SECRET_KEY=secret))

    def test_wildcard_cors_is_rejected_in_production(self):
        with self.assertRaisesRegex(RuntimeError, "CORS"):
            validate_runtime_settings(self.make_settings(CORS_ORIGINS="*"))

    def test_development_keeps_local_defaults(self):
        validate_runtime_settings(
            Settings(
                _env_file=None,
                APP_ENV="development",
                DB_PASSWORD="password!",
                SECRET_KEY="wengaofabu-dev-secret-change-me",
                CORS_ORIGINS="*",
            )
        )

    def test_unknown_environment_uses_production_protection(self):
        with self.assertRaisesRegex(RuntimeError, "数据库密码"):
            validate_runtime_settings(
                self.make_settings(APP_ENV="staging", DB_PASSWORD="password!")
            )


if __name__ == "__main__":
    unittest.main()
