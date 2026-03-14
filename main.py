# -*- coding: utf-8 -*-
"""
斗鱼荧光棒赠送工具 - GitHub Actions版
自动赠送背包中所有荧光棒到指定直播间
支持Cookie保活刷新
"""

import os
import sys
import time
import json
import re
import requests
import logging
from urllib.parse import unquote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# 常量配置
DEFAULT_ROOM_ID = "74751"
FLUORESCENT_STICK_ID = 268  # 荧光棒ID

# 刷新接口
RENEW_URL = "https://passport.douyu.com/lapi/passport/iframe/safeAuth?client_id=1"
CSRF_URL = "https://www.douyu.com/curl/csrfApi/getCsrfCookie"

# 日志配置
LOG_LEVEL = os.environ.get("LOG_LEVEL", "").strip().upper() or "WARNING"
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

# 降低第三方库日志噪音
for _name in ("webdriver_manager", "WDM", "selenium", "urllib3"):
    logging.getLogger(_name).setLevel(logging.ERROR)
log = logging.getLogger(__name__)

COOKIE_ATTR_KEYS = {"path", "domain", "expires", "max-age", "secure", "httponly", "samesite"}


def normalize_cookie_string(cookie_str: str) -> str:
    if not cookie_str:
        return ""
    cookie_str = cookie_str.strip()
    if (cookie_str.startswith('"') and cookie_str.endswith('"')) or (
        cookie_str.startswith("'") and cookie_str.endswith("'")
    ):
        cookie_str = cookie_str[1:-1]
    cookie_str = cookie_str.replace("\r", "").replace("\n", "")
    return cookie_str.strip()


def parse_cookie(cookie_str: str) -> dict:
    """将Cookie字符串解析为字典"""
    cookie_str = normalize_cookie_string(cookie_str)
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            key = key.strip()
            if not key:
                continue
            if key.lower() in COOKIE_ATTR_KEYS:
                continue
            cookies[key] = value.strip()
    return cookies


def cookie_dict_to_string(cookie_dict: dict) -> str:
    return "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])


def get_cookie_string(session: requests.Session) -> str:
    """从Session中提取Cookie字符串"""
    header_cookie = session.headers.get("Cookie", "").strip()
    if header_cookie:
        return header_cookie
    cookie_dict = session.cookies.get_dict()
    return cookie_dict_to_string(cookie_dict)


def merge_cookie_string(cookie_str: str, response_cookies: requests.cookies.RequestsCookieJar) -> str:
    cookies = parse_cookie(cookie_str)
    for c in response_cookies:
        if c.name:
            cookies[c.name] = c.value
    return cookie_dict_to_string(cookies)


def set_session_cookie_header(session: requests.Session, cookie_str: str) -> None:
    if cookie_str:
        session.headers["Cookie"] = cookie_str


def should_output_cookie() -> bool:
    val = os.environ.get("OUTPUT_COOKIE", "").strip().lower()
    return val in {"1", "true", "yes", "y"}


def status(msg: str) -> None:
    print(msg, flush=True)


def emit_cookie_output(cookie_str: str) -> None:
    """Emit cookie to stdout for GitHub Actions outputs."""
    if should_output_cookie() and cookie_str:
        print(f"cookie={cookie_str}", flush=True)


def parse_jsonp(jsonp_str: str) -> dict:
    """解析JSONp字符串"""
    try:
        if not jsonp_str:
            return {}
        jsonp_str = jsonp_str.strip()
        match = re.search(r'^[^(]*\((.*)\)[^)]*$', jsonp_str)
        if match:
            return json.loads(match.group(1))
        # Fallback: sometimes server returns plain JSON
        if jsonp_str.startswith("{") and jsonp_str.endswith("}"):
            return json.loads(jsonp_str)
    except Exception as e:
        log.error(f"JSONp解析失败: {e}")
    return {}


