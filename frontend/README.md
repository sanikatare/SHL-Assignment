# Talent Match — SHL Assessment Recommender (Frontend)

A production-ready chat UI for the SHL Assessment Recommendation Agent. Built
with **React + Vite + Tailwind CSS**. This is a frontend-only layer — it does
not modify or require changes to the existing FastAPI backend.

## Features

- ChatGPT/Notion-style chat interface with user + assistant bubbles
- Typewriter-style streaming animation for assistant replies
- Recommendation cards (grid on desktop, stacked on mobile) with test-type
  badges, relevance meter, and a link out to each SHL assessment
- Fixed, auto-resizing input bar — `Enter` to send, `Shift+Enter` for a newline
- Loading, empty, and error states, with a **Retry** button on failure
- Suggested prompts on first load
- Persistent chat history (localStorage) that survives a page refresh
- Clear conversation button
- Dark mode toggle (persisted, respects system preference on first visit)
- Copy-message button
- Toast notifications
- Live backend connection indicator (polls `GET /health`)
- Fully responsive, keyboard-accessible (visible focus rings), and respects
  `prefers-reduced-motion`

## Tech stack

- React 18 + Vite 6
- Tailwind CSS 3
- Axios for API calls
- lucide-react for icons
- framer-motion is installed and available, though the current animations are
  implemented with lightweight CSS/Tailwind keyframes to keep the bundle small

## Getting started

```bash
npm install
npm run dev
```

The app runs at `http://localhost:5173` and expects the FastAPI backend at
`http://localhost:8000` by default.

### Pointing at a different backend URL

Copy `.env.example` to `.env` and set:

```
VITE_API_BASE_URL=http://localhost:8000
```

### Production build

```bash
npm run build
npm run preview
```

## Backend contract (unchanged)

```
GET  /health
POST /chat
  Request:  { "messages": [{ "role": "user" | "assistant", "content": string }] }
  Response: { "reply": string, "recommendations": Recommendation[], "end_of_conversation": boolean }

Recommendation: { name: string, url: string, test_type: string, score?: number }
```

The frontend always sends the **full** message history on every request
(the backend agent is stateless), stripping any local-only fields (ids,
timestamps, recommendations) before the request goes out.

## Project structure

```
src/
  api/chatApi.js          # axios client + typed error handling for /health and /chat
  components/              # presentational components (chat, cards, sidebar, input, states)
  context/ToastContext.jsx # toast notification provider/hook
  hooks/                   # useChat, useLocalStorage, useDarkMode, useHealthCheck, useTypewriter
  App.jsx
  main.jsx
  index.css
```

## Design notes

The visual language is built around the idea of a "match report": each
recommendation renders as an index-card with a monospace rank tag, a
test-type badge, and an optional relevance meter. Palette is a cool paper
background with a deep evergreen primary (evaluation / verified) and a warm
amber accent for scoring — paired with Space Grotesk (display), Inter
(body), and JetBrains Mono (data/labels).
