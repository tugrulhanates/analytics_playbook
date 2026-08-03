<div align="center">

# 📊 Analytics Playbook

**Real-world analytics, causal inference, and data leadership — worked, not just explained.**

[![Newsletter](https://img.shields.io/badge/LinkedIn-Analytics%20Playbook-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/)
[![Issues](https://img.shields.io/badge/Issues-growing%20weekly-0E7C6B?style=for-the-badge)](#-whats-in-this-repo)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey?style=for-the-badge)](#license)

</div>

---

## 🧠 What this is

**Analytics Playbook** is a LinkedIn newsletter for analysts, data scientists, and the people who lead them — built around one idea: most analytics mistakes aren't statistical, they're procedural. The same handful of failure modes (unchecked controls, misread significance, metrics without governance) show up in every domain, every team, every year.

Each issue takes **one technique or one habit** and walks through it the way you'd actually use it at work:

- 🧪 **A real method** — difference-in-differences, regression discontinuity, experiment design, and more
- 🔢 **A numeric worked example** you can follow step by step, not just a definition
- 📈 **Visual intuition** — the chart that makes the concept click
- ⚠️ **The mistakes people actually make** with it, and how to catch them
- ✅ **A checklist** you can run before you ship the result

This repository is the companion to the newsletter: the data, charts, and source files behind every issue, so you can rebuild the example yourself instead of just taking the conclusion on faith.

> A number is only as trustworthy as the process that produced it. This repo is that process, shown in the open.

---

## 📬 Read the newsletter

**➡️ [Analytics Playbook on LinkedIn](https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/)**

New issues ship regularly. Subscribe on LinkedIn to get each one as it's published — this repo is updated alongside every issue.

---

## 📁 What's in this repo

Each issue gets its own folder containing the source material used to build it — figures, worked-example data, and the write-up itself.

| Example Name | Folder Name | Notes |
|---|---|---|
| **Customer Segmentation** | `customer_segmentation` | The python script ins this folder provides "Rule Based", "RFM Segmentation" and "K-means Clustering" examples with dummy data to practice each segmentation option. |
| **Regression Discontinuity** | `regression-discontinuity` | Loyalty-programme tier-upgrade case study — using a hard points threshold as a natural experiment, plus the bunching/manipulation check that can quietly invalidate it. |

> 📌 New folders are added as new issues publish. If you're looking for an issue and don't see its folder yet, it's coming.

---

## 🗂️ How to use this repo

```bash
git clone https://github.com/<your-username>/analytics_playbook.git
cd analytics_playbook
```

Each folder is self-contained — open its notes, rerun the numbers, or drop the worked example straight into your own team's next data debate.

---

## 🙋 Who this is for

Analysts who want to get promoted for their judgment, not just their dashboards. Managers who want their team to stop re-litigating the same statistical mistakes. Anyone who has ever presented a number in a meeting and quietly hoped nobody asked "compared to what?"

---

## ⭐ Follow along

If a technique in here saves you from shipping a wrong conclusion, that's the whole point. Subscribe to the newsletter, star the repo, and feel free to open an issue if you spot a mistake — that's exactly the kind of thing this playbook is about catching.

<div align="center">

**[📬 Subscribe on LinkedIn](https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/)**

</div>

---

<sub>© Analytics Playbook. Content shared for educational use — see [license](#license) for terms.</sub>
