#!/usr/bin/env python3
"""Storyboard Studio V1 — Web UI mínima para probar bienvenida y script."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.project import StoryboardProject, CharacterAsset, LocationAsset, PropAsset, Shot, ShotStatus
from schemas.validator import save_project, validate_dict
from pipeline.script_parser import parse_script, rebuild_markdown

app = Flask(__name__)
app.config["SECRET_KEY"] = "storyboard-studio-v1"

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route("/static/asset_images/<asset_id>.png")
def serve_asset_image(asset_id: str):
    from flask import send_from_directory
    return send_from_directory(str(OUTPUT_DIR / "_asset_images"), f"{asset_id}.png")

STYLES = [
    "Realistic",
    "Anime",
    "Watercolor",
    "Cinematic Noir",
    "Pixar-style 3D",
    "Comic Book",
    "Studio Ghibli",
]

WELCOME_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Story Studio — Bienvenida</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d1117;
    color: #c9d1d9;
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .modal {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 48px;
    width: 520px;
    max-width: 95vw;
    text-align: center;
  }
  .modal h1 { font-size: 22px; margin-bottom: 8px; }
  .modal .subtitle { color: #8b949e; margin-bottom: 24px; }
  label { display: block; text-align: left; color: #8b949e; font-size: 12px; margin-bottom: 6px; }
  select, input[type="text"] {
    width: 100%;
    background: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 16px;
    font-size: 14px;
  }
  button[type="submit"] {
    width: 100%;
    background: #1f6feb;
    color: #fff;
    border: none;
    border-radius: 999px;
    padding: 12px;
    font-size: 14px;
    cursor: pointer;
  }
  .err { color: #ff7b72; margin-top: 12px; font-size: 13px; }
</style>
</head>
<body>
  <form class="modal" method="post" action="/">
    <h1>Welcome to Story Studio</h1>
    <p class="subtitle">Elegí el estilo visual de tu proyecto</p>

    <label for="style">Storyboard style</label>
    <select id="style" name="style">
      {% for s in styles %}
      <option value="{{ s }}" {% if s=='Realistic' %}selected{% endif %}>{{ s }}</option>
      {% endfor %}
    </select>

    <label for="title">Project title</label>
    <input id="title" name="title" type="text" value="Mi Proyecto" required>

    <button type="submit">Get Started</button>
    {% if error %}
      <div class="err">{{ error }}</div>
    {% endif %}
  </form>
</body>
</html>
"""

