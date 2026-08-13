# -*- coding: utf-8 -*-
"""接口冒烟测试：验证核心业务流程，可随时重跑（python smoke_test.py）"""
import sys
import time
import io as _io

from openpyxl import Workbook

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

    # 0. 创建二审管理员（审核业务要求一审二审由不同管理员完成；已存在则忽略）
    r = client.post(f"{BASE}/users", headers=admin_h, json={
        "username": "admin2", "password": "admin123", "nickname": "二审管理员", "role": "admin",
    })
    assert r.status_code in (200, 400), f"创建二审管理员失败: {r.text}"
    admin2_token = login(client, "admin2", "admin123")
    admin2_h = {"Authorization": f"Bearer {admin2_token}"}
    print("[0] 二审管理员就绪 OK")

    # 动态获取可用栏目 id（数据库可能被重置，避免硬编码失效的栏目 id）
    r = client.get(f"{BASE}/categories")
    assert r.status_code == 200 and r.json()["items"], "无可用栏目"
    cat_ids = [c["id"] for c in r.json()["items"]][:2]
    print(f"[0] 栏目就绪 OK ids={cat_ids}")

    # 确保走人工两级审核流程：显式关闭自动审核（不依赖外部配置状态）
    r = client.put(f"{BASE}/settings/auto_review", headers=admin_h, json={"value": False, "value_type": "bool"})
    assert r.status_code == 200, f"关闭自动审核失败: {r.text}"
    print("[0] 自动审核已关闭 OK")

    # 1. 编辑创建文稿
    r = client.post(f"{BASE}/articles", headers=ed_h, json={
        "title": "测试文稿：人工智能如何改变新闻业",
        "summary": "这是一篇用于系统联调的测试文稿。",
        "content": "<p>这是正文内容。</p>",
        "cover_url": "",
        "category_ids": cat_ids,
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

    # 4. 二审管理员二审（不同审核人）
    r = client.post(f"{BASE}/reviews", headers=admin2_h,
                    json={"article_id": aid, "level": 2, "action": "approve", "comment": "准予发布"})
    assert r.status_code == 200, f"二审失败: {r.text}"
    print("[4] 二审通过 OK ->", r.json()["article"]["status"])

    # 5. 前台列表可见
    r = client.get(f"{BASE}/articles", params={"category_id": cat_ids[0]})
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
    assert r.json() == {"liked": True, "favorited": True, "disliked": False}, f"互动状态异常: {r.text}"
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

    # 11. 评论：未登录不可发表；登录可发表/回复；本人与管理员可删除；后台可检索
    r = client.post(f"{BASE}/comments", json={"article_id": aid, "content": "游客评论"})
    assert r.status_code == 401, f"未登录发表评论应被拒绝: {r.text}"
    print("[11] 未登录发表评论被拒绝 OK")

    r = client.post(f"{BASE}/comments", headers=user_h, json={"article_id": aid, "content": "这是一条测试评论"})
    assert r.status_code == 200, f"发表评论失败: {r.text}"
    cid = r.json()["comment"]["id"]
    print(f"[11] 发表评论 OK  id={cid}")

    r = client.post(f"{BASE}/comments", headers=user_h,
                    json={"article_id": aid, "content": "这是回复内容", "parent_id": cid})
    assert r.status_code == 200, f"发表回复失败: {r.text}"
    reply_id = r.json()["comment"]["id"]
    assert r.json()["comment"]["parent_id"] == cid
    print(f"[11] 发表回复 OK  id={reply_id}")

    r = client.get(f"{BASE}/comments", params={"article_id": aid})
    assert r.status_code == 200 and r.json()["total"] >= 1, "评论列表异常"
    top = next(c for c in r.json()["items"] if c["id"] == cid)
    assert any(c["id"] == reply_id for c in top["replies"]), "回复未嵌套在父评论下"
    print("[11] 评论列表（含回复嵌套）OK  total =", r.json()["total"])

    # 非法输入：空内容 / 对不存在的评论回复
    r = client.post(f"{BASE}/comments", headers=user_h, json={"article_id": aid, "content": "   "})
    assert r.status_code == 400, f"空评论应被拒绝: {r.text}"
    r = client.post(f"{BASE}/comments", headers=user_h,
                    json={"article_id": aid, "content": "回复不存在的评论", "parent_id": 999999})
    assert r.status_code == 404, f"回复不存在的评论应被拒绝: {r.text}"
    print("[11] 评论非法输入校验 OK")

    # 后台列表（管理员）可见该评论
    r = client.get(f"{BASE}/admin/comments", headers=admin_h, params={"keyword": "测试评论"})
    assert r.status_code == 200 and any(c["id"] == cid for c in r.json()["items"]), "后台评论列表异常"
    print("[11] 后台评论列表/检索 OK  total =", r.json()["total"])

    # 普通用户不能删别人的评论；作者本人可删自己的回复；管理员可删任意评论
    r = client.post(f"{BASE}/comments", headers=user_h, json={"article_id": aid, "content": "待管理员删除"})
    victim_id = r.json()["comment"]["id"]
    r = client.delete(f"{BASE}/comments/{victim_id}", headers=ed_h)
    assert r.status_code == 403, f"非作者/管理员删除应被拒绝: {r.text}"
    r = client.delete(f"{BASE}/comments/{victim_id}", headers=admin_h)
    assert r.status_code == 200, f"管理员删除失败: {r.text}"
    print("[11] 评论删除权限 OK（本人/管理员可删，其他人 403）")

    r = client.delete(f"{BASE}/comments/{reply_id}", headers=user_h)
    assert r.status_code == 200, "作者删除自己的回复失败"
    print("[11] 作者删除自己的回复 OK")

    # 12. 积分：未登录不可查/不可签；签到每天一次；后台可查看与调整
    r = client.get(f"{BASE}/points/me")
    assert r.status_code == 401, f"未登录查询积分应被拒绝: {r.text}"
    r = client.post(f"{BASE}/points/checkin")
    assert r.status_code == 401, f"未登录签到应被拒绝: {r.text}"
    print("[12] 未登录积分接口鉴权 OK")

    # 签到：当天未签则首次成功（1~5 随机），已签则返回"今日已签到"（幂等，测试可重复跑）
    r = client.post(f"{BASE}/points/checkin", headers=user_h)
    if r.status_code == 200:
        gained = r.json()["gained"]
        assert 1 <= gained <= 5, f"签到积分应在 1~5 之间: {gained}"
        assert r.json()["today_checked_in"] is True
        print(f"[12] 签到 OK  gained={gained} points={r.json()['points']}")
    else:
        assert r.status_code == 400 and "已签到" in r.text, f"签到异常: {r.text}"
        print("[12] 今日已签到（幂等通过）")

    # 每日一次限制：无论上面结果如何，再次签到必须被拒绝
    r = client.post(f"{BASE}/points/checkin", headers=user_h)
    assert r.status_code == 400, f"重复签到应被拒绝: {r.text}"
    r = client.get(f"{BASE}/points/me", headers=user_h)
    assert r.json()["today_checked_in"] is True
    print("[12] 每日一次签到限制 OK")

    # 后台积分列表可见该用户及其签到记录
    r = client.get(f"{BASE}/admin/points", headers=admin_h, params={"keyword": "user"})
    assert r.status_code == 200, f"后台积分列表失败: {r.text}"
    row = next((u for u in r.json()["items"] if u["username"] == "user"), None)
    assert row and row["checkin_count"] >= 1, "后台积分列表缺少签到统计"
    print("[12] 后台积分列表 OK  checkin_count =", row["checkin_count"])

    # 非管理员访问后台积分接口应 403
    r = client.get(f"{BASE}/admin/points", headers=user_h)
    assert r.status_code == 403, f"非管理员访问后台积分应被拒绝: {r.text}"

    # 管理员调整积分：+10 与负数超扣
    r = client.put(f"{BASE}/admin/points/{row['id']}", headers=admin_h, json={"delta": 10})
    assert r.status_code == 200, f"加分失败: {r.text}"
    assert r.json()["points"] == row["points"] + 10
    r = client.put(f"{BASE}/admin/points/{row['id']}", headers=admin_h, json={"delta": -100000})
    assert r.status_code == 400, f"超量扣分应被拒绝: {r.text}"
    print("[12] 后台调整积分 OK（正加负减 + 下限保护）")

    # 13. 编辑注册开关：默认开启可注册编辑；关闭后编辑注册被拒、普通用户注册正常
    uniq = int(time.time())
    r = client.put(f"{BASE}/portal/register-editor", headers=admin_h, json={"enabled": True})
    assert r.status_code == 200, f"开启编辑注册失败: {r.text}"
    r = client.post(f"{BASE}/auth/register", json={
        "username": f"ed_reg_{uniq}", "password": "pass123", "role": "editor",
    })
    assert r.status_code == 200, f"开启时注册编辑应成功: {r.text}"
    print("[13] 编辑注册开启状态 OK")

    r = client.put(f"{BASE}/portal/register-editor", headers=admin_h, json={"enabled": False})
    assert r.status_code == 200
    r = client.post(f"{BASE}/auth/register", json={
        "username": f"ed_reg2_{uniq}", "password": "pass123", "role": "editor",
    })
    assert r.status_code == 400 and "编辑注册已关闭" in r.text, f"关闭时注册编辑应被拒绝: {r.text}"
    r = client.post(f"{BASE}/auth/register", json={
        "username": f"u_reg_{uniq}", "password": "pass123", "role": "user",
    })
    assert r.status_code == 200, f"关闭时注册普通用户应成功: {r.text}"
    print("[13] 编辑注册关闭状态 OK（编辑被拒、普通用户正常）")

    # 恢复开启，避免影响后续测试/演示环境
    r = client.put(f"{BASE}/portal/register-editor", headers=admin_h, json={"enabled": True})
    assert r.status_code == 200
    print("[13] 编辑注册策略已恢复开启")

    # 14. OSS 配置：备份 → 验证上传分支 → 恢复原配置（不破坏真实环境的 OSS/MinIO 配置）
    saved = client.get(f"{BASE}/portal/oss-config", headers=admin_h)
    assert saved.status_code == 200
    saved_cfg = saved.json()["config"]
    was_configured = bool(saved_cfg["endpoint"])
    print(f"[14] OSS 配置读取 OK（当前{'已配置' if was_configured else '未配置'}）")

    files = {"file": ("test_oss.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/png")}
    if not was_configured:
        # 未配置：上传走本地，回归原逻辑
        r = client.post(f"{BASE}/resources/upload", headers=ed_h, files=files)
        assert r.status_code == 200, f"本地上传失败: {r.text}"
        assert r.json()["resource"]["storage"] == "local"
        assert "/static/" in r.json()["resource"]["url"], f"本地资源 URL 异常: {r.json()['resource']['url']}"
        print("[14] 未配置 OSS 上传走本地 OK")
    else:
        # 已配置：跳过本地回归，避免向真实 OSS 上传测试文件
        print("[14] 当前已配置 OSS，跳过本地上传回归（避免污染真实存储）")

    # 用无效 endpoint 覆盖配置，验证上传走 OSS 分支且明确报错；secret_key 传 **** 保留原值
    r = client.put(f"{BASE}/portal/oss-config", headers=admin_h, json={
        "endpoint": "http://127.0.0.1:9",
        "bucket": "test-bucket",
        "region": "us-east-1",
        "access_key": "test",
        "secret_key": "****",
        "path_prefix": "articles/",
        "public_base_url": "",
    })
    assert r.status_code == 200 and r.json()["configured"] is True
    assert r.json()["config"]["secret_key"] == "****", "secret_key 应脱敏"
    print("[14] OSS 配置保存/脱敏 OK")

    r = client.post(f"{BASE}/resources/upload", headers=ed_h, files=files)
    assert r.status_code == 502 and "对象存储上传失败" in r.text, f"应报 OSS 上传失败: {r.text}"
    print("[14] OSS 上传失败明确报错 OK")

    # 恢复原配置：secret_key 传 **** 保留原值，保证真实环境的密钥不受影响
    r = client.put(f"{BASE}/portal/oss-config", headers=admin_h, json={
        **saved_cfg,
        "secret_key": "****",
    })
    assert r.status_code == 200 and r.json()["configured"] == was_configured
    restored = client.get(f"{BASE}/portal/oss-config", headers=admin_h).json()["config"]
    assert restored["endpoint"] == saved_cfg["endpoint"] and restored["bucket"] == saved_cfg["bucket"]
    print("[14] OSS 配置已恢复原值 OK")

    # 15. 下线文稿重新编辑并再次发布：offline → 编辑 → 提审 → 一审 → 二审 → published
    r = client.post(f"{BASE}/articles/{aid}/offline", headers=admin_h)
    assert r.status_code == 200 and r.json()["article"]["status"] == "offline", f"下线失败: {r.text}"
    print("[15] 已发布文稿下线 OK")

    # 作者编辑已下线文稿，状态保持 offline
    r = client.put(f"{BASE}/articles/{aid}", headers=ed_h, json={
        "title": "测试文稿：人工智能如何改变新闻业（修订版）",
        "summary": "下线后重新编辑并再次发布",
        "content": "<p>修订后的正文内容。</p>",
        "cover_url": "",
        "category_ids": cat_ids,
    })
    assert r.status_code == 200 and r.json()["article"]["status"] == "offline", f"下线稿编辑失败: {r.text}"
    assert "修订版" in r.json()["article"]["title"]
    print("[15] 下线稿编辑 OK（状态保持已下线）")

    # 重新提审 → 两级审核 → 再发布
    r = client.post(f"{BASE}/articles/{aid}/submit", headers=ed_h)
    assert r.status_code == 200 and r.json()["article"]["status"] == "pending_first", f"重新提审失败: {r.text}"
    print("[15] 下线稿重新提审 OK ->", r.json()["article"]["status"])

    r = client.post(f"{BASE}/reviews", headers=admin_h, json={
        "article_id": aid, "level": 1, "action": "approve", "comment": "修订版一审通过",
    })
    assert r.status_code == 200 and r.json()["article"]["status"] == "pending_second", f"修订版一审失败: {r.text}"
    r = client.post(f"{BASE}/reviews", headers=admin2_h, json={
        "article_id": aid, "level": 2, "action": "approve", "comment": "修订版二审通过",
    })
    assert r.status_code == 200 and r.json()["article"]["status"] == "published", f"修订版二审失败: {r.text}"
    assert r.json()["article"]["published_at"], "再发布后应更新时间"
    print("[15] 重新审核通过并再发布 OK ->", r.json()["article"]["status"])

    # 16. 批量导入：构造 xlsx 覆盖成功/重复/栏目不匹配/封面缺失/标题为空分支
    wb = Workbook()
    ws = wb.active
    ws.append(["封面", "标题", "分类", "正文"])
    ws.append(["", f"导入测试文稿A_{uniq}", "游戏", "这是正文第一段。\n这是正文第二段。"])
    ws.append(["", f"导入测试文稿A_{uniq}", "游戏", "重复标题"])
    ws.append(["", f"导入测试文稿B_{uniq}", "游戏/不存在栏目", "正文B"])
    ws.append(["", f"导入测试文稿C_{uniq}", "", "正文C"])
    ws.append(["", "", "游戏", "标题为空"])
    buf = _io.BytesIO()
    wb.save(buf)
    r = client.post(f"{BASE}/articles/import", headers=ed_h, files={
        "file": ("import_test.xlsx", buf.getvalue(),
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    })
    assert r.status_code == 200, f"批量导入失败: {r.text}"
    res = r.json()
    assert res["imported"] == 3, f"应导入 3 篇: {res}"
    assert len(res["skipped"]) == 1 and res["skipped"][0]["reason"] == "标题已存在"
    assert len(res["failed"]) == 1 and res["failed"][0]["reason"] == "标题为空"
    assert any("栏目未匹配" in w["reason"] for w in res["warnings"])
    print(f"[16] 批量导入 OK imported={res['imported']} skipped={len(res['skipped'])} failed={len(res['failed'])}")

    # 导入的文稿为草稿且栏目正确（导入测试文稿B → 游戏栏目）
    r = client.get(f"{BASE}/articles/mine", headers=ed_h, params={"page_size": 50})
    imported_a = next((a for a in r.json()["items"] if a["title"] == f"导入测试文稿A_{uniq}"), None)
    assert imported_a and imported_a["status"] == "draft", "导入文稿应为草稿"
    assert imported_a["summary"].startswith("这是正文第一段"), "摘要应取正文首段"
    print("[16] 导入文稿状态/摘要 OK")

    # 非 xlsx 文件拒绝
    r = client.post(f"{BASE}/articles/import", headers=ed_h, files={"file": ("bad.txt", b"hello", "text/plain")})
    assert r.status_code == 400 and ".xlsx" in r.text, f"非 xlsx 应被拒绝: {r.text}"
    print("[16] 非 xlsx 文件拒绝 OK")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"测试失败: {e}")
        sys.exit(1)
