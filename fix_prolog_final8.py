with open("agi_core.pl", "r") as f:
    content = f.read()

content = content.replace("start_explore_refine('Texto de teste', CycleResult),\n    format('  ✅ Ciclo: ~w~n', [CycleResult]),", "start_explore_refine('Texto de teste', CycleResult2),\n    format('  ✅ Ciclo: ~w~n', [CycleResult2]),")

with open("agi_core.pl", "w") as f:
    f.write(content)
