(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const TOKEN_KEY = "taskboard:token";
  const state = { token: localStorage.getItem(TOKEN_KEY), user: null, boards: [], boardId: null, tasks: [], editing: null, newStatus: "todo" };

  // api ----------------------------------------------------------------
  async function api(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (state.token) headers.Authorization = "Bearer " + state.token;
    const res = await fetch("/api" + path, { ...options, headers, body: options.body ? JSON.stringify(options.body) : undefined });
    if (res.status === 401 && state.token) { signOut(); throw new Error("Session expired, please sign in again"); }
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join(", ") : data.detail;
      throw new Error(detail || "Request failed");
    }
    return data;
  }

  let toastTimer;
  function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 2200); }

  // auth ---------------------------------------------------------------
  let mode = "login";
  $(".tabs").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    mode = b.dataset.mode;
    document.querySelectorAll(".tabs button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    $("#auth-submit").textContent = mode === "login" ? "Sign in" : "Create account";
    $("#auth-error").textContent = "";
  });
  $("#auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    if (!form.checkValidity()) { $("#auth-error").textContent = "Enter a valid email and a password of 8+ characters."; return; }
    const body = { email: form.email.value.trim(), password: form.password.value };
    try {
      if (mode === "register") await api("/auth/register", { method: "POST", body });
      const token = await api("/auth/login", { method: "POST", body });
      state.token = token.access_token; localStorage.setItem(TOKEN_KEY, state.token);
      form.reset();
      await boot();
    } catch (err) { $("#auth-error").textContent = err.message; }
  });
  function signOut() { state.token = null; state.user = null; localStorage.removeItem(TOKEN_KEY); $("#app").hidden = true; $("#auth").hidden = false; }
  $("#logout").addEventListener("click", signOut);

  // boards -------------------------------------------------------------
  async function loadBoards(selectId) {
    state.boards = await api("/boards");
    if (selectId != null) state.boardId = selectId;
    if (!state.boards.some((b) => b.id === state.boardId)) state.boardId = state.boards[0]?.id ?? null;
    renderBoards();
    if (state.boardId != null) await loadTasks(); else renderNoBoards();
  }
  function renderBoards() {
    $("#boards").innerHTML = state.boards.map((b) => `<li><button class="${b.id === state.boardId ? "active" : ""}" data-board="${b.id}"><span>${esc(b.name)}</span><small>${b.task_count}</small></button></li>`).join("");
  }
  $("#boards").addEventListener("click", async (e) => { const b = e.target.closest("button[data-board]"); if (!b) return; state.boardId = Number(b.dataset.board); renderBoards(); await loadTasks(); });
  const boardDialog = $("#board-dialog"), boardForm = $("#board-form");
  function createBoard() { boardForm.reset(); boardDialog.showModal(); boardForm.name.focus(); }
  $("#board-cancel").addEventListener("click", () => boardDialog.close());
  boardForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = boardForm.name.value.trim();
    if (!name) { boardForm.name.focus(); return; }
    try {
      const board = await api("/boards", { method: "POST", body: { name } });
      boardDialog.close(); await loadBoards(board.id); toast("Board created");
    } catch (err) { toast(err.message); }
  });
  $("#new-board").addEventListener("click", createBoard);
  $("#first-board").addEventListener("click", createBoard);
  $("#rename-board").addEventListener("click", () => { const h = $("#board-name"); h.contentEditable = "true"; h.focus(); document.getSelection().selectAllChildren(h); });
  $("#board-name").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); e.target.blur(); } if (e.key === "Escape") { e.target.textContent = currentBoard().name; e.target.blur(); } });
  $("#board-name").addEventListener("blur", async (e) => {
    const h = e.target; if (h.contentEditable !== "true") return;
    h.contentEditable = "false";
    const name = h.textContent.trim();
    if (!name || name === currentBoard().name) { h.textContent = currentBoard().name; return; }
    await api(`/boards/${state.boardId}`, { method: "PATCH", body: { name } });
    await loadBoards();
  });
  $("#delete-board").addEventListener("click", async () => {
    const board = currentBoard();
    if (!confirm(`Delete "${board.name}" and all its tasks?`)) return;
    await api(`/boards/${board.id}`, { method: "DELETE" });
    await loadBoards(); toast("Board deleted");
  });
  const currentBoard = () => state.boards.find((b) => b.id === state.boardId);
  function renderNoBarsVisibility(hasBoards) { $("#columns").hidden = !hasBoards; $(".board-head").hidden = !hasBoards; $("#no-boards").hidden = hasBoards; }
  function renderNoBoards() { renderNoBarsVisibility(false); }

  // tasks --------------------------------------------------------------
  async function loadTasks() {
    renderNoBarsVisibility(true);
    $("#board-name").textContent = currentBoard().name;
    state.tasks = await api(`/boards/${state.boardId}/tasks`);
    renderTasks();
  }
  function dueBadge(t) {
    if (!t.due_date) return "";
    const due = new Date(t.due_date + "T00:00"); const today = new Date(); today.setHours(0, 0, 0, 0);
    const days = Math.round((due - today) / 86400000);
    const cls = t.status !== "done" && days < 0 ? "overdue" : t.status !== "done" && days <= 2 ? "soon" : "";
    return `<span class="pill ${cls}">📅 ${due.toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</span>`;
  }
  function renderTasks() {
    for (const status of ["todo", "doing", "done"]) {
      const tasks = state.tasks.filter((t) => t.status === status).sort((a, b) => a.position - b.position);
      $(`.tasks[data-status="${status}"]`).innerHTML = tasks.map((t) => `
        <article class="task ${t.priority} ${t.status}" draggable="true" data-id="${t.id}">
          <div class="title">${esc(t.title)}</div>
          ${t.description ? `<div class="desc">${esc(t.description)}</div>` : ""}
          <div class="meta"><span class="pill">${t.priority}</span>${dueBadge(t)}</div>
        </article>`).join("");
      $(`.column[data-status="${status}"] .count`).textContent = tasks.length;
    }
    const board = currentBoard(); if (board) { board.task_count = state.tasks.length; renderBoards(); }
  }

  // dialog -------------------------------------------------------------
  const dialog = $("#task-dialog"), form = $("#task-form");
  function openDialog(task, status) {
    state.editing = task || null; state.newStatus = status || "todo";
    $("#task-dialog-title").textContent = task ? "Edit task" : "New task";
    form.title.value = task?.title || ""; form.description.value = task?.description || "";
    form.priority.value = task?.priority || "medium"; form.due_date.value = task?.due_date || "";
    $("#task-delete").hidden = !task;
    dialog.showModal(); form.title.focus();
  }
  $("#columns").addEventListener("click", (e) => {
    const add = e.target.closest(".add-task"); if (add) return openDialog(null, add.dataset.status);
    const card = e.target.closest(".task"); if (card) openDialog(state.tasks.find((t) => t.id === Number(card.dataset.id)));
  });
  $("#task-cancel").addEventListener("click", () => dialog.close());
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!form.title.value.trim()) { form.title.focus(); return; }
    const body = { title: form.title.value.trim(), description: form.description.value, priority: form.priority.value };
    try {
      if (state.editing) {
        if (form.due_date.value) body.due_date = form.due_date.value; else body.clear_due_date = true;
        await api(`/tasks/${state.editing.id}`, { method: "PATCH", body });
      } else {
        body.status = state.newStatus; if (form.due_date.value) body.due_date = form.due_date.value;
        await api(`/boards/${state.boardId}/tasks`, { method: "POST", body });
      }
      dialog.close(); await loadTasks();
    } catch (err) { toast(err.message); }
  });
  $("#task-delete").addEventListener("click", async () => {
    await api(`/tasks/${state.editing.id}`, { method: "DELETE" });
    dialog.close(); await loadTasks(); toast("Task deleted");
  });

  // drag and drop ------------------------------------------------------
  let dragId = null;
  $("#columns").addEventListener("dragstart", (e) => { const card = e.target.closest(".task"); if (!card) return; dragId = Number(card.dataset.id); card.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
  $("#columns").addEventListener("dragend", (e) => { e.target.closest(".task")?.classList.remove("dragging"); document.querySelectorAll(".tasks.over").forEach((el) => el.classList.remove("over")); });
  $("#columns").addEventListener("dragover", (e) => { const list = e.target.closest(".tasks"); if (!list) return; e.preventDefault(); e.dataTransfer.dropEffect = "move"; list.classList.add("over"); });
  $("#columns").addEventListener("dragleave", (e) => { const list = e.target.closest(".tasks"); if (list && !list.contains(e.relatedTarget)) list.classList.remove("over"); });
  $("#columns").addEventListener("drop", async (e) => {
    const list = e.target.closest(".tasks"); if (!list || dragId == null) return;
    e.preventDefault(); list.classList.remove("over");
    const cards = [...list.querySelectorAll(".task:not(.dragging)")];
    const index = cards.findIndex((c) => e.clientY < c.getBoundingClientRect().top + c.offsetHeight / 2);
    const position = index === -1 ? cards.length : index;
    const task = state.tasks.find((t) => t.id === dragId);
    // optimistic update
    state.tasks = state.tasks.filter((t) => t.id !== dragId);
    state.tasks.filter((t) => t.status === list.dataset.status && t.position >= position).forEach((t) => t.position++);
    state.tasks.push({ ...task, status: list.dataset.status, position });
    renderTasks();
    try { await api(`/tasks/${dragId}/move`, { method: "POST", body: { status: list.dataset.status, position } }); }
    catch (err) { toast(err.message); }
    await loadTasks();
    dragId = null;
  });

  // boot ---------------------------------------------------------------
  function esc(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]); }
  async function boot() {
    if (!state.token) { $("#auth").hidden = false; return; }
    try {
      state.user = await api("/auth/me");
      $("#user-email").textContent = state.user.email;
      $("#auth").hidden = true; $("#app").hidden = false;
      await loadBoards();
    } catch (err) { if (state.token) toast(err.message); $("#auth").hidden = false; }
  }
  boot();
})();
