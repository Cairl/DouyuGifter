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
   - `COOKIE_PAT`: （可选）用于自动更新 `COOKIE` 的 GitHub PAT，需要 `repo` 权限
4. 启用 Actions 工作流

默认每 6 小时自动执行

## 注意事项

- Cookie 有效期约一周，需定期更新
- 每批最多赠送 100 个，自动分批

## 自动续期说明
当设置 `COOKIE_PAT` 后，工作流会在每次运行后自动把最新 Cookie 回写到仓库 Secret `COOKIE`。
如果 `COOKIE` 已完全过期，刷新接口无法挽救，仍需重新扫码获取新的 Cookie。

本文档只说明 GitHub Actions 的配置方式。
