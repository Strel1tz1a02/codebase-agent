const state = {
  projects: [],
  project: null,
  sessionId: "",
  runId: "",
};

const el = {
  apiStatus: document.getElementById("apiStatus"),
  projectStatus: document.getElementById("projectStatus"),
  indexStatus: document.getElementById("indexStatus"),
  projectForm: document.getElementById("projectForm"),
  projectName: document.getElementById("projectName"),
  repoPath: document.getElementById("repoPath"),
  projectList: document.getElementById("projectList"),
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
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || response.statusText);
  }
  return data;
}

function renderProjects() {
  el.projectList.innerHTML = "";
  for (const project of state.projects) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "project-item";
    button.innerHTML = `<strong>${escapeHtml(project.name)}</strong><span>${escapeHtml(project.index_status)} · ${escapeHtml(project.repo_path)}</span>`;
    button.addEventListener("click", () => selectProject(project));
    el.projectList.appendChild(button);
  }
}

function renderDetails() {
  const project = state.project;
  el.projectStatus.textContent = project ? project.name : "未选择项目";
  el.indexStatus.textContent = project ? project.index_status : "not_indexed";
  el.detailProject.textContent = project ? project.name : "-";
  el.detailProjectId.textContent = project ? project.project_id : "-";
  el.detailRepo.textContent = project ? project.repo_path : "-";
  el.detailSession.textContent = state.sessionId || "-";
  el.detailRun.textContent = state.runId || "-";
  el.indexButton.disabled = !project;
  el.askForm.querySelector("button").disabled = !project;
}

async function selectProject(project) {
  state.project = project;
  state.sessionId = "";
  state.runId = "";
  el.events.innerHTML = "";
  resetConversation();
  renderDetails();
  const session = await request(`/projects/${project.project_id}/sessions`, {
    method: "POST",
    body: "{}",
  });
  state.sessionId = session.session_id;
  renderDetails();
}

function resetConversation() {
  el.conversation.innerHTML = `
    <div class="empty-state">
      <h2>${state.project ? escapeHtml(state.project.name) : "选择或创建一个项目"}</h2>
      <p>先为仓库建立索引，然后询问代码库问题。</p>
    </div>
  `;
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
});

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
  if (!state.project || !state.sessionId) return;
  const question = el.question.value.trim();
  if (!question) return;
  appendMessage("user", question);
  el.question.value = "";
  try {
    const run = await request(`/projects/${state.project.project_id}/sessions/${state.sessionId}/runs`, {
      method: "POST",
      body: JSON.stringify({ question }),
    });
    state.runId = run.run_id;
    appendMessage("assistant", run.answer || run.reason || run.status);
    renderDetails();
    const eventList = await request(`/projects/${state.project.project_id}/sessions/${state.sessionId}/runs/${run.run_id}/events`);
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
resetConversation();
checkHealth();
