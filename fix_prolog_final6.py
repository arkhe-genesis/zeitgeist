import re
with open("agi_core.pl", "r") as f:
    content = f.read()

# At step 20 it prints Shared, but wait, `collaborative_learning('Texto', Shared)` succeeds.
# And then it prints `✅ Conhecimento Compartilhado`. Wait, it didn't print it!
# Wait, let's trace Test 20.
# format('~n─── [20/20] Substratos 215-217 (Colaboração + Convergência + Coordenação) ───~n'),
# collaborative_learning('Texto', Shared),
# format('  ✅ Conhecimento Compartilhado: ~w~n', [Shared]),
# coordinate_substrates(state, CoordinationStatus),
# format('  ✅ Coordenação: ~w~n', [CoordinationStatus]),
# It didn't print the Shared knowledge.
# Wait, `collaborative_learning` calls `substrate_contribution`, which calls `compute_pci(Context, PCI), PCI > 0.5`.
# `compute_pci(State, PCI)` binds `PCI` based on `State`.
# If `Context` is 'Texto', `State = 'Texto'`.
# `compute_pci('Texto', PCI)` -> `PCI = 0.5`.
# Then `PCI > 0.5` -> `0.5 > 0.5` FALSE.
# Then `substrate_contribution(172, Context, cgf_analysis) :- compute_alpha(Context, Alpha), Alpha < 0.7.` -> TRUE.
# Then `substrate_contribution(184, Context, veto_status) :- circuit_breaker_check(Alpha, 0, _), Alpha < 0.85.`
# Wait, `circuit_breaker_check(Alpha, 0, _)` -> `Alpha` is UNBOUND!
# Then `Alpha >= 0.95` inside `circuit_breaker_check` throws an error because `Alpha` is an unbound variable!
# Yes! `circuit_breaker_check(Alpha, DAlphaDt, Status) :- ( Alpha >= 0.95, ... )` expects Alpha to be a number!

content = content.replace("circuit_breaker_check(Alpha, 0, _), Alpha < 0.85.", "compute_alpha(Context, Alpha), circuit_breaker_check(Alpha, 0, _), Alpha < 0.85.")
content = content.replace("coherence_harvesting(Input, _Harvested2), _ = _Harvested2,", "coherence_harvesting(Input, _Harvested2),")
content = content.replace("start_explore_refine(Input, CycleResult), _ = CycleResult,", "start_explore_refine(Input, _CycleResult),")
content = content.replace("collaborative_learning(Context, SharedKnowledge) :-\n    _ = Context,", "collaborative_learning(Context, SharedKnowledge) :-")

with open("agi_core.pl", "w") as f:
    f.write(content)
