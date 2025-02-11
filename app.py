import json
import os
import re
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

SHEET_ID = "1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY"
SHEETS = {
    1595979957: "Shotguns",
    1090554564: "Sniper Rifles",
    1318165198: "Fusion Rifles",
    657764751: "Energy Grenade Launchers",
    1239299765: "Glaives",
    288998351: "Trace Rifles",
    550485113: "Rocket Sidearms",
    1919916707: "Light Machine Guns",
    439751986: "Heavy Grenade Launchers",
    473850359: "Swords",
    981030684: "Rocket Launchers",
    29008106: "Linear Fusion Rifles",
    1890042119: "Auto Rifles",
    324500912: "Bows",
    1315046624: "Hand Cannons",
    1712537582: "Pulse Rifles",
    946843299: "Scout Rifles",
    1594008157: "Sidearms",
    1405969509: "Submachine Guns"
}

DATA_FILE = "selected_items.json"
WEAPON_DATA_FILE = "weapon_data.json"
CACHE_DURATION = timedelta(hours=1)

def fetch_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json&gid={gid}"
    response = requests.get(url)
    match = re.search(r'google.visualization.Query.setResponse\((.*)\);', response.text)
    if not match:
        return [], []
    
    data = json.loads(match.group(1))["table"]
    headers = [col["label"] for col in data["cols"]]
    
    weapon_icon_index = headers.index("WEAPON Icon") if "WEAPON Icon" in headers else None
    if weapon_icon_index is not None:
        headers.pop(weapon_icon_index)
    
    rows = []
    for row in data["rows"]:
        processed_row = [cell.get("v", "") if cell else "" for cell in row["c"]]
        if weapon_icon_index is not None:
            processed_row.pop(weapon_icon_index)
        
        if processed_row and processed_row[-1] not in ("/", "?"):
            for i, cell in enumerate(processed_row):
                if isinstance(cell, str):
                    processed_row[i] = cell.replace('\n', '<br>')
            rows.append(processed_row)
    
    return headers, rows

def load_selected_items():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_selected_items(selected_items):
    with open(DATA_FILE, "w") as f:
        json.dump(selected_items, f, indent=4)

def load_weapon_data():
    if os.path.exists(WEAPON_DATA_FILE):
        with open(WEAPON_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_weapon_data(weapon_data):
    with open(WEAPON_DATA_FILE, "w") as f:
        json.dump(weapon_data, f, indent=4)

def is_cache_valid():
    if os.path.exists(WEAPON_DATA_FILE):
        with open(WEAPON_DATA_FILE, "r") as f:
            data = json.load(f)
            last_fetched = data.get("last_fetched")
            if last_fetched:
                last_fetched_time = datetime.fromisoformat(last_fetched)
                if datetime.now() - last_fetched_time < CACHE_DURATION:
                    return True
    return False

def update_cache_timestamp():
    data = load_weapon_data()
    data["last_fetched"] = datetime.now().isoformat()
    save_weapon_data(data)

@app.route("/")
def index():
    return render_template("index.html", sheets=SHEETS)

@app.route("/sheet/<int:gid>")
def sheet(gid):
    if gid not in SHEETS:
        return "Invalid Sheet ID", 404
    headers, rows = fetch_sheet_data(gid)
    return render_template("sheet.html", sheet_name=SHEETS[gid], headers=headers, rows=rows, sheets=SHEETS)

@app.route("/get_selected_items")
def get_selected_items():
    return jsonify(load_selected_items())

@app.route("/save_selected_items", methods=["POST"])
def save_selected_items_route():
    data = request.json
    existing_data = load_selected_items()

    for sheet_name, selected_items in data.items():
        existing_data[sheet_name] = selected_items

    save_selected_items(existing_data)
    return jsonify({"status": "success", "message": "Selection saved!"})

@app.route("/saved_weapons")
def saved_weapons():
    selected_items = load_selected_items()

    if not is_cache_valid():
        weapon_details = {}

        for sheet_gid, sheet_name in SHEETS.items():
            headers, rows = fetch_sheet_data(sheet_gid)
            
            if not headers:
                continue

            possible_name_columns = ["WEAPON Name", "Name"]
            name_index = next((headers.index(col) for col in possible_name_columns if col in headers), None)

            if name_index is None:
                continue

            weapon_map = {row[name_index]: row for row in rows}

            if sheet_name in selected_items:
                for weapon_name in selected_items[sheet_name]:
                    if weapon_name in weapon_map:
                        if sheet_name not in weapon_details:
                            weapon_details[sheet_name] = {
                                "sheet_name": sheet_name,
                                "headers": headers,
                                "data": []
                            }
                        weapon_details[sheet_name]["data"].append(weapon_map[weapon_name])

        update_cache_timestamp()
        save_weapon_data({"weapon_details": weapon_details})

    else:
        weapon_details = load_weapon_data().get("weapon_details", {})

    weapon_details_list = []
    for sheet_name, details in weapon_details.items():
        weapon_details_list.append({
            "sheet_name": sheet_name,
            "headers": details["headers"],
            "data": details["data"]
        })

    return render_template("saved_weapons.html", weapon_details=weapon_details_list, sheets=SHEETS)


if __name__ == "__main__":
    app.run(debug=True)
