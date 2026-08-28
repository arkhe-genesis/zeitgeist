# Ah! It fails AT step7!
# This means `quantum_mesh_status(QStatus)` failed!
# Let's check `quantum_mesh_status(Status)`
# quantum_mesh_status(Status) :-
#    quantum_alpha(Alpha),
#    findall(A-B, quantum_pair(A, B, _), Pairs),
#    length(Pairs, NumPairs),
#    Status = quantum_state{ ... }
#
# Wait, let's trace `quantum_alpha(Alpha)`
# quantum_alpha(Alpha) :-
#    findall(F, quantum_pair(_, _, F), Fs),
#    ( Fs = [] -> Alpha = 0.0
#    ; sum_list(Fs, Sum), length(Fs, N),
#      AvgF is Sum / N,
#      network_state(NetState),
#      network_alpha(NetState, NetAlpha),
#      Alpha is AvgF * (1.0 - NetAlpha)
#    ).
#
# Does `network_state(NetState)` succeed?
# During initialization:
# `assertz(network_state(state{ ... }))`
# BUT `network_update_state` replaces it with:
# `retractall(network_state(_)), assertz(network_state(state{...}))`.
# What does `network_alpha(NetState, NetAlpha)` do?
# network_alpha(Metrics, Alpha) :-
#    Metrics = state{avg_latency_ms: Lat, total_bandwidth_gbps: TotBW,
#                    used_bandwidth_gbps: UsedBW, failover_count: FC}, ...
# Wait, `network_update_state` creates `state{ status: operational, active_nodes: ActiveCount, avg_latency_ms: AvgLat, total_bandwidth_gbps: TotalBW, used_bandwidth_gbps: TotalBW * 0.3, failover_count: 0, inc_operations: 0, alpha_network: AlphaNet }`.
# But `network_alpha(Metrics, Alpha)` matches `Metrics = state{avg_latency_ms: Lat, total_bandwidth_gbps: TotBW, used_bandwidth_gbps: UsedBW, failover_count: FC}`.
# BUT wait! In SWI-Prolog, `state{a: 1}` ONLY MATCHES `state{a: 1}` if it's the exact same dict, OR if we extract fields: `Lat = Metrics.avg_latency_ms`.
# YOU CANNOT UNIFY A DICT WITH A PARTIAL DICT!
# `Metrics = state{avg_latency_ms: Lat, total_bandwidth_gbps: TotBW, used_bandwidth_gbps: UsedBW, failover_count: FC}` WILL FAIL if `Metrics` has more fields!
#
# YES! `network_update_state` has `status`, `active_nodes`, `inc_operations`, etc.
# So `Metrics = state{...}` fails!

import re
with open("agi_core.pl", "r") as f:
    content = f.read()

content = content.replace("    Metrics = state{avg_latency_ms: Lat, total_bandwidth_gbps: TotBW, \n                    used_bandwidth_gbps: UsedBW, failover_count: FC},",
"    Lat = Metrics.avg_latency_ms, TotBW = Metrics.total_bandwidth_gbps,\n    UsedBW = Metrics.used_bandwidth_gbps, FC = Metrics.failover_count,")

with open("agi_core.pl", "w") as f:
    f.write(content)
