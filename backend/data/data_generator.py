import json
import random
import uuid
import copy

with open("golden_records.json", "r") as f:
    base_parts = json.load(f)

generated = []

NUM_PARTS_TO_GENERATE = 250  

def generate_ps_id():
    return f"PS{random.randint(10000000, 99999999)}"

def generate_oem_part_number():
    prefixes = ["WP", "W", "WD", "WDT", "530", "242", "EDR", "WB"]
    prefix = random.choice(prefixes)
    return f"{prefix}{random.randint(1000000, 9999999)}"


def generate_real_model():
    models = [
        "WDT780SAEM1",
        "WDT730PAHZ0",
        "KDTE334GPS0",
        "GDF650SMJ0ES",
        "FGHD2465NF1A",
        "KDTM354ESS3",
        "ADB1500AWW",
        "FFSS2615TS",
        "LFX28968ST",
        "WRF535SMMB00"
    ]
    return random.choice(models)

for _ in range(NUM_PARTS_TO_GENERATE):
    base = random.choice(base_parts)
    part = copy.deepcopy(base)

   
    part["id"] = generate_ps_id()
    part["part_number"] = generate_oem_part_number()
    part["price"] = round(part["price"] * random.uniform(0.9, 1.15), 2)

    part["review_count"] = max(
        0, part["review_count"] + random.randint(5, 120)
    )

    extra_models = [
        generate_real_model()
        for _ in range(random.randint(1, 3))
    ]

    part["compatible_models"] = list(
        set(part.get("compatible_models", []) + extra_models)
    )

    
    if "description" in part:
        part["description"] += (
            " This item is part of our verified OEM-compatible appliance replacement catalog."
        )

   
    part["in_stock"] = random.choices(
        [True, False],
        weights=[92, 8]
    )[0]

    generated.append(part)


with open("full_catalog.json", "w") as f:
    json.dump(generated, f, indent=2)

print(f" Generated {len(generated)} realistic PartSelect-style appliance parts.")
