"""
generate_neptune_data.py
Converts drug_interactions.csv into Neptune-compatible bulk load files (CSV format).
Run: python generate_neptune_data.py
Outputs: vertices.csv and edges.csv → upload both to S3
"""

import csv
import json

INPUT_FILE = "drug_interactions.csv"
VERTICES_FILE = "neptune_vertices.csv"
EDGES_FILE = "neptune_edges.csv"

seen_nodes = {}  # name → id
vertices = []
edges = []

def slugify(name):
    return name.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")

def get_or_create_node(name, node_type):
    key = name.strip().lower()
    if key not in seen_nodes:
        node_id = f"{node_type}_{slugify(name)}"
        seen_nodes[key] = node_id
        vertices.append({
            "~id": node_id,
            "~label": node_type,
            "name:String": name.strip()
        })
    return seen_nodes[key]

with open(INPUT_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        drug_a = row["drug_a"].strip()
        drug_b = row["drug_b"].strip()
        interaction_type = row["interaction_type"].strip()
        severity = row["severity"].strip()
        description = row["description"].strip()

        # Determine label for each node
        type_a = "Drug"
        if interaction_type == "drug-food":
            type_b = "Food"
        elif interaction_type == "drug-alcohol":
            type_b = "Substance"
        else:
            type_b = "Drug"

        id_a = get_or_create_node(drug_a, type_a)
        id_b = get_or_create_node(drug_b, type_b)

        edge_id = f"edge_{i}"
        edges.append({
            "~id": edge_id,
            "~label": "INTERACTS_WITH",
            "~from": id_a,
            "~to": id_b,
            "interaction_type:String": interaction_type,
            "severity:String": severity,
            "description:String": description.replace('"', "'")
        })

# Write vertices
with open(VERTICES_FILE, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["~id", "~label", "name:String"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(vertices)

# Write edges
with open(EDGES_FILE, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["~id", "~label", "~from", "~to", "interaction_type:String", "severity:String", "description:String"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(edges)

print(f"✅ Created {VERTICES_FILE} with {len(vertices)} nodes")
print(f"✅ Created {EDGES_FILE} with {len(edges)} edges")
print("\nNext: Upload both files to your S3 bucket under the path: neptune-data/")
