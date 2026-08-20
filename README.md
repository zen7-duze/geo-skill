# Vigilath GEO Skills

把「品牌在 AI 搜索引擎里的可见性」这件事,做成你的 AI 助手可以直接调用的技能。

支持 [OpenClaw](https://openclaw.ai)、Claude Code,以及任何能读 `SKILL.md` 的 agent。

**三个能力不需要注册、不需要任何凭证,装上就能用**:任意网站的 GEO 体检、SEO 体检,
以及拿一个品牌去问 AI 引擎、把原话贴回来。

## 装

```bash
# 一行装(装进机器上所有已存在的 skills 目录)
curl -fsSL https://vigilath.cn/skill/install.sh | bash

# 或者:克隆本仓库后本地装(想先读代码再跑的话)
git clone https://github.com/zen7-duze/geo-skill.git && cd geo-skill
bash vigilath-geo/install.sh --dir ~/.openclaw/skills

# 或者:交给 OpenClaw 的安装器
openclaw skills install git:zen7-duze/geo-skill@main --global
```

无参数运行会走设备码授权(终端出配对码 → 浏览器批准)。**只想用免登录那三个能力的话,授权可以跳过。**

## 八个窄技能

| 目录 | 一句话价值 | 用户要给 | 首次见效 | 要登录 | 免费段 / 墙 |
|---|---|---|---|---|---|
| `vigilath-site-audit` | **网站 AI 友好度检测** —— 给个网址,看 AI 能不能读懂你的网站 | 1 个网址 | 30 秒 | **否** | 全量 25 类,不限次;**无墙** |
| `vigilath-seo-audit` | **搜索引擎优化检测** —— 百度谷歌那套你还差哪几项 | 1 个网址 | 30 秒 | **否** | 全量 12 类,不限次;**无墙** |
| `vigilath-mention` | **AI 会不会推荐你** —— 拿品牌去问 AI,把原话贴回来 | 品牌 + 行业词 | 1–3 分钟 | **否** | 每设备 2 次/30 天(按设备 + 出口 IP) |
| `vigilath-report` | **品牌 AI 搜索体检报告** —— 能直接发给老板的完整报告 | 品牌 + 行业词 | 8–20 分钟 | 是 | 终身赠 1 次;之后按档配额 |
| `vigilath-radar` | **客户会怎么问 AI** —— 40 条客户真会问的问题,标出你没出现的 | 品牌 | 30 秒 | 是 | 40 条候选全预览;**加入持续监测 → 收费** |
| `vigilath-content` | **写一篇 AI 愿意引用的文章** —— 成稿前先过广告法 | 选一个 AI 没提到你的问题 | 5 分钟 | 是 | 提纲 + 首段 + 合规结论;**全文 + 配图 → 收费** |
| `vigilath-weekly` | **AI 搜索周报** —— 每周涨了还是跌了 | 无 | 秒 | 是 | 首期一份;**第二期起订阅** |
| `vigilath-sentinel` | **品牌负面预警** —— 真人发的帖,带原帖链接和时间 | 品牌 + 别名 | 秒 | 是 | 今日前 5 条 + 热榜;**历史/预警/配词 → 收费** |

`vigilath-geo` = 兜底全能包,**八种场景一个包全吃**(上面八个窄技能的能力它都有),
给一次只肯装一个技能的宿主用。SkillHub 上架的就是它。

## 收费边界

**看现状免费,持续盯和动手收费。**

- 检测线(站内 25 类、SEO 12 类、AEO、爬虫可达、权威信号、全面诊断)—— 免费,分档管控
- 监测线(持续跑批、日周月报、舆情、任务中心)—— 收费
- 发文线(生成、配图、合规、分发、被引归因)—— 收费

## 三条纪律(所有技能共用)

1. **免费段绝不给假数据充数。** 只跑 3 个引擎就说 3 个,不摆 10 个格子打码 7 个。显式降级优于视觉充数。
2. **每个数字都能下钻到引擎原话和采集时间。** 这是与同类产品的根本区别。
3. **每个要花钱的停顿都必须说清三件事**:做什么 / 花多少 / 还剩多少。三缺一就别往下走。

## 这个客户端在你机器上做什么

装之前你可以先把 `install.sh` 和 `geo_client.py` 下下来读一遍 —— 它们加起来不到 500 行,纯 Python 标准库,**零三方依赖**。

**会做的:**

- 向**你指定的那一个站点**发请求(`VIGILATH_BASE`,默认 `https://vigilath.cn`)。代码里所有出网点都拼自这个变量,没有第二个目的地。
- 发出去的内容就是你让它测的东西:网址、品牌名、行业词,加一个本机随机生成的设备标识(用于免登录额度分桶)。
- 在 `~/.vigilath/config` 写凭证与设备标识,权限 `600`。
- 授权凭证只放进 `Authorization` 请求头;免登录的三个命令(`check` / `mention` / `industry`)**明确不带**它。

**不会做的:**

- 不读你机器上的其他文件、不扫目录、不收集环境变量
- 不打印凭证,任何报错信息里都不会带上它
- 不装任何依赖、不改你的 shell 配置、不留后台进程

不放心 `curl | bash` 的话,克隆本仓库后本地安装即可:

```bash
git clone https://github.com/zen7-duze/geo-skill.git && cd geo-skill
bash vigilath-geo/install.sh --dir ~/.openclaw/skills
```

## 测试

零依赖,只要 `python3` 和 `bash`:

```bash
bash tests/run.sh
```

| 文件 | 测什么 |
|---|---|
| `tests/test_geo_client.py` | 客户端 15 项:凭证读写、设备标识不冲掉已有 token、**免登录命令不带 Authorization**、402 当成付款要求而非错误、金额换算、命令分发 |
| `tests/test_skills_meta.py` | 技能包 7 项:frontmatter 的 name 与目录名一致、描述含触发语、SKILL.md 里写的命令客户端真的有、**零三方依赖**、无内部信息 |
| `tests/test_install.sh` | 安装 7 项:装到哪、`--skills` 选装、错误技能名跳过不中断、**在源码仓库里跑不污染源码目录**、凭证权限 600 |

每次 push 由 GitHub Actions 自动跑(`.github/workflows/test.yml`)。CI 里**刻意不装任何依赖** —— 一旦需要 `pip install`,说明零依赖这个承诺已经被破坏了。

## 共享客户端

客户端只有一份源:`vigilath-geo/scripts/geo_client.py`,安装时复制进每个技能目录 —— 各技能自带副本是 skill 规范要求的自包含,但源只有一份,不会各自漂移。

```
check <网址> [--no-seo|--seo-only]   免登录、免费、不限次
mention <品牌> <行业词>              免登录,拿品牌问 AI 贴原话;每设备 2 次/30 天
industry [行业名]                    免登录,行业里谁是 TOP1(仅已建库行业)
chat "<问题>"                        走平台 agent,需授权
wallet                              看余额(花钱的动作之前先看一眼)
topup <金额> [--tx 0x…]             充值:先拿付款要求,链上付完带交易哈希核销
data <名字>                          直接取数,不走大模型,需授权
capabilities                        当前凭证能做什么
login                               设备码授权 / 重新授权
```

---

数据与账号由 [Vigilath](https://vigilath.cn) 提供。技能定义与客户端代码按 Apache 2.0 开源。
