const state = {
  projects: [],
  sessionsByProject: {},
  runsBySession: {},
  project: null,
  sessionId: "",
  sessionDraft: false,
  runId: "",
};

const SIDEBAR_WIDTH_KEY = "codebase-agent.sidebarWidth";
const SIDEBAR_WIDTH_MIN = 320;
const SIDEBAR_WIDTH_MAX = 640;

const el = {
  apiStatus: document.getElementById("apiStatus"),
  projectStatus: document.getElementById("projectStatus"),
  sessionStatus: document.getElementById("sessionStatus"),
  indexStatus: document.getElementById("indexStatus"),
  projectForm: document.getElementById("projectForm"),
  projectName: document.getElementById("projectName"),
  repoPath: document.getElementById("repoPath"),
  projectList: document.getElementById("projectList"),
  sessionList: document.getElementById("sessionList"),
  newSessionButton: document.getElementById("newSessionButton"),
  indexButton: document.getElementById("indexButton"),
  askForm: document.getElementById("askForm"),
  question: document.getElementById("question"),
  conversation: document.getElementById("conversation"),
  detailProject: document.getElementById("detailProject"),
  detailProjectId: document.getElementById("detailProjectId"),
  detailRepo: document.getElementById("detailRepo"),
  detailSession: document.getElementById("detailSession"),
  detailRun: document.getElementById("detailRun"),
  events: document.getElementById("events"),
  sidebarResizer: document.getElementById("sidebarResizer"),
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!response.ok) {
    throw new Error(data.detail || response.statusText);
  }
  return data;
}

function renderProjects() {
  el.projectList.innerHTML = "";
  if (state.projects.length === 0) {
    renderEmpty(el.projectList, "暂无项目");
    return;
  }
  for (const project of state.projects) {
    const item = document.createElement("div");
    item.className = "project-item";
    if (state.project && state.project.project_id === project.project_id) {
      item.classList.add("active");
    }

    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.className = "project-select";
    selectButton.innerHTML = `
      <strong>${escapeHtml(project.name)}</strong>
      <span>${escapeHtml(project.index_status)} · ${escapeHtml(project.repo_path)}</span>
    `;
    selectButton.addEventListener("click", () => selectProject(project));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "project-delete";
    deleteButton.title = "删除项目";
    deleteButton.setAttribute("aria-label", `删除项目 ${project.name}`);
    deleteButton.textContent = "×";
    deleteButton.addEventListener("click", () => deleteProject(project));

    item.appendChild(selectButton);
    item.appendChild(deleteButton);
    el.projectList.appendChild(item);
  }
}

function renderSessions(projectId = state.project?.project_id || "") {
  el.sessionList.innerHTML = "";
  if (!projectId) {
    renderEmpty(el.sessionList, "先选择项目");
    return;
  }
  const sessions = state.sessionsByProject[projectId] || [];
  if (sessions.length === 0) {
    renderEmpty(el.sessionList, "暂无会话");
    return;
  }
  for (const session of sessions) {
    const item = document.createElement("div");
    item.className = "session-row";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "session-item";
    if (state.sessionId === session.session_id) {
      button.classList.add("active");
    }
    button.innerHTML = `
      <strong>${escapeHtml(sessionTitle(projectId, session.session_id))}</strong>
      <span>${escapeHtml(session.session_id.slice(0, 8))}</span>
    `;
    button.addEventListener("click", () => selectSession(projectId, session.session_id));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "session-delete";
    deleteButton.title = "删除会话";
    deleteButton.setAttribute("aria-label", `删除会话 ${session.session_id}`);
    deleteButton.textContent = "×";
    deleteButton.addEventListener("click", () => deleteSession(projectId, session));

    item.appendChild(button);
    item.appendChild(deleteButton);
    el.sessionList.appendChild(item);
  }
}

function renderDetails() {
  const project = state.project;
  el.projectStatus.textContent = project ? project.name : "未选择项目";
  el.sessionStatus.textContent = state.sessionId ? `会话 ${state.sessionId.slice(0, 8)}` : "选择或创建会话";
  if (state.sessionDraft) {
    el.sessionStatus.textContent = "新会话草稿";
  }
  el.indexStatus.textContent = project ? project.index_status : "not_indexed";
  el.detailProject.textContent = project ? project.name : "-";
  el.detailProjectId.textContent = project ? project.project_id : "-";
  el.detailRepo.textContent = project ? project.repo_path : "-";
  el.detailSession.textContent = state.sessionId || "-";
  el.detailRun.textContent = state.runId || "-";
  el.indexButton.disabled = !project;
  el.newSessionButton.disabled = !project;
  el.askForm.querySelector("button").disabled = !project || (!state.sessionId && !state.sessionDraft);
  el.question.disabled = !project || (!state.sessionId && !state.sessionDraft);
}

