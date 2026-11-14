# AnalyticsHub

Exam practice for the oral exam in Data Analytics in Accounting. Students practise the same
kind of exam they will sit: a timed data manipulation exam (Excel and SQL) and a timed data
interpretation exam (regression).

## What is in the site

- **Manipulation exams**: 60 exams, each with three Excel questions on one data file and two
  SQL questions on one database, with an eight-minute timer.
- **Question bank**: all 226 Excel and SQL questions, filterable by subject, data file and skill.
- **Interpretation exams**: 12 regression exams of four questions, fitted on the restaurant case.

Every exam and question has its own address (for example `#/exams/E017`), so it can be shared.

## Where the questions come from

All questions are written from the course cases, and every answer is computed from the course
data files by `scripts/build_question_bank.py`. SQL answers are the real output of the model
query; Excel answers are calculated from the same files students download; regression exams are
real regressions on the restaurant data. Nothing is typed in by hand.

```
python scripts/build_question_bank.py "<path to materials folder>"   # rebuilds src/data/*.json
python scripts/copy_datasets.py "<path to materials folder>"         # fills public/datasets
```

The builder needs Python with pandas, numpy, scipy and openpyxl.

## Run it locally

```
npm install
npm run dev
```

## Skill coverage (the added functionality)

Every question trains one of 23 skills (9 Excel, 8 SQL, 6 regression). After revealing an answer,
the student compares it with their own result and rates it: got it, partly, or missed it. The
**Skill coverage** page turns those ratings into a map of which skills are secure, started, need
work, or have never been practised, and **Build an exam from my gaps** composes an exam in the real
format (three Excel questions on one file, two SQL questions on one database) from the skills the
student has not secured.

Coverage is stored only in the student's browser (`localStorage`). There are no accounts and nothing
is sent to a server. The logic is in `src/lib/progress.js`.

Why it matters, measured on this site's own 60 exams (20,000 simulated students each):

| Practice | Manipulation skills seen (of 17) |
|---|---|
| 5 randomly chosen exams | 11.8 on average; 97% of students miss three or more |
| 10 randomly chosen exams | 14.4 on average; 51% still miss three or more |
| 4 exams built from gaps | all 17 |

## AI help

Each question has a "Get a hint from AI" panel. The student shows an attempt and gets the next
step, not the solution. The browser calls `/api/help` on our own Cloudflare Worker
(`worker/index.js`); the Worker looks the question up in the bank, adds its checked answer and the
real column names as private context, and calls the Gemini API. The API key exists only on the
server as the secret `GEMINI_API_KEY` and is never sent to the browser or stored in this repository.

To try it locally, copy `.dev.vars.example` to `.dev.vars`, add the key, then:

```
npm run dev:full      # builds the site and serves it with the Worker on http://localhost:8787
```

`npm run dev` still works for everything except AI help.

## Deploy

```
npm run deploy        # builds and publishes to Cloudflare Workers
```

The Gemini model is set in `wrangler.jsonc` (`GEMINI_MODEL`).

## The two large databases

`movies.db` (69 MB) and `pcards.db` (94 MB) are not in the repository. Locally, copy them into
`public/datasets`. On the hosted site they are served from a GitHub release; its address is set in
`src/config.js`.

## Project layout

- `src/data/` generated question bank (skills, datasets, questions, regression exams)
- `src/lib/` data loading, exam composition, routing, skill coverage
- `src/components/` timer, question view, AI help, data file links
- `src/pages/` the five pages
- `worker/` Cloudflare Worker: serves the site and the AI help endpoint
- `scripts/` question bank builder and dataset copier
