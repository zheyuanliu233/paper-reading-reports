# Paper Reading Reports

一个支持人工标签、关键词检索和筛选的中文论文阅读报告库。

## 访问地址

**[打开论文阅读报告库](https://zheyuanliu233.github.io/paper-reading-reports/)**

- GitHub Pages：https://zheyuanliu233.github.io/paper-reading-reports/
- GitHub 仓库：https://github.com/zheyuanliu233/paper-reading-reports

## 添加报告

把报告 HTML 放进 `reports/`，并在 `<head>` 中填写：

```html
<meta name="paper-slug" content="paper-slug">
<meta name="paper-title" content="论文标题">
<meta name="paper-summary" content="一句话中文摘要">
<meta name="paper-venue" content="CVPR 2025">
<meta name="paper-topics" content="world model, video">
<meta name="paper-tags" content="data process, theory, distill">
```

`paper-topics` 是第一级主题文件夹，一篇论文可以属于多个主题；`paper-tags` 是第二级方法标签，用于主题内筛选。两者都支持中文或英文，以逗号分隔。

前端的“编辑分类”可以把修改保存到当前浏览器，也可直接打开对应 GitHub 文件永久修改。永久修改后推送到 `main`，GitHub Actions 会自动重建索引、更新关联对比入口并部署 GitHub Pages。

## 本地重建

```bash
python3 build_index.py .
```

首次修改站点名称时使用：

```bash
python3 build_index.py . \
  --title "论文阅读报告库" \
  --description "中文精读、方法对比与复现指南"
```