async function selectProject(project) {
  state.project = project;
  state.sessionId = "";
  state.sessionDraft = false;
  state.runId = "";
  el.events.innerHTML = "";
  renderProjects();
  renderSessions(project.project_id);
  resetConversation();
  renderDetails();
  await loadSessions(project.project_id);
}

async function loadProjects() {
  try {
    const payload = await request("/projects");
    state.projects = payload.projects || [];
    renderProjects();
  } catch (error) {
    el.projectList.innerHTML = "";
    renderEmpty(el.projectList, error.message, true);
  }
}

async function loadSessions(projectId) {
  try {
    const payload = await request(`/projects/${projectId}/sessions`);
    state.sessionsByProject[projectId] = payload.sessions || [];
    renderSessions(projectId);
  } catch (error) {
    el.sessionList.innerHTML = "";
    renderEmpty(el.sessionList, error.message, true);
  }
}

function startDraftSession() {
  if (!state.project) return;
  state.sessionId = "";
  state.sessionDraft = true;
  state.runId = "";
  el.events.innerHTML = "";
  renderSessions(state.project.project_id);
  resetConversation();
  renderDetails();
}

async function ensureSessionForQuestion() {
  if (!state.project) return "";
  if (state.sessionId) return state.sessionId;
  if (!state.sessionDraft) return "";
  try {
    const session = await request(`/projects/${state.project.project_id}/sessions`, {
      method: "POST",
      body: "{}",
    });
    const sessions = state.sessionsByProject[state.project.project_id] || [];
    state.sessionsByProject[state.project.project_id] = [session, ...sessions];
    state.sessionId = session.session_id;
    state.sessionDraft = false;
    state.runsBySession[session.session_id] = [];
    renderSessions(state.project.project_id);
    renderDetails();
    return session.session_id;
  } catch (error) {
    appendMessage("system", error.message, "error");
    return "";
  }
}

async function selectSession(projectId, sessionId) {
  state.sessionId = sessionId;
  state.sessionDraft = false;
  state.runId = "";
  el.events.innerHTML = "";
  renderSessions(projectId);
  renderDetails();
  await loadRuns(projectId, sessionId);
}

async function deleteSession(projectId, session) {
  try {
    await request(`/projects/${projectId}/sessions/${session.session_id}`, { method: "DELETE" });
    state.sessionsByProject[projectId] = (state.sessionsByProject[projectId] || []).filter(
      (item) => item.session_id !== session.session_id,
    );
    delete state.runsBySession[session.session_id];
    if (state.sessionId === session.session_id) {
      state.sessionId = "";
      state.sessionDraft = false;
      state.runId = "";
      el.events.innerHTML = "";
      resetConversation();
      renderDetails();
    }
    renderSessions(projectId);
  } catch (error) {
    appendMessage("system", error.message, "error");
  }
}

async function loadRuns(projectId, sessionId) {
  try {
    const payload = await request(`/projects/${projectId}/sessions/${sessionId}/runs`);
    state.runsBySession[sessionId] = payload.runs || [];
    renderConversationFromRuns(state.runsBySession[sessionId]);
  } catch (error) {
    resetConversation();
    appendMessage("system", error.message, "error");
  }
}

async function deleteProject(project) {
  try {
    await request(`/projects/${project.project_id}`, { method: "DELETE" });
    state.projects = state.projects.filter((item) => item.project_id !== project.project_id);
    delete state.sessionsByProject[project.project_id];
    if (state.project && state.project.project_id === project.project_id) {
      state.project = null;
      state.sessionId = "";
      state.sessionDraft = false;
      state.runId = "";
      el.events.innerHTML = "";
      resetConversation();
      renderSessions("");
      renderDetails();
    }
    renderProjects();
  } catch (error) {
    appendMessage("system", error.message, "error");
  }
}

function resetConversation() {
  el.conversation.innerHTML = `
    <div class="empty-state">
      <h2>${state.project ? escapeHtml(state.project.name) : "选择一个项目"}</h2>
      <p>${state.sessionId || state.sessionDraft ? "开始询问这个代码库。" : "选择已有会话，或创建一个新会话。"}</p>
    </div>
  `;
}

function renderConversationFromRuns(runs) {
  el.conversation.innerHTML = "";
  if (!runs.length) {
    resetConversation();
    return;
  }
  for (const run of runs) {
    appendMessage("user", run.question);
    appendMessage("assistant", run.answer || run.reason || run.status);
  }
  state.runId = runs[runs.length - 1].run_id;
  renderDetails();
}

function appendMessage(role, content, cssClass = "") {
  const empty = el.conversation.querySelector(".empty-state");
  if (empty) empty.remove();
  const item = document.createElement("div");
  item.className = `message ${role} ${cssClass}`.trim();
  item.innerHTML = `<div class="meta">${escapeHtml(displayRole(role))}</div>${escapeHtml(content)}`;
  el.conversation.appendChild(item);
  el.conversation.scrollTop = el.conversation.scrollHeight;
}

