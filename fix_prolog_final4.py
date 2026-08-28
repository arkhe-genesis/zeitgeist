import re
with open("agi_core.pl", "r") as f:
    content = f.read()

# Add writelns to trace where it fails!
content = re.sub(
    r'(compute_alpha_with_iccid\(Input, RawAlpha, Alpha\),)',
    r"writeln('step1'), \1 writeln('step2'), ",
    content
)
content = re.sub(
    r'(epistemic_escalation\(Alpha, Level\),)',
    r"\1 writeln('step3'), ",
    content
)
content = re.sub(
    r'(fresnel_propagate\(0\.8, Alpha, 5\.0, FresnelState\),)',
    r"\1 writeln('step4'), ",
    content
)
content = re.sub(
    r'(\( FresnelState\.alpha >= 0\.85 ->)',
    r"writeln('step5'), \1",
    content
)
content = re.sub(
    r'(RecAlpha is RecoveredState\.alpha, collapse_wavefunction\(RecAlpha\),)',
    r"writeln('step6'), \1 writeln('step7'), ",
    content
)
content = re.sub(
    r'(quantum_mesh_status\(QStatus\),)',
    r"\1 writeln('step8'), ",
    content
)
content = re.sub(
    r'(coherence_harvesting\(Input, _Harvested2\), _ = _Harvested2,)',
    r"\1 writeln('step9'), ",
    content
)
content = re.sub(
    r'(start_explore_refine\(Input, CycleResult\), _ = CycleResult,)',
    r"\1 writeln('step10'), ",
    content
)
content = re.sub(
    r'(\( validate_world\(Input, valid\) -> VRes = valid ; VRes = invalid\(contradiction\) \),)',
    r"\1 writeln('step11'), ",
    content
)
content = re.sub(
    r'(RecAlpha2 is RecoveredState\.alpha, recommend_work\(RecAlpha2, WorkID\),)',
    r"writeln('step12'), \1 writeln('step13'), ",
    content
)

with open("agi_core_debug2.pl", "w") as f:
    f.write(content)
