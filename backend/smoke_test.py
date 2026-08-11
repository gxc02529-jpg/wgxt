# -*- coding: utf-8 -*-
"""接口冒烟测试：验证核心业务流程，可随时重跑（python smoke_test.py）"""
import sys

import httpx

BASE = "http://127.0.0.1:8000/api"


def login(client, username, password):
    r = client.post(f"{BASE}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"登录失败: {r.text}"
    return r.json()["access_token"]


def main():
    client = httpx.Client(timeout=10)
    ed_token = login(client, "editor", "editor123")
    admin_token = login(client, "admin", "admin123")
    user_token = login(client, "user", "user123")
    ed_h, admin_h, user_h = (
        {"Authorization": f"Bearer {t}"} for t in (ed_token, admin_token, user_token)
    )

    # 1. 编辑创建文稿
    r = client.post(f"{BASE}/articles", headers=ed_h, json={
        "title": "测试文稿：人工智能如何改变新闻业",
        "summary": "这是一篇用于系统联调的测试文稿。",
        "content": "<p>这是正文内容。</p>",
        "cover_url": "",
        "category_ids": [3, 4],
    })
    assert r.status_code == 200, f"创建失败: {r.text}"
    aid = r.json()["article"]["id"]
    print(f"[1] 创建草稿 OK  id={aid}")

    # 2. 提交审核
    r = client.post(f"{BASE}/articles/{aid}/submit", headers=ed_h)
    assert r.status_code == 200, f"提交失败: {r.text}"
    print("[2] 提交一审 OK ->", r.json()["article"]["status"])

    # 3. 管理员一审
    r = client.post(f"{BASE}/reviews", headers=admin_h,
                    json={"article_id": aid, "level": 1, "action": "approve", "comment": "内容合格，通过一审"})
    assert r.status_code == 200, f"一审失败: {r.text}"
    print("[3] 一审通过 OK ->", r.json()["article"]["status"])

    # 4. 管理员二审
    r = client.post(f"{BASE}/reviews", headers=admin_h,
                    json={"article_id": aid, "level": 2, "action": "approve", "comment": "准予发布"})
    assert r.status_code == 200, f"二审失败: {r.text}"
    print("[4] 二审通过 OK ->", r.json()["article"]["status"])

    # 5. 前台列表可见
    r = client.get(f"{BASE}/articles", params={"category_id": 3})
    assert any(a["id"] == aid for a in r.json()["items"]), "文稿未出现在栏目列表中"
    print("[5] 前台列表可见 OK  total =", r.json()["total"])

    # 6. 用户观看埋点
    r = client.post(f"{BASE}/events", headers=user_h, json={"event_type": "view", "article_id": aid})
    assert r.json()["ok"], "观看埋点失败"
    print("[6] 观看埋点 OK")

    # 7. 点赞 / 收藏 / 转发
    for ep in ("like", "favorite", "share"):
        r = client.post(f"{BASE}/interactions/{ep}?article_id={aid}", headers=user_h)
        assert r.status_code == 200, f"{ep} 失败: {r.text}"
        print(f"[7] {ep} OK ->", r.json()["message"])

    r = client.get(f"{BASE}/interactions/status?article_id={aid}", headers=user_h)
    assert r.json() == {"liked": True, "favorited": True}, f"互动状态异常: {r.text}"
    print("[7] 互动状态 OK ->", r.json())

    # 8. 审核记录
    r = client.get(f"{BASE}/reviews/history", headers=admin_h)
    assert r.json()["total"] >= 2, "审核记录数量异常"
    print("[8] 审核记录 OK  total =", r.json()["total"])

    # 9. 统计概览
    r = client.get(f"{BASE}/stats/overview", headers=admin_h)
    stats = r.json()
    assert stats["total_views"] >= 1 and stats["total_likes"] >= 1, "统计数据异常"
    print("[9] 统计概览 OK ->", {k: stats[k] for k in ("published_articles", "total_views", "total_likes", "total_shares")})

    # 10. 趋势与用户活跃
    r = client.get(f"{BASE}/stats/trends", headers=admin_h, params={"days": 7})
    assert len(r.json()["items"]) == 7
    r = client.get(f"{BASE}/stats/user-activity", headers=admin_h, params={"days": 7})
    assert len(r.json()["items"]) == 7
    print("[10] 趋势/活跃统计 OK")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"测试失败: {e}")
        sys.exit(1)
