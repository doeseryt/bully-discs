#!/usr/bin/env python3
"""Generate recipe JSONs for BULLY discs.

The BULLY ritual craft: a golden checkerboard around a core item that
identifies the track. Rotten flesh (the bully's mallet), gold nuggets
(YZY gold), and a per-track core.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "src", "main", "resources", "data", "bully_discs", "recipes")
os.makedirs(REC, exist_ok=True)

CORES = {
    "king": "minecraft:gold_ingot",
    "this_a_must": "minecraft:gunpowder",
    "father": "minecraft:compass",
    "all_the_love": "minecraft:poppy",
    "punch_drunk": "minecraft:sugar",
    "whatever_works": "minecraft:paper",
    "mamas_favorite": "minecraft:baked_potato",
    "sisters_and_brothers": "minecraft:stick",
    "bully": "minecraft:rotten_flesh",
    "highs_and_lows": "minecraft:slime_ball",
    "i_cant_wait": "minecraft:clock",
    "white_lines": "minecraft:quartz",
    "circles": "minecraft:echo_shard",
    "preacher_man": "minecraft:book",
    "beauty_and_the_beast": "minecraft:rose_bush",
    "damn": "minecraft:coal",
    "last_breath": "minecraft:firework_rocket",
    "this_one_here": "minecraft:nether_star",
    "losing_your_mind": "minecraft:ender_eye",
}

def disc_item(name):
    return "bully_discs:bully_disc_" + name

for name, core in CORES.items():
    recipe = {
        "type": "minecraft:crafting_shaped",
        "pattern": ["GRG", "RCR", "GRG"],
        "key": {
            "G": {"item": "minecraft:gold_nugget"},
            "R": {"item": "minecraft:rotten_flesh"},
            "C": {"item": core},
        },
        "result": {"item": disc_item(name), "count": 1},
    }
    with open(os.path.join(REC, f"bully_disc_{name}.json"), "w", encoding="utf-8") as f:
        json.dump(recipe, f, indent=2)
    print("recipe:", name, "core:", core)
