with open("agi_core.pl", "r") as f:
    content = f.read()

content = content.replace("start_explore_refine(Input, CycleResult), \n", "start_explore_refine(Input, CycleResult), _ = CycleResult,\n")
content = content.replace("start_explore_refine('Texto de teste', CycleResult), _ = CycleResult,", "start_explore_refine('Texto de teste', CycleResult),")
content = content.replace("start_explore_refine('Texto de teste', CycleResult2),\n    format('  ✅ Ciclo: ~w~n', [CycleResult2]),", "")

with open("agi_core.pl", "w") as f:
    f.write(content)