def get_session(cookie_str: str) -> requests.Session:
    """从Cookie字符串创建Session"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://www.douyu.com",
        "Referer": "https://www.douyu.com/",
    })
    cookie_str = normalize_cookie_string(cookie_str)
    set_session_cookie_header(session, cookie_str)
    return session


def visit_room_with_selenium(cookie_str: str, room_id: str) -> bool:
    """使用 Selenium 无头浏览器访问目标直播间，触发荧光棒发放到背包"""
    log.info(f"触发荧光棒发放: 访问直播间 {room_id}")

    driver_path = ChromeDriverManager().install()
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(f'https://www.douyu.com/{room_id}')

        dy_cookies = parse_cookie(cookie_str)
        for name, value in dy_cookies.items():
            driver.add_cookie({
                'domain': '.douyu.com',
                'name': name,
                'value': value,
                'path': '/',
            })

        driver.refresh()

        # 检查登录状态
        try:
            WebDriverWait(driver, 30, 0.5).until(
                lambda d: d.find_element(By.XPATH, "//header//div[contains(@class, 'login')] | //header//div[contains(@class, 'user')]")
            )
            log.info("身份验证成功: 已登录")
        except Exception:
            log.warning("身份验证: 登录状态未知")

        log.info("等待荧光棒发放到背包...")
        time.sleep(10)
        log.info("浏览器任务完成")
        return True

    except Exception as e:
        log.error(f"浏览器异常: {e}")
        return False
    finally:
        driver.quit()
        log.debug("浏览器进程已终止")


def validate_cookie(session: requests.Session, room_id: str) -> tuple[bool, str]:
    """验证Cookie有效性，返回 (是否有效, 消息)"""
    try:
        url = f"https://www.douyu.com/japi/prop/backpack/web/v1?rid={room_id}"
        resp = session.get(url, timeout=10)
        data = resp.json()
        if data.get("error") == 0:
            return True, "验证通过"
        return False, data.get("msg", "验证失败")
    except Exception as e:
        return False, str(e)


def renew_cookies(session: requests.Session) -> tuple[bool, str]:
    """刷新Cookie和CSRF Token"""
    log.info("正在执行Cookie保活刷新...")
    refreshed = False
    cookie_str = get_cookie_string(session)

    # 1. 刷新Cookie
    headers = {
        "Referer": "https://www.douyu.com/directory/myFollow",
        "X-Requested-With": "XMLHttpRequest",
    }
    if cookie_str:
        headers["Cookie"] = cookie_str
    try:
        resp = session.get(RENEW_URL, headers=headers, timeout=10)
        data = parse_jsonp(resp.text)
        if data.get("error") != 0:
            log.warning(f"Cookie刷新接口返回异常: {data.get('msg')}")
        else:
            log.info("Cookie刷新请求成功")
            refreshed = True
        cookie_str = merge_cookie_string(cookie_str, resp.cookies)
        set_session_cookie_header(session, cookie_str)
    except Exception as e:
        log.error(f"Cookie刷新请求失败: {e}")

    # 2. 刷新CSRF Token
    try:
        csrf_headers = {}
        if cookie_str:
            csrf_headers["Cookie"] = cookie_str
        resp = session.get(CSRF_URL, headers=csrf_headers, timeout=10)
        data = resp.json()
        if data.get("error") == 0:
            log.info("CSRF Token刷新成功")
            refreshed = True
        else:
            log.warning(f"CSRF Token刷新失败: {data.get('msg')}")
        cookie_str = merge_cookie_string(cookie_str, resp.cookies)
        set_session_cookie_header(session, cookie_str)
    except Exception as e:
        log.error(f"CSRF Token刷新请求失败: {e}")

    # 输出更新后的Cookie由调用方决定，这里仅记录摘要
    log.info(f"Cookie refresh done. Total cookies: {len(session.cookies.get_dict())}")

    return refreshed, cookie_str


def keepalive_session(session: requests.Session) -> str:
    """保持Session活跃"""
    # 执行刷新逻辑
    _, cookie_str = renew_cookies(session)

    endpoints = [
        "https://www.douyu.com/member/cp/getFansBadgeList",
        "https://www.douyu.com/japi/prop/backpack/web/v1?rid=0",
    ]

    for url in endpoints:
        try:
            session.get(url, timeout=10)
            log.debug(f"保活请求: {url}")
        except Exception:
            pass
    return cookie_str


def get_backpack_gifts(session: requests.Session, room_id: str, retry: int = 3) -> list:
    """获取背包礼物，带重试机制"""
    url = f"https://www.douyu.com/japi/prop/backpack/web/v1?rid={room_id}"

    for i in range(retry):
        try:
            resp = session.get(url, timeout=10)
            data = resp.json()
            if data.get("error") == 0:
                gifts = data.get("data", {}).get("list", [])
                if any(g.get("id") == FLUORESCENT_STICK_ID for g in gifts) or i == retry - 1:
                    log.info(f"背包查询成功: {len(gifts)} 件物品")
                    return gifts
                log.warning(f"重试 {i+1}/{retry}: 未发现目标物品")
                time.sleep(2)
            else:
                log.warning(f"API错误 ({i+1}/{retry}): {data.get('msg')}")
                if i == retry - 1:
                    return []
                time.sleep(2)
        except Exception as e:
            log.error(f"网络异常 ({i+1}/{retry}): {e}")
            if i == retry - 1:
                return []
            time.sleep(2)

    return []


def send_gift(session: requests.Session, room_id: str, prop_id: int, count: int) -> bool:
    """赠送礼物"""
    url = "https://www.douyu.com/japi/prop/donate/mainsite/v1"
    data = {
        "propId": prop_id,
        "propCount": count,
        "roomId": room_id,
        "bizExt": '{"yzxq":{}}',
    }

    try:
        resp = session.post(url, data=data, timeout=10)
        result = resp.json()
        if result.get("error") == 0:
            log.info(f"赠送成功: [{prop_id}] x {count}")
            return True
        log.error(f"赠送失败: {result.get('msg')}")
        return False
    except Exception as e:
        log.error(f"请求异常: {e}")
        return False


def main():
    """主函数"""
    cookie = os.environ.get("COOKIE", "").strip()
    room_id = os.environ.get("ROOM_ID", DEFAULT_ROOM_ID)

    if not cookie:
        log.error("环境变量 COOKIE 未设置")
        sys.exit(1)

    status(f"room={room_id}")

    session = get_session(cookie)

    # ===== 步骤1: Cookie验证 =====
    log.info("=" * 40)
    log.info("[1/4] Cookie验证")
    # Refresh cookies first to extend TTL (best-effort)
    refreshed_cookie = keepalive_session(session)
    if refreshed_cookie:
        cookie = refreshed_cookie

    cookie_valid, msg = validate_cookie(session, room_id)
    if not cookie_valid:
        log.warning(f"验证失败: {msg}，尝试再次刷新 Cookie")
        refreshed_cookie = keepalive_session(session)
        if refreshed_cookie:
            cookie = refreshed_cookie
        cookie_valid, msg = validate_cookie(session, room_id)
        if not cookie_valid:
            log.error(f"验证失败: {msg}")
            sys.exit(1)
    status("cookie=ok")

    # 输出最新Cookie给 GitHub Actions（stdout），避免泄露到日志
    cookie = get_cookie_string(session) or cookie
    emit_cookie_output(cookie)

    # ===== 步骤2: 触发荧光棒发放 =====
    log.info("=" * 40)
    log.info("[2/4] 触发荧光棒发放")
    triggered = visit_room_with_selenium(cookie, room_id)
    status("trigger=ok" if triggered else "trigger=fail")

    # ===== 步骤3: 获取背包 =====
    log.info("=" * 40)
    log.info("[3/4] 查询背包")
    gifts = get_backpack_gifts(session, room_id)

    if not gifts:
        status("gifts=0 sticks=0")
        sys.exit(0)

    # 筛选荧光棒
    fluorescent_sticks = [g for g in gifts if g.get("id") == FLUORESCENT_STICK_ID]

    if not fluorescent_sticks:
        status(f"gifts={len(gifts)} sticks=0")
        sys.exit(0)
    stick_total = sum(int(s.get("count", 0) or 0) for s in fluorescent_sticks)
    status(f"gifts={len(gifts)} sticks={stick_total}")

    # ===== 步骤4: 赠送荧光棒 =====
    log.info("=" * 40)
    log.info("[4/4] 赠送荧光棒")
    total_sent = 0
    for stick in fluorescent_sticks:
        count = stick.get("count", 0)
        if count <= 0:
            continue

        if send_gift(session, room_id, FLUORESCENT_STICK_ID, count):
            total_sent += count
        time.sleep(0.3)

    log.info("=" * 40)
    status(f"sent={total_sent}")


if __name__ == "__main__":
    main()
