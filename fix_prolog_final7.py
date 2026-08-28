with open("agi_core.pl", "r") as f:
    content = f.read()

content = content.replace("start_explore_refine('Texto de teste', CycleResult),", "start_explore_refine('Texto de teste', CycleResult), _ = CycleResult,")
with open("agi_core.pl", "w") as f:
    f.write(content)
