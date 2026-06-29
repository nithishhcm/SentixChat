![Python](https://img.shields.io/badge/Python-3.x-blue)
![NLP](https://img.shields.io/badge/NLP-Sentiment_Analysis-orange)
![Selenium](https://img.shields.io/badge/Selenium-Automation-green)
![Matplotlib](https://img.shields.io/badge/Matplotlib-Analytics-purple)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
# 💬 SentixChat: Advanced NLP Sentiment & Live Conversational Interest Analytics

An enterprise-grade, dark-themed Natural Language Processing (NLP) desktop application engineered using **Python 3**, **Tkinter Interface Engines**, **Selenium Core Web Drivers**, and **Matplotlib**. 

**SentixChat** delivers an end-to-end framework capable of transforming raw conversational text strings into high-fidelity behavioral analytics. By blending localized token-matching heuristic rules with multi-threaded browser automation, SentixChat parses real-time text flows to model participant messaging speed, semantic polarity, and custom composite engagement indices.

---

## ⚡ Direct Live WhatsApp Web Integration & Real-Time Syncing

Unlike basic, static text parsers, **SentixChat** features an advanced, multi-threaded live scraping pipeline designed to read, sanitize, and track incoming text directly from a live WhatsApp environment:

* **Asynchronous Scraper Subsystems:** Utilizes a decoupled background `threading.Thread` instance to manage web drivers, completely isolating heavy automated page interactions from the parent Tkinter window loop to ensure a zero-lag user experience.
* **Persistent Session Token Profiling:** Generates a localized data sandbox directory (`.whatsapp_profile`) on runtime. This retains authentication cookies, session states, and secure local storage metrics so you only have to scan the WhatsApp Web QR code once across separate application runs.
* **Reactive DOM Focus Switching:** Programmatically targets active `.copyable-text` container elements. The browser routine extracts raw message text bodies, automatically filters out meta-noise elements (such as "Read", "Delivered", and timestamp receipts), and listens for top-bar target contact changes to shift graph scopes on the fly.

<!-- INSERT SYSTEM WORKFLOW ARCHITECTURE OR DASHBOARD SCREENSHOT HERE -->

---

## 🚀 Specialized Processing Engine Highlights

### 🧠 1. Light-Weight Lexicon-Based Sentiment Pipeline
To circumvent the resource overhead and external API rate limits of heavy Transformer-based models, SentixChat deploys a precision rule-based string evaluation matrix:
* **Contextual Negation Flip Timers:** Scans tokens for core negation words (`not`, `never`, `dont`, `cant`). Detection triggers a localized multi-word multiplier, effectively reversing emotional polarity flags on succeeding words (e.g., scoring "not great" safely as a negative value of $-1.0$ instead of a false positive $+1.0$).
* **Linguistic Booster Amplifiers:** Identifies lexical intensifiers (`very`, `really`, `so`, `extremely`) to scale the mathematical sentiment impact of following words by a $1.5\times$ amplification multiplier (e.g., scaling "happy" from $+1.0$ to $+1.5$).
* **Direct Unicode Emoji Weighting Mapping:** Maps explicit graphical emoticons directly to custom mathematical weights reflecting modern messaging semantics ($\text{e.g., } ❤️ = +1.5, 😭 = -1.5, 🤬 = -1.8$).

### 📊 2. Multi-Dimensional Composite Interest Indexing
To measure participant engagement accurately, SentixChat pipes raw conversational vectors into a comprehensive heuristic behavioral scale ranking senders from $0 \text{ to } 100$:

$$\text{Interest Score} = \text{Velocity Pts (30)} + \text{Volume Pts (25)} + \text{Polarity Pts (25)} + \text{Emoji Density Pts (20)}$$

1. **Response Velocity Speed (30 Points Max):** Tracks cross-sender interaction timings. An automated filter drops outlier time gaps exceeding 8 hours to eliminate sleeping/working anomalies, focusing strictly on active conversational chemistry.
2. **Volumetric Word Counts (25 Points Max):** Scores the textual thickness and character length per message to separate high-investment, descriptive replies from low-investment, brief fillers (e.g., "Ok", "Yeah").
3. **Sentiment Base Trajectory (25 Points Max):** Monitors continuous moving averages of sentiment polarity to graph systemic conversational warmth versus coldness.
4. **Emoji Expression Concentration (20 Points Max):** Analyzes the exact structural ratio of emojis per message string to evaluate overall graphical enthusiasm.

---

## 🛠️ Local Deployment & Deployment Blueprint

### Prerequisites
* **Python 3.8** or higher installed on your master workstation.
* **Google Chrome Web Browser** installed (Selenium handles specific driver binary configurations downstreams automatically).

<img width="1687" height="1035" alt="image" src="https://github.com/user-attachments/assets/a07fb01d-89a9-4af9-83e7-ea059a273fa6" />

