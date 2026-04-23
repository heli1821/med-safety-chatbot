"""
lambda/handler.py
AWS Lambda handler: receives user message → queries Neptune → calls Claude via Bedrock → returns response
"""

import json
import os
import boto3
from gremlin_python.driver import client, serializer

NEPTUNE_ENDPOINT = os.environ["NEPTUNE_ENDPOINT"]   # e.g. your-cluster.cluster-xxxx.us-east-1.neptune.amazonaws.com
NEPTUNE_PORT = os.environ.get("NEPTUNE_PORT", "8182")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
CLAUDE_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def query_neptune(drugs: list[str]) -> list[dict]:
    """Query Neptune graph for interactions among the given drug/food list."""
    gremlin_client = client.Client(
        f"wss://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/gremlin",
        "g",
        message_serializer=serializer.GraphSONSerializersV2d0()
    )

    # Normalize drug names to lowercase for matching
    drug_names_lower = [d.lower() for d in drugs]

    # Find all interaction edges where EITHER end matches a drug the user mentioned
    query = """
        g.E().hasLabel('INTERACTS_WITH').as('e')
         .outV().has('name', within(drugList)).as('a')
         .select('e').inV().has('name', within(substanceList)).as('b')
         .select('a','e','b')
         .by('name').by(valueMap('severity','description','interaction_type')).by('name')
    """

    # Also check the reverse direction
    query_reverse = """
        g.E().hasLabel('INTERACTS_WITH').as('e')
         .inV().has('name', within(drugList)).as('b')
         .select('e').outV().has('name', within(substanceList)).as('a')
         .select('a','e','b')
         .by('name').by(valueMap('severity','description','interaction_type')).by('name')
    """

    results = []

    for q in [query, query_reverse]:
        try:
            result_set = gremlin_client.submit(
                q,
                {"drugList": drugs, "substanceList": drugs}
            )
            for result in result_set.all().result():
                results.append({
                    "drug_a": result["a"],
                    "drug_b": result["b"],
                    "severity": result["e"]["severity"][0] if isinstance(result["e"]["severity"], list) else result["e"]["severity"],
                    "type": result["e"]["interaction_type"][0] if isinstance(result["e"]["interaction_type"], list) else result["e"]["interaction_type"],
                    "description": result["e"]["description"][0] if isinstance(result["e"]["description"], list) else result["e"]["description"],
                })
        except Exception as ex:
            print(f"Neptune query error: {ex}")

    gremlin_client.close()
    return results


def call_bedrock(user_message: str, interactions: list[dict]) -> str:
    """Call Claude via Bedrock with the interaction context."""
    if interactions:
        interaction_text = "\n".join([
            f"- {i['drug_a']} + {i['drug_b']}: [{i['severity']}] {i['description']}"
            for i in interactions
        ])
        context = f"""The following drug/food/alcohol interactions were found in the database for the substances the user mentioned:

{interaction_text}

Please use this information to answer the user's question clearly and helpfully.
"""
    else:
        context = "No specific interactions were found in the database for the substances mentioned. Remind the user to consult their pharmacist or doctor for personalized advice."

    system_prompt = """You are MedSafe, a friendly and helpful medication safety assistant on a patient-facing website.

Your job is to:
1. Answer questions about potential interactions between medications, foods, and alcohol.
2. Use the interaction data provided to give clear, accurate answers.
3. Always remind the user that this is for informational purposes only and not a substitute for professional medical advice.
4. Use plain language — avoid overly technical jargon.
5. Be warm, reassuring, and clear. If something is HIGH or CRITICAL risk, emphasize it clearly.
6. Never diagnose, treat, or prescribe. Always encourage consulting a doctor or pharmacist.

Format your response in a friendly, readable way using short paragraphs. Use emojis sparingly (⚠️ for warnings, ✅ for safe combinations)."""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": f"{context}\n\nUser's question: {user_message}"
            }
        ]
    })

    response = bedrock.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body
    )

    response_body = json.loads(response["body"].read())
    return response_body["content"][0]["text"]


def extract_substances(text: str) -> list[str]:
    """Simple keyword extraction — Claude will do the heavy lifting here."""
    # Known substances from our dataset (extend this list as dataset grows)
    known = [
        "warfarin", "aspirin", "ibuprofen", "naproxen", "metformin", "simvastatin",
        "atorvastatin", "lisinopril", "ciprofloxacin", "levothyroxine", "methotrexate",
        "fluoxetine", "sertraline", "amoxicillin", "tetracycline", "digoxin",
        "clopidogrel", "metronidazole", "tinidazole", "amlodipine", "buspirone",
        "felodipine", "cyclosporine", "tacrolimus", "sildenafil", "lithium",
        "doxycycline", "phenytoin", "carbamazepine", "spironolactone", "prednisone",
        "ketoconazole", "rifampin",
        # Foods and substances
        "grapefruit", "grapefruit juice", "alcohol", "dairy", "milk", "cheese",
        "coffee", "caffeine", "potassium", "bananas", "spinach", "kale", "broccoli",
        "cranberry juice", "red wine", "licorice", "antacids", "iron", "calcium",
        "st. john's wort", "tyramine", "salt substitute"
    ]
    text_lower = text.lower()
    found = []
    for substance in known:
        if substance in text_lower:
            # Capitalize properly
            found.append(" ".join(w.capitalize() for w in substance.split()))
    return list(set(found))


def handler(event, context):
    """Main Lambda handler."""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST,OPTIONS"
    }

    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    try:
        body = json.loads(event.get("body", "{}"))
        user_message = body.get("message", "").strip()

        if not user_message:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({"error": "No message provided"})
            }

        # Extract substance names from the message
        substances = extract_substances(user_message)
        print(f"Detected substances: {substances}")

        # Query Neptune for interactions
        interactions = []
        if substances:
            interactions = query_neptune(substances)
        print(f"Found {len(interactions)} interactions")

        # Call Bedrock / Claude
        reply = call_bedrock(user_message, interactions)

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "reply": reply,
                "detected_substances": substances,
                "interactions_found": len(interactions)
            })
        }

    except Exception as e:
        print(f"ERROR: {e}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": "Internal server error. Please try again."})
        }
