# Frontend Development Rules (Vue 3 & Vite)

## 🎨 UI/UX Standards
- **Componentry**: Use **Element Plus** for all UI elements (Tables, Forms, Dialogs).
- **API Calls**: All requests must go through `frontend/src/api/` using the Axios instance.

## 🏗 Composition API
- Use `<script setup>` syntax for all Vue components.
- Maintain clear separation between business logic in `views/` and data fetching in `api/`.