SCRIPT_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Story Studio — Script</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d1117;
    color: #c9d1d9;
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    border-bottom: 1px solid #21262d;
  }
  header h1 { font-size: 16px; color: #c9d1d9; }
  header .meta { color: #8b949e; font-size: 12px; }
  header .meta a { color: #58a6ff; text-decoration: none; margin: 0 6px; }
  .layout {
    display: grid;
    grid-template-columns: 280px 1fr;
    flex: 1;
    min-height: 0;
  }
  .sidebar {
    border-right: 1px solid #21262d;
    padding: 16px;
    overflow: auto;
  }
  .sidebar h2 {
    font-size: 12px;
    text-transform: uppercase;
    color: #8b949e;
    margin-bottom: 12px;
    letter-spacing: 2px;
  }
  .pill {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid #30363d;
    background: #0d1117;
    color: #c9d1d9;
    font-size: 12px;
    margin: 0 6px 8px 0;
    cursor: pointer;
  }
  .pill.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }
  .editor {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .toolbar {
    display: flex;
    gap: 8px;
    padding: 10px 16px;
    border-bottom: 1px solid #21262d;
  }
  .toolbar button {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 999px;
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
  }
  .toolbar .primary { background: #1f6feb; border-color: #1f6feb; color: #fff; }
  textarea#markdown {
    flex: 1;
    width: 100%;
    background: #0d1117;
    color: #c9d1d9;
    border: none;
    padding: 16px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    line-height: 1.55;
    resize: none;
    outline: none;
  }
  .status {
    padding: 10px 16px;
    border-top: 1px solid #21262d;
    color: #8b949e;
    font-size: 12px;
  }
  .status .ok { color: #3fb950; }
  .status .err { color: #ff7b72; }
</style>
</head>
<body>
  <header>
    <h1>{{ project.projectTitle }} <span style="color:#484f58">/ Script</span></h1>
    <div class="meta">
      <a href="/" style="color:#58a6ff;text-decoration:none;">New project</a>
      &nbsp;|&nbsp;
      <a href="/assets/{{ project_id }}" style="color:#58a6ff;text-decoration:none;">Assets →</a>
      &nbsp;|&nbsp;
      <a href="/storyboard/{{ project_id }}" style="color:#58a6ff;text-decoration:none;">Storyboard →</a>
    </div>
  </header>

  <div class="layout">
    <div class="sidebar">
      <h2>Style</h2>
      <div>
        <span class="pill active">{{ project.globalStyle }}</span>
      </div>

      <h2 style="margin-top:20px">Scenes</h2>
      <div id="scene-list">
        {% for s in scenes %}
          <div class="pill active">{{ s.slugline }}</div>
        {% else %}
          <div class="empty">No scenes yet.</div>
        {% endfor %}
      </div>

      <h2 style="margin-top:20px">Dialogues</h2>
      <div id="dialogue-list">
        {% for d in dialogues %}
          <div class="pill">{{ d.character }}</div>
        {% else %}
          <div class="empty">No dialogues yet.</div>
        {% endfor %}
      </div>
    </div>

    <div class="editor">
      <form class="toolbar" method="post" action="/script/{{ project_id }}/save" enctype="multipart/form-data">
        <button type="button" class="primary" onclick="document.getElementById('json-upload').click()">Load JSON</button>
        <input type="file" id="json-upload" name="project_json" accept=".json" style="display:none">
        <button type="submit">Save script</button>
      </form>

      <textarea id="markdown" name="markdown" spellcheck="false">{{ markdown }}</textarea>

      <div class="status">
        {% if saved %}
          <span class="ok">✅ Guardado: {{ saved }}</span>
        {% endif %}
        {% if error %}
          <span class="err">❌ {{ error }}</span>
        {% endif %}
        &nbsp;
        {{ scenes|length }} scenes · {{ dialogues|length }} dialogues
      </div>
    </div>
  </div>

  <script>
    document.getElementById('json-upload').addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const form = new FormData();
      form.append('project_json', file);
      const res = await fetch('/script/{{ project_id }}', {
        method: 'POST',
        body: form,
      });
      if (res.ok) {
        window.location.reload();
      } else {
        alert('Error loading JSON');
      }
    });
  </script>
</body>
</html>
"""

STORYBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Story Studio — Storyboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d1117;
    color: #c9d1d9;
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    border-bottom: 1px solid #21262d;
  }
  header h1 { font-size: 16px; color: #c9d1d9; }
  header .meta { color: #8b949e; font-size: 12px; }
  header .meta a { color: #58a6ff; text-decoration: none; margin: 0 6px; }
  .content { padding: 24px; overflow: auto; }
  .scene-block {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 20px;
  }
  .scene-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .scene-header h2 { font-size: 14px; }
  .shots {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
  }
  .shot-card {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 10px;
  }
  .shot-media {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #010409;
    border-radius: 8px;
    margin-bottom: 8px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #484f58;
    font-size: 11px;
  }
  .shot-media img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .shot-title { font-size: 13px; font-weight: 600; }
  .shot-meta { color: #8b949e; font-size: 11px; margin-top: 4px; }
  .shot-actions { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
  .btn {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 11px;
    cursor: pointer;
  }
  .btn.primary { background: #1f6feb; border-color: #1f6feb; color: #fff; }
  .empty { color: #484f58; font-size: 12px; }
  .status {
    padding: 12px 24px;
    border-top: 1px solid #21262d;
    color: #8b949e;
    font-size: 12px;
  }
  .status .ok { color: #3fb950; }
  .status .err { color: #ff7b72; }
</style>
</head>
<body>
  <header>
    <h1>{{ project.projectTitle }} <span style="color:#484f58">/ Storyboard</span></h1>
    <div class="meta">
      <a href="/script/{{ project_id }}">← Script</a>
      <a href="/assets/{{ project_id }}">Assets →</a>
    </div>
  </header>

  <form class="content" method="post" action="/storyboard/{{ project_id }}" enctype="multipart/form-data">
    <div class="section">
      <div class="section-header">
        <h2>Storyboard</h2>
        <div>
          <button type="button" class="btn primary" onclick="generateStoryboard()">Generate Storyboard</button>
        </div>
      </div>
      <div id="storyboard-container">
        {% for scene in storyboard.scenes %}
        <div class="scene-block">
          <div class="scene-header">
            <h2>{{ scene.sceneNumber }} — {{ scene.sceneTitle }}</h2>
            <span class="pill">{{ scene.shots|length }} shots</span>
          </div>
          <div class="shots">
            {% for shot in scene.shots %}
            <div class="shot-card">
              <div class="shot-media">
                {% if shot.image_url %}
                  <img src="{{ shot.image_url }}" alt="Shot {{ shot.shotNumber }}">
                {% else %}
                  <span>No image</span>
                {% endif %}
              </div>
              <div class="shot-title">{{ shot.shotNumber }}. {{ shot.title }}</div>
              <div class="shot-meta">{{ shot.camera }} · {{ shot.status }}</div>
              <div class="shot-meta">{{ shot.prompt[:120] }}</div>
              <div class="shot-actions">
                <button type="button" class="btn primary" onclick="generateShot('{{ scene.sceneId }}', '{{ shot.id }}')">Generate Image</button>
              </div>
            </div>
            {% endfor %}
            {% if not scene.shots %}
              <div class="empty">No shots yet. Click Generate Storyboard.</div>
            {% endif %}
          </div>
        </div>
        {% endfor %}
        {% if not storyboard.scenes %}
          <div class="empty">No storyboard yet. Click Generate Storyboard to create shots from script scenes.</div>
        {% endif %}
      </div>
    </div>

    <div class="status">
      {% if saved %}
        <span class="ok">✅ Guardado: {{ saved }}</span>
      {% endif %}
      {% if error %}
        <span class="err">❌ {{ error }}</span>
      {% endif %}
      &nbsp;
      {{ storyboard.scenes|length }} scenes · {{ total_shots }} shots
    </div>
  </form>

  <script>
    async function generateStoryboard() {
      const res = await fetch('/storyboard/{{ project_id }}/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
      });
      if (res.ok) {
        window.location.reload();
      } else {
        alert('Failed to generate storyboard');
      }
    }

    async function generateShot(sceneId, shotId) {
      const res = await fetch('/storyboard/{{ project_id }}/shot/' + shotId + '/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({sceneId}),
      });
      if (res.ok) {
        window.location.reload();
      } else {
        alert('Failed to generate shot');
      }
    }
  </script>
</body>
</html>
"""


def new_project_path(title: str) -> tuple[str, Path]:
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title).strip().replace(" ", "_")
    proj_id = f"{safe}"
    out = OUTPUT_DIR / proj_id
    out.mkdir(parents=True, exist_ok=True)
    return proj_id, out


@app.route("/", methods=["GET", "POST"])
def welcome():
    if request.method == "POST":
        title = request.form.get("title", "Mi Proyecto").strip() or "Mi Proyecto"
        style = request.form.get("style", "Realistic")
        proj_id, out_dir = new_project_path(title)
        project = StoryboardProject(projectTitle=title, globalStyle=style)
        project_path = out_dir / "project.json"
        save_project(project, project_path)
        return redirect(url_for("script_editor", project_id=proj_id))
    return render_template_string(WELCOME_TEMPLATE, styles=STYLES, error=None)


@app.route("/script/<project_id>", methods=["GET", "POST"])
def script_editor(project_id: str):
    project_path = OUTPUT_DIR / project_id / "project.json"
    if not project_path.exists():
        return redirect(url_for("welcome"))

    project = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
    markdown = ""
    saved = None
    error = None

    if request.method == "POST":
        uploaded = request.files.get("project_json")
        if uploaded and uploaded.filename.endswith(".json"):
            try:
                raw = uploaded.read()
                data = json.loads(raw.decode("utf-8"))
                project = validate_dict(data)
                save_project(project, project_path)
                markdown = rebuild_markdown(project)
                saved = str(project_path)
            except Exception as exc:
                error = f"JSON error: {exc}"
        else:
            markdown = request.form.get("markdown", "")
            try:
                parsed = parse_script(markdown)
                project.script = parsed
                save_project(project, project_path)
                saved = str(project_path)
            except Exception as exc:
                error = str(exc)

    if not saved:
        project = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
        markdown = rebuild_markdown(project)

    scenes = project.script.get("scenes", [])
    dialogues = project.script.get("dialogues", [])

    return render_template_string(
        SCRIPT_TEMPLATE,
        project=project,
        project_id=project_id,
        markdown=markdown,
        scenes=scenes,
        dialogues=dialogues,
        saved=saved,
        error=error,
    )


ASSETS_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Story Studio — Assets</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d1117;
    color: #c9d1d9;
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    border-bottom: 1px solid #21262d;
  }
  header h1 { font-size: 16px; color: #c9d1d9; }
  header .meta { color: #8b949e; font-size: 12px; }
  header .meta a { color: #58a6ff; text-decoration: none; margin: 0 6px; }
  .layout { display: grid; grid-template-columns: 240px 1fr; flex: 1; min-height: 0; }
  .sidebar {
    border-right: 1px solid #21262d;
    padding: 16px;
  }
  .sidebar h2 {
    font-size: 12px;
    text-transform: uppercase;
    color: #8b949e;
    margin-bottom: 12px;
    letter-spacing: 2px;
  }
  .pill {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid #30363d;
    background: #0d1117;
    color: #c9d1d9;
    font-size: 12px;
    margin: 0 6px 8px 0;
  }
  .pill.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }
  .content { padding: 24px; overflow: auto; }
  .section { margin-bottom: 28px; }
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }
  .section-header h2 { font-size: 14px; color: #c9d1d9; }
  .btn {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 999px;
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
  }
  .btn.primary { background: #1f6feb; border-color: #1f6feb; color: #fff; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
  .card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 12px;
  }
  .card .media {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #0d1117;
    border-radius: 8px;
    margin-bottom: 10px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #484f58;
    font-size: 12px;
  }
  .card .media img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .card .name { font-size: 13px; font-weight: 600; }
  .card .meta { color: #8b949e; font-size: 11px; margin-top: 4px; }
  .empty { color: #484f58; font-size: 12px; }
  .status {
    padding: 12px 24px;
    border-top: 1px solid #21262d;
    color: #8b949e;
    font-size: 12px;
  }
  .status .ok { color: #3fb950; }
  .status .err { color: #ff7b72; }
</style>
</head>
<body>
  <header>
    <h1>{{ project.projectTitle }} <span style="color:#484f58">/ Assets</span></h1>
    <div class="meta">
      <a href="/script/{{ project_id }}">← Script</a>
      <a href="/storyboard/{{ project_id }}">Storyboard →</a>
    </div>
  </header>

  <div class="layout">
    <div class="sidebar">
      <h2>Style</h2>
      <div>
        <span class="pill active">{{ project.globalStyle }}</span>
      </div>

      <h2 style="margin-top:20px">Project</h2>
      <div>
        <span class="pill">Characters {{ assets.characters|length }}</span>
        <span class="pill">Locations {{ assets.locations|length }}</span>
        <span class="pill">Props {{ assets.props|length }}</span>
      </div>

      <h2 style="margin-top:20px">Tips</h2>
      <p class="empty">Usá Autofill para generar assets desde el guion. También podés cargar un JSON con assets manuales.</p>
    </div>

    <form class="content" method="post" action="/assets/{{ project_id }}" enctype="multipart/form-data">
      <div class="section">
        <div class="section-header">
          <h2>Characters</h2>
          <div>
            <button type="button" class="btn primary" onclick="autofill('characters')">Autofill Characters</button>
            <button type="button" class="btn" onclick="document.getElementById('char-json').click()">Load JSON</button>
            <input type="file" id="char-json" name="char_json" accept=".json" style="display:none">
          </div>
        </div>
        <div class="grid">
          {% for a in assets.characters %}
          <div class="card">
            <div class="meta">ID: {{ a.id[:8] }}</div>
            <div class="name">{{ a.name }}</div>
            <div class="meta">{{ a.physical[:120] }}</div>
            <div class="meta">{{ a.clothing[:120] }}</div>
            {% if a.image_url %}
            <div class="media"><img src="{{ a.image_url }}" alt="{{ a.name }}"></div>
            {% else %}
            <div class="media">Sin imagen</div>
            {% endif %}
            <div class="shot-actions">
              <button type="button" class="btn primary" onclick="generateAssetImage('{{ a.id }}')">Generate Image</button>
            </div>
          </div>
          {% endfor %}
          {% if not assets.characters %}
          <div class="empty">No hay personajes aún.</div>
          {% endif %}
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <h2>Locations</h2>
          <div>
            <button type="button" class="btn primary" onclick="autofill('locations')">Autofill Locations</button>
            <button type="button" class="btn" onclick="document.getElementById('loc-json').click()">Load JSON</button>
            <input type="file" id="loc-json" name="loc_json" accept=".json" style="display:none">
          </div>
        </div>
        <div class="grid">
          {% for a in assets.locations %}
          <div class="card">
            <div class="meta">ID: {{ a.id[:8] }}</div>
            <div class="name">{{ a.name }}</div>
            <div class="meta">{{ a.time_of_day }}</div>
            <div class="meta">{{ a.prompt[:140] }}</div>
            {% if a.image_url %}
            <div class="media"><img src="{{ a.image_url }}" alt="{{ a.name }}"></div>
            {% else %}
            <div class="media">Sin imagen</div>
            {% endif %}
            <div class="shot-actions">
              <button type="button" class="btn primary" onclick="generateAssetImage('{{ a.id }}')">Generate Image</button>
            </div>
          </div>
          {% endfor %}
          {% if not assets.locations %}
          <div class="empty">No hay locaciones aún.</div>
          {% endif %}
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <h2>Props</h2>
          <div>
            <button type="button" class="btn primary" onclick="autofill('props')">Autofill Props</button>
            <button type="button" class="btn" onclick="document.getElementById('prop-json').click()">Load JSON</button>
            <input type="file" id="prop-json" name="prop_json" accept=".json" style="display:none">
          </div>
        </div>
        <div class="grid">
          {% for a in assets.props %}
          <div class="card">
            <div class="meta">ID: {{ a.id[:8] }}</div>
            <div class="name">{{ a.name }}</div>
            <div class="meta">{{ a.prompt[:140] }}</div>
            {% if a.image_url %}
            <div class="media"><img src="{{ a.image_url }}" alt="{{ a.name }}"></div>
            {% else %}
            <div class="media">Sin imagen</div>
            {% endif %}
            <div class="shot-actions">
              <button type="button" class="btn primary" onclick="generateAssetImage('{{ a.id }}')">Generate Image</button>
            </div>
          </div>
          {% endfor %}
          {% if not assets.props %}
          <div class="empty">No hay props aún.</div>
          {% endif %}
        </div>
      </div>

      <div class="status">
        {% if saved %}
          <span class="ok">✅ Guardado: {{ saved }}</span>
        {% endif %}
        {% if error %}
          <span class="err">❌ {{ error }}</span>
        {% endif %}
        &nbsp;
        {{ assets.characters|length }} characters · {{ assets.locations|length }} locations · {{ assets.props|length }} props
      </div>
    </form>
  </div>

  <script>
    async function autofill(kind) {
      const res = await fetch('/assets/{{ project_id }}/autofill', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({kind}),
      });
      if (res.ok) {
        window.location.reload();
      } else {
        alert('Autofill failed');
      }
    }

    async function generateAssetImage(assetId) {
      const res = await fetch('/assets/{{ project_id }}/asset/' + assetId + '/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
      });
      if (res.ok) {
        window.location.reload();
      } else {
        alert('Failed to generate asset image');
      }
    }

    ['char','loc','prop'].forEach(prefix => {
      const input = document.getElementById(prefix + '-json');
      if (!input) return;
      input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const form = new FormData();
        form.append(prefix + '_json', file);
        const url = '/assets/' + '{{ project_id }}';
        const res = await fetch(url, { method: 'POST', body: form });
        if (res.ok) {
          window.location.reload();
        } else {
          alert('Error loading JSON');
        }
      });
    });
  </script>
</body>
</html>
"""


@app.route("/assets/<project_id>", methods=["GET", "POST"])
def assets_page(project_id: str):
    project_path = OUTPUT_DIR / project_id / "project.json"
    if not project_path.exists():
        return redirect(url_for("welcome"))

    project = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
    saved = None
    error = None

    if request.method == "POST":
        uploaded = request.files.get("char_json")
        kind = None
        payload = None
        if uploaded and uploaded.filename.endswith(".json"):
            kind = "char"
            payload = json.loads(uploaded.read().decode("utf-8"))
        uploaded = request.files.get("loc_json")
        if uploaded and uploaded.filename.endswith(".json"):
            kind = "loc"
            payload = json.loads(uploaded.read().decode("utf-8"))
        uploaded = request.files.get("prop_json")
        if uploaded and uploaded.filename.endswith(".json"):
            kind = "prop"
            payload = json.loads(uploaded.read().decode("utf-8"))

        if kind and payload is not None:
            try:
                proj = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
                new_assets = payload if isinstance(payload, list) else [payload]
                typed_assets = []
                for item in new_assets:
                    atype = item.get("type", "prop")
                    if atype == "character":
                        typed_assets.append(CharacterAsset(**item))
                    elif atype == "location":
                        typed_assets.append(LocationAsset(**item))
                    else:
                        typed_assets.append(PropAsset(**item))
                if kind == "char":
                    proj.assets = [a for a in proj.assets if a.type != "character"] + typed_assets
                elif kind == "loc":
                    proj.assets = [a for a in proj.assets if a.type != "location"] + typed_assets
                elif kind == "prop":
                    proj.assets = [a for a in proj.assets if a.type != "prop"] + typed_assets
                save_project(proj, project_path)
                project = proj
                saved = str(project_path)
            except Exception as exc:
                error = f"Assets JSON error: {exc}"

    assets_by_type = {"characters": [], "locations": [], "props": []}
    for a in project.assets:
        atype = a.type
        if atype == "character":
            assets_by_type["characters"].append(a)
        elif atype == "location":
            assets_by_type["locations"].append(a)
        elif atype == "prop":
            assets_by_type["props"].append(a)

    return render_template_string(
        ASSETS_TEMPLATE,
        project=project,
        project_id=project_id,
        assets=assets_by_type,
        saved=saved,
        error=error,
    )


@app.route("/assets", defaults={"path": ""}, methods=["GET"])
@app.route("/assets/", defaults={"path": ""}, methods=["GET"])
def assets_redirect(path):
    return redirect(url_for("welcome"))


@app.route("/assets/<project_id>/autofill", methods=["POST"])
def assets_autofill(project_id: str):
    project_path = OUTPUT_DIR / project_id / "project.json"
    if not project_path.exists():
        return redirect(url_for("welcome"))

    project = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
    data = request.get_json(silent=True) or {}
    kind = data.get("kind", "")

    if kind == "characters":
        chars = [
            CharacterAsset(
                id="char_01",
                name="Thalasso",
                include_in_prompt=True,
                physical="Mediterranean man, early 30s, lean athletic build, olive skin, wavy raven-black hair, short beard, piercing amber eyes.",
                clothing="Navy canvas jacket, charcoal t-shirt, dark indigo jeans, brown leather boots, silver ring.",
                backstory="Political refugee traveling across borders to reunite with his partner.",
                image_url=None,
            )
        ]
        existing = list(project.assets)
        merged = [a for a in existing if a.type != "character"] + chars
        project.assets = merged
    elif kind == "locations":
        locs = [
            LocationAsset(
                id="loc_01",
                name="Parque Central",
                include_in_prompt=True,
                prompt="Expansive public park with golden-green grass, ancient oak trees, paved paths, distant city skyline.",
                time_of_day="Late afternoon",
                image_url=None,
            )
        ]
        existing = list(project.assets)
        merged = [a for a in existing if a.type != "location"] + locs
        project.assets = merged
    elif kind == "props":
        props = [
            PropAsset(
                id="prop_01",
                name="Fuente De Piedra",
                include_in_prompt=True,
                prompt="Three-tiered circular stone fountain with weathered gray limestone, moss, bronze lion heads.",
                image_url=None,
            )
        ]
        existing = list(project.assets)
        merged = [a for a in existing if a.type != "prop"] + props
        project.assets = merged

    save_project(project, project_path)
    return {"ok": True}


def _generate_shot_image(shot_id: str, shot: object, style: str, assets: list | None = None) -> str | None:
    try:
        from backends.hf_image import generate_from_prompt
    except Exception:
        return None

    title = ""
    prompt = ""
    if isinstance(shot, dict):
        title = shot.get("title", "") or ""
        prompt = shot.get("prompt", "") or ""
    else:
        title = getattr(shot, "title", "") or ""
        prompt = getattr(shot, "prompt", "") or ""

    scene_text = f"{prompt or title}".lower()
    asset_parts: list[str] = []
    asset_refs: list[str] = []

    if assets:
        for asset in assets:
            if isinstance(asset, dict):
                asset_type = asset.get("type", "")
                name = asset.get("name", "")
                physical = asset.get("physical", "")
                clothing = asset.get("clothing", "")
                prompt_text = asset.get("prompt", "")
                time_of_day = asset.get("time_of_day", "")
            else:
                asset_type = getattr(asset, "type", "")
                name = getattr(asset, "name", "")
                physical = getattr(asset, "physical", "")
                clothing = getattr(asset, "clothing", "")
                prompt_text = getattr(asset, "prompt", "")
                time_of_day = getattr(asset, "time_of_day", "")

            if not name:
                continue

            name_lower = name.lower()
            mentioned = name_lower in scene_text
            if asset_type == "character" and mentioned:
                desc = " ".join(filter(None, [physical, clothing])).strip()
                if desc:
                    asset_parts.append(f"{name}: {desc}")
                asset_refs.append(name)
            elif asset_type == "location" and mentioned:
                loc_desc = " ".join(filter(None, [prompt_text, time_of_day])).strip()
                if loc_desc:
                    asset_parts.append(f"{name}: {loc_desc}")
                asset_refs.append(name)
            elif asset_type == "prop" and mentioned:
                asset_parts.append(f"{name}: {prompt_text}")
                asset_refs.append(name)

    asset_context = "; ".join(asset_parts)
    shot_prompt = (
        f"{prompt or title}. "
        f"Style: {style}. Cinematic storyboard frame, 16:9, high detail."
    )
    if asset_context:
        shot_prompt = f"{shot_prompt} Reference assets: {asset_context}."

    out_dir = OUTPUT_DIR / "_asset_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{shot_id}.png"

    asset_image_url = _pick_asset_image_url(assets, asset_refs)
    if asset_image_url:
        try:
            from backends.kie_image import generate_from_image
            safe_prompt = _safe_img2img_prompt(shot_prompt)
            kie_path = generate_from_image(safe_prompt, image_url=asset_image_url, output_dir=out_dir, dest=dest)
            if kie_path:
                return f"/static/asset_images/{shot_id}.png"
        except Exception:
            pass

    image_path = generate_from_prompt(shot_prompt, "16:9", output_dir=out_dir, dest=dest)
    if image_path:
        return f"/static/asset_images/{shot_id}.png"
    return None


def _safe_img2img_prompt(prompt: str) -> str:
    blocked = [
        "gore",
        "blood",
        "violence",
        "nsfw",
        "nude",
        "naked",
        "sexual",
        "erotic",
        "weapon",
        "gun",
        "knife",
        "kill",
        "dead",
        "corpse",
        "terror",
        "terrorist",
        "abuse",
        "racist",
        "hate",
        "drug",
        "cocaine",
        "heroin",
        "meth",
    ]
    lowered = prompt.lower()
    for term in blocked:
        if term in lowered:
            return "Cinematic scene, stylized characters, safe for all audiences, high detail, 16:9"
    return prompt


def _pick_asset_image_url(assets: list | None, asset_refs: list[str]) -> str | None:
    if not assets or not asset_refs:
        return None
    ref_set = {name.lower() for name in asset_refs}
    for asset in assets:
        if isinstance(asset, dict):
            asset_name = (asset.get("name") or "").strip()
            image_url = asset.get("image_url") or ""
        else:
            asset_name = (getattr(asset, "name", "") or "").strip()
            image_url = getattr(asset, "image_url", "") or ""
        if asset_name.lower() in ref_set and image_url:
            return image_url
    return None


def _fake_asset_image(asset_id: str, name: str) -> str | None:
    try:
        from PIL import Image, ImageDraw
        out_dir = OUTPUT_DIR / "_asset_images"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{asset_id}.png"
        img = Image.new("RGB", (512, 512), (30, 30, 40))
        draw = ImageDraw.Draw(img)
        text = name[:24]
        bbox = draw.textbbox((0, 0), text)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((512 - w) / 2, (512 - h) / 2), text, fill=(200, 200, 200))
        img.save(path)
        return f"/static/asset_images/{asset_id}.png"
    except Exception:
        return None


def _atlas_asset_image(asset_id: str, asset: object, style: str) -> str | None:
    try:
        from backends.hf_image import generate_from_prompt
    except Exception:
        return None

    # Accept both dicts and Pydantic models
    if isinstance(asset, dict):
        asset_type = asset.get("type", "")
        name = asset.get("name", "")
        physical = asset.get("physical", "")
        clothing = asset.get("clothing", "")
        prompt_text = asset.get("prompt", "")
        time_of_day = asset.get("time_of_day", "")
    else:
        asset_type = getattr(asset, "type", "")
        name = getattr(asset, "name", "")
        physical = getattr(asset, "physical", "")
        clothing = getattr(asset, "clothing", "")
        prompt_text = getattr(asset, "prompt", "")
        time_of_day = getattr(asset, "time_of_day", "")

    if asset_type == "character":
        prompt = (
            f"Character portrait, full body shot. "
            f"{physical}. {clothing}. "
            f"Style: {style}. White background, high detail, consistent design."
        )
    elif asset_type == "location":
        prompt = (
            f"Location shot. {prompt_text}. {time_of_day}. "
            f"Style: {style}. Cinematic, wide shot."
        )
    elif asset_type == "prop":
        prompt = (
            f"Prop shot. {prompt_text}. Style: {style}. "
            f"Isolated object, clean background, high detail."
        )
    else:
        return None

    out_dir = OUTPUT_DIR / "_asset_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{asset_id}.png"
    image_path = generate_from_prompt(prompt, "16:9", output_dir=out_dir, dest=dest)
    if image_path:
        return f"/static/asset_images/{asset_id}.png"
    return None


@app.route("/assets/<project_id>/asset/<asset_id>/generate", methods=["POST"])
def asset_generate(project_id: str, asset_id: str):
    project_path = OUTPUT_DIR / project_id / "project.json"
    if not project_path.exists():
        return redirect(url_for("welcome"))

    project = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
    updated = False
    for a in project.assets:
        if a.id == asset_id:
            image_url = _atlas_asset_image(asset_id, a, project.globalStyle)
            if not image_url:
                image_url = _fake_asset_image(asset_id, a.name)
            a.image_url = image_url
            updated = True
            break

    if updated:
        save_project(project, project_path)
    return {"ok": updated}


@app.route("/storyboard/<project_id>", methods=["GET", "POST"])
def storyboard_page(project_id: str):
    project_path = OUTPUT_DIR / project_id / "project.json"
    if not project_path.exists():
        return redirect(url_for("welcome"))

    project = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
    saved = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "generate":
            script_scenes = project.script.get("scenes", [])
            storyboard_scenes = []
            for idx, scene in enumerate(script_scenes, start=1):
                title = scene.get("description") or scene.get("slugline", "") if isinstance(scene, dict) else getattr(scene, "description", "") or getattr(scene, "slugline", "")
                shots = [
                    Shot(
                        shotNumber=f"Shot-{idx}-{sidx+1}",
                        title=title,
                        prompt=title,
                        camera="static",
                    )
                    for sidx in range(2)
                ]
                scene_id = scene.get("id") if isinstance(scene, dict) else getattr(scene, "id", "")
                storyboard_scenes.append(
                    {
                        "sceneId": scene_id,
                        "sceneNumber": f"Scene {idx}",
                        "sceneTitle": title,
                        "shots": [s.model_dump() for s in shots],
                    }
                )
            project.storyboard = {"scenes": storyboard_scenes}
            save_project(project, project_path)
            saved = str(project_path)

    storyboard = project.storyboard if isinstance(project.storyboard, dict) else {"scenes": []}
    scenes = storyboard.get("scenes", [])
    total_shots = sum(len(scene.get("shots", [])) for scene in scenes)

    return render_template_string(
        STORYBOARD_TEMPLATE,
        project=project,
        project_id=project_id,
        storyboard=storyboard,
        total_shots=total_shots,
        saved=saved,
        error=error,
    )


@app.route("/storyboard/<project_id>/generate", methods=["POST"])
def storyboard_generate(project_id: str):
    project_path = OUTPUT_DIR / project_id / "project.json"
    if not project_path.exists():
        return redirect(url_for("welcome"))

    project = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
    script_scenes = project.script.get("scenes", [])
    storyboard_scenes = []
    for idx, scene in enumerate(script_scenes, start=1):
        title = scene.get("description") or scene.get("slugline", "") if isinstance(scene, dict) else getattr(scene, "description", "") or getattr(scene, "slugline", "")
        shots = [
            Shot(
                shotNumber=f"Shot-{idx}-{sidx+1}",
                title=title,
                prompt=title,
                camera="static",
            )
            for sidx in range(2)
        ]
        scene_id = scene.get("id") if isinstance(scene, dict) else getattr(scene, "id", "")
        storyboard_scenes.append(
            {
                "sceneId": scene_id,
                "sceneNumber": f"Scene {idx}",
                "sceneTitle": title,
                "shots": [s.model_dump() for s in shots],
            }
        )
    project.storyboard = {"scenes": storyboard_scenes}
    save_project(project, project_path)
    return {"ok": True}


@app.route("/storyboard/<project_id>/shot/<shot_id>/generate", methods=["POST"])
def shot_generate(project_id: str, shot_id: str):
    project_path = OUTPUT_DIR / project_id / "project.json"
    if not project_path.exists():
        return redirect(url_for("welcome"))

    project = validate_dict(json.loads(project_path.read_text(encoding="utf-8")))
    assets = list(project.assets)
    updated = False
    for scene in project.storyboard.get("scenes", []):
        for shot in scene.get("shots", []):
            if shot.get("id") == shot_id:
                shot["status"] = ShotStatus.image_generated.value
                shot["image_url"] = _generate_shot_image(shot_id, shot, project.globalStyle, assets=assets)
                updated = True
                break
        if updated:
            break

    if updated:
        save_project(project, project_path)
    return {"ok": updated}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
