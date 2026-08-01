<div align="center">

# 🏛 Youth Council Bot

### A Telegram bot that runs a council meeting from the agenda to the signed protocol

The admin opens a session, members join with a code and a password, everyone votes on each
agenda item separately, and the bot produces the meeting protocol and the attendance appendix
as DOCX files. Built for the Youth Council of the Rava-Ruska city council.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Language](https://img.shields.io/badge/Interface-Ukrainian-005BBB)

</div>

---

## 🛠 Tech Stack

<div align="center">

**Bot and backend**<br>
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.17-26A5E4?logo=telegram&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-async-D71F00?logo=sqlalchemy&logoColor=white)

**AI and NLP**<br>
![OpenAI](https://img.shields.io/badge/OpenAI-post%20generation-412991?logo=openai&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy-uk__core__news__sm-09A3D5?logo=spacy&logoColor=white)

**Storage and documents**<br>
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![python-docx](https://img.shields.io/badge/python--docx-DOCX%20output-2B579A?logo=microsoftword&logoColor=white)

</div>

---

## 🎯 What problem it solves

Running a council meeting on paper means one person tracking who is present, who voted how on
each item, and then rewriting all of it into a protocol that has to follow a fixed format.
The bot does the tracking during the meeting and emits the finished documents at the end.

---

## 🎬 Demo

The whole flow runs locally without Telegram, a database or an API key:

```bash
python demo.py
```

```
==============================================================================
1. The admin creates a session
==============================================================================
   Session code: 228782
   Password:     ofwwcgun
   These are shared with the council members, who join from their own Telegram.

==============================================================================
2. Members join
==============================================================================
   joined: Коваль О. І.
   joined: Мельник Д. С.
   joined: Ткаченко І. П.
   joined: Бондар Л. В.
   joined: Шевчук Н. О.
   5 participants registered for the attendance appendix.

==============================================================================
3. Voting, one agenda item at a time
==============================================================================
   Item 1: Про затвердження програми розвитку молоді
      for 5 · against 0 · abstained 0 · did not vote 0
   Item 2: Про створення робочої групи
      for 4 · against 1 · abstained 0 · did not vote 0
   Item 3: Про припинення повноважень члена ради
      for 3 · against 0 · abstained 2 · did not vote 0

==============================================================================
4. The protocol is written in the wording the paperwork requires
==============================================================================
   Agenda item (as submitted)                      Protocol wording (decision)
   ---------------------------------------------------------------------------
   Про затвердження програми розвитку молоді       затвердити програми розвитку молоді
   Про створення робочої групи                     створити робочої групи
   Про припинення повноважень члена ради           припинити повноважень члена ради
```

---

## ✨ Features

### 🗳 Session-based voting

- Admin creates a session; the bot generates a **join code** and a **password**
- Members enter both in their own Telegram and register under their name
- Voting runs **item by item** — the next question opens only when the current one closes
- Each member votes *for*, *against* or *abstains*; the bot records who has already voted
- The admin can close a vote early and see the running tallies

### 📄 Document generation

- **Протокол №N** — decisions and vote tallies for every agenda item, in the required layout
  (Times New Roman 14, fixed margins, numbered items, "Ухвалили" sections)
- **Додаток присутності** — the attendance appendix as a signable table
- Both are sent straight into the chat as DOCX files when the session ends

### 🔤 Ukrainian NLP for the protocol wording

- Agenda items arrive as nominalisations: *"Про затвердження програми"*
- A protocol has to state the decision as a verb: *"затвердити програму"*
- spaCy's `uk_core_news_sm` finds the nominalisation and the bot rewrites it
- Participant names are stored in the genitive case so they read correctly in the document

### 🤖 AI post generation

- Given the details of an event, an OpenAI-backed prompt writes a social media post
- The prompt encodes the council's established style: official tone, up to 700 characters,
  at most three emoji, no hashtags

### 🗄 Council profile and history

- Council name, city, region, chair and secretary are stored once and reused in every protocol
- Sessions are numbered, so protocol numbering continues across meetings

### ⚙️ Runs on either database

- The same async SQLAlchemy layer works on SQLite locally and PostgreSQL via asyncpg in production
- Selected by a single environment variable

---

## 🚀 Quick Start

### Requirements

- Python 3.12+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- An OpenAI API key — only needed for the post-generation feature

### Run

```bash
git clone https://github.com/sergiyclas/youth-council-bot.git
cd youth-council-bot
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in the tokens
python app.py
```

The Ukrainian spaCy model is installed from the wheel pinned in `requirements.txt`.
The app runs the bot and a small Flask service side by side.

---

## 🏗 Architecture

```mermaid
flowchart LR
    A([Admin]) -->|create session, set agenda| B[aiogram bot]
    P([Members]) -->|code and password, vote| B
    B --> FSM[FSM conversation state]
    B --> DB[(SQLite / PostgreSQL)]
    B --> NLP[spaCy uk_core_news_sm]
    B --> AI[OpenAI post generation]
    DB --> DOC[python-docx]
    NLP --> DOC
    DOC -->|protocol and attendance| A
```

**Project layout**

```
bot/
├── handlers/     admin, participant and shared conversation flows
├── keyboards/    inline and reply keyboards per role
├── database/     async SQLAlchemy models, SQLite and PostgreSQL backends
├── middlewares/  database session injection
├── filters/      role-based access checks
└── common/       document generation, OpenAI prompts, Ukrainian NLP
app.py            bot and Flask service entry point
demo.py           full session flow, no tokens required
```

---

## ⚙️ Configuration

| Variable | Description |
|:---|:---|
| `TELEGRAM_TOKEN` | Production bot token |
| `TELEGRAM_TOKEN_TEST` | Token used when `OPTION=test` |
| `API_ID` / `API_HASH` | Telegram API credentials |
| `OPENAI` | OpenAI API key for post generation |
| `DATABASE_URL` | Async database URL |
| `POSTGRESQL` | `true` for PostgreSQL, otherwise SQLite |
| `ALLOWED_ADMINS` | Comma-separated Telegram user ids allowed to run admin commands |
| `GOOGLE_DOCX_URL` | Protocol template document |
| `OPTION` | `test` or `production` |

---

## 📬 Contact

**Serhiy Dzen** – AI Software Engineer

[![Email](https://img.shields.io/badge/Email-sergiyclas@gmail.com-EA4335?logo=gmail&logoColor=white)](mailto:sergiyclas@gmail.com)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-in/sergiyclas-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/sergiyclas/)
[![GitHub](https://img.shields.io/badge/GitHub-sergiyclas-181717?logo=github&logoColor=white)](https://github.com/sergiyclas)

---

<div align="center">

Licensed under the [MIT License](LICENSE)

</div>
