import json
import os
import sys
from datetime import datetime
from pathlib import Path

DOCUMENTS_DIR = os.path.join(os.path.expanduser("~"), "Documents")
DATA_DIR = os.path.join(DOCUMENTS_DIR, "zetnote_data")
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")
LINKS_FILE = os.path.join(DATA_DIR, "links.json")
SHORTMAP_FILE = os.path.join(DATA_DIR, "shortmap.json")

def load_data(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    for f in [NOTES_FILE, LINKS_FILE]:
        if not os.path.exists(f):
            save_data(f, {})

    notes = load_data(NOTES_FILE)
    short_map = {}
    for full_id in notes:
        short_id = get_short_id(full_id)
        if short_id in short_map and short_map[short_id] != full_id:
            print(f"UYARI: {short_id} çakışıyor! ({short_map[short_id]} ve {full_id})")
        short_map[short_id] = full_id
    save_data(SHORTMAP_FILE, short_map)

def generate_id():
    return datetime.now().strftime("%Y%m%d%H%M%S")

def get_short_id(full_id):
    return str(abs(hash(full_id)) % 100000).zfill(5)

def update_short_map(full_id):
    short_map = load_data(SHORTMAP_FILE)
    short_id = get_short_id(full_id)
    if short_id in short_map and short_map[short_id] != full_id:
        print(f"UYARI: {short_id} başka bir nota da atanmış!")
    short_map[short_id] = full_id
    save_data(SHORTMAP_FILE, short_map)

def resolve_id(prefix):
    notes = load_data(NOTES_FILE)
    short_map = load_data(SHORTMAP_FILE)

    # Kısa ID öncelikli
    if prefix in short_map:
        return short_map[prefix]

    # Uzun ID başı eşleşmesi
    matches = [id_ for id_ in notes if id_.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print("Birden fazla not eşleşiyor. Daha fazla karakter gir.")
    else:
        print("Eşleşen not bulunamadı.")
    return None

def add_note(content):
    notes = load_data(NOTES_FILE)
    id_ = generate_id()
    notes[id_] = content
    save_data(NOTES_FILE, notes)
    update_short_map(id_)
    print(f"Not eklendi: {id_} (kısa ID: {get_short_id(id_)})")
    print(f"Veri klasörü: {DATA_DIR}")

def delete_note(id_):
    notes = load_data(NOTES_FILE)
    links = load_data(LINKS_FILE)
    short_map = load_data(SHORTMAP_FILE)
    
    full_id = resolve_id(id_)
    if not full_id:
        print("Not bulunamadı.")
        return
    
    if full_id in notes:
        del notes[full_id]
        save_data(NOTES_FILE, notes)
        print(f"Not silindi: {full_id}")
    else:
        print("Not bulunamadı.")
        return
    
    # Shortmap'ten sildim 
    short_id = get_short_id(full_id)
    if short_id in short_map:
        del short_map[short_id]
        save_data(SHORTMAP_FILE, short_map)
    
    # Bağlantılardan sil
    if full_id in links:
        del links[full_id]
    
    # Diğer notların bağlantılarından bu notu sil
    for note_id in list(links.keys()):
        if full_id in links[note_id]:
            links[note_id].remove(full_id)
    
    # Bu kısmı Şebnem Ferah dinleyerek yazdım ;)
    save_data(LINKS_FILE, links)

def list_notes():
    notes = load_data(NOTES_FILE)
    for id_, content in notes.items():
        print(f"[{get_short_id(id_)}] {content}")

def link_notes(id1, id2):
    links = load_data(LINKS_FILE)
    id1 = resolve_id(id1)
    id2 = resolve_id(id2)
    if not id1 or not id2:
        return
    if id1 not in links:
        links[id1] = []
    if id2 not in links[id1]:
        links[id1].append(id2)
    save_data(LINKS_FILE, links)
    print(f"{get_short_id(id1)} <--> {get_short_id(id2)} bağlantısı kuruldu.")

def show_note(id_):
    notes = load_data(NOTES_FILE)
    links = load_data(LINKS_FILE)
    short_map = load_data(SHORTMAP_FILE)

    full_id = resolve_id(id_)
    if not full_id or full_id not in notes:
        print("Not bulunamadı.")
        return

    print(f"[{get_short_id(full_id)}] {notes[full_id]}")
    
    linked = links.get(full_id, [])
    if linked:
        print("\nBağlantılı notlar:")
        for lid in linked:
            short = get_short_id(lid)
            content = notes.get(lid, "---")
            print(f"  - [{short}] {content}")
    else:
        print("\nBağlantı yok.")

def export_notes():
    notes = load_data(NOTES_FILE)
    if not notes:
        print("Hiç not yok, dışa aktarılacak bir şey bulunamadı.")
        return
    
    os.makedirs(os.path.join(DATA_DIR, "exports"), exist_ok=True)
    export_name = datetime.now().strftime("export_%Y%m%d.txt")
    export_path = os.path.join(DATA_DIR, "exports", export_name)

    with open(export_path, "w", encoding="utf-8") as f:
        sorted_notes = sorted(notes.items(), key=lambda x: x[0])  # Tarihe göre sırala
        for full_id, content in sorted_notes:
            short = get_short_id(full_id)
            f.write(f"[{short}] {content}\n")
    
    print(f"Notlar dışa aktarıldı: {export_path}")

def export_related_notes(id_):
    notes = load_data(NOTES_FILE)
    links = load_data(LINKS_FILE)
    full_id = resolve_id(id_)

    if not full_id or full_id not in notes:
        print("Not bulunamadı.")
        return

    related_ids = set()
    to_visit = [full_id]
    visited = set()

    while to_visit:
        current = to_visit.pop()
        if current in visited:
            continue
        visited.add(current)
        related_ids.add(current)
        for linked in links.get(current, []):
            if linked not in visited:
                to_visit.append(linked)

    os.makedirs(os.path.join(DATA_DIR, "exports"), exist_ok=True)
    short_main = get_short_id(full_id)
    export_name = f"related_{short_main}.txt"
    export_path = os.path.join(DATA_DIR, "exports", export_name)

    with open(export_path, "w", encoding="utf-8") as f:
        for rid in sorted(related_ids):
            short = get_short_id(rid)
            content = notes.get(rid, "---")
            f.write(f"[{short}] {content}\n")

    print(f"Not ve bağlantılı notlar dışa aktarıldı: {export_path}")

def interactive_mode():
    print("Zettelkasten CLI'ye hoş geldin!")
    print(f"Veri klasörü: {DATA_DIR}")
    print("Komutlar: add | delete | link | list | show | export[-related] | exit\n")

    while True:
        try:
            raw = input(">>> ").strip()
            if not raw:
                continue
            args = raw.split()
            cmd = args[0]

            if cmd == "exit":
                break
            elif cmd == "add" and len(args) >= 2:
                content = " ".join(args[1:])
                add_note(content)
            elif cmd == "delete" and len(args) == 2:
                delete_note(args[1])
            elif cmd == "link" and len(args) == 3:
                link_notes(args[1], args[2])
            elif cmd == "list":
                list_notes()
            elif cmd == "show" and len(args) == 2:
                show_note(args[1])
            elif cmd == "export":
                export_notes()
            elif cmd == "export-related" and len(args) == 2:
                export_related_notes(args[1])
            else:
                print("Hatalı komut veya eksik argüman.")
        except KeyboardInterrupt:
            print("\nÇıkılıyor...")
            break

if __name__ == "__main__":
    ensure_data_files()

    if len(sys.argv) < 2:
        interactive_mode()
    else:
        cmd = sys.argv[1]

        if cmd == "add" and len(sys.argv) >= 3:
            content = " ".join(sys.argv[2:])
            add_note(content)
        elif cmd == "delete" and len(sys.argv) == 3:
            delete_note(sys.argv[2])
        elif cmd == "link" and len(sys.argv) == 4:
            link_notes(sys.argv[2], sys.argv[3])
        elif cmd == "list":
            list_notes()
        elif cmd == "show" and len(sys.argv) == 3:
            show_note(sys.argv[2])
        elif cmd == "export":
            export_notes()
        elif cmd == "export-related" and len(sys.argv) == 3:
            export_related_notes(sys.argv[2])
        else:
            print("Hatalı komut.")