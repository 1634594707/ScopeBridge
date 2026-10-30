# 统一风格采集模板

用于 `awesome-design-md`、提示词站点和自定义设计方向之间做中间层整理。

> 页面构建的主路径是 `/hallmark`(50 个现成主题材质 + 三级质量门 + sloplint 实测,用户级已装)。本采集卡的定位:**采集来的风格喂给 hallmark 的自定义 direction,或维持 DESIGN.md 作为项目长期设计基线**。

## 0. 先决定走哪条路

| 场景 | 走法 |
|---|---|
| 新页面、没有既定品牌风格 | 直接 `/hallmark <需求>`,让它推荐 3 个适配主题,不采集 |
| 有明确品牌/风格倾向,现成主题不够贴 | 用本模板采集 → 回写成 hallmark 自定义 `direction.md` → `/hallmark <需求>` 带自定义方向 |
| 长期项目要统一设计语言 | 采集 → 回写 `DESIGN.md` 作为基线,后续页面都基于它构建 |

hallmark 三级质量门(无论走哪条路都生效):

- **The Floor(底线,不过不上线)**:对比度、焦点可见、支持减少动效、不编造事实、移动端布局不坏
- **Reflex gates(反射门,要豁免必须记录理由)**:eyeball 小标签、全大写拉字距、标题单字变色、空框架占位、每页结尾邮箱订阅、提交了没反应的表单
- **Finish checks(细节检查,不阻塞)**:工艺细节

上线前实测:`node <hallmark 路径>/scripts/sloplint.mjs <文件> --render`(8 种宽度浏览器检查)。

---

## 1. 采集流程

建议使用顺序:

1. 先看真实品牌站点
2. 再看风格分类站点
3. 再补生成型 prompt
4. 最后回写成 `direction.md`(hallmark 自定义)或 `DESIGN.md`(项目基线)

不要先写 prompt,再倒推风格。

## 完整版采集卡

```text
# 风格采集卡

## 1. 基本信息
- 站点名称：
- 目录名称：
- 页面类型：官网 / SaaS / 文档 / 电商 / 作品集 / 后台 / 其他
- 主要模式：Light / Dark / Light + Dark

## 2. 真实品牌参考
- 主参考站点：
- 次参考站点：
- 参考原因：
- 最像它的地方：
- 明显不同的地方：

## 3. 风格标签
- 风格标签 1：
- 风格标签 2：
- 风格标签 3：
- 布局标签：
- 气质关键词：

## 4. 视觉摘要
- 一句话气质总结：
- 信息密度：低 / 中 / 高
- 留白感：弱 / 中 / 强
- 对比度：低 / 中 / 高
- 品牌感：弱 / 中 / 强
- 工具感 / 内容感 / 营销感：

## 5. 色彩系统
- 主色：
- 强调色：
- 背景色：
- 文本主色：
- 文本辅色：
- 边框 / 阴影色：
- 状态色：
- 色彩使用原则：

## 6. 排版系统
- 标题字体：
- 正文字体：
- 等宽字体：
- 标题风格：
- 正文风格：
- 字重策略：
- 字距策略：
- 行高策略：

## 7. 组件风格
- 按钮：
- 卡片：
- 导航：
- 输入框：
- 标签 / Badge：
- 弹层 / Modal：
- 图表 / 数据块：

## 8. 布局系统
- 容器宽度：
- 网格方式：
- 间距节奏：
- 圆角体系：
- 边框策略：
- 阴影策略：

## 9. 响应式行为
- 移动端变化：
- 平板变化：
- 桌面端特征：
- 折叠规则：

## 10. Do / Don't
- Do 1：
- Do 2：
- Do 3：
- Don't 1：
- Don't 2：
- Don't 3：

## 11. AI 生成表达
- 来自 uiprompt / designprompts 的可用表达：
- 可直接复用的描述句：
- 必须删除的空泛描述：

## 12. 最终落地产物
- DESIGN.md 重点章节：
- preview.html 必须展示的内容：
- preview-dark.html 必须展示的内容：
- README 需要特别说明的点：
```

---

## 极简版

```text
站点：
参考品牌：
风格标签：
一句话风格：
主色 / 背景 / 文本：
标题排版：
正文排版：
按钮风格：
卡片风格：
布局风格：
响应式特点：
Do：
Don't：
生成型 prompt：
最终要写入 DESIGN.md 的关键点：
```

---

## 示例

```text
站点名称：Vercel
目录名称：vercel
页面类型：SaaS / Developer Platform
主要模式：Light

主参考站点：Vercel
次参考站点：Linear
参考原因：都属于开发者工具审美，强调克制、精密、工程感

风格标签：
- minimal
- monochrome
- corporate-clean
- data-dense

一句话气质总结：
极度克制的工程化极简设计，靠留白、压缩字距和微妙边界建立秩序感。

主色：#171717
背景色：#ffffff
强调色：蓝 / 粉 / 红，仅用于流程语义
文本主色：#171717
边框策略：shadow-as-border

标题排版：Geist，大字号，负字距，600 权重
正文排版：Geist，16-20px，400 权重，较高可读性

按钮风格：小圆角、克制、深色主按钮
卡片风格：白底、轻阴影、边框感来自阴影
布局风格：大留白、规则网格、强节奏

Do：
- 用近黑而不是纯黑
- 用轻阴影模拟边框
- 用功能性色彩而不是装饰性色彩

Don't：
- 不要使用高饱和装饰色作为主视觉
- 不要堆积圆角和厚阴影
- 不要让组件比内容更抢眼

生成型 prompt：
clean white canvas, near-black typography, compressed headline tracking, subtle shadow-as-border cards, restrained accent color usage, developer-tool aesthetic

最终要写入 DESIGN.md 的关键点：
- Typography Rules
- Depth & Elevation
- Do's and Don'ts
- Agent Prompt Guide
```
