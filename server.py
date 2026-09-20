import os
import json
import shutil
import urllib.parse
import subprocess
import re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(BASE_DIR, "projects.json")
PORT = 5500
VALID_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}

DEFAULT_CATEGORIES = {
    '1': 'General',
    '2': 'Quiz',
    '3': 'Judges',
    '4': 'Awards',
    '5': 'Mentors',
    '6': 'Other',
    '7': 'Prizes'
}

def slugify(text):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text).lower()

def load_projects_data():
    if not os.path.exists(PROJECTS_FILE):
        data = {
            "active_project_id": "microsoft_visit",
            "selected_root": "/Volumes/C/Selected",
            "projects": {
                "microsoft_visit": {
                    "id": "microsoft_visit",
                    "name": "Microsoft Visit - SVIET Impact AI Ideathon",
                    "source_dir": "/Volumes/C/Microsoft Visit - SVIET Impact AI Ideathon",
                    "output_dir": "/Volumes/C/Selected/Microsoft Visit - SVIET Impact AI Ideathon",
                    "categories": DEFAULT_CATEGORIES
                }
            }
        }
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return data
    
    with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_projects_data(data):
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def get_active_project(data=None):
    if data is None:
        data = load_projects_data()
    active_id = data.get("active_project_id")
    projects = data.get("projects", {})
    if active_id in projects:
        return projects[active_id]
    if projects:
        first_key = list(projects.keys())[0]
        data["active_project_id"] = first_key
        save_projects_data(data)
        return projects[first_key]
    return None

def get_volume_path(path):
    if not path or not path.startswith('/Volumes/'):
        return None
    parts = path.split('/')
    if len(parts) >= 3:
        return f"/Volumes/{parts[2]}"
    return None

def is_volume_mounted(path):
    if not path:
        return False
    vol = get_volume_path(path)
    if vol:
        return os.path.exists(vol)
    return os.path.exists(path) or os.path.exists(os.path.dirname(path))

def ensure_project_structure(project):
    out_dir = project.get("output_dir", "")
    if not is_volume_mounted(out_dir):
        return False
    try:
        os.makedirs(os.path.join(out_dir, "Overall_Selected"), exist_ok=True)
        os.makedirs(os.path.join(out_dir, "Categories"), exist_ok=True)
        os.makedirs(os.path.join(out_dir, "Removed"), exist_ok=True)
        for cat_id, cat_name in project.get("categories", {}).items():
            os.makedirs(os.path.join(out_dir, "Categories", f"{cat_id}_{cat_name}"), exist_ok=True)
        return True
    except Exception as e:
        print(f"Error ensuring project structure: {e}")
        return False

def discover_candidate_folders(root_dir="/Volumes/C"):
    candidates = []
    if not os.path.exists(root_dir):
        return candidates
    
    ignore_names = {'$recycle.bin', '.spotlight-v100', '.temporaryitems', '.trashes', '.fseventsd', 'system volume information', 'selected', 'android', 'all downloads', 'misc'}
    try:
        for entry in os.listdir(root_dir):
            if entry.startswith('.') or entry.lower() in ignore_names:
                continue
            full_p = os.path.join(root_dir, entry)
            if os.path.isdir(full_p):
                try:
                    files = [f for f in os.listdir(full_p) if not f.startswith('.') and os.path.splitext(f)[1].lower() in VALID_EXTS]
                    if len(files) > 0:
                        candidates.append({
                            "name": entry,
                            "path": full_p,
                            "photo_count": len(files)
                        })
                except Exception:
                    pass
    except Exception:
        pass
    return sorted(candidates, key=lambda x: x["name"])

# Initialize default active project structure on startup
active_proj = get_active_project()
if active_proj:
    ensure_project_structure(active_proj)

class SpeedCullerHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        if self.path.startswith('/photo/'):
            self.send_header('Cache-Control', 'public, max-age=86400, immutable')
        SimpleHTTPRequestHandler.end_headers(self)

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == '/favicon.ico' or path == '/favicon.svg':
            fav_path = os.path.join(BASE_DIR, 'favicon.svg')
            if os.path.exists(fav_path):
                self.send_response(200)
                self.send_header('Content-Type', 'image/svg+xml')
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                return
        SimpleHTTPRequestHandler.do_HEAD(self)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            html_path = os.path.join(BASE_DIR, 'index.html')
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())
            return

        if path == '/favicon.ico' or path == '/favicon.svg':
            fav_path = os.path.join(BASE_DIR, 'favicon.svg')
            if os.path.exists(fav_path):
                self.send_response(200)
                self.send_header('Content-Type', 'image/svg+xml')
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                with open(fav_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404)
                return

        if path == '/api/projects':
            data = load_projects_data()
            projects_list = list(data.get("projects", {}).values())
            candidates = discover_candidate_folders()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "active_project_id": data.get("active_project_id"),
                "selected_root": data.get("selected_root", "/Volumes/C/Selected"),
                "projects": projects_list,
                "discovered_folders": candidates
            }).encode('utf-8'))
            return

        if path == '/api/photos':
            data = load_projects_data()
            project = get_active_project(data)
            if not project:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'No active project', 'drive_connected': False}).encode('utf-8'))
                return

            src_dir = project["source_dir"]
            out_dir = project["output_dir"]
            vol_path = get_volume_path(src_dir) or get_volume_path(out_dir)
            drive_mounted = is_volume_mounted(src_dir) and is_volume_mounted(out_dir)

            if not drive_mounted:
                res_data = {
                    'drive_connected': False,
                    'volume_path': vol_path or src_dir,
                    'active_project': project,
                    'source_dir': src_dir,
                    'output_dir': out_dir,
                    'categories': project.get("categories", DEFAULT_CATEGORIES),
                    'total_master': 0,
                    'total_selected': 0,
                    'master_photos': [],
                    'selected_photos': [],
                    'photos': [],
                    'assigned': {},
                    'error': f"External drive ({vol_path or 'drive'}) is disconnected."
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(res_data).encode('utf-8'))
                return

            ensure_project_structure(project)
            overall_dir = os.path.join(out_dir, "Overall_Selected")
            categories_dir = os.path.join(out_dir, "Categories")
            cats = project.get("categories", DEFAULT_CATEGORIES)

            # 1. Master photos
            master_photos = []
            if os.path.exists(src_dir):
                master_photos = sorted([
                    f for f in os.listdir(src_dir)
                    if not f.startswith('.') and os.path.splitext(f)[1].lower() in VALID_EXTS
                ])

            # 2. Selected photos
            selected_photos = []
            if os.path.exists(overall_dir):
                selected_photos = sorted([
                    f for f in os.listdir(overall_dir)
                    if not f.startswith('.') and os.path.splitext(f)[1].lower() in VALID_EXTS
                ])

            # 3. Category assignments
            cat_map = {}
            if os.path.exists(categories_dir):
                for cat_id, cat_name in cats.items():
                    folder = os.path.join(categories_dir, f"{cat_id}_{cat_name}")
                    if os.path.exists(folder):
                        for f in os.listdir(folder):
                            if not f.startswith('.') and os.path.splitext(f)[1].lower() in VALID_EXTS:
                                cat_map[f] = cat_name

            res_data = {
                'drive_connected': True,
                'volume_path': vol_path,
                'active_project': project,
                'source_dir': src_dir,
                'output_dir': out_dir,
                'categories': cats,
                'total_master': len(master_photos),
                'total_selected': len(selected_photos),
                'master_photos': master_photos,
                'selected_photos': selected_photos,
                'photos': selected_photos, # default compatibility
                'assigned': cat_map
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            return

        if path.startswith('/photo/'):
            filename = urllib.parse.unquote(path[7:])
            project = get_active_project()
            file_path = None

            if project:
                out_dir = project["output_dir"]
                src_dir = project["source_dir"]
                # 1. Check Overall_Selected
                p1 = os.path.join(out_dir, "Overall_Selected", filename)
                if os.path.exists(p1):
                    file_path = p1
                # 2. Check source_dir
                elif os.path.exists(os.path.join(src_dir, filename)):
                    file_path = os.path.join(src_dir, filename)
                # 3. Check Categories subfolders
                elif os.path.exists(os.path.join(out_dir, "Categories")):
                    for sub in os.listdir(os.path.join(out_dir, "Categories")):
                        sub_p = os.path.join(out_dir, "Categories", sub, filename)
                        if os.path.exists(sub_p):
                            file_path = sub_p
                            break

            if not file_path or not os.path.exists(file_path):
                self.send_error(404, "File not found")
                return

            self.send_response(200)
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.jpg', '.jpeg']:
                self.send_header('Content-Type', 'image/jpeg')
            elif ext == '.png':
                self.send_header('Content-Type', 'image/png')
            else:
                self.send_header('Content-Type', 'application/octet-stream')
            
            size = os.path.getsize(file_path)
            self.send_header('Content-Length', str(size))
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
        payload = json.loads(post_body.decode('utf-8')) if post_body else {}

        if path == '/api/projects/switch':
            project_id = payload.get("project_id")
            data = load_projects_data()
            if project_id in data.get("projects", {}):
                data["active_project_id"] = project_id
                save_projects_data(data)
                ensure_project_structure(data["projects"][project_id])
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "active_project": data["projects"][project_id]}).encode('utf-8'))
                return
            else:
                self.send_error(400, "Invalid project ID")
                return

        if path == '/api/projects/create':
            name = payload.get("name", "").strip()
            source_dir = payload.get("source_dir", "").strip()
            categories = payload.get("categories") or DEFAULT_CATEGORIES
            
            if not name or not source_dir or not os.path.exists(source_dir):
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Invalid name or folder path does not exist"}).encode('utf-8'))
                return

            data = load_projects_data()
            project_id = slugify(name)
            selected_root = data.get("selected_root", "/Volumes/C/Selected")
            output_dir = payload.get("output_dir") or os.path.join(selected_root, name)

            project = {
                "id": project_id,
                "name": name,
                "source_dir": source_dir,
                "output_dir": output_dir,
                "categories": categories
            }

            ensure_project_structure(project)
            data["projects"][project_id] = project
            data["active_project_id"] = project_id
            save_projects_data(data)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "project": project}).encode('utf-8'))
            return

        if path == '/api/projects/update_categories':
            project_id = payload.get("project_id")
            categories = payload.get("categories")
            data = load_projects_data()
            if not project_id:
                project_id = data.get("active_project_id")
            if project_id in data.get("projects", {}) and isinstance(categories, dict):
                data["projects"][project_id]["categories"] = categories
                save_projects_data(data)
                ensure_project_structure(data["projects"][project_id])
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "categories": categories}).encode('utf-8'))
                return
            else:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Invalid project ID or categories"}).encode('utf-8'))
                return

        project = get_active_project()
        if not project:
            self.send_error(500, "No active project")
            return

        src_dir = project["source_dir"]
        out_dir = project["output_dir"]
        overall_dir = os.path.join(out_dir, "Overall_Selected")
        categories_dir = os.path.join(out_dir, "Categories")
        removed_dir = os.path.join(out_dir, "Removed")
        cats = project.get("categories", DEFAULT_CATEGORIES)

        if not is_volume_mounted(src_dir) or not is_volume_mounted(out_dir):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "External drive is disconnected. Please reconnect your drive."}).encode('utf-8'))
            return

        if path == '/api/categorize':
            filename = payload.get('filename')
            category = payload.get('category')
            
            if filename:
                src_in_overall = os.path.join(overall_dir, filename)
                src_in_master = os.path.join(src_dir, filename)

                # 1. Ensure in Overall_Selected
                if not os.path.exists(src_in_overall) and os.path.exists(src_in_master):
                    shutil.copy2(src_in_master, src_in_overall)

                file_to_copy = src_in_overall if os.path.exists(src_in_overall) else src_in_master

                # 2. Clear from all category subfolders
                for cat_id, cat_name in cats.items():
                    old_path = os.path.join(categories_dir, f"{cat_id}_{cat_name}", filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    dot_f = os.path.join(categories_dir, f"{cat_id}_{cat_name}", "._" + filename)
                    if os.path.exists(dot_f):
                        os.remove(dot_f)

                # 3. Copy to targeted category folder if assigned
                if category and os.path.exists(file_to_copy):
                    for cat_id, cat_name in cats.items():
                        if cat_name.lower() == category.lower():
                            target_dir = os.path.join(categories_dir, f"{cat_id}_{cat_name}")
                            dst = os.path.join(target_dir, filename)
                            if not os.path.exists(dst):
                                shutil.copy2(file_to_copy, dst)
                            break
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'filename': filename, 'category': category}).encode('utf-8'))
            return

        if path == '/api/toggle_selection':
            filename = payload.get('filename')
            select = payload.get('select') # True, False, or None
            should_select = False
            
            if filename:
                src_master = os.path.join(src_dir, filename)
                dst_overall = os.path.join(overall_dir, filename)
                is_selected = os.path.exists(dst_overall)
                should_select = not is_selected if select is None else bool(select)

                if should_select:
                    if os.path.exists(src_master) and not os.path.exists(dst_overall):
                        shutil.copy2(src_master, dst_overall)
                else:
                    if os.path.exists(dst_overall):
                        dst_removed = os.path.join(removed_dir, filename)
                        shutil.move(dst_overall, dst_removed)
                    for cat_id, cat_name in cats.items():
                        cat_file = os.path.join(categories_dir, f"{cat_id}_{cat_name}", filename)
                        if os.path.exists(cat_file):
                            os.remove(cat_file)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'filename': filename, 'selected': should_select}).encode('utf-8'))
            return

        if path == '/api/remove_from_selection':
            filename = payload.get('filename')
            if filename:
                dst_overall = os.path.join(overall_dir, filename)
                if os.path.exists(dst_overall):
                    dst_removed = os.path.join(removed_dir, filename)
                    shutil.move(dst_overall, dst_removed)
                for cat_id, cat_name in cats.items():
                    cat_file = os.path.join(categories_dir, f"{cat_id}_{cat_name}", filename)
                    if os.path.exists(cat_file):
                        os.remove(cat_file)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'filename': filename}).encode('utf-8'))
            return

        if path == '/api/open_dest':
            subprocess.run(['open', out_dir])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'path': out_dir}).encode('utf-8'))
            return

        self.send_error(404)

if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', PORT), SpeedCullerHandler)
    print(f"Speed Culler running at http://127.0.0.1:{PORT}")
    server.serve_forever()
