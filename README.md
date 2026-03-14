# DouyuGifter

斗鱼直播荧光棒自动赠送工具，专为 GitHub Actions 设计。

## 功能

* 领取每日免费荧光棒
* 自动赠送指定直播间

## GitHub Actions 部署

1. Fork 本仓库
2. 进入 Settings → Secrets and variables → Actions
3. 添加 Secrets:
   - `COOKIE`: 斗鱼账号 Cookie（必需）
   - `ROOM_ID`: 目标直播间 ID（可选，默认 74751）
4. 启用 Actions 工作流

默认每天北京时间 8:00 自动执行

## 注意事项

- Cookie 有效期约一周，需定期更新
- 每批最多赠送 100 个，自动分批
