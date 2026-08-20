#!/usr/bin/env python3
"""技能包结构校验 —— 装出去之前就该拦住的低级错。

宿主 agent 靠 frontmatter 选技能:name 错了装不上、description 缺了选不中、
触发语重叠会让它在几个技能之间挑错。这些都是"看起来没事、用起来才发现"的问题。

    python3 tests/test_skills_meta.py
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p for p in ROOT.glob("vigilath-*/SKILL.md"))
FREE = {"vigilath-site-audit", "vigilath-seo-audit", "vigilath-mention"}


def frontmatter(md: Path) -> dict:
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    out, key = {}, None
    for line in block.splitlines():
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).strip()
        elif key and line.strip():
            out[key] += " " + line.strip()
    return out


class StructureTest(unittest.TestCase):
    def test_at_least_eight_skills(self):
        self.assertGreaterEqual(len(SKILLS), 8, f"只找到 {len(SKILLS)} 个技能")

    def test_每个技能都有可用的_frontmatter(self):
        for md in SKILLS:
            with self.subTest(skill=md.parent.name):
                fm = frontmatter(md)
                self.assertIn("name", fm)
                self.assertIn("description", fm)
                self.assertEqual(fm["name"], md.parent.name,
                                 "name 必须等于目录名,否则宿主装进去找不到")
                self.assertGreaterEqual(len(fm["description"]), 40,
                                        "description 太短,商店里选不中")
                self.assertLessEqual(len(fm["description"]), 800,
                                     "description 过长,有的宿主会截断")

    def test_描述里要有触发语(self):
        """没有「当用户问…时使用」这类触发线索,宿主没法判断什么时候调。"""
        for md in SKILLS:
            with self.subTest(skill=md.parent.name):
                d = frontmatter(md)["description"]
                self.assertTrue(("当用户" in d) or ("使用" in d), "缺触发语描述")

    def test_免登录技能必须写明不需要登录(self):
        for md in SKILLS:
            if md.parent.name not in FREE:
                continue
            with self.subTest(skill=md.parent.name):
                d = frontmatter(md)["description"]
                self.assertTrue(("免登录" in d) or ("不需要登录" in d) or ("不需要注册" in d),
                                "免登录是最大卖点,描述里必须写")

    def test_正文提到的命令都真实存在(self):
        """SKILL.md 里写了个客户端没有的命令 = agent 照着跑必然失败。"""
        client = (ROOT / "vigilath-geo" / "scripts" / "geo_client.py").read_text(encoding="utf-8")
        known = set(re.findall(r'cmd == "([a-z-]+)"', client))
        self.assertTrue(known, "没从客户端解析出任何命令")
        for md in SKILLS:
            used = set(re.findall(r"geo_client\.py\s+([a-z-]+)", md.read_text(encoding="utf-8")))
            for c in used - {"--no-seo", "--seo-only"}:
                with self.subTest(skill=md.parent.name, cmd=c):
                    self.assertIn(c, known, f"SKILL.md 写了不存在的命令 {c!r}")

    def test_skillhub_发布字段齐全(self):
        """SkillHub 发布要求 slug / version(SemVer) / displayName —— 缺一个 publish 直接失败。

        Claude 与 OpenClaw 只认 name + description,多出来的字段它们会忽略,
        所以一份 SKILL.md 能同时满足三个平台。别为了迁就某一家把 name 改掉。
        """
        semver = re.compile(r"^\d+\.\d+\.\d+(?:[-+].+)?$")
        slug_pat = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        for md in SKILLS:
            with self.subTest(skill=md.parent.name):
                fm = frontmatter(md)
                self.assertEqual(fm.get("slug"), md.parent.name, "slug 必须等于目录名")
                self.assertTrue(slug_pat.match(fm.get("slug", "")), "slug 必须是 kebab-case")
                self.assertTrue(semver.match(fm.get("version", "")), f"version 不是 SemVer: {fm.get('version')}")
                self.assertTrue((fm.get("displayName") or "").strip(), "缺 displayName")
                self.assertTrue((fm.get("summary") or "").strip(), "缺 summary(商店列表页展示这句)")
                self.assertLessEqual(len(fm.get("summary", "")), 120, "summary 太长,列表页会截断")

    def test_全能包覆盖客户端所有命令(self):
        """全能包是唯一入口(SkillHub 上架的就是它),客户端有的命令它必须都写到。

        只在表格里写中文能力名不算数 —— agent 要照着敲命令,
        文档里没有命令名,它就跑不出来。2026-08-20 漏过 mention。
        """
        client = (ROOT / "vigilath-geo" / "scripts" / "geo_client.py").read_text(encoding="utf-8")
        umbrella = (ROOT / "vigilath-geo" / "SKILL.md").read_text(encoding="utf-8")
        cmds = set(re.findall(r'cmd == "([a-z-]+)"', client))
        for c in sorted(cmds):
            with self.subTest(cmd=c):
                self.assertIn(c, umbrella, f"全能包文档没提到命令 {c!r}")
        for mode in re.findall(r'^\s+"([a-z-]+)":\s+\("(?:url|entity|urls)"', client, re.M):
            with self.subTest(advanced_mode=mode):
                self.assertIn(mode, umbrella, f"全能包文档没提到高级检测模式 {mode!r}")

    def test_网站九张卡片全部列入(self):
        """网站「高级检测能力」那一屏的九张卡片,全能包文档必须逐条列到。

        用户看着网站上的卡片名来问,文档里没有这个词,agent 就接不上话。
        名字取自 i18n 的 home.advanced.cards.*,改文案时两边要一起改。
        """
        cards = ["一键全面诊断", "AEO 可见性审计", "竞争对比检测", "AI 爬虫测试",
                 "权威信号审计", "AI 引用检测", "AI 可见性审计", "实体 GEO 审计", "舆情监测"]
        doc = (ROOT / "vigilath-geo" / "SKILL.md").read_text(encoding="utf-8")
        for c in cards:
            with self.subTest(card=c):
                self.assertIn(c, doc, f"网站上有「{c}」这张卡片,全能包文档里没提")

    def test_合集列全八个窄技能(self):
        """全能包是「合集」,SkillHub 上架的就是它 —— 八个窄技能的名字必须都能在里面找到。

        用户装了合集,就该在文档里看到自己买到了哪些能力;
        少列一个,那个能力对他等于不存在。
        """
        umbrella = (ROOT / "vigilath-geo" / "SKILL.md").read_text(encoding="utf-8")
        for md in SKILLS:
            if md.parent.name == "vigilath-geo":
                continue
            name = frontmatter(md).get("displayName", "")
            with self.subTest(skill=md.parent.name, displayName=name):
                self.assertIn(name, umbrella, f"合集里没提到「{name}」({md.parent.name})")

    def test_没有内部信息泄漏(self):
        """这些文件会进公开仓库 —— 内网地址、内部服务名、凭证样式都不能有。"""
        bad = re.compile(r"127\.0\.0\.1|localhost|172\.80|123\.125|/opt/geo|ec2-|"
                         r"geo-backend|geo-telemetry|browser-service|github_pat_")
        for f in list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.sh")):
            if "tests/" in str(f.relative_to(ROOT)):
                continue
            with self.subTest(file=str(f.relative_to(ROOT))):
                hits = bad.findall(f.read_text(encoding="utf-8", errors="ignore"))
                self.assertFalse(hits, f"疑似内部信息:{set(hits)}")

    def test_客户端零三方依赖(self):
        """装完即用是这套 skill 的立身之本,任何 import 三方包都会破坏它。"""
        client = (ROOT / "vigilath-geo" / "scripts" / "geo_client.py").read_text(encoding="utf-8")
        stdlib_ok = {"json", "os", "sys", "urllib", "base64", "time", "socket", "uuid",
                     "hashlib", "importlib", "__future__", "typing", "datetime"}
        for mod in re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_][\w.]*)", client, re.M):
            with self.subTest(module=mod):
                self.assertIn(mod.split(".")[0], stdlib_ok, f"引入了非标准库 {mod}")


class CoverageAgainstBackendTest(unittest.TestCase):
    """与后端能力对齐 —— 仅在能看到后端源码时运行(公开仓库里自动跳过)。

    2026-08-20 两次漏接:第一次漏了 visibility(网站七张卡片只接了六个),
    第二次漏了 competitive-intel(后端有端点、标 free,网站卡片里没有)。
    靠人眼比对必然再漏,所以让测试直接数后端有几个。
    """

    def test_高级检测模式与后端一致(self):
        backend = ROOT.parent / "backend" / "geo" / "api" / "advanced_anon.py"
        if not backend.exists():
            self.skipTest("看不到后端源码(公开仓库里正常)")
        server_modes = set(re.findall(r'@router\.post\("/check/advanced-anon/([a-z-]+)"\)',
                                      backend.read_text(encoding="utf-8")))
        client = (ROOT / "vigilath-geo" / "scripts" / "geo_client.py").read_text(encoding="utf-8")
        client_modes = set(re.findall(r'^\s+"([a-z-]+)":\s+\("(?:url|entity|urls)"', client, re.M))
        self.assertEqual(server_modes, client_modes,
                         f"后端有而 skill 没接:{server_modes - client_modes};"
                         f"skill 有而后端没有:{client_modes - server_modes}")


class BackendSanityTest(unittest.TestCase):
    """后端自检 —— 仅在能看到后端源码时运行(公开仓库里自动跳过)。"""

    def test_微信服务里调用的自身方法都存在(self):
        """`self.xxx()` 调了不存在的方法,Python 要等到那行真跑到才报错。

        2026-08-20 就这么炸过:create_topup_native_order 里写了 self.is_configured(),
        而这个方法根本不存在;单测把整个函数 mock 掉了,直到线上第一次真调才发现。
        """
        src = ROOT.parent / "backend" / "geo" / "services" / "wechat_pay_service.py"
        if not src.exists():
            self.skipTest("看不到后端源码(公开仓库里正常)")
        # 去掉注释与文档字符串再扫 —— 否则"我原来写成了 self.xxx()"这种注释会误报
        raw = src.read_text(encoding="utf-8")
        text = re.sub(r'"""[\s\S]*?"""', "", raw)
        text = "\n".join(re.sub(r"#.*$", "", ln) for ln in text.splitlines())
        defined = set(re.findall(r"^\s{4}def ([a-zA-Z_]+)\(", text, re.M))
        called = set(re.findall(r"self\.([a-zA-Z_]+)\(", text))
        missing = {c for c in called if c not in defined}
        self.assertFalse(missing, f"调用了不存在的方法:{sorted(missing)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
