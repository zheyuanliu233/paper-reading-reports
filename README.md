# Paper Reading Reports

一个支持人工标签、关键词检索和筛选的中文论文阅读报告库。

## 添加报告

把报告 HTML 放进 `reports/`，并在 `<head>` 中填写：

```html
<meta name="paper-slug" content="paper-slug">
<meta name="paper-title" content="论文标题">
<meta name="paper-summary" content="一句话中文摘要">
<meta name="paper-venue" content="CVPR 2025">
<meta name="paper-tags" content="diffusion, image-generation, cvpr-2025">
```

标签可以用英文或中文，以逗号分隔。修改报告或标签后推送到 `main`，GitHub Actions 会自动重建索引并部署 GitHub Pages。

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
