# app-inspect（中文说明）

**那个 4.7 分的 App，现在还是 4.7 分吗？** `app-inspect` 用苹果公开的数据接口，把 App Store 应用的历史总评分和最近评论的真实情况放在一起比：按版本拆分、列出差评主要在抱怨什么，一条命令搞定。不需要 API Key、不需要账号、没有后端、零依赖。

## 为什么需要

App Store 首页显示的分数是历史累计平均分，评分数一多就几乎不动。一次糟糕的更新、新加的付费墙、登录 bug，可能让最近的评论一落千丈，而「获取」按钮旁边的数字依然是 4.7。2026 年一项针对 120 个热门 App 的研究发现，[有 27 个 App 最近评论比显示评分低 2 星以上](https://github.com/Rajeshzheng/rating-gap-study)。

## 安装

```sh
pipx install git+https://github.com/Harrison0223-svg/app-inspect-cli
```

需要 Python 3.9+，只用标准库。

## 用法

```sh
app-inspect "microsoft authenticator"            # 名称、id 或 App Store 链接
app-inspect 983156458 --country cn               # 其他地区商店
app-inspect compare 983156458 388497605 494168017  # 多个 App 横向对比
app-inspect search "笔记" --country cn           # 查 id
app-inspect 983156458 --format json              # 给脚本和 AI agent 用
```

## 怎么看结果

- **差距（Gap）** = 历史总评分 − 最近文字评论平均分。`in line` < 1，`drifting` 1–2，`big gap` ≥ 2，`improving` ≤ −0.5。
- **按版本**：某版本（≥5 条评论）比上一版本低 0.5 星以上会标记 `▼ regression`。
- **差评主题**：在 1–2 星评论里归类崩溃、订阅/价格、广告、登录、性能、数据丢失、更新倒退、隐私、客服等，并各附一句原文。
- **请横向比较**：写文字评论的人本来就更偏负面，所以差距 1 左右很正常；同类 App 都在 1 而它在 3，才是信号。`compare` 就是为此准备的。

## 开发者：监控自己的 App

`--max-gap 1.5` 在差距超过阈值时以退出码 3 结束，适合放进 cron 或 CI 做报警。

## 在 Claude Code / Codex 里用

把 `skills/app-inspect` 文件夹复制到 `~/.claude/skills/` 或 `~/.codex/skills/`，装好 CLI，然后直接问「Authy 现在还值得装吗？」即可。

## 许可证

MIT

## 长期追踪（v0.2）

`app-inspect watch <app> --history data/history.jsonl --fail-on-change`：每次运行记录一条快照，并说明相比上次的变化（新版本、评分下降、差距等级变化、新的版本退步）；变差时退出码为 4，可接入 cron / GitHub Action（见 `examples/watch-app.yml`）。