function renderEvents(events) {
  el.events.innerHTML = "";
  for (const event of events) {
    const item = document.createElement("div");
    item.className = "event";
    item.textContent = `${event.event_type} ${JSON.stringify(event.payload)}`;
    el.events.appendChild(item);
  }
}

async function checkHealth() {
  try {
    const health = await request("/health");
    el.apiStatus.textContent = `API ${health.status}`;
  } catch (error) {
    el.apiStatus.textContent = `API 不可用：${error.message}`;
  }
}

function sessionTitle(projectId, sessionId) {
  const runs = state.runsBySession[sessionId] || [];
  const firstQuestion = runs.find((run) => run.question)?.question;
  if (firstQuestion) return firstQuestion;
  const sessions = state.sessionsByProject[projectId] || [];
  const index = sessions.findIndex((session) => session.session_id === sessionId);
  return `会话 ${index >= 0 ? index + 1 : sessionId.slice(0, 8)}`;
}

function renderEmpty(container, text, isError = false) {
  const empty = document.createElement("div");
  empty.className = `list-empty ${isError ? "error" : ""}`.trim();
  empty.textContent = text;
  container.appendChild(empty);
}

function initSidebarResize() {
  if (!el.sidebarResizer) return;
  const savedWidth = Number(localStorage.getItem(SIDEBAR_WIDTH_KEY));
  if (Number.isFinite(savedWidth)) {
    setSidebarWidth(savedWidth);
  }

  let dragging = false;
  el.sidebarResizer.addEventListener("pointerdown", (event) => {
    dragging = true;
    el.sidebarResizer.classList.add("dragging");
    el.sidebarResizer.setPointerCapture(event.pointerId);
  });

  el.sidebarResizer.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    setSidebarWidth(event.clientX);
  });

  el.sidebarResizer.addEventListener("pointerup", (event) => {
    if (!dragging) return;
    dragging = false;
    el.sidebarResizer.classList.remove("dragging");
    el.sidebarResizer.releasePointerCapture(event.pointerId);
    localStorage.setItem(SIDEBAR_WIDTH_KEY, String(readSidebarWidth()));
  });

  el.sidebarResizer.addEventListener("pointercancel", () => {
    dragging = false;
    el.sidebarResizer.classList.remove("dragging");
  });
}

function setSidebarWidth(width) {
  const clamped = Math.max(SIDEBAR_WIDTH_MIN, Math.min(SIDEBAR_WIDTH_MAX, Number(width)));
  document.documentElement.style.setProperty("--sidebar-width", `${clamped}px`);
}

function readSidebarWidth() {
  const value = getComputedStyle(document.documentElement).getPropertyValue("--sidebar-width");
  return Number.parseInt(value, 10) || SIDEBAR_WIDTH_MIN;
}

el.projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const project = await request("/projects", {
    method: "POST",
    body: JSON.stringify({
      name: el.projectName.value.trim(),
      repo_path: el.repoPath.value.trim(),
    }),
  });
  state.projects.unshift(project);
  renderProjects();
  await selectProject(project);
  startDraftSession();
});

el.newSessionButton.addEventListener("click", startDraftSession);

el.indexButton.addEventListener("click", async () => {
  if (!state.project) return;
  el.indexButton.disabled = true;
  el.indexStatus.textContent = "indexing";
  try {
    const project = await request(`/projects/${state.project.project_id}/index`, { method: "POST" });
    state.project = project;
    const index = state.projects.findIndex((item) => item.project_id === project.project_id);
    if (index >= 0) state.projects[index] = project;
    renderProjects();
    renderDetails();
  } catch (error) {
    appendMessage("system", error.message, "error");
  } finally {
    el.indexButton.disabled = false;
  }
});

el.askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.project || (!state.sessionId && !state.sessionDraft)) return;
  const question = el.question.value.trim();
  if (!question) return;
  appendMessage("user", question);
  el.question.value = "";
  try {
    const sessionId = await ensureSessionForQuestion();
    if (!sessionId) return;
    const run = await request(`/projects/${state.project.project_id}/sessions/${sessionId}/runs`, {
      method: "POST",
      body: JSON.stringify({ question }),
    });
    state.runId = run.run_id;
    state.runsBySession[sessionId] = [...(state.runsBySession[sessionId] || []), run];
    appendMessage("assistant", run.answer || run.reason || run.status);
    renderSessions(state.project.project_id);
    renderDetails();
    const eventList = await request(`/projects/${state.project.project_id}/sessions/${sessionId}/runs/${run.run_id}/events`);
    renderEvents(eventList.events || []);
  } catch (error) {
    appendMessage("system", error.message, "error");
  }
});

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function displayRole(role) {
  return {
    user: "用户",
    assistant: "助手",
    system: "系统",
  }[role] || role;
}

renderDetails();
renderSessions("");
resetConversation();
initSidebarResize();
checkHealth();
loadProjects();